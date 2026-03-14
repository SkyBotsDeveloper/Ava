# Ava Progress

## 2026-03-14

### Completed

- Bootstrapped the repository from an empty directory
- Added Python packaging, linting, tests, and pre-commit foundation
- Added runtime config loading and `.env.example`
- Added structured logging and runtime path bootstrap
- Added SQLite schema bootstrap and action journal store
- Added intent router, safety policy, browser strategy, and app controller scaffolding
- Added a Phase 2-ready PySide6/QML orb shell with text command fallback hooks

### Verified

- Repository initialized locally
- Core tests for config, journal logging, intent routing, and browser selection pass locally once the local Python 3.11-capable environment is created
- The app bootstrap path creates runtime folders and the SQLite database file

### Blocked

- Real Gemini Live verification is blocked until a Gemini API key is provided
- Wake-word, voice streaming, and Windows automation execution are intentionally deferred to later phases
- The machine’s standard Python 3.11 launcher path is inconsistent, so local verification uses a local 3.11-capable environment workaround
