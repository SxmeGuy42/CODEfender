# 🛡️ CODEfender

AI agent pro bezpečnostní analýzu kódu – detekuje SQL injection, XSS, command injection, buffer overflow a další zranitelnosti.

---

## 🚀 Rychlý start

### První spuštění

```powershell
cd FIRST-START
.\setup-and-run.ps1
```

**nebo** dvakrát klikni na `FIRST-START/SPUSTIT.bat`

Skript automaticky:
- ✅ Nainstaluje Kiro CLI (pokud chybí)
- ✅ Provede přihlášení do Kiro
- ✅ Nainstaluje Python závislosti
- ✅ Vytvoří zástupce na ploše
- ✅ Spustí aplikaci
- ✅ Smaže se po dokončení

**Další spuštění:** Použij zástupce `CODEfender.lnk` na ploše nebo `python run.py`

**Detaily:** Viz `FIRST-START/README.md`

---

## 📋 Požadavky

- **Python 3.11+**
- **Kiro účet** – https://kiro.dev/ (registrace zdarma)
- **Kiro CLI** – instaluje se automaticky
- **Node.js** – volitelné, pro ESLint (JavaScript analýza)

---

## 🎯 Co detekuje?

| Jazyk | Zranitelnosti |
|-------|---------------|
| **Python** | SQL injection, command injection, slabé hashování hesel, hardcoded secrets |
| **PHP** | SQL injection, XSS, RCE, file inclusion, type juggling |
| **JavaScript/TS** | XSS, NoSQL injection, prototype pollution, ReDoS |
| **C/C++** | Buffer overflow, use-after-free, memory leaks, null pointer dereference |
| **SQL** | SQL injection, nadměrná oprávnění, blind injection |

---

## 🏗️ Jak to funguje?

```
Desktopová aplikace (PySide6)
    ↓ spustí subprocess
Kiro CLI agent
    ↓ komunikace přes JSON-RPC 2.0
LLM model (Claude/GPT/Ollama)
    ↓ volá tools
SAST nástroje (bandit, semgrep, eslint, cppcheck)
```

**Agent je řízen steering files** (`.kiro/steering/*.md`) – editovatelná pravidla v češtině:
- `behaviour-persona.md` – tón komunikace, zásady
- `workflow-postup.md` – 6 kroků analýzy
- `vulnerabilities-db.md` – katalog CWE pro každý jazyk
- `output-format.md` – přesná struktura reportu

---

## 🧪 Testování

Projekt obsahuje testovací soubory pro ověření funkčnosti:

**Zranitelné kódy** (agent by měl najít chyby):
- `codefender/test_cases/vulnerable/python/sql_injection_01.py`
- `codefender/test_cases/vulnerable/php/xss_01.php`
- `codefender/test_cases/vulnerable/javascript/nosql_injection_01.js`
- `codefender/test_cases/vulnerable/cpp/buffer_overflow_01.cpp`

**Bezpečné kódy** (kontrola false positive):
- `codefender/test_cases/clean/python/secure_db_01.py`
- `codefender/test_cases/clean/php/secure_output_01.php`
- `codefender/test_cases/clean/javascript/secure_dom_01.js`

---

## 📚 Dokumentace

- **[FIRST-START/README.md](FIRST-START/README.md)** – průvodce prvním spuštěním, Kiro účet
- **[docs/PROJECT-STRUCTURE.md](docs/PROJECT-STRUCTURE.md)** – struktura projektu, tok dat
- **[docs/ACP-COMMUNICATION.md](docs/ACP-COMMUNICATION.md)** – jak funguje propojení s Kiro CLI

---

## ⚙️ Ovládání aplikace

### Přiložení kódu (4 způsoby)
1. **Vložit text** – Ctrl+V do vstupního pole
2. **Přiložit soubor** – tlačítko `PŘILOŽIT SOUBORY` → vyber soubor(y)
3. **Přiložit složku** – tlačítko `PŘILOŽIT SOUBORY` → vyber složku (rekurzivně načte .py, .php, .js, .cpp, .sql)
4. **Drag & drop** – přetáhni soubor/složku myší do okna

### Klávesové zkratky
- `Enter` – odeslat analýzu
- `Shift+Enter` – nový řádek
- `Ctrl+V` – vložit kód

### Tlačítka
- `ANALYZOVAT` – spustit analýzu
- `PŘERUŠIT` – zastavit probíhající analýzu
- `KOPÍROVAT` – zkopírovat poslední odpověď do schránky
- `EXPORT` – uložit celou konverzaci do .txt/.md souboru

### Přizpůsobení (⚙ ikona)
- **Barva CRT** – 4 palety (fosforová zelená, amber, ledová modrá, vintage bílá)
- **Velikost písma** – 10-22 px
- **Síla zakřivení** – 0-100 % (vignette efekt)

---

## 🔧 Pokročilé

### Úprava chování agenta
Edituj soubory v `.kiro/steering/`:
- Změň tón komunikace → `behaviour-persona.md`
- Přidej nový typ zranitelnosti → `vulnerabilities-db.md`
- Uprav formát výstupu → `output-format.md`

### Ruční instalace
```powershell
# Kiro CLI
irm 'https://cli.kiro.dev/install.ps1' | iex
kiro-cli login

# Python závislosti
pip install -r requirements.txt

# Node.js závislosti (volitelné)
npm install

# Spuštění
python run.py
```

### Časté problémy

**❌ `Kiro CLI není přihlášené`**
```powershell
kiro-cli login
kiro-cli whoami  # ověření
```

**❌ `Seznam modelů je prázdný`**
- Přihlášení do Kiro se nezdařilo
- Zkus: `kiro-cli login` znovu

**❌ `Chyba při analýze: Internal error`**
- Zkontroluj log: `%TEMP%\kiro-log\logs\kiro-chat.log`
- Hledej `NoToken` → problém s přihlášením

---

## 📝 Struktura projektu

```
CODEfender/
├── .kiro/                    # Konfigurace agenta
│   ├── agents/codefender.json
│   └── steering/*.md
├── codefender/               # Zdrojový kód
│   ├── app.py                # GUI
│   ├── acp_client.py         # Komunikace s Kiro CLI
│   ├── ui_theme.py           # 4 barevné palety
│   ├── crt_overlay.py        # CRT efekty
│   └── test_cases/           # Testovací soubory
├── FIRST-START/              # První spuštění
├── docs/                     # Dokumentace
├── scripts/                  # Instalační skripty
├── run.py                    # Spouštěč
├── requirements.txt          # Python závislosti
└── package.json              # Node.js závislosti
```

---

## 📝 Licence

Akademický prototyp vytvořený pro dlouhodobou práci.

---

## 🔗 Odkazy

- **Kiro CLI:** https://cli.kiro.dev/
- **Kiro registrace:** https://kiro.dev/
- **Agent Client Protocol:** Otevřený standard (Zed editor)
