"""
ACP klient - transportní vrstva mezi GUI a Kiro agentem.

Spustí `kiro-cli acp --agent codefender` jako podproces a komunikuje s ním
JSON-RPC 2.0 (newline-delimited) přes stdin/stdout. Logika analýzy je na
straně Kira (řídí ji steering files v .kiro/steering/), tady je jen roura.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

# ─────────────────────────────────────────────────────────────
# Konstanty protokolu
# ─────────────────────────────────────────────────────────────

PROTOCOL_VERSION = 1
CLIENT_NAME = "codefender-desktop"
CLIENT_VERSION = "4.0.0"
AGENT_NAME = "codefender"

# kategorie config option, kterou ACP používá pro výběr modelu
MODEL_CATEGORY = "model"


class AcpError(RuntimeError):
    """Chyba v komunikaci s ACP agentem."""


class KiroCliNotFoundError(AcpError):
    """kiro-cli není nainstalován nebo nebyl nalezen."""


# ─────────────────────────────────────────────────────────────
# Datové struktury
# ─────────────────────────────────────────────────────────────


@dataclass
class ModelOption:
    """Jeden model, který agent nabízí."""

    id: str
    name: str
    description: str = ""


@dataclass
class ModelSelector:
    """Config option kategorie `model` - seznam voleb + aktuální hodnota."""

    option_id: str
    label: str
    current_value: str
    options: list[ModelOption] = field(default_factory=list)


@dataclass
class PermissionOption:
    """Volba, kterou agent nabídne při žádosti o povolení nástroje."""

    option_id: str
    name: str
    kind: str = ""


# ─────────────────────────────────────────────────────────────
# Hledání kiro-cli
# ─────────────────────────────────────────────────────────────


def find_kiro_cli() -> str | None:
    """
    Najde spustitelný `kiro-cli`.

    Nejdřív PATH, pak obvyklé instalační cesty - IDE spuštěné mimo shell
    nemusí mít PATH nastavené.
    """
    found = shutil.which("kiro-cli")
    if found:
        return found

    local_app = os.environ.get("LOCALAPPDATA", "")
    home = Path.home()

    candidates = [
        home / ".local" / "bin" / "kiro-cli.exe",
        home / ".local" / "bin" / "kiro-cli",
        home / ".kiro" / "bin" / "kiro-cli.exe",
        Path(local_app) / "Programs" / "kiro-cli" / "kiro-cli.exe" if local_app else None,
        Path(local_app) / "kiro-cli" / "kiro-cli.exe" if local_app else None,
        Path(local_app) / "Programs" / "Kiro" / "bin" / "kiro-cli.exe" if local_app else None,
    ]

    for candidate in candidates:
        if candidate and candidate.is_file():
            return str(candidate)

    return None


INSTALL_HINT = (
    "kiro-cli nebyl nalezen.\n\n"
    "CODEfender používá jako agenta Kiro, které běží přes `kiro-cli acp`.\n"
    "Nainstaluj Kiro CLI (Windows 11, PowerShell):\n\n"
    "    irm 'https://cli.kiro.dev/install.ps1' | iex\n\n"
    "Po instalaci se přihlas příkazem `kiro-cli login` a aplikaci spusť znovu."
)

LOGIN_HINT = (
    "kiro-cli není přihlášený, takže agent nemůže volat model.\n\n"
    "Přihlas se v terminálu:\n\n"
    "    kiro-cli login\n\n"
    "Přihlášení otevře prohlížeč. Po dokončení spusť aplikaci znovu.\n"
    "Stav přihlášení zkontroluješ příkazem `kiro-cli whoami`."
)


def check_login(cli_path: str | None) -> tuple[bool, str]:
    """
    Ověří přihlášení přes `kiro-cli whoami`.

    Bez přihlášení agent selže na volání modelu - lepší to zjistit hned.
    Vrací (přihlášen, popis).
    """
    if not cli_path:
        return False, "kiro-cli nenalezen"

    creationflags = 0
    if sys.platform == "win32":
        # potlač black console window u GUI aplikace
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        result = subprocess.run(
            [cli_path, "whoami"],
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
    except Exception as exc:  # noqa: BLE001 - diagnostika, nesmí shodit app
        return False, f"whoami selhalo: {exc}"

    detail = (result.stdout or result.stderr or "").strip()
    return result.returncode == 0, detail or "bez výstupu"


# ─────────────────────────────────────────────────────────────
# ACP klient
# ─────────────────────────────────────────────────────────────


class AcpClient:
    """
    Klient Kiro ACP agenta.

    Callbacky se volají z reader threadu - GUI si je musí přehodit do svého
    vlákna (v PySide6 přes signály, viz AcpBridge v app.py).
    """

    def __init__(
        self,
        workspace: Path,
        agent: str | None = AGENT_NAME,
        cli_path: str | None = None,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.agent = agent
        self.cli_path = cli_path or find_kiro_cli()

        self._proc: subprocess.Popen[str] | None = None
        self._reader: threading.Thread | None = None
        self._stderr_reader: threading.Thread | None = None
        self._write_lock = threading.Lock()

        # JSON-RPC request bookkeeping - id → event/výsledek/chyba
        self._next_id = 0
        self._id_lock = threading.Lock()
        self._pending: dict[int, threading.Event] = {}
        self._results: dict[int, Any] = {}
        self._errors: dict[int, dict[str, Any]] = {}

        self.session_id: str | None = None
        self.model_selector: ModelSelector | None = None
        # fallback pole `models` u starších/Kiro-specifických odpovědí
        self._legacy_models: list[ModelOption] = []
        self._legacy_current_model: str | None = None
        self.agent_info: dict[str, Any] = {}
        self.auth_methods: list[dict[str, Any]] = []
        self.prompt_capabilities: dict[str, Any] = {}
        self._stderr_tail: list[str] = []

        # callbacky - nastavuje si GUI
        self.on_text: Callable[[str], None] = lambda _text: None
        self.on_tool_call: Callable[[str, str], None] = lambda _name, _status: None
        self.on_turn_end: Callable[[str], None] = lambda _reason: None
        self.on_permission_request: Callable[[int, str, list[PermissionOption]], None] = (
            lambda _rid, _tool, _opts: None
        )
        self.on_models_changed: Callable[[], None] = lambda: None
        self.on_log: Callable[[str], None] = lambda _msg: None
        self.on_credits_changed: Callable[[], None] = lambda: None

        # Kumulativní spotřeba kreditů za session. Kiro-cli 2.16.2 nemá
        # žádný dotaz na zbývající zůstatek (whoami/profile ho nevrací a
        # ACP nemá "balance" metodu) - jediné dostupné číslo je spotřeba
        # za jednotlivý tah v notifikaci _kiro.dev/metadata. Sčítáme.
        self.session_credits_used: float = 0.0
        self.credit_unit: str = "credits"

    # ── životní cyklus ────────────────────────────────────────

    def start(self) -> None:
        """Nastartuje `kiro-cli acp` jako podproces."""
        if not self.cli_path:
            raise KiroCliNotFoundError(INSTALL_HINT)

        cmd = [self.cli_path, "acp"]
        if self.agent:
            cmd += ["--agent", self.agent]

        creationflags = 0
        if sys.platform == "win32":
            # bez tohohle vyskočí konzolové okno vedle GUI
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.workspace),
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=creationflags,
            )
        except FileNotFoundError as exc:
            raise KiroCliNotFoundError(INSTALL_HINT) from exc

        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self._stderr_reader = threading.Thread(target=self._read_stderr, daemon=True)
        self._stderr_reader.start()

    def stop(self) -> None:
        """Ukončí podproces (best effort)."""
        proc = self._proc
        self._proc = None
        if not proc:
            return
        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:
            pass
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            # když se nechce ukončit sám, zabij
            try:
                proc.kill()
            except Exception:
                pass

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    # ── JSON-RPC vrstva ───────────────────────────────────────

    def _send(self, payload: dict[str, Any]) -> None:
        proc = self._proc
        if not proc or not proc.stdin:
            raise AcpError("ACP proces neběží.")
        line = json.dumps(payload, ensure_ascii=False) + "\n"
        with self._write_lock:
            try:
                proc.stdin.write(line)
                proc.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise AcpError(f"Spojení s kiro-cli bylo přerušeno: {exc}") from exc

    def _request(self, method: str, params: dict[str, Any] | None = None, timeout: float = 300.0) -> Any:
        """Pošle request, počká na odpověď stejným id."""
        with self._id_lock:
            request_id = self._next_id
            self._next_id += 1

        event = threading.Event()
        self._pending[request_id] = event

        self._send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            }
        )

        if not event.wait(timeout):
            self._pending.pop(request_id, None)
            raise AcpError(f"Timeout při čekání na odpověď na '{method}' ({timeout:.0f}s).")

        self._pending.pop(request_id, None)

        if request_id in self._errors:
            err = self._errors.pop(request_id)
            raise AcpError(f"{method} selhalo: {err.get('message', err)}")

        return self._results.pop(request_id, None)

    def _notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def _respond(self, request_id: Any, result: dict[str, Any]) -> None:
        self._send({"jsonrpc": "2.0", "id": request_id, "result": result})

    def _respond_error(self, request_id: Any, code: int, message: str) -> None:
        self._send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": code, "message": message},
            }
        )

    # ── čtecí smyčky ──────────────────────────────────────────

    def _read_loop(self) -> None:
        """Čte stdout, parsuje JSON-RPC zprávy, dispatchuje je."""
        proc = self._proc
        if not proc or not proc.stdout:
            return
        try:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    # občas kiro-cli vypíše ne-JSON řádek (log, welcome...)
                    self.on_log(f"[acp] nečitelný řádek: {line[:200]}")
                    continue
                try:
                    self._dispatch(msg)
                except Exception as exc:
                    self.on_log(f"[acp] chyba při zpracování zprávy: {exc}")
        except Exception as exc:
            self.on_log(f"[acp] čtení stdout skončilo: {exc}")
        finally:
            # když padne kiro-cli, probud všechny čekající requesty ať GUI netuhne
            for rid, event in list(self._pending.items()):
                self._errors[rid] = {"message": "kiro-cli ukončil spojení."}
                event.set()

    def _read_stderr(self) -> None:
        """Sbírá stderr do ring bufferu pro diagnostiku."""
        proc = self._proc
        if not proc or not proc.stderr:
            return
        try:
            for line in proc.stderr:
                line = line.rstrip()
                if not line:
                    continue
                self._stderr_tail.append(line)
                # drž jen posledních 40 řádků
                del self._stderr_tail[:-40]
                self.on_log(f"[kiro-cli] {line}")
        except Exception:
            pass

    def stderr_tail(self) -> str:
        return "\n".join(self._stderr_tail[-15:])

    def _dispatch(self, msg: dict[str, Any]) -> None:
        # odpověď na náš request (má id + result/error)
        if "id" in msg and ("result" in msg or "error" in msg):
            rid = msg["id"]
            if isinstance(rid, int) and rid in self._pending:
                if "error" in msg:
                    self._errors[rid] = msg["error"] or {}
                else:
                    self._results[rid] = msg.get("result")
                self._pending[rid].set()
            return

        method = msg.get("method")

        # request od agenta - musíme odpovědět
        if "id" in msg and method:
            self._handle_agent_request(msg["id"], method, msg.get("params") or {})
            return

        # notifikace od agenta - jen si ji zpracujeme
        if method:
            self._handle_agent_notification(method, msg.get("params") or {})

    # ── obsluha požadavků agenta ──────────────────────────────

    def _handle_agent_request(self, request_id: Any, method: str, params: dict[str, Any]) -> None:
        if method == "fs/read_text_file":
            self._handle_read_text_file(request_id, params)

        elif method == "fs/write_text_file":
            # zápis je záměrně zakázaný - CODEfender do souborů nezasahuje
            self._respond_error(request_id, -32601, "Zápis do souborů není povolen.")

        elif method == "session/request_permission":
            options = [
                PermissionOption(
                    option_id=opt.get("optionId", ""),
                    name=opt.get("name", ""),
                    kind=opt.get("kind", ""),
                )
                for opt in params.get("options", [])
            ]
            tool_call = params.get("toolCall") or {}
            tool_name = tool_call.get("title") or tool_call.get("rawInput", {}).get("command") or "neznámý nástroj"
            self.on_permission_request(request_id, str(tool_name), options)

        else:
            self._respond_error(request_id, -32601, f"Metoda '{method}' není podporovaná.")

    def _handle_read_text_file(self, request_id: Any, params: dict[str, Any]) -> None:
        raw_path = params.get("path", "")
        try:
            path = Path(raw_path)
            if not path.is_absolute():
                path = self.workspace / path
            text = path.read_text(encoding="utf-8", errors="replace")
            # volitelný slice řádků (line + limit)
            line = params.get("line")
            limit = params.get("limit")
            if line is not None or limit is not None:
                lines = text.splitlines(keepends=True)
                start = max(0, int(line) - 1) if line else 0
                end = start + int(limit) if limit else len(lines)
                text = "".join(lines[start:end])
            self._respond(request_id, {"content": text})
        except Exception as exc:
            self._respond_error(request_id, -32000, f"Nelze přečíst '{raw_path}': {exc}")

    def respond_permission(self, request_id: Any, option_id: str | None) -> None:
        """Odpověď na žádost o povolení. None = zamítnuto/zrušeno."""
        if option_id:
            outcome = {"outcome": "selected", "optionId": option_id}
        else:
            outcome = {"outcome": "cancelled"}
        self._respond(request_id, {"outcome": outcome})

    # ── obsluha notifikací agenta ─────────────────────────────

    def _handle_agent_notification(self, method: str, params: dict[str, Any]) -> None:
        if method == "_kiro.dev/metadata":
            self._handle_kiro_metadata(params)
            return

        if method not in ("session/update", "session/notification"):
            return

        update = params.get("update") or params
        kind = update.get("sessionUpdate") or update.get("type") or ""

        if kind in ("agent_message_chunk", "AgentMessageChunk"):
            # streamovaný text z agenta - pošli ho do GUI
            self.on_text(_content_to_text(update.get("content")))

        elif kind in ("agent_thought_chunk", "AgentThoughtChunk"):
            # vnitřní úvahy agenta zahodíme (steering to zakazuje do reportu)
            pass

        elif kind in ("tool_call", "ToolCall", "tool_call_update", "ToolCallUpdate"):
            title = update.get("title") or update.get("kind") or "nástroj"
            status = update.get("status", "")
            self.on_tool_call(str(title), str(status))

        elif kind in ("config_option_update", "ConfigOptionUpdate"):
            self._parse_config_options(update.get("configOptions") or [])
            self.on_models_changed()

        elif kind in ("turn_end", "TurnEnd"):
            self.on_turn_end(str(update.get("stopReason", "end_turn")))

    def _handle_kiro_metadata(self, params: dict[str, Any]) -> None:
        """
        Kiro-specifická notifikace `_kiro.dev/metadata`.

        Nese `meteringUsage` s cenou jen za PROBĚHLÝ tah (zbývající
        kredity API nedává), takže hodnoty pouze sčítáme.
        """
        usage = params.get("meteringUsage")
        if not usage:
            return
        changed = False
        for entry in usage:
            if entry.get("unit") == "credit":
                self.session_credits_used += float(entry.get("value", 0.0))
                self.credit_unit = entry.get("unitPlural", "credits")
                changed = True
        if changed:
            self.on_credits_changed()

    # ── ACP metody ────────────────────────────────────────────

    def initialize(self) -> dict[str, Any]:
        result = self._request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "clientCapabilities": {
                    "fs": {
                        "readTextFile": True,
                        # zápis nepovolujeme ani na úrovni protokolu
                        "writeTextFile": False,
                    },
                    "terminal": False,
                    "session": {"configOptions": {"boolean": {}}},
                },
                "clientInfo": {"name": CLIENT_NAME, "version": CLIENT_VERSION},
            },
            timeout=60,
        ) or {}
        self.agent_info = result.get("agentInfo") or {}
        self.auth_methods = result.get("authMethods") or []
        self.prompt_capabilities = (
            (result.get("agentCapabilities") or {}).get("promptCapabilities") or {}
        )
        return result

    def supports_embedded_context(self) -> bool:
        """Umí agent přijmout `resource` block s vloženým obsahem souboru?"""
        return bool(self.prompt_capabilities.get("embeddedContext"))

    def new_session(self) -> str:
        result = self._request(
            "session/new",
            {"cwd": str(self.workspace), "mcpServers": []},
            timeout=120,
        ) or {}

        session_id = result.get("sessionId")
        if not session_id:
            raise AcpError("Agent nevrátil sessionId.")
        self.session_id = session_id

        # standardní i legacy formát seznamu modelů - zkusíme oba
        self._parse_config_options(result.get("configOptions") or [])
        self._parse_legacy_models(result.get("models"))

        return session_id

    def _parse_config_options(self, config_options: list[dict[str, Any]]) -> None:
        for option in config_options:
            if option.get("category") != MODEL_CATEGORY:
                continue
            if option.get("type") not in (None, "select"):
                continue
            values = [
                ModelOption(
                    id=str(value.get("id", "")),
                    name=str(value.get("name", value.get("id", ""))),
                    description=str(value.get("description", "") or ""),
                )
                for value in option.get("options") or []
            ]
            self.model_selector = ModelSelector(
                option_id=str(option.get("id", "")),
                label=str(option.get("name", "Model")),
                current_value=str(option.get("currentValue", "")),
                options=values,
            )
            return

    def _parse_legacy_models(self, models: Any) -> None:
        # starší/Kiro-specifický formát: pole `models` mimo configOptions
        if not isinstance(models, dict):
            return
        available = models.get("availableModels") or models.get("models") or []
        self._legacy_models = [
            ModelOption(
                id=str(m.get("modelId") or m.get("id", "")),
                name=str(m.get("name") or m.get("modelId") or m.get("id", "")),
                description=str(m.get("description", "") or ""),
            )
            for m in available
            if isinstance(m, dict)
        ]
        current = models.get("currentModelId") or models.get("currentModel")
        self._legacy_current_model = str(current) if current else None

    # ── modely ────────────────────────────────────────────────

    def available_models(self) -> list[ModelOption]:
        if self.model_selector:
            return list(self.model_selector.options)
        return list(self._legacy_models)

    def current_model(self) -> str | None:
        if self.model_selector:
            return self.model_selector.current_value or None
        return self._legacy_current_model

    def supports_model_switching(self) -> bool:
        return bool(self.available_models())

    def set_model(self, model_id: str) -> None:
        """
        Přepne model. Nejdřív standardní `set_config_option`, jinak fallback
        na legacy `session/set_model`.
        """
        if not self.session_id:
            raise AcpError("Session není vytvořená.")

        if self.model_selector:
            result = self._request(
                "session/set_config_option",
                {
                    "sessionId": self.session_id,
                    "optionId": self.model_selector.option_id,
                    "value": model_id,
                },
                timeout=60,
            ) or {}
            options = result.get("configOptions")
            if options:
                self._parse_config_options(options)
            else:
                self.model_selector.current_value = model_id
            return

        # fallback - starší API bez configOptions
        self._request(
            "session/set_model",
            {"sessionId": self.session_id, "modelId": model_id},
            timeout=60,
        )
        self._legacy_current_model = model_id

    # ── prompt ────────────────────────────────────────────────

    def prompt(self, blocks: list[dict[str, Any]], timeout: float = 900.0) -> str:
        """
        Pošle vstup agentovi, blokuje do konce tahu.

        Text agenta se streamuje průběžně přes `on_text`. Vrací stop reason
        (end_turn / cancelled / refusal / max_tokens).
        """
        if not self.session_id:
            raise AcpError("Session není vytvořená.")

        result = self._request(
            "session/prompt",
            # klíč `prompt` (ne `content`) - ACP v1, ověřeno proti kiro-cli 2.16.2
            {"sessionId": self.session_id, "prompt": blocks},
            timeout=timeout,
        ) or {}
        return str(result.get("stopReason", "end_turn"))

    def cancel(self) -> None:
        if self.session_id:
            self._notify("session/cancel", {"sessionId": self.session_id})


# ─────────────────────────────────────────────────────────────
# Pomocné funkce
# ─────────────────────────────────────────────────────────────


def _content_to_text(content: Any) -> str:
    """Rozbalí text z ContentBlocku (může být string, dict nebo pole)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        if content.get("type") == "text":
            return str(content.get("text", ""))
        if "text" in content:
            return str(content["text"])
        return ""
    if isinstance(content, list):
        return "".join(_content_to_text(item) for item in content)
    return ""


def text_block(text: str) -> dict[str, Any]:
    """ContentBlock s textem."""
    return {"type": "text", "text": text}


def resource_block(path: Path, text: str) -> dict[str, Any]:
    """
    ContentBlock s vloženým obsahem souboru. Posílej jen když agent hlásí
    `promptCapabilities.embeddedContext: true` (kiro-cli 2.16.2 ne).
    """
    return {
        "type": "resource",
        "resource": {
            "uri": path.resolve().as_uri(),
            "mimeType": "text/plain",
            "text": text,
        },
    }
