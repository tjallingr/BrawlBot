from bs4 import BeautifulSoup

from stages.scrape.ufcstats.parsing import to_int
from stages.scrape.urls import id_from_url

TOTALS_STATS = ["kd", "sig_str", "sig_str_pct", "total_str", "td", "td_pct", "sub_att", "rev", "ctrl"]
SIG_STR_STATS = ["sig_str", "sig_str_pct", "head", "body", "leg", "distance", "clinch", "ground"]


def _cell_texts(td) -> list[str]:
    return [p.get_text(strip=True) for p in td.select("p")]


def _split_landed_of_att(text: str | None) -> tuple[int | None, int | None]:
    if not text or " of " not in text:
        return None, None
    landed, attempted = text.split(" of ")
    return int(landed), int(attempted)


def _ctrl_to_seconds(text: str | None) -> int | None:
    if not text or ":" not in text:
        return None
    minutes, seconds = text.split(":")
    return int(minutes) * 60 + int(seconds)


def _iter_round_stats(table, stat_names: list[str]):
    round_tbodies = table.find_all("tbody")[1:]
    for round_num, tbody in enumerate(round_tbodies, start=1):
        cells = tbody.select_one("tr").select("td")
        stat_columns = [_cell_texts(cell) for cell in cells[1:]]
        for fighter_idx in (0, 1):
            stats = {name: column[fighter_idx] for name, column in zip(stat_names, stat_columns)}
            yield round_num, fighter_idx, stats


def parse_fight_page(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    fighter_ids = [id_from_url(a["href"]) for a in soup.select(".b-fight-details__person-link")]

    # An unscored fight's page carries no stats tables at all, only the result.
    tables = soup.select("table")
    stats_by_round_fighter: dict[tuple[int, int], dict] = {}
    if len(tables) > 3:
        for round_num, fighter_idx, stats in _iter_round_stats(tables[1], TOTALS_STATS):
            stats_by_round_fighter[(round_num, fighter_idx)] = stats
        for round_num, fighter_idx, stats in _iter_round_stats(tables[3], SIG_STR_STATS):
            stats_by_round_fighter[(round_num, fighter_idx)].update(stats)

    round_stats = []
    for (round_num, fighter_idx), stats in sorted(stats_by_round_fighter.items()):
        sig_str_landed, sig_str_att = _split_landed_of_att(stats.get("sig_str"))
        total_str_landed, total_str_att = _split_landed_of_att(stats.get("total_str"))
        td_landed, td_att = _split_landed_of_att(stats.get("td"))
        round_stats.append(
            {
                "round": round_num,
                "fighter_ufcstats_id": fighter_ids[fighter_idx],
                "kd": to_int(stats.get("kd")),
                "sig_str_landed": sig_str_landed,
                "sig_str_att": sig_str_att,
                "total_str_landed": total_str_landed,
                "total_str_att": total_str_att,
                "td_landed": td_landed,
                "td_att": td_att,
                "sub_att": to_int(stats.get("sub_att")),
                "rev": to_int(stats.get("rev")),
                "ctrl_time_sec": _ctrl_to_seconds(stats.get("ctrl")),
                "sig_str_head": _split_landed_of_att(stats.get("head"))[0],
                "sig_str_body": _split_landed_of_att(stats.get("body"))[0],
                "sig_str_leg": _split_landed_of_att(stats.get("leg"))[0],
                "sig_str_distance": _split_landed_of_att(stats.get("distance"))[0],
                "sig_str_clinch": _split_landed_of_att(stats.get("clinch"))[0],
                "sig_str_ground": _split_landed_of_att(stats.get("ground"))[0],
            }
        )

    fight_title = soup.select_one(".b-fight-details__fight-title").get_text(strip=True)
    method_label = soup.find("i", class_="b-fight-details__label", string=lambda s: s and "Method" in s)
    method_value = method_label.find_next_sibling("i") if method_label else None

    return {
        "ufcstats_fight_id": id_from_url(url),
        "is_title_fight": "title" in fight_title.lower(),
        "method_detail": method_value.get_text(strip=True) if method_value else None,
        "round_stats": round_stats,
    }
