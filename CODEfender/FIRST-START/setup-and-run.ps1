# CODEfender - První spuštění
# Tento skript nainstaluje závislosti, vytvoří zástupce, spustí aplikaci a smaže se

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CODEfender - První spuštění" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ============================================
# 1. Kontrola Python
# ============================================
Write-Host "[1/5] Kontroluji Python..." -ForegroundColor Yellow

try {
    $pythonVersion = & python --version 2>&1
    Write-Host "✓ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python není nainstalovaný!" -ForegroundColor Red
    Write-Host "  Stáhni Python 3.11+ z https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

# ============================================
# 2. Kontrola a instalace Kiro CLI
# ============================================
Write-Host "[2/5] Kontroluji Kiro CLI..." -ForegroundColor Yellow

$kiroPath = $null
$possiblePaths = @(
    "kiro-cli",
    "$env:LOCALAPPDATA\Programs\Kiro\kiro-cli.exe",
    "$env:LOCALAPPDATA\kiro-cli\kiro-cli.exe",
    "$env:USERPROFILE\.local\bin\kiro-cli.exe"
)

foreach ($path in $possiblePaths) {
    try {
        $null = & $path --version 2>&1
        $kiroPath = $path
        break
    } catch {}
}

if (-not $kiroPath) {
    Write-Host "✗ Kiro CLI není nainstalované" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Stahuji a instaluji Kiro CLI..." -ForegroundColor Cyan
    
    try {
        # Stažení a instalace Kiro CLI
        irm 'https://cli.kiro.dev/install.ps1' | iex
        
        # Pokus najít Kiro CLI znovu
        Start-Sleep -Seconds 2
        foreach ($path in $possiblePaths) {
            try {
                $null = & $path --version 2>&1
                $kiroPath = $path
                break
            } catch {}
        }
        
        if ($kiroPath) {
            Write-Host "✓ Kiro CLI úspěšně nainstalováno" -ForegroundColor Green
        } else {
            Write-Host "✗ Instalace se nezdařila" -ForegroundColor Red
            Write-Host "  Zkus ručně: irm 'https://cli.kiro.dev/install.ps1' | iex" -ForegroundColor Yellow
            exit 1
        }
    } catch {
        Write-Host "✗ Chyba při instalaci Kiro CLI" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        exit 1
    }
} else {
    $kiroVersion = & $kiroPath --version 2>&1
    Write-Host "✓ Kiro CLI nalezeno: $kiroVersion" -ForegroundColor Green
}

# ============================================
# 2b. Kontrola přihlášení do Kiro
# ============================================
Write-Host ""
Write-Host "Kontroluji přihlášení do Kiro..." -ForegroundColor Yellow

$loginCheck = & $kiroPath whoami 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Jsi přihlášený do Kiro" -ForegroundColor Green
} else {
    Write-Host "✗ Nejsi přihlášený do Kiro!" -ForegroundColor Red
    Write-Host ""
    Write-Host "════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host "  Pro použití CODEfenderu potřebuješ Kiro účet" -ForegroundColor Yellow
    Write-Host "════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. Ještě nemáš účet?" -ForegroundColor Cyan
    Write-Host "   → Vytvoř si ho na: https://kiro.dev/" -ForegroundColor White
    Write-Host ""
    Write-Host "2. Už máš účet?" -ForegroundColor Cyan
    Write-Host "   → Přihlaš se zadáním: kiro-cli login" -ForegroundColor White
    Write-Host ""
    
    $response = Read-Host "Chceš se přihlásit teď? (a/n)"
    if ($response -eq "a" -or $response -eq "A") {
        Write-Host ""
        Write-Host "Otevírám přihlašovací stránku v prohlížeči..." -ForegroundColor Cyan
        & $kiroPath login
        
        # Ověření po přihlášení
        Start-Sleep -Seconds 2
        $loginCheck = & $kiroPath whoami 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Úspěšně přihlášen!" -ForegroundColor Green
        } else {
            Write-Host "✗ Přihlášení se nezdařilo" -ForegroundColor Red
            Write-Host "  Zkus to znovu: kiro-cli login" -ForegroundColor Yellow
            exit 1
        }
    } else {
        Write-Host ""
        Write-Host "Bez přihlášení nemůže CODEfender fungovat." -ForegroundColor Red
        Write-Host "Až se přihlásíš, spusť tento skript znovu." -ForegroundColor Yellow
        exit 1
    }
}

# ============================================
# 3. Instalace Python závislostí
# ============================================
Write-Host "[3/5] Instaluji Python závislosti..." -ForegroundColor Yellow

$requirementsPath = Join-Path $RepoRoot "requirements.txt"
if (Test-Path $requirementsPath) {
    try {
        & python -m pip install -q -r $requirementsPath
        Write-Host "✓ Python závislosti nainstalovány" -ForegroundColor Green
    } catch {
        Write-Host "✗ Chyba při instalaci Python závislostí" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✗ requirements.txt nenalezen!" -ForegroundColor Red
    exit 1
}

# ============================================
# 4. Vytvoření zástupce na ploše
# ============================================
Write-Host "[4/5] Vytvářím zástupce na ploše..." -ForegroundColor Yellow

$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "CODEfender.lnk"
$targetPath = "python.exe"
$arguments = "`"$RepoRoot\run.py`""
$workingDir = $RepoRoot

$WScriptShell = New-Object -ComObject WScript.Shell
$shortcut = $WScriptShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetPath
$shortcut.Arguments = $arguments
$shortcut.WorkingDirectory = $workingDir
$shortcut.Description = "CODEfender - AI bezpečnostní analýza kódu"
$shortcut.Save()

Write-Host "✓ Zástupce vytvořen: $shortcutPath" -ForegroundColor Green

# ============================================
# 5. Spuštění aplikace
# ============================================
Write-Host "[5/6] Spouštím CODEfender..." -ForegroundColor Yellow
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Hotovo!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "✓ Zástupce na ploše: CODEfender.lnk" -ForegroundColor Cyan
Write-Host "✓ Dokumentace: README.md" -ForegroundColor Cyan
Write-Host ""
Write-Host "Aplikace se spustí za 2 sekundy..." -ForegroundColor Yellow

Start-Sleep -Seconds 2

# Spuštění aplikace na pozadí
Set-Location $RepoRoot
Start-Process -FilePath "python" -ArgumentList "run.py" -WorkingDirectory $RepoRoot

# Krátké čekání, aby se aplikace spustila
Start-Sleep -Milliseconds 1000

# ============================================
# 6. Přesun README a samosmazání
# ============================================
Write-Host "[6/6] Přesouvám dokumentaci a uklízím..." -ForegroundColor Yellow

$readmePath = Join-Path $PSScriptRoot "README.md"
$docsPath = Join-Path $RepoRoot "docs"
$targetReadme = Join-Path $docsPath "FIRST-START.md"

# Přesunout README do docs
if (Test-Path $readmePath) {
    try {
        Copy-Item -Path $readmePath -Destination $targetReadme -Force
        Write-Host "✓ README přesunut do docs/FIRST-START.md" -ForegroundColor Green
    } catch {
        Write-Host "⚠ Nepodařilo se přesunout README" -ForegroundColor Yellow
    }
}

# Vytvořit dočasný skript pro smazání FIRST-START složky
$tempScript = Join-Path $env:TEMP "codefender_cleanup.ps1"
@"
Start-Sleep -Seconds 2
Remove-Item -Path '$PSScriptRoot' -Recurse -Force -ErrorAction SilentlyContinue
"@ | Out-File -FilePath $tempScript -Encoding UTF8

# Spustit cleanup na pozadí
Start-Process -FilePath "powershell" -ArgumentList "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$tempScript`"" -WindowStyle Hidden

Write-Host "✓ Instalační složka FIRST-START bude odstraněna" -ForegroundColor Green
Write-Host ""
Write-Host "Instalace dokončena! Aplikace běží." -ForegroundColor Green
Write-Host ""
