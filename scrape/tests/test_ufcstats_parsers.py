from datetime import date
from pathlib import Path

from scrape.ufcstats.events import discover_event_urls, parse_event_page
from scrape.ufcstats.fights import parse_fight_page

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "scrape" / "examples"


def test_parse_event_page():
    html = (EXAMPLES_DIR / "ufcstats.html").read_text(encoding="utf-8")
    event = parse_event_page(html, "http://www.ufcstats.com/event-details/a0a69dc9914ef6e1")

    assert event["source_event_id"] == "a0a69dc9914ef6e1"
    assert event["date"] == date(2026, 8, 22)
    assert event["location"] == "Sacramento, California, USA"

    main_event = event["fights"][0]
    assert main_event["ufcstats_fight_id"] == "fb77b08a90b92d5b"
    assert main_event["fighter_a_name"] == "Gregory Rodrigues"
    assert main_event["fighter_b_name"] == "Anthony Hernandez"
    assert main_event["winner_ufcstats_id"] == main_event["fighter_a_ufcstats_id"]
    assert (main_event["kd_a"], main_event["kd_b"]) == (3, 0)
    assert (main_event["str_a"], main_event["str_b"]) == (174, 90)
    assert (main_event["td_a"], main_event["td_b"]) == (0, 3)
    assert main_event["weight_class"] == "Middleweight"
    assert main_event["method"] == "U-DEC"
    assert main_event["round"] == 5
    assert main_event["time"] == "5:00"


def test_parse_fight_page():
    html = (EXAMPLES_DIR / "ufcstats-fight.html").read_text(encoding="utf-8")
    fight = parse_fight_page(html, "http://www.ufcstats.com/fight-details/fb77b08a90b92d5b")

    assert fight["ufcstats_fight_id"] == "fb77b08a90b92d5b"
    assert fight["is_title_fight"] is False
    assert fight["method_detail"] == "Decision - Unanimous"
    assert len(fight["round_stats"]) == 10
    assert {r["round"] for r in fight["round_stats"]} == {1, 2, 3, 4, 5}

    round_1 = {r["fighter_ufcstats_id"]: r for r in fight["round_stats"] if r["round"] == 1}
    hernandez, rodrigues = round_1["093e1f5bb73850be"], round_1["d1c65d2cf2925ddd"]
    assert (hernandez["sig_str_landed"], hernandez["sig_str_att"]) == (10, 19)
    assert (rodrigues["sig_str_landed"], rodrigues["sig_str_att"]) == (25, 33)

    totals_round = {r["fighter_ufcstats_id"]: r for r in fight["round_stats"] if r["round"] == 5}
    assert totals_round["093e1f5bb73850be"]["ctrl_time_sec"] is not None


def test_discover_event_urls_skips_upcoming_event():
    listing = """
    <table class="b-statistics__table-events"><tbody>
      <tr class="b-statistics__table-row"><td></td></tr>
      <tr class="b-statistics__table-row_type_first">
        <td><a class="b-link" href="http://www.ufcstats.com/event-details/upcoming">Upcoming</a></td>
      </tr>
      <tr class="b-statistics__table-row">
        <td><a class="b-link" href="http://www.ufcstats.com/event-details/completed">Completed</a></td>
      </tr>
    </tbody></table>
    """
    assert discover_event_urls(listing) == ["http://www.ufcstats.com/event-details/completed"]
