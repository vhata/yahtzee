"""
Yahtzee AI — Strategy interface, game loop, and AI player implementations.

Contains:
- Action types (RollAction, ScoreAction)
- YahtzeeStrategy abstract base class
- play_turn() and play_game() game loop functions
- RandomStrategy, GreedyStrategy, ExpectedValueStrategy
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from typing import Tuple, Union
import random

from collections import Counter

from game_engine import (
    Category, GameState, DieState, Scorecard,
    roll_dice, toggle_die_hold, select_category,
    can_roll, can_select_category, calculate_score,
)


# ── Action Types ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RollAction:
    """Hold specific dice and re-roll the rest."""
    hold: Tuple[int, ...]  # dice indices (0-4) to hold; rest get rolled


@dataclass(frozen=True)
class ScoreAction:
    """Lock in a score for a category."""
    category: Category


# ── Strategy Interface ──────────────────────────────────────────────────────

class YahtzeeStrategy(ABC):
    """Abstract base class for Yahtzee AI strategies."""

    @abstractmethod
    def choose_action(self, state: GameState) -> Union[RollAction, ScoreAction]:
        """Given state (after at least 1 roll), decide: roll again or score.

        Args:
            state: Current game state with rolls_used >= 1

        Returns:
            RollAction to hold dice and re-roll, or ScoreAction to lock in a category
        """
        ...


# ── Game Loop ───────────────────────────────────────────────────────────────

def _apply_holds(state: GameState, hold_indices: Tuple[int, ...]) -> GameState:
    """Set hold status on dice: hold those in hold_indices, unhold the rest.

    This ensures the dice hold state matches exactly what the strategy requested,
    regardless of what was held before.
    """
    for i in range(5):
        should_hold = i in hold_indices
        is_held = state.dice[i].held
        if should_hold != is_held:
            state = toggle_die_hold(state, i)
    return state


def play_turn(state: GameState, strategy: YahtzeeStrategy) -> GameState:
    """Play one turn: mandatory first roll, then strategy decisions until scoring.

    Args:
        state: Game state at the start of a turn (rolls_used == 0)
        strategy: The AI strategy to use for decisions

    Returns:
        Game state after the turn is complete (category scored, ready for next turn)
    """
    # Mandatory first roll
    state = roll_dice(state)

    while True:
        action = strategy.choose_action(state)

        if isinstance(action, ScoreAction):
            return select_category(state, action.category)

        # RollAction: apply holds and roll again
        if not can_roll(state):
            # Strategy returned RollAction but no rolls left — shouldn't happen
            # with well-behaved strategies, but handle gracefully by forcing a score.
            # Pick first available category.
            for cat in Category:
                if can_select_category(state, cat):
                    return select_category(state, cat)

        state = _apply_holds(state, action.hold)
        state = roll_dice(state)


def play_game(strategy: YahtzeeStrategy) -> GameState:
    """Play a complete 13-round Yahtzee game.

    Args:
        strategy: The AI strategy to use

    Returns:
        Final game state with game_over == True
    """
    state = GameState.create_initial()
    while not state.game_over:
        state = play_turn(state, strategy)
    return state


# ── RandomStrategy ──────────────────────────────────────────────────────────

class RandomStrategy(YahtzeeStrategy):
    """Baseline strategy: random holds, random category selection.

    50% chance to roll again (if rolls remain), random subset of dice held,
    random unfilled category chosen when scoring.
    """

    def choose_action(self, state: GameState) -> Union[RollAction, ScoreAction]:
        # If we've used all 3 rolls, must score
        if state.rolls_used >= 3:
            return self._random_score(state)

        # 50% chance to roll again
        if random.random() < 0.5:
            # Random subset of dice to hold
            hold = tuple(i for i in range(5) if random.random() < 0.5)
            return RollAction(hold=hold)

        return self._random_score(state)

    def _random_score(self, state: GameState) -> ScoreAction:
        """Pick a random unfilled category."""
        available = [cat for cat in Category if not state.scorecard.is_filled(cat)]
        return ScoreAction(category=random.choice(available))


# ── GreedyStrategy ─────────────────────────────────────────────────────────

# Upper section categories mapped to their face value
_UPPER_CATS = {
    Category.ONES: 1, Category.TWOS: 2, Category.THREES: 3,
    Category.FOURS: 4, Category.FIVES: 5, Category.SIXES: 6,
}

# Thresholds for "good enough" scores to take immediately
_GOOD_SCORE_THRESHOLDS = {
    Category.YAHTZEE: 50,
    Category.LARGE_STRAIGHT: 40,
    Category.SMALL_STRAIGHT: 30,
    Category.FULL_HOUSE: 25,
}


class GreedyStrategy(YahtzeeStrategy):
    """Rule-based strategy that takes good scores and holds promising dice.

    Decision logic:
    - Takes any "good enough" score immediately (Yahtzee, straights, full house)
    - For upper section, takes scores >= 3x face value
    - For n-of-a-kind, takes scores >= 20
    - When re-rolling: holds the most frequent value (aiming for n-of-a-kind)
      or holds partial straights
    """

    def choose_action(self, state: GameState) -> Union[RollAction, ScoreAction]:
        if state.rolls_used >= 3:
            return self._best_score(state)

        # Check if any category has a "good enough" score worth taking now
        good_action = self._check_good_scores(state)
        if good_action is not None:
            return good_action

        # Re-roll with smart holds
        hold = self._choose_holds(state)
        return RollAction(hold=hold)

    def _check_good_scores(self, state: GameState) -> Union[ScoreAction, None]:
        """Check if any unfilled category has a score worth taking immediately."""
        available = [cat for cat in Category if not state.scorecard.is_filled(cat)]

        # Check high-value fixed-score categories first
        for cat in [Category.YAHTZEE, Category.LARGE_STRAIGHT,
                    Category.SMALL_STRAIGHT, Category.FULL_HOUSE]:
            if cat in available:
                score = calculate_score(cat, state.dice)
                if score >= _GOOD_SCORE_THRESHOLDS[cat]:
                    return ScoreAction(category=cat)

        # Check upper section — take if >= 3x face value (on track for bonus)
        for cat, face in _UPPER_CATS.items():
            if cat in available:
                score = calculate_score(cat, state.dice)
                if score >= face * 3:
                    return ScoreAction(category=cat)

        # Check n-of-a-kind categories for high scores
        for cat in [Category.FOUR_OF_KIND, Category.THREE_OF_KIND]:
            if cat in available:
                score = calculate_score(cat, state.dice)
                if score >= 20:
                    return ScoreAction(category=cat)

        # Check Chance for high scores
        if Category.CHANCE in available:
            score = calculate_score(Category.CHANCE, state.dice)
            if score >= 25:
                return ScoreAction(category=Category.CHANCE)

        return None

    def _choose_holds(self, state: GameState) -> Tuple[int, ...]:
        """Decide which dice to hold when re-rolling."""
        values = [die.value for die in state.dice]
        counts = Counter(values)

        # Check for partial straight (4 in a row) — hold those dice
        value_set = set(values)
        for straight in [{1, 2, 3, 4}, {2, 3, 4, 5}, {3, 4, 5, 6}]:
            overlap = straight & value_set
            if len(overlap) >= 3:
                # Hold dice that are part of the straight
                hold = []
                held_values = set()
                for i, v in enumerate(values):
                    if v in straight and v not in held_values:
                        hold.append(i)
                        held_values.add(v)
                return tuple(hold)

        # Default: hold the most frequent value (aiming for n-of-a-kind)
        most_common_val = counts.most_common(1)[0][0]
        hold = tuple(i for i, v in enumerate(values) if v == most_common_val)
        return hold

    def _best_score(self, state: GameState) -> ScoreAction:
        """Pick the best available category to score."""
        available = [cat for cat in Category if not state.scorecard.is_filled(cat)]

        best_cat = None
        best_score = -1

        for cat in available:
            score = calculate_score(cat, state.dice)

            # Weight upper section scores to encourage bonus
            if cat in _UPPER_CATS:
                face = _UPPER_CATS[cat]
                # Bonus if at or above 3x face value target
                if score >= face * 3:
                    score += 5  # Small bonus for being on-target for upper bonus

            if score > best_score:
                best_score = score
                best_cat = cat

        # If everything scores 0, pick the least damaging category to waste
        if best_score == 0:
            return self._waste_category(state, available)

        return ScoreAction(category=best_cat)

    def _waste_category(self, state: GameState, available: list) -> ScoreAction:
        """When forced to score 0, pick the least valuable category to waste."""
        # Prefer wasting categories with lowest expected value
        waste_order = [
            Category.YAHTZEE,  # hardest to get, waste if already 0
            Category.LARGE_STRAIGHT,
            Category.FULL_HOUSE,
            Category.SMALL_STRAIGHT,
            Category.ONES,  # lowest upper section impact
            Category.TWOS,
            Category.THREES,
            Category.FOUR_OF_KIND,
            Category.THREE_OF_KIND,
            Category.FOURS,
            Category.FIVES,
            Category.SIXES,
            Category.CHANCE,  # never waste Chance — it always scores something
        ]
        for cat in waste_order:
            if cat in available:
                return ScoreAction(category=cat)
        return ScoreAction(category=available[0])


# ── ExpectedValueStrategy ──────────────────────────────────────────────────

class ExpectedValueStrategy(YahtzeeStrategy):
    """Simulation-based strategy that evaluates all 32 hold combinations.

    For each of the 32 possible subsets of dice to hold, simulates N random
    re-rolls and computes the average best-available-category score. Compares
    "score now" vs "best hold + roll again" and picks the higher expected value.

    Also considers upper section bonus progress when choosing categories.
    """

    def __init__(self, num_simulations: int = 200):
        self.num_simulations = num_simulations

    def choose_action(self, state: GameState) -> Union[RollAction, ScoreAction]:
        if state.rolls_used >= 3:
            return ScoreAction(category=self._best_category(state))

        available = [cat for cat in Category if not state.scorecard.is_filled(cat)]

        # Evaluate scoring now: best category score
        best_now_cat = self._best_category(state)
        best_now_score = self._adjusted_score(state, best_now_cat)

        # Evaluate all 32 hold combinations
        best_hold = None
        best_hold_ev = -1.0

        for mask in range(32):
            hold = tuple(i for i in range(5) if mask & (1 << i))
            ev = self._simulate_hold(state, hold, available)
            if ev > best_hold_ev:
                best_hold_ev = ev
                best_hold = hold

        # Compare: score now vs roll again
        if best_now_score >= best_hold_ev:
            return ScoreAction(category=best_now_cat)
        else:
            return RollAction(hold=best_hold)

    def _simulate_hold(self, state: GameState, hold: Tuple[int, ...],
                       available: list) -> float:
        """Simulate N re-rolls with given hold and return average best score."""
        total = 0.0
        held_values = [state.dice[i].value for i in hold]
        num_reroll = 5 - len(hold)

        for _ in range(self.num_simulations):
            # Generate random values for non-held dice
            new_values = list(held_values)
            rerolled = [random.randint(1, 6) for _ in range(num_reroll)]

            # Reconstruct full dice tuple in correct order
            dice_values = [0] * 5
            for i in hold:
                dice_values[i] = state.dice[i].value
            ri = 0
            for i in range(5):
                if i not in hold:
                    dice_values[i] = rerolled[ri]
                    ri += 1

            sim_dice = tuple(DieState(value=v) for v in dice_values)

            # Find best score across available categories
            best = 0.0
            for cat in available:
                score = self._adjusted_score_for_dice(state, cat, sim_dice)
                if score > best:
                    best = score
            total += best

        return total / self.num_simulations

    def _best_category(self, state: GameState) -> Category:
        """Pick the best category to score given current dice."""
        available = [cat for cat in Category if not state.scorecard.is_filled(cat)]

        best_cat = available[0]
        best_score = -1.0

        for cat in available:
            score = self._adjusted_score(state, cat)
            if score > best_score:
                best_score = score
                best_cat = cat

        return best_cat

    def _adjusted_score(self, state: GameState, cat: Category) -> float:
        """Calculate score with upper section bonus consideration."""
        return self._adjusted_score_for_dice(state, cat, state.dice)

    def _adjusted_score_for_dice(self, state: GameState, cat: Category,
                                  dice: Tuple[DieState, ...]) -> float:
        """Calculate adjusted score for specific dice, considering bonus progress."""
        score = float(calculate_score(cat, dice))

        if cat in _UPPER_CATS:
            face = _UPPER_CATS[cat]
            target = face * 3  # Target for upper bonus (63 total = 3x each)

            # Current upper section progress
            upper_total = state.scorecard.get_upper_section_total()
            upper_filled = sum(1 for c in _UPPER_CATS if state.scorecard.is_filled(c))
            upper_remaining = 6 - upper_filled

            if upper_remaining > 0:
                # How much more we need for the bonus
                needed = 63 - upper_total
                avg_needed_per_cat = needed / upper_remaining

                actual = calculate_score(cat, dice)
                surplus = actual - avg_needed_per_cat

                # Reward being on-track for bonus, penalize falling behind
                if surplus >= 0:
                    score += min(surplus, 10)  # Cap the bonus at 10
                else:
                    score += surplus * 0.5  # Smaller penalty for being behind

        # Penalize scoring 0 — prefer to waste less valuable categories
        if score == 0:
            score = -self._category_waste_cost(cat)

        return score

    @staticmethod
    def _category_waste_cost(cat: Category) -> float:
        """Estimate how costly it is to waste a category with 0 points.

        Higher values mean the category is more valuable and more costly to waste.
        """
        costs = {
            Category.ONES: 1.5,
            Category.TWOS: 3.0,
            Category.THREES: 4.5,
            Category.FOURS: 6.0,
            Category.FIVES: 7.5,
            Category.SIXES: 9.0,
            Category.THREE_OF_KIND: 10.0,
            Category.FOUR_OF_KIND: 8.0,
            Category.FULL_HOUSE: 12.0,
            Category.SMALL_STRAIGHT: 14.0,
            Category.LARGE_STRAIGHT: 16.0,
            Category.YAHTZEE: 5.0,  # Low because it's very hard to get
            Category.CHANCE: 20.0,  # Very costly — always scores something
        }
        return costs.get(cat, 10.0)
