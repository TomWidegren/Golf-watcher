import json
import re
from pathlib import Path

import requests
import yaml

from playwright.sync_api import sync_playwright

HANINGE_LEADERBOARD_URL = "https://www.haningegk.se/tavling#/competition/5624874/leaderboard/5080993"

CONFIG_FILE = Path("config.yml")
STATE_FILE = Path("state.json")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def load_config():
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_state():
    if STATE_FILE.exists():
        with STATE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
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

def fetch_player_snapshot(url: str, player_full_name: str):
    targets = [
        normalize(player_full_name).lower(),
        "widegren, lukas",
        "lukas widegren",
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1200})

        try:
            page.goto(url, wait_until="networkidle", timeout=120000)

            # Försök hitta raden direkt först
            def search_now():
                text = normalize(page.locator("body").inner_text()).lower()
                return any(target in text for target in targets), text

            found, text = search_now()
            if found:
                idx = next(text.index(t) for t in targets if t in text)
                return {"row_text": normalize(page.locator("body").inner_text()[max(0, idx - 200): idx + 500])}

            # Scrolla ned lite i taget och sök igen
            for _ in range(12):
                page.mouse.wheel(0, 1200)
                page.wait_for_timeout(1500)

                found, text = search_now()
                if found:
                    idx = next(text.index(t) for t in targets if t in text)
                    return {"row_text": normalize(page.locator("body").inner_text()[max(0, idx - 200): idx + 500])}

            print("DEBUG: Lukas hittades inte efter scroll")
            print(page.locator("body").inner_text()[:4000])
            return None
        finally:
            browser.close()


def main():
    config = load_config()
    state = load_state()

    topic = config["ntfy"]["topic"]
    updates = []

    for watch in config["watches"]:
        competition_id = watch["competition"]
        player_name = watch["player"]
        key = f"{competition_id}::{player_name}"

        leaderboard_url = watch.get("leaderboard_url", HANINGE_LEADERBOARD_URL)
        current = fetch_player_snapshot(leaderboard_url, player_name)
        if not current:
            print(f"{player_name}: hittade ingen rad")
            continue

        previous = state.get(key)

        if previous is None:
            state[key] = current
            updates.append(f"Baslinje sparad för {player_name}")
            continue

        if previous != current:
            message = f"{player_name}\n{current['row_text']}\n"
            send_ntfy(topic, f"Golfuppdatering: {player_name}", message)
            state[key] = current
            updates.append(f"Uppdaterad: {player_name}")

    save_state(state)
    print("\n".join(updates) if updates else "Ingen ändring.")
