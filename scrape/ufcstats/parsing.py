def to_int(text: str | None) -> int | None:
    return int(text) if text and text.lstrip("-").isdigit() else None
