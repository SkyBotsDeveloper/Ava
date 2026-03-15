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
- Added a dedicated spoken-command normalization layer for fragmented domains, trusted domain correction, query preservation, and ambiguity confirmation prompts
- Hardened the voice runtime so spoken clarification prompts persist across follow-up confirmation turns instead of being cleared on the next manual capture
- Added a spoken YouTube search intent and live browser action path, while keeping sensitive/destructive browser actions confirmation-gated

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
- Live spoken verification now confirms `python dot org kholo` normalizes from fragmented STT (`py tho n.org`) into `python.org kholo` and opens the real default Edge session to `https://python.org/`
- Live spoken verification now confirms `youtube kholo` normalizes from fragmented STT (`YouTube Colo`) into `youtube kholo` and opens `https://www.youtube.com/` in the real default Edge session
- Live spoken verification now confirms `current page ka title batao` still routes through the real command pipeline even when Gemini STT heavily distorts the transcript, and returns the active Edge page title/URL
- Live spoken verification now confirms the ambiguous-domain fallback flow: `hub dot com kholo` prompts `Aap \`github.com\` bol rahe the na?`, and spoken `yes` opens `https://github.com` in the real default Edge session

### Blocked

- Always-on wake testing is blocked until a real openWakeWord model path is configured
- Exact arbitrary spoken URL dictation and longer spoken search queries are still less reliable than text fallback because Gemini STT can distort domains/queries before they reach the intent router
- Exact spoken `github dot com kholo` is still unreliable under live STT because the transcript can collapse to `. com` before the normalizer sees enough signal to recover it
- Longer Hinglish spoken search commands like `YouTube par lofi hip hop playlist search karo` still sometimes fall through to Gemini's conversational reply path instead of Ava's browser command path, even though keyword preservation is improved once STT captures enough of the phrase
- The machine's standard Python 3.11 launcher path is inconsistent, so local verification uses a local Python 3.11 conda environment workaround

## 2026-03-15

### Completed

- Hardened spoken browser-command recovery so browser-like turns stay on Ava's deterministic browser path longer before falling back to general Gemini conversation
- Added model-output recovery for collapsed spoken domains such as `. com` so Ava can ask a safe browser-specific confirmation instead of drifting into chat mode
- Added targeted phrase repair for the observed YouTube search collapse so `YouTube par lofi hip hop playlist search karo` recovers to a browser search confirmation with the full query intact
- Added live verification helper script for spoken-browser command regression checks against Gemini STT and the real Ava runtime
- Added sticky browser-task context in the controller so in-progress YouTube/browser flows can reuse the last query and stay on the browser path across follow-up turns
- Added follow-up browser retry routing in the voice runtime so corrective phrases are intercepted before Gemini chat fallback
- Added explicit follow-up browser logs for task detection, corrective action choice, YouTube search submission, and final browser state observation
- Added collapsed follow-up recovery so a distorted retry utterance that lands as just `search` can still retry the active YouTube search

### Verified

- `ruff check .` passes
- `pytest` passes (`78 passed`)
- Live spoken verification confirms `github dot com kholo` now recovers from collapsed Gemini STT into the browser-specific prompt `Aap \`github.com\` bol rahe the na?`
- Live spoken verification confirms `YouTube par lofi hip hop playlist search karo` now recovers into the browser-specific prompt `Ye search query \`lofi hip hop playlist\` sahi hai na?`
- Browser-command priority is improved in live runs: both target phrases stayed on the browser-command path and produced confirmation prompts instead of falling back to general conversational replies
- Live browser verification confirms a sticky YouTube search task can be retried from a spoken follow-up in the real default Edge session: the follow-up utterance collapsed to `search.`, Ava detected it as a browser follow-up, chose `search_youtube`, submitted `lofi hip hop playlist`, and observed the final Edge URL `https://www.youtube.com/results?search_query=lofi+hip+hop+playlist`

### Blocked

- Automated live confirmation follow-up (`haan` / `yes`) is still flaky in the scripted spoken verification harness, even though the primary phrase recovery is working live
- Arbitrary spoken domains and longer spoken queries outside the explicitly hardened patterns are still less reliable than text fallback because the upstream Gemini STT can drop key tokens before Ava sees them
