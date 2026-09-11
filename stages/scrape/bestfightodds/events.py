import json
import re
from datetime import datetime

from bs4 import BeautifulSoup

SITEMAP_URL = "https://www.bestfightodds.com/sitemap-events.xml"
DATE_HINT_PATTERN = re.compile(r"for (\w+) (\d{1,2})\b")

# a real event page's slug has a descriptive part between "ufc-" and its
# trailing id (ufc-271-2338, ufc-260-miocic-vs-ngannou-2-2055). A bare
# "ufc-<digits>" slug is a different kind of page entirely -- checked several:
# titled just "UFC for <date>", and every fighter on it listed 2-4 times, which
# means it's some rolling/speculative listing, not a real settled event. It
# duplicates fights already covered correctly by their real, named pages.
BARE_SLUG_PATTERN = re.compile(r"/events/ufc-\d+$")

# the trailing id in every event url increases with time (an internal db key,
# not a UFC event number) -- checked across eras: id 1909 (UFC 250, 2020) has
# no odds, id 2055 (UFC 260, 2021) does. min_id sits safely below that boundary
# so nothing real gets excluded, at the cost of a few empty requests near it.
MIN_TRACKED_EVENT_ID = 1900


def discover_ufc_event_urls(sitemap_xml: str, min_id: int = MIN_TRACKED_EVENT_ID) -> list[str]:
    soup = BeautifulSoup(sitemap_xml, "xml")
    urls = {loc.get_text(strip=True) for loc in soup.select("loc")}
    ufc_urls = [url for url in urls if "/events/ufc-" in url and not BARE_SLUG_PATTERN.search(url)]
    recent = [url for url in ufc_urls if url.rsplit("-", 1)[-1].isdigit() and int(url.rsplit("-", 1)[-1]) >= min_id]
    return sorted(recent)


def parse_event_date_hint(html: str) -> tuple[int, int] | None:
    # historical event pages title themselves "... for July 10" (no year --
    # the year isn't needed: it's only used to tell apart which of several
    # meetings between the same two fighters a rematch's odds belong to, and
    # our fights table's own event dates give the year). Current/upcoming
    # pages don't carry this suffix, which is fine: a fighter's first-ever
    # meeting has nothing to disambiguate.
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
    # some events, mostly pre-2009 ones, have a page but no odds data at all --
    # sportsbooks weren't tracked that far back on this site
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
