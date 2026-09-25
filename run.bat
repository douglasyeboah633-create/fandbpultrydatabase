@echo off
setlocal EnableExtensions
title F ^& B Poultry Farm Management System - Start
cd /d "%~dp0backend"

echo ============================================================
echo    F ^& B POULTRY FARM MANAGEMENT SYSTEM
echo    Local server  :  http://localhost:5000
echo ============================================================
echo.

REM ---------- 1. Python must be installed ----------
python --version >nul 2>&1
if errorlevel 1 (
  echo [X] Python was not found.
  echo     Install it from https://www.python.org/downloads/ and tick
  echo     "Add python.exe to PATH" during setup, then run this file again.
  echo.
  pause
  exit /b 1
)

REM ---------- 2. Python packages ----------
echo [1/5] Checking the Python packages...
python -c "import flask, flask_cors, flask_bcrypt, flask_jwt_extended, sqlalchemy, dotenv" >nul 2>&1
if errorlevel 1 (
  echo       Installing the missing packages, please wait...
  python -m pip install --disable-pip-version-check -r requirements.txt
  if errorlevel 1 (
    echo [X] The packages could not be installed. Check your internet and try again.
    echo.
    pause
    exit /b 1
  )
)

REM ---------- 3. Database ----------
echo [2/5] Checking the database ^(farm.db^)...
if not exist farm.db (
  echo       Creating farm.db for the first time...
  python seed.py
  if errorlevel 1 (
    echo [X] The database could not be created. See the message above.
    echo.
    pause
    exit /b 1
  )
)

REM ---------- 4. Port 5000 must belong to THIS app ----------
REM If another server is holding port 5000 (for example the older Node copy
REM of this project that lived in "F and B Poultry Database"), then Windows
REM sends "localhost" to that other server and you see the wrong website.
REM So stop whatever holds the port, then let the farm server own it alone.
echo [3/5] Making sure port 5000 is free...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$seen=@(); $mine=0; $t=Get-Content 'server.pid' -ErrorAction SilentlyContinue; if ($t) { $mine=[int]($t[0] -replace '[^0-9]','') }; $c=Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue; foreach ($x in $c) { $p=$x.OwningProcess; if (($p -gt 0) -and ($seen -notcontains $p)) { $seen += $p; $n=(Get-Process -Id $p -ErrorAction SilentlyContinue).ProcessName; Write-Host ('      stopping ' + $n + ' (PID ' + $p + ') which was holding port 5000'); Stop-Process -Id $p -Force -ErrorAction SilentlyContinue } }; if ($seen.Count -eq 0) { Write-Host '      port 5000 is free' }; Start-Sleep -Milliseconds 900"

REM ---------- 5. Start the farm server in the background ----------
echo [4/5] Starting the farm server...
start "FB Poultry Farm Server" /B cmd /c "python app.py > _out.log 2> _err.log"

REM ---------- 6. Wait until the website really answers ----------
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; $url='http://localhost:5000'; for ($i=0; $i -lt 45; $i++) { foreach ($u in @('http://localhost:5000/','http://127.0.0.1:5000/')) { try { $r=Invoke-WebRequest -UseBasicParsing -Uri $u -TimeoutSec 2; if ($r.StatusCode -eq 200) { $url=$u.TrimEnd('/'); $ok=$true; break } } catch { } }; if ($ok) { break }; Start-Sleep -Milliseconds 700 }; Set-Content -Path ($env:TEMP + '\fb_url.txt') -Value $url -Encoding ASCII; if ($ok) { Write-Host ('      the farm website is answering on ' + $url) } else { Write-Host '      the server did not answer yet - see backend\_err.log' }"
REM ---------- 7. Open the website in the browser ----------
echo [5/5] Opening the farm website in your browser...
set "SITEURL=http://localhost:5000"
if exist "%TEMP%\fb_url.txt" (
  set /p SITEURL=<"%TEMP%\fb_url.txt"
  del "%TEMP%\fb_url.txt" >nul 2>&1
)
start "" %SITEURL%

set "LANIP="
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ip=''; $a=Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue; foreach ($x in $a) { if (($ip -eq '') -and ($x.IPAddress -notlike '127.*') -and ($x.IPAddress -notlike '169.254.*')) { $ip=$x.IPAddress } }; $ip" > "%TEMP%\fb_lan_ip.txt" 2>nul
set /p LANIP=<"%TEMP%\fb_lan_ip.txt"
del "%TEMP%\fb_lan_ip.txt" >nul 2>&1

echo.
echo ============================================================
echo   OPEN THE FARM WEBSITE AT:   %SITEURL%
echo   This start button makes port 5000 belong to the farm system,
echo   so that address always opens THIS poultry app.
echo.
if defined LANIP echo   Workers on the same Wi-Fi can open:  http://%LANIP%:5000
echo.
echo   Manager login : the username and password in backend\.env
echo                   ^(not printed here - this file goes to GitHub^).
echo   Add or reset workers : Manager page, then "Workers".
echo.
echo   Keep this window OPEN while the farm app is being used.
echo   Press any key to STOP the farm server and free the port.
echo ============================================================
pause >nul

echo Stopping the farm server...
if exist server.pid (
  for /f "usebackq delims=" %%P in ("server.pid") do taskkill /PID %%P /F >nul 2>&1
  del server.pid >nul 2>&1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$c=Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue; foreach ($x in $c) { Stop-Process -Id $x.OwningProcess -Force -ErrorAction SilentlyContinue }"
echo Server stopped. You can close this window.
endlocal

