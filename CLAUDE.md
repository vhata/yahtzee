# Project Conventions

## Architecture

- **game_engine.py** — Pure game logic. `GameState` is immutable (frozen dataclass). All engine functions return new state. No pygame dependency.
- **game_coordinator.py** — `GameCoordinator` owns all game state, timers, AI pacing. No pygame dependency. main.py delegates to this.
- **main.py** — Thin pygame rendering shell. Only owns display/animation concerns.
- **ai.py** — AI strategies implement `YahtzeeStrategy.choose_action()`, returning `RollAction` or `ScoreAction`.
- **dice_tables.py** — Precomputed combinatorics for `OptimalStrategy`.
- **score_history.py** — Score persistence to `~/.yahtzee_scores.json`.
- **sounds.py** — Synthesized PCM waveforms via struct+math (no numpy).

## Development

- **Package manager**: `uv` (not pip)
- **Python**: 3.10+
- **Run game**: `uv run python main.py`
- **Run tests**: `uv run pytest`
- **Benchmark AI**: `uv run python ai_benchmark.py --strategy optimal --games 200`

## Conventions

- Always explain *why* you are making a change
- One feature = one commit with descriptive message
- Test before committing
- Read relevant code before modifying it
- Keep changes minimal and focused
