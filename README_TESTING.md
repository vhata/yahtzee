# Testing Guide

## Running Tests

### Run all tests
```bash
uv run pytest test_game_engine.py -v
```

### Run specific test
```bash
uv run pytest test_game_engine.py::test_yahtzee_scoring -v
```

### Run with coverage (requires pytest-cov)
```bash
uv run pytest test_game_engine.py --cov=game_engine --cov-report=html
```

## Test Organization

### Unit Tests (test_game_engine.py)

Tests pure game logic without any GUI dependencies - **45 tests total**:

**Data Structure Tests (7 tests)**
- DieState creation, immutability, rolling, held state
- GameState creation, dice value validation

**Game Action Tests (12 tests)**
- Roll dice: increments counter, respects held, max 3 rolls
- Toggle hold: updates die, handles invalid indices
- Category selection: updates scorecard, advances round, resets turn
- Validation: can_roll, can_select_category
- Game over: ends after 13 categories
- Reset game functionality

**Scoring Tests (20 tests)**
- All 13 Yahtzee categories tested
- Upper section: Ones through Sixes
- Lower section: 3/4 of a Kind, Full House, Straights, Yahtzee, Chance
- Helper functions: has_n_of_kind, has_yahtzee, has_full_house, etc.
- Upper section bonus calculation (35 if >= 63)
- Grand total calculation

**Integration Tests (4 tests)**
- Complete 13-round game flow
- Held dice persistence across rolls
- Scorecard copy and with_score methods

**Key Testing Features:**
- No pygame dependencies - runs headlessly
- Fast execution (~0.01s for all tests)
- Deterministic testing of random elements
- Tests both success and failure cases

### Manual GUI Testing

Since pygame GUI is difficult to test automatically, use this checklist for manual testing:

#### Basic Gameplay
- [ ] Game launches without errors
- [ ] Window displays correctly with title, dice, scorecard

#### Dice Rolling
- [ ] Click "ROLL" button - dice values change
- [ ] Roll animation shows shake effect (1 second duration)
- [ ] Unheld dice change values, held dice stay constant
- [ ] Roll button disabled after 3 rolls
- [ ] "Rolls left" counter decrements correctly (3 → 2 → 1 → 0)

#### Dice Holding
- [ ] Click dice to hold - green border appears
- [ ] Click held die again - green border disappears
- [ ] Held dice don't change when rolling
- [ ] Can hold/unhold any combination of dice
- [ ] Held status resets after scoring category

#### Scorecard
- [ ] All 13 categories visible on right side
- [ ] Hover over unfilled category - highlights in blue
- [ ] Potential scores show in green (valid) or gray (zero)
- [ ] Click category - locks in score
- [ ] Filled categories show score in black
- [ ] Can't select already-filled category
- [ ] Upper section total updates correctly
- [ ] Bonus shows 35 when upper section >= 63, else 0
- [ ] Grand total calculates correctly

#### Scoring Validation
Test each category scores correctly:
- [ ] Ones through Sixes: Sum of matching dice
- [ ] 3 of a Kind: Sum all dice if 3+ match
- [ ] 4 of a Kind: Sum all dice if 4+ match
- [ ] Full House: 25 if 3 of one + 2 of another
- [ ] Small Straight: 30 if 4 consecutive (1-2-3-4, 2-3-4-5, or 3-4-5-6)
- [ ] Large Straight: 40 if 5 consecutive (1-2-3-4-5 or 2-3-4-5-6)
- [ ] Yahtzee: 50 if all 5 dice match
- [ ] Chance: Sum of all dice

#### Turn Management
- [ ] After selecting category, round advances (Round 1/13 → Round 2/13)
- [ ] Rolls reset to 0 after scoring
- [ ] Dice unheld after scoring
- [ ] Roll button re-enabled after scoring

#### Game Flow
- [ ] Game lasts exactly 13 rounds
- [ ] After round 13, game over screen appears
- [ ] Game over screen shows final score
- [ ] Breakdown shows upper section, bonus, lower section
- [ ] "PLAY AGAIN" button appears
- [ ] Click play again - game resets to Round 1/13

#### Edge Cases
- [ ] Can't roll when game is over
- [ ] Can't select categories when game is over
- [ ] Scorecard correctly disabled when all categories filled
- [ ] No crashes or visual glitches

## Test Coverage Goals

- **game_engine.py**: 100% coverage (pure logic must be fully tested)
- **main.py**: Manual testing only (GUI tested visually)

## Adding New Tests

### For new game logic

Add tests to `test_game_engine.py`:

```python
def test_new_feature():
    """Test description of what this verifies"""
    state = GameState.create_initial()
    # ... test code
    assert expected_behavior
```

### For deterministic testing

Use `random.seed()` when testing randomness:

```python
import random

def test_dice_roll_deterministic():
    random.seed(42)  # Makes random predictable
    die = DieState(value=1, held=False)
    rolled = die.roll()
    # Now behavior is predictable for testing
    assert 1 <= rolled.value <= 6
```

### For state immutability

Always test that original state is unchanged:

```python
def test_state_immutability():
    original_state = GameState.create_initial()
    new_state = roll_dice(original_state)

    # Original state should be unchanged
    assert original_state.rolls_used == 0
    assert new_state.rolls_used == 1
```

## Common Test Patterns

### Testing scoring with specific dice

```python
dice = (
    DieState(5), DieState(5), DieState(5), DieState(2), DieState(1)
)
score = calculate_score(Category.FIVES, dice)
assert score == 15  # 5 + 5 + 5
```

### Testing game flow

```python
state = GameState.create_initial()
state = roll_dice(state)  # Roll 1
state = toggle_die_hold(state, 0)  # Hold first die
state = roll_dice(state)  # Roll 2
state = select_category(state, Category.CHANCE)  # Score
assert state.current_round == 2  # Advanced to next round
```

### Testing edge cases

```python
# Test invalid input is handled gracefully
state = GameState.create_initial()
original_state = state
state = toggle_die_hold(state, 99)  # Invalid index
assert state == original_state  # State unchanged
```

## Debugging Failed Tests

### View test output in detail
```bash
uv run pytest test_game_engine.py -vv
```

### Run single test with print statements
```bash
uv run pytest test_game_engine.py::test_name -s
```

### Use pytest's built-in debugging
```bash
uv run pytest test_game_engine.py --pdb
```

## Continuous Integration

To run tests in CI/CD pipeline:

```bash
# Install dependencies
uv sync --extra dev

# Run tests with exit code
uv run pytest test_game_engine.py -v

# Generate coverage report
uv run pytest test_game_engine.py --cov=game_engine --cov-fail-under=95
```

## Test Maintenance

- Run tests after every code change
- Keep tests focused and independent
- Test one behavior per test function
- Use descriptive test names
- Update tests when requirements change
- Remove obsolete tests
