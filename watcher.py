import json
import re
from pathlib import Path

import requests
import yaml
from playwright.sync_api import sync_playwright

HANINGE_LEADERBOARD_URL = (
    "https://www.haningegk.se/tavling#/competition/5624874/leaderboard/5080993"
)

CONFIG_FILE = Path("config.yml")
STATE_FILE = Path("state.json")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def load_config():
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_state():
    if not STATE_FILE.exists():
        return {}

    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_state(state):
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def send_ntfy(topic: str, title: str, message: str):
    url = f"https://ntfy.sh/{topic}"
    resp = requests.post(
        url,
        data=message.encode("utf-8"),
        headers={"Title": title},
        timeout=30,
    )
    resp.raise_for_status()


def display(value: str) -> str:
    value = normalize(value)
    return value if value else "-"


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


def find_player_link(page, player_name: str):
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

    snapshot = {
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
    return snapshot


def fetch_player_snapshot(page, player_name: str):
    page.goto(HANINGE_LEADERBOARD_URL, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(8000)

    link = find_player_link(page, player_name)
    if not link:
        return None

    row = link.locator("xpath=ancestor::div[contains(@class,'list-row')]")
    if row.count() == 0:
        return None

    return extract_row_snapshot(row)


def main():
    config = load_config()
    state = load_state()

    topic = config["ntfy"]["topic"]
    updates = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1200})

        try:
            for watch in config["watches"]:
                competition_id = watch["competition"]
                player_name = watch["player"]
                key = f"{competition_id}::{player_name}"

                current = fetch_player_snapshot(page, player_name)
                if not current:
                    print(f"{player_name}: hittade ingen rad")
                    continue

                previous = state.get(key)

                # Första körningen sparar bara basläget.
                if previous is None:
                    state[key] = current
                    updates.append(f"Baslinje sparad för {player_name}")
                    continue

                if previous != current:
                    message = (
                        f"{display(current['name'])}\n"
                        f"Placering: {display(current['position'])}\n"
                        f"Klubb: {display(current['club'])}\n"
                        f"Till par: {display(current['topar'])}\n"
                        f"Hål: {display(current['hole'])}\n"
                        f"Idag: {display(current['today'])}\n"
                        f"Rond 1: {display(current['r1'])}\n"
                        f"Rond 2: {display(current['r2'])}\n"
                        f"Total: {display(current['total'])}\n"
                    )
                    send_ntfy(topic, f"Golfuppdatering: {player_name}", message)
                    state[key] = current
                    updates.append(f"Uppdaterad: {player_name} -> {current['position']}")

        finally:
            browser.close()

    save_state(state)
    print("\n".join(updates) if updates else "Ingen ändring.")


if __name__ == "__main__":
    main()
