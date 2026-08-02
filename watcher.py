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
    tokens = [normalize(part).lower() for part in player_full_name.split() if part]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1200})

        try:
            page.goto(url, wait_until="networkidle", timeout=120000)
            page.wait_for_timeout(5000)

            # Välj Herr klass om dropdown finns
            try:
                page.locator("select").first.select_option(label="Herr klass")
                page.wait_for_timeout(3000)
            except Exception as e:
                print(f"DEBUG: kunde inte välja Herr klass: {e}", flush=True)

            rows = page.locator("tr")
            for i in range(rows.count()):
                row = rows.nth(i)
                row_text = normalize(row.inner_text())
                row_lower = row_text.lower()

                if tokens and all(token in row_lower for token in tokens):
                    cells = [normalize(t) for t in row.locator("th, td").all_inner_texts()]

                    def cell(n: int) -> str:
                        return cells[n] if n < len(cells) else ""

                    snapshot = {
                        "row_text": row_text,
                        "place": cell(0),
                        "delta": cell(1),
                        "name": cell(2),
                        "club": cell(3),
                        "to_par": cell(4),
                        "hole": cell(5),
                        "today": cell(6),
                        "round1": cell(7),
                        "round2": cell(8),
                        "total": cell(9),
                    }
                    return snapshot

            print("DEBUG: Lukas hittades inte i tabellen", flush=True)
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
            message = (
                f"{player_name}\n"
                f"Plats: {current['place']}\n"
                f"Till par: {current['to_par']}\n"
                f"Hål: {current['hole']}\n"
                f"Idag: {current['today']}\n"
                f"Totalt: {current['total']}\n"
            )
            send_ntfy(topic, f"Golfuppdatering: {player_name}", message)
            state[key] = current
            updates.append(f"Uppdaterad: {player_name}")

    save_state(state)
    print("\n".join(updates) if updates else "Ingen ändring.")

if __name__ == "__main__":
    main()
