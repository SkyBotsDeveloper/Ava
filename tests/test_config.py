from ava.config.paths import build_app_paths
from ava.config.settings import Settings


def test_settings_default_browser_fallback() -> None:
    settings = Settings(_env_file=None)

    assert settings.preferred_browser == "edge"
    assert settings.browser_live_session_first is True
    assert settings.launch_edge_when_browser_missing is True


def test_app_paths_use_custom_root(tmp_path) -> None:
    settings = Settings(_env_file=None, data_root=tmp_path)
    paths = build_app_paths(settings)
    paths.ensure_exists()

    assert paths.root == tmp_path
    assert paths.logs_dir.exists()
    assert paths.database_path.parent.exists()
