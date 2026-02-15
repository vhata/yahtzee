#!/usr/bin/env python3
"""Web UI screenshot tests with automated DOM assertions.

Takes screenshots of the web UI in various states AND runs programmatic checks
on the DOM to catch layout issues (overlapping elements, viewport overflow,
inconsistent dice/scorecard state). This catches bugs that a quick visual
glance at screenshots might miss — like the HELD label overlapping the die
number, or dice overflowing on mobile viewports.

Usage:
    uv run python web.py --port 5099 &
    uv run python screenshot_test.py

Requires: playwright (uv run playwright install chromium)
"""
import os
import sys
import time

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5099"
SHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")

# JavaScript that runs in-browser to detect layout/DOM issues.
# Returns a list of human-readable issue strings (empty = all good).
CHECK_LAYOUT_JS = """() => {
    const issues = [];

    // 1. Check dice wrapper children don't overlap each other
    document.querySelectorAll('.die-wrapper').forEach((w, i) => {
        const children = Array.from(w.children);
        for (let a = 0; a < children.length; a++) {
            const ra = children[a].getBoundingClientRect();
            if (ra.width === 0 && ra.height === 0) continue;  // hidden
            for (let b = a + 1; b < children.length; b++) {
                const rb = children[b].getBoundingClientRect();
                if (rb.width === 0 && rb.height === 0) continue;
                if (ra.bottom > rb.top && ra.top < rb.bottom &&
                    ra.right > rb.left && ra.left < rb.right) {
                    issues.push(
                        `Die ${i+1}: "${children[a].className}" overlaps ` +
                        `"${children[b].className}" ` +
                        `(a: ${ra.top.toFixed(0)}-${ra.bottom.toFixed(0)}, ` +
                        `b: ${rb.top.toFixed(0)}-${rb.bottom.toFixed(0)})`
                    );
                }
            }
        }
    });

    // 2. Check key containers don't overflow viewport width
    const vw = window.innerWidth;
    ['#dice-container', '#scorecard', '#roll-btn'].forEach(sel => {
        const el = document.querySelector(sel);
        if (el) {
            const r = el.getBoundingClientRect();
            if (r.right > vw + 2)
                issues.push(`${sel} overflows viewport ` +
                    `(right=${r.right.toFixed(0)}, viewport_width=${vw})`);
        }
    });

    // 3. Dice dot count matches data-value (skip rolling/in-cup dice)
    document.querySelectorAll('.die:not(.in-cup):not(.rolling)').forEach((d, i) => {
        const val = parseInt(d.dataset.value);
        const dots = d.querySelectorAll('.dot').length;
        if (!isNaN(val) && val !== dots)
            issues.push(`Die ${i+1}: data-value=${val} but has ${dots} dots`);
    });

    // 4. Held dice must have HELD in their label
    document.querySelectorAll('.die.held').forEach(d => {
        const label = d.parentElement.querySelector('.die-label');
        if (label && !label.textContent.includes('HELD'))
            issues.push(`Held die label "${label.textContent}" missing HELD text`);
    });

    // 5. In-cup dice must contain cup-text child
    document.querySelectorAll('.die.in-cup').forEach((d, i) => {
        if (!d.querySelector('.cup-text'))
            issues.push(`In-cup die ${i+1} missing .cup-text child`);
    });

    // 6. Scorecard should have 13 category rows (if any exist)
    const catRows = document.querySelectorAll('tr.category-row');
    if (catRows.length > 0 && catRows.length !== 13)
        issues.push(`Scorecard has ${catRows.length} category rows, expected 13`);

    // 7. No row should be both filled and selected
    document.querySelectorAll('tr.category-row.filled.selected').forEach(r => {
        const name = r.querySelector('td') ? r.querySelector('td').textContent.trim() : '?';
        issues.push(`Row "${name}" is both filled and selected`);
    });

    // 8. Overlay exclusivity: at most one overlay visible at a time
    const overlayIds = [
        'overlay-help', 'overlay-history', 'overlay-replay',
        'overlay-confirm', 'overlay-gameover', 'overlay-transition'
    ];
    const visible = overlayIds.filter(id => {
        const el = document.getElementById(id);
        return el && !el.classList.contains('hidden');
    });
    if (visible.length > 1)
        issues.push(`Multiple overlays visible: ${visible.join(', ')}`);

    return issues;
}"""


def check_layout(page, name):
    """Run DOM layout assertions via in-browser JavaScript.

    Raises AssertionError with descriptive messages if any issues are found.
    """
    issues = page.evaluate(CHECK_LAYOUT_JS)
    if issues:
        raise AssertionError(
            f"Layout issues in '{name}':\n" +
            "\n".join(f"  - {issue}" for issue in issues)
        )


def screenshot(page, filename, label):
    """Take a screenshot and run layout checks."""
    path = os.path.join(SHOTS_DIR, filename)
    page.screenshot(path=path)
    print(f"  screenshot: {filename}")
    check_layout(page, label)
    print(f"  ✓ DOM checks passed: {label}")


def run_tests():
    os.makedirs(SHOTS_DIR, exist_ok=True)
    passed = 0
    failed = 0
    errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ── 1. Landing page ──────────────────────────────────────────────
        def test_landing():
            page = browser.new_page(viewport={"width": 1000, "height": 800})
            try:
                page.goto(BASE)
                page.wait_for_load_state("networkidle")
                screenshot(page, "01_landing.png", "landing page")
            finally:
                page.close()

        # ── 2. Initial game state (dice in cup) ─────────────────────────
        def test_initial():
            page = browser.new_page(viewport={"width": 1000, "height": 800})
            try:
                page.goto(f"{BASE}/game")
                page.wait_for_load_state("networkidle")
                time.sleep(1)
                screenshot(page, "02_game_initial.png", "initial game state")
            finally:
                page.close()

        # ── 3. After rolling dice ────────────────────────────────────────
        def test_after_roll():
            page = browser.new_page(viewport={"width": 1000, "height": 800})
            try:
                page.goto(f"{BASE}/game")
                time.sleep(1)
                page.keyboard.press("Space")
                time.sleep(2.5)  # Wait for roll animation
                screenshot(page, "03_after_roll.png", "after roll")
            finally:
                page.close()

        # ── 4. Held dice ────────────────────────────────────────────────
        def test_held_dice():
            page = browser.new_page(viewport={"width": 1000, "height": 800})
            try:
                page.goto(f"{BASE}/game")
                time.sleep(1)
                page.keyboard.press("Space")
                time.sleep(2.5)
                page.keyboard.press("1")
                time.sleep(0.5)
                page.keyboard.press("3")
                time.sleep(0.5)
                screenshot(page, "04_dice_held.png", "held dice")
            finally:
                page.close()

        # ── 5. Category navigation ──────────────────────────────────────
        def test_category_nav():
            page = browser.new_page(viewport={"width": 1000, "height": 800})
            try:
                page.goto(f"{BASE}/game")
                time.sleep(1)
                page.keyboard.press("Space")
                time.sleep(2.5)
                page.keyboard.press("Tab")
                time.sleep(0.3)
                page.keyboard.press("Tab")
                time.sleep(0.3)
                page.keyboard.press("Tab")
                time.sleep(0.3)
                screenshot(page, "05_category_selected.png", "category selected")

                # Extra check: exactly one row should be selected
                selected = page.evaluate(
                    "() => document.querySelectorAll('tr.category-row.selected').length"
                )
                assert selected == 1, (
                    f"Expected 1 selected category row, got {selected}"
                )
                print("  ✓ Exactly 1 category row selected")
            finally:
                page.close()

        # ── 6. Dark mode ────────────────────────────────────────────────
        def test_dark_mode():
            page = browser.new_page(viewport={"width": 1000, "height": 800})
            try:
                page.goto(f"{BASE}/game")
                time.sleep(1)
                page.keyboard.press("Space")
                time.sleep(2.5)
                # Toggle dark mode on if not already active
                already_dark = page.evaluate(
                    "() => document.body.classList.contains('dark-mode')"
                )
                if not already_dark:
                    page.keyboard.press("d")
                    time.sleep(0.5)
                screenshot(page, "06_dark_mode.png", "dark mode")

                has_dark = page.evaluate(
                    "() => document.body.classList.contains('dark-mode')"
                )
                assert has_dark, "Body should have dark-mode class"
                print("  ✓ dark-mode class present")

                # Toggle it back off so we don't affect other tests
                page.keyboard.press("d")
                time.sleep(0.3)
            finally:
                page.close()

        # ── 7. AI spectator ─────────────────────────────────────────────
        def test_ai_spectator():
            page = browser.new_page(viewport={"width": 1000, "height": 800})
            try:
                page.goto(
                    f"{BASE}/game?ai=true&strategy=greedy&speed=fast"
                )
                time.sleep(5)
                screenshot(page, "07_ai_spectator.png", "AI spectator")
            finally:
                page.close()

        # ── 8. Multiplayer ──────────────────────────────────────────────
        def test_multiplayer():
            page = browser.new_page(viewport={"width": 1000, "height": 800})
            try:
                page.goto(
                    f"{BASE}/game?players=human,greedy&names=Alice,Bot&speed=fast"
                )
                time.sleep(8)
                screenshot(page, "08_multiplayer.png", "multiplayer")
            finally:
                page.close()

        # ── 9. Help overlay ─────────────────────────────────────────────
        def test_help_overlay():
            page = browser.new_page(viewport={"width": 1000, "height": 800})
            try:
                page.goto(
                    f"{BASE}/game?players=human,greedy&names=Alice,Bot&speed=fast"
                )
                time.sleep(8)
                page.keyboard.press("F1")
                time.sleep(0.5)
                screenshot(page, "09_help_overlay.png", "help overlay")

                # Help visible, others hidden
                help_visible = page.evaluate(
                    "() => !document.getElementById('overlay-help')"
                    ".classList.contains('hidden')"
                )
                assert help_visible, "Help overlay should be visible"

                history_hidden = page.evaluate(
                    "() => document.getElementById('overlay-history')"
                    ".classList.contains('hidden')"
                )
                assert history_hidden, (
                    "History overlay should be hidden when help is open"
                )
                print("  ✓ Overlay exclusivity verified")
            finally:
                page.close()

        # ── 10. Mobile viewport ─────────────────────────────────────────
        def test_mobile():
            page = browser.new_page(viewport={"width": 375, "height": 812})
            try:
                page.goto(f"{BASE}/game")
                time.sleep(1)
                page.keyboard.press("Space")
                time.sleep(2.5)
                screenshot(page, "10_mobile.png", "mobile viewport")
            finally:
                page.close()

        # ── 11. AI vs AI turn log ───────────────────────────────────────
        def test_turn_log():
            page = browser.new_page(viewport={"width": 1000, "height": 900})
            try:
                page.goto(
                    f"{BASE}/game?players=greedy,greedy"
                    f"&names=Alice,Bob&speed=fast"
                )
                time.sleep(12)
                screenshot(page, "11_turn_log.png", "AI vs AI turn log")

                # Turn log should have entries after several turns
                log_entries = page.evaluate(
                    "() => document.querySelectorAll('#turn-log .turn-log-entry').length"
                )
                assert log_entries > 0, (
                    f"Turn log should have entries after AI play, got {log_entries}"
                )
                print(f"  ✓ Turn log has {log_entries} entries")
            finally:
                page.close()

        # ── 12. Human turn after AI ─────────────────────────────────────
        def test_human_after_ai():
            page = browser.new_page(viewport={"width": 1000, "height": 900})
            try:
                page.goto(
                    f"{BASE}/game?players=greedy,human"
                    f"&names=Bot,You&speed=fast"
                )
                time.sleep(8)
                screenshot(page, "12_human_after_ai.png",
                           "human turn after AI")
            finally:
                page.close()

        # ── Run all tests ───────────────────────────────────────────────
        tests = [
            ("Landing page", test_landing),
            ("Initial state", test_initial),
            ("After roll", test_after_roll),
            ("Held dice", test_held_dice),
            ("Category navigation", test_category_nav),
            ("Dark mode", test_dark_mode),
            ("AI spectator", test_ai_spectator),
            ("Multiplayer", test_multiplayer),
            ("Help overlay", test_help_overlay),
            ("Mobile viewport", test_mobile),
            ("Turn log (AI vs AI)", test_turn_log),
            ("Human after AI", test_human_after_ai),
        ]

        for label, test_fn in tests:
            print(f"\n[{label}]")
            try:
                test_fn()
                passed += 1
            except Exception as e:
                failed += 1
                errors.append((label, e))
                print(f"  ✗ FAILED: {e}")

        browser.close()

    # ── Summary ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")

    if errors:
        print(f"\nFailures:")
        for label, e in errors:
            print(f"  [{label}] {e}")
        print(f"\nScreenshots saved to {SHOTS_DIR}/")
        sys.exit(1)
    else:
        print(f"All screenshots and DOM checks passed!")
        print(f"Screenshots saved to {SHOTS_DIR}/")


if __name__ == "__main__":
    run_tests()
