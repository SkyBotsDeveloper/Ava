from __future__ import annotations

from ava.config.settings import Settings


class ObservationEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def sampling_seconds(self) -> float:
        return self.settings.observation_sampling_seconds

    def should_observe_process(self, process_name: str) -> bool:
        normalized = process_name.lower()
        return not any(token in normalized for token in self.settings.observation_private_processes)
