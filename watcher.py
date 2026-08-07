import json
import re
from pathlib import Path

import requests
import yaml
from playwright.sync_api import sync_playwright

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


def display(value) -> str:
    value = normalize("" if value is None else str(value))
    return value if value else "-"


def get_fetcher(connector_name: str):
    if connector_name == "golfbox_leaderboard":
        from connectors.golfbox_leaderboard import fetch_player_snapshot as fetcher
        return fetcher

    if connector_name == "sgf_ranking":
        from connectors.sgf_ranking import fetch_player_snapshot as fetcher
        return fetcher

    raise ValueError(f"Unknown connector: {connector_name}")


def snapshot_for(fields: dict) -> str:
    return json.dumps(fields, ensure_ascii=False, sort_keys=True)


def format_message(fields: dict, player_name: str) -> str:
    if "points" in fields:
        return (
            f"{display(fields.get('name', player_name))}\n"
            f"Placering: {display(fields.get('position'))}\n"
            f"Födelseår: {display(fields.get('birth_year'))}\n"
            f"Klubb: {display(fields.get('club'))}\n"
            f"Distrikt: {display(fields.get('district'))}\n"
            f"Status: {display(fields.get('status'))}\n"
            f"Poäng: {display(fields.get('points'))}\n"
            f"Tävlingar: {display(fields.get('competitions'))}\n"
        )

    return (
        f"{display(fields.get('name', player_name))}\n"
        f"Placering: {display(fields.get('position'))}\n"
        f"Klubb: {display(fields.get('club'))}\n"
        f"Till par: {display(fields.get('topar'))}\n"
        f"Hål: {display(fields.get('hole'))}\n"
        f"Idag: {display(fields.get('today'))}\n"
        f"Rond 1: {display(fields.get('r1'))}\n"
        f"Rond 2: {display(fields.get('r2'))}\n"
        f"Total: {display(fields.get('total'))}\n"
    )


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
                connector_name = watch.get("connector", "sgf_ranking")
                watch_mode = watch.get("mode", "daily")
                competition_id = watch.get("competition", "")
                player_name = watch["player"]
                key = f"{connector_name}::{competition_id}::{player_name}"

                fetch_player_snapshot = get_fetcher(connector_name)
                current_fields = fetch_player_snapshot(page, player_name)

                if not current_fields:
                    print(f"{player_name}: hittade ingen rad")
                    continue

                current_snapshot = snapshot_for(current_fields)

                previous = state.get(key)
                if isinstance(previous, dict):
                    previous_snapshot = previous.get("snapshot")
                    if previous_snapshot is None:
                        previous_snapshot = snapshot_for(previous)
                else:
                    previous_snapshot = None

                if previous is None:
                    state[key] = {"snapshot": current_snapshot, "fields": current_fields}

                    if watch_mode == "live":
                        message = format_message(current_fields, player_name)
                        send_ntfy(topic, f"Golfuppdatering: {player_name}", message)
                        updates.append(f"Första live-resultat notifierat för {player_name}")
                    else:
                        updates.append(f"Baslinje sparad för {player_name}")

                    continue

                if previous_snapshot != current_snapshot:
                    message = format_message(current_fields, player_name)
                    send_ntfy(topic, f"Golfuppdatering: {player_name}", message)
                    state[key] = {"snapshot": current_snapshot, "fields": current_fields}
                    updates.append(f"Uppdaterad: {player_name}")

        finally:
            browser.close()

    save_state(state)
    print("\n".join(updates) if updates else "Ingen ändring.")


if __name__ == "__main__":
    main()
