@echo off
setlocal
REM NutriFlow local deployment: single Windows entry point.
REM The PowerShell policy override applies only to this child process.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy.ps1" %*
exit /b %ERRORLEVEL%
