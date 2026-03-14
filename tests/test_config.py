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


def test_empty_wakeword_env_value_loads_as_empty_tuple(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("AVA_WAKEWORD_MODEL_PATHS=\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.wakeword_model_paths == ()
