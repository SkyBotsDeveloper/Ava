from __future__ import annotations

import sys

from ava.app.bootstrap import bootstrap_application


def main() -> int:
    try:
        from ava.ui.window import run_ui
    except ImportError as exc:
        print(f"PySide6 is required to run Ava's desktop shell: {exc}", file=sys.stderr)
        return 1

    context = bootstrap_application()
    return run_ui(context)


if __name__ == "__main__":
    raise SystemExit(main())
