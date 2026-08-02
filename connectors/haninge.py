import re

from playwright.sync_api import Page

HANINGE_LEADERBOARD_URL = (
    "https://www.haningegk.se/tavling#/competition/5624874/leaderboard/5080993"
)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def candidate_names(player_name: str):
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


def find_player_link(page: Page, player_name: str):
    candidates = candidate_names(player_name)
    links = page.locator("a.truncate")

    for i in range(links.count()):
        link = links.nth(i)
        title = normalize(link.get_attribute("title") or "").lower()
        text = normalize(link.inner_text() or "").lower()

        for candidate in candidates:
            if candidate in title or candidate in text:
                return link

    return None


def extract_row_snapshot(row):
    def safe(selector: str) -> str:
        try:
            return normalize(row.locator(selector).first.inner_text())
        except Exception:
            return ""

    return {
        "row_text": normalize(row.inner_text()),
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
    page.goto(HANINGE_LEADERBOARD_URL, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(8000)

    link = find_player_link(page, player_name)
    if not link:
        return None

    row = link.locator("xpath=ancestor::div[contains(@class,'list-row')]")
    if row.count() == 0:
        return None

    return extract_row_snapshot(row)
