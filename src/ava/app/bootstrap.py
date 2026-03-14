from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from ava.app.controller import AvaController
from ava.app.state import AssistantState
from ava.automation.browser import BrowserController
from ava.config.paths import AppPaths, build_app_paths
from ava.config.settings import Settings, load_settings
from ava.intents.router import IntentRouter
from ava.memory.bootstrap import initialize_database
from ava.memory.database import build_engine, build_session_factory
from ava.memory.journal import ActionJournalStore
from ava.safety.policy import SafetyPolicy
from ava.telemetry.logging import configure_logging


@dataclass(slots=True)
class BootstrapContext:
    settings: Settings
    paths: AppPaths
    state: AssistantState
    controller: AvaController


def bootstrap_application(env_file: str | Path | None = ".env") -> BootstrapContext:
    settings = load_settings(env_file=env_file)
    paths = build_app_paths(settings)
    paths.ensure_exists()

    configure_logging(paths=paths, level=settings.log_level, debug=settings.debug)
    logging.getLogger(__name__).info("Starting Ava bootstrap", extra={"event": "bootstrap"})

    engine = build_engine(paths.database_path)
    initialize_database(engine)
    session_factory = build_session_factory(engine)

    state = AssistantState(observation_enabled=settings.observation_enabled)
    controller = AvaController(
        settings=settings,
        state=state,
        intent_router=IntentRouter(),
        safety_policy=SafetyPolicy(),
        journal=ActionJournalStore(session_factory),
        browser_controller=BrowserController(settings),
    )
    return BootstrapContext(settings=settings, paths=paths, state=state, controller=controller)
