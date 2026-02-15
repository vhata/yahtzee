#!/usr/bin/env python3
"""Screenshot specifically to verify the multiplayer turn log."""
import time
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5099"
SHOTS_DIR = "/Users/jonathan.hitchcock/src/yahtzee/screenshots"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # AI vs AI multiplayer — turns complete fast, turn log fills up
        page = browser.new_page(viewport={"width": 1000, "height": 900})
        page.goto(f"{BASE}/game?players=greedy,greedy&names=Alice,Bob&speed=fast")
        time.sleep(12)  # Let several turns play out
        page.screenshot(path=f"{SHOTS_DIR}/11_turn_log.png")
        print("✓ 11_turn_log.png")

        # Human vs AI — wait for AI to finish, then screenshot human's turn
        page2 = browser.new_page(viewport={"width": 1000, "height": 900})
        page2.goto(f"{BASE}/game?players=greedy,human&names=Bot,You&speed=fast")
        time.sleep(8)  # Bot goes first, then it's You's turn
        page2.screenshot(path=f"{SHOTS_DIR}/12_human_after_ai.png")
        print("✓ 12_human_after_ai.png")

        browser.close()


if __name__ == "__main__":
    main()
