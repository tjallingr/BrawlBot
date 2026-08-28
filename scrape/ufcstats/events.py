from datetime import datetime

from bs4 import BeautifulSoup

BASE_URL = "http://www.ufcstats.com"
COMPLETED_EVENTS_URL = f"{BASE_URL}/statistics/events/completed?page=all"


def _id_from_url(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def discover_event_urls(listing_html: str) -> list[str]:
    soup = BeautifulSoup(listing_html, "lxml")
    links = soup.select("table.b-statistics__table-events a.b-link")
    return [a["href"] for a in links]


def _fight_row_result(row) -> dict:
    cells = row.select("td")
    fighter_links = cells[1].select("a")
    fighter_ids = [_id_from_url(a["href"]) for a in fighter_links]
    fighter_names = [a.get_text(strip=True) for a in fighter_links]

    flag = cells[0].select_one("a.b-flag")
    won_by_first = flag is not None and "b-flag_style_green" in flag.get("class", [])

    stat_pairs = [[p.get_text(strip=True) for p in cells[i].select("p")] for i in (2, 3, 4, 5)]
    kd, str_, td, sub = stat_pairs

    return {
        "ufcstats_fight_id": _id_from_url(row["data-link"]),
        "fighter_a_ufcstats_id": fighter_ids[0],
        "fighter_a_name": fighter_names[0],
        "fighter_b_ufcstats_id": fighter_ids[1],
        "fighter_b_name": fighter_names[1],
        "winner_ufcstats_id": fighter_ids[0] if won_by_first else None,
        "kd_a": int(kd[0]),
        "kd_b": int(kd[1]),
        "str_a": int(str_[0]),
        "str_b": int(str_[1]),
        "td_a": int(td[0]),
        "td_b": int(td[1]),
        "sub_a": int(sub[0]),
        "sub_b": int(sub[1]),
        "weight_class": cells[6].get_text(strip=True),
        "method": cells[7].select_one("p").get_text(strip=True),
        "round": int(cells[8].get_text(strip=True)),
        "time": cells[9].get_text(strip=True),
    }


def parse_event_page(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")

    date_text = soup.select(".b-list__box-list-item")[0].get_text(strip=True).removeprefix("Date:").strip()
    location = soup.select(".b-list__box-list-item")[1].get_text(strip=True).removeprefix("Location:").strip()

    return {
        "source_event_id": _id_from_url(url),
        "name": soup.select_one(".b-content__title-highlight").get_text(strip=True),
        "date": datetime.strptime(date_text, "%B %d, %Y").date(),
        "location": location,
        "fights": [_fight_row_result(row) for row in soup.select("tbody.b-fight-details__table-body tr")],
    }
