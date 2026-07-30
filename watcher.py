import requests
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

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
    url = f"https://ntfy.sh/{urllib.parse.quote(topic)}"
    data = message.encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Title": title},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()


def fetch_leaderboard_json(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "User-Agent": "Mozilla/5.0",
        },
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        event_name = None
        data_lines = []

        for raw_line in resp:
            line = raw_line.decode("utf-8", errors="ignore").strip()

            if line == "":
                if event_name == "leaderboard" and data_lines:
                    payload = "\n".join(data_lines).strip()
                    return json.loads(payload)

                event_name = None
                data_lines = []
                continue

            if line.startswith("event:"):
                event_name = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:"):].strip())

    return None


def extract_player_snapshot(data: dict, player_full_name: str):
    parts = player_full_name.strip().split(None, 1)
    if len(parts) != 2:
        raise ValueError(f"Expected 'First Last' format, got: {player_full_name}")

    first_name, last_name = parts[0], parts[1]

    for leaderboard in data.get("leaderboards", []):
        classes = leaderboard.get("Classes", [])
        class_name = classes[0].get("Name", "") if classes else ""

        for entry in leaderboard.get("LeaderboardEntries", []):
            player = entry.get("Player", {})
            if (
                player.get("FirstName", "").strip() == first_name
                and player.get("LastName", "").strip() == last_name
            ):
                return {
                    "class": class_name,
                    "position": entry.get("Position", {}).get("Text", ""),
                    "score": entry.get("ScoreSum"),
                    "to_par": entry.get("ScoringToPar", {}).get("ToPar", {}).get("Text", ""),
                    "played_holes": entry.get("PlayedHoles"),
                    "scoring_status": entry.get("ScoringStatus"),
                    "entry_id": entry.get("EntryID"),
                }

    return None


def main():
    config = load_config()
    state = load_state()
    updates = []

    topic = config["ntfy"]["topic"]

    for watch in config["watches"]:
        name = watch["name"]
        url = watch["url"]
        player = watch["player"]
        key = f"{name}::{player}::{url}"

        data = fetch_leaderboard_json(url)
        if not data:
            updates.append(f"{name}: kunde inte läsa leaderboard-data")
            continue

        current = extract_player_snapshot(data, player)
        if not current:
            updates.append(f"{name}: hittade ingen rad för {player}")
            continue

        previous = state.get(key)

        if previous != current:
            message = (
                f"{player}\n"
                f"Placering: {current['position']}\n"
                f"Score: {current['score']} ({current['to_par']})\n"
                f"Hål spelade: {current['played_holes']}\n"
                f"Klass: {current['class']}\n\n"
                f"{url}"
            )
            send_ntfy(topic, f"Golfuppdatering: {player}", message)
            state[key] = current
            updates.append(f"Uppdaterad: {player} -> {current['position']}")

    save_state(state)
    print("\n".join(updates) if updates else "Ingen ändring.")


if __name__ == "__main__":
    main()
