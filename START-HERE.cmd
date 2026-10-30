@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install.ps1" -FromLauncher
set "WIZARD_EXIT=%ERRORLEVEL%"
if "%WIZARD_EXIT%"=="20" exit /b 0
if "%WIZARD_EXIT%"=="21" exit /b 1
if "%WIZARD_EXIT%"=="22" exit /b 2
pause
exit /b %WIZARD_EXIT%
