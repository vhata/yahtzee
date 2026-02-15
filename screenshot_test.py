#!/usr/bin/env python3
"""Take screenshots of the web UI in various states for visual verification.

Run with the web server already running on port 5099:
    uv run python web.py --port 5099 &
    uv run python screenshot_test.py
"""
import time
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5099"
SHOTS_DIR = "/Users/jonathan.hitchcock/src/yahtzee/screenshots"


def take_screenshots():
    import os
    os.makedirs(SHOTS_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # 1. Landing page
        page = browser.new_page(viewport={"width": 1000, "height": 800})
        page.goto(BASE)
        page.wait_for_load_state("networkidle")
        page.screenshot(path=f"{SHOTS_DIR}/01_landing.png")
        print("✓ 01_landing.png")
        page.close()

        # 2. Single player - initial state (dice in cup)
        page = browser.new_page(viewport={"width": 1000, "height": 800})
        page.goto(f"{BASE}/game")
        page.wait_for_load_state("networkidle")
        time.sleep(1)  # Wait for WebSocket state
        page.screenshot(path=f"{SHOTS_DIR}/02_game_initial.png")
        print("✓ 02_game_initial.png")

        # 3. Roll dice
        page.keyboard.press("Space")
        time.sleep(2.5)  # Wait for roll animation to complete
        page.screenshot(path=f"{SHOTS_DIR}/03_after_roll.png")
        print("✓ 03_after_roll.png")

        # 4. Hold some dice
        page.keyboard.press("1")
        time.sleep(0.5)
        page.keyboard.press("3")
        time.sleep(0.5)
        page.screenshot(path=f"{SHOTS_DIR}/04_dice_held.png")
        print("✓ 04_dice_held.png")

        # 5. Navigate categories with keyboard
        page.keyboard.press("Tab")
        time.sleep(0.3)
        page.keyboard.press("Tab")
        time.sleep(0.3)
        page.keyboard.press("Tab")
        time.sleep(0.3)
        page.screenshot(path=f"{SHOTS_DIR}/05_category_selected.png")
        print("✓ 05_category_selected.png")
        page.close()

        # 6. Dark mode
        page = browser.new_page(viewport={"width": 1000, "height": 800})
        page.goto(f"{BASE}/game")
        time.sleep(1)
        page.keyboard.press("Space")
        time.sleep(2.5)
        page.keyboard.press("d")
        time.sleep(0.5)
        page.screenshot(path=f"{SHOTS_DIR}/06_dark_mode.png")
        print("✓ 06_dark_mode.png")
        page.close()

        # 7. AI spectator game
        page = browser.new_page(viewport={"width": 1000, "height": 800})
        page.goto(f"{BASE}/game?ai=true&strategy=greedy&speed=fast")
        time.sleep(5)  # Let AI play a few turns
        page.screenshot(path=f"{SHOTS_DIR}/07_ai_spectator.png")
        print("✓ 07_ai_spectator.png")
        page.close()

        # 8. Multiplayer game
        page = browser.new_page(viewport={"width": 1000, "height": 800})
        page.goto(f"{BASE}/game?players=human,greedy&names=Alice,Bot&speed=fast")
        time.sleep(8)  # Let the AI take its turn, then it should be human's turn
        page.screenshot(path=f"{SHOTS_DIR}/08_multiplayer.png")
        print("✓ 08_multiplayer.png")

        # 9. Help overlay
        page.keyboard.press("F1")
        time.sleep(0.5)
        page.screenshot(path=f"{SHOTS_DIR}/09_help_overlay.png")
        print("✓ 09_help_overlay.png")
        page.keyboard.press("Escape")
        time.sleep(0.3)
        page.close()

        # 10. Mobile viewport
        page = browser.new_page(viewport={"width": 375, "height": 812})
        page.goto(f"{BASE}/game")
        time.sleep(1)
        page.keyboard.press("Space")
        time.sleep(2.5)
        page.screenshot(path=f"{SHOTS_DIR}/10_mobile.png")
        print("✓ 10_mobile.png")
        page.close()

        browser.close()
        print(f"\nAll screenshots saved to {SHOTS_DIR}/")


if __name__ == "__main__":
    take_screenshots()
