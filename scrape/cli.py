from datetime import datetime, timezone

import click
from sqlalchemy import select

from data.storage.db import get_engine, get_session
from data.storage.models import Event, Fighter, ScrapeCheckpoint
from data.storage.raw_html import save_raw_html
from scrape.bestfightodds.events import discover_ufc_event_urls, parse_event_odds
from scrape.fetch.browser import browser_session
from scrape.fetch.http import fetch as http_fetch
from scrape.fetch.http import make_session
from scrape.storage_sync import store_event, store_fight_odds, store_fighter, store_round_stats
from scrape.ufcstats import COMPLETED_EVENTS_URL, fight_url, fighter_url
from scrape.ufcstats.events import discover_event_urls, parse_event_page
from scrape.ufcstats.fighters import parse_fighter_page
from scrape.ufcstats.fights import parse_fight_page
from scrape.urls import id_from_url


@click.group()
def cli():
    pass


@cli.command("ufcstats")
@click.option("--limit", type=int, default=None, help="Process at most N new events (for a bounded first run).")
@click.option("--headless/--headed", default=True)
def scrape_ufcstats(limit: int | None, headless: bool):
    session = get_session(get_engine())

    known_event_ids = {
        row.source_event_id
        for row in session.execute(select(Event.source_event_id).where(Event.source == "ufcstats"))
    }
    fighter_ids = dict(
        session.execute(select(Fighter.ufcstats_id, Fighter.id).where(Fighter.ufcstats_id.is_not(None))).all()
    )

    with browser_session(headless=headless) as fetch:
        listing_html = fetch(COMPLETED_EVENTS_URL)
        new_urls = [url for url in discover_event_urls(listing_html) if id_from_url(url) not in known_event_ids]

        for event_url in new_urls[:limit]:
            click.echo(f"event: {event_url}")
            event_html = fetch(event_url)
            event_data = parse_event_page(event_html, event_url)
            event_data["raw_html_path"] = save_raw_html("ufcstats", "events", event_data["source_event_id"], event_html)

            for fighter_id in _fighter_ids_in(event_data) - fighter_ids.keys():
                fighter_html = fetch(fighter_url(fighter_id))
                fighter_data = parse_fighter_page(fighter_html, fighter_url(fighter_id))
                fighter_data["raw_html_path"] = save_raw_html("ufcstats", "fighters", fighter_id, fighter_html)
                fighter_ids[fighter_id] = store_fighter(session, fighter_data).id

            _, fights = store_event(session, event_data, fighter_ids)

            for fight_row, fight_data in zip(fights, event_data["fights"]):
                fight_id = fight_data["ufcstats_fight_id"]
                fight_html = fetch(fight_url(fight_id))
                fight_details = parse_fight_page(fight_html, fight_url(fight_id))
                fight_row.raw_html_path = save_raw_html("ufcstats", "fights", fight_id, fight_html)
                fight_row.is_title_fight = fight_details["is_title_fight"]
                fight_row.method_detail = fight_details["method_detail"]
                store_round_stats(session, fight_row, fight_details["round_stats"], fighter_ids)

            session.commit()

    session.merge(ScrapeCheckpoint(source="ufcstats", last_run_at=datetime.now(timezone.utc)))
    session.commit()


@cli.command("bestfightodds")
@click.option("--limit", type=int, default=None, help="Process at most N event pages.")
def scrape_bestfightodds(limit: int | None):
    session = get_session(get_engine())
    http_session = make_session()

    home_html = http_fetch(http_session, "https://www.bestfightodds.com/")
    fighter_candidates = dict(session.execute(select(Fighter.name_normalized, Fighter.id)).all())

    for event_url in discover_ufc_event_urls(home_html)[:limit]:
        click.echo(f"odds event: {event_url}")
        html = http_fetch(http_session, event_url)
        save_raw_html("bestfightodds", "events", id_from_url(event_url), html)
        store_fight_odds(session, parse_event_odds(html), fighter_candidates)

    session.merge(ScrapeCheckpoint(source="bestfightodds", last_run_at=datetime.now(timezone.utc)))
    session.commit()


def _fighter_ids_in(event_data: dict) -> set[str]:
    fights = event_data["fights"]
    return {f["fighter_a_ufcstats_id"] for f in fights} | {f["fighter_b_ufcstats_id"] for f in fights}


if __name__ == "__main__":
    cli()
