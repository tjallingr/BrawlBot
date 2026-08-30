import signal
from collections.abc import Callable
from datetime import datetime, timezone

import click

from data.storage.db import get_engine, get_session
from data.storage.raw_html import save_raw_html
from data.storage.repositories import checkpoints as checkpoint_repo
from data.storage.repositories import events as event_repo
from data.storage.repositories import fighters as fighter_repo
from stages.scrape.bestfightodds.events import discover_ufc_event_urls, parse_event_odds
from stages.scrape.fetch.browser import browser_session
from stages.scrape.fetch.http import fetch as http_fetch
from stages.scrape.fetch.http import make_session
from stages.scrape.ingest import store_event, store_fight_details, store_fight_odds, store_fighter
from stages.scrape.ufcstats import COMPLETED_EVENTS_URL, fight_url, fighter_url
from stages.scrape.ufcstats.events import discover_event_urls, parse_event_page
from stages.scrape.ufcstats.fighters import parse_fighter_page
from stages.scrape.ufcstats.fights import parse_fight_page
from stages.scrape.urls import id_from_url


@click.group()
def cli():
    pass


@cli.command("ufcstats")
@click.option("--limit", type=int, default=None, help="Process at most N new events (for a bounded first run).")
@click.option("--headless/--headed", default=True)
def scrape_ufcstats(limit: int | None, headless: bool):
    stop_requested = _stop_on_interrupt()
    session = get_session(get_engine())

    known_event_ids = event_repo.get_source_ids(session, "ufcstats")
    fighter_ids = fighter_repo.get_ufcstats_ids(session)

    with browser_session(headless=headless) as fetch:
        listing_html = fetch(COMPLETED_EVENTS_URL)
        new_urls = [url for url in discover_event_urls(listing_html) if id_from_url(url) not in known_event_ids]

        for event_url in new_urls[:limit]:
            if stop_requested():
                click.echo("stopped at event boundary; rerun to continue")
                break

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
                raw_html_path = save_raw_html("ufcstats", "fights", fight_id, fight_html)
                store_fight_details(session, fight_row, fight_details, raw_html_path, fighter_ids)

            session.commit()

    checkpoint_repo.mark_run(session, "ufcstats", datetime.now(timezone.utc))
    session.commit()


@cli.command("bestfightodds")
@click.option("--limit", type=int, default=None, help="Process at most N event pages.")
def scrape_bestfightodds(limit: int | None):
    session = get_session(get_engine())
    http_session = make_session()

    home_html = http_fetch(http_session, "https://www.bestfightodds.com/")
    fighter_candidates = fighter_repo.get_normalized_names(session)

    for event_url in discover_ufc_event_urls(home_html)[:limit]:
        click.echo(f"odds event: {event_url}")
        html = http_fetch(http_session, event_url)
        save_raw_html("bestfightodds", "events", id_from_url(event_url), html)
        store_fight_odds(session, parse_event_odds(html), fighter_candidates)

    checkpoint_repo.mark_run(session, "bestfightodds", datetime.now(timezone.utc))
    session.commit()


def _stop_on_interrupt() -> Callable[[], bool]:
    requested = False

    def handle(signum, frame):
        nonlocal requested
        if requested:
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            click.echo("Ctrl+C again to stop immediately, discarding the current event")
            return
        requested = True
        click.echo("finishing the current event, then stopping")

    signal.signal(signal.SIGINT, handle)
    return lambda: requested


def _fighter_ids_in(event_data: dict) -> set[str]:
    fights = event_data["fights"]
    return {f["fighter_a_ufcstats_id"] for f in fights} | {f["fighter_b_ufcstats_id"] for f in fights}


if __name__ == "__main__":
    cli()
