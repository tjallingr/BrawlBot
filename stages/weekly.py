import json
from pathlib import Path
from statistics import median

import click

from core.name_match import best_fighter_match
from data.storage.db import get_engine, get_session
from data.storage.repositories import fighters as fighter_repo
from stages.run.run import predict_matchup
from stages.scrape.bestfightodds.events import SITEMAP_URL, discover_ufc_event_urls, parse_event_odds
from stages.scrape.cli import scrape_bestfightodds, scrape_ufcstats
from stages.scrape.fetch.browser import browser_session
from stages.scrape.fetch.http import fetch as http_fetch
from stages.scrape.fetch.http import make_session
from stages.scrape.ufcstats import COMPLETED_EVENTS_URL
from stages.scrape.ufcstats.events import discover_upcoming_event_url, parse_event_page

PREDICTIONS_PATH = Path(__file__).resolve().parents[1] / "data" / "upcoming_predictions.json"


def scrape_upcoming_card() -> list[dict]:
    with browser_session(headless=True) as fetch:
        listing_html = fetch(COMPLETED_EVENTS_URL)
        upcoming_url = discover_upcoming_event_url(listing_html)
        if not upcoming_url:
            return []
        return parse_event_page(fetch(upcoming_url), upcoming_url)["fights"]


def fetch_current_odds(fighter_candidates: dict[str, int]) -> dict[int, float]:
    """median moneyline per fighter, read off the most recently posted odds page"""
    http_session = make_session()
    sitemap_xml = http_fetch(http_session, SITEMAP_URL)
    latest_url = discover_ufc_event_urls(sitemap_xml)[-1]
    odds_rows = parse_event_odds(http_fetch(http_session, latest_url))

    moneylines: dict[int, list[float]] = {}
    for row in odds_rows:
        fighter_id = best_fighter_match(row["fighter_name"], fighter_candidates)
        if fighter_id:
            moneylines.setdefault(fighter_id, []).append(row["moneyline"])
    return {fighter_id: median(values) for fighter_id, values in moneylines.items()}


def predict_upcoming_card() -> list[dict]:
    session = get_session(get_engine())
    names = fighter_repo.get_normalized_names(session)
    moneylines = fetch_current_odds(names)

    results = []
    for fight in scrape_upcoming_card():
        a_id = best_fighter_match(fight["fighter_a_name"], names)
        b_id = best_fighter_match(fight["fighter_b_name"], names)
        try:
            name_a, proba_a, name_b, proba_b = predict_matchup(
                fight["fighter_a_name"],
                fight["fighter_b_name"],
                fight["weight_class"],
                moneylines.get(a_id) if a_id else None,
                moneylines.get(b_id) if b_id else None,
            )
        except ValueError as error:
            results.append({"fighter_a": fight["fighter_a_name"], "fighter_b": fight["fighter_b_name"], "error": str(error)})
            continue
        results.append({"fighter_a": name_a, "proba_a": proba_a, "fighter_b": name_b, "proba_b": proba_b})

    PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PREDICTIONS_PATH.write_text(json.dumps(results, indent=2))
    return results


@click.command()
def weekly():
    scrape_ufcstats.callback(limit=None, headless=True)
    scrape_bestfightodds.callback(limit=None)
    for result in predict_upcoming_card():
        if "error" in result:
            click.echo(f"skipping {result['fighter_a']} vs {result['fighter_b']}: {result['error']}")
        else:
            click.echo(f"{result['fighter_a']}: {result['proba_a']:.1%}  vs  {result['fighter_b']}: {result['proba_b']:.1%}")


if __name__ == "__main__":
    weekly()
