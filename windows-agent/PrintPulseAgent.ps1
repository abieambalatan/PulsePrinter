$ErrorActionPreference = 'Stop'
$channel = 'Microsoft-Windows-PrintService/Operational'
$dataDirectory = Join-Path $env:LOCALAPPDATA 'PrintPulseAgent'
$configPath = Join-Path $dataDirectory 'config.json'
$statePath = Join-Path $dataDirectory 'state.json'
$logPath = Join-Path $dataDirectory 'agent.log'

function Write-AgentLog([string]$message) {
    try {
        $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $message
        Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
    } catch {
        # Logging must not stop print-event collection.
    }
}

function Save-AgentState([long]$recordId) {
    @{ lastRecordId = $recordId } | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8
}

function Get-PrintParameters($eventRecord) {
    $xml = [xml]$eventRecord.ToXml()
    $values = @{}
    foreach ($node in $xml.SelectNodes("//*[starts-with(local-name(), 'Param')]") ) {
        if ($node.LocalName -match '^Param([1-8])$') {
            $values[[int]$Matches[1]] = [string]$node.InnerText
        }
    }
    return $values
}

function Get-EventPaperSize($eventRecord) {
    # Event 307 usually has no paper-size field. Some vendor providers add a
    # named PaperSize/MediaSize field, so inspect those without guessing from
    # byte counts or job page counts.
    try {
        $xml = [xml]$eventRecord.ToXml()
        foreach ($node in $xml.SelectNodes('//*')) {
            $fieldName = [string]$node.GetAttribute('Name')
            if (-not $fieldName) { $fieldName = [string]$node.LocalName }
            if ($fieldName -match '(?i)(paper|media).?size|size.?name') {
                $value = ([string]$node.InnerText).Trim()
                if ($value) {
                    if ($value -match '(?i)\bA4\b') { return 'A4' }
                    if ($value -match '(?i)\b(letter|short)\b') { return 'Short' }
                    if ($value -match '(?i)\b(legal|long)\b') { return 'Long' }
                }
            }
        }
    } catch {
        # Size is optional; keep collecting the job if event XML is unusual.
    }
    return 'Unknown'
}

function ConvertTo-TrackedPaperSize([string]$value) {
    if ($value -match '(?i)\bA4\b') { return 'A4' }
    if ($value -match '(?i)\b(letter|short)\b') { return 'Short' }
    if ($value -match '(?i)\b(legal|long)\b') { return 'Long' }
    return 'Unknown'
}

function Update-QueuedJobPaperSizes($cache) {
    # Win32_PrintJob exposes the driver's selected paper while a job is queued.
    # Keep the last observed size briefly because Event 307 is raised on completion,
    # after Windows may already have removed the job from the queue.
    try {
        foreach ($job in @(Get-CimInstance -ClassName Win32_PrintJob -ErrorAction Stop)) {
            $size = ConvertTo-TrackedPaperSize ([string]$job.PaperSize)
            $jobId = [string]$job.JobId
            $jobName = [string]$job.Name
            $comma = $jobName.LastIndexOf(',')
            if ($size -eq 'Unknown' -or -not $jobId -or $comma -lt 1) { continue }
            $printerName = $jobName.Substring(0, $comma).Trim()
            if ($printerName) {
                $key = ('{0}|{1}' -f $printerName.ToLowerInvariant(), $jobId)
                $cache[$key] = @{ paper_size = $size; seen_at = Get-Date }
            }
        }
    } catch {
        # WMI may be unavailable on some Windows configurations; events still upload.
    }

    $cutoff = (Get-Date).AddMinutes(-10)
    foreach ($key in @($cache.Keys)) {
        if ($cache[$key].seen_at -lt $cutoff) { $cache.Remove($key) }
    }
}

function Get-LocalPrinterInventory {
    $printers = @()
    foreach ($printer in @(Get-CimInstance -ClassName Win32_Printer -ErrorAction Stop)) {
        $name = ([string]$printer.Name).Trim()
        if (-not $name) { continue }
        $status = if ($printer.WorkOffline -or [int]$printer.PrinterStatus -eq 7) { 'Offline' } else { 'Online' }
        $printers += @{
            name = $name
            location = ([string]$printer.Location).Trim()
            status = $status
        }
    }
    return $printers
}

if (-not (Test-Path -LiteralPath $configPath)) {
    Write-AgentLog 'Configuration file is missing; run Setup-PrintPulseAgent.ps1 again.'
    exit 1
}

$config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
$apiBaseUrl = ([string]$config.apiBaseUrl).TrimEnd('/')
$secureToken = ConvertTo-SecureString ([string]$config.protectedToken)
$tokenPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
$apiToken = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPointer)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPointer)
$headers = @{ Authorization = "Bearer $apiToken" }

try {
    $latest = Get-WinEvent -LogName $channel -MaxEvents 1 -ErrorAction SilentlyContinue
    $latestRecordId = if ($latest) { [long]$latest.RecordId } else { 0 }

    if (Test-Path -LiteralPath $statePath) {
        $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        $lastRecordId = [long]$state.lastRecordId
    } else {
        # Start from now; do not upload print history created before setup.
        $lastRecordId = $latestRecordId
        Save-AgentState $lastRecordId
    }

    Write-AgentLog 'Monitoring completed jobs from the Windows print queue.'
    $jobPaperSizes = @{}
    $nextPrinterSync = [DateTime]::MinValue
    while ($true) {
        try {
            Update-QueuedJobPaperSizes $jobPaperSizes

            if ((Get-Date) -ge $nextPrinterSync) {
                $nextPrinterSync = (Get-Date).AddSeconds(60)
                try {
                    $inventory = @{
                        source_machine = $env:COMPUTERNAME
                        printers = @(Get-LocalPrinterInventory)
                    } | ConvertTo-Json -Depth 4 -Compress
                    $syncResult = Invoke-RestMethod -Uri "$apiBaseUrl/api/printers/agent-sync/" -Method Post -Headers $headers -ContentType 'application/json' -Body $inventory -TimeoutSec 30
                    Write-AgentLog "Reported $($syncResult.synced) local printer(s) to PrintPulse."
                } catch {
                    Write-AgentLog "Could not report local printer inventory; it will retry. $($_.Exception.Message)"
                    $nextPrinterSync = (Get-Date).AddSeconds(15)
                }
            }

            $latest = Get-WinEvent -LogName $channel -MaxEvents 1 -ErrorAction SilentlyContinue
            $latestRecordId = if ($latest) { [long]$latest.RecordId } else { 0 }
            if ($latestRecordId -lt $lastRecordId) {
                # The Windows event log was cleared or rotated to a new record sequence.
                $lastRecordId = $latestRecordId
                Save-AgentState $lastRecordId
                Write-AgentLog 'Windows print log sequence changed; monitoring resumed from the current log.'
            }

            $xpath = "*[System[(EventID=307) and (EventRecordID > $lastRecordId)]]"
            $events = @(Get-WinEvent -LogName $channel -FilterXPath $xpath -Oldest -ErrorAction SilentlyContinue)
            $uploadFailed = $false

            foreach ($eventRecord in $events) {
                $eventRecordId = [long]$eventRecord.RecordId
                $parameters = Get-PrintParameters $eventRecord
                $printerName = ([string]$parameters[5]).Trim()
                $pageText = ([string]$parameters[8]).Trim()
                $paperSize = Get-EventPaperSize $eventRecord
                if ($paperSize -eq 'Unknown') {
                    $jobKey = ('{0}|{1}' -f $printerName.ToLowerInvariant(), ([string]$parameters[1]).Trim())
                    if ($jobPaperSizes.ContainsKey($jobKey)) {
                        $paperSize = $jobPaperSizes[$jobKey].paper_size
                        $jobPaperSizes.Remove($jobKey)
                    }
                }

                if (-not $printerName -or $pageText -notmatch '^\d+$') {
                    $lastRecordId = $eventRecordId
                    Save-AgentState $lastRecordId
                    Write-AgentLog "Skipped an unsupported print event (record $eventRecordId)."
                    continue
                }

                $payload = @{
                    printer_name = $printerName
                    user_name = ([string]$parameters[3]).Trim()
                    pages = [long]$pageText
                    paper_size = $paperSize
                    source_machine = $env:COMPUTERNAME
                    source_event_id = [string]$eventRecordId
                    created_at = $eventRecord.TimeCreated.ToUniversalTime().ToString('o')
                } | ConvertTo-Json -Compress

                try {
                    $null = Invoke-RestMethod -Uri "$apiBaseUrl/api/print-jobs/ingest/" -Method Post -Headers $headers -ContentType 'application/json' -Body $payload -TimeoutSec 90
                    $lastRecordId = $eventRecordId
                    Save-AgentState $lastRecordId
                    Write-AgentLog "Uploaded completed print event $eventRecordId."
                } catch {
                    $uploadFailed = $true
                    $errorDetail = $_.Exception.Message
                    $response = $_.Exception.Response
                    if ($response -and $response.StatusCode) {
                        $errorDetail += " HTTP $([int]$response.StatusCode)"
                    }
                    Write-AgentLog "Could not upload event $eventRecordId; it will be retried. $errorDetail"
                    break
                }
            }

            if (-not $uploadFailed -and $latestRecordId -gt $lastRecordId) {
                $lastRecordId = $latestRecordId
                Save-AgentState $lastRecordId
            }
        } catch {
            Write-AgentLog 'Could not read the Windows print log; retrying.'
        }

        Start-Sleep -Seconds 1
    }
} catch {
    Write-AgentLog 'Agent could not start. Run setup again and confirm the PrintService Operational log is enabled.'
    exit 1
}
