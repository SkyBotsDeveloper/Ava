# Ava

Ava is a Windows-only, voice-first AI desktop agent with a premium orb UI, local memory, strict action safety, and Gemini Live as the initial realtime intelligence layer.

## Current status

Phase 4 browser command work is now underway on top of the frozen shell:

- Python project scaffold with tooling, linting, tests, and pre-commit hooks
- Config loading via `.env`
- Structured logging and runtime path bootstrap
- SQLite-backed action journal and memory schema bootstrap
- Live-verified PySide6/QML orb shell with a compact collapsed default
- Final shell styling pass with smoother halo motion, lighter panel glass, and cleaner premium controls
- Expandable control drawer with text fallback, mute, cancel, and recent activity history
- Intent routing, browser strategy defaults, and safety policy scaffolding
- Gemini Live client adapter and Hinglish system prompt
- Async voice runtime for Gemini text turns, manual voice trigger, audio playback, wake-word monitoring, and state transitions
- Isolated sacrificial browser controller plus real Ava command-pipeline wiring for safe browser MVP flows

## Product defaults locked in this repo

- Voice-first, but text command, push-to-talk, mute, and emergency stop are mandatory controls
- Wake-word detection will use a proven local detector (`openWakeWord`) as the primary path in the next phase
- Browser command execution currently defaults to an isolated sacrificial Edge/Chrome session so the user's real browser stays untouched during Phase 4 verification
- Automation priority is UI Automation first, input simulation second, DOM automation third, visual fallback last
- Development secrets stay in `.env`; packaged builds should migrate sensitive secrets to Windows Credential Manager or an equivalent secure store

## Quick start

1. Install Python 3.11.
2. Create a virtual environment.
3. Install dependencies:

```powershell
python -m pip install -e ".[dev,voice]"
```

4. Copy `.env.example` to `.env`.
5. Add your Gemini API key to `AVA_GEMINI_API_KEY`.
6. Add one or more local wake-word model paths to `AVA_WAKEWORD_MODEL_PATHS` only when you are ready to test always-on wake.
7. Run tests:

```powershell
pytest
```

8. Start the desktop shell:

```powershell
python -m ava.main
```

The shell launches as a compact orb by default. Click the orb to open the assistant sheet.

## Repo layout

```text
src/ava/app          Application bootstrap and orchestration
src/ava/ui           PySide6/QML orb shell and UI bridge
src/ava/voice        Voice runtime, audio, VAD, and wake-word interfaces
src/ava/live         Gemini Live adapter and prompting
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
- During the current Phase 4 browser MVP, `AVA_BROWSER_COMMAND_MODE=isolated` keeps Ava on a disposable sacrificial browser profile for safer verification.

## Safety baseline

- Sending messages, deleting files, installing apps, submitting logins, and sensitive or identity-dependent actions require confirmation.
- `Stop Ava` and `Cancel` are hard interruption commands and must stop active tasks safely.
- Banking, password managers, and similarly sensitive contexts are private-by-default and should stay suggestion-only unless explicitly overridden.

## Phase 3 blockers

- Always-on wake testing is blocked until `AVA_WAKEWORD_MODEL_PATHS` points to a real local openWakeWord model file.
- The current `Ctrl+Alt+A` manual trigger path is app-focused, not a system-wide global hotkey yet.
