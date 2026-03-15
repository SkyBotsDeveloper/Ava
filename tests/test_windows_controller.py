from __future__ import annotations

from pathlib import Path

from ava.automation.windows import WindowController


def test_resolve_fuzzy_relative_path_matches_hyphenated_folder(tmp_path: Path) -> None:
    target = tmp_path / "Ava-Test"
    target.mkdir()

    match = WindowController._resolve_fuzzy_relative_path(
        target_name="test",
        search_roots=(tmp_path,),
    )

    assert match == target


def test_resolve_fuzzy_relative_path_returns_none_for_ambiguous_match(tmp_path: Path) -> None:
    (tmp_path / "Ava-Test").mkdir()
    (tmp_path / "Test-Backup").mkdir()

    match = WindowController._resolve_fuzzy_relative_path(
        target_name="test",
        search_roots=(tmp_path,),
    )

    assert match is None


def test_relative_search_roots_include_local_home_folders() -> None:
    roots = WindowController._relative_search_roots()

    assert Path.home() / "Desktop" in roots
    assert Path.home() / "Downloads" in roots
    assert Path.home() / "Documents" in roots


def test_rank_fuzzy_path_match_prefers_exact_token_match() -> None:
    assert WindowController._rank_fuzzy_path_match("test", "Ava-Test") == 0
    assert WindowController._rank_fuzzy_path_match("test", "tests") == 2
