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
    while ($true) {
        try {
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
                    Write-AgentLog "Could not upload event $eventRecordId; it will be retried. Check the internet connection and agent token."
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

        Start-Sleep -Seconds 5
    }
} catch {
    Write-AgentLog 'Agent could not start. Run setup again and confirm the PrintService Operational log is enabled.'
    exit 1
}
