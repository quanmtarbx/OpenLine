@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "APP_DIR=%~dp0"
echo %APP_DIR% | findstr /I /L /C:"\Temp\Rar$" >nul
if not errorlevel 1 (
  echo This copy is running from WinRAR's temporary preview folder.
  echo Close this window, right-click the ZIP, choose Extract All, and run the starter from the extracted folder.
  pause
  exit /b 1
)
if not exist "%~dp0OpenLineDesk.py" (
  echo OpenLineDesk.py is missing beside this starter.
  echo Extract the entire ZIP, then run Start-OpenLine.bat from the extracted folder.
  pause
  exit /b 1
)
set "RUNTIME=%LOCALAPPDATA%\OpenLineDesk\Python313"
set "INSTALLER=%TEMP%\openline-python-3.13.17-amd64.exe"
set "INSTALL_LOG=%LOCALAPPDATA%\OpenLineDesk\python-install.log"

if exist "%RUNTIME%\python.exe" (
  "%RUNTIME%\python.exe" -c "import tkinter" >nul 2>&1
  if not errorlevel 1 goto :private_python
)

where py >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import tkinter" >nul 2>&1
  if not errorlevel 1 (
    py -3 "%~dp0OpenLineDesk.py"
    if errorlevel 1 goto :app_error
    goto :end
  )
)

where python >nul 2>&1
if not errorlevel 1 (
  python -c "import tkinter" >nul 2>&1
  if not errorlevel 1 (
    python "%~dp0OpenLineDesk.py"
    if errorlevel 1 goto :app_error
    goto :end
  )
)

for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
  if exist "%%~D\python.exe" (
    "%%~D\python.exe" -c "import tkinter" >nul 2>&1
    if not errorlevel 1 (
      "%%~D\python.exe" "%~dp0OpenLineDesk.py"
      if errorlevel 1 goto :app_error
      goto :end
    )
  )
)

for /d %%D in ("%ProgramFiles%\Python3*") do (
  if exist "%%~D\python.exe" (
    "%%~D\python.exe" -c "import tkinter" >nul 2>&1
    if not errorlevel 1 (
      "%%~D\python.exe" "%~dp0OpenLineDesk.py"
      if errorlevel 1 goto :app_error
      goto :end
    )
  )
)

echo No usable Python with Tkinter was found. Preparing a private runtime...
echo This one-time setup downloads Python from python.org.
if not exist "%LOCALAPPDATA%\OpenLineDesk" mkdir "%LOCALAPPDATA%\OpenLineDesk"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.13.17/python-3.13.17-amd64.exe' -OutFile '%INSTALLER%' -UseBasicParsing; exit 0 } catch { Write-Error $_; exit 1 }"
if errorlevel 1 (
  echo Could not download Python. Check your internet connection and try again.
  pause
  exit /b 1
)
start /wait "" "%INSTALLER%" /passive InstallAllUsers=0 TargetDir="%RUNTIME%" Include_launcher=0 Include_test=0 Include_pip=0 Include_tcltk=1 PrependPath=0 Shortcuts=0 /log "%INSTALL_LOG%"
set "PYTHON_INSTALL_EXIT=!ERRORLEVEL!"
if not exist "%RUNTIME%\python.exe" (
  echo Python setup did not finish. Installer exit code: !PYTHON_INSTALL_EXIT!
  echo Details were saved to:
  echo %INSTALL_LOG%
  echo If the error repeats, send that log file.
  pause
  exit /b 1
)
del "%INSTALLER%" >nul 2>&1

:private_python
"%RUNTIME%\python.exe" "%~dp0OpenLineDesk.py"
if errorlevel 1 goto :app_error
goto :end

:app_error
echo.
echo OpenLine Desk stopped with an error. Please send a screenshot of the error above.
pause
goto :end

:end
endlocal




