from playwright.sync_api import Page

RANKING_URL = "https://golfdata.se/sgfranking/Rankinglista_ind"

def fetch_player_snapshot(page: Page, player_name: str):
    page.goto(RANKING_URL, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(2000)

    selects = page.locator("select")
    selects.nth(0).select_option(label="Pojkar (juniorer)")
    selects.nth(1).select_option(label="2026")
    selects.nth(2).select_option(label="Haninge Golfklubb")

    page.get_by_role("button", name="Visa listan").click()
    page.wait_for_timeout(3000)

    player = page.get_by_text(player_name, exact=True).first
    row = player.locator("xpath=ancestor::tr[1]")

    print("=== ROW TEXT ===")
    print(row.inner_text())
    print("=== ROW HTML ===")
    print(row.evaluate("e => e.outerHTML"))

    return None
