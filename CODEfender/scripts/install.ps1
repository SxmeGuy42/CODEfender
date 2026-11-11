# Instalace závislostí CODEfenderu (Python + Node + kontrola Kiro CLI).

Write-Host "CODEfender - instalace zavislosti" -ForegroundColor Cyan
Write-Host ""

Set-Location (Split-Path $PSScriptRoot -Parent)

# ── Python ────────────────────────────────────────────────
Write-Host "Kontroluji Python..." -ForegroundColor Gray
$pythonVersion = py --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "   OK: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "   Python neni nainstalovan!" -ForegroundColor Red
    Write-Host "   Stahni Python z: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Instaluji Python balicky (PySide6, SAST nastroje)..." -ForegroundColor Cyan
py -m pip install --upgrade pip
py -m pip install -r requirements.txt

# ── Node.js (volitelné - jen pro ESLint) ─────────────────
Write-Host ""
if (Get-Command npm -ErrorAction SilentlyContinue) {
    Write-Host "Instaluji Node.js balicky (ESLint toolchain)..." -ForegroundColor Cyan
    npm install
} else {
    # bez npm prostě jen JavaScript analýza nefunguje, není to fatal
    Write-Host "npm nenalezen - ESLint analyza JavaScriptu nebude dostupna." -ForegroundColor Yellow
}

# ── Kiro CLI (samotného agenta neinstalujeme, jen zkontrolujeme) ──
Write-Host ""
if (Get-Command kiro-cli -ErrorAction SilentlyContinue) {
    Write-Host "Kiro CLI je nainstalovano." -ForegroundColor Green
} else {
    Write-Host "Kiro CLI NENI nainstalovano - bez nej agent nefunguje." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Nainstaluj ho timto prikazem (Windows 11):" -ForegroundColor White
    Write-Host "    irm 'https://cli.kiro.dev/install.ps1' | iex" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Po instalaci se prihlas prikazem: kiro-cli" -ForegroundColor White
}

Write-Host ""
Write-Host "Instalace dokoncena." -ForegroundColor Green
Write-Host ""
Write-Host "Dalsi kroky:" -ForegroundColor Cyan
Write-Host "1. Ujisti se, ze je nainstalovane a prihlasene Kiro CLI" -ForegroundColor White
Write-Host "2. Spust aplikaci:  .\scripts\run-app.ps1   (nebo: py run.py)" -ForegroundColor White
Write-Host ""
