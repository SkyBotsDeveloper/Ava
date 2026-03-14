from ava.memory.bootstrap import initialize_database
from ava.memory.database import build_engine, build_session_factory
from ava.memory.journal import ActionJournalStore
from ava.safety.policy import ConfirmationStatus, ResultStatus


def test_action_journal_records_round_trip(tmp_path) -> None:
    database_path = tmp_path / "ava.db"
    engine = build_engine(database_path)
    initialize_database(engine)
    store = ActionJournalStore(build_session_factory(engine))

    entry_id = store.record_action(
        command_text="Ava, insta kholo",
        action_name="browser_plan",
        confirmation_status=ConfirmationStatus.NOT_NEEDED,
        result_status=ResultStatus.PLANNED,
        source="text",
        details={"browser": "edge"},
    )
    rows = store.list_recent()

    assert entry_id > 0
    assert len(rows) == 1
    assert rows[0].command_text == "Ava, insta kholo"
    assert rows[0].details == {"browser": "edge"}
