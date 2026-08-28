"""Pre-UFC fight history from sherdog.com fighter profiles.

Stubbed out deliberately: a live check (2026-08-28) showed sherdog.com
sits behind a genuine Cloudflare *managed challenge* (not just a JS puzzle
like ufcstats.com), on both /robots.txt and /events/. A plain Playwright
session is not guaranteed to pass it reliably.

Next steps to pick this back up, roughly in order of effort:
  1. Try Playwright first -- it may just work for this domain even though
     robots.txt/events did not (Cloudflare's challenge decision can vary
     by path and traffic pattern).
  2. If not, a headed (non-headless) browser to solve the challenge once
     manually, saving cookies/storage_state for reuse by later headless runs.
  3. If cookies expire too fast for that to be practical, a paid
     anti-bot-bypass API (e.g. ScraperAPI, ZenRows) is the reliable option,
     at the cost of a per-request fee.

Once fetching works, the fighter-profile page (sherdog.com/fighter/<slug>)
lists a fighter's full cross-org record with an organization tag per fight
(e.g. "Ultimate-Fighting-Championship-2" vs a regional promotion) -- that's
what identifies which rows are pre-UFC.
"""


def fetch_fighter_profile(sherdog_id: str) -> str:
    raise NotImplementedError("sherdog.com fetching is blocked by a Cloudflare managed challenge -- see module docstring")
