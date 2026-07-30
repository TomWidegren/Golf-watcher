import json
import re
from pathlib import Path

import requests
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
    url = f"https://ntfy.sh/{topic}"
    resp = requests.post(
        url,
        data=message.encode("utf-8"),
        headers={"Title": title},
        timeout=30,
    )
    resp.raise_for_status()


def fetch_leaderboard_json(competition_id: int):
    url = f"https://tournytt.se/api/leaderboard/stream?competitions={competition_id}"

    resp = requests.get(
        url,
        headers={
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "User-Agent": "Mozilla/5.0",
        },
        stream=True,
        timeout=60,
    )
    resp.raise_for_status()

    event_name = None
    data_lines = []

    for raw_line in resp.iter_lines(decode_unicode=True):
        if raw_line is None:
            continue

        line = raw_line.strip()

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
    parts = player_full_name.strip().split(maxsplit=1)
    if len(parts) != 2:
        raise ValueError("player must be in 'First Last' format")

    first_name, last_name = parts

    for leaderboard in data.get("leaderboards", []):
        classes = leaderboard.get("Classes", [])
        class_name = classes[0].get("Name", "") if classes else ""

        for entry in leaderboard.get("LeaderboardEntries", []):
            player = entry.get("Player", {})
            if (
                normalize(player.get("FirstName", "")) == first_name
                and normalize(player.get("LastName", "")) == last_name
            ):
                return {
                    "class": class_name,
                    "position": entry.get("Position", {}).get("Text", ""),
                    "score": entry.get("ScoreSum"),
                    "to_par": entry.get("ScoringToPar", {}).get("ToPar", {}).get("Text", ""),
                    "played_holes": entry.get("PlayedHoles"),
                    "status": entry.get("ScoringStatus"),
                }

    return None


def main():
    config = load_config()
    state = load_state()

    topic = config["ntfy"]["topic"]
    updates = []

    for watch in config["watches"]:
        competition_id = watch["competition"]
        player_name = watch["player"]
        key = f"{competition_id}::{player_name}"

        data = fetch_leaderboard_json(competition_id)
        if not data:
            print(f"{player_name}: kunde inte läsa leaderboard-data")
            continue

        current = extract_player_snapshot(data, player_name)
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
                f"{player_name}\n"
                f"Placering: {current['position']}\n"
                f"Score: {current['score']} ({current['to_par']})\n"
                f"Hål spelade: {current['played_holes']}\n"
                f"Klass: {current['class']}\n"
            )
            send_ntfy(topic, f"Golfuppdatering: {player_name}", message)
            state[key] = current
            updates.append(f"Uppdaterad: {player_name} -> {current['position']}")

    save_state(state)
    print("\n".join(updates) if updates else "Ingen ändring.")


if __name__ == "__main__":
    main()
