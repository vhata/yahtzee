# Yahtzee Game

A graphical Yahtzee game implementation using Python and pygame, with a clean separation between game logic and GUI rendering.

## Architecture

This project uses a **testable architecture** with pure game logic separated from GUI rendering:

### Game Engine (`game_engine.py`)
Pure Python game logic with **no pygame dependencies**:
- **Immutable game state**: `GameState` and `DieState` dataclasses
- **Pure functions**: `roll_dice()`, `toggle_die_hold()`, `select_category()`
- **Score calculation**: All 13 Yahtzee categories
- **Fully unit-testable**: 45 tests covering all game logic

### GUI Layer (`main.py`)
Pygame-based graphical interface:
- **Visual rendering**: `DiceSprite` class for dice display
- **Animation effects**: Rolling dice with shake effects
- **Event handling**: Mouse clicks, hovers, keyboard input
- **Delegates all logic** to game_engine

### Tests (`test_game_engine.py`)
Comprehensive unit tests:
- **45 tests** covering all game logic
- **Runs headlessly** - no GUI required
- **Fast execution** (~0.01s for all tests)
- **Integration tests** for complete game flow

## Project Structure

```
yahtzee/
├── main.py              # GUI layer (pygame)
├── game_engine.py       # Pure game logic
├── test_game_engine.py  # Unit tests
├── README.md            # This file
├── README_TESTING.md    # Testing guide
├── PLAN.md              # Development roadmap
├── CLAUDE.md            # Workflow guide for AI agents
└── pyproject.toml       # Dependencies
```

## Setup

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

### Prerequisites
- Python 3.10 or higher
- uv package manager

### Installation

1. Clone the repository
2. Install dependencies:
```bash
uv sync
```

3. (Optional) Install dev dependencies for testing:
```bash
uv sync --extra dev
```

### Running the Game

```bash
uv run python main.py
```

### Running Tests

```bash
# Run all tests
uv run pytest test_game_engine.py -v

# Run with coverage
uv run pytest test_game_engine.py --cov=game_engine

# See README_TESTING.md for more details
```

## Architecture Benefits

**Testability:**
- Test all game logic without pygame
- Fast test execution
- Deterministic testing of game rules

**Maintainability:**
- Clear separation of concerns
- Easy to locate bugs (logic vs rendering)
- Simpler code in each layer

**Extensibility:**
- Add AI players (test strategies without GUI)
- Create alternative UIs (terminal, web)
- Implement replay/undo systems
- Run automated playtesting

## Development

See [PLAN.md](PLAN.md) for the complete development roadmap and history.
See [CLAUDE.md](CLAUDE.md) for workflow guide for AI agents.
See [README_TESTING.md](README_TESTING.md) for testing guide.

## Game Rules

Yahtzee is a dice game where players roll 5 dice up to 3 times per turn, trying to achieve specific combinations to score points across 13 categories.
