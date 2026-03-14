# Ava Roadmap

## Phase 1: Foundation

- Initialize git repo and project scaffold
- Add docs, config loading, logging, tests, and pre-commit
- Bootstrap SQLite runtime and action journal
- Create the first runnable desktop shell skeleton

## Phase 2: Orb shell

- Build the floating orb and tray integration
- Add text command fallback, mute control, and cancel control
- Surface state transitions for idle, listening, thinking, and speaking

## Phase 3: Voice and Gemini Live

- Add `openWakeWord`-based local wake detection
- Add push-to-talk capture path
- Integrate Gemini Live with a swappable model layer
- Wire interruption-safe audio input/output and Hinglish response style

## Phase 4: Windows and browser control MVP

- UI Automation-first control paths
- Live browser session targeting for Chrome/Edge
- Safe website opening, browser search/navigation, and basic file/window actions

## Phase 5: Local memory

- Conversation history
- Action history
- Task context and preferences
- Workflow repetition signals

## Phase 6: Observation mode

- Configurable, privacy-aware observation engine
- Suggestion-only focus and workflow hints

## Phase 7: Guided task flows

- Messaging flows with ambiguity handling and confirmation
- Safer multi-step social/web tasks

## Phase 8: Polish and packaging

- Voice quality and interaction tuning
- Reliability work
- Windows packaging and secure secret storage migration plan
