"""
Exhaustive Yahtzee Rules Test Suite

This test file is the authoritative specification of Yahtzee game rules.
Every rule has both positive tests (what IS allowed) and negative tests
(what is NOT allowed). If a behavior isn't tested here, it isn't guaranteed.

Sections:
    1. Dice — values, immutability, rolling, holding
    2. Game Setup — initial state, reset
    3. Rolling — when allowed, what changes, limits
    4. Holding Dice — when allowed, toggling, persistence
    5. Scoring a Category — when allowed, what it calculates, turn transitions
    6. Scoring Rules — every category's formula, positive and negative cases
    7. Scorecard — upper/lower sections, bonus, grand total
    8. Game Flow — full game, round progression, game over
"""
import pytest
import random
from dataclasses import replace

from game_engine import (
    DieState, GameState, Category, Scorecard,
    roll_dice, toggle_die_hold, select_category,
    can_roll, can_select_category, reset_game,
    calculate_score, calculate_score_in_context,
    has_yahtzee, has_full_house,
    has_small_straight, has_large_straight, has_n_of_kind,
    MultiplayerGameState,
    mp_roll_dice, mp_toggle_die_hold, mp_select_category,
    mp_can_roll, mp_can_select_category, mp_get_current_scorecard,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_dice(*values):
    """Create a tuple of DieState from integer values."""
    return tuple(DieState(value=v) for v in values)


def state_with_dice(*values, rolls_used=1):
    """Create a GameState with specific dice values and rolls_used.
    Defaults to rolls_used=1 so that scoring/holding are legal."""
    state = GameState.create_initial()
    return replace(state, dice=make_dice(*values), rolls_used=rolls_used)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. DICE
#    Rule: Each die has a value from 1 to 6 and a held/unheld status.
#    Rule: DieState is immutable — operations return new instances.
# ═══════════════════════════════════════════════════════════════════════════════

class TestDieState:

    def test_die_has_value_and_held_status(self):
        die = DieState(value=3, held=False)
        assert die.value == 3
        assert die.held is False

    def test_die_defaults_to_unheld(self):
        die = DieState(value=4)
        assert die.held is False

    def test_die_is_immutable(self):
        die = DieState(value=3, held=False)
        with pytest.raises((AttributeError, Exception)):
            die.value = 6

    def test_rolling_unheld_die_produces_value_1_through_6(self):
        die = DieState(value=1, held=False)
        seen = set()
        for seed in range(200):
            random.seed(seed)
            seen.add(die.roll().value)
        assert seen == {1, 2, 3, 4, 5, 6}

    def test_rolling_unheld_die_does_not_hold_it(self):
        die = DieState(value=1, held=False)
        assert die.roll().held is False

    def test_rolling_held_die_preserves_value(self):
        for v in range(1, 7):
            die = DieState(value=v, held=True)
            assert die.roll().value == v

    def test_rolling_held_die_keeps_it_held(self):
        die = DieState(value=5, held=True)
        assert die.roll().held is True

    def test_toggle_held_flips_false_to_true(self):
        die = DieState(value=4, held=False)
        assert die.toggle_held().held is True

    def test_toggle_held_flips_true_to_false(self):
        die = DieState(value=4, held=True)
        assert die.toggle_held().held is False

    def test_toggle_held_preserves_value(self):
        die = DieState(value=6, held=False)
        assert die.toggle_held().value == 6

    def test_toggle_held_returns_new_instance(self):
        die = DieState(value=4, held=False)
        toggled = die.toggle_held()
        assert die.held is False  # original unchanged


# ═══════════════════════════════════════════════════════════════════════════════
# 2. GAME SETUP
#    Rule: A new game starts with 5 dice (values 1-6, all unheld),
#          rolls_used=0, round 1, game not over, all categories empty.
# ═══════════════════════════════════════════════════════════════════════════════

class TestGameSetup:

    def test_initial_state_has_five_dice(self):
        state = GameState.create_initial()
        assert len(state.dice) == 5

    def test_initial_dice_values_are_1_through_6(self):
        state = GameState.create_initial()
        for die in state.dice:
            assert 1 <= die.value <= 6

    def test_initial_dice_are_all_unheld(self):
        state = GameState.create_initial()
        for die in state.dice:
            assert die.held is False

    def test_initial_rolls_used_is_zero(self):
        state = GameState.create_initial()
        assert state.rolls_used == 0

    def test_initial_round_is_one(self):
        state = GameState.create_initial()
        assert state.current_round == 1

    def test_initial_game_is_not_over(self):
        state = GameState.create_initial()
        assert state.game_over is False

    def test_initial_scorecard_is_all_empty(self):
        state = GameState.create_initial()
        for cat in Category:
            assert not state.scorecard.is_filled(cat)

    def test_reset_game_returns_fresh_state(self):
        state = GameState.create_initial()
        state = roll_dice(state)
        state = select_category(state, Category.CHANCE)

        fresh = reset_game()
        assert fresh.rolls_used == 0
        assert fresh.current_round == 1
        assert fresh.game_over is False
        for cat in Category:
            assert not fresh.scorecard.is_filled(cat)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. ROLLING
#    Rule: Player gets up to 3 rolls per turn.
#    Rule: Rolling re-randomizes unheld dice and increments rolls_used.
#    Rule: Cannot roll when game is over.
#    Rule: Cannot roll after 3 rolls used.
# ═══════════════════════════════════════════════════════════════════════════════

class TestRolling:

    # ── What's allowed ──

    def test_can_roll_at_start_of_turn(self):
        state = GameState.create_initial()
        assert can_roll(state) is True

    def test_first_roll_sets_rolls_used_to_1(self):
        state = GameState.create_initial()
        state = roll_dice(state)
        assert state.rolls_used == 1

    def test_second_roll_sets_rolls_used_to_2(self):
        state = GameState.create_initial()
        state = roll_dice(roll_dice(state))
        assert state.rolls_used == 2

    def test_third_roll_sets_rolls_used_to_3(self):
        state = GameState.create_initial()
        state = roll_dice(roll_dice(roll_dice(state)))
        assert state.rolls_used == 3

    def test_can_roll_after_1_roll(self):
        state = roll_dice(GameState.create_initial())
        assert can_roll(state) is True

    def test_can_roll_after_2_rolls(self):
        state = roll_dice(roll_dice(GameState.create_initial()))
        assert can_roll(state) is True

    def test_roll_produces_values_1_through_6(self):
        seen = set()
        for seed in range(200):
            random.seed(seed)
            state = roll_dice(GameState.create_initial())
            for die in state.dice:
                seen.add(die.value)
        assert seen == {1, 2, 3, 4, 5, 6}

    def test_roll_does_not_change_held_dice(self):
        state = GameState.create_initial()
        state = roll_dice(state)
        state = toggle_die_hold(state, 0)
        val = state.dice[0].value

        state = roll_dice(state)
        assert state.dice[0].value == val
        assert state.dice[0].held is True

    def test_roll_leaves_dice_unheld_by_default(self):
        state = roll_dice(GameState.create_initial())
        for die in state.dice:
            assert die.held is False

    # ── What's forbidden ──

    def test_cannot_roll_after_3_rolls(self):
        state = roll_dice(roll_dice(roll_dice(GameState.create_initial())))
        assert can_roll(state) is False

    def test_fourth_roll_is_no_op(self):
        state = roll_dice(roll_dice(roll_dice(GameState.create_initial())))
        before = state
        after = roll_dice(state)
        assert after.rolls_used == 3
        assert after.dice == before.dice

    def test_cannot_roll_when_game_over(self):
        state = replace(GameState.create_initial(), game_over=True)
        assert can_roll(state) is False
        after = roll_dice(state)
        assert after == state


# ═══════════════════════════════════════════════════════════════════════════════
# 4. HOLDING DICE
#    Rule: After rolling at least once, player may hold/unhold any die.
#    Rule: Held dice keep their value on the next roll.
#    Rule: Cannot hold dice before the first roll of a turn.
#    Rule: Cannot hold dice when game is over.
#    Rule: Invalid die indices (outside 0-4) are rejected.
# ═══════════════════════════════════════════════════════════════════════════════

class TestHoldingDice:

    # ── What's allowed ──

    def test_can_hold_any_die_after_rolling(self):
        state = roll_dice(GameState.create_initial())
        for i in range(5):
            s = toggle_die_hold(state, i)
            assert s.dice[i].held is True

    def test_can_unhold_a_held_die(self):
        state = roll_dice(GameState.create_initial())
        state = toggle_die_hold(state, 2)
        assert state.dice[2].held is True
        state = toggle_die_hold(state, 2)
        assert state.dice[2].held is False

    def test_hold_does_not_change_die_value(self):
        state = roll_dice(GameState.create_initial())
        val = state.dice[3].value
        state = toggle_die_hold(state, 3)
        assert state.dice[3].value == val

    def test_hold_does_not_affect_other_dice(self):
        state = roll_dice(GameState.create_initial())
        before = [d.held for d in state.dice]
        state = toggle_die_hold(state, 2)
        for i in range(5):
            if i != 2:
                assert state.dice[i].held == before[i]

    def test_can_hold_multiple_dice(self):
        state = roll_dice(GameState.create_initial())
        state = toggle_die_hold(state, 0)
        state = toggle_die_hold(state, 3)
        state = toggle_die_hold(state, 4)
        assert state.dice[0].held is True
        assert state.dice[1].held is False
        assert state.dice[2].held is False
        assert state.dice[3].held is True
        assert state.dice[4].held is True

    def test_can_hold_all_five_dice(self):
        state = roll_dice(GameState.create_initial())
        for i in range(5):
            state = toggle_die_hold(state, i)
        for die in state.dice:
            assert die.held is True

    def test_held_dice_persist_across_rolls(self):
        state = roll_dice(GameState.create_initial())
        state = toggle_die_hold(state, 0)
        state = toggle_die_hold(state, 2)
        val0 = state.dice[0].value
        val2 = state.dice[2].value

        state = roll_dice(state)
        assert state.dice[0].value == val0
        assert state.dice[2].value == val2

        state = roll_dice(state)
        assert state.dice[0].value == val0
        assert state.dice[2].value == val2

    # ── What's forbidden ──

    def test_cannot_hold_before_first_roll(self):
        state = GameState.create_initial()
        for i in range(5):
            assert toggle_die_hold(state, i) == state

    def test_cannot_hold_at_start_of_new_turn(self):
        """After scoring, rolls_used resets to 0 — holding is blocked again."""
        state = roll_dice(GameState.create_initial())
        state = select_category(state, Category.ONES)
        assert state.rolls_used == 0
        for i in range(5):
            assert toggle_die_hold(state, i) == state

    def test_cannot_hold_when_game_over(self):
        state = replace(roll_dice(GameState.create_initial()), game_over=True)
        for i in range(5):
            assert toggle_die_hold(state, i) == state

    def test_invalid_index_negative(self):
        state = roll_dice(GameState.create_initial())
        assert toggle_die_hold(state, -1) == state

    def test_invalid_index_too_large(self):
        state = roll_dice(GameState.create_initial())
        assert toggle_die_hold(state, 5) == state
        assert toggle_die_hold(state, 10) == state


# ═══════════════════════════════════════════════════════════════════════════════
# 5. SCORING A CATEGORY (turn mechanics)
#    Rule: Must roll at least once before scoring.
#    Rule: Can score after 1, 2, or 3 rolls.
#    Rule: Can only score in an unfilled category.
#    Rule: Cannot score when game is over.
#    Rule: Scoring calculates the correct value for the chosen category.
#    Rule: After scoring, rolls_used resets to 0.
#    Rule: After scoring, all dice become unheld.
#    Rule: After scoring (if game not complete), round advances by 1.
#    Rule: After filling all 13 categories, game_over becomes True.
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoringTurnMechanics:

    # ── What's allowed ──

    def test_can_score_after_one_roll(self):
        state = roll_dice(GameState.create_initial())
        assert can_select_category(state, Category.CHANCE) is True
        state = select_category(state, Category.CHANCE)
        assert state.scorecard.is_filled(Category.CHANCE)

    def test_can_score_after_two_rolls(self):
        state = roll_dice(roll_dice(GameState.create_initial()))
        state = select_category(state, Category.CHANCE)
        assert state.scorecard.is_filled(Category.CHANCE)

    def test_can_score_after_three_rolls(self):
        state = roll_dice(roll_dice(roll_dice(GameState.create_initial())))
        state = select_category(state, Category.CHANCE)
        assert state.scorecard.is_filled(Category.CHANCE)

    def test_scoring_records_correct_value(self):
        state = state_with_dice(5, 5, 5, 5, 5)
        state = select_category(state, Category.FIVES)
        assert state.scorecard.scores[Category.FIVES] == 25

    def test_scoring_resets_rolls_used_to_zero(self):
        state = roll_dice(roll_dice(GameState.create_initial()))
        assert state.rolls_used == 2
        state = select_category(state, Category.ONES)
        assert state.rolls_used == 0

    def test_scoring_unholds_all_dice(self):
        state = roll_dice(GameState.create_initial())
        state = toggle_die_hold(state, 0)
        state = toggle_die_hold(state, 3)
        state = select_category(state, Category.ONES)
        for die in state.dice:
            assert die.held is False

    def test_scoring_advances_round(self):
        state = roll_dice(GameState.create_initial())
        assert state.current_round == 1
        state = select_category(state, Category.ONES)
        assert state.current_round == 2

    def test_can_score_any_unfilled_category(self):
        """Every unfilled category is available to score into."""
        state = roll_dice(GameState.create_initial())
        for cat in Category:
            assert can_select_category(state, cat) is True

    # ── What's forbidden ──

    def test_cannot_score_without_rolling(self):
        state = GameState.create_initial()
        for cat in Category:
            assert can_select_category(state, cat) is False
            assert select_category(state, cat) == state

    def test_cannot_score_already_filled_category(self):
        state = roll_dice(GameState.create_initial())
        state = select_category(state, Category.ONES)
        state = roll_dice(state)
        assert can_select_category(state, Category.ONES) is False
        round_before = state.current_round
        state = select_category(state, Category.ONES)
        assert state.current_round == round_before  # no change

    def test_cannot_score_when_game_over(self):
        state = replace(
            roll_dice(GameState.create_initial()),
            game_over=True
        )
        for cat in Category:
            assert can_select_category(state, cat) is False
            assert select_category(state, cat) == state

    def test_scoring_without_rolling_does_not_advance_round(self):
        state = GameState.create_initial()
        for cat in Category:
            state = select_category(state, cat)
        assert state.current_round == 1
        assert not state.scorecard.is_complete()

    def test_scoring_without_rolling_does_not_fill_category(self):
        state = GameState.create_initial()
        state = select_category(state, Category.YAHTZEE)
        assert not state.scorecard.is_filled(Category.YAHTZEE)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. SCORING RULES — every category formula
#    Upper section: sum of dice matching that number
#    Three of a Kind: sum of all dice if 3+ match
#    Four of a Kind: sum of all dice if 4+ match
#    Full House: 25 if exactly 3+2 distinct values
#    Small Straight: 30 if 4 consecutive values
#    Large Straight: 40 if 5 consecutive values
#    Yahtzee: 50 if all 5 dice match
#    Chance: sum of all dice (always)
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoringOnes:
    def test_all_ones(self):
        assert calculate_score(Category.ONES, make_dice(1, 1, 1, 1, 1)) == 5

    def test_some_ones(self):
        assert calculate_score(Category.ONES, make_dice(1, 1, 3, 4, 5)) == 2

    def test_one_one(self):
        assert calculate_score(Category.ONES, make_dice(1, 2, 3, 4, 5)) == 1

    def test_no_ones(self):
        assert calculate_score(Category.ONES, make_dice(2, 3, 4, 5, 6)) == 0


class TestScoringTwos:
    def test_all_twos(self):
        assert calculate_score(Category.TWOS, make_dice(2, 2, 2, 2, 2)) == 10

    def test_some_twos(self):
        assert calculate_score(Category.TWOS, make_dice(2, 2, 3, 4, 5)) == 4

    def test_no_twos(self):
        assert calculate_score(Category.TWOS, make_dice(1, 3, 4, 5, 6)) == 0


class TestScoringThrees:
    def test_all_threes(self):
        assert calculate_score(Category.THREES, make_dice(3, 3, 3, 3, 3)) == 15

    def test_some_threes(self):
        assert calculate_score(Category.THREES, make_dice(3, 3, 3, 1, 5)) == 9

    def test_no_threes(self):
        assert calculate_score(Category.THREES, make_dice(1, 2, 4, 5, 6)) == 0


class TestScoringFours:
    def test_all_fours(self):
        assert calculate_score(Category.FOURS, make_dice(4, 4, 4, 4, 4)) == 20

    def test_some_fours(self):
        assert calculate_score(Category.FOURS, make_dice(4, 4, 1, 2, 3)) == 8

    def test_no_fours(self):
        assert calculate_score(Category.FOURS, make_dice(1, 2, 3, 5, 6)) == 0


class TestScoringFives:
    def test_all_fives(self):
        assert calculate_score(Category.FIVES, make_dice(5, 5, 5, 5, 5)) == 25

    def test_some_fives(self):
        assert calculate_score(Category.FIVES, make_dice(5, 5, 1, 2, 3)) == 10

    def test_no_fives(self):
        assert calculate_score(Category.FIVES, make_dice(1, 2, 3, 4, 6)) == 0


class TestScoringSixes:
    def test_all_sixes(self):
        assert calculate_score(Category.SIXES, make_dice(6, 6, 6, 6, 6)) == 30

    def test_some_sixes(self):
        assert calculate_score(Category.SIXES, make_dice(6, 6, 1, 2, 3)) == 12

    def test_no_sixes(self):
        assert calculate_score(Category.SIXES, make_dice(1, 2, 3, 4, 5)) == 0


class TestScoringThreeOfAKind:
    """Three of a Kind: if 3+ dice share a value, score = sum of ALL dice. Else 0."""

    def test_exactly_three_matching(self):
        assert calculate_score(Category.THREE_OF_KIND, make_dice(4, 4, 4, 2, 1)) == 15

    def test_four_matching_also_qualifies(self):
        assert calculate_score(Category.THREE_OF_KIND, make_dice(3, 3, 3, 3, 1)) == 13

    def test_five_matching_also_qualifies(self):
        assert calculate_score(Category.THREE_OF_KIND, make_dice(6, 6, 6, 6, 6)) == 30

    def test_only_two_matching_scores_zero(self):
        assert calculate_score(Category.THREE_OF_KIND, make_dice(4, 4, 3, 2, 1)) == 0

    def test_all_different_scores_zero(self):
        assert calculate_score(Category.THREE_OF_KIND, make_dice(1, 2, 3, 4, 5)) == 0


class TestScoringFourOfAKind:
    """Four of a Kind: if 4+ dice share a value, score = sum of ALL dice. Else 0."""

    def test_exactly_four_matching(self):
        assert calculate_score(Category.FOUR_OF_KIND, make_dice(6, 6, 6, 6, 2)) == 26

    def test_five_matching_also_qualifies(self):
        assert calculate_score(Category.FOUR_OF_KIND, make_dice(5, 5, 5, 5, 5)) == 25

    def test_only_three_matching_scores_zero(self):
        assert calculate_score(Category.FOUR_OF_KIND, make_dice(3, 3, 3, 2, 1)) == 0

    def test_two_pair_scores_zero(self):
        assert calculate_score(Category.FOUR_OF_KIND, make_dice(3, 3, 2, 2, 1)) == 0


class TestScoringFullHouse:
    """Full House: exactly 3 of one value AND 2 of another = 25 points. Else 0."""

    def test_three_and_two(self):
        assert calculate_score(Category.FULL_HOUSE, make_dice(3, 3, 3, 6, 6)) == 25

    def test_two_and_three_reversed_order(self):
        assert calculate_score(Category.FULL_HOUSE, make_dice(2, 2, 5, 5, 5)) == 25

    def test_four_of_kind_is_not_full_house(self):
        assert calculate_score(Category.FULL_HOUSE, make_dice(3, 3, 3, 3, 6)) == 0

    def test_yahtzee_is_not_full_house(self):
        assert calculate_score(Category.FULL_HOUSE, make_dice(4, 4, 4, 4, 4)) == 0

    def test_all_different_is_not_full_house(self):
        assert calculate_score(Category.FULL_HOUSE, make_dice(1, 2, 3, 4, 5)) == 0

    def test_three_of_kind_with_two_singletons_is_not_full_house(self):
        assert calculate_score(Category.FULL_HOUSE, make_dice(2, 2, 2, 3, 4)) == 0


class TestScoringSmallStraight:
    """Small Straight: 4 consecutive values present = 30 points. Else 0."""

    def test_1_2_3_4_with_extra(self):
        assert calculate_score(Category.SMALL_STRAIGHT, make_dice(1, 2, 3, 4, 6)) == 30

    def test_2_3_4_5_with_extra(self):
        assert calculate_score(Category.SMALL_STRAIGHT, make_dice(2, 3, 4, 5, 1)) == 30

    def test_3_4_5_6_with_extra(self):
        assert calculate_score(Category.SMALL_STRAIGHT, make_dice(3, 4, 5, 6, 1)) == 30

    def test_large_straight_also_qualifies(self):
        assert calculate_score(Category.SMALL_STRAIGHT, make_dice(1, 2, 3, 4, 5)) == 30
        assert calculate_score(Category.SMALL_STRAIGHT, make_dice(2, 3, 4, 5, 6)) == 30

    def test_with_duplicate_in_straight(self):
        assert calculate_score(Category.SMALL_STRAIGHT, make_dice(1, 2, 3, 4, 4)) == 30

    def test_only_three_consecutive_scores_zero(self):
        assert calculate_score(Category.SMALL_STRAIGHT, make_dice(1, 2, 3, 5, 6)) == 0

    def test_all_same_scores_zero(self):
        assert calculate_score(Category.SMALL_STRAIGHT, make_dice(3, 3, 3, 3, 3)) == 0

    def test_gap_in_middle_scores_zero(self):
        assert calculate_score(Category.SMALL_STRAIGHT, make_dice(1, 2, 4, 5, 6)) == 0

    def test_unsorted_still_detected(self):
        assert calculate_score(Category.SMALL_STRAIGHT, make_dice(4, 1, 3, 2, 6)) == 30


class TestScoringLargeStraight:
    """Large Straight: 5 consecutive values (1-2-3-4-5 or 2-3-4-5-6) = 40. Else 0."""

    def test_1_through_5(self):
        assert calculate_score(Category.LARGE_STRAIGHT, make_dice(1, 2, 3, 4, 5)) == 40

    def test_2_through_6(self):
        assert calculate_score(Category.LARGE_STRAIGHT, make_dice(2, 3, 4, 5, 6)) == 40

    def test_unsorted_still_detected(self):
        assert calculate_score(Category.LARGE_STRAIGHT, make_dice(5, 3, 1, 4, 2)) == 40

    def test_only_small_straight_scores_zero(self):
        assert calculate_score(Category.LARGE_STRAIGHT, make_dice(1, 2, 3, 4, 6)) == 0

    def test_four_consecutive_plus_duplicate_scores_zero(self):
        assert calculate_score(Category.LARGE_STRAIGHT, make_dice(1, 2, 3, 4, 4)) == 0

    def test_all_same_scores_zero(self):
        assert calculate_score(Category.LARGE_STRAIGHT, make_dice(5, 5, 5, 5, 5)) == 0


class TestScoringYahtzee:
    """Yahtzee: all 5 dice the same value = 50 points. Else 0."""

    def test_all_ones(self):
        assert calculate_score(Category.YAHTZEE, make_dice(1, 1, 1, 1, 1)) == 50

    def test_all_sixes(self):
        assert calculate_score(Category.YAHTZEE, make_dice(6, 6, 6, 6, 6)) == 50

    def test_four_matching_scores_zero(self):
        assert calculate_score(Category.YAHTZEE, make_dice(5, 5, 5, 5, 4)) == 0

    def test_all_different_scores_zero(self):
        assert calculate_score(Category.YAHTZEE, make_dice(1, 2, 3, 4, 5)) == 0


class TestScoringChance:
    """Chance: always sum of all dice. No conditions."""

    def test_sum_of_mixed_dice(self):
        assert calculate_score(Category.CHANCE, make_dice(1, 2, 3, 4, 5)) == 15

    def test_all_ones_minimum(self):
        assert calculate_score(Category.CHANCE, make_dice(1, 1, 1, 1, 1)) == 5

    def test_all_sixes_maximum(self):
        assert calculate_score(Category.CHANCE, make_dice(6, 6, 6, 6, 6)) == 30

    def test_arbitrary_dice(self):
        assert calculate_score(Category.CHANCE, make_dice(2, 3, 3, 5, 6)) == 19


# ═══════════════════════════════════════════════════════════════════════════════
# 6b. SCORING HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoringHelpers:

    def test_has_n_of_kind_detects_pairs(self):
        assert has_n_of_kind(make_dice(3, 3, 1, 2, 4), 2) is True

    def test_has_n_of_kind_detects_three(self):
        assert has_n_of_kind(make_dice(3, 3, 3, 1, 2), 3) is True

    def test_has_n_of_kind_rejects_insufficient(self):
        assert has_n_of_kind(make_dice(3, 3, 1, 2, 4), 3) is False

    def test_has_yahtzee_true(self):
        assert has_yahtzee(make_dice(5, 5, 5, 5, 5)) is True

    def test_has_yahtzee_false(self):
        assert has_yahtzee(make_dice(5, 5, 5, 5, 1)) is False

    def test_has_full_house_true(self):
        assert has_full_house(make_dice(2, 2, 3, 3, 3)) is True

    def test_has_full_house_false(self):
        assert has_full_house(make_dice(2, 2, 2, 3, 4)) is False

    def test_has_small_straight_true(self):
        assert has_small_straight(make_dice(1, 2, 3, 4, 6)) is True

    def test_has_small_straight_false(self):
        assert has_small_straight(make_dice(1, 2, 4, 5, 6)) is False

    def test_has_large_straight_true(self):
        assert has_large_straight(make_dice(1, 2, 3, 4, 5)) is True

    def test_has_large_straight_false(self):
        assert has_large_straight(make_dice(1, 2, 3, 4, 6)) is False


# ═══════════════════════════════════════════════════════════════════════════════
# 7. SCORECARD
#    Rule: 13 categories, each filled at most once.
#    Rule: Upper section = Ones through Sixes. Bonus of 35 if total >= 63.
#    Rule: Lower section = Three of a Kind through Chance.
#    Rule: Grand total = upper total + bonus + lower total.
# ═══════════════════════════════════════════════════════════════════════════════

class TestScorecard:

    def test_new_scorecard_has_13_empty_categories(self):
        sc = Scorecard()
        assert len(sc.scores) == 13
        for cat in Category:
            assert sc.scores[cat] is None

    def test_is_filled_false_when_empty(self):
        sc = Scorecard()
        for cat in Category:
            assert sc.is_filled(cat) is False

    def test_is_filled_true_after_set(self):
        sc = Scorecard()
        sc.set_score(Category.ONES, 3)
        assert sc.is_filled(Category.ONES) is True

    def test_set_score_records_value(self):
        sc = Scorecard()
        sc.set_score(Category.YAHTZEE, 50)
        assert sc.scores[Category.YAHTZEE] == 50

    def test_set_score_does_not_overwrite_filled(self):
        sc = Scorecard()
        sc.set_score(Category.ONES, 3)
        sc.set_score(Category.ONES, 5)
        assert sc.scores[Category.ONES] == 3

    def test_zero_score_counts_as_filled(self):
        sc = Scorecard()
        sc.set_score(Category.SIXES, 0)
        assert sc.is_filled(Category.SIXES) is True
        assert sc.scores[Category.SIXES] == 0

    def test_is_complete_when_all_filled(self):
        sc = Scorecard()
        for cat in Category:
            sc.set_score(cat, 0)
        assert sc.is_complete() is True

    def test_is_not_complete_when_one_missing(self):
        sc = Scorecard()
        for cat in list(Category)[:-1]:
            sc.set_score(cat, 0)
        assert sc.is_complete() is False

    def test_copy_is_independent(self):
        sc = Scorecard()
        sc.set_score(Category.ONES, 5)
        copy = sc.copy()
        copy.set_score(Category.TWOS, 10)
        assert sc.scores[Category.TWOS] is None

    def test_with_score_returns_new_scorecard(self):
        sc = Scorecard()
        sc.set_score(Category.ONES, 5)
        new = sc.with_score(Category.TWOS, 10)
        assert new.scores[Category.TWOS] == 10
        assert sc.scores[Category.TWOS] is None

    def test_with_score_does_not_overwrite_filled(self):
        sc = Scorecard()
        sc.set_score(Category.ONES, 3)
        new = sc.with_score(Category.ONES, 99)
        assert new.scores[Category.ONES] == 3


class TestScorecardTotals:

    def test_upper_section_total(self):
        sc = Scorecard()
        sc.set_score(Category.ONES, 3)
        sc.set_score(Category.TWOS, 6)
        sc.set_score(Category.THREES, 9)
        sc.set_score(Category.FOURS, 12)
        sc.set_score(Category.FIVES, 15)
        sc.set_score(Category.SIXES, 18)
        assert sc.get_upper_section_total() == 63

    def test_upper_section_total_ignores_unfilled(self):
        sc = Scorecard()
        sc.set_score(Category.ONES, 3)
        assert sc.get_upper_section_total() == 3

    def test_upper_section_total_ignores_lower_categories(self):
        sc = Scorecard()
        sc.set_score(Category.YAHTZEE, 50)
        assert sc.get_upper_section_total() == 0

    def test_bonus_awarded_at_exactly_63(self):
        sc = Scorecard()
        sc.set_score(Category.ONES, 3)
        sc.set_score(Category.TWOS, 6)
        sc.set_score(Category.THREES, 9)
        sc.set_score(Category.FOURS, 12)
        sc.set_score(Category.FIVES, 15)
        sc.set_score(Category.SIXES, 18)
        assert sc.get_upper_section_bonus() == 35

    def test_bonus_awarded_above_63(self):
        sc = Scorecard()
        sc.set_score(Category.ONES, 5)
        sc.set_score(Category.TWOS, 10)
        sc.set_score(Category.THREES, 15)
        sc.set_score(Category.FOURS, 20)
        sc.set_score(Category.FIVES, 25)
        sc.set_score(Category.SIXES, 30)
        assert sc.get_upper_section_bonus() == 35

    def test_no_bonus_below_63(self):
        sc = Scorecard()
        sc.set_score(Category.ONES, 3)
        sc.set_score(Category.TWOS, 6)
        sc.set_score(Category.THREES, 9)
        sc.set_score(Category.FOURS, 12)
        sc.set_score(Category.FIVES, 15)
        sc.set_score(Category.SIXES, 17)  # total = 62
        assert sc.get_upper_section_bonus() == 0

    def test_no_bonus_when_upper_empty(self):
        sc = Scorecard()
        assert sc.get_upper_section_bonus() == 0

    def test_lower_section_total(self):
        sc = Scorecard()
        sc.set_score(Category.THREE_OF_KIND, 15)
        sc.set_score(Category.FOUR_OF_KIND, 22)
        sc.set_score(Category.FULL_HOUSE, 25)
        sc.set_score(Category.SMALL_STRAIGHT, 30)
        sc.set_score(Category.LARGE_STRAIGHT, 40)
        sc.set_score(Category.YAHTZEE, 50)
        sc.set_score(Category.CHANCE, 23)
        assert sc.get_lower_section_total() == 205

    def test_lower_section_total_ignores_upper_categories(self):
        sc = Scorecard()
        sc.set_score(Category.ONES, 5)
        assert sc.get_lower_section_total() == 0

    def test_grand_total_with_bonus(self):
        sc = Scorecard()
        sc.set_score(Category.ONES, 3)
        sc.set_score(Category.TWOS, 6)
        sc.set_score(Category.THREES, 9)
        sc.set_score(Category.FOURS, 12)
        sc.set_score(Category.FIVES, 15)
        sc.set_score(Category.SIXES, 18)
        sc.set_score(Category.CHANCE, 20)
        # upper=63, bonus=35, lower=20 → 118
        assert sc.get_grand_total() == 118

    def test_grand_total_without_bonus(self):
        sc = Scorecard()
        sc.set_score(Category.ONES, 3)
        sc.set_score(Category.YAHTZEE, 50)
        # upper=3, bonus=0, lower=50 → 53
        assert sc.get_grand_total() == 53

    def test_grand_total_all_zeros(self):
        sc = Scorecard()
        for cat in Category:
            sc.set_score(cat, 0)
        assert sc.get_grand_total() == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 8. GAME FLOW — full games, round progression, game over
#    Rule: Game has exactly 13 rounds.
#    Rule: Each round: roll (1-3 times) → score one category.
#    Rule: Game ends when all 13 categories are filled.
#    Rule: After game over, no actions are possible.
# ═══════════════════════════════════════════════════════════════════════════════

class TestGameFlow:

    def test_complete_game_13_rounds(self):
        """Play a full game: 13 rounds, each with rolls then scoring."""
        state = GameState.create_initial()
        categories = list(Category)

        for round_num in range(1, 14):
            assert state.current_round == round_num
            assert state.game_over is False

            state = roll_dice(state)
            state = select_category(state, categories[round_num - 1])

        assert state.game_over is True
        assert state.scorecard.is_complete()

    def test_complete_game_using_all_three_rolls_each_turn(self):
        state = GameState.create_initial()
        for cat in Category:
            state = roll_dice(roll_dice(roll_dice(state)))
            state = select_category(state, cat)
        assert state.game_over is True

    def test_grand_total_is_non_negative_after_complete_game(self):
        state = GameState.create_initial()
        for cat in Category:
            state = roll_dice(state)
            state = select_category(state, cat)
        assert state.scorecard.get_grand_total() >= 0

    def test_game_over_blocks_all_actions(self):
        """Once game is over, rolling, holding, and scoring all do nothing."""
        state = GameState.create_initial()
        for cat in Category:
            state = roll_dice(state)
            state = select_category(state, cat)
        assert state.game_over is True
        frozen = state

        assert roll_dice(frozen) == frozen
        assert toggle_die_hold(frozen, 0) == frozen
        for cat in Category:
            assert select_category(frozen, cat) == frozen

    def test_turn_cycle_roll_hold_roll_score(self):
        """Typical turn: roll → hold some → roll again → score."""
        state = GameState.create_initial()

        state = roll_dice(state)
        state = toggle_die_hold(state, 0)
        state = toggle_die_hold(state, 1)
        state = roll_dice(state)
        state = select_category(state, Category.CHANCE)

        assert state.current_round == 2
        assert state.rolls_used == 0
        assert all(not d.held for d in state.dice)

    def test_turn_cycle_single_roll_then_score(self):
        """Minimal turn: one roll, then score immediately."""
        state = GameState.create_initial()
        state = roll_dice(state)
        state = select_category(state, Category.CHANCE)

        assert state.current_round == 2
        assert state.rolls_used == 0

    def test_consecutive_turns_are_independent(self):
        """Each turn starts fresh: rolls_used=0, no holds, regardless of prior turn."""
        state = GameState.create_initial()

        # Turn 1: use all 3 rolls, hold dice
        state = roll_dice(state)
        state = toggle_die_hold(state, 0)
        state = toggle_die_hold(state, 3)
        state = roll_dice(state)
        state = roll_dice(state)
        assert state.rolls_used == 3
        state = select_category(state, Category.ONES)

        # Turn 2: clean slate
        assert state.rolls_used == 0
        assert all(not d.held for d in state.dice)

        # Cannot hold or score yet
        assert toggle_die_hold(state, 0) == state
        assert select_category(state, Category.TWOS) == state

        # Roll works, then hold and score work
        state = roll_dice(state)
        state = toggle_die_hold(state, 1)
        assert state.dice[1].held is True
        state = select_category(state, Category.TWOS)
        assert state.current_round == 3

    def test_categories_can_be_filled_in_any_order(self):
        """No restriction on which category to fill first."""
        state = GameState.create_initial()
        reversed_cats = list(reversed(list(Category)))

        for cat in reversed_cats:
            state = roll_dice(state)
            state = select_category(state, cat)

        assert state.game_over is True
        assert state.scorecard.is_complete()

    def test_exactly_13_categories_exist(self):
        assert len(list(Category)) == 13


# ═══════════════════════════════════════════════════════════════════════════════
# 8b. YAHTZEE BONUS AND JOKER RULES
#    Rule: +100 bonus for each additional Yahtzee when the first was scored 50.
#    Rule: Joker rules apply when bonus Yahtzee AND matching upper cat is filled:
#          Full House → 25, Small Straight → 30, Large Straight → 40.
#    Rule: Three/Four of Kind, Chance, upper cats → normal calculation.
# ═══════════════════════════════════════════════════════════════════════════════


class TestYahtzeeBonusTracking:
    """Yahtzee bonus: +100 per additional Yahtzee when first was scored 50."""

    def test_first_yahtzee_no_bonus(self):
        state = state_with_dice(6, 6, 6, 6, 6)
        state = select_category(state, Category.YAHTZEE)
        assert state.scorecard.yahtzee_bonus_count == 0
        assert state.scorecard.scores[Category.YAHTZEE] == 50

    def test_second_yahtzee_awards_bonus(self):
        state = state_with_dice(6, 6, 6, 6, 6)
        state = select_category(state, Category.YAHTZEE)
        state = replace(state, dice=make_dice(3, 3, 3, 3, 3), rolls_used=1)
        state = select_category(state, Category.THREES)
        assert state.scorecard.yahtzee_bonus_count == 1

    def test_no_bonus_if_yahtzee_scored_zero(self):
        """If Yahtzee was scored as 0 (not a Yahtzee), no bonus on subsequent."""
        sc = Scorecard()
        sc.set_score(Category.YAHTZEE, 0)
        state = GameState(
            dice=make_dice(4, 4, 4, 4, 4),
            scorecard=sc, rolls_used=1, current_round=2,
        )
        state = select_category(state, Category.FOURS)
        assert state.scorecard.yahtzee_bonus_count == 0

    def test_multiple_bonuses_accumulate(self):
        sc = Scorecard()
        sc.set_score(Category.YAHTZEE, 50)
        sc.yahtzee_bonus_count = 2  # Already got 2 bonuses
        state = GameState(
            dice=make_dice(5, 5, 5, 5, 5),
            scorecard=sc, rolls_used=1, current_round=4,
        )
        state = select_category(state, Category.FIVES)
        assert state.scorecard.yahtzee_bonus_count == 3

    def test_grand_total_includes_bonuses(self):
        sc = Scorecard()
        sc.set_score(Category.YAHTZEE, 50)
        sc.set_score(Category.CHANCE, 20)
        sc.yahtzee_bonus_count = 2
        assert sc.get_grand_total() == 50 + 20 + 200  # 270

    def test_copy_preserves_bonus_count(self):
        sc = Scorecard()
        sc.yahtzee_bonus_count = 3
        copy = sc.copy()
        assert copy.yahtzee_bonus_count == 3
        copy.yahtzee_bonus_count = 0
        assert sc.yahtzee_bonus_count == 3  # original unchanged

    def test_bonus_not_awarded_for_non_yahtzee(self):
        """Regular dice (not all same) never trigger bonus."""
        sc = Scorecard()
        sc.set_score(Category.YAHTZEE, 50)
        state = GameState(
            dice=make_dice(1, 2, 3, 4, 5),
            scorecard=sc, rolls_used=1, current_round=2,
        )
        state = select_category(state, Category.CHANCE)
        assert state.scorecard.yahtzee_bonus_count == 0


class TestJokerRules:
    """Joker rules: when bonus Yahtzee and matching upper cat is filled."""

    def test_joker_full_house_scores_25(self):
        """With joker rules, a Yahtzee scores 25 as Full House."""
        sc = Scorecard()
        sc.set_score(Category.YAHTZEE, 50)
        sc.set_score(Category.THREES, 9)  # matching upper cat filled
        dice = make_dice(3, 3, 3, 3, 3)
        assert calculate_score_in_context(Category.FULL_HOUSE, dice, sc) == 25

    def test_joker_small_straight_scores_30(self):
        sc = Scorecard()
        sc.set_score(Category.YAHTZEE, 50)
        sc.set_score(Category.FOURS, 12)
        dice = make_dice(4, 4, 4, 4, 4)
        assert calculate_score_in_context(Category.SMALL_STRAIGHT, dice, sc) == 30

    def test_joker_large_straight_scores_40(self):
        sc = Scorecard()
        sc.set_score(Category.YAHTZEE, 50)
        sc.set_score(Category.FIVES, 15)
        dice = make_dice(5, 5, 5, 5, 5)
        assert calculate_score_in_context(Category.LARGE_STRAIGHT, dice, sc) == 40

    def test_joker_three_of_kind_scores_sum(self):
        sc = Scorecard()
        sc.set_score(Category.YAHTZEE, 50)
        sc.set_score(Category.SIXES, 18)
        dice = make_dice(6, 6, 6, 6, 6)
        assert calculate_score_in_context(Category.THREE_OF_KIND, dice, sc) == 30

    def test_joker_four_of_kind_scores_sum(self):
        sc = Scorecard()
        sc.set_score(Category.YAHTZEE, 50)
        sc.set_score(Category.SIXES, 18)
        dice = make_dice(6, 6, 6, 6, 6)
        assert calculate_score_in_context(Category.FOUR_OF_KIND, dice, sc) == 30

    def test_joker_chance_scores_sum(self):
        sc = Scorecard()
        sc.set_score(Category.YAHTZEE, 50)
        sc.set_score(Category.TWOS, 6)
        dice = make_dice(2, 2, 2, 2, 2)
        assert calculate_score_in_context(Category.CHANCE, dice, sc) == 10

    def test_no_joker_when_upper_cat_open(self):
        """If matching upper cat is NOT filled, no joker — normal rules apply."""
        sc = Scorecard()
        sc.set_score(Category.YAHTZEE, 50)
        # THREES is NOT filled
        dice = make_dice(3, 3, 3, 3, 3)
        # Full House normally requires 3+2, Yahtzee (5 of kind) doesn't qualify
        assert calculate_score_in_context(Category.FULL_HOUSE, dice, sc) == 0

    def test_no_joker_when_yahtzee_scored_zero(self):
        """No joker rules if Yahtzee was scored as 0."""
        sc = Scorecard()
        sc.set_score(Category.YAHTZEE, 0)
        sc.set_score(Category.FOURS, 12)
        dice = make_dice(4, 4, 4, 4, 4)
        # Without joker, Full House doesn't apply to 5-of-a-kind
        assert calculate_score_in_context(Category.FULL_HOUSE, dice, sc) == 0

    def test_no_joker_when_not_yahtzee(self):
        """Normal dice (not all same) never trigger joker."""
        sc = Scorecard()
        sc.set_score(Category.YAHTZEE, 50)
        sc.set_score(Category.ONES, 3)
        dice = make_dice(1, 1, 1, 2, 3)
        assert calculate_score_in_context(Category.FULL_HOUSE, dice, sc) == 0

    def test_no_joker_when_yahtzee_not_scored_yet(self):
        """If Yahtzee category is unfilled, no joker."""
        sc = Scorecard()
        # Yahtzee not scored
        sc.set_score(Category.FOURS, 12)
        dice = make_dice(4, 4, 4, 4, 4)
        assert calculate_score_in_context(Category.FULL_HOUSE, dice, sc) == 0

    def test_context_delegates_to_normal_for_non_yahtzee_dice(self):
        """calculate_score_in_context matches calculate_score for non-Yahtzee dice."""
        sc = Scorecard()
        sc.set_score(Category.YAHTZEE, 50)
        dice = make_dice(1, 2, 3, 4, 5)
        for cat in Category:
            if not sc.is_filled(cat):
                assert calculate_score_in_context(cat, dice, sc) == calculate_score(cat, dice)

    def test_joker_upper_category_scores_normally(self):
        """Joker doesn't change upper category scoring — just sum of matching."""
        sc = Scorecard()
        sc.set_score(Category.YAHTZEE, 50)
        sc.set_score(Category.FOURS, 12)  # This upper cat is filled
        dice = make_dice(4, 4, 4, 4, 4)
        # Fours is already filled, but Ones should score normally (0 fours found? no, these are 4s)
        # Let's check FIVES which is not filled — normal score is 0
        assert calculate_score_in_context(Category.FIVES, dice, sc) == 0
        # SIXES not filled — normal score is 0
        assert calculate_score_in_context(Category.SIXES, dice, sc) == 0


class TestMultiplayerYahtzeeBonus:
    """Bonus Yahtzees work correctly across multiplayer turn rotation."""

    def test_bonus_tracks_per_player(self):
        """Each player's scorecard independently tracks bonus count."""
        state = MultiplayerGameState.create_initial(2)
        # Give player 0 a Yahtzee
        state = replace(state, dice=make_dice(5, 5, 5, 5, 5), rolls_used=1)
        state = mp_select_category(state, Category.YAHTZEE)
        assert state.scorecards[0].scores[Category.YAHTZEE] == 50
        assert state.scorecards[0].yahtzee_bonus_count == 0

        # Player 1 plays normally
        state = replace(state, dice=make_dice(1, 2, 3, 4, 5), rolls_used=1)
        state = mp_select_category(state, Category.CHANCE)

        # Player 0 gets another Yahtzee — should get bonus
        state = replace(state, dice=make_dice(5, 5, 5, 5, 5), rolls_used=1)
        state = mp_select_category(state, Category.FIVES)
        assert state.scorecards[0].yahtzee_bonus_count == 1
        assert state.scorecards[1].yahtzee_bonus_count == 0

    def test_mp_joker_rules_apply(self):
        """Joker rules work in multiplayer."""
        sc0 = Scorecard()
        sc0.set_score(Category.YAHTZEE, 50)
        sc0.set_score(Category.THREES, 9)  # matching upper filled
        sc1 = Scorecard()

        state = MultiplayerGameState(
            num_players=2,
            scorecards=(sc0, sc1),
            current_player_index=0,
            dice=make_dice(3, 3, 3, 3, 3),
            rolls_used=1,
            current_round=3,
        )
        state = mp_select_category(state, Category.FULL_HOUSE)
        # Joker: Full House should score 25
        assert state.scorecards[0].scores[Category.FULL_HOUSE] == 25
        assert state.scorecards[0].yahtzee_bonus_count == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 9. MULTIPLAYER
#    Rule: 2-4 players take turns on independent scorecards.
#    Rule: Turn order rotates: player 0 → 1 → ... → N-1 → 0.
#    Rule: Round advances each time play wraps back to player 0.
#    Rule: Game ends only when ALL players' scorecards are complete.
#    Rule: Dice rolls/holds reset between turns (same as single-player).
#    Rule: mp_* functions delegate to single-player logic where possible.
# ═══════════════════════════════════════════════════════════════════════════════


def mp_state_with_dice(*values, rolls_used=1, num_players=2):
    """Create a MultiplayerGameState with specific dice values."""
    state = MultiplayerGameState.create_initial(num_players)
    return replace(state, dice=make_dice(*values), rolls_used=rolls_used)


class TestMultiplayerSetup:

    def test_create_2_players(self):
        state = MultiplayerGameState.create_initial(2)
        assert state.num_players == 2
        assert len(state.scorecards) == 2

    def test_create_3_players(self):
        state = MultiplayerGameState.create_initial(3)
        assert state.num_players == 3
        assert len(state.scorecards) == 3

    def test_create_4_players(self):
        state = MultiplayerGameState.create_initial(4)
        assert state.num_players == 4
        assert len(state.scorecards) == 4

    def test_initial_state_has_five_dice(self):
        state = MultiplayerGameState.create_initial(2)
        assert len(state.dice) == 5

    def test_initial_dice_values_1_through_6(self):
        state = MultiplayerGameState.create_initial(2)
        for die in state.dice:
            assert 1 <= die.value <= 6

    def test_initial_dice_all_unheld(self):
        state = MultiplayerGameState.create_initial(2)
        for die in state.dice:
            assert die.held is False

    def test_initial_current_player_is_zero(self):
        state = MultiplayerGameState.create_initial(3)
        assert state.current_player_index == 0

    def test_initial_rolls_used_is_zero(self):
        state = MultiplayerGameState.create_initial(2)
        assert state.rolls_used == 0

    def test_initial_round_is_one(self):
        state = MultiplayerGameState.create_initial(2)
        assert state.current_round == 1

    def test_initial_game_not_over(self):
        state = MultiplayerGameState.create_initial(2)
        assert state.game_over is False

    def test_initial_all_scorecards_empty(self):
        state = MultiplayerGameState.create_initial(3)
        for sc in state.scorecards:
            for cat in Category:
                assert not sc.is_filled(cat)

    def test_scorecards_are_independent_objects(self):
        state = MultiplayerGameState.create_initial(2)
        assert state.scorecards[0] is not state.scorecards[1]


class TestMultiplayerTurnRotation:

    def test_scoring_advances_to_next_player(self):
        state = mp_state_with_dice(1, 2, 3, 4, 5, num_players=3)
        state = mp_select_category(state, Category.CHANCE)
        assert state.current_player_index == 1

    def test_scoring_wraps_around_to_player_zero(self):
        state = mp_state_with_dice(1, 2, 3, 4, 5, num_players=2)
        state = mp_select_category(state, Category.ONES)
        assert state.current_player_index == 1

        # Player 1 rolls and scores
        state = mp_roll_dice(state)
        state = mp_select_category(state, Category.TWOS)
        assert state.current_player_index == 0

    def test_three_player_rotation(self):
        """Full rotation: 0 → 1 → 2 → 0"""
        state = mp_state_with_dice(1, 2, 3, 4, 5, num_players=3)

        # Player 0 scores
        state = mp_select_category(state, Category.ONES)
        assert state.current_player_index == 1

        # Player 1 scores
        state = mp_roll_dice(state)
        state = mp_select_category(state, Category.TWOS)
        assert state.current_player_index == 2

        # Player 2 scores
        state = mp_roll_dice(state)
        state = mp_select_category(state, Category.THREES)
        assert state.current_player_index == 0


class TestMultiplayerRoundAdvancement:

    def test_round_advances_when_wrapping_to_player_zero(self):
        state = mp_state_with_dice(1, 2, 3, 4, 5, num_players=2)
        assert state.current_round == 1

        # Player 0 scores
        state = mp_select_category(state, Category.ONES)
        assert state.current_round == 1  # still round 1

        # Player 1 scores — wraps to player 0, round increments
        state = mp_roll_dice(state)
        state = mp_select_category(state, Category.TWOS)
        assert state.current_round == 2

    def test_round_does_not_advance_mid_rotation(self):
        state = mp_state_with_dice(1, 2, 3, 4, 5, num_players=3)

        # Player 0 scores
        state = mp_select_category(state, Category.ONES)
        assert state.current_round == 1

        # Player 1 scores — not yet wrapped
        state = mp_roll_dice(state)
        state = mp_select_category(state, Category.TWOS)
        assert state.current_round == 1

        # Player 2 scores — wraps to 0, round increments
        state = mp_roll_dice(state)
        state = mp_select_category(state, Category.THREES)
        assert state.current_round == 2


class TestMultiplayerIndependentScorecards:

    def test_scoring_only_affects_current_player(self):
        state = mp_state_with_dice(3, 3, 3, 1, 2, num_players=2)
        state = mp_select_category(state, Category.THREES)

        # Player 0's scorecard was updated
        assert state.scorecards[0].is_filled(Category.THREES)
        assert state.scorecards[0].scores[Category.THREES] == 9

        # Player 1's scorecard is untouched
        assert not state.scorecards[1].is_filled(Category.THREES)

    def test_both_players_can_fill_same_category(self):
        state = mp_state_with_dice(5, 5, 5, 5, 5, num_players=2)

        # Player 0 fills Yahtzee
        state = mp_select_category(state, Category.YAHTZEE)
        assert state.scorecards[0].is_filled(Category.YAHTZEE)
        assert state.scorecards[0].scores[Category.YAHTZEE] == 50

        # Player 1 fills Yahtzee too
        state = mp_roll_dice(state)
        state = mp_select_category(state, Category.YAHTZEE)
        assert state.scorecards[1].is_filled(Category.YAHTZEE)

    def test_get_current_scorecard_returns_correct_player(self):
        state = mp_state_with_dice(1, 2, 3, 4, 5, num_players=2)
        assert mp_get_current_scorecard(state) is state.scorecards[0]

        state = mp_select_category(state, Category.ONES)
        assert mp_get_current_scorecard(state) is state.scorecards[1]


class TestMultiplayerDiceReset:

    def test_dice_unheld_after_scoring(self):
        state = mp_state_with_dice(1, 2, 3, 4, 5, num_players=2)
        state = mp_toggle_die_hold(state, 0)
        state = mp_toggle_die_hold(state, 2)
        assert state.dice[0].held is True

        state = mp_select_category(state, Category.CHANCE)
        for die in state.dice:
            assert die.held is False

    def test_rolls_used_reset_after_scoring(self):
        state = mp_state_with_dice(1, 2, 3, 4, 5, num_players=2)
        assert state.rolls_used == 1
        state = mp_select_category(state, Category.CHANCE)
        assert state.rolls_used == 0


class TestMultiplayerRolling:

    def test_mp_roll_dice_increments_rolls_used(self):
        state = MultiplayerGameState.create_initial(2)
        state = mp_roll_dice(state)
        assert state.rolls_used == 1

    def test_mp_roll_dice_changes_unheld_dice(self):
        random.seed(42)
        state = MultiplayerGameState.create_initial(2)
        state = mp_roll_dice(state)
        # After roll, values should be 1-6 (we just check it ran)
        for die in state.dice:
            assert 1 <= die.value <= 6

    def test_mp_roll_dice_preserves_held_dice(self):
        state = mp_state_with_dice(6, 6, 6, 1, 2, num_players=2)
        state = mp_toggle_die_hold(state, 0)
        state = mp_roll_dice(state)
        assert state.dice[0].value == 6
        assert state.dice[0].held is True

    def test_mp_roll_dice_no_op_after_3_rolls(self):
        state = MultiplayerGameState.create_initial(2)
        state = mp_roll_dice(mp_roll_dice(mp_roll_dice(state)))
        assert state.rolls_used == 3
        before = state
        after = mp_roll_dice(state)
        assert after.rolls_used == 3
        assert after.dice == before.dice

    def test_mp_roll_dice_no_op_when_game_over(self):
        state = replace(MultiplayerGameState.create_initial(2), game_over=True)
        after = mp_roll_dice(state)
        assert after == state

    def test_mp_can_roll_true_at_start(self):
        state = MultiplayerGameState.create_initial(2)
        assert mp_can_roll(state) is True

    def test_mp_can_roll_false_after_3(self):
        state = mp_roll_dice(mp_roll_dice(mp_roll_dice(
            MultiplayerGameState.create_initial(2))))
        assert mp_can_roll(state) is False

    def test_mp_can_roll_false_when_game_over(self):
        state = replace(MultiplayerGameState.create_initial(2), game_over=True)
        assert mp_can_roll(state) is False


class TestMultiplayerHolding:

    def test_mp_toggle_die_hold_works_after_roll(self):
        state = mp_roll_dice(MultiplayerGameState.create_initial(2))
        state = mp_toggle_die_hold(state, 0)
        assert state.dice[0].held is True

    def test_mp_toggle_die_hold_no_op_before_roll(self):
        state = MultiplayerGameState.create_initial(2)
        after = mp_toggle_die_hold(state, 0)
        assert after == state

    def test_mp_toggle_die_hold_no_op_when_game_over(self):
        state = replace(mp_roll_dice(MultiplayerGameState.create_initial(2)),
                        game_over=True)
        after = mp_toggle_die_hold(state, 0)
        assert after == state

    def test_mp_toggle_die_hold_no_op_invalid_index(self):
        state = mp_roll_dice(MultiplayerGameState.create_initial(2))
        assert mp_toggle_die_hold(state, -1) == state
        assert mp_toggle_die_hold(state, 5) == state


class TestMultiplayerScoring:

    def test_cannot_score_without_rolling(self):
        state = MultiplayerGameState.create_initial(2)
        for cat in Category:
            assert mp_can_select_category(state, cat) is False
            assert mp_select_category(state, cat) == state

    def test_cannot_score_filled_category(self):
        state = mp_state_with_dice(1, 2, 3, 4, 5, num_players=2)
        state = mp_select_category(state, Category.ONES)

        # Player 1 scores something else
        state = mp_roll_dice(state)
        state = mp_select_category(state, Category.TWOS)

        # Back to player 0 — ONES is already filled
        state = mp_roll_dice(state)
        assert mp_can_select_category(state, Category.ONES) is False
        round_before = state.current_round
        after = mp_select_category(state, Category.ONES)
        assert after.current_round == round_before

    def test_cannot_score_when_game_over(self):
        state = replace(
            mp_state_with_dice(1, 2, 3, 4, 5, num_players=2),
            game_over=True
        )
        for cat in Category:
            assert mp_can_select_category(state, cat) is False
            assert mp_select_category(state, cat) == state

    def test_can_select_any_unfilled_category(self):
        state = mp_state_with_dice(1, 2, 3, 4, 5, num_players=2)
        for cat in Category:
            assert mp_can_select_category(state, cat) is True


class TestMultiplayerGameOver:

    def test_game_over_when_all_scorecards_complete(self):
        """Play a full 2-player game — 26 turns total."""
        state = MultiplayerGameState.create_initial(2)
        categories = list(Category)

        for round_idx in range(13):
            # Player 0's turn
            state = mp_roll_dice(state)
            state = mp_select_category(state, categories[round_idx])

            # Player 1's turn
            state = mp_roll_dice(state)
            state = mp_select_category(state, categories[round_idx])

        assert state.game_over is True
        assert all(sc.is_complete() for sc in state.scorecards)

    def test_game_not_over_if_one_player_incomplete(self):
        """If player 0 has filled all categories but player 1 hasn't, game continues."""
        state = MultiplayerGameState.create_initial(2)
        categories = list(Category)

        for round_idx in range(12):
            # Player 0 scores
            state = mp_roll_dice(state)
            state = mp_select_category(state, categories[round_idx])
            # Player 1 scores
            state = mp_roll_dice(state)
            state = mp_select_category(state, categories[round_idx])

        # Round 13: player 0 scores last category
        state = mp_roll_dice(state)
        state = mp_select_category(state, categories[12])
        # Player 0's scorecard is now complete, but player 1 still needs one
        assert state.scorecards[0].is_complete()
        assert not state.scorecards[1].is_complete()
        assert state.game_over is False

        # Player 1 scores last category — now game over
        state = mp_roll_dice(state)
        state = mp_select_category(state, categories[12])
        assert state.game_over is True

    def test_game_over_blocks_all_actions(self):
        state = MultiplayerGameState.create_initial(2)
        categories = list(Category)
        for round_idx in range(13):
            state = mp_roll_dice(state)
            state = mp_select_category(state, categories[round_idx])
            state = mp_roll_dice(state)
            state = mp_select_category(state, categories[round_idx])

        assert state.game_over is True
        frozen = state
        assert mp_roll_dice(frozen) == frozen
        assert mp_toggle_die_hold(frozen, 0) == frozen
        for cat in Category:
            assert mp_select_category(frozen, cat) == frozen


class TestMultiplayerFullGame3Players:

    def test_3_player_complete_game(self):
        """Play a full 3-player game — 39 turns total."""
        state = MultiplayerGameState.create_initial(3)
        categories = list(Category)

        for round_idx in range(13):
            for _ in range(3):  # 3 players
                state = mp_roll_dice(state)
                state = mp_select_category(state, categories[round_idx])

        assert state.game_over is True
        assert all(sc.is_complete() for sc in state.scorecards)
