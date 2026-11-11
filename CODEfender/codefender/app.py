"""
CODEfender - desktopové GUI (PySide6).

Chatovací okno nad Kiro agentem `codefender`. Uživatel napíše/vloží kód
nebo přiloží soubor(y)/složku, vybere model a odešle. Vlastní analýzu
neděláme - řídí ji steering files v .kiro/steering/, tady je jen UI.
"""

from __future__ import annotations

import re
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, QSize, Qt, Signal, QTimer
from PySide6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QGuiApplication,
    QIcon,
    QKeyEvent,
    QPainter,
    QPixmap,
    QResizeEvent,
    QTextBlockFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListView,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QTextBrowser,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from .acp_client import (
    LOGIN_HINT,
    AcpClient,
    AcpError,
    KiroCliNotFoundError,
    PermissionOption,
    check_login,
    resource_block,
    text_block,
)
from .crt_overlay import CRTOverlay
from .ui_theme import (
    DEFAULT_FONT_PX,
    DEFAULT_THEME,
    MAX_FONT_PX,
    MIN_FONT_PX,
    THEMES,
    build_chat_css,
    build_qss,
    role_colors,
)

# ─────────────────────────────────────────────────────────────
# Konstanty
# ─────────────────────────────────────────────────────────────

APP_TITLE = "CODEfender"
WORKSPACE = Path(__file__).resolve().parent.parent
ICON_PATH = WORKSPACE / "assets" / "codefender.ico"

MAX_FILE_BYTES = 1_000_000  # 1 MB - větší soubor nemá smysl cpát do kontextu

CODE_FILE_FILTER = (
    "Kód (*.py *.php *.js *.jsx *.ts *.tsx *.cpp *.cc *.cxx *.c *.h *.hpp *.sql);;"
    "Všechny soubory (*)"
)

# přípony, které při výběru složky rekurzivně nasosáme
CODE_FILE_EXTENSIONS = {
    ".py", ".php", ".js", ".jsx", ".ts", ".tsx",
    ".cpp", ".cc", ".cxx", ".c", ".h", ".hpp", ".sql"
}

# jak často překreslujeme streamovanou odpověď (jinak se GUI zadýchá)
STREAM_THROTTLE_MS = 120

# ASCII spinner - retro animovaný loader v status baru během analýzy
SPINNER_FRAMES = ("[|]", "[/]", "[-]", "[\\]")
SPINNER_INTERVAL_MS = 100

# vignette (zakřivení skla CRT) - síla 0-100 % v UI, mapuje se na 0-255 alpha
DEFAULT_VIGNETTE_PCT = 50

# setMarkdown() přidává na každý <p> inline margin 6px nahoře i dole. Na
# 13px monofontu to prakticky splývá s žádnou mezerou a CSS to nepřebije
# (inline styl má přednost). Musíme block formaty přepsat programově
# přes QTextCursor až po vykreslení - viz _widen_paragraph_spacing.
PARAGRAPH_SPACING_PX = 14

_LIST_ITEM_RE = re.compile(r"^\s*([-*+]|\d+\.)\s")
_TABLE_ROW_RE = re.compile(r"^\s*\|")


def _normalize_prose_spacing(text: str) -> str:
    """
    Dohodí chybějící prázdné řádky mezi odstavci.

    setMarkdown() bere CommonMark doslova - jedno \\n je jen "soft break"
    a slepí řádky do jednoho odstavce. Model občas produkuje sousední
    řádky bez prázdné mezery a report se vizuálně slepí. Tady se to
    proto dorovná, kromě tabulek, seznamů a code fenců (ty musí zůstat).
    """
    lines = text.split("\n")
    out_lines: list[str] = []
    in_code_fence = False

    for i, line in enumerate(lines):
        out_lines.append(line)

        if line.strip().startswith("```"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue
        if i + 1 >= len(lines):
            continue

        current = line.strip()
        nxt = lines[i + 1].strip()

        if not current or not nxt:
            continue  # už tam prázdný řádek je
        if _TABLE_ROW_RE.match(line) and _TABLE_ROW_RE.match(lines[i + 1]):
            continue  # tabulku nerozbíjej
        if _LIST_ITEM_RE.match(line) and _LIST_ITEM_RE.match(lines[i + 1]):
            continue  # ani seznam

        out_lines.append("")

    return "\n".join(out_lines)


def _widen_paragraph_spacing(browser: QTextBrowser, px: int = PARAGRAPH_SPACING_PX) -> None:
    """
    Zvětší mezeru mezi odstavci po vykreslení markdownu.

    Musí to jít přes QTextCursor - inline margin, který Qt vloží do
    <p>/<li>, přebije jakýkoli CSS. Iteruje jen bloky v root framu,
    takže buňky tabulek zůstanou stejné (mají vlastní frame).
    """
    doc = browser.document()
    root_frame = doc.rootFrame()
    cursor = QTextCursor(doc)
    cursor.movePosition(QTextCursor.MoveOperation.Start)

    while True:
        if cursor.currentFrame() is root_frame:
            block_format = cursor.blockFormat()
            new_format = QTextBlockFormat(block_format)
            new_format.setTopMargin(0)
            new_format.setBottomMargin(px)
            cursor.setBlockFormat(new_format)

        if not cursor.movePosition(QTextCursor.MoveOperation.NextBlock):
            break


# ─────────────────────────────────────────────────────────────
# Vstupní pole s vlastním zpracováním Enter
# ─────────────────────────────────────────────────────────────


class ChatInput(QPlainTextEdit):
    """
    Chat pole: Enter odesílá, Shift+Enter vloží nový řádek.

    QShortcut(Return) tady nefunguje - QPlainTextEdit zprocesuje Enter už
    ve svém keyPressEvent dřív, než se dostane ke QShortcut. Řeší se to
    přepsáním keyPressEvent.
    """

    submitted = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 - Qt API
        is_enter = event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
        if is_enter and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.submitted.emit()
            event.accept()
            return
        super().keyPressEvent(event)


# ─────────────────────────────────────────────────────────────
# Most mezi ACP vlákny a Qt GUI
# ─────────────────────────────────────────────────────────────


def make_gear_icon(color: str, size: int = 24) -> QIcon:
    """
    Nakreslí ikonu ozubeného kola v dané barvě.

    Nepoužívá Unicode '⚙' záměrně - většina Windows fontů ho renderuje
    jako emoji s pevnou barvou (nedá se přebarvit CSS ani QPalette).
    Programově kreslený tvar barvu respektuje.
    """
    import math

    # kreslíme na 4x supersampled canvas pro hladké zuby, pak scale dolů
    scale = 4
    canvas = QPixmap(size * scale, size * scale)
    canvas.fill(Qt.GlobalColor.transparent)

    p = QPainter(canvas)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))

    s = size * scale
    cx = s / 2
    cy = s / 2
    body_r = s * 0.34         # tělo kola
    tooth_outer = s * 0.48    # špička zubu
    tooth_half_w = s * 0.075  # polovina šířky zubu
    hole_r = s * 0.13         # díra uprostřed
    n_teeth = 8

    # zuby - obdélníky vysunuté z těla kola, otočené kolem středu
    for i in range(n_teeth):
        angle = i * (360.0 / n_teeth)
        p.save()
        p.translate(cx, cy)
        p.rotate(angle)
        # zub jde od těla ven, ne od středu, aby nepřekrýval kolo dvojitě
        p.drawRoundedRect(
            QRectF(-tooth_half_w, -tooth_outer, tooth_half_w * 2, tooth_outer - body_r * 0.85),
            s * 0.015,
            s * 0.015,
        )
        p.restore()

    # tělo kola
    p.drawEllipse(QPointF(cx, cy), body_r, body_r)

    # díra uprostřed - vyřízne se pomocí clear composition
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
    p.drawEllipse(QPointF(cx, cy), hole_r, hole_r)

    p.end()

    # scale dolů se smooth transform - výsledná ikona má měkké okraje
    pixmap = canvas.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    return QIcon(pixmap)


class SettingsDialog(QDialog):
    """
    Popup s přizpůsobením vzhledu - barva CRT a velikost fontu.

    Změny se aplikují live přes signály na MainWindow, takže uživatel
    okamžitě vidí efekt bez potvrzení.
    """

    themeChanged = Signal(str)
    fontSizeChanged = Signal(int)
    vignetteChanged = Signal(int)

    def __init__(
        self,
        current_theme: str,
        current_font_px: int,
        current_vignette_pct: int,
        parent: QWidget,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Přizpůsobení")
        self.setModal(False)
        # bez systémových tlačítek maximalizovat/minimalizovat - jen zavřít
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        form = QFormLayout(self)
        form.setContentsMargins(16, 14, 16, 14)
        form.setSpacing(10)

        # barevná varianta
        self.theme_combo = QComboBox()
        for theme_id, theme in THEMES.items():
            self.theme_combo.addItem(theme.label, theme_id)
        idx = self.theme_combo.findData(current_theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_index)
        form.addRow("Barva CRT:", self.theme_combo)

        # velikost fontu
        self.font_spin = QSpinBox()
        self.font_spin.setRange(MIN_FONT_PX, MAX_FONT_PX)
        self.font_spin.setValue(current_font_px)
        self.font_spin.setSuffix(" px")
        self.font_spin.valueChanged.connect(self.fontSizeChanged.emit)
        form.addRow("Velikost písma:", self.font_spin)

        # intenzita vignette (zakřivení skla CRT) - slider 0-100 %
        # + label vpravo se aktuální hodnotou pro čitelnost
        vignette_row = QHBoxLayout()
        vignette_row.setSpacing(8)
        self.vignette_slider = QSlider(Qt.Orientation.Horizontal)
        self.vignette_slider.setRange(0, 100)
        self.vignette_slider.setValue(current_vignette_pct)
        self.vignette_slider.setMinimumWidth(140)
        self.vignette_value_label = QLabel(f"{current_vignette_pct} %")
        self.vignette_value_label.setMinimumWidth(42)
        self.vignette_slider.valueChanged.connect(self._on_vignette_slider)
        vignette_row.addWidget(self.vignette_slider, stretch=1)
        vignette_row.addWidget(self.vignette_value_label)
        form.addRow("Zakřivení (vignette):", vignette_row)

        # zavřít
        close_button = QPushButton("ZAVŘÍT")
        close_button.setObjectName("SecondaryButton")
        close_button.clicked.connect(self.accept)
        form.addRow(close_button)

    def _on_vignette_slider(self, value: int) -> None:
        self.vignette_value_label.setText(f"{value} %")
        self.vignetteChanged.emit(value)

    def _on_theme_index(self, index: int) -> None:
        if index < 0:
            return
        theme_id = self.theme_combo.itemData(index)
        if theme_id:
            self.themeChanged.emit(theme_id)


class AcpBridge(QObject):
    """Signály - přehazují callbacky z reader threadu ACP klienta do GUI vlákna."""

    textReceived = Signal(str)
    toolCall = Signal(str, str)
    turnEnded = Signal(str)
    permissionRequested = Signal(object, str, object)
    modelsChanged = Signal()
    creditsChanged = Signal()
    logMessage = Signal(str)

    connectResult = Signal(bool, str)
    promptFinished = Signal(bool, str)
    modelApplied = Signal(bool, str)
    authWarning = Signal(str)


# ─────────────────────────────────────────────────────────────
# Hlavní okno
# ─────────────────────────────────────────────────────────────


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(APP_TITLE)
        self.resize(1080, 760)
        self.setMinimumSize(720, 520)
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        self.bridge = AcpBridge()
        self.client = AcpClient(workspace=WORKSPACE)

        self._messages: list[tuple[str, str]] = []
        self._agent_buffer = ""
        self._streaming = False
        self._busy = False
        self._connected = False
        self._attached: list[tuple[Path, str]] = []
        self._suppress_model_signal = False
        self._logged_in = True

        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(STREAM_THROTTLE_MS)
        self._render_timer.timeout.connect(self._render)

        # vzhled - přizpůsobitelné přes Settings dialog
        self._theme_id = DEFAULT_THEME
        self._font_px = DEFAULT_FONT_PX
        self._vignette_pct = DEFAULT_VIGNETTE_PCT
        self._role_colors = role_colors(self._theme_id)
        self._settings_dialog: SettingsDialog | None = None

        # animovaný spinner v status baru během busy stavu
        self._spinner_frame = 0
        self._spinner_status = ""
        self._spinner_timer = QTimer(self)
        self._spinner_timer.setInterval(SPINNER_INTERVAL_MS)
        self._spinner_timer.timeout.connect(self._tick_spinner)

        self._build_ui()
        self._wire_signals()
        self._wire_client_callbacks()

        # drag & drop souborů/složek přímo do okna
        self.setAcceptDrops(True)

        self._set_status("Spouštím Kiro agenta…")
        self._start_connection()

    # ── UI ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("RootPanel")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(10)

        # hlavička okna - title, model dropdown, kredity, status, settings
        header = QHBoxLayout()
        header.setSpacing(12)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel("CODEfender")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Bezpečnostní analýza kódu · agent: Kiro")
        subtitle.setObjectName("SubtitleLabel")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles)

        header.addStretch(1)

        model_label = QLabel("Model:")
        model_label.setObjectName("FieldLabel")
        header.addWidget(model_label)

        self.model_combo = QComboBox()
        self.model_combo.setEnabled(False)
        self.model_combo.setToolTip("Model, kterým agent provede analýzu")
        header.addWidget(self.model_combo)

        self.credits_label = QLabel("")
        self.credits_label.setObjectName("StatusLabel")
        self.credits_label.setToolTip(
            "Spotřebované kredity za tuto session.\n"
            "Kiro CLI neposkytuje zbývající zůstatek, jen spotřebu\n"
            "za jednotlivé odpovědi - tady se to průběžně sčítá."
        )
        self.credits_label.setVisible(False)
        header.addWidget(self.credits_label)

        self.status_label = QLabel("…")
        self.status_label.setObjectName("StatusLabel")
        header.addWidget(self.status_label)

        # settings tlačítko - programově kreslené ozubené kolo v barvě tématu
        self.settings_button = QPushButton()
        self.settings_button.setObjectName("IconButton")
        self.settings_button.setToolTip("Přizpůsobit vzhled (barva, velikost, zakřivení)")
        self.settings_button.setIconSize(QSize(20, 20))
        self.settings_button.setIcon(make_gear_icon(THEMES[self._theme_id].fg))
        header.addWidget(self.settings_button)

        outer.addLayout(header)

        # obrazovka terminálu s CRT efekty (chat s reportem)
        self.screen = QTextBrowser()
        self.screen.setObjectName("Screen")
        self.screen.setOpenExternalLinks(True)
        self.screen.document().setDefaultStyleSheet(
            build_chat_css(self._theme_id, self._font_px)
        )
        outer.addWidget(self.screen, stretch=1)

        # CRT overlay - vignette + scan lines přes celý screen widget.
        # Parent je screen (ne viewport) - jen tak overlay dosáhne na okraje
        # se zaoblenými rohy. Clip path uvnitř overlay ho ořízne podle tvaru.
        # Hodnoty border-width/radius musí souhlasit s QSS v ui_theme.py.
        self.crt_overlay = CRTOverlay(self.screen)
        self.crt_overlay.set_edge_color(THEMES[self._theme_id].screen_edge)
        self.crt_overlay.set_screen_shape(border_width=8, border_radius=26)
        self.crt_overlay.set_vignette_strength(round(self._vignette_pct * 255 / 100))
        self.crt_overlay.raise_()
        self.screen.installEventFilter(self)
        # počáteční geometrie - před prvním paintem
        self._update_overlay_geometry()

        # label s aktuálně přiloženým souborem (nebo počet)
        self.attachment_label = QLabel("")
        self.attachment_label.setObjectName("FieldLabel")
        self.attachment_label.setVisible(False)
        outer.addWidget(self.attachment_label)

        # vstupní pole - Enter posílá, Shift+Enter je nový řádek
        self.input = ChatInput()
        self.input.setObjectName("Input")
        self.input.setPlaceholderText(
            "Napiš nebo vlož kód (Ctrl+V) k analýze…    "
            "[Enter = odeslat text i přílohy, Shift+Enter = nový řádek]"
        )
        self.input.setFixedHeight(140)
        outer.addWidget(self.input)

        # spodní řada tlačítek - přílohy, export/copy, cancel, send
        buttons = QHBoxLayout()
        buttons.setSpacing(10)

        self.attach_button = QPushButton("PŘILOŽIT SOUBORY")
        self.attach_button.setObjectName("SecondaryButton")
        self.attach_button.setToolTip(
            "Přilož jednotlivé soubory nebo celou složku s kódem\n"
            "(taky jde přetáhnout myší přímo do okna)"
        )
        buttons.addWidget(self.attach_button)

        self.clear_attach_button = QPushButton("ODEBRAT PŘÍLOHU")
        self.clear_attach_button.setObjectName("SecondaryButton")
        self.clear_attach_button.setVisible(False)
        buttons.addWidget(self.clear_attach_button)

        self.copy_button = QPushButton("KOPÍROVAT")
        self.copy_button.setObjectName("SecondaryButton")
        self.copy_button.setToolTip("Zkopíruj poslední odpověď agenta do schránky")
        buttons.addWidget(self.copy_button)

        self.export_button = QPushButton("EXPORT")
        self.export_button.setObjectName("SecondaryButton")
        self.export_button.setToolTip("Ulož celý report do textového souboru")
        buttons.addWidget(self.export_button)

        buttons.addStretch(1)

        self.cancel_button = QPushButton("PŘERUŠIT")
        self.cancel_button.setObjectName("SecondaryButton")
        self.cancel_button.setEnabled(False)
        buttons.addWidget(self.cancel_button)

        self.send_button = QPushButton("ANALYZOVAT")
        self.send_button.setEnabled(False)
        buttons.addWidget(self.send_button)

        outer.addLayout(buttons)

        self.setCentralWidget(root)

    def _wire_signals(self) -> None:
        self.send_button.clicked.connect(self._on_send)
        self.attach_button.clicked.connect(self._on_attach)
        self.clear_attach_button.clicked.connect(self._clear_attachment)
        self.copy_button.clicked.connect(self._on_copy)
        self.export_button.clicked.connect(self._on_export)
        self.cancel_button.clicked.connect(self._on_cancel)
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        self.settings_button.clicked.connect(self._open_settings)
        self.input.submitted.connect(self._on_send)

        self.bridge.textReceived.connect(self._on_text)
        self.bridge.toolCall.connect(self._on_tool_call)
        self.bridge.turnEnded.connect(self._on_turn_end)
        self.bridge.permissionRequested.connect(self._on_permission_request)
        self.bridge.modelsChanged.connect(self._refresh_models)
        self.bridge.creditsChanged.connect(self._refresh_credits)
        self.bridge.logMessage.connect(self._on_log)
        self.bridge.connectResult.connect(self._on_connect_result)
        self.bridge.promptFinished.connect(self._on_prompt_finished)
        self.bridge.modelApplied.connect(self._on_model_applied)
        self.bridge.authWarning.connect(self._on_auth_warning)

    def _wire_client_callbacks(self) -> None:
        self.client.on_text = self.bridge.textReceived.emit
        self.client.on_tool_call = self.bridge.toolCall.emit
        self.client.on_turn_end = self.bridge.turnEnded.emit
        self.client.on_permission_request = (
            lambda rid, tool, opts: self.bridge.permissionRequested.emit(rid, tool, opts)
        )
        self.client.on_models_changed = self.bridge.modelsChanged.emit
        self.client.on_credits_changed = self.bridge.creditsChanged.emit
        self.client.on_log = self.bridge.logMessage.emit

    # ── připojení k agentovi ──────────────────────────────────

    def _start_connection(self) -> None:
        def worker() -> None:
            # ověř přihlášení dřív, než uživatel pošle první prompt -
            # jinak by dostal nejasný "Internal error"
            logged_in, detail = check_login(self.client.cli_path)
            if not logged_in and self.client.cli_path:
                self.bridge.authWarning.emit(detail)

            try:
                self.client.start()
                self.client.initialize()
                self.client.new_session()
            except KiroCliNotFoundError as exc:
                self.bridge.connectResult.emit(False, str(exc))
                return
            except AcpError as exc:
                tail = self.client.stderr_tail()
                detail = f"{exc}"
                if tail:
                    detail += f"\n\nVýstup kiro-cli:\n{tail}"
                self.bridge.connectResult.emit(False, detail)
                return
            except Exception as exc:  # noqa: BLE001 - musíme to ukázat uživateli
                self.bridge.connectResult.emit(False, f"Neočekávaná chyba: {exc}")
                return
            self.bridge.connectResult.emit(True, "")

        threading.Thread(target=worker, daemon=True).start()

    def _on_connect_result(self, ok: bool, message: str) -> None:
        if not ok:
            self._set_status("Nepřipojeno")
            self._append("error", f"**Agenta nelze spustit**\n\n```\n{message}\n```")
            self.send_button.setEnabled(False)
            self.input.setEnabled(False)
            self.attach_button.setEnabled(False)
            return

        self._connected = True
        self._set_status(self._idle_status())

        self._refresh_models()
        self._append("system", self._greeting())

        self.send_button.setEnabled(True)
        self.input.setFocus()

    def _on_auth_warning(self, detail: str) -> None:
        self._logged_in = False
        self._append(
            "error",
            f"**Kiro CLI není přihlášené** (`kiro-cli whoami` → {detail})\n\n"
            f"```\n{LOGIN_HINT}\n```",
        )
        self._set_status(self._idle_status())

    def _greeting(self) -> str:
        return (
            "🛡️  **CODEfender** – bezpečnostní analytik kódu\n\n"
            "Analyzuji předložený kód a hledám bezpečnostní slabiny, chyby v kódu "
            "a potenciální rizika. Nálezy seřadím podle závažnosti a ke každému "
            "popíšu způsob opravy.\n\n"
            "Vlož kód do chatu nebo přilož soubor k analýze.\n\n"
            "**Podporované jazyky:** Python, PHP, JavaScript, C++, SQL"
        )

    # ── modely ────────────────────────────────────────────────

    def _refresh_models(self) -> None:
        models = self.client.available_models()
        current = self.client.current_model()

        self._suppress_model_signal = True
        self.model_combo.clear()

        if not models:
            self.model_combo.addItem("výchozí model agenta", None)
            self.model_combo.setEnabled(False)
            self.model_combo.setToolTip(
                "Agent nenabídl seznam modelů – použije se model nastavený v Kiru."
            )
        else:
            for model in models:
                label = model.name or model.id
                self.model_combo.addItem(label, model.id)
                if model.description:
                    self.model_combo.setItemData(
                        self.model_combo.count() - 1,
                        model.description,
                        Qt.ItemDataRole.ToolTipRole,
                    )
            self.model_combo.setEnabled(not self._busy)
            self.model_combo.setToolTip("Model, kterým agent provede analýzu")

            if current:
                index = self.model_combo.findData(current)
                if index >= 0:
                    self.model_combo.setCurrentIndex(index)

        self._suppress_model_signal = False

    def _on_model_changed(self, index: int) -> None:
        if self._suppress_model_signal or index < 0 or not self._connected:
            return
        model_id = self.model_combo.itemData(index)
        if not model_id:
            return

        label = self.model_combo.itemText(index)
        self._set_busy(True, f"Přepínám na {label}…")

        def worker() -> None:
            try:
                self.client.set_model(model_id)
            except AcpError as exc:
                self.bridge.modelApplied.emit(False, str(exc))
                return
            self.bridge.modelApplied.emit(True, label)

        threading.Thread(target=worker, daemon=True).start()

    # ── kredity ───────────────────────────────────────────────

    def _refresh_credits(self) -> None:
        used = self.client.session_credits_used
        unit = self.client.credit_unit
        self.credits_label.setText(f"💳 {used:.2f} {unit}")
        self.credits_label.setVisible(True)

    def _on_model_applied(self, ok: bool, message: str) -> None:
        self._set_busy(False)
        if ok:
            self._append("system", f"Model přepnut na **{message}**.")
        else:
            self._append("error", f"Model se nepodařilo přepnout: {message}")
            self._refresh_models()

    # ── příloha ───────────────────────────────────────────────

    def _on_attach(self) -> None:
        """
        File dialog - vybere jednotlivé soubory NEBO složku.

        Když padne na složku, rekurzivně z ní vytáhne všechny kódové
        soubory (viz CODE_FILE_EXTENSIONS).
        """
        dialog = QFileDialog(self, "Vyber soubory nebo složku s kódem", str(WORKSPACE))
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dialog.setNameFilter(CODE_FILE_FILTER)
        # nutné pro naši úpravu vzhledu - nativní dialog ignoruje QSS
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)

        # aby dialog ladil s CRT terminál stylem - jinak by měl systémové barvy
        t = THEMES[self._theme_id]
        dialog.setStyleSheet(f"""
            QFileDialog {{
                background-color: {t.case};
            }}
            QFileDialog QWidget {{
                color: {t.fg};
                background-color: {t.screen};
            }}
            QFileDialog QTreeView, QFileDialog QListView {{
                background-color: {t.screen};
                color: {t.fg};
                border: 2px solid {t.fg_dim};
            }}
            QFileDialog QTreeView::item:selected, QFileDialog QListView::item:selected {{
                background-color: {t.fg_dim};
                color: {t.fg_glow};
            }}
            QFileDialog QLabel {{
                color: {t.fg};
            }}
            QFileDialog QLineEdit {{
                background-color: {t.screen};
                color: {t.fg};
                border: 2px solid {t.fg_dim};
                padding: 4px;
            }}
            QFileDialog QPushButton {{
                background-color: {t.screen};
                color: {t.fg};
                border: 2px solid {t.fg};
                padding: 5px 12px;
            }}
            QFileDialog QPushButton:hover {{
                background-color: {t.fg_dim};
                color: {t.fg_glow};
            }}
            QFileDialog QComboBox {{
                background-color: {t.screen};
                color: {t.fg};
                border: 2px solid {t.fg_dim};
            }}
            QFileDialog QHeaderView::section {{
                background-color: {t.screen};
                color: {t.fg_glow};
                border: 1px solid {t.fg_dim};
                padding: 3px;
            }}
        """)
        
        # Qt defaultně nedovolí vybrat složku v ExistingFiles režimu -
        # vyhrábneme si listView/treeView a povolíme extended selection,
        # takže uživatel může kliknout na adresář a otevřít ho jako výběr
        file_view = dialog.findChild(QListView, "listView")
        if file_view:
            file_view.setSelectionMode(QListView.SelectionMode.ExtendedSelection)
        tree_view = dialog.findChild(QTreeView, "treeView")
        if tree_view:
            tree_view.setSelectionMode(QTreeView.SelectionMode.ExtendedSelection)

        if not dialog.exec():
            return

        selected = dialog.selectedFiles()
        if not selected:
            return

        skipped: list[str] = []
        already_attached = {p.name for p, _ in self._attached}

        for selected_path in selected:
            path = Path(selected_path)
            if path.is_dir():
                self._attach_folder(path, already_attached, skipped)
            else:
                self._attach_single_file(path, already_attached, skipped)

        if skipped:
            QMessageBox.warning(
                self,
                APP_TITLE,
                "Některé soubory se nepodařilo přiložit:\n\n" + "\n".join(skipped[:20])
                + (f"\n... a {len(skipped) - 20} dalších" if len(skipped) > 20 else ""),
            )

        self._update_attachment_label()

    def _attach_single_file(
        self,
        path: Path,
        already_attached: set[str],
        skipped: list[str],
    ) -> None:
        """Načte soubor a přidá ho do příloh. Filtrujeme velikost a UTF-8."""
        if path.name in already_attached:
            return

        try:
            size = path.stat().st_size
        except OSError as exc:
            skipped.append(f"{path.name} (nelze načíst: {exc})")
            return

        if size > MAX_FILE_BYTES:
            skipped.append(f"{path.name} (příliš velký, {size / 1024:.0f} kB)")
            return

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # binárka nebo jiné kódování - do promptu nemá smysl posílat
            skipped.append(f"{path.name} (není textový soubor UTF-8)")
            return
        except OSError as exc:
            skipped.append(f"{path.name} (nelze načíst: {exc})")
            return

        self._attached.append((path, content))
        already_attached.add(path.name)

    def _attach_folder(
        self,
        folder: Path,
        already_attached: set[str],
        skipped: list[str],
    ) -> None:
        """Rekurzivně nasosá všechny kódové soubory ze složky."""
        if not folder.is_dir():
            return

        found_files = []
        for ext in CODE_FILE_EXTENSIONS:
            found_files.extend(folder.rglob(f"*{ext}"))

        if not found_files:
            skipped.append(f"{folder.name}/ (žádné kódové soubory)")
            return

        for file_path in sorted(found_files):
            self._attach_single_file(file_path, already_attached, skipped)

    def _update_attachment_label(self) -> None:
        if not self._attached:
            self.attachment_label.setVisible(False)
            self.attachment_label.clear()
            self.clear_attach_button.setVisible(False)
            return

        if len(self._attached) == 1:
            path, content = self._attached[0]
            lines = content.count("\n") + 1
            size_kb = len(content.encode("utf-8")) / 1024
            text = f"📎  Příloha: {path.name}   ({lines} řádků, {size_kb:.1f} kB)"
        else:
            names = ", ".join(path.name for path, _ in self._attached)
            text = f"📎  {len(self._attached)} přílohy: {names}"

        self.attachment_label.setText(text)
        self.attachment_label.setVisible(True)
        self.clear_attach_button.setVisible(True)

    def _clear_attachment(self) -> None:
        self._attached = []
        self._update_attachment_label()

    # ── odeslání ──────────────────────────────────────────────

    def _on_send(self) -> None:
        # ignore když je agent zaneprázdněný nebo offline
        if self._busy or not self._connected:
            return

        typed = self.input.toPlainText().strip()
        if not typed and not self._attached:
            return

        blocks = []
        transcript_parts = []

        if self._attached:
            if len(self._attached) == 1:
                default_instruction = (
                    f"Analyzuj přiložený soubor `{self._attached[0][0].name}` "
                    "a najdi bezpečnostní slabiny."
                )
            else:
                names = ", ".join(f"`{p.name}`" for p, _ in self._attached)
                default_instruction = (
                    f"Analyzuj přiložené soubory ({names}) a najdi bezpečnostní slabiny."
                )
            instruction = typed or default_instruction

            file_sections = "\n\n".join(
                f"Soubor k analýze: `{path.name}`\n\n```\n{content}\n```"
                for path, content in self._attached
            )
            blocks.append(text_block(f"{instruction}\n\n{file_sections}"))

            # resource blok jen když ho agent umí (kiro-cli 2.16.2 ne)
            if self.client.supports_embedded_context():
                for path, content in self._attached:
                    blocks.append(resource_block(path, content))

            transcript_parts.append(instruction)
            for path, content in self._attached:
                lines = content.count("\n") + 1
                transcript_parts.append(f"*📎 příloha: `{path.name}` ({lines} řádků)*")
        else:
            blocks.append(text_block(typed))
            transcript_parts.append(typed)

        self._append("user", "\n\n".join(transcript_parts))

        self.input.clear()
        self._clear_attachment()

        # připrav placeholder pro streamovanou odpověď agenta
        self._agent_buffer = ""
        self._streaming = True
        self._messages.append(("agent", ""))
        self._set_busy(True, "Analyzuji…")

        def worker() -> None:
            try:
                reason = self.client.prompt(blocks)
            except AcpError as exc:
                self.bridge.promptFinished.emit(False, str(exc))
                return
            except Exception as exc:  # noqa: BLE001
                self.bridge.promptFinished.emit(False, f"Neočekávaná chyba: {exc}")
                return
            self.bridge.promptFinished.emit(True, reason)

        threading.Thread(target=worker, daemon=True).start()

    def _on_prompt_finished(self, ok: bool, detail: str) -> None:
        self._streaming = False
        self._flush_agent_buffer()
        self._set_busy(False)

        if not ok:
            message = f"**Chyba při analýze**\n\n```\n{detail}\n```"
            # "Internal error" bývá skoro vždycky nepřihlášené kiro-cli
            if not self._logged_in or "Internal error" in detail:
                message += f"\n\nPravděpodobná příčina:\n\n```\n{LOGIN_HINT}\n```"
            self._append("error", message)
            return

        if detail == "cancelled":
            self._append("system", "Analýza přerušena uživatelem.")
        elif detail == "refusal":
            self._append("system", "Agent odmítl v analýze pokračovat.")
        elif detail == "max_tokens":
            self._append(
                "system",
                "Dosažen limit tokenů – zkus soubor rozdělit na menší části.",
            )

        self.input.setFocus()

    def _on_cancel(self) -> None:
        if not self._busy:
            return
        try:
            self.client.cancel()
        except AcpError as exc:
            self._append("error", f"Přerušení selhalo: {exc}")
        else:
            self._set_status("Přerušuji…")

    # ── příjem od agenta ──────────────────────────────────────

    def _on_text(self, chunk: str) -> None:
        """Streamovaný kousek textu od agenta - buferujeme a překreslíme s throttle."""
        if not chunk:
            return
        self._agent_buffer += chunk
        if self._messages and self._messages[-1][0] == "agent":
            self._messages[-1] = ("agent", self._agent_buffer)
        else:
            self._messages.append(("agent", self._agent_buffer))
        # timer zabrání překreslení při každém chunk (GUI by se zadýchalo)
        if not self._render_timer.isActive():
            self._render_timer.start()

    def _flush_agent_buffer(self) -> None:
        if self._messages and self._messages[-1][0] == "agent" and not self._messages[-1][1]:
            self._messages.pop()
        self._render_timer.stop()
        self._render()

    def _on_tool_call(self, title: str, status: str) -> None:
        # tool calls se do chatu nedávají (steering to zakazuje), jen do status baru
        if status in ("in_progress", "pending", ""):
            self._set_status(f"Nástroj: {title}")
        elif self._busy:
            self._set_status("Analyzuji…")

    def _on_turn_end(self, reason: str) -> None:
        self._streaming = False
        self._flush_agent_buffer()

    def _on_log(self, message: str) -> None:
        # diagnostika ven ze stderr, ne do chatu
        print(message, file=sys.stderr)

    def _on_permission_request(
        self, request_id: object, tool_name: str, options: object
    ) -> None:
        """Agent chce spustit nástroj mimo whitelist - ptáme se uživatele."""
        opts: list[PermissionOption] = list(options)  # type: ignore[arg-type]

        if not opts:
            # nic k odsouhlasení - odmítni bez ptaní
            self.client.respond_permission(request_id, None)
            return

        box = QMessageBox(self)
        box.setWindowTitle(f"{APP_TITLE} – povolení nástroje")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText("Agent žádá o povolení spustit nástroj:")
        box.setInformativeText(f"{tool_name}")

        button_map = {}
        for opt in opts:
            role = (
                QMessageBox.ButtonRole.RejectRole
                if opt.kind.startswith("reject")
                else QMessageBox.ButtonRole.AcceptRole
            )
            button = box.addButton(opt.name or opt.option_id, role)
            button_map[button] = opt.option_id

        box.exec()
        clicked = box.clickedButton()
        chosen = button_map.get(clicked)

        self.client.respond_permission(request_id, chosen)

        if chosen is None:
            self._append("system", f"Spuštění nástroje `{tool_name}` bylo zamítnuto.")

    # ── vykreslení chatu ──────────────────────────────────────

    def _append(self, role: str, text: str) -> None:
        self._messages.append((role, text))
        self._render()

    def _render(self) -> None:
        # zapamatuj si, jestli je scroll dole - po překreslení tam vrátíme
        scrollbar = self.screen.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - 24

        parts = []
        for role, text in self._messages:
            if not text:
                continue
            text = _normalize_prose_spacing(text)
            color = self._role_colors.get(role, self._role_colors["agent"])
            if role == "user":
                parts.append(f'<span style="color:{color}">&gt; <b>TY</b></span>\n\n{text}')
            elif role == "agent":
                parts.append(f'<span style="color:{color}">&gt; <b>CODEFENDER</b></span>\n\n{text}')
            elif role == "error":
                parts.append(f'<span style="color:{color}">&gt; <b>CHYBA</b></span>\n\n{text}')
            else:
                parts.append(f'<span style="color:{color}">&gt; <b>SYSTÉM</b></span>\n\n{text}')

        self.screen.setMarkdown("\n\n---\n\n".join(parts))
        _widen_paragraph_spacing(self.screen)

        if at_bottom:
            self.screen.moveCursor(QTextCursor.MoveOperation.End)
            scrollbar.setValue(scrollbar.maximum())

    # ── stav ──────────────────────────────────────────────────

    def _idle_status(self) -> str:
        """Text stavu, když agent nic nedělá."""
        if not self._connected:
            return "Nepřipojeno"
        if not self._logged_in:
            return "Nepřihlášeno · spusť `kiro-cli login`"
        agent_name = self.client.agent_info.get("name", "kiro-cli")
        agent_version = self.client.agent_info.get("version", "")
        return f"Připojeno · {agent_name} {agent_version}".strip()

    def _set_status(self, text: str, *, animated: bool = False) -> None:
        """Nastaví text status baru. `animated=True` přidá rotující ASCII spinner."""
        if animated:
            self._spinner_status = text
            self._spinner_frame = 0
            self.status_label.setText(f"{SPINNER_FRAMES[0]} {text}")
            if not self._spinner_timer.isActive():
                self._spinner_timer.start()
        else:
            self._spinner_status = ""
            if self._spinner_timer.isActive():
                self._spinner_timer.stop()
            self.status_label.setText(text)

    def _tick_spinner(self) -> None:
        """Posune spinner o rámeček dopředu."""
        if not self._spinner_status:
            self._spinner_timer.stop()
            return
        self._spinner_frame = (self._spinner_frame + 1) % len(SPINNER_FRAMES)
        frame = SPINNER_FRAMES[self._spinner_frame]
        self.status_label.setText(f"{frame} {self._spinner_status}")

    def _set_busy(self, busy: bool, status: str | None = None) -> None:
        self._busy = busy
        self.send_button.setEnabled(not busy and self._connected)
        self.attach_button.setEnabled(not busy and self._connected)
        self.cancel_button.setEnabled(busy)
        self.model_combo.setEnabled(
            not busy and self._connected and self.client.supports_model_switching()
        )
        self.input.setReadOnly(busy)

        if status:
            # při busy status animujeme, jinak statický text
            self._set_status(status, animated=busy)
        elif not busy:
            self._set_status(self._idle_status())

    # ── settings / theme / font ───────────────────────────────

    def _open_settings(self) -> None:
        """Otevře popup s barvou a velikostí fontu. Změny se aplikují live."""
        # jeden dialog na okno - když už je otevřený, jen ho aktivuj
        if self._settings_dialog is not None and self._settings_dialog.isVisible():
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
            return

        dialog = SettingsDialog(
            self._theme_id,
            self._font_px,
            self._vignette_pct,
            self,
        )
        dialog.themeChanged.connect(self.apply_theme)
        dialog.fontSizeChanged.connect(self.apply_font_size)
        dialog.vignetteChanged.connect(self.apply_vignette_strength)
        dialog.finished.connect(lambda _: self._forget_settings_dialog())
        self._settings_dialog = dialog
        dialog.show()

    def _forget_settings_dialog(self) -> None:
        self._settings_dialog = None

    def _reapply_style(self) -> None:
        """Přenačte QSS + chat CSS pro aktuální theme a font, aktualizuje overlay + ikonu."""
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_qss(self._theme_id, self._font_px))
        self.screen.document().setDefaultStyleSheet(
            build_chat_css(self._theme_id, self._font_px)
        )
        self.crt_overlay.set_edge_color(THEMES[self._theme_id].screen_edge)
        # gear ikona v barvě tématu (fg) - musí se překreslit při každé změně
        self.settings_button.setIcon(make_gear_icon(THEMES[self._theme_id].fg))

    def apply_theme(self, theme_id: str) -> None:
        """Přepne barevnou paletu za běhu."""
        if theme_id not in THEMES or theme_id == self._theme_id:
            return
        self._theme_id = theme_id
        self._role_colors = role_colors(theme_id)
        self._reapply_style()
        # překreslit chat s novými barvami rolí
        self._render()

    def apply_font_size(self, font_px: int) -> None:
        """Nastaví velikost hlavního fontu (chat, input, kód, tlačítka)."""
        font_px = max(MIN_FONT_PX, min(MAX_FONT_PX, int(font_px)))
        if font_px == self._font_px:
            return
        self._font_px = font_px
        self._reapply_style()
        # chat musí přerenderovat, aby se změny v setDefaultStyleSheet projevily
        self._render()

    def apply_vignette_strength(self, percent: int) -> None:
        """Nastaví intenzitu zakřivení (vignette) v procentech 0-100."""
        percent = max(0, min(100, int(percent)))
        self._vignette_pct = percent
        # mapování 0-100 % → 0-255 alpha
        alpha = round(percent * 255 / 100)
        self.crt_overlay.set_vignette_strength(alpha)

    # ── copy / export ─────────────────────────────────────────

    def _on_copy(self) -> None:
        """Zkopíruje poslední odpověď agenta do systémové schránky."""
        last_agent = None
        for role, text in reversed(self._messages):
            if role == "agent" and text:
                last_agent = text
                break

        if not last_agent:
            self._set_status("Není co kopírovat", animated=False)
            return

        clipboard = QGuiApplication.clipboard()
        if clipboard is None:
            return
        clipboard.setText(last_agent)
        self._set_status("Zkopírováno do schránky", animated=False)

    def _on_export(self) -> None:
        """Uloží celou konverzaci do textového souboru."""
        if not self._messages:
            self._set_status("Není co exportovat", animated=False)
            return

        default_name = "codefender-report.txt"
        path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Uložit report",
            str(WORKSPACE / default_name),
            "Textový soubor (*.txt);;Markdown (*.md);;Všechny soubory (*)",
        )
        if not path_str:
            return

        path = Path(path_str)
        try:
            path.write_text(self._build_export_text(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(
                self,
                APP_TITLE,
                f"Nepodařilo se uložit report:\n\n{exc}",
            )
            return

        self._set_status(f"Uloženo: {path.name}", animated=False)

    def _build_export_text(self) -> str:
        """Serializuje self._messages do plain textu pro export."""
        from datetime import datetime

        header = (
            f"CODEfender - report analýzy\n"
            f"Vygenerováno: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"{'=' * 60}\n\n"
        )

        role_labels = {
            "user": "TY",
            "agent": "CODEFENDER",
            "system": "SYSTÉM",
            "error": "CHYBA",
            "tool": "NÁSTROJ",
        }

        parts = []
        for role, text in self._messages:
            if not text:
                continue
            label = role_labels.get(role, role.upper())
            parts.append(f"> {label}\n\n{text}\n")

        return header + ("\n" + "-" * 60 + "\n\n").join(parts)

    # ── drag & drop ───────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802 - Qt API
        # akceptuj jen když je v datech seznam file:// URL
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802 - Qt API
        urls = event.mimeData().urls()
        if not urls:
            event.ignore()
            return

        skipped: list[str] = []
        already_attached = {p.name for p, _ in self._attached}

        for url in urls:
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.is_dir():
                self._attach_folder(path, already_attached, skipped)
            else:
                self._attach_single_file(path, already_attached, skipped)

        if skipped:
            QMessageBox.warning(
                self,
                APP_TITLE,
                "Některé soubory se nepodařilo přiložit:\n\n"
                + "\n".join(skipped[:20])
                + (f"\n... a {len(skipped) - 20} dalších" if len(skipped) > 20 else ""),
            )

        self._update_attachment_label()
        event.acceptProposedAction()

    # ── overlay geometry (CRT curvature + scan lines) ─────────

    def _update_overlay_geometry(self) -> None:
        """Roztáhne CRT overlay přes celou plochu screen widgetu."""
        # rect() vrací (0, 0, w, h) - overlay je child screen, tohle je
        # jeho lokální souřadnicový systém. Clip path uvnitř overlay
        # ho ořízne podle border-radius.
        self.crt_overlay.setGeometry(self.screen.rect())
        self.crt_overlay.raise_()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 - Qt API
        # resize screen widgetu = musíme přeroztáhnout overlay
        if obj is self.screen and event.type() == QEvent.Type.Resize:
            self._update_overlay_geometry()
        return super().eventFilter(obj, event)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt API
        # při prvním zobrazení okna už viewport má správnou velikost,
        # ale event filter už resize event nepřijme (proběhl dřív)
        super().showEvent(event)
        self._update_overlay_geometry()

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 - Qt API
        # pojistka - kdyby viewport resize neproběhl, tak nás zachrání okno
        super().resizeEvent(event)
        self._update_overlay_geometry()

    # ── zavření ───────────────────────────────────────────────

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        try:
            self.client.stop()
        except Exception:
            pass
        super().closeEvent(event)


# ─────────────────────────────────────────────────────────────
# Vstupní bod
# ─────────────────────────────────────────────────────────────


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setStyleSheet(build_qss(DEFAULT_THEME))

    # ikona pro okno + taskbar - .ico má víc velikostí, Qt si vybere
    if ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(ICON_PATH)))

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
