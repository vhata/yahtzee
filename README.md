# Yahtzee

A Yahtzee game with three frontends (pygame, terminal, browser), AI opponents, multiplayer support, and a clean testable architecture.

## Quick Start

```bash
uv sync            # Install dependencies
uv run yahtzee     # Play!
```

Requires Python 3.10+ and [uv](https://github.com/astral-sh/uv).

## Setup

The core install (`uv sync`) gives you the pygame frontend. For the terminal or browser frontends, install their extras:

```bash
uv sync --extra tui                        # Terminal UI (Textual)
uv sync --extra web                        # Browser UI (Flask)
uv sync --extra dev --extra tui --extra web # Everything (dev + all frontends)
```

Or use Make shortcuts: `make setup-tui`, `make setup-web`, `make setup-all`.

## How to Play

```bash
uv run yahtzee                             # Pygame (default)
uv run yahtzee --ui tui                    # Terminal
uv run yahtzee --ui web                    # Browser (localhost:5000)
uv run yahtzee --ai --optimal              # Watch AI play
uv run yahtzee --players human optimal     # Play against AI
uv run yahtzee --ui tui --players human greedy optimal
```

Make shortcuts: `make play`, `make play-tui`, `make play-web`.

### Controls

| Key / Action | Effect |
|---|---|
| Click dice / 1-5 keys | Toggle hold |
| Space / ROLL button | Roll dice |
| Tab / ↓ | Next category |
| Shift+Tab / ↑ | Previous category |
| Enter | Score selected category |
| Click scorecard row | Score category |
| Ctrl+Z / Cmd+Z | Undo (human turns) |
| H | Score history |
| M / S | Toggle sound |
| C | Colorblind mode |
| D | Dark mode |
| R | Game replay (after game) |
| +/- | Adjust AI speed |
| ? / F1 | Help overlay |
| Esc | Close overlay / Quit |

## Features

- Full Yahtzee rules with all 13 categories, upper section bonus, and Yahtzee bonus/joker rules
- Three frontends: pygame (graphical), Textual (terminal), Flask+WebSocket (browser)
- 2-4 player multiplayer with turn transitions
- Four AI strategies from random to optimal
- Dice animation (shake, bounce), score flash, dark mode, colorblind mode
- Score history persisted to `~/.yahtzee_scores.json`
- Sound effects (synthesized PCM, no external assets)
- Undo for human players
- Autosave/resume, persistent settings
- Post-game stats (% of optimal play) and turn-by-turn replay
- Three AI speed presets (slow/normal/fast)

## AI Strategies

| Strategy | Description | Avg Score |
|---|---|---|
| `random` | Random holds and category picks | ~45 |
| `greedy` | Rule-based: takes good scores, holds promising dice | ~155 |
| `ev` | Monte Carlo simulation over all 32 hold combos | ~219 |
| `optimal` | Exact probability via precomputed dice tables | ~223 |

## Architecture

```
game_engine.py         Pure game logic (immutable GameState, pure functions)
game_coordinator.py    State machine, AI pacing, timers (no pygame)
frontend_adapter.py    Shared UI state: overlays, settings, score saving
    ├── main.py        Pygame rendering shell + Layout dataclass
    ├── tui.py         Textual terminal UI
    └── web.py         Flask + WebSocket server
ai.py                  4 AI strategies + game loop
dice_tables.py         Precomputed dice combinatorics
score_history.py       Score persistence (JSON)
settings.py            Persistent user preferences
game_log.py            Turn-by-turn replay recording
sounds.py              Synthesized PCM sound effects
```

Game logic is fully separated from rendering. `GameState` is an immutable frozen dataclass; all engine functions return new state. The `FrontendAdapter` provides shared UI state management (overlays, zero-confirm, keyboard navigation, score flash, settings persistence) so all three frontends share the same logic without duplication.

Layout constants for the pygame frontend are centralized in a frozen `Layout` dataclass with a `compute_layout(multiplayer)` factory function. Dependent values (e.g. scorecard top derived from player bar bottom) are computed automatically so changes cascade without manual updates. Constraint tests catch spatial violations (overlap, overflow) before they ship.

## Testing

```bash
uv run pytest                # Full suite (554 fast + 10 slow)
uv run pytest -m "not slow"  # Fast only (~9s)
make coverage                # With coverage report (80% threshold)
```

| Test file | Tests | What it covers |
|---|---|---|
| `test_game_engine.py` | 219 | Single-player + multiplayer game logic |
| `test_game_coordinator.py` | 153 | State machine, undo, animations, layout constraints, smoke rendering |
| `test_frontend_adapter.py` | 48 | Overlays, zero-confirm, navigation, settings, snapshot |
| `test_web.py` | 57 | WebSocket action dispatch, category lookup |
| `test_ai.py` | 35 | Strategy legality, quality ranking, edge cases |
| `test_dice_tables.py` | 21 | Combinatorics, probabilities, score tables |
| `test_score_history.py` | 16 | Score persistence and retrieval |
| `test_game_log.py` | 8 | Roll/score/hold logging, filtering, multiplayer |
| `test_settings.py` | 7 | Settings persistence, corrupt file handling |

## Benchmarking

```bash
uv run python ai_benchmark.py --strategy optimal --games 200
```
