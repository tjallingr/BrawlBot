BASE_URL = "http://www.ufcstats.com"
COMPLETED_EVENTS_URL = f"{BASE_URL}/statistics/events/completed?page=all"


def fighter_url(fighter_id: str) -> str:
    return f"{BASE_URL}/fighter-details/{fighter_id}"


def fight_url(fight_id: str) -> str:
    return f"{BASE_URL}/fight-details/{fight_id}"
