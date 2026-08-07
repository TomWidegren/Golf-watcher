import os
import re
from typing import List

from playwright.sync_api import Page

DEFAULT_LEADERBOARD_URL = (
    "https://strangnasgk.se/tavling/tavlingskalender/"
    "#/competition/5324636/leaderboard/4844005"
)

LEADERBOARD_URL = os.getenv(
    "GOLFBOX_LEADERBOARD_URL",
    DEFAULT_LEADERBOARD_URL,
)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def candidate_names(player_name: str) -> List[str]:
    full = normalize(player_name)
    parts = full.split()

    candidates = [full]

    if len(parts) >= 2:
        first = parts[0]
        last = parts[-1]

        candidates.extend(
            [
                f"{last}, {first}",
                f"{last.upper()}, {first}",
                f"{last.upper()}, {first.upper()}",
            ]
        )

    seen = set()
    result = []

    for item in candidates:
        item = normalize(item).lower()

        if item and item not in seen:
            seen.add(item)
            result.append(item)

    return result


def fetch_player_snapshot(page: Page, player_name: str):
    page.goto(
        LEADERBOARD_URL,
        wait_until="domcontentloaded",
        timeout=120000,
    )

    page.wait_for_timeout(5000)

    print("=== GOLFBOX DEBUG ===", flush=True)
    print(f"URL: {page.url}", flush=True)
    print(
        f"Player candidates: {candidate_names(player_name)}",
        flush=True,
    )

    # Leta brett efter element vars synliga text innehåller efternamnet.
    last_name = normalize(player_name).split()[-1]

    matches = page.get_by_text(
        re.compile(re.escape(last_name), re.IGNORECASE)
    )

    print(
        f"Elements containing '{last_name}': {matches.count()}",
        flush=True,
    )

    for i in range(matches.count()):
        element = matches.nth(i)

        try:
            print(f"=== MATCH {i} ===", flush=True)
            print(
                "TAG:",
                element.evaluate("e => e.tagName"),
                flush=True,
            )
            print(
                "TEXT:",
                repr(normalize(element.inner_text())),
                flush=True,
            )
            print(
                "HTML:",
                element.evaluate("e => e.outerHTML"),
                flush=True,
            )

            # Visa även närmaste tänkbara rad/container.
            print(
                "PARENT HTML:",
                element.evaluate(
                    "e => e.parentElement ? "
                    "e.parentElement.outerHTML : ''"
                ),
                flush=True,
            )

        except Exception as exc:
            print(
                f"Kunde inte läsa MATCH {i}: {exc}",
                flush=True,
            )

    print("=== END GOLFBOX DEBUG ===", flush=True)

    return None
