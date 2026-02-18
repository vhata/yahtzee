"""
Dice Tables — Precomputed combinatorics for exact Yahtzee probability calculations.

All constants are computed at import time (~10ms). No randomness involved.

Constants:
    ALL_COMBOS       — 252 distinct unordered 5-dice outcomes (sorted tuples)
    COMBO_TO_INDEX   — Reverse lookup: sorted tuple → index (0-251)
    COMBO_PROBS      — Multinomial probability of each combo when rolling 5 dice
    SCORE_TABLE      — 252×13 table: score for each combo in each category
    TRANSITIONS      — Dict: held_values_tuple → list of (combo_idx, probability)
    CATEGORY_EV      — Dict: Category → expected score for a dedicated 3-roll turn

Functions:
    unique_holds(combo) — All distinct sub-multisets of a 5-dice combo
"""
import itertools
import math
from collections import Counter

from game_engine import Category, DieState, calculate_score

# ── ALL_COMBOS: 252 distinct unordered 5-dice outcomes ───────────────────────

ALL_COMBOS = list(itertools.combinations_with_replacement(range(1, 7), 5))

COMBO_TO_INDEX = {combo: i for i, combo in enumerate(ALL_COMBOS)}


# ── COMBO_PROBS: multinomial probability of each combo ───────────────────────

def _multinomial_prob(combo):
    """Probability of rolling this unordered combo with 5 fair dice.

    P = (5! / (n1! × n2! × ... × nk!)) / 6^5
    where n_i are the counts of each distinct value.
    """
    counts = Counter(combo)
    numerator = math.factorial(5)
    for c in counts.values():
        numerator //= math.factorial(c)
    return numerator / (6 ** 5)

COMBO_PROBS = [_multinomial_prob(combo) for combo in ALL_COMBOS]


# ── SCORE_TABLE: 252×13 score lookup ─────────────────────────────────────────

_ALL_CATEGORIES = list(Category)

def _build_score_table():
    """Build SCORE_TABLE[combo_idx][cat_idx] using game_engine.calculate_score()."""
    table = []
    for combo in ALL_COMBOS:
        dice = tuple(DieState(value=v) for v in combo)
        row = [calculate_score(cat, dice) for cat in _ALL_CATEGORIES]
        table.append(row)
    return table

SCORE_TABLE = _build_score_table()


# ── unique_holds: all distinct sub-multisets of a combo ──────────────────────

def unique_holds(combo):
    """Return all distinct sorted tuples that are sub-multisets of combo.

    For a combo like (1,1,2,3,4), the holds include (), (1,), (1,1), (2,),
    (1,2), etc. — every distinct subset of the multiset of dice values.

    Args:
        combo: Sorted tuple of 5 dice values (1-6)

    Returns:
        List of distinct sorted tuples (sub-multisets)
    """
    seen = set()
    # Generate all 2^5 = 32 subsets by index, but deduplicate by value
    for mask in range(32):
        hold = tuple(sorted(combo[i] for i in range(5) if mask & (1 << i)))
        seen.add(hold)
    return list(seen)


# ── TRANSITIONS: held_values → distribution over resulting combos ────────────

def _build_transitions():
    """Build the transition table for all possible held-values multisets.

    For each unique held-values tuple, compute the probability distribution
    over resulting 5-dice combos when keeping those values and rerolling the rest.
    """
    transitions = {}

    # Collect all unique held-values from all combos
    all_holds = set()
    for combo in ALL_COMBOS:
        for hold in unique_holds(combo):
            all_holds.add(hold)

    for held in all_holds:
        num_reroll = 5 - len(held)

        if num_reroll == 0:
            # Holding all dice — deterministic
            combo = tuple(sorted(held))
            idx = COMBO_TO_INDEX[combo]
            transitions[held] = [(idx, 1.0)]
            continue

        # Enumerate all possible reroll outcomes
        outcome_probs = {}
        for reroll in itertools.product(range(1, 7), repeat=num_reroll):
            result = tuple(sorted(held + reroll))
            idx = COMBO_TO_INDEX[result]
            # Each specific ordered reroll has probability (1/6)^num_reroll
            prob = (1.0 / 6.0) ** num_reroll
            outcome_probs[idx] = outcome_probs.get(idx, 0.0) + prob

        transitions[held] = list(outcome_probs.items())

    return transitions

TRANSITIONS = _build_transitions()


# ── CATEGORY_EV: expected score per category for a dedicated 3-roll turn ─────

def _compute_category_ev():
    """Compute expected score for each category via backward induction.

    For a single category played optimally over 3 rolls:
    - roll3_value[combo] = score for that category with combo
    - roll2_value[combo] = max over holds of: E[roll3_value | hold]
    - roll1_value = E over all combos of: max over holds of: E[roll2_value | hold]
    """
    num_combos = len(ALL_COMBOS)
    category_evs = {}

    for cat_idx, cat in enumerate(_ALL_CATEGORIES):
        # Phase 3: After 3rd roll — just the score
        roll3_value = [float(SCORE_TABLE[i][cat_idx]) for i in range(num_combos)]

        # Phase 2: After 2nd roll — best hold leading to 3rd roll
        roll2_value = [0.0] * num_combos
        for i, combo in enumerate(ALL_COMBOS):
            best = roll3_value[i]  # Option: score now (don't reroll)
            for hold in unique_holds(combo):
                ev = sum(prob * roll3_value[ci] for ci, prob in TRANSITIONS[hold])
                if ev > best:
                    best = ev
            roll2_value[i] = best

        # Phase 1: Before any roll — expected value over all first-roll combos
        # First roll = holding nothing
        ev = sum(prob * roll2_value[ci] for ci, prob in TRANSITIONS[()])
        category_evs[cat] = ev

    return category_evs

CATEGORY_EV = _compute_category_ev()
