@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
set "NODE_DIRECTORY=%ProgramFiles%\nodejs"
set "NPM_COMMAND=%NODE_DIRECTORY%\npm.cmd"

if not exist "%NPM_COMMAND%" (
    echo Node.js was not found at "%NODE_DIRECTORY%".
    echo Install Node.js LTS, then run this file again.
    pause
    exit /b 1
)

start "PrintPulse Django API" powershell.exe -NoExit -Command "Set-Location -LiteralPath '%PROJECT_ROOT%backend'; python manage.py migrate; if ($LASTEXITCODE -eq 0) { python manage.py runserver 127.0.0.1:8000 }"
start "PrintPulse React App" powershell.exe -NoExit -Command "$env:Path = '%NODE_DIRECTORY%;' + $env:Path; Set-Location -LiteralPath '%PROJECT_ROOT%'; & '%NPM_COMMAND%' run dev -- --host 0.0.0.0"

timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:5173/"
for /f "delims=" %%I in ('powershell -NoProfile -Command "Get-NetIPAddress -AddressFamily IPv4 ^| Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and $_.AddressState -eq 'Preferred' } ^| Select-Object -First 1 -ExpandProperty IPAddress"') do set "LAN_ADDRESS=%%I"
echo.
echo Other computers on this network can open: http://%LAN_ADDRESS%:5173/
echo Allow port 5173 through Windows Defender Firewall on this PC if prompted.
echo.
pause

endlocal
