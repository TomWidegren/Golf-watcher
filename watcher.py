print("VERSION 2 - DEBUG")

import json
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


def fetch_stream_snapshot(url: str, player: str) -> str | None:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "User-Agent": "Mozilla/5.0",
        },
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        event_data = []

        while True:
            line = resp.readline()
            if not line:
                break

            text = line.decode("utf-8", errors="ignore").rstrip("\n\r")

            if text == "":
                if event_data:
                    payload = "\n".join(event_data).strip()
                    print("PAYLOAD:")
                    print(payload)
                    return payload
                continue

            if text.startswith("data:"):
                event_data.append(text[5:].strip())

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

        current = fetch_stream_snapshot(url, player)
        key = f"{name}::{player}::{url}"
        previous = state.get(key)

        if not current:
            updates.append(f"{name}: hittade ingen uppdatering för {player}")
            continue

        if previous != current:
            message = f"{player}\n\n{current}\n\n{url}"
            send_ntfy(topic, f"Golfuppdatering: {player}", message)
            state[key] = current
            updates.append(f"Uppdaterad: {player}")

    save_state(state)
    print("\n".join(updates) if updates else "Ingen ändring.")


if __name__ == "__main__":
    main()
