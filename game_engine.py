"""
Yahtzee Game Engine - Pure game logic without GUI dependencies

This module contains all the core game logic for Yahtzee, with no pygame dependencies.
It uses immutable data structures and pure functions to enable unit testing without a GUI.
"""
from dataclasses import dataclass, replace
from typing import Tuple
from enum import Enum
from collections import Counter
import random


class Category(Enum):
    """Yahtzee score categories"""
    ONES = "Ones"
    TWOS = "Twos"
    THREES = "Threes"
    FOURS = "Fours"
    FIVES = "Fives"
    SIXES = "Sixes"
    THREE_OF_KIND = "3 of a Kind"
    FOUR_OF_KIND = "4 of a Kind"
    FULL_HOUSE = "Full House"
    SMALL_STRAIGHT = "Small Straight"
    LARGE_STRAIGHT = "Large Straight"
    YAHTZEE = "Yahtzee"
    CHANCE = "Chance"


class Scorecard:
    """Manages the Yahtzee scorecard"""

    def __init__(self):
        """Initialize an empty scorecard"""
        # Dictionary to store scores for each category (None = not filled)
        self.scores = {category: None for category in Category}

    def is_filled(self, category):
        """Check if a category has been filled"""
        return self.scores[category] is not None

    def set_score(self, category, score):
        """Set the score for a category"""
        if not self.is_filled(category):
            self.scores[category] = score

    def get_upper_section_total(self):
        """Calculate total for upper section (Ones through Sixes)"""
        upper_categories = [Category.ONES, Category.TWOS, Category.THREES,
                           Category.FOURS, Category.FIVES, Category.SIXES]
        total = 0
        for cat in upper_categories:
            if self.scores[cat] is not None:
                total += self.scores[cat]
        return total

    def get_upper_section_bonus(self):
        """Calculate bonus (35 points if upper section >= 63)"""
        return 35 if self.get_upper_section_total() >= 63 else 0

    def get_lower_section_total(self):
        """Calculate total for lower section"""
        lower_categories = [Category.THREE_OF_KIND, Category.FOUR_OF_KIND,
                           Category.FULL_HOUSE, Category.SMALL_STRAIGHT,
                           Category.LARGE_STRAIGHT, Category.YAHTZEE, Category.CHANCE]
        total = 0
        for cat in lower_categories:
            if self.scores[cat] is not None:
                total += self.scores[cat]
        return total

    def get_grand_total(self):
        """Calculate grand total including bonus"""
        return (self.get_upper_section_total() +
                self.get_upper_section_bonus() +
                self.get_lower_section_total())

    def is_complete(self):
        """Check if all categories are filled"""
        return all(score is not None for score in self.scores.values())

    def copy(self):
        """Create a deep copy of the scorecard"""
        new_card = Scorecard()
        new_card.scores = self.scores.copy()
        return new_card

    def with_score(self, category, score):
        """Return new Scorecard with score set for category"""
        new_card = self.copy()
        if not new_card.is_filled(category):
            new_card.scores[category] = score
        return new_card


def count_values(dice):
    """
    Count occurrences of each die value

    Works with any object that has a .value attribute (Dice or DieState)

    Args:
        dice: List of dice objects (Dice or DieState)

    Returns:
        Counter object with die values as keys
    """
    values = [die.value for die in dice]
    return Counter(values)


def has_n_of_kind(dice, n):
    """
    Check if dice contain at least n of the same value

    Works with any object that has a .value attribute (Dice or DieState)

    Args:
        dice: List of dice objects (Dice or DieState)
        n: Number of matching dice required

    Returns:
        True if at least n dice have the same value
    """
    counts = count_values(dice)
    return max(counts.values()) >= n


def has_full_house(dice):
    """
    Check if dice form a full house (3 of one value, 2 of another)

    Works with any object that has a .value attribute (Dice or DieState)

    Args:
        dice: List of dice objects (Dice or DieState)

    Returns:
        True if dice form a full house
    """
    counts = count_values(dice)
    sorted_counts = sorted(counts.values(), reverse=True)
    return sorted_counts == [3, 2]


def has_small_straight(dice):
    """
    Check if dice contain a small straight (4 consecutive values)

    Works with any object that has a .value attribute (Dice or DieState)

    Args:
        dice: List of dice objects (Dice or DieState)

    Returns:
        True if dice contain a small straight
    """
    values = set(die.value for die in dice)
    # Possible small straights: 1-2-3-4, 2-3-4-5, 3-4-5-6
    small_straights = [{1, 2, 3, 4}, {2, 3, 4, 5}, {3, 4, 5, 6}]
    return any(straight.issubset(values) for straight in small_straights)


def has_large_straight(dice):
    """
    Check if dice contain a large straight (5 consecutive values)

    Works with any object that has a .value attribute (Dice or DieState)

    Args:
        dice: List of dice objects (Dice or DieState)

    Returns:
        True if dice contain a large straight
    """
    values = set(die.value for die in dice)
    # Possible large straights: 1-2-3-4-5, 2-3-4-5-6
    large_straights = [{1, 2, 3, 4, 5}, {2, 3, 4, 5, 6}]
    return any(straight == values for straight in large_straights)


def has_yahtzee(dice):
    """
    Check if all dice have the same value

    Works with any object that has a .value attribute (Dice or DieState)

    Args:
        dice: List of dice objects (Dice or DieState)

    Returns:
        True if all dice match
    """
    return has_n_of_kind(dice, 5)


def calculate_score(category, dice):
    """
    Calculate the score for a given category and dice

    Works with any object that has a .value attribute (Dice or DieState)

    Args:
        category: Category enum value
        dice: List of dice objects (Dice or DieState)

    Returns:
        Integer score for the category (0 if doesn't qualify)
    """
    values = [die.value for die in dice]
    total = sum(values)
    counts = count_values(dice)

    # Upper section - sum of matching dice
    if category == Category.ONES:
        return counts[1] * 1
    elif category == Category.TWOS:
        return counts[2] * 2
    elif category == Category.THREES:
        return counts[3] * 3
    elif category == Category.FOURS:
        return counts[4] * 4
    elif category == Category.FIVES:
        return counts[5] * 5
    elif category == Category.SIXES:
        return counts[6] * 6

    # Three of a kind - sum of all dice if at least 3 match
    elif category == Category.THREE_OF_KIND:
        return total if has_n_of_kind(dice, 3) else 0

    # Four of a kind - sum of all dice if at least 4 match
    elif category == Category.FOUR_OF_KIND:
        return total if has_n_of_kind(dice, 4) else 0

    # Full house - 25 points
    elif category == Category.FULL_HOUSE:
        return 25 if has_full_house(dice) else 0

    # Small straight - 30 points
    elif category == Category.SMALL_STRAIGHT:
        return 30 if has_small_straight(dice) else 0

    # Large straight - 40 points
    elif category == Category.LARGE_STRAIGHT:
        return 40 if has_large_straight(dice) else 0

    # Yahtzee - 50 points
    elif category == Category.YAHTZEE:
        return 50 if has_yahtzee(dice) else 0

    # Chance - sum of all dice
    elif category == Category.CHANCE:
        return total

    return 0


@dataclass(frozen=True)
class DieState:
    """Pure representation of a single die's state - immutable"""
    value: int  # 1-6
    held: bool = False

    def roll(self) -> 'DieState':
        """Return new DieState with random value (if not held)"""
        if self.held:
            return self
        return replace(self, value=random.randint(1, 6))

    def toggle_held(self) -> 'DieState':
        """Return new DieState with held status toggled"""
        return replace(self, held=not self.held)


@dataclass(frozen=True)
class GameState:
    """Immutable game state - represents complete game state at a point in time"""
    dice: Tuple[DieState, ...]  # 5 dice (tuple for immutability)
    scorecard: Scorecard
    rolls_used: int  # 0-3
    current_round: int  # 1-13
    game_over: bool = False

    @staticmethod
    def create_initial():
        """Create a fresh game state"""
        dice = tuple(DieState(value=random.randint(1, 6), held=False) for _ in range(5))
        return GameState(
            dice=dice,
            scorecard=Scorecard(),
            rolls_used=0,
            current_round=1,
            game_over=False
        )


# Game Action Functions

def roll_dice(state: GameState) -> GameState:
    """
    Roll all unheld dice and increment roll counter.

    Returns new GameState with updated dice and rolls_used.
    If already rolled 3 times or game is over, returns state unchanged.

    Args:
        state: Current game state

    Returns:
        New GameState with rolled dice
    """
    if state.rolls_used >= 3 or state.game_over:
        return state

    new_dice = tuple(die.roll() for die in state.dice)
    return replace(state,
                   dice=new_dice,
                   rolls_used=state.rolls_used + 1)


def toggle_die_hold(state: GameState, die_index: int) -> GameState:
    """
    Toggle hold status of a specific die.

    Returns new GameState with updated die.
    If index is invalid or game is over, returns state unchanged.

    Args:
        state: Current game state
        die_index: Index of die to toggle (0-4)

    Returns:
        New GameState with die hold toggled
    """
    if not (0 <= die_index < 5) or state.game_over:
        return state

    dice_list = list(state.dice)
    dice_list[die_index] = dice_list[die_index].toggle_held()
    return replace(state, dice=tuple(dice_list))


def select_category(state: GameState, category: Category) -> GameState:
    """
    Lock in score for a category and advance to next turn.

    Calculates score for the category, updates scorecard, advances round,
    and resets turn state (unholds all dice, resets rolls_used).
    If all categories filled, sets game_over to True.

    Args:
        state: Current game state
        category: Category to score

    Returns:
        New GameState with category scored and turn advanced
    """
    # Validate category is available
    if state.scorecard.is_filled(category) or state.game_over:
        return state

    # Calculate and set score
    score = calculate_score(category, state.dice)
    new_scorecard = state.scorecard.with_score(category, score)

    # Check if game is complete
    is_complete = new_scorecard.is_complete()

    if is_complete:
        return replace(state,
                      scorecard=new_scorecard,
                      game_over=True)
    else:
        # Start new turn - reset dice holds and rolls
        new_dice = tuple(replace(die, held=False) for die in state.dice)
        return replace(state,
                      dice=new_dice,
                      scorecard=new_scorecard,
                      rolls_used=0,
                      current_round=state.current_round + 1)


def can_roll(state: GameState) -> bool:
    """
    Check if player can roll dice.

    Player can roll if game is not over and hasn't used all 3 rolls.

    Args:
        state: Current game state

    Returns:
        True if can roll, False otherwise
    """
    return not state.game_over and state.rolls_used < 3


def can_select_category(state: GameState, category: Category) -> bool:
    """
    Check if category is available to select.

    Category is available if game is not over and category not yet filled.

    Args:
        state: Current game state
        category: Category to check

    Returns:
        True if category can be selected, False otherwise
    """
    return not state.game_over and not state.scorecard.is_filled(category)


def reset_game() -> GameState:
    """
    Create a fresh game state (equivalent to starting over).

    Returns:
        New GameState with initial values
    """
    return GameState.create_initial()
