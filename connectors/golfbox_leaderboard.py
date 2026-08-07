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


def safe_text(page: Page, selector: str) -> str:
    try:
        locator = page.locator(selector)

        if locator.count() == 0:
            return ""

        return normalize(locator.first.inner_text())
    except Exception:
        return ""


def fetch_player_snapshot(page: Page, player_name: str):
    page.goto(
        LEADERBOARD_URL,
        wait_until="domcontentloaded",
        timeout=120000,
    )

    page.wait_for_timeout(5000)

    if page.get_by_text("Inga resultat ännu", exact=False).count() > 0:
        print(f"{player_name}: inga resultat ännu")
        return None

    candidates = candidate_names(player_name)

    name_cells = page.locator("[id^='list-item-'][id$='-name']")

    for i in range(name_cells.count()):
        name_cell = name_cells.nth(i)

        text = normalize(name_cell.inner_text())
        text_lower = text.lower()

        if not any(candidate in text_lower for candidate in candidates):
            continue

        element_id = name_cell.get_attribute("id") or ""

        match = re.match(
            r"list-item-(.+)-name$",
            element_id,
        )

        if not match:
            continue

        row_id = match.group(1)

        snapshot = {
            "position": safe_text(
                page,
                f"#list-item-{row_id}-position",
            ),
            "name": text,
            "club": safe_text(
                page,
                f"#list-item-{row_id}-club",
            ),
            "topar": safe_text(
                page,
                f"#list-item-{row_id}-topar",
            ),
            "hole": safe_text(
                page,
                f"#list-item-{row_id}-hole",
            ),
            "today": safe_text(
                page,
                f"#list-item-{row_id}-today",
            ),
            "r1": safe_text(
                page,
                f"#list-item-{row_id}-r1",
            ),
            "r2": safe_text(
                page,
                f"#list-item-{row_id}-r2",
            ),
            "total": safe_text(
                page,
                f"#list-item-{row_id}-total",
            ),
        }

        print(
            f"{player_name}: hittade GolfBox-rad {row_id}",
            flush=True,
        )

        return snapshot

    print(f"{player_name}: hittade ingen rad")
    return None
