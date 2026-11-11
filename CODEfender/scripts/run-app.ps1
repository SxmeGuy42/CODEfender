# Spouštěč CODEfenderu. Před startem zkontroluje Python a upozorní,
# když chybí kiro-cli (aplikace se stejně nastartuje, agent ale nepojede).

Write-Host "CODEfender - bezpecnostni analyza kodu" -ForegroundColor Cyan
Write-Host ("=" * 50)
Write-Host ""

Set-Location (Split-Path $PSScriptRoot -Parent)

# některé systémy mají jen `py`, jiné jen `python` - zkus oba
$pythonCmd = $null
foreach ($candidate in @("py", "python")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $pythonCmd = $candidate
        break
    }
}

if (-not $pythonCmd) {
    Write-Host "Python neni nainstalovan nebo neni v PATH" -ForegroundColor Red
    exit 1
}

# kiro-cli je nutné pro reálný běh analýzy, ale aplikaci to nezastavuje
if (-not (Get-Command kiro-cli -ErrorAction SilentlyContinue)) {
    Write-Host "Upozorneni: kiro-cli nebyl nalezen v PATH." -ForegroundColor Yellow
    Write-Host "Aplikace se spusti, ale agenta nebude mozne pouzit." -ForegroundColor Yellow
    Write-Host "Instalace: irm 'https://cli.kiro.dev/install.ps1' | iex" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Spoustim aplikaci..." -ForegroundColor Green
& $pythonCmd run.py
