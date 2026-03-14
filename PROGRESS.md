# Ava Progress

## 2026-03-14

### Completed

- Bootstrapped the repository from an empty directory
- Added Python packaging, linting, tests, and pre-commit foundation
- Added runtime config loading and `.env.example`
- Added structured logging and runtime path bootstrap
- Added SQLite schema bootstrap and action journal store
- Added intent router, safety policy, browser strategy, and app controller scaffolding
- Added a compact PySide6/QML orb shell with a collapsed-by-default footprint
- Added an expandable control drawer with visible idle/listening/thinking/speaking/muted states
- Added text command fallback, mute/unmute, emergency stop, and recent journal history wiring
- Added a Qt history model and tray integration for a more usable desktop shell

### Verified

- Repository initialized locally
- `ruff check .` passes
- `pytest` passes
- The app bootstrap path creates runtime folders and the SQLite database file
- The shell launches locally as a real frameless topmost window with no caption
- The live shell starts collapsed at `138x166` and expands via the real `Open` control to `332x494`

### Blocked

- Real Gemini Live verification is blocked until a Gemini API key is provided
- Wake-word, voice streaming, and Windows automation execution are intentionally deferred to later phases
- The machine's standard Python 3.11 launcher path is inconsistent, so local verification uses a local Python 3.11 conda environment workaround
