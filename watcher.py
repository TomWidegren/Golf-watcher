import requests

url = "https://tournytt.se/api/leaderboard/stream?competitions=5405880"

r = requests.get(
    url,
    headers={
        "Accept": "text/event-stream",
        "User-Agent": "Mozilla/5.0"
    },
    stream=True,
    timeout=60,
)

print("Status:", r.status_code)

for line in r.iter_lines(decode_unicode=True):
    if line:
        print(line)
