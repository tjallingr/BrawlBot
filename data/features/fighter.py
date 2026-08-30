from dataclasses import dataclass, field
from datetime import date

from data.storage.repositories.fights import ROUND_STAT_COLUMNS

# these features stay as rates
RATE_STATS = ("sig_str_landed", "sig_str_att", "td_landed", "td_att", "kd", "sub_att", "ctrl_time_sec")


@dataclass
class FighterHistory:
    fights: int = 0
    wins: int = 0
    ko_wins: int = 0
    sub_wins: int = 0
    rounds: int = 0
    last_fight_date: date | None = None
    totals: dict[str, float] = field(default_factory=lambda: dict.fromkeys(ROUND_STAT_COLUMNS, 0.0))

    def record(self, fight_date: date, won: bool, method: str | None, rounds: int, stats: dict | None) -> None:
        self.fights += 1
        self.wins += int(won)
        self.rounds += rounds
        self.last_fight_date = fight_date
        if won and method:
            self.ko_wins += int("KO" in method)
            self.sub_wins += int("SUB" in method)
        for name, value in (stats or {}).items():
            if value is not None:
                self.totals[name] += value


def fighter_features(history: FighterHistory, fighter, as_of: date) -> dict[str, float | None]:
    """
        returns features of a fighter up until given date, no future fights are considered
    """
    per_round = (lambda name: history.totals[name] / history.rounds) if history.rounds else (lambda name: None)

    features: dict[str, float | None] = {
        "fights": history.fights,
        "wins": history.wins,
        "win_rate": history.wins / history.fights if history.fights else None,
        "ko_win_rate": history.ko_wins / history.wins if history.wins else None,
        "sub_win_rate": history.sub_wins / history.wins if history.wins else None,
        "rounds": history.rounds,
        "avg_rounds": history.rounds / history.fights if history.fights else None,
        "days_since_last": (as_of - history.last_fight_date).days if history.last_fight_date else None,
        "age_years": (as_of - fighter.dob).days / 365.25 if fighter and fighter.dob else None,
        "height_cm": fighter.height_cm if fighter else None,
        "reach_cm": fighter.reach_cm if fighter else None,
        "is_orthodox": float(fighter.stance == "Orthodox") if fighter and fighter.stance else None,
    }
    features |= {f"{name}_pr": per_round(name) for name in RATE_STATS}
    features["sig_str_acc"] = _ratio(history.totals["sig_str_landed"], history.totals["sig_str_att"])
    features["td_acc"] = _ratio(history.totals["td_landed"], history.totals["td_att"])
    return features


def _ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None
