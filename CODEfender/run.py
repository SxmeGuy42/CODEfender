"""
CODEfender - spouštěč desktopové aplikace.

Vlastní analýzu neřeší, jen nabootuje GUI. Práci dělá Kiro agent `codefender`
podle steering files v .kiro/.
"""

import sys
from pathlib import Path

# aby šel importovat balíček `codefender`, když se skript spustí z rootu
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _fail(message: str) -> int:
    print(f"\n❌ {message}\n", file=sys.stderr)
    return 1


def main() -> int:
    print("🛡️  CODEfender - bezpečnostní analýza kódu")
    print("=" * 50)

    try:
        from codefender.app import main as run_app
    except ImportError as exc:
        # nejčastější případ - chybí PySide6, dej uživateli konkrétní radu
        if "PySide6" in str(exc):
            return _fail(
                "Chybí PySide6 (GUI framework desktopové aplikace).\n"
                "   Nainstaluj závislosti:  py -m pip install -r requirements.txt"
            )
        return _fail(f"Aplikaci nelze naimportovat: {exc}")

    return run_app()


if __name__ == "__main__":
    sys.exit(main())
