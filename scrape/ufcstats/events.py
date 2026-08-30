from datetime import datetime

from bs4 import BeautifulSoup

from scrape.ufcstats.parsing import to_int
from scrape.urls import id_from_url

UPCOMING_ROW_CLASS = "b-statistics__table-row_type_first"


def discover_event_urls(listing_html: str) -> list[str]:
    soup = BeautifulSoup(listing_html, "lxml")
    urls = []
    for row in soup.select("table.b-statistics__table-events tbody tr"):
        link = row.select_one("a.b-link")
        if link and UPCOMING_ROW_CLASS not in row.get("class", []):
            urls.append(link["href"])
    return urls


def _fight_row_result(row) -> dict:
    cells = row.select("td")
    fighter_links = cells[1].select("a")
    fighter_ids = [id_from_url(a["href"]) for a in fighter_links]
    fighter_names = [a.get_text(strip=True) for a in fighter_links]

    # ufcstats lists the winner first and flags the row green; draws and no-contests
    # use another flag style, which leaves the winner unset.
    flag = cells[0].select_one("a.b-flag")
    won_by_first = flag is not None and "b-flag_style_green" in flag.get("class", [])

    kd, str_, td, sub = [[to_int(p.get_text(strip=True)) for p in cells[i].select("p")] for i in (2, 3, 4, 5)]

    return {
        "ufcstats_fight_id": id_from_url(row["data-link"]),
        "fighter_a_ufcstats_id": fighter_ids[0],
        "fighter_a_name": fighter_names[0],
        "fighter_b_ufcstats_id": fighter_ids[1],
        "fighter_b_name": fighter_names[1],
        "winner_ufcstats_id": fighter_ids[0] if won_by_first else None,
        "kd_a": kd[0],
        "kd_b": kd[1],
        "str_a": str_[0],
        "str_b": str_[1],
        "td_a": td[0],
        "td_b": td[1],
        "sub_a": sub[0],
        "sub_b": sub[1],
        "weight_class": cells[6].get_text(strip=True),
        "method": cells[7].select_one("p").get_text(strip=True),
        "round": to_int(cells[8].get_text(strip=True)),
        "time": cells[9].get_text(strip=True),
    }


def parse_event_page(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    date_item, location_item = soup.select(".b-list__box-list-item")[:2]
    date_text = date_item.get_text(strip=True).removeprefix("Date:").strip()

    return {
        "source_event_id": id_from_url(url),
        "name": soup.select_one(".b-content__title-highlight").get_text(strip=True),
        "date": datetime.strptime(date_text, "%B %d, %Y").date(),
        "location": location_item.get_text(strip=True).removeprefix("Location:").strip(),
        "fights": [_fight_row_result(row) for row in soup.select("tbody.b-fight-details__table-body tr")],
    }
