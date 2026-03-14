from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_dir

from ava.config.settings import Settings


@dataclass(slots=True)
class AppPaths:
    root: Path
    logs_dir: Path
    cache_dir: Path
    database_path: Path

    def ensure_exists(self) -> None:
        for directory in (self.root, self.logs_dir, self.cache_dir):
            directory.mkdir(parents=True, exist_ok=True)


def build_app_paths(settings: Settings) -> AppPaths:
    root = settings.data_root or Path(user_data_dir(settings.app_name, "SkyBotsDeveloper"))
    return AppPaths(
        root=root,
        logs_dir=root / "logs",
        cache_dir=root / "cache",
        database_path=root / "ava.db",
    )
