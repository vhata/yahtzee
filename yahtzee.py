#!/usr/bin/env python3
"""
Unified entry point for all Yahtzee interfaces.

Usage:
    python yahtzee.py                           # Default: pygame
    python yahtzee.py --ui tui                  # Terminal (Textual)
    python yahtzee.py --ui web                  # Browser (Flask)
    python yahtzee.py --ui tui --ai --optimal   # TUI AI spectator
    python yahtzee.py --ui web --port 8080      # Web on custom port

Individual entry points (main.py, tui.py, web.py) still work independently.
"""
import argparse
import sys


def main():
    # Pre-parse just the --ui flag, pass everything else through
    parser = argparse.ArgumentParser(
        description="Yahtzee — play in pygame, terminal, or browser",
        add_help=False,
    )
    parser.add_argument("--ui", choices=["pygame", "tui", "web"], default="pygame",
                        help="Interface: pygame (default), tui (terminal), web (browser)")
    args, remaining = parser.parse_known_args()

    if args.ui == "pygame":
        # Restore remaining args for parse_args() in main.py
        sys.argv = [sys.argv[0]] + remaining
        from main import main as run_pygame
        run_pygame()

    elif args.ui == "tui":
        sys.argv = [sys.argv[0]] + remaining
        from tui import main as run_tui
        run_tui()

    elif args.ui == "web":
        sys.argv = [sys.argv[0]] + remaining
        from web import main as run_web
        run_web()


if __name__ == "__main__":
    main()
