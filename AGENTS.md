# Ava Repo Instructions

## Scope

This repo builds Ava, a Windows-only, voice-first desktop AI agent with a premium orb UI, local memory, strict safety controls, and a modular Gemini Live integration.

## Non-negotiable product rules

- Voice is primary, but the app must remain usable via text input, push-to-talk, mute, and emergency stop.
- The default browser strategy is live Chrome/Edge session first, then preferred Microsoft Edge profile fallback.
- Windows automation priority is UI Automation first, input simulation second, DOM automation third, visual fallback last.
- Sensitive actions require confirmation.
- Sensitive secrets must not be committed and should move beyond `.env` in packaging phases.

## Engineering rules

- Keep modules swappable across voice, live AI, automation, and memory layers.
- Add tests with every non-trivial behavior change.
- Do not claim functionality works unless it was executed or tested.
- Keep comments concise and only where they improve maintainability.
- Preserve a clean commit history with meaningful milestone commits.
