@echo off
REM Stop everything this project started on Windows, then show what is still up.
REM
REM   stop.bat              stop the API and the sis-* containers
REM   stop.bat --dry-run    print what would be stopped, change nothing
REM
REM Scope: only the API listening on the demo port and the sis-* containers.
REM Data survives: containers are stopped, never removed, no volume is pruned.
REM UNTESTED: written against Docker Desktop but never executed on Windows (no Windows host).
setlocal enabledelayedexpansion
set "API_PORT=8000"
set "CONTAINERS=sis-mongos sis-mongo-a sis-mongo-b sis-mongo-cfg sis-redis sis-postgres sis-verify-pg"
set "DRY=0"
for %%a in (%*) do if "%%a"=="--dry-run" set "DRY=1"

echo.
echo ==^> Stopping this project's services

set "STOPPED_API=0"
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":%API_PORT% .*LISTENING"') do (
  if "!STOPPED_API!"=="0" (
    if "%DRY%"=="1" (
      echo     would stop API pid %%p
    ) else (
      taskkill /PID %%p /F >nul 2>&1 && echo     API stopped ^(pid %%p^)
    )
    set "STOPPED_API=1"
  )
)
if "%STOPPED_API%"=="0" echo     API was not running

where docker >nul 2>&1 || goto :verify
for %%n in (%CONTAINERS%) do (
  docker container inspect %%n >nul 2>&1 || continue
  for /f "delims=" %%s in ('docker inspect -f "{{.State.Running}}" %%n 2^>nul') do set "STATE=%%s"
  if "!STATE!"=="true" (
    if "%DRY%"=="1" (
      echo     would stop container %%n
    ) else (
      docker stop %%n >nul 2>&1 && echo     container stopped: %%n
    )
  )
)

if "%DRY%"=="1" (
  echo.
  echo Dry run: nothing was changed.
  exit /b 0
)

:verify
echo.
echo ==^> Verifying nothing is left running
set "LEFTOVER=0"
netstat -ano | findstr /r /c:":%API_PORT% .*LISTENING" >nul 2>&1 && (echo     port %API_PORT% still open & set "LEFTOVER=1") || echo     port %API_PORT% closed
if not "%LEFTOVER%"=="0" goto :ports
echo     api stopped

:ports
set "STILL="
if exist "%SystemRoot%\System32\docker.exe" for /f "delims=" %%n in ('docker ps --filter "name=sis-" --format "{{.Names}}" 2^>nul') do set "STILL=!STILL! %%n"
if defined STILL (
  echo     containers still running:!STILL!
  set "LEFTOVER=1"
) else (
  echo     containers stopped
)

if "%LEFTOVER%"=="1" (
  echo.
  echo Something is still up. Check it with:
  echo   netstat -ano ^| findstr :%API_PORT%
  echo   docker ps --format "{{.Names}} {{.Status}}"
  exit /b 1
)

echo.
echo All stopped. Data volumes are untouched: run.bat brings the same database back.
echo.
exit /b 0
