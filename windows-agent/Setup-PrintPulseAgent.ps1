$ErrorActionPreference = 'Stop'

$channel = 'Microsoft-Windows-PrintService/Operational'
$defaultUrl = 'https://printpulse-1wpm.onrender.com'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this setup in PowerShell as Administrator, using your normal Windows account.'
}

Write-Host 'Step 1 of 2: Press Enter to use the default website URL. Do not paste the agent token here.'
$apiBaseUrl = (Read-Host "PrintPulse URL [$defaultUrl]").Trim()
if (-not $apiBaseUrl) { $apiBaseUrl = $defaultUrl }
$apiBaseUrl = $apiBaseUrl.TrimEnd('/')
$parsedUrl = $null
if (-not [Uri]::TryCreate($apiBaseUrl, [UriKind]::Absolute, [ref]$parsedUrl) -or $parsedUrl.Scheme -ne 'https') {
    throw 'That is not an HTTPS URL. Rerun setup, press Enter to accept the default URL, then paste the agent token at the next prompt.'
}

Write-Host 'Step 2 of 2: Paste the token from the Render Environment page at the next prompt.'
$agentToken = Read-Host 'Paste PRINTPULSE_AGENT_TOKEN_V2' -AsSecureString
if ($agentToken.Length -eq 0) { throw 'The agent token cannot be empty.' }

Write-Host 'Checking that PrintPulse is reachable...'
$null = Invoke-WebRequest -Uri "$apiBaseUrl/api/health/" -TimeoutSec 120 -UseBasicParsing

$wevtutil = Join-Path $env:SystemRoot 'System32\wevtutil.exe'
& $wevtutil sl $channel /e:true
if ($LASTEXITCODE -ne 0) {
    throw 'Windows could not enable the PrintService Operational log.'
}

$dataDirectory = Join-Path $env:LOCALAPPDATA 'PrintPulseAgent'
New-Item -ItemType Directory -Path $dataDirectory -Force | Out-Null
$configPath = Join-Path $dataDirectory 'config.json'
$config = @{
    apiBaseUrl = $apiBaseUrl
    protectedToken = ConvertFrom-SecureString $agentToken
}
$config | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8

$agentPath = Join-Path $PSScriptRoot 'PrintPulseAgent.ps1'
$powershellPath = Join-Path $PSHOME 'powershell.exe'
$startupCommand = '"{0}" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "{1}"' -f $powershellPath, $agentPath
$runKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
New-Item -Path $runKey -Force | Out-Null
Set-ItemProperty -Path $runKey -Name 'PrintPulseAgent' -Value $startupCommand

# Replace an already-running copy so an upgrade does not leave two monitors
# polling the same event log and writing the shared cursor file.
$agentPathFull = [IO.Path]::GetFullPath($agentPath)
Get-CimInstance -ClassName Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -and $_.CommandLine.IndexOf($agentPathFull, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

$arguments = '-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}"' -f $agentPath
Start-Process -FilePath $powershellPath -ArgumentList $arguments -WindowStyle Hidden

Write-Host ''
Write-Host 'PrintPulse printer monitoring is set up.' -ForegroundColor Green
Write-Host 'The agent starts when you sign in to this Windows account.'
Write-Host "Local status log: $(Join-Path $dataDirectory 'agent.log')"
Write-Host 'Print one test page, then check Print Jobs on the PrintPulse website.'
