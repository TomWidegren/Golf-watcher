from playwright.sync_api import sync_playwright

URL = "https://www.haningegk.se/tavling#/competition/5624874/leaderboard/5080993"

def main():
    print("DEBUG START", flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1200})

        page.goto(URL, wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(8000)

        print("TITLE:", page.title(), flush=True)
        print("URL:", page.url, flush=True)

        body_text = page.locator("body").inner_text()
        print("BODY_LEN:", len(body_text), flush=True)
        print("BODY_HAS_WIDEGREN:", "WIDEGREN" in body_text.upper(), flush=True)

        hits = page.locator("text=WIDEGREN")
        print("WIDEGREN_COUNT:", hits.count(), flush=True)

        for i in range(min(hits.count(), 5)):
            el = hits.nth(i)
            print(f"--- HIT {i} TEXT ---", flush=True)
            print(el.inner_text(), flush=True)
            print(f"--- HIT {i} HTML ---", flush=True)
            print(el.evaluate("e => e.outerHTML"), flush=True)

        browser.close()

    print("DEBUG END", flush=True)

if __name__ == "__main__":
    main()
