param(
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $PythonExe) {
    $PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
}
if (-not $PythonExe) {
    $PythonExe = (Get-Command py -ErrorAction SilentlyContinue).Source
}
if (-not $PythonExe) {
    throw "Python no está disponible. Instala Python 3.11 o superior."
}

Push-Location $ProjectRoot
try {
    & $PythonExe ".\pipeline\run_pipeline.py"
    if ($LASTEXITCODE -ne 0) {
        throw "El pipeline terminó con código $LASTEXITCODE."
    }
    & $PythonExe ".\pipeline\analyze_portfolio.py"
    if ($LASTEXITCODE -ne 0) {
        throw "El análisis de KPIs terminó con código $LASTEXITCODE."
    }
    & $PythonExe ".\pipeline\create_dashboard_previews.py"
    if ($LASTEXITCODE -ne 0) {
        throw "La generación de capturas terminó con código $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
