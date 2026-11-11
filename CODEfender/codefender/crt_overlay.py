"""
CRT overlay - efekty pro obrazovku terminálu.

Widget se pokládá přes celý screen widget (QTextBrowser) a kreslí:
  - vignette (radial gradient, ztmavení rohů - iluze zakřivení skla)
  - scan-line efekt (horizontální tmavé linky)

Efekt je clip-nutý zaobleným obdélníkem podle border-radius screenu,
aby přesně kopíroval tvar CRT. Overlay nechytá myš, takže scroll a
selekce fungují normálně.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget


class CRTOverlay(QWidget):
    """Průhledný overlay nad chat browserem s CRT efekty."""

    # rozestup scan-line (px)
    SCAN_LINE_SPACING = 3
    SCAN_LINE_ALPHA = 90          # 0-255, síla ztmavení proužku
    VIGNETTE_DEFAULT = 170        # 0-255, výchozí síla ztmavení rohů

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # neblokuj interakci s widgetem pod overlayem
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # nemá se dostat do focus chainu
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._scan_lines_enabled = True
        self._vignette_strength = self.VIGNETTE_DEFAULT
        self._edge_color = QColor(0, 0, 0)

        # shape screen widgetu pod námi - potřebujeme kopírovat zaoblení
        # (border-radius + border-width odpovídají QSS v ui_theme.py)
        self._border_width = 8
        self._border_radius = 26

    def set_edge_color(self, color: str) -> None:
        """Barva vignette (typicky screen_edge z tématu)."""
        self._edge_color = QColor(color)
        self.update()

    def set_screen_shape(self, border_width: int, border_radius: int) -> None:
        """
        Nastaví geometrii zaoblení screen widgetu - overlay ji použije
        pro clip path, aby efekt přesně kopíroval tvar CRT.
        """
        self._border_width = max(0, border_width)
        self._border_radius = max(0, border_radius)
        self.update()

    def set_scan_lines(self, enabled: bool) -> None:
        self._scan_lines_enabled = enabled
        self.update()

    def set_vignette_strength(self, alpha: int) -> None:
        """Síla ztmavení rohů (0 = vypnuto, 255 = maximum)."""
        self._vignette_strength = max(0, min(255, int(alpha)))
        self.update()

    def _inner_clip_path(self) -> QPainterPath:
        """
        Vytvoří clip path uvnitř border screenu se zaoblenými rohy -
        overlay se ořízne tak, aby netekl přes rám ani zaoblené rohy.
        """
        # vnitřní radius je o border menší (vnější 26px - border 8px = 18px)
        inner_radius = max(0, self._border_radius - self._border_width)
        inner_rect = QRectF(self.rect()).adjusted(
            self._border_width,
            self._border_width,
            -self._border_width,
            -self._border_width,
        )
        path = QPainterPath()
        path.addRoundedRect(inner_rect, inner_radius, inner_radius)
        return path

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # clip do zaobleného vnitřku - efekt se pak automaticky ořízne
        # v rozích, takže sedí na tvar CRT
        painter.setClipPath(self._inner_clip_path())

        rect_f = QRectF(self.rect())

        # ── vignette (radial gradient tmavý na rozích) ──
        if self._vignette_strength > 0:
            cx = rect_f.width() / 2
            cy = rect_f.height() / 2
            # poloměr = polovina úhlopříčky, aby gradient stačil do rohů
            radius = (rect_f.width() ** 2 + rect_f.height() ** 2) ** 0.5 / 2

            gradient = QRadialGradient(cx, cy, radius)
            # střed skoro průhledný
            center = QColor(self._edge_color)
            center.setAlpha(0)
            gradient.setColorAt(0.0, center)
            # 55 % poloměru ještě průhledné
            mid = QColor(self._edge_color)
            mid.setAlpha(0)
            gradient.setColorAt(0.55, mid)
            # kraje - aktuální síla podle nastavení
            edge = QColor(self._edge_color)
            edge.setAlpha(self._vignette_strength)
            gradient.setColorAt(1.0, edge)

            painter.fillRect(rect_f, gradient)

        # ── scan lines (horizontální ztmavené proužky) ──
        if self._scan_lines_enabled:
            # QPen s alphou dobře fungujícím i na tmavém pozadí
            pen = QPen(QColor(0, 0, 0, self.SCAN_LINE_ALPHA))
            pen.setWidth(1)
            pen.setCosmetic(True)
            painter.setPen(pen)
            # antialias off pro ostré vodorovné čáry (jinak splynou)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

            w = int(rect_f.width())
            h = int(rect_f.height())
            y = 0
            while y < h:
                painter.drawLine(0, y, w, y)
                y += self.SCAN_LINE_SPACING

        painter.end()
