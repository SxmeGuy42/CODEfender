# 📂 Struktura projektu a tok dat

## Adresářová struktura

```
CODEfender/
├── .kiro/                          # Konfigurace Kiro agenta = jádro CODEfenderu
│   ├── steering/                   #   pravidla řídící agenta (inclusion: always)
│   │   ├── product.md
│   │   ├── tech.md
│   │   ├── structure.md
│   │   ├── behaviour-persona.md
│   │   ├── workflow-postup.md
│   │   ├── vulnerabilities-db.md
│   │   └── output-format.md
│   ├── agents/
│   │   └── codefender.json         #   nástroje, permissions, welcomeMessage
│   └── hooks/                      #   Kiro hooks (volitelné)
│
├── codefender/                     # Desktopová aplikace (jen GUI klient)
│   ├── __init__.py
│   ├── app.py                      #   PySide6 okno, chat, výběr modelu, settings
│   ├── acp_client.py               #   JSON-RPC klient pro kiro-cli acp
│   ├── ui_theme.py                 #   QSS styl + 4 palety (green/amber/blue/white)
│   ├── crt_overlay.py              #   overlay widget (vignette + scan-line efekt)
│   └── test_cases/
│       ├── vulnerable/{python,php,javascript,cpp,sql}/
│       └── clean/{python,php,javascript,cpp,sql}/
│
├── docs/
│   ├── PROJECT-STRUCTURE.md        #   tento soubor
│   ├── ACP-COMMUNICATION.md
│   └── PREHLED-PROJEKTU.txt
│
├── scripts/
│   ├── install.ps1
│   └── run-app.ps1
│
├── results/                        # Výstupy testování (metriky, csv)
│   └── .gitkeep                    #   složka je ignorována v gitu
│
├── run.py
├── requirements.txt
└── package.json
```

---

## Tok dat při analýze

```
 uživatel
    │  napíše kód / přiloží soubor, vybere model
    ▼
┌─────────────────────────────────────────┐
│ codefender/app.py                       │
│  · sestaví ContentBlocky (type: text)   │
│  · vlákno na pozadí, GUI neblokuje      │
└────────────────┬────────────────────────┘
                 │ session/prompt
                 ▼
┌─────────────────────────────────────────┐
│ codefender/acp_client.py                │
│  · JSON-RPC 2.0, newline-delimited      │
│  · stdin/stdout podprocesu              │
└────────────────┬────────────────────────┘
                 │ kiro-cli acp --agent codefender
                 ▼
┌─────────────────────────────────────────┐
│ Kiro agent                              │
│  1. načte .kiro/steering/*.md           │
│  2. identifikuje jazyk (workflow krok 1)│
│  3. mapuje vstupy (krok 2)              │
│  4. kontroluje kategorie (krok 3)       │
│     volitelně SAST přes shell           │
│  5. ověří nálezy (krok 4)               │
│  6. složí report dle output-format.md   │
└────────────────┬────────────────────────┘
                 │ session/update (AgentMessageChunk)
                 ▼
┌─────────────────────────────────────────┐
│ app.py                                  │
│  · streamuje text do chatu (throttle)   │
│  · QTextBrowser.setMarkdown()           │
│    → renderuje tabulku nálezů           │
└────────────────┬────────────────────────┘
                 ▼
             report v okně
```

---

## ACP metody, které klient používá

| Metoda | Kdy | Poznámka |
|--------|-----|----------|
| `initialize` | při startu | vyjednání capabilities, získání `authMethods` |
| `session/new` | po initialize | vrací `sessionId` a seznam modelů |
| `session/prompt` | odeslání vstupu | pole se jmenuje `prompt` (ne `content`) |
| `session/set_config_option` | přepnutí modelu | standardní ACP cesta (`category: model`) |
| `session/set_model` | přepnutí modelu | fallback pro starší kiro-cli (2.x) |
| `session/cancel` | tlačítko PŘERUŠIT | notifikace, bez odpovědi |

### Požadavky, které klient obsluhuje

| Metoda od agenta | Reakce klienta |
|------------------|----------------|
| `fs/read_text_file` | přečte soubor a vrátí obsah |
| `fs/write_text_file` | **odmítne** (zápis není povolen) |
| `session/request_permission` | zobrazí dialog uživateli |

### Notifikace, které klient zpracovává

| `sessionUpdate` | Zpracování |
|-----------------|------------|
| `agent_message_chunk` | přidá text do chatu |
| `agent_thought_chunk` | ignoruje (interní uvažování se v reportu neuvádí) |
| `tool_call` / `tool_call_update` | zobrazí ve stavové liště |
| `config_option_update` | aktualizuje seznam modelů |
| `turn_end` | dokončí zprávu |

---

## Kompatibilita verzí

`acp_client.py` podporuje dvě cesty výběru modelu, protože ACP standard se mění:

- **Novější (standard):** `session/new` vrátí `configOptions` s položkou `category: "model"`; změna přes `session/set_config_option`
- **Starší (kiro-cli 2.x):** `session/new` vrátí `models`; změna přes `session/set_model`

Klient nejdřív zkusí `configOptions`, jinak spadne na legacy variantu. Ověřeno proti **kiro-cli 2.16.2**, které používá legacy cestu.

Podobně `resource` ContentBlock se posílá jen když agent hlásí `promptCapabilities.embeddedContext: true`. kiro-cli 2.16.2 ho nepodporuje, proto se obsah souboru vkládá do textového bloku.

---

## Bezpečnostní hranice

| Vrstva | Omezení |
|--------|---------|
| ACP capabilities | klient neinzeruje `fs.writeTextFile` ani `terminal` |
| Agent permissions | `fs_write` = deny, `shell` = allow jen SAST nástroje |
| Denylist | `rm`, `del`, `Remove-Item`, `sudo`, `curl`, `wget`, `Invoke-WebRequest`, `git push` |
| Nepovolené příkazy | vyžádají potvrzení uživatele dialogem |
| Velikost vstupu | max 1 MB na soubor, jen textový UTF-8 |

Analyzovaný kód se **nespouští** – jde o statickou analýzu.

---

## Uživatelské rozhraní (GUI)

Kromě chatu a přílohy má okno několik doplňkových prvků:

| Prvek | Kde | Účel |
|-------|-----|------|
| Ikona ⚙ | pravý horní roh | otevře popup `Přizpůsobení` (barva CRT, velikost písma 10-22 px, síla vignette 0-100 %) |
| 💳 kredity | vedle status baru | kumulativní spotřeba za session z `_kiro.dev/metadata` |
| `KOPÍROVAT` | tlačítková lišta | poslední odpověď agenta → schránka |
| `EXPORT` | tlačítková lišta | celá konverzace → `.txt` / `.md` s časovým razítkem |
| CRT overlay | přes chat browser | vignette (radial gradient) + scan lines, clip path kopíruje `border-radius` |
| Animovaný spinner | status bar | `[|] [/] [-] [\]` během analýzy, 100 ms interval |
| Drag & drop | celé okno | přetažením souboru/složky se přílohy načtou |

Vzhled řídí `codefender/ui_theme.py` (build_qss/build_chat_css) + `codefender/crt_overlay.py`. Přepnutí tématu za běhu volá `MainWindow.apply_theme()`, přebuduje QSS.
