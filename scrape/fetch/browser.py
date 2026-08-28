import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

REQUEST_DELAY_SECONDS = 1.0
NAVIGATION_TIMEOUT_MS = 30_000
MAX_ATTEMPTS = 3

CONTENT_SELECTOR = ".b-head"


@contextmanager
def browser_session(headless: bool = True) -> Iterator[Callable[[str], str]]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()

        def fetch(url: str) -> str:
            for attempt in range(MAX_ATTEMPTS):
                time.sleep(REQUEST_DELAY_SECONDS * (attempt + 1))
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
                    page.wait_for_selector(CONTENT_SELECTOR, timeout=NAVIGATION_TIMEOUT_MS)
                    return page.content()
                except PlaywrightError:
                    if attempt == MAX_ATTEMPTS - 1:
                        raise

        try:
            yield fetch
        finally:
            browser.close()
