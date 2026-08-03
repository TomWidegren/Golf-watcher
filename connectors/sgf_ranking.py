from playwright.sync_api import Page

RANKING_URL = "https://golfdata.se/sgfranking/Rankinglista_ind"


def fetch_player_snapshot(page: Page, player_name: str):
    page.goto(RANKING_URL, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(3000)

    selects = page.locator("select")
    selects.nth(0).select_option(label="Pojkar (juniorer)")
    selects.nth(1).select_option(label="2026")
    selects.nth(4).select_option(label="Haninge Golfklubb")

    page.get_by_role("button", name="Visa listan").click()
    page.wait_for_timeout(3000)

    rows = page.locator("tr")
    print("ROW_COUNT:", rows.count(), flush=True)

    for i in range(min(rows.count(), 15)):
        txt = rows.nth(i).inner_text().strip()
        print(f"=== ROW {i} ===", flush=True)
        print(txt, flush=True)

    return None
