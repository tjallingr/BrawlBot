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
    return row
