# Ava

Ava is a Windows-only, voice-first AI desktop agent with a premium orb UI, local memory, strict action safety, and Gemini Live as the initial realtime intelligence layer.

## Current status

Phase 1 foundation is in place:

- Python project scaffold with tooling, linting, tests, and pre-commit hooks
- Config loading via `.env`
- Structured logging and runtime path bootstrap
- SQLite-backed action journal and memory schema bootstrap
- Phase 2-ready PySide6/QML app shell with text command fallback
- Intent routing, browser strategy defaults, and safety policy scaffolding

## Product defaults locked in this repo

- Voice-first, but text command, push-to-talk, mute, and emergency stop are mandatory controls
- Wake-word detection will use a proven local detector (`openWakeWord`) as the primary path in the next phase
- Browser control is live-session first for Chrome/Edge, with Microsoft Edge as the default fallback browser profile
- Automation priority is UI Automation first, input simulation second, DOM automation third, visual fallback last
- Development secrets stay in `.env`; packaged builds should migrate sensitive secrets to Windows Credential Manager or an equivalent secure store

## Quick start

1. Install Python 3.11.
2. Create a virtual environment.
3. Install dependencies:

```powershell
python -m pip install -e ".[dev]"
```

4. Copy `.env.example` to `.env` and add your Gemini API key when Phase 3 begins.
5. Run tests:

```powershell
pytest
```

6. Start the desktop shell:

```powershell
python -m ava.main
```

## Repo layout

```text
src/ava/app          Application bootstrap and orchestration
src/ava/ui           PySide6/QML orb shell and UI bridge
src/ava/voice        Voice and wake-word interfaces
src/ava/live         Gemini Live interfaces
src/ava/intents      Shared text/voice intent routing
src/ava/automation   Browser and Windows control planning
src/ava/observation  Observation policy and privacy controls
src/ava/memory       SQLite schema, journal, and bootstrap
src/ava/safety       Confirmation and safety policy
src/ava/config       Settings and runtime paths
src/ava/telemetry    Logging and diagnostics
tests/               Unit tests and integration scaffolding
```

## Browser behavior

- If a suitable live Chrome or Edge session is already open, Ava should control that first.
- If no suitable live session exists, Ava should open the preferred browser profile in Microsoft Edge by default unless the setting is changed later.
- Playwright is a fallback for flows that need DOM certainty, not the default browsing experience.

## Safety baseline

- Sending messages, deleting files, installing apps, submitting logins, and sensitive or identity-dependent actions require confirmation.
- `Stop Ava` and `Cancel` are hard interruption commands and must stop active tasks safely.
- Banking, password managers, and similarly sensitive contexts are private-by-default and should stay suggestion-only unless explicitly overridden.
