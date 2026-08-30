import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

REQUEST_DELAY_SECONDS = 2.0
NAVIGATION_TIMEOUT_MS = 30_000

# ufcstats throttles a long run, gotta throttle
RETRY_BACKOFF_SECONDS = (5, 30, 120, 300)

CONTENT_SELECTOR = ".b-head"


@contextmanager
def browser_session(headless: bool = True) -> Iterator[Callable[[str], str]]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()

        def fetch(url: str) -> str:
            delays = (REQUEST_DELAY_SECONDS, *RETRY_BACKOFF_SECONDS)
            for attempt, delay in enumerate(delays):
                if attempt:
                    print(f"  retry {attempt}/{len(delays) - 1} in {delay:.0f}s: {url}", flush=True)
                time.sleep(delay)
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
                    page.wait_for_selector(CONTENT_SELECTOR, state="attached", timeout=NAVIGATION_TIMEOUT_MS)
                    return page.content()
                except PlaywrightError:
                    if attempt == len(delays) - 1:
                        raise

        try:
            yield fetch
        finally:
            browser.close()
