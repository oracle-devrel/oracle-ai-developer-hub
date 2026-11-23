"""Browser checks with Playwright (Chromium) against a running appbook.

    python tests/check_browser.py [--base http://127.0.0.1:8735/]

Every page at desktop and phone width (diagrams drawn, no JavaScript errors,
no horizontal scroll), one live step from the page (Part 4: two Grok calls),
the Data Explorer, the theme, the status modal and a new lab run.
Screenshots land in tests/artifacts/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ART = Path(__file__).resolve().parent / "artifacts"
FIGURES = {
    "": 6,
    "part3": 1,
    "part4": 1,
    "part5": 1,
    "part6": 3,
    "part7": 3,
    "part8": 3,
    "part9": 3,
    "todos": 1,
}
FAILS: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(("PASS " if ok else "FAIL ") + label + (f"  — {detail}" if detail else ""), flush=True)
    if not ok:
        FAILS.append(label)


def open_page(browser, w, h):
    page = browser.new_page(viewport={"width": w, "height": h})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on(
        "console",
        lambda m: errors.append(m.text) if m.type == "error" and "fonts.g" not in m.text else None,
    )
    return page, errors


def wait_ready(page):
    page.wait_for_function(
        "() => typeof App !== 'undefined' && App.state.health && App.state.health.ready === true",
        timeout=60_000,
    )


def pages_pass(browser, base, w, h, tag):
    page, errors = open_page(browser, w, h)
    page.goto(base)
    wait_ready(page)
    for r, n in FIGURES.items():
        page.goto(base + "#/" + r)
        page.wait_for_selector("#stage h1", timeout=15_000)
        page.wait_for_timeout(900)
        figs = page.locator("#stage .dg-wrap svg.dg").count()
        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        page.screenshot(path=str(ART / f"{tag}-{r or 'overview'}.png"))
        check(
            figs >= n and overflow <= 1 and not errors and page.locator(".pager").count() == 1,
            f"[{tag}] #/{r} renders",
            f"{figs} diagram(s)"
            + (f"; overflow {overflow}px" if overflow > 1 else "")
            + (f"; errors {errors[:2]}" if errors else ""),
        )
        errors.clear()
    page.close()


def interactions(browser, base):
    page, errors = open_page(browser, 1360, 900)
    page.goto(base)
    wait_ready(page)
    page.click("[data-new-run]")
    page.wait_for_timeout(1200)
    run = page.locator("#run-box .mono").inner_text()
    check(
        len(run) == 10 and "0/" in page.inner_text("#run-box"),
        "New run starts an empty lab run",
        run,
    )

    page.goto(base + "#/part4")
    page.wait_for_selector("#p4-step [data-run-step]")
    page.click("#p4-step [data-run-step]")
    page.wait_for_selector("#p4-step .job .compare", timeout=180_000)
    answers = page.locator("#p4-step .job .compare .answer").all_inner_texts()
    gap = page.inner_text("#p4-gap")
    check(
        len(answers) == 2 and "unknown" in answers[1].lower(),
        "Part 4 runs live and shows both answers",
        " | ".join(a.replace("\n", " ")[:50] for a in answers),
    )
    check(
        answers[0].split("\n")[0][:12] in gap,
        "the context-gap diagram redraws with the live answer",
    )
    check(
        page.locator("#p4-step .llm-call").count() == 2,
        "both Grok calls are listed with their prompts",
    )
    page.screenshot(path=str(ART / "part4-live.png"), full_page=True)

    page.goto(base + "#/part7")
    page.wait_for_selector("#p7-journey svg", timeout=15_000)
    check(
        "NOTEBOOK RUN" in page.inner_text("#p7-journey")
        or "ACTUAL ANSWER" in page.inner_text("#p7-journey"),
        "Part 7 draws the four-stage journey",
    )

    page.click("[data-drawer]")
    page.wait_for_selector("#drawer-body .tbl-list button", timeout=30_000)
    names = page.locator("#drawer-body .tbl-list button").all_inner_texts()
    store = page.evaluate("App.state.health.store")
    check(
        len(names) >= 6 and all(n.startswith(store + "_") for n in names),
        "Data Explorer lists only the appbook's store tables",
        f"{len(names)} tables",
    )
    page.click("[data-drawer]")
    theme = page.evaluate("document.documentElement.dataset.theme")
    page.click("[data-theme-toggle]")
    check(page.evaluate("document.documentElement.dataset.theme") != theme, "theme toggle")
    page.click("[data-status]")
    check(page.locator("#modal .status-item").count() == 4, "status pills open the runtime status")
    check(not errors, "no JavaScript errors during the interactions", "; ".join(errors[:3]))
    page.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8735/")
    base = ap.parse_args().base.rstrip("/") + "/"
    ART.mkdir(exist_ok=True)
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
