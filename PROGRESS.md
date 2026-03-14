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
- Added a manual voice trigger path that works without wake-word models
- Added initial Phase 3 tests for prompting, Gemini event normalization, and voice runtime state/journal flow
- Added a sacrificial browser controller that launches an isolated Edge/Chrome window with a temporary profile and CDP automation for fallback/testing browser verification
- Switched the normal browser command default to the user's real Microsoft Edge profile/session, while keeping the sacrificial browser as a fallback mode
- Wired live Edge browser actions into Ava's real intent/controller/executor command pipeline for website open, tab control, page search/info, YouTube result opening, and confirmation-gated Instagram/WhatsApp flows
- Wired spoken voice commands into the same real controller/executor browser path with transcript normalization for common Gemini STT split-word variants

### Verified

- Repository initialized locally
- `ruff check .` passes
- `pytest` passes
- The app bootstrap path creates runtime folders and the SQLite database file
- The shell launches locally as a real frameless topmost window with no caption
- The live shell starts collapsed at `138x166` and expands via the real `Open` control to `332x494`
- The frozen shell launches locally after the final visual pass with no runtime errors
- Phase 3 runtime tests pass without a real Gemini key by using fakes for the live client
- Real Gemini Live text fallback now connects with the `.env` key and returns a Hinglish response
- Real manual voice trigger starts `listening` and transitions to `thinking` after manual stop, even with wake-word paths still empty
- Real sacrificial browser verification succeeds for isolated website open/navigation, tab actions, page info detection, YouTube playlist playback, Instagram login page open, and WhatsApp Web open
- Real Ava command-pipeline verification succeeds for live Edge browser commands via `AvaController.handle_text_command(...)`, including confirmation-gated tab close, Instagram login, and WhatsApp Web
- Real spoken-command verification succeeds against the live Gemini STT pipeline for browser open, address bar focus, new tab, tab switch, page search, page title/url readout, confirmation-gated tab close, YouTube open, spoken YouTube result opening, confirmation-gated Instagram login page open, and confirmation-gated WhatsApp Web open

### Blocked

- Always-on wake testing is blocked until a real openWakeWord model path is configured
- Exact arbitrary spoken URL dictation and longer spoken search queries are still less reliable than text fallback because Gemini STT can distort domains/queries before they reach the intent router
- The machine's standard Python 3.11 launcher path is inconsistent, so local verification uses a local Python 3.11 conda environment workaround
