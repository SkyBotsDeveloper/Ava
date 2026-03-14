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
- Froze the shell layout and applied a final visual pass with smoother ring motion, cleaner glow, and lighter panel glass
- Added Gemini Live session interfaces, the Gemini adapter, and a Hinglish assistant system prompt
- Added a Phase 3 voice runtime with async session orchestration, audio playback wiring, wake-word scaffolding, and VAD-based turn ending
- Added initial Phase 3 tests for prompting, Gemini event normalization, and voice runtime state/journal flow

### Verified

- Repository initialized locally
- `ruff check .` passes
- `pytest` passes
- The app bootstrap path creates runtime folders and the SQLite database file
- The shell launches locally as a real frameless topmost window with no caption
- The live shell starts collapsed at `138x166` and expands via the real `Open` control to `332x494`
- The frozen shell launches locally after the final visual pass with no runtime errors
- Phase 3 runtime tests pass without a real Gemini key by using fakes for the live client

### Blocked

- Real Gemini Live verification is blocked until a Gemini API key is provided
- Always-on wake testing is blocked until a real openWakeWord model path is configured
- Global push-to-talk hotkey wiring is still pending on top of the Phase 3 runtime
- The machine's standard Python 3.11 launcher path is inconsistent, so local verification uses a local Python 3.11 conda environment workaround
