import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from playwright.sync_api import sync_playwright

REQUEST_DELAY_SECONDS = 2.0


@contextmanager
def browser_session(headless: bool = True) -> Iterator[Callable[[str], str]]:
    """Yields a fetch(url) -> html callable backed by one browser context.

    ufcstats.com fronts every page with a JS proof-of-work challenge. Loading
    it once in a real browser solves it and the session cookie then covers
    every subsequent page.goto() in this context, so the whole run only pays
    the challenge cost once.
    """
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()

        def fetch(url: str) -> str:
            time.sleep(REQUEST_DELAY_SECONDS)
            page.goto(url, wait_until="networkidle")
            return page.content()

        try:
            yield fetch
        finally:
            browser.close()
