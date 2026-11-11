# 🚀 První spuštění CODEfender

Vítej v CODEfenderu – AI agentovi pro bezpečnostní analýzu kódu.

---

## ⚠️ Než začneš

CODEfender vyžaduje **Kiro účet** pro přístup k AI modelům.

### 1. Vytvoř si Kiro účet

Pokud ještě nemáš Kiro účet:
1. Jdi na **https://kiro.dev/**
2. Zaregistruj se (e-mail + heslo)
3. Potvrd e-mail

### 2. Přihlaš se do Kiro CLI

Po instalaci Kiro CLI (automaticky proběhne):
```powershell
kiro-cli login
```

Otevře se prohlížeč → přihlaš se svým Kiro účtem.

**Ověření přihlášení:**
```powershell
kiro-cli whoami
```

Mělo by vypsat tvůj Kiro účet. Pokud vidíš `Not logged in`, zkus přihlášení znovu.

---

## 🚀 Rychlý start

### 1️⃣ Instalace a spuštění

Dvakrát klikni na:
```
SPUSTIT.bat
```

**nebo** spusť v PowerShellu:

```powershell
.\setup-and-run.ps1
```

Tento skript automaticky:
- ✅ Zkontroluje Python
- ✅ **Nainstaluje Kiro CLI** (pokud chybí)
- ✅ **Provede přihlášení do Kiro** (interaktivně)
- ✅ Nainstaluje Python závislosti
- ✅ Vytvoří zástupce na ploše
- ✅ Spustí aplikaci
- ✅ Automaticky se smaže po dokončení

**Další spuštění:** Použij zástupce `CODEfender.lnk` na ploše

---

### 2️⃣ Co je potřeba předem

| Požadavek | Kontrola | Poznámka |
|-----------|----------|----------|
| **Python 3.11+** | `python --version` | Nutné |
| **Kiro účet** | https://kiro.dev/ | **Nutné** – registrace zdarma |
| **Kiro CLI** | `kiro-cli --version` | Instaluje se automaticky |
| **Přihlášení** | `kiro-cli whoami` | Skript se zeptá |

---

## 🔐 Proč potřebuji Kiro účet?

CODEfender používá AI modely (Claude, GPT) přes **Kiro CLI**.

- ✅ **Žádné API klíče** – aplikace nespravuje žádné tokeny
- ✅ **Bezpečné** – přihlášení přes OAuth v prohlížeči
- ✅ **Zdarma start** – Kiro nabízí free tier pro testování

**Alternativa:** Pokud chceš použít vlastní API klíče, musíš upravit kód (není v scope tohoto projektu).

---

## 📚 Detailní dokumentace

Po instalaci najdeš kompletní návody:

- **[../README.md](../README.md)** – kompletní návod k použití a ovládání
- **[PROJECT-STRUCTURE.md](../docs/PROJECT-STRUCTURE.md)** – struktura projektu, tok dat
- **[ACP-COMMUNICATION.md](../docs/ACP-COMMUNICATION.md)** – jak funguje propojení s Kiro CLI

---

## ❓ Časté problémy

### ❌ `Nejsi přihlášený do Kiro`

```powershell
kiro-cli login
```

Otevře se prohlížeč → přihlaš se. Pak ověř:

```powershell
kiro-cli whoami
```

### ❌ `Nemám Kiro účet`

Registruj se zdarma na: **https://kiro.dev/**

### ❌ `kiro-cli není rozpoznán jako příkaz`

Kiro CLI se možná nenainstaloval správně. Zkus ručně:

```powershell
irm 'https://cli.kiro.dev/install.ps1' | iex
```

Po instalaci **restartuj PowerShell** a zkus znovu.

### ❌ `Chybí PySide6`

```powershell
pip install -r ../requirements.txt
```

### ❌ `Aplikace nenajde kiro-cli`

Zkontroluj, že je v PATH:

```powershell
$env:PATH -split ';' | Select-String kiro
```

---

## 🎯 Co dělá CODEfender?

CODEfender analyzuje kód a hledá:
- 🔴 **SQL Injection** (Python, PHP, SQL)
- 🔴 **Command Injection** (Python, PHP)
- 🔴 **XSS** (JavaScript, PHP)
- 🔴 **Buffer Overflow** (C++)
- 🟠 **Slabé hashování hesel**
- 🟠 **Hardcoded secrets**
- 🟡 **Zastaralé závislosti**

Agent je řízen steering files v `.kiro/steering/` – můžeš upravit jeho chování editací těchto souborů.

---

*Po úspěšné instalaci a spuštění bude tento dokument přesunut do `docs/FIRST-START.md` a instalační složka bude automaticky odstraněna.*
