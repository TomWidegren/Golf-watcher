import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

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


def fetch_player_line(url: str, player: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 1200})
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)

        rows = page.locator("tr")
        for i in range(rows.count()):
            text = normalize(rows.nth(i).inner_text())
            if player.lower() in text.lower():
                browser.close()
                return text

        body = normalize(page.locator("body").inner_text())
        browser.close()

        for line in body.splitlines():
            line = normalize(line)
            if player.lower() in line.lower():
                return line

    return None


def main():
    config = load_config()
    state = load_state()
    updates = []

    for watch in config["watches"]:
        name = watch["name"]
        url = watch["url"]
        player = watch["player"]
        topic = config["ntfy"]["topic"]

        current = fetch_player_line(url, player)
        key = f"{name}::{player}::{url}"
        previous = state.get(key)

        if not current:
            updates.append(f"{name}: hittade ingen rad för {player}")
            continue

        if previous != current:
            message = (
                f"{player}\n"
                f"{current}\n\n"
                f"{url}"
            )
            send_ntfy(topic, f"Golfuppdatering: {player}", message)
            state[key] = current
            updates.append(f"Uppdaterad: {player}")

    save_state(state)
    print("\n".join(updates) if updates else "Ingen ändring.")


if __name__ == "__main__":
    main()
