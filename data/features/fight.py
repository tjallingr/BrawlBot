def matchup_features(red: dict, blue: dict) -> dict[str, float | None]:
    """
        returns a matchup as a flat row with features in two formats: absolute and deltas
    """
    row: dict[str, float | None] = {}
    row |= {f"r_{name}": value for name, value in red.items()}
    row |= {f"b_{name}": value for name, value in blue.items()}
    row |= {
        f"d_{name}": None if red[name] is None or blue[name] is None else red[name] - blue[name]
        for name in red
    }
    row["r_td_edge"] = _edge(red["td_acc"], blue["td_def"])
    row["b_td_edge"] = _edge(blue["td_acc"], red["td_def"])
    row["r_striking_edge"] = _edge(red["slpm"], blue["sapm"])
    row["b_striking_edge"] = _edge(blue["slpm"], red["sapm"])
    return row


def _edge(offense: float | None, defense: float | None) -> float | None:
    return None if offense is None or defense is None else offense - defense
