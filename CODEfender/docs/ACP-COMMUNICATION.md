# 🔄 Propojení CODEfender GUI s Kiro CLI

Stručné vysvětlení, jak aplikace komunikuje s Kiro agentem.

---

## Základní princip

```
Desktopová aplikace (PySide6)
    ↓ spustí subprocess
kiro-cli acp --agent codefender
    ↓ komunikace přes
JSON-RPC 2.0 (stdin/stdout)
    ↓ agent načte
.kiro/agents/codefender.json + steering files
    ↓ volá
LLM model (Claude/GPT/...)
```

---

## Jak to funguje krok za krokem

### 1. Spuštění
Aplikace spustí `kiro-cli` jako subprocess (skrytý na pozadí):
```python
subprocess.Popen([
    "kiro-cli", "acp", "--agent", "codefender"
], stdin=PIPE, stdout=PIPE, stderr=PIPE)
```

### 2. Handshake
Aplikace řekne Kiro, co umí:
- ✅ Umím číst soubory
- ❌ Neumím zapisovat
- ❌ Nemám terminál

### 3. Vytvoření session
Kiro vrátí:
- `sessionId` – ID konverzace
- Seznam dostupných modelů → naplní dropdown v GUI

### 4. Odeslání kódu
Uživatel vloží kód → aplikace pošle JSON zprávu:
```json
{
  "method": "session/prompt",
  "params": {
    "sessionId": "abc-123",
    "prompt": [{"type": "text", "text": "Analyzuj tento kód: ..."}]
  }
}
```

### 5. Streaming odpovědi
Kiro posílá report po malých kouscích (chunks):
```json
{"type": "agent_message_chunk", "text": "*Analyzovaný soubor* [python]\n\n"}
{"type": "agent_message_chunk", "text": "🔴 Kritická ➟ [1]\n"}
{"type": "turn_end", "stopReason": "end_turn"}
```
Každý chunk se hned zobrazí v chatu.

### 6. Tool calls (pokud agent potřebuje SAST nástroj)
Agent: "Chci spustit `bandit`"
- Whitelist v `.kiro/agents/codefender.json` → automaticky povoleno
- Ostatní příkazy → zobrazí se dialog uživateli

---

## Bezpečnost

**Co je zakázáno:**
- Zápis do souborů (`fs/write_text_file`)
- Přístup k terminálu
- Destruktivní příkazy (`rm`, `git push`, `curl`)

**Co je povoleno:**
- Čtení souborů z workspace
- SAST nástroje: `bandit`, `semgrep`, `cppcheck`, `eslint`

---

## Threading

- **Main thread** = GUI (okno, chat, tlačítka)
- **Background thread** = čte zprávy od Kiro CLI
- **Propojení** = Qt signály (thread-safe)

Proč? Protože čtení z `stdout` blokuje → kdyby to bylo v main threadu, GUI by zamrzlo.

---

## Kde jsou logy

- **Kiro CLI:** `%TEMP%\kiro-log\logs\kiro-chat.log`
- **Stderr aplikace:** ring buffer v `AcpClient` (40 řádků)

---

## Soubory

| Soubor | Účel |
|--------|------|
| `codefender/acp_client.py` | Komunikace s Kiro CLI |
| `.kiro/agents/codefender.json` | Konfigurace agenta (nástroje, permissions) |
| `.kiro/steering/*.md` | Pravidla chování agenta |

---

*JSON-RPC komunikace = každá zpráva je jeden řádek JSON. Aplikace posílá příkazy na stdin, Kiro odpovídá na stdout.*
