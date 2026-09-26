import json
import re
from datetime import datetime

from bs4 import BeautifulSoup

SITEMAP_URL = "https://www.bestfightodds.com/sitemap-events.xml"
DATE_HINT_PATTERN = re.compile(r"for (\w+) (\d{1,2})\b")

BARE_SLUG_PATTERN = re.compile(r"/events/ufc-\d+$")

MIN_TRACKED_EVENT_ID = 1900


def _event_id(url: str) -> int | None:
    trailing = url.rsplit("-", 1)[-1]
    return int(trailing) if trailing.isdigit() else None


def discover_ufc_event_urls(sitemap_xml: str, min_id: int = MIN_TRACKED_EVENT_ID) -> list[str]:
    soup = BeautifulSoup(sitemap_xml, "xml")
    urls = {loc.get_text(strip=True) for loc in soup.select("loc")}
    ufc_urls = [url for url in urls if "/events/ufc-" in url and not BARE_SLUG_PATTERN.search(url)]
    recent = [url for url in ufc_urls if _event_id(url) is not None and _event_id(url) >= min_id]
    return sorted(recent, key=_event_id)


def parse_event_date_hint(html: str) -> tuple[int, int] | None:
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text() if soup.title else ""
    match = DATE_HINT_PATTERN.search(title)
    if not match:
        return None
    try:
        parsed = datetime.strptime(match.group(1), "%B")
    except ValueError:
        return None
    return parsed.month, int(match.group(2))


def parse_event_odds(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    table = next((t for t in soup.select("table.odds-table") if t.get("class") == ["odds-table"]), None)
    if table is None:
        return []

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
