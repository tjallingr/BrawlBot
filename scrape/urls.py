def id_from_url(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]
