# Yahtzee

A graphical Yahtzee game with AI opponents, multiplayer support, and a clean testable architecture.

## Setup

Requires Python 3.10+ and [uv](https://github.com/astral-sh/uv).

```bash
uv sync
uv run python main.py
```

## How to Play

```bash
# Single player
uv run python main.py

# Watch AI play
uv run python main.py --ai --optimal

# Multiplayer (2-4 players, any mix of human/AI)
uv run python main.py --players human optimal
uv run python main.py --players human greedy ev optimal
```

### Controls

| Key / Action | Effect |
|---|---|
| Click dice | Toggle hold |
| 1-5 keys | Toggle hold on die 1-5 |
| Space / ROLL button | Roll dice |
| Click scorecard row | Score category |
| Ctrl+Z / Cmd+Z | Undo (human turns) |
| M | Toggle sound |
| +/- | Adjust AI speed |
| Esc | Quit |

## Features

- Full Yahtzee rules with all 13 categories and upper section bonus
- Dice animation with shake effects
- 2-4 player multiplayer with turn transitions
- Score history persisted to `~/.yahtzee_scores.json`
- Sound effects (synthesized PCM, no external assets)
- Undo for human players
- Three AI speed presets (slow/normal/fast, `--speed` flag)

## AI Strategies

| Strategy | Description | Avg Score |
|---|---|---|
| `random` | Random holds and category picks | ~45 |
| `greedy` | Rule-based: takes good scores, holds promising dice | ~155 |
| `ev` | Monte Carlo simulation over all 32 hold combos | ~219 |
| `optimal` | Exact probability via precomputed dice tables | ~223 |

## Architecture

```
game_engine.py       Pure game logic (immutable GameState, pure functions)
game_coordinator.py  State machine, AI pacing, timers (no pygame)
main.py              Thin pygame rendering shell
ai.py                4 AI strategies + game loop
dice_tables.py       Precomputed dice combinatorics
score_history.py     Score persistence (JSON)
sounds.py            Synthesized PCM sound effects
```

Game logic is fully separated from rendering. `GameState` is an immutable frozen dataclass; all engine functions return new state.

## Testing

```bash
uv run pytest           # full suite (390 tests)
uv run pytest -x -q     # stop on first failure
```

| Test file | Tests | What it covers |
|---|---|---|
| `test_game_engine.py` | 198 | Single-player + multiplayer game logic |
| `test_ai.py` | 35 | Strategy legality, quality ranking, edge cases |
| `test_dice_tables.py` | 21 | Combinatorics, probabilities, score tables |
| `test_game_coordinator.py` | 123 | State machine, undo, animations, integration |
| `test_score_history.py` | 9 | Score persistence and retrieval |

## Benchmarking

```bash
uv run python ai_benchmark.py --strategy optimal --games 200
```
