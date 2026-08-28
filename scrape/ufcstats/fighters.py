import re
from datetime import datetime

from bs4 import BeautifulSoup

# Field layout is the well-documented ufcstats.com fighter-details structure
# (stable across every public scraper), but -- unlike the event/fight pages --
# no saved example exists for this one. Verify against a live page first.


def _id_from_url(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def _box_item_text(soup: BeautifulSoup, label: str) -> str | None:
    label_tag = soup.find("i", class_="b-list__box-item-title", string=lambda s: s and label in s)
    if not label_tag:
        return None
    text = label_tag.parent.get_text(" ", strip=True).removeprefix(label).strip()
    return text or None


def _height_to_cm(text: str | None) -> float | None:
    match = re.match(r"(\d+)'\s*(\d+)", text or "")
    if not match:
        return None
    feet, inches = int(match.group(1)), int(match.group(2))
    return round((feet * 12 + inches) * 2.54, 1)


def _reach_to_cm(text: str | None) -> float | None:
    match = re.match(r"(\d+)", text or "")
    return round(int(match.group(1)) * 2.54, 1) if match else None


def _parse_dob(text: str | None):
    if not text or text == "--":
        return None
    return datetime.strptime(text, "%b %d, %Y").date()


def parse_fighter_page(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    name = soup.select_one(".b-content__title-highlight").get_text(strip=True)
    stance = _box_item_text(soup, "STANCE:")

    return {
        "ufcstats_id": _id_from_url(url),
        "name_raw": name,
        "dob": _parse_dob(_box_item_text(soup, "DOB:")),
        "height_cm": _height_to_cm(_box_item_text(soup, "Height:")),
        "reach_cm": _reach_to_cm(_box_item_text(soup, "Reach:")),
        "stance": stance if stance and stance != "--" else None,
    }
