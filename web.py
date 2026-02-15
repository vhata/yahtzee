#!/usr/bin/env python3
"""
Yahtzee Web — Flask + WebSocket server for browser-based play.

Each WebSocket connection gets its own GameCoordinator instance.
State is pushed to the client as JSON snapshots at ~30 FPS during active play.
"""
import json
import logging
import threading
import time
import sys

logger = logging.getLogger(__name__)

from flask import Flask, render_template, request
from flask_sock import Sock

from game_engine import Category
from game_coordinator import GameCoordinator, _make_strategy
from frontend_adapter import FrontendAdapter, NullSound, CATEGORY_ORDER

app = Flask(__name__)
sock = Sock(app)


@app.route("/")
def index():
    """Landing page with game configuration form."""
    has_autosave = GameCoordinator.load_state() is not None
    return render_template("index.html", has_autosave=has_autosave)


@app.route("/game")
def game():
    """Main game page — connects to WebSocket for real-time play."""
    return render_template("game.html")


@sock.route("/ws")
def websocket(ws):
    """WebSocket handler — one game per connection."""
    # Parse game config from query params
    ai = request.args.get("ai", "false") == "true"
    strategy_name = request.args.get("strategy", "greedy")
    players_str = request.args.get("players", "")
    names_str = request.args.get("names", "")
    speed = request.args.get("speed", "normal")
    resume = request.args.get("resume", "false") == "true"

    if speed not in ("slow", "normal", "fast"):
        speed = "normal"

    coordinator = None

    # Try autosave resume
    if resume:
        coordinator = GameCoordinator.load_state()

    if coordinator is None and players_str:
        # Multiplayer
        player_tokens = [t.strip() for t in players_str.split(",") if t.strip()]
        name_list = [n.strip() for n in names_str.split(",") if n.strip()] if names_str else []

        players = []
        for i, token in enumerate(player_tokens):
            strategy = _make_strategy(token)
            if i < len(name_list):
                name = name_list[i]
            elif strategy is None:
                name = f"Player {i + 1}"
            else:
                ai_name = strategy.__class__.__name__.replace("Strategy", "")
                name = f"P{i + 1} {ai_name}"
            players.append((name, strategy))

        if len(players) >= 2:
            coordinator = GameCoordinator(speed=speed, players=players)

    if coordinator is None:
        # Single player
        ai_strategy = None
        if ai:
            ai_strategy = _make_strategy(strategy_name)
        coordinator = GameCoordinator(ai_strategy=ai_strategy, speed=speed)

    adapter = FrontendAdapter(coordinator, sound=NullSound())
    adapter.load_settings()
    lock = threading.Lock()
    running = True

    def tick_loop():
        """Background thread: tick coordinator and push state at ~30 FPS."""
        nonlocal running
        while running:
            try:
                with lock:
                    coordinator.tick()
                    adapter.update()
                    snapshot = adapter.get_game_snapshot()
                ws.send(json.dumps(snapshot))
            except Exception:
                logger.error("Tick loop error", exc_info=True)
                running = False
                break
            time.sleep(1 / 30)

    tick_thread = threading.Thread(target=tick_loop, daemon=True)
    tick_thread.start()

    try:
        while running:
            data = ws.receive()
            if data is None:
                break
            try:
                action = json.loads(data)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from client: %s", data)
                continue

            with lock:
                _handle_action(adapter, action)
    except Exception:
        logger.error("WebSocket receive error", exc_info=True)
    finally:
        running = False


def _handle_action(adapter, action):
    """Dispatch a client action to the adapter."""
    cmd = action.get("action", "")

    if cmd == "roll":
        adapter.do_roll()

    elif cmd == "hold":
        idx = action.get("die_index")
        if isinstance(idx, int) and 0 <= idx < 5:
            adapter.do_hold(idx)

    elif cmd == "score":
        cat_name = action.get("category", "")
        cat = _category_by_name(cat_name)
        if cat is not None:
            adapter.try_score_category(cat)

    elif cmd == "confirm_zero_yes":
        adapter.confirm_zero_yes()

    elif cmd == "confirm_zero_no":
        adapter.confirm_zero_no()

    elif cmd == "navigate_category":
        direction = action.get("direction", 1)
        adapter.navigate_category(direction)

    elif cmd == "hover":
        cat_name = action.get("category", "")
        cat = _category_by_name(cat_name)
        if cat is not None:
            adapter.set_hovered_category(cat)
        else:
            adapter.clear_hover()

    elif cmd == "clear_hover":
        adapter.clear_hover()

    elif cmd == "undo":
        adapter.do_undo()

    elif cmd == "reset":
        adapter.do_reset()

    elif cmd == "toggle_help":
        adapter.toggle_help()

    elif cmd == "toggle_history":
        adapter.toggle_history()

    elif cmd == "toggle_replay":
        adapter.toggle_replay()

    elif cmd == "toggle_dark_mode":
        adapter.toggle_dark_mode()

    elif cmd == "toggle_colorblind":
        adapter.toggle_colorblind()

    elif cmd == "toggle_sound":
        adapter.toggle_sound()

    elif cmd == "speed_up":
        adapter.change_speed(+1)

    elif cmd == "speed_down":
        adapter.change_speed(-1)

    elif cmd == "cycle_player_filter":
        adapter.cycle_player_filter()

    elif cmd == "cycle_mode_filter":
        adapter.cycle_mode_filter()


def _category_by_name(name):
    """Look up a Category enum by its display name."""
    for cat in Category:
        if cat.value == name:
            return cat
    return None


def main():
    """Entry point for the web server."""
    import argparse
    parser = argparse.ArgumentParser(description="Yahtzee Web Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="Port (default: 5000)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    print(f"Starting Yahtzee web server at http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
