from pathlib import Path

import pytest

from data.storage.db import get_engine, get_session
from data.storage.repositories import fighters as fighter_repo
from data.storage.repositories import fights as fight_repo
from stages.scrape.ingest import store_event, store_fight_details, store_fighter
from stages.scrape.ufcstats.events import parse_event_page
from stages.scrape.ufcstats.fights import parse_fight_page

EXAMPLES = Path(__file__).resolve().parents[1] / "stages" / "scrape" / "examples"


@pytest.fixture
def session(tmp_path):
    return get_session(get_engine(tmp_path / "test.sqlite3"))


def test_event_and_fights_are_stored(session):
    event_data = parse_event_page(
        (EXAMPLES / "ufcstats.html").read_text(encoding="utf-8"),
        "http://x/event-details/a0a69dc9914ef6e1",
    )
    ids = {}
    for fight in event_data["fights"]:
        for key in ("fighter_a_ufcstats_id", "fighter_b_ufcstats_id"):
            source_id = fight[key]
            if source_id not in ids:
                ids[source_id] = store_fighter(
                    session, {"ufcstats_id": source_id, "name_raw": f"Fighter {source_id[:4]}"}
                ).id

    event, fights = store_event(session, event_data, ids)
    session.commit()

    assert event.source_event_id == "a0a69dc9914ef6e1"
    assert len(fights) == len(event_data["fights"])

    main = fights[0]
    assert (main.kd_a, main.kd_b) == (3, 0)
    assert (main.str_a, main.str_b) == (174, 90)
    assert main.method == "U-DEC" and main.round == 5
    assert main.winner_id == main.fighter_a_id
    # the parser's source ids are not columns and must not have been stored
    assert not hasattr(main, "ufcstats_fight_id")


def test_fight_details_and_round_stats_are_stored(session):
    event_data = parse_event_page(
        (EXAMPLES / "ufcstats.html").read_text(encoding="utf-8"),
        "http://x/event-details/a0a69dc9914ef6e1",
    )
    ids = {}
    for fight in event_data["fights"]:
        for key in ("fighter_a_ufcstats_id", "fighter_b_ufcstats_id"):
            source_id = fight[key]
            ids.setdefault(
                source_id,
                store_fighter(session, {"ufcstats_id": source_id, "name_raw": f"F {source_id[:4]}"}).id,
            )
    _, fights = store_event(session, event_data, ids)

    details = parse_fight_page(
        (EXAMPLES / "ufcstats-fight.html").read_text(encoding="utf-8"),
        "http://x/fight-details/fb77b08a90b92d5b",
    )
    store_fight_details(session, fights[0], details, "/tmp/x.html", ids)
    session.commit()

    stored = fight_repo.get_all_round_stats(session)
    assert len(stored) == len(details["round_stats"])
    assert fights[0].method_detail == "Decision - Unanimous"
    assert fights[0].is_title_fight is False
    assert fights[0].raw_html_path == "/tmp/x.html"
    assert all(row.fight_id == fights[0].id for row in stored)


def test_store_fighter_normalizes_the_name(session):
    fighter = store_fighter(session, {"ufcstats_id": "abc123", "name_raw": "Conor  McGregor-Jr."})
    session.commit()
    assert fighter.name_normalized == "conor mcgregorjr"
    assert fighter_repo.get_ufcstats_ids(session) == {"abc123": fighter.id}
