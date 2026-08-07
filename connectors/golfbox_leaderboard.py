import os
import re
from typing import List

from playwright.sync_api import Page

DEFAULT_LEADERBOARD_URL = (
    "https://strangnasgk.se/tavling/tavlingskalender/#/competition/5324636/leaderboard/4844005"
)
LEADERBOARD_URL = os.getenv("GOLFBOX_LEADERBOARD_URL", DEFAULT_LEADERBOARD_URL)


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
                f"{last.upper()}, {first.capitalize()}",
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


def row_matches_player(row, candidates: List[str]) -> bool:
    try:
        row_text = normalize(row.inner_text()).lower()
    except Exception:
        row_text = ""

    for candidate in candidates:
        if candidate in row_text:
            return True

    links = row.locator("a.truncate")
    for i in range(links.count()):
        link = links.nth(i)
        title = normalize(link.get_attribute("title") or "").lower()
        text = normalize(link.inner_text() or "").lower()
        for candidate in candidates:
            if candidate in title or candidate in text:
                return True

    return False


def extract_row_snapshot(row):
    def safe(selector: str) -> str:
        try:
            return normalize(row.locator(selector).first.inner_text())
        except Exception:
            return ""

    return {
        "position": safe("[id$='-position']"),
        "name": safe("[id$='-name']"),
        "club": safe("[id$='-club']"),
        "topar": safe("[id$='-topar']"),
        "hole": safe("[id$='-hole']"),
        "today": safe("[id$='-today']"),
        "r1": safe("[id$='-r1']"),
        "r2": safe("[id$='-r2']"),
        "total": safe("[id$='-total']"),
    }


def fetch_player_snapshot(page: Page, player_name: str):
    page.goto(LEADERBOARD_URL, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(3000)

    if page.get_by_text("Inga resultat ännu", exact=False).count() > 0:
        print(f"{player_name}: inga resultat ännu")
        return None

    candidates = candidate_names(player_name)

    rows = page.locator("div[id^='list-item-']")
    for i in range(rows.count()):
        row = rows.nth(i)

        try:
            row_text = normalize(row.inner_text())
        except Exception:
            continue

        if not row_text:
            continue

        if "inga resultat ännu" in row_text.lower():
            return None

        if row.locator("[id$='-position']").count() == 0:
            continue

        if not row_matches_player(row, candidates):
            continue

        snapshot = extract_row_snapshot(row)
        if not snapshot["name"]:
            continue

        return snapshot

    print(f"{player_name}: hittade ingen rad")
    return None
