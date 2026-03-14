# Ava Architecture

## Runtime model

Ava is a single Windows desktop application with a Python backend and a PySide6/QML shell. The backend owns orchestration, memory, safety, logging, and future automation/voice services. The orb UI is a control surface, not the system of record.

## Core subsystems

- `app`: bootstrap, dependency wiring, and command orchestration
- `ui`: orb shell, tray flow, text fallback, and UI bridge
- `voice`: wake-word, microphone, and playback interfaces
- `live`: Gemini Live session interfaces
- `intents`: shared parsing for text and voice commands
- `automation`: browser/window planning with UIA-first priorities
- `observation`: configurable sampling and privacy rules
- `memory`: SQLite schema, action journal, and future task/context memory
- `safety`: confirmation policy and interruption rules
- `config`: environment loading and runtime paths
- `telemetry`: structured logs and diagnostics

## Browser strategy

1. Detect a suitable live Chrome/Edge session and prefer controlling it.
2. If no live session exists, open the preferred browser profile, defaulting to Microsoft Edge.
3. Use Playwright only when DOM certainty is required and a live-session path is insufficient.

## Safety and interruption model

- All meaningful actions are journaled locally.
- Sensitive operations require confirmation.
- `Stop Ava` and `Cancel` are immediate interruption intents that must stop audio playback and queued automation safely.

## Secrets strategy

- Development: `.env` only.
- Packaging/polish: migrate sensitive secrets/config to Windows Credential Manager or an equivalent secure store.
- Do not store sensitive auth/session data in plain text if it can be avoided.
