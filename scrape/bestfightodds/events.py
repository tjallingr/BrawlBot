import json

from bs4 import BeautifulSoup

BASE_URL = "https://www.bestfightodds.com"


def discover_ufc_event_urls(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    hrefs = {a["href"] for a in soup.select('a[href^="/events/ufc-"]')}
    return [BASE_URL + href for href in sorted(hrefs)]


def parse_event_odds(html: str) -> list[dict]:
    """Returns one row per (fighter, sportsbook) with the odds shown on the
    event page. For a past event this is the final/closing line -- betting
    is closed by fight time, so there's no separate opening line to recover
    from this page alone."""
    soup = BeautifulSoup(html, "lxml")
    table = next(t for t in soup.select("table.odds-table") if t.get("class") == ["odds-table"])

    sportsbook_by_id = {
        th["data-b"]: th.select_one("a").get_text(strip=True)
        for th in table.select("thead th[data-b]")
        if th.select_one("a")
    }

    odds = []
    fighter_name, fighter_bfo_id = None, None
    for row in table.select("tbody > tr"):
        name_link = row.select_one('th a[href^="/fighters/"]')
        if name_link:
            fighter_name = name_link.select_one("span").get_text(strip=True)
            fighter_bfo_id = name_link["href"].rsplit("-", 1)[-1]

        for cell in row.select("td.but-sg"):
            book_id, _, matchup_id = json.loads(cell["data-li"])
            sportsbook = sportsbook_by_id.get(str(book_id))
            odds_span = cell.select_one("span[id]")
            if not sportsbook or odds_span is None:
                continue
            odds.append(
                {
                    "matchup_id": matchup_id,
                    "fighter_name": fighter_name,
                    "fighter_bfo_id": fighter_bfo_id,
                    "sportsbook": sportsbook,
                    "moneyline": int(odds_span.get_text(strip=True)),
                }
            )
    return odds
