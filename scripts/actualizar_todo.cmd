@echo off
setlocal
cd /d "%~dp0.."
set "PS_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS_EXE%" set "PS_EXE=powershell.exe"
"%PS_EXE%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0actualizar_datos.ps1"
if errorlevel 1 exit /b %errorlevel%
echo.
echo Proyecto actualizado. Abre Power BI Desktop y pulsa Actualizar.
endlocal
