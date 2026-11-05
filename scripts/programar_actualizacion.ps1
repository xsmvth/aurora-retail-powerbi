param(
    [string]$Hora = "06:00",
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$UpdateScript = Join-Path $PSScriptRoot "actualizar_datos.ps1"
if (-not $PythonExe) {
    $PythonExe = (Get-Command python -ErrorAction Stop).Source
}

$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$UpdateScript`" -PythonExe `"$PythonExe`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments -WorkingDirectory $ProjectRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $Hora
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName "Aurora Retail ETL" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Actualiza el almacén Aurora Retail y los CSV para Power BI." `
    -Force | Out-Null

Write-Host "Tarea 'Aurora Retail ETL' programada diariamente a las $Hora."
