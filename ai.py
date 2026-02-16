"""
Yahtzee AI — Strategy interface, game loop, and AI player implementations.

Contains:
- Action types (RollAction, ScoreAction)
- YahtzeeStrategy abstract base class
- play_turn() and play_game() game loop functions
- RandomStrategy, GreedyStrategy, ExpectedValueStrategy, OptimalStrategy
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
    calculate_score_in_context,
)


# ── Action Types ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RollAction:
    """Hold specific dice and re-roll the rest."""
    hold: Tuple[int, ...]  # dice indices (0-4) to hold; rest get rolled
    reason: str = ""


@dataclass(frozen=True)
class ScoreAction:
    """Lock in a score for a category."""
    category: Category
    reason: str = ""


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
            return RollAction(hold=hold, reason="Feeling lucky — random hold and re-roll")

        return self._random_score(state)

    def _random_score(self, state: GameState) -> ScoreAction:
        """Pick a random unfilled category."""
        available = [cat for cat in Category if not state.scorecard.is_filled(cat)]
        cat = random.choice(available)
        return ScoreAction(category=cat, reason=f"Randomly picking {cat.value}")


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
        hold, hold_reason = self._choose_holds(state)
        return RollAction(hold=hold, reason=hold_reason)

    def _check_good_scores(self, state: GameState) -> Union[ScoreAction, None]:
        """Check if any unfilled category has a score worth taking immediately."""
        available = [cat for cat in Category if not state.scorecard.is_filled(cat)]

        # Check high-value fixed-score categories first
        for cat in [Category.YAHTZEE, Category.LARGE_STRAIGHT,
                    Category.SMALL_STRAIGHT, Category.FULL_HOUSE]:
            if cat in available:
                score = calculate_score_in_context(cat, state.dice, state.scorecard)
                if score >= _GOOD_SCORE_THRESHOLDS[cat]:
                    return ScoreAction(
                        category=cat,
                        reason=f"Taking {cat.value} for {score} — that's a great score!")

        # Check upper section — take if >= 3x face value (on track for bonus)
        for cat, face in _UPPER_CATS.items():
            if cat in available:
                score = calculate_score_in_context(cat, state.dice, state.scorecard)
                if score >= face * 3:
                    return ScoreAction(
                        category=cat,
                        reason=f"Scoring {cat.value} for {score} — on track for upper bonus")

        # Check n-of-a-kind categories for high scores
        for cat in [Category.FOUR_OF_KIND, Category.THREE_OF_KIND]:
            if cat in available:
                score = calculate_score_in_context(cat, state.dice, state.scorecard)
                if score >= 20:
                    return ScoreAction(
                        category=cat,
                        reason=f"Taking {cat.value} for {score}")

        # Check Chance for high scores
        if Category.CHANCE in available:
            score = calculate_score_in_context(Category.CHANCE, state.dice, state.scorecard)
            if score >= 25:
                return ScoreAction(
                    category=Category.CHANCE,
                    reason=f"Taking Chance for {score} — high dice total")

        return None

    def _choose_holds(self, state: GameState) -> tuple:
        """Decide which dice to hold when re-rolling.

        Returns:
            (hold_indices, reason) tuple
        """
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
                held_vals = sorted(held_values)
                return tuple(hold), f"Holding {held_vals} — going for a straight"

        # Default: hold the most frequent value (aiming for n-of-a-kind)
        most_common_val = counts.most_common(1)[0][0]
        hold = tuple(i for i, v in enumerate(values) if v == most_common_val)
        return hold, f"Holding the {most_common_val}s — going for multiple of a kind"

    def _best_score(self, state: GameState) -> ScoreAction:
        """Pick the best available category to score."""
        available = [cat for cat in Category if not state.scorecard.is_filled(cat)]

        best_cat = None
        best_score = -1

        for cat in available:
            score = calculate_score_in_context(cat, state.dice, state.scorecard)

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

        actual_score = calculate_score_in_context(best_cat, state.dice, state.scorecard)
        return ScoreAction(
            category=best_cat,
            reason=f"Out of rolls — best available is {best_cat.value} for {actual_score}")

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
                return ScoreAction(
                    category=cat,
                    reason=f"Nothing scores — sacrificing {cat.value}")
        return ScoreAction(
            category=available[0],
            reason=f"Nothing scores — sacrificing {available[0].value}")


# ── Shared upper section targets (used by EV and Optimal strategies) ───────

from dice_tables import CATEGORY_EV

_UPPER_TARGETS = {
    Category.ONES: 3, Category.TWOS: 6, Category.THREES: 9,
    Category.FOURS: 12, Category.FIVES: 15, Category.SIXES: 18,
}


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
            best_cat = self._best_category(state)
            score = calculate_score_in_context(best_cat, state.dice, state.scorecard)
            return ScoreAction(
                category=best_cat,
                reason=f"Out of rolls — {best_cat.value} is the best option for {score}")

        available = [cat for cat in Category if not state.scorecard.is_filled(cat)]

        # Evaluate scoring now: best category score
        best_now_cat = self._best_category(state)
        best_now_score = self._adjusted_score(state, best_now_cat)

        # Evaluate all 32 hold combinations (with caching for identical held values)
        best_hold = None
        best_hold_ev = -1.0
        ev_cache = {}  # key: tuple(sorted(held_values)) -> cached EV

        for mask in range(32):
            hold = tuple(i for i in range(5) if mask & (1 << i))
            cache_key = tuple(sorted(state.dice[i].value for i in hold))
            if cache_key in ev_cache:
                ev = ev_cache[cache_key]
            else:
                ev = self._simulate_hold(state, hold, available)
                ev_cache[cache_key] = ev
            if ev > best_hold_ev:
                best_hold_ev = ev
                best_hold = hold

        # Compare: score now vs roll again
        if best_now_score >= best_hold_ev:
            actual_score = calculate_score_in_context(best_now_cat, state.dice, state.scorecard)
            return ScoreAction(
                category=best_now_cat,
                reason=f"Scoring {best_now_cat.value} for {actual_score} (EV of rolling: {best_hold_ev:.1f})")
        else:
            held_values = sorted([state.dice[i].value for i in best_hold])
            return RollAction(
                hold=best_hold,
                reason=f"Holding {held_values} and rolling (EV: {best_hold_ev:.1f} vs scoring now: {best_now_score:.1f})")

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
        """Calculate score with upper section bonus consideration.

        Uses calculate_score_in_context for the actual dice (not simulated)
        so joker rules are applied when scoring now.
        """
        raw_score = float(calculate_score_in_context(cat, state.dice, state.scorecard))
        adjustment = 0.0

        # Opportunity cost: penalize using a category for less than its EV
        category_ev = CATEGORY_EV[cat]
        if raw_score > 0:
            opportunity_cost = max(0.0, category_ev - raw_score)
            adjustment -= opportunity_cost
        else:
            # Zero score: heavy penalty based on the category's expected value
            adjustment -= (category_ev + 5.0)

        # Upper bonus delta: how does scoring here affect bonus probability?
        if cat in _UPPER_CATS:
            upper_total = state.scorecard.get_upper_section_total()
            upper_filled = sum(1 for c in _UPPER_CATS if state.scorecard.is_filled(c))
            upper_remaining = 6 - upper_filled

            if upper_remaining > 0:
                needed = 63 - upper_total
                expected_remaining_before = sum(
                    _UPPER_TARGETS[c] for c in _UPPER_CATS
                    if not state.scorecard.is_filled(c)
                )
                expected_remaining_after = expected_remaining_before - _UPPER_TARGETS[cat] + raw_score

                scale = max(10.0, upper_remaining * 3.0)

                p_before = max(0.0, min(1.0, (expected_remaining_before - needed) / scale + 0.5))
                p_after = max(0.0, min(1.0, (expected_remaining_after - needed) / scale + 0.5))

                adjustment += (p_after - p_before) * 35.0

        return raw_score + adjustment

    def _adjusted_score_for_dice(self, state: GameState, cat: Category,
                                  dice: Tuple[DieState, ...]) -> float:
        """Calculate adjusted score using opportunity cost and bonus probability.

        Uses the same principled model as OptimalStrategy:
        - Opportunity cost: penalizes using a category for less than its EV
        - Zero score: heavy penalty based on category's expected value
        - Upper bonus delta: probability-based model of bonus impact
        """
        raw_score = float(calculate_score_in_context(cat, dice, state.scorecard))
        adjustment = 0.0

        # Opportunity cost: penalize using a category for less than its EV
        category_ev = CATEGORY_EV[cat]
        if raw_score > 0:
            opportunity_cost = max(0.0, category_ev - raw_score)
            adjustment -= opportunity_cost
        else:
            # Zero score: heavy penalty based on the category's expected value
            adjustment -= (category_ev + 5.0)

        # Upper bonus delta: how does scoring here affect bonus probability?
        if cat in _UPPER_CATS:
            upper_total = state.scorecard.get_upper_section_total()
            upper_filled = sum(1 for c in _UPPER_CATS if state.scorecard.is_filled(c))
            upper_remaining = 6 - upper_filled

            if upper_remaining > 0:
                needed = 63 - upper_total
                expected_remaining_before = sum(
                    _UPPER_TARGETS[c] for c in _UPPER_CATS
                    if not state.scorecard.is_filled(c)
                )
                expected_remaining_after = expected_remaining_before - _UPPER_TARGETS[cat] + raw_score

                scale = max(10.0, upper_remaining * 3.0)

                p_before = max(0.0, min(1.0, (expected_remaining_before - needed) / scale + 0.5))
                p_after = max(0.0, min(1.0, (expected_remaining_after - needed) / scale + 0.5))

                adjustment += (p_after - p_before) * 35.0

        return raw_score + adjustment


# ── OptimalStrategy ───────────────────────────────────────────────────────────

from dice_tables import (
    ALL_COMBOS, COMBO_TO_INDEX, COMBO_PROBS,
    SCORE_TABLE, TRANSITIONS,
    unique_holds,
)

_ALL_CATEGORIES = list(Category)
_UPPER_CAT_INDICES = {
    Category.ONES: 0, Category.TWOS: 1, Category.THREES: 2,
    Category.FOURS: 3, Category.FIVES: 4, Category.SIXES: 5,
}


class OptimalStrategy(YahtzeeStrategy):
    """Exact-probability strategy with two-roll lookahead and opportunity cost.

    Uses precomputed dice tables for exact EV calculations instead of
    Monte Carlo simulation. Considers:
    - All possible hold combinations via unique_holds()
    - Two-roll lookahead (rolls_used==1: look through both remaining rolls)
    - Opportunity cost: penalizes using a category for less than its EV
    - Upper bonus probability: adjusts values based on bonus likelihood

    No randomness — purely deterministic given the same game state.
    """

    def choose_action(self, state: GameState) -> Union[RollAction, ScoreAction]:
        available = [cat for cat in Category if not state.scorecard.is_filled(cat)]
        available_indices = [_ALL_CATEGORIES.index(cat) for cat in available]

        if state.rolls_used >= 3:
            best_cat = self._best_category(state, available, available_indices)
            score = calculate_score_in_context(best_cat, state.dice, state.scorecard)
            return ScoreAction(
                category=best_cat,
                reason=f"Must score — {best_cat.value} for {score}")

        combo = tuple(sorted(die.value for die in state.dice))
        combo_idx = COMBO_TO_INDEX[combo]

        # Build value tables for remaining rolls
        if state.rolls_used == 2:
            # 1 roll left: compare scoring now vs one more roll
            roll_values = self._build_roll3_values(available_indices, state)
            best_score_cat, best_score_val = self._best_score_now(
                state, available, available_indices, combo_idx)
            best_hold, best_hold_ev = self._best_hold_ev(combo, roll_values)

            if best_score_val >= best_hold_ev:
                score = calculate_score_in_context(best_score_cat, state.dice, state.scorecard)
                return ScoreAction(
                    category=best_score_cat,
                    reason=f"Scoring {best_score_cat.value} for {score} (roll EV: {best_hold_ev:.1f})")
            else:
                hold_indices = self._hold_to_indices(state.dice, best_hold)
                held_vals = sorted(state.dice[i].value for i in hold_indices)
                return RollAction(
                    hold=hold_indices,
                    reason=f"Holding {held_vals} (EV: {best_hold_ev:.1f} vs score: {best_score_val:.1f})")

        else:
            # rolls_used == 1: 2 rolls left — two-level lookahead
            roll3_values = self._build_roll3_values(available_indices, state)
            roll2_values = self._build_roll2_values(roll3_values)

            best_score_cat, best_score_val = self._best_score_now(
                state, available, available_indices, combo_idx)
            best_hold, best_hold_ev = self._best_hold_ev(combo, roll2_values)

            if best_score_val >= best_hold_ev:
                score = calculate_score_in_context(best_score_cat, state.dice, state.scorecard)
                return ScoreAction(
                    category=best_score_cat,
                    reason=f"Scoring {best_score_cat.value} for {score} (2-roll EV: {best_hold_ev:.1f})")
            else:
                hold_indices = self._hold_to_indices(state.dice, best_hold)
                held_vals = sorted(state.dice[i].value for i in hold_indices)
                return RollAction(
                    hold=hold_indices,
                    reason=f"Holding {held_vals} (2-roll EV: {best_hold_ev:.1f} vs score: {best_score_val:.1f})")

    def _build_roll3_values(self, available_indices, state):
        """Build roll3_values[252]: best category value for each combo after final roll."""
        num_combos = len(ALL_COMBOS)
        values = [0.0] * num_combos
        for ci in range(num_combos):
            best = -1e9
            for cat_idx in available_indices:
                cat = _ALL_CATEGORIES[cat_idx]
                raw = float(SCORE_TABLE[ci][cat_idx])
                adjusted = raw + self._category_adjustment(state, cat, raw)
                if adjusted > best:
                    best = adjusted
            values[ci] = best
        return values

    def _build_roll2_values(self, roll3_values):
        """Build roll2_values[252]: best of score-now or roll-once using roll3_values."""
        num_combos = len(ALL_COMBOS)
        values = [0.0] * num_combos
        for ci, combo in enumerate(ALL_COMBOS):
            # Best hold EV from one more roll
            best = roll3_values[ci]  # baseline: don't reroll (hold all)
            for hold in unique_holds(combo):
                ev = sum(prob * roll3_values[ri] for ri, prob in TRANSITIONS[hold])
                if ev > best:
                    best = ev
            values[ci] = best
        return values

    def _best_score_now(self, state, available, available_indices, combo_idx):
        """Find the best category to score right now and its adjusted value."""
        best_cat = available[0]
        best_val = -1e9
        for i, cat_idx in enumerate(available_indices):
            cat = available[i]
            raw = float(SCORE_TABLE[combo_idx][cat_idx])
            adjusted = raw + self._category_adjustment(state, cat, raw)
            if adjusted > best_val:
                best_val = adjusted
                best_cat = cat
        return best_cat, best_val

    def _best_hold_ev(self, combo, roll_values):
        """Find the best hold and its EV given a roll_values lookup."""
        best_hold = ()
        best_ev = -1e9
        for hold in unique_holds(combo):
            ev = sum(prob * roll_values[ci] for ci, prob in TRANSITIONS[hold])
            if ev > best_ev:
                best_ev = ev
                best_hold = hold
        return best_hold, best_ev

    def _best_category(self, state, available, available_indices):
        """Pick the best category when forced to score (rolls_used==3)."""
        combo = tuple(sorted(die.value for die in state.dice))
        combo_idx = COMBO_TO_INDEX[combo]
        best_cat = available[0]
        best_val = -1e9
        for i, cat_idx in enumerate(available_indices):
            cat = available[i]
            raw = float(SCORE_TABLE[combo_idx][cat_idx])
            adjusted = raw + self._category_adjustment(state, cat, raw)
            if adjusted > best_val:
                best_val = adjusted
                best_cat = cat
        return best_cat

    def _category_adjustment(self, state, cat, raw_score):
        """Compute the adjustment to a raw score for category valuation.

        Includes opportunity cost penalty and upper bonus probability delta.
        """
        adjustment = 0.0

        # Opportunity cost: penalize using a category for less than its EV
        category_ev = CATEGORY_EV[cat]
        if raw_score > 0:
            opportunity_cost = max(0.0, category_ev - raw_score)
            adjustment -= opportunity_cost
        else:
            # Zero score: heavy penalty based on the category's expected value
            adjustment -= (category_ev + 5.0)

        # Upper bonus delta: how does scoring here affect bonus probability?
        if cat in _UPPER_CATS:
            face = _UPPER_CATS[cat]
            target = face * 3  # target contribution for this category

            upper_total = state.scorecard.get_upper_section_total()
            upper_filled = sum(1 for c in _UPPER_CATS if state.scorecard.is_filled(c))
            upper_remaining = 6 - upper_filled

            if upper_remaining > 0:
                needed = 63 - upper_total
                # Simple linear model: P(bonus) ≈ clamp((expected_remaining - needed) / scale + 0.5)
                # Expected remaining contribution if each unfilled cat scores its target
                expected_remaining_before = sum(
                    _UPPER_TARGETS[c] for c in _UPPER_CATS
                    if not state.scorecard.is_filled(c)
                )
                expected_remaining_after = expected_remaining_before - _UPPER_TARGETS[cat] + raw_score

                # Scale factor: how tight is the bonus race?
                scale = max(10.0, upper_remaining * 3.0)

                p_before = max(0.0, min(1.0, (expected_remaining_before - needed) / scale + 0.5))
                p_after = max(0.0, min(1.0, (expected_remaining_after - needed) / scale + 0.5))

                adjustment += (p_after - p_before) * 35.0

        return adjustment

    @staticmethod
    def _hold_to_indices(dice, held_values):
        """Convert value-based hold tuple to positional dice indices.

        Matches held values to actual dice positions, handling duplicates correctly.
        """
        indices = []
        remaining = list(held_values)
        for i, die in enumerate(dice):
            if die.value in remaining:
                indices.append(i)
                remaining.remove(die.value)
        return tuple(indices)
