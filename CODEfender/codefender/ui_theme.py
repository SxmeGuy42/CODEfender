"""
QSS stylesheet + palety pro CODEfender.

Retro CRT terminal - béžový plast okolo, tmavá obrazovka s fosforovým
textem uvnitř. Podporuje víc barevných variant (zelená / amber / modrá
/ bílá) - přepnutí za běhu přes MainWindow.apply_theme().
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """Jedna paleta CRT monitoru."""

    id: str
    label: str
    # béžový plast okolo obrazovky (typicky beige/khaki)
    case: str
    case_dark: str
    bezel: str
    # obrazovka
    screen: str
    screen_edge: str      # tmavší varianta pro vignette overlay
    # hlavní fosforová barva (text)
    fg: str
    fg_dim: str
    fg_glow: str
    # text na béžovém pozadí (nadpisy, popisky)
    text_case: str


# ── palety ─────────────────────────────────────────────────

THEMES: dict[str, Theme] = {
    "green": Theme(
        id="green",
        label="Fosforová zelená",
        case="#e8dfc2",
        case_dark="#cfc4a0",
        bezel="#5b5338",
        screen="#0b0f0a",
        screen_edge="#020402",
        fg="#33ff5b",
        fg_dim="#1c8a35",
        fg_glow="#7dffa0",
        text_case="#3a331f",
    ),
    "amber": Theme(
        id="amber",
        label="Amber (IBM 5151)",
        case="#e8dfc2",
        case_dark="#cfc4a0",
        bezel="#5b4a28",
        screen="#0f0a02",
        screen_edge="#050300",
        fg="#ffb000",
        fg_dim="#8a5a00",
        fg_glow="#ffd070",
        text_case="#3a331f",
    ),
    "blue": Theme(
        id="blue",
        label="Ledová modrá",
        case="#d8d8e0",
        case_dark="#b5b5c0",
        bezel="#4a4a5a",
        screen="#050810",
        screen_edge="#010208",
        fg="#5bc8ff",
        fg_dim="#2a6a90",
        fg_glow="#a8e2ff",
        text_case="#22223a",
    ),
    "white": Theme(
        id="white",
        label="Vintage bílá (VT100)",
        case="#e0dccc",
        case_dark="#bab5a0",
        bezel="#4a4438",
        screen="#0a0a08",
        screen_edge="#020202",
        fg="#e0e0d0",
        fg_dim="#8a8a7a",
        fg_glow="#ffffff",
        text_case="#3a331f",
    ),
}

DEFAULT_THEME = "green"

MONO_FONT = "Consolas"

# velikost fontu v hlavních plochách (chat, input) - přenastavitelné
DEFAULT_FONT_PX = 15
MIN_FONT_PX = 10
MAX_FONT_PX = 22


# ── mapování role zprávy -> barva záhlaví bloku ────────────

def role_colors(theme_id: str = DEFAULT_THEME) -> dict[str, str]:
    """Barvy pro role zpráv v chatu (user/agent/system/error/tool)."""
    t = THEMES.get(theme_id, THEMES[DEFAULT_THEME])
    return {
        "user": t.fg_glow,
        "agent": t.fg,
        "system": "#c8a24a" if theme_id != "amber" else "#ff9040",
        "error": "#ff6b5b",
        "tool": t.fg_dim,
    }


# ── stavba QSS pro danou paletu ────────────────────────────

def build_qss(theme_id: str = DEFAULT_THEME, font_px: int = DEFAULT_FONT_PX) -> str:
    t = THEMES.get(theme_id, THEMES[DEFAULT_THEME])
    # velikosti popisků škálují mírněji než hlavní font
    label_px = max(MIN_FONT_PX, min(font_px - 2, 16))
    button_px = max(MIN_FONT_PX, min(font_px - 1, 18))
    return f"""
/* okno = béžový plast okolo obrazovky */
QMainWindow, QWidget#RootPanel {{
    background-color: {t.case};
}}

QWidget {{
    color: {t.text_case};
    font-family: "{MONO_FONT}", "Courier New", monospace;
    font-size: {font_px}px;
}}

QLabel#TitleLabel {{
    color: {t.text_case};
    font-size: 20px;
    font-weight: bold;
    letter-spacing: 2px;
    padding: 2px 0px;
}}

QLabel#SubtitleLabel {{
    color: {t.text_case};
    font-size: {label_px}px;
}}

QLabel#StatusLabel {{
    color: {t.text_case};
    font-size: {label_px}px;
    padding: 2px 6px;
    border: 1px solid {t.case_dark};
    border-radius: 3px;
    background-color: {t.case_dark};
}}

QLabel#FieldLabel {{
    color: {t.text_case};
    font-size: {label_px}px;
}}

/* obrazovka terminálu - chat s reportem */
QTextBrowser#Screen {{
    background-color: {t.screen};
    color: {t.fg};
    border: 8px solid {t.bezel};
    border-radius: 26px;
    padding: 22px 26px;
    font-family: "{MONO_FONT}", "Courier New", monospace;
    font-size: {font_px}px;
    selection-background-color: {t.fg_dim};
    selection-color: {t.screen};
}}

/* pole pro psaní promptu */
QPlainTextEdit#Input {{
    background-color: {t.screen};
    color: {t.fg};
    border: 2px solid {t.fg_dim};
    border-radius: 10px;
    padding: 8px;
    font-family: "{MONO_FONT}", "Courier New", monospace;
    font-size: {font_px}px;
    selection-background-color: {t.fg_dim};
    selection-color: {t.screen};
}}

QPlainTextEdit#Input:focus {{
    border: 2px solid {t.fg};
}}

/* tlačítka */
QPushButton {{
    background-color: {t.screen};
    color: {t.fg};
    border: 2px solid {t.fg};
    border-radius: 6px;
    padding: 7px 16px;
    font-family: "{MONO_FONT}", "Courier New", monospace;
    font-size: {button_px}px;
    font-weight: bold;
}}

/* malé ikonkové tlačítko - settings ⚙ */
QPushButton#IconButton {{
    padding: 4px 8px;
    min-width: 0;
    font-size: {button_px + 2}px;
}}

QPushButton:hover {{
    background-color: {t.fg_dim};
    color: {t.fg_glow};
}}

QPushButton:pressed {{
    background-color: {t.fg};
    color: {t.screen};
}}

QPushButton:disabled {{
    background-color: #2a2a24;
    color: #6b7a6b;
    border: 2px solid #4a4a40;
}}

QPushButton#SecondaryButton {{
    border: 2px solid {t.fg_dim};
    color: {t.fg_dim};
}}

QPushButton#SecondaryButton:hover {{
    border: 2px solid {t.fg};
    color: {t.fg};
}}

/* dropdown pro výběr modelu a theme */
QComboBox {{
    background-color: {t.screen};
    color: {t.fg};
    border: 2px solid {t.fg_dim};
    border-radius: 6px;
    padding: 5px 10px;
    min-width: 180px;
    font-family: "{MONO_FONT}", "Courier New", monospace;
    font-size: {button_px}px;
}}

/* spinbox v settings dialogu */
QSpinBox {{
    background-color: {t.screen};
    color: {t.fg};
    border: 2px solid {t.fg_dim};
    border-radius: 6px;
    padding: 4px 8px;
    font-family: "{MONO_FONT}", "Courier New", monospace;
    font-size: {button_px}px;
}}

QSpinBox:focus {{
    border: 2px solid {t.fg};
}}

QSpinBox::up-button, QSpinBox::down-button {{
    background-color: transparent;
    border: none;
    width: 14px;
}}

QSpinBox::up-arrow {{
    image: none;
    border-left: 3px solid transparent;
    border-right: 3px solid transparent;
    border-bottom: 5px solid {t.fg};
    width: 0; height: 0;
}}

QSpinBox::down-arrow {{
    image: none;
    border-left: 3px solid transparent;
    border-right: 3px solid transparent;
    border-top: 5px solid {t.fg};
    width: 0; height: 0;
}}

QComboBox:hover {{
    border: 2px solid {t.fg};
}}

QComboBox:disabled {{
    color: #6b7a6b;
    border: 2px solid #4a4a40;
}}

QComboBox::drop-down {{
    border: none;
    width: 18px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid {t.fg};
    width: 0px;
    height: 0px;
    margin-right: 6px;
}}

QComboBox QAbstractItemView {{
    background-color: {t.screen};
    color: {t.fg};
    border: 2px solid {t.fg_dim};
    selection-background-color: {t.fg_dim};
    selection-color: {t.fg_glow};
    outline: none;
    padding: 2px;
}}

/* scrollbar - v barvě obrazovky */
QScrollBar:vertical {{
    background-color: {t.screen};
    width: 12px;
    margin: 0px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: {t.fg_dim};
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {t.fg};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

/* dialogy (message box) */
QMessageBox, QDialog {{
    background-color: {t.case};
}}

QMessageBox QLabel, QDialog QLabel {{
    color: {t.text_case};
}}

QFileDialog {{
    background-color: {t.case};
}}
"""


def build_chat_css(theme_id: str = DEFAULT_THEME, font_px: int = DEFAULT_FONT_PX) -> str:
    """
    CSS pro obsah v QTextBrowseru. Pozor: Qt vkládá inline margin
    přímo na <p>/<li>, který přebije tenhle stylesheet - mezery mezi
    odstavci se řeší v app.py programově.
    """
    t = THEMES.get(theme_id, THEMES[DEFAULT_THEME])
    # kód / pre blok - trochu tmavší podklad než obrazovka
    code_bg = _shift_toward_black(t.screen, 0.4)
    return f"""
body {{
    color: {t.fg};
    font-family: "{MONO_FONT}", "Courier New", monospace;
    font-size: {font_px}px;
}}
h1, h2, h3, h4 {{
    color: {t.fg_glow};
    font-family: "{MONO_FONT}", "Courier New", monospace;
}}
a {{ color: {t.fg_glow}; }}
code, pre {{
    font-family: "{MONO_FONT}", "Courier New", monospace;
    color: {t.fg_glow};
    background-color: {code_bg};
}}
table {{
    border-collapse: collapse;
    color: {t.fg};
}}
th, td {{
    border: 1px solid {t.fg_dim};
    padding: 4px 8px;
}}
th {{ color: {t.fg_glow}; }}
hr {{ color: {t.fg_dim}; }}
"""


def _shift_toward_black(hex_color: str, amount: float) -> str:
    """Ztmaví hex barvu o `amount` (0..1) směrem k černé."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    r = int(r * (1 - amount))
    g = int(g * (1 - amount))
    b = int(b * (1 - amount))
    return f"#{r:02x}{g:02x}{b:02x}"


# ── zpětná kompatibilita (pro externí importy) ─────────────
# aplikace by měla používat build_qss()/build_chat_css()/role_colors(),
# ale kdyby něco importovalo tyhle konstanty přímo, aby to nespadlo

QSS = build_qss(DEFAULT_THEME)
CHAT_DOCUMENT_CSS = build_chat_css(DEFAULT_THEME)
ROLE_COLORS = role_colors(DEFAULT_THEME)
