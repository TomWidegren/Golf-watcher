import json
import re
from pathlib import Path

import requests
import yaml
from playwright.sync_api import sync_playwright

from connectors.sgf_ranking import fetch_player_snapshot

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
