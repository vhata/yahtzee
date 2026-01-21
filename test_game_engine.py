"""
Unit tests for Yahtzee game engine.
Tests pure game logic without pygame dependencies.
"""
import pytest
import random
from game_engine import (
    DieState, GameState, Category, Scorecard,
    roll_dice, toggle_die_hold, select_category,
    can_roll, can_select_category, reset_game,
    calculate_score, has_yahtzee, has_full_house,
    has_small_straight, has_large_straight, has_n_of_kind
)


# Test Data Structures

def test_die_state_creation():
    """Test creating a DieState"""
    die = DieState(value=5, held=False)
    assert die.value == 5
    assert die.held == False


def test_die_state_immutable():
    """Test that DieState is immutable"""
    die = DieState(value=3, held=False)
    with pytest.raises((AttributeError, Exception)):
        die.value = 6


def test_die_toggle_held():
    """Test toggling held state"""
    die = DieState(value=4, held=False)
    die_held = die.toggle_held()
    assert die_held.held == True
    assert die_held.value == 4  # Value unchanged
    assert die.held == False  # Original unchanged


def test_die_roll_when_not_held():
    """Test that rolling changes value when not held"""
    random.seed(42)  # Deterministic test
    die = DieState(value=1, held=False)
    rolled = die.roll()
    # Should be in valid range
    assert 1 <= rolled.value <= 6
    assert rolled.held == False


def test_die_roll_when_held():
    """Test that rolling preserves value when held"""
    die = DieState(value=6, held=True)
    rolled = die.roll()
    assert rolled.value == 6
    assert rolled.held == True


def test_game_state_creation():
    """Test creating initial game state"""
    state = GameState.create_initial()
    assert len(state.dice) == 5
    assert state.rolls_used == 0
    assert state.current_round == 1
    assert state.game_over == False
    assert isinstance(state.scorecard, Scorecard)


def test_game_state_dice_values_in_range():
    """Test that initial dice values are valid"""
    state = GameState.create_initial()
    for die in state.dice:
        assert 1 <= die.value <= 6
        assert die.held == False


# Test Game Actions

def test_roll_dice_increments_counter():
    """Test that rolling increments the roll counter"""
    state = GameState.create_initial()
    assert state.rolls_used == 0

    state = roll_dice(state)
    assert state.rolls_used == 1

    state = roll_dice(state)
    assert state.rolls_used == 2


def test_roll_dice_respects_held():
    """Test that held dice don't change when rolling"""
    state = GameState.create_initial()
    # Hold first die
    state = toggle_die_hold(state, 0)
    original_value = state.dice[0].value

    # Roll multiple times
    for _ in range(5):
        state = roll_dice(state)
        assert state.dice[0].value == original_value
        assert state.dice[0].held == True


def test_cannot_roll_more_than_three_times():
    """Test that can't roll after 3 rolls"""
    state = GameState.create_initial()

    # Roll 3 times
    state = roll_dice(state)
    state = roll_dice(state)
    state = roll_dice(state)
    assert state.rolls_used == 3

    # Try 4th roll - should be ignored
    rolls_before = state.rolls_used
    state = roll_dice(state)
    assert state.rolls_used == rolls_before  # Still 3


def test_can_roll_validation():
    """Test can_roll helper function"""
    state = GameState.create_initial()
    assert can_roll(state) == True

    # After 3 rolls
    state = roll_dice(roll_dice(roll_dice(state)))
    assert can_roll(state) == False

    # When game over
    from dataclasses import replace
    state = replace(state, game_over=True)
    assert can_roll(state) == False


def test_toggle_die_hold():
    """Test toggling die hold status"""
    state = GameState.create_initial()
    assert state.dice[2].held == False

    state = toggle_die_hold(state, 2)
    assert state.dice[2].held == True

    state = toggle_die_hold(state, 2)
    assert state.dice[2].held == False


def test_toggle_die_invalid_index():
    """Test that invalid die index is handled gracefully"""
    state = GameState.create_initial()
    original_state = state

    state = toggle_die_hold(state, 10)  # Invalid index
    assert state == original_state  # State unchanged


def test_select_category_updates_scorecard():
    """Test selecting a category updates the scorecard"""
    # Create state with all 5s
    dice = tuple(DieState(value=5, held=False) for _ in range(5))
    from dataclasses import replace
    state = GameState.create_initial()
    state = replace(state, dice=dice, rolls_used=1)

    state = select_category(state, Category.FIVES)

    assert state.scorecard.is_filled(Category.FIVES)
    assert state.scorecard.scores[Category.FIVES] == 25  # 5 * 5


def test_select_category_advances_round():
    """Test that selecting category advances to next round"""
    state = GameState.create_initial()
    assert state.current_round == 1

    state = select_category(state, Category.CHANCE)
    assert state.current_round == 2


def test_select_category_resets_turn():
    """Test that selecting category resets turn state"""
    state = GameState.create_initial()
    state = roll_dice(roll_dice(state))  # 2 rolls
    state = toggle_die_hold(state, 0)  # Hold a die

    assert state.rolls_used == 2
    assert state.dice[0].held == True

    state = select_category(state, Category.ONES)

    assert state.rolls_used == 0  # Reset
    assert state.dice[0].held == False  # Reset


def test_cannot_select_filled_category():
    """Test that can't select already filled category"""
    state = GameState.create_initial()
    state = select_category(state, Category.ONES)
    round_after_first = state.current_round

    # Try to select same category again
    state = select_category(state, Category.ONES)
    assert state.current_round == round_after_first  # Round didn't advance


def test_game_ends_after_13_rounds():
    """Test that game ends after all categories filled"""
    state = GameState.create_initial()

    # Fill all 13 categories
    categories = list(Category)
    for cat in categories:
        assert state.game_over == False
        state = select_category(state, cat)

    assert state.game_over == True


def test_reset_game():
    """Test resetting game creates fresh state"""
    state = GameState.create_initial()
    state = roll_dice(state)
    state = select_category(state, Category.CHANCE)

    new_state = reset_game()

    assert new_state.rolls_used == 0
    assert new_state.current_round == 1
    assert new_state.game_over == False
    assert not new_state.scorecard.is_filled(Category.CHANCE)


# Test Scoring Functions

def test_yahtzee_scoring():
    """Test Yahtzee scoring (all same value)"""
    dice = tuple(DieState(value=5, held=False) for _ in range(5))
    score = calculate_score(Category.YAHTZEE, dice)
    assert score == 50


def test_yahtzee_scoring_failure():
    """Test Yahtzee scores 0 when not all same"""
    dice = (
        DieState(5), DieState(5), DieState(5), DieState(5), DieState(4)
    )
    score = calculate_score(Category.YAHTZEE, dice)
    assert score == 0


def test_full_house_scoring():
    """Test full house scoring (3 of one, 2 of another)"""
    dice = (
        DieState(3), DieState(3), DieState(3), DieState(6), DieState(6)
    )
    score = calculate_score(Category.FULL_HOUSE, dice)
    assert score == 25


def test_full_house_scoring_failure():
    """Test full house scores 0 when not 3+2"""
    dice = (
        DieState(3), DieState(3), DieState(3), DieState(3), DieState(6)
    )
    score = calculate_score(Category.FULL_HOUSE, dice)
    assert score == 0


def test_large_straight_scoring():
    """Test large straight scoring (1-2-3-4-5 or 2-3-4-5-6)"""
    dice = (
        DieState(1), DieState(2), DieState(3), DieState(4), DieState(5)
    )
    score = calculate_score(Category.LARGE_STRAIGHT, dice)
    assert score == 40


def test_large_straight_scoring_alt():
    """Test large straight with 2-3-4-5-6"""
    dice = (
        DieState(2), DieState(3), DieState(4), DieState(5), DieState(6)
    )
    score = calculate_score(Category.LARGE_STRAIGHT, dice)
    assert score == 40


def test_small_straight_scoring():
    """Test small straight scoring (4 consecutive)"""
    dice = (
        DieState(1), DieState(2), DieState(3), DieState(4), DieState(6)
    )
    score = calculate_score(Category.SMALL_STRAIGHT, dice)
    assert score == 30


def test_small_straight_in_sequence():
    """Test small straight with 2-3-4-5"""
    dice = (
        DieState(2), DieState(3), DieState(4), DieState(5), DieState(1)
    )
    score = calculate_score(Category.SMALL_STRAIGHT, dice)
    assert score == 30


def test_upper_section_scoring():
    """Test upper section categories (sum of matching dice)"""
    dice = (
        DieState(3), DieState(3), DieState(5), DieState(3), DieState(1)
    )
    score = calculate_score(Category.THREES, dice)
    assert score == 9  # Three 3s


def test_upper_section_all_categories():
    """Test all upper section categories"""
    dice = (
        DieState(1), DieState(2), DieState(3), DieState(4), DieState(5)
    )
    assert calculate_score(Category.ONES, dice) == 1
    assert calculate_score(Category.TWOS, dice) == 2
    assert calculate_score(Category.THREES, dice) == 3
    assert calculate_score(Category.FOURS, dice) == 4
    assert calculate_score(Category.FIVES, dice) == 5
    assert calculate_score(Category.SIXES, dice) == 0


def test_chance_scoring():
    """Test chance scoring (sum of all dice)"""
    dice = (
        DieState(1), DieState(2), DieState(3), DieState(4), DieState(5)
    )
    score = calculate_score(Category.CHANCE, dice)
    assert score == 15


def test_three_of_kind_scoring():
    """Test 3 of a kind scoring (sum all dice if 3+ match)"""
    dice = (
        DieState(4), DieState(4), DieState(4), DieState(2), DieState(1)
    )
    score = calculate_score(Category.THREE_OF_KIND, dice)
    assert score == 15  # Sum all: 4+4+4+2+1


def test_three_of_kind_scoring_failure():
    """Test 3 of a kind scores 0 when only 2 match"""
    dice = (
        DieState(4), DieState(4), DieState(3), DieState(2), DieState(1)
    )
    score = calculate_score(Category.THREE_OF_KIND, dice)
    assert score == 0


def test_four_of_kind_scoring():
    """Test 4 of a kind scoring (sum all dice if 4+ match)"""
    dice = (
        DieState(6), DieState(6), DieState(6), DieState(6), DieState(2)
    )
    score = calculate_score(Category.FOUR_OF_KIND, dice)
    assert score == 26  # Sum all: 6+6+6+6+2


def test_upper_section_bonus():
    """Test upper section bonus calculation"""
    scorecard = Scorecard()
    # Fill upper section with values totaling >= 63
    scorecard.set_score(Category.ONES, 3)
    scorecard.set_score(Category.TWOS, 6)
    scorecard.set_score(Category.THREES, 9)
    scorecard.set_score(Category.FOURS, 12)
    scorecard.set_score(Category.FIVES, 15)
    scorecard.set_score(Category.SIXES, 18)

    assert scorecard.get_upper_section_total() == 63
    assert scorecard.get_upper_section_bonus() == 35


def test_upper_section_no_bonus():
    """Test no bonus when upper section < 63"""
    scorecard = Scorecard()
    scorecard.set_score(Category.ONES, 1)
    scorecard.set_score(Category.TWOS, 2)

    assert scorecard.get_upper_section_total() == 3
    assert scorecard.get_upper_section_bonus() == 0


def test_scorecard_grand_total():
    """Test grand total calculation"""
    scorecard = Scorecard()
    scorecard.set_score(Category.ONES, 3)
    scorecard.set_score(Category.YAHTZEE, 50)

    total = scorecard.get_grand_total()
    assert total == 53  # 3 + 0 (no bonus) + 50


# Test Helper Functions

def test_has_n_of_kind():
    """Test has_n_of_kind helper"""
    dice = (
        DieState(3), DieState(3), DieState(3), DieState(1), DieState(2)
    )
    assert has_n_of_kind(dice, 3) == True
    assert has_n_of_kind(dice, 4) == False
    assert has_n_of_kind(dice, 2) == True


def test_has_yahtzee():
    """Test has_yahtzee helper"""
    all_fives = tuple(DieState(5) for _ in range(5))
    assert has_yahtzee(all_fives) == True

    mixed = (DieState(5), DieState(5), DieState(5), DieState(5), DieState(1))
    assert has_yahtzee(mixed) == False


def test_has_full_house():
    """Test has_full_house helper"""
    full_house = (DieState(2), DieState(2), DieState(3), DieState(3), DieState(3))
    assert has_full_house(full_house) == True

    not_full_house = (DieState(2), DieState(2), DieState(2), DieState(3), DieState(4))
    assert has_full_house(not_full_house) == False


def test_has_small_straight():
    """Test has_small_straight helper"""
    straight = (DieState(1), DieState(2), DieState(3), DieState(4), DieState(6))
    assert has_small_straight(straight) == True

    not_straight = (DieState(1), DieState(2), DieState(4), DieState(5), DieState(6))
    assert has_small_straight(not_straight) == False


def test_has_large_straight():
    """Test has_large_straight helper"""
    straight = (DieState(1), DieState(2), DieState(3), DieState(4), DieState(5))
    assert has_large_straight(straight) == True

    not_straight = (DieState(1), DieState(2), DieState(3), DieState(4), DieState(6))
    assert has_large_straight(not_straight) == False


# Integration Tests

def test_complete_game_flow():
    """Integration test: play a complete game programmatically"""
    state = GameState.create_initial()

    # Play 13 rounds
    for round_num in range(1, 14):
        assert state.current_round == round_num
        assert not state.game_over

        # Roll dice 3 times
        state = roll_dice(state)
        state = roll_dice(state)
        state = roll_dice(state)
        assert state.rolls_used == 3

        # Select first available category
        for cat in Category:
            if not state.scorecard.is_filled(cat):
                state = select_category(state, cat)
                break

    # Game should be over
    assert state.game_over == True
    assert state.scorecard.is_complete()

    # Grand total should be calculated
    total = state.scorecard.get_grand_total()
    assert total >= 0  # Valid score


def test_held_dice_across_rolls():
    """Test that holding dice persists across multiple rolls"""
    state = GameState.create_initial()

    # Hold dice 0 and 2
    state = toggle_die_hold(state, 0)
    state = toggle_die_hold(state, 2)

    original_val_0 = state.dice[0].value
    original_val_2 = state.dice[2].value

    # Roll multiple times
    state = roll_dice(state)
    assert state.dice[0].value == original_val_0
    assert state.dice[2].value == original_val_2

    state = roll_dice(state)
    assert state.dice[0].value == original_val_0
    assert state.dice[2].value == original_val_2

    state = roll_dice(state)
    assert state.dice[0].value == original_val_0
    assert state.dice[2].value == original_val_2


def test_scorecard_copy():
    """Test that scorecard copy works correctly"""
    original = Scorecard()
    original.set_score(Category.ONES, 5)

    copy = original.copy()
    copy.set_score(Category.TWOS, 10)

    # Original should not be affected
    assert original.scores[Category.TWOS] is None
    assert copy.scores[Category.ONES] == 5
    assert copy.scores[Category.TWOS] == 10


def test_scorecard_with_score():
    """Test that with_score returns new scorecard"""
    original = Scorecard()
    original.set_score(Category.ONES, 5)

    new = original.with_score(Category.TWOS, 10)

    # New scorecard has both scores
    assert new.scores[Category.ONES] == 5
    assert new.scores[Category.TWOS] == 10

    # Original only has first score
    assert original.scores[Category.ONES] == 5
    assert original.scores[Category.TWOS] is None
