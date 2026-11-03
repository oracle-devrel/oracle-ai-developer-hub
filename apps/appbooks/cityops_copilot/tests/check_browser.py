"""Browser checks with Playwright (Chromium) against a running appbook.

    python tests/check_browser.py [--base http://127.0.0.1:8730/]

Every page at desktop and phone width (no JavaScript errors, no horizontal
scroll) and the cheap live panels (embedding, findings search, memory log,
Data Explorer, theme). No model calls. Screenshots land in tests/artifacts/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ART = Path(__file__).resolve().parent / "artifacts"
ROUTES = ["", "part1", "part2", "part3", "part4", "part5", "part6", "handoff", "memory-types"]
# diagrams each page must draw (the overview has the architecture, state, loop and roadmap figures)
FIGURES = {
    "": 4,
    "part1": 2,
    "part2": 2,
    "part3": 2,
    "part4": 2,
    "part5": 1,
    "part6": 1,
    "handoff": 1,
    "memory-types": 1,
}
FAILS: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(("PASS " if ok else "FAIL ") + label + (f"  — {detail}" if detail else ""), flush=True)
    if not ok:
        FAILS.append(label)


def open_page(browser, width: int, height: int):
    page = browser.new_page(viewport={"width": width, "height": height})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on(
        "console",
        lambda m: errors.append(m.text) if m.type == "error" and "fonts.g" not in m.text else None,
    )
    return page, errors


def wait_ready(page) -> None:
    # App is a top-level const, so it is a global binding but not a window property.
    page.wait_for_function(
        "() => typeof App !== 'undefined' && App.state.health && App.state.health.ready === true",
        timeout=60_000,
    )


def pages_pass(browser, base: str, width: int, height: int, tag: str) -> None:
    page, errors = open_page(browser, width, height)
    page.goto(base)
    wait_ready(page)
    for r in ROUTES:
        page.goto(base + "#/" + r)
        page.wait_for_selector("#stage h1", timeout=15_000)
        page.wait_for_timeout(900)  # live panels load
        h1 = page.inner_text("#stage h1")
        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        has_pager = page.locator(".pager").count() == 1
        figs = page.locator("#stage .dg-wrap svg.dg").count()
        page.screenshot(path=str(ART / f"{tag}-{r or 'overview'}.png"), full_page=False)
        check(
            bool(h1) and has_pager and overflow <= 1 and not errors and figs >= FIGURES[r],
            f"[{tag}] #/{r or ''} renders",
            f"{h1[:50]!r} · {figs} diagram(s)"
            + (f"; overflow {overflow}px" if overflow > 1 else "")
            + (f"; errors {errors[:2]}" if errors else ""),
        )
        errors.clear()
    page.close()


def interactions(browser, base: str) -> None:
    page, errors = open_page(browser, 1360, 900)
    page.goto(base + "#/part2")
    wait_ready(page)
    page.goto(base + "#/part2")
    page.click("[data-embed]")
    page.wait_for_selector(".matrix td.cell", timeout=60_000)
    check(
        page.locator(".matrix td.cell").count() == 6
        and page.locator("svg.spark").count() == 3
        and page.locator("#p2-out .mm-pt").count() == 3,
        "Part 2: embedding lab draws vectors, a distance matrix and the meaning map",
    )
    page.screenshot(path=str(ART / "part2-embed.png"), full_page=True)

    page.goto(base + "#/part4")
    page.wait_for_selector("[data-cat] option:nth-child(2)", state="attached", timeout=30_000)
    page.select_option("[data-asset]", "Harbor Bridge")
    page.click("[data-go]")
    page.wait_for_selector("#p4-out tbody tr", timeout=60_000)
    cells = page.locator("#p4-out tbody tr td:nth-child(2)").all_inner_texts()
    check(
        cells and all(c.strip() == "Harbor Bridge" for c in cells),
        "Part 4: findings search with the asset filter",
        f"{len(cells)} rows",
    )
    page.click("[data-checkpoint]")
    page.wait_for_selector("#p4-out .chip.ok, #p4-out .chip.err", timeout=60_000)
    check(
        page.locator("#p4-out .chip.err").count() == 0
        and page.locator("#p4-out .chip.ok").count() == 3,
        "Part 4: TODO 5 checkpoint passes in the page",
    )

    page.goto(base + "#/part3")
    page.wait_for_selector("#p3-log-out .record, #p3-log-out .empty", timeout=30_000)
    try:  # the chart has its own request; wait for it rather than racing the memory log
        page.wait_for_selector("#p3-assets .barlist .item", timeout=30_000)
    except Exception:
        pass
    check(page.locator("#p3-assets .barlist .item").count() >= 8, "Part 3: asset classes chart")
    page.wait_for_selector("[data-pick] option:nth-child(2)", state="attached", timeout=30_000)
    page.select_option("[data-pick]", index=1)
    check(
        len(page.input_value("[data-narr]")) > 40, "Part 3: picking a narrative fills the text box"
    )
    page.click("[data-search]")
    page.wait_for_selector("#p3-search-out .code", timeout=60_000)
    check(
        "search_async" in page.inner_text("#p3-search-out"),
        "Part 3: scoped search shows the call it made",
    )

    page.goto(base + "#/part5")
    page.select_option("[data-preset]", "city")
    check(
        "only records that belong to" in page.inner_text("#p5-explain"),
        "Part 5: the scope explorer explains user_id=None",
    )

    page.click("[data-drawer]")
    page.wait_for_selector("#drawer-body .tbl-list button", timeout=30_000)
    page.wait_for_selector("#drawer-rows table, #drawer-rows .empty", timeout=30_000)
    names = page.locator("#drawer-body .tbl-list button").all_inner_texts()
    check(
        len(names) >= 6 and all("CITYAPP_" in n for n in names),
        "Data Explorer lists only the appbook's tables",
        f"{len(names)} tables",
    )
    page.screenshot(path=str(ART / "drawer.png"))
    page.click("[data-drawer]")

    theme = page.evaluate("document.documentElement.dataset.theme")
    page.click("[data-theme-toggle]")
    check(
        page.evaluate("document.documentElement.dataset.theme") != theme,
        "theme toggle switches light/dark",
    )
    page.screenshot(path=str(ART / "part5-other-theme.png"))

    page.goto(base + "#/handoff")
    page.wait_for_selector("#story .tl-item", timeout=30_000)
    check(page.locator("#story .tl-item").count() == 5, "Handoff: the five story steps render")
    page.click("[data-status]")
    check(page.locator("#modal .status-item").count() == 4, "status pills open the runtime status")
    check(not errors, "no JavaScript errors during the interactions", "; ".join(errors[:3]))
    page.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8730/")
    args = ap.parse_args()
    ART.mkdir(exist_ok=True)
    base = args.base.rstrip("/") + "/"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pages_pass(browser, base, 1360, 900, "desktop")
        pages_pass(browser, base, 390, 844, "phone")
        interactions(browser, base)
        browser.close()
    print(f"\n{'ALL PASSED' if not FAILS else str(len(FAILS)) + ' FAILED: ' + '; '.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
