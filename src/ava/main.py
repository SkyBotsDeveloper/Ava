from __future__ import annotations

import os
import sys

from ava.app.bootstrap import bootstrap_application


def main() -> int:
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    os.environ.setdefault("QT_QUICK_CONTROLS_FALLBACK_STYLE", "Basic")
    try:
        from ava.ui.window import run_ui
    except ImportError as exc:
        print(f"PySide6 is required to run Ava's desktop shell: {exc}", file=sys.stderr)
        return 1

    context = bootstrap_application()
    return run_ui(context)


if __name__ == "__main__":
    raise SystemExit(main())
