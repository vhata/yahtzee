# Yahtzee Game Development Plan

This document outlines the step-by-step plan for building a Yahtzee game using pygame with graphics.

## Project Overview
- **Technology**: Python with pygame
- **Environment**: uv-managed virtualenv
- **Development Approach**: Small, incremental commits for each feature

---

## Development Steps

### Step 1: Project Setup
- Create `pyproject.toml` for uv dependency management
- Add `.gitignore` (virtualenv, __pycache__, etc.)
- Initialize uv virtualenv and add pygame dependency
- Basic README with setup instructions

**Deliverable**: Project can be cloned and set up with `uv sync`

---

### Step 2: Basic Pygame Window
- Create `main.py` with pygame initialization
- Set up game loop with event handling and display
- Window sizing and basic structure

**Deliverable**: Running game shows empty window with proper game loop

---

### Step 3: Dice Class & Graphics
- Implement `Dice` class to represent a single die
- Draw dice faces graphically (dots for 1-6)
- Render 5 dice on screen in a row

**Deliverable**: 5 dice displayed on screen with visible faces

---

### Step 4: Dice Rolling Mechanics
- Add rolling animation (visual feedback)
- Random number generation for dice values
- "Roll" button to trigger rolling

**Deliverable**: Clicking "Roll" button randomizes all dice values

---

### Step 5: Dice Selection UI
- Implement click-to-hold/release dice functionality
- Visual indicator for held dice (highlight or different color)
- Held dice don't re-roll on subsequent rolls

**Deliverable**: Can click dice to hold/release, held dice stay constant when rolling

---

### Step 6: Scorecard Data Structure
- Create score category classes (Ones, Twos, etc.)
- Validation logic to check which categories are valid for current dice
- Data model to track filled vs available categories

**Deliverable**: Backend data structure for managing scorecard state

---

### Step 7: Score Calculation Logic
- Implement scoring algorithms for all 13 categories:
  - **Upper section**: Ones, Twos, Threes, Fours, Fives, Sixes
  - **Lower section**: 3 of a Kind, 4 of a Kind, Full House, Small Straight, Large Straight, Yahtzee, Chance

**Deliverable**: Given dice values, can calculate score for any category

---

### Step 8: Scorecard UI Rendering
- Display all 13 categories on screen
- Show current score and potential scores for available categories
- Visual layout for upper/lower sections and totals

**Deliverable**: Scorecard visible on screen with all categories

---

### Step 9: Turn Management
- Enforce 3-roll maximum per turn
- Track roll count and disable roll button after 3rd roll
- Reset turn state after scoring

**Deliverable**: Game enforces 3-roll limit per turn

---

### Step 10: Score Selection
- Click on scorecard category to lock in score
- Validate that category is available
- Update scorecard and move to next turn

**Deliverable**: Can select and lock in scores, scorecard updates correctly

---

### Step 11: Game Flow
- Implement 13-round game loop
- Calculate upper section bonus (35 points if upper section >= 63)
- Track game state (current round, game over)

**Deliverable**: Full 13-round game plays from start to finish

---

### Step 12: Game Over Screen
- Display final total score
- Show game summary
- "Play Again" button to restart

**Deliverable**: Game ends properly with final score display

---

### Step 13: Visual Polish
- Improve colors and fonts
- Add hover effects on buttons and scorecard
- Better spacing and layout
- Animation improvements

**Deliverable**: Polished, visually appealing game

---

## Progress Tracking - Development Steps

- [x] Step 1: Project Setup
- [x] Step 2: Basic Pygame Window
- [x] Step 3: Dice Class & Graphics
- [x] Step 4: Dice Rolling Mechanics
- [x] Step 5: Dice Selection UI
- [x] Step 6: Scorecard Data Structure
- [x] Step 7: Score Calculation Logic
- [x] Step 8: Scorecard UI Rendering
- [x] Step 9: Turn Management
- [x] Step 10: Score Selection
- [x] Step 11: Game Flow
- [x] Step 12: Game Over Screen
- [x] Step 13: Visual Polish

---

# Quality Assurance & Bug Fixes

After completing all 13 development steps, the game underwent QA testing to identify and fix issues.

---

## Bug Fix 1: Dice Layout Overlap (commit d7d5f2a)

**Issue Discovered**: 2.5 dice were hidden behind the scorecard panel

**Root Cause**: Dice were centered horizontally on screen, causing overlap with the right-side scorecard panel

**Fix Applied**:
- Repositioned dice to left side of screen (starting at x=80 instead of centered)
- Moved roll button to align with dice area
- Adjusted "Rolls left" text position to left side
- All UI elements now properly spaced without overlap

**Deliverable**: All 5 dice fully visible on left side, scorecard clearly visible on right

---

## Bug Fix 2: Roll Animation Not Pronounced (commit d7d5f2a)

**Issue Discovered**: Roll animation was too fast and subtle - hard to notice dice were rolling

**Root Cause**:
- Animation duration only 0.5 seconds (30 frames at 60 FPS)
- Only visual feedback was rapidly changing numbers
- No physical motion or shake effect

**Fix Applied**:
- Increased animation duration from 30 to 60 frames (0.5s → 1.0s)
- Added shake/wobble effect to unheld dice during rolling animation
- Implemented sine/cosine wave calculations for smooth shaking motion
- Held dice remain stationary during animation (reinforces selection feedback)
- Added math module import for animation calculations

**Deliverable**: Dice have pronounced, satisfying shake effect while rolling; clear visual feedback that rolling is happening

---

## Progress Tracking - Bug Fixes

- [x] Bug Fix 1: Dice Layout Overlap
- [x] Bug Fix 2: Roll Animation Not Pronounced

---

## Notes

Each step is designed to be:
- Independently testable
- Committable to git
- Buildable on previous steps
- Small enough to complete in one session

## Development Process

This project followed a structured development approach:

1. **Planning**: Created comprehensive step-by-step plan
2. **Implementation**: Built features incrementally with git commits per step (Steps 1-13)
3. **Quality Assurance**: Tested complete game to identify issues
4. **Bug Fixes**: Addressed discovered issues with documented fixes

This methodology ensures:
- Clear progress tracking
- Easy rollback if needed
- Documented decision history
- Quality validation before completion

5. **Workflow Documentation**: Created CLAUDE.md to document the development process and workflow for future AI agents

**Total Commits**: 16 (13 feature steps + 1 visual polish + 1 bug fix commit + 1 workflow documentation)

---

# Phase 2: Architecture Refactoring for Testability

After completing the initial implementation and bug fixes, the game underwent a major refactoring to separate game logic from GUI rendering, enabling unit testing without pygame dependencies.

## Motivation

**Problem**: Game logic is tightly coupled with pygame rendering code in main.py (808 lines):
- `Dice` class mixes state (value, held) with rendering (draw method)
- `YahtzeeGame` class combines state management, game logic, event handling, and rendering
- Impossible to test game rules without creating a pygame window
- Difficult to add features like AI players, replay system, or alternative UIs

**Goal**: Create a testable architecture where:
- Pure game logic exists in separate module with no pygame dependencies
- GUI layer calls logic functions and renders results
- Complete game can be tested headlessly with unit tests
- Backend state updates are testable independently of visual rendering

## Refactoring Architecture

### New Structure
- **game_engine.py**: Pure Python game logic, immutable state, no pygame
  - `DieState` dataclass: value (1-6) + held flag
  - `GameState` dataclass: 5 dice, scorecard, rolls_used, current_round, game_over
  - Pure functions: `roll_dice()`, `toggle_die_hold()`, `select_category()`, etc.
  - All scoring functions (moved from main.py)

- **main.py**: Thin GUI layer (reduces from 808 to ~400 lines)
  - `DiceSprite` class: Visual rendering only (position + draw)
  - `YahtzeeGame` class: Delegates logic to game_engine, handles events and rendering

- **test_game_engine.py**: Comprehensive unit tests
  - 30+ tests covering all game logic
  - No pygame dependencies - runs headlessly
  - Tests state transitions, scoring, game flow

### Key Design Decisions
- **Immutable State (Copy-on-Write)**: All game actions return new GameState
- **Separation of Concerns**: DieState (logic) vs DiceSprite (rendering)
- **Pure Functions**: Testable without side effects
- **Duck Typing**: Scoring functions work with both Dice and DieState objects

---

## Refactoring Step 1: Create game_engine.py - Data Structures

Create pure game logic module with data structures.

**Actions**:
- Create `game_engine.py`
- Move from main.py:
  - `Category` enum
  - `Scorecard` class
  - All scoring functions: `count_values`, `has_*`, `calculate_score`
- Add new immutable data structures:
  - `DieState(value, held)` - frozen dataclass with `roll()` and `toggle_held()` methods
  - `GameState(dice, scorecard, rolls_used, current_round, game_over)` - frozen dataclass
  - `GameState.create_initial()` - static factory method
- Update scoring functions: Work with any object with `.value` attribute (duck typing)
- Add `Scorecard.copy()` and `Scorecard.with_score()` helper methods

**Testing**:
- Import in main.py: `from game_engine import Category, Scorecard, calculate_score`
- Run game: `uv run python main.py`
- Game should work identically (just using imported versions)

**Deliverable**: game_engine.py exists with pure data structures, main.py still works

---

## Refactoring Step 2: Add Pure Game Action Functions

Add game logic functions to game_engine.py.

**Actions**:
Add to game_engine.py:
- `roll_dice(state: GameState) -> GameState` - Roll unheld dice, increment rolls_used
- `toggle_die_hold(state: GameState, die_index: int) -> GameState` - Toggle hold status
- `select_category(state: GameState, category: Category) -> GameState` - Lock score, advance round, reset turn
- `can_roll(state: GameState) -> bool` - Check if player can roll
- `can_select_category(state: GameState, category: Category) -> bool` - Check if category available
- `reset_game() -> GameState` - Return fresh GameState

All functions return new immutable GameState (copy-on-write pattern).

**Testing**:
- Run game: `uv run python main.py`
- Game should still work (functions not used yet)

**Deliverable**: game_engine.py has complete game logic API

---

## Refactoring Step 3: Write Comprehensive Unit Tests

Create test suite for game engine.

**Actions**:
- Update `pyproject.toml`: Add `pytest>=7.0.0` to dev dependencies
- Create `test_game_engine.py` with tests:
  - Data structure tests: DieState, GameState immutability
  - Roll dice tests: Increments counter, respects held, max 3 rolls
  - Toggle hold tests: Updates die, invalid index handling
  - Category selection tests: Updates scorecard, advances round, resets turn
  - Game over tests: Ends after 13 categories
  - Scoring tests: All 13 categories
  - Integration tests: Complete 13-round game flow, held dice persistence

**Testing**:
- Install dev dependencies: `uv sync --extra dev`
- Run tests: `uv run pytest test_game_engine.py -v`
- All tests should pass

**Deliverable**: Comprehensive test suite proving game logic works headlessly

---

## Refactoring Step 4: Add DiceSprite Class

Create rendering-only class for dice visualization.

**Actions**:
- Create `DiceSprite` class in main.py:
  - `__init__(x, y)` - Store position only
  - `draw(surface, die_state, offset_x, offset_y)` - Render based on DieState
  - `contains_point(pos)` - Click detection
  - `_draw_dots()` - Move dot rendering logic from Dice class
- Keep old `Dice` class temporarily for compatibility

**Testing**:
- Run game: `uv run python main.py`
- Game should work identically

**Deliverable**: DiceSprite class ready for YahtzeeGame refactoring

---

## Refactoring Step 5: Refactor YahtzeeGame to Use GameState

Major refactoring - update YahtzeeGame to delegate all logic to game_engine.

**Actions**:
1. Update imports to use game_engine functions
2. Replace state variables with `self.state = GameState.create_initial()`
3. Create `self.dice_sprites` for visual rendering (replace `self.dice`)
4. Update `roll_dice()` to call `engine_roll_dice(self.state)`
5. Update `update()` to commit state after animation
6. Update event handlers to use engine functions for die clicks and category selection
7. Update `draw()` to render based on `self.state`
8. Update `draw_scorecard()` and `draw_game_over()` to use `self.state`
9. Remove old `Dice` class and direct state variables

**Testing**:
- Run game: `uv run python main.py`
- Complete playthrough: roll, hold, select categories, verify behavior unchanged

**Deliverable**: main.py uses GameState, all logic delegated to game_engine

---

## Refactoring Step 6: Clean Up and Add Integration Tests

Remove duplication and add high-level integration tests.

**Actions**:
- Remove duplicated code between files
- Verify all imports correct
- Add integration tests:
  - `test_complete_game_flow()` - Play 13 full rounds programmatically
  - `test_held_dice_across_rolls()` - Verify holding persists

**Testing**:
- Run all tests: `uv run pytest test_game_engine.py -v`
- Run game: Full manual playthrough

**Deliverable**: Clean codebase, integration tests verify complete game flow

---

## Refactoring Step 7: Add Testing Documentation

Document testing approach and create manual testing checklist.

**Actions**:
- Create `README_TESTING.md`:
  - How to run tests
  - Test organization
  - Manual GUI testing checklist
  - Coverage goals

**Testing**:
- Run tests with manual checklist verification

**Deliverable**: Testing documentation

---

## Refactoring Step 8: Final Verification and Documentation

Update project documentation and verify complete refactoring.

**Actions**:
- Update `README.md`: Add architecture section, project structure, testing instructions
- Update `pyproject.toml`: Add `pytest-cov>=4.0.0` to dev dependencies
- Run final verification: All tests pass, complete manual playthrough

**Testing**:
- All unit tests pass
- No regressions in behavior

**Deliverable**: Fully refactored, tested, documented architecture

---

## Progress Tracking - Refactoring Steps

- [x] Refactoring Step 1: Create game_engine.py - Data Structures
- [x] Refactoring Step 2: Add Pure Game Action Functions
- [x] Refactoring Step 3: Write Comprehensive Unit Tests
- [x] Refactoring Step 4: Add DiceSprite Class
- [x] Refactoring Step 5: Refactor YahtzeeGame to Use GameState
- [x] Refactoring Step 6: Clean Up and Add Integration Tests
- [x] Refactoring Step 7: Add Testing Documentation
- [ ] Refactoring Step 8: Final Verification and Documentation

---

## Refactoring Benefits

**Testability**:
- Can test all game logic without pygame window
- Fast test execution (no graphics initialization)
- 30+ unit tests covering all logic paths

**Maintainability**:
- Clear separation of concerns (logic vs rendering)
- Easy to locate bugs (state logic vs visual bugs)
- Simpler code in each layer

**Extensibility**:
- Can add AI players (test strategies without GUI)
- Can create alternative UIs (terminal, web)
- Can implement replay/undo systems
- Can run automated playtesting
