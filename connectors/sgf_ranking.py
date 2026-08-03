from playwright.sync_api import Page

RANKING_URL = "https://golfdata.se/sgfranking/Rankinglista_ind"


def fetch_player_snapshot(page: Page, player_name: str):
    page.goto(RANKING_URL, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(3000)

    selects = page.locator("select")
    print("SELECT_COUNT:", selects.count(), flush=True)

    for i in range(selects.count()):
        sel = selects.nth(i)
        options = sel.locator("option")

        print(f"=== SELECT {i} ===", flush=True)
        for j in range(options.count()):
            opt = options.nth(j)
            print(
                j,
                repr(opt.inner_text()),
                opt.get_attribute("value"),
                opt.get_attribute("selected"),
                flush=True,
            )

    return None
