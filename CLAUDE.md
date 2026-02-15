# Project Conventions

## Architecture

**IMPORTANT: Strict separation between game logic and UI.** Only `main.py` and `sounds.py` may import pygame. All other modules must remain pure Python with no pygame dependency. This enables headless testing and keeps the engine reusable.

- **game_engine.py** — Pure game logic. `GameState` is immutable (frozen dataclass). All engine functions return new state. **No pygame.**
- **game_coordinator.py** — `GameCoordinator` owns all game state, timers, AI pacing. **No pygame.** main.py delegates to this.
- **main.py** — Thin pygame rendering shell. Only owns display/animation concerns.
- **ai.py** — AI strategies implement `YahtzeeStrategy.choose_action()`, returning `RollAction` or `ScoreAction`. **No pygame.**
- **dice_tables.py** — Precomputed combinatorics for `OptimalStrategy`. **No pygame.**
- **score_history.py** — Score persistence to `~/.yahtzee_scores.json`. **No pygame.**
- **sounds.py** — Synthesized PCM waveforms via struct+math (no numpy). Uses pygame.mixer for playback only.

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
