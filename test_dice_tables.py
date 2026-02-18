"""
Dice Tables Test Suite

Tests for the precomputed dice combinatorics module (dice_tables.py).
Written first (TDD) — these tests define the API before implementation.

Covers:
    1. Combo enumeration — 252 distinct sorted 5-dice outcomes
    2. Probabilities — multinomial correctness, transition tables
    3. Score table — known scores for specific combos and categories
    4. Unique holds — sub-multiset enumeration
    5. Category EVs — expected values for dedicated 3-roll turns
"""

from dice_tables import (
    ALL_COMBOS,
    CATEGORY_EV,
    COMBO_PROBS,
    COMBO_TO_INDEX,
    SCORE_TABLE,
    TRANSITIONS,
    unique_holds,
)
from game_engine import Category

# ═══════════════════════════════════════════════════════════════════════════════
# 1. COMBO ENUMERATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestComboEnumeration:
    """ALL_COMBOS must be exactly the 252 distinct unordered 5-dice outcomes."""

    def test_252_combos(self):
        """There are exactly C(6+5-1, 5) = 252 distinct unordered 5-dice outcomes."""
        assert len(ALL_COMBOS) == 252

    def test_combos_are_sorted(self):
        """Each combo is a sorted tuple of values 1-6."""
        for combo in ALL_COMBOS:
            assert isinstance(combo, tuple)
            assert len(combo) == 5
            assert combo == tuple(sorted(combo))
            assert all(1 <= v <= 6 for v in combo)

    def test_combo_index_roundtrip(self):
        """COMBO_TO_INDEX[ALL_COMBOS[i]] == i for all i."""
        for i, combo in enumerate(ALL_COMBOS):
            assert COMBO_TO_INDEX[combo] == i

    def test_no_duplicate_combos(self):
        """All combos are unique."""
        assert len(set(ALL_COMBOS)) == len(ALL_COMBOS)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. PROBABILITIES
# ═══════════════════════════════════════════════════════════════════════════════

class TestProbabilities:
    """COMBO_PROBS and TRANSITIONS must be valid probability distributions."""

    def test_combo_probs_sum_to_one(self):
        """All 252 combo probabilities sum to 1.0."""
        total = sum(COMBO_PROBS)
        assert abs(total - 1.0) < 1e-10

    def test_known_probability_all_ones(self):
        """P((1,1,1,1,1)) = 1/7776 (only one way to roll all ones)."""
        idx = COMBO_TO_INDEX[(1, 1, 1, 1, 1)]
        expected = 1.0 / 7776.0
        assert abs(COMBO_PROBS[idx] - expected) < 1e-12

    def test_known_probability_pair(self):
        """P((1,1,2,3,4)) = 5!/(2!×1!×1!×1!) / 6^5 = 60/7776."""
        idx = COMBO_TO_INDEX[(1, 1, 2, 3, 4)]
        expected = 60.0 / 7776.0
        assert abs(COMBO_PROBS[idx] - expected) < 1e-12

    def test_transition_probs_sum_to_one(self):
        """For each held-values entry in TRANSITIONS, output probs sum to 1.0."""
        for held, outcomes in TRANSITIONS.items():
            total = sum(prob for _, prob in outcomes)
            assert abs(total - 1.0) < 1e-10, (
                f"Transition probs for held={held} sum to {total}, not 1.0"
            )

    def test_transition_hold_all_deterministic(self):
        """Holding all 5 dice → single outcome with probability 1.0."""
        held = (3, 3, 3, 3, 3)
        outcomes = TRANSITIONS[held]
        assert len(outcomes) == 1
        combo_idx, prob = outcomes[0]
        assert ALL_COMBOS[combo_idx] == held
        assert abs(prob - 1.0) < 1e-12

    def test_transition_hold_none(self):
        """Holding nothing → 252 outcomes matching full roll distribution."""
        outcomes = TRANSITIONS[()]
        assert len(outcomes) == 252
        total = sum(prob for _, prob in outcomes)
        assert abs(total - 1.0) < 1e-10


# ═══════════════════════════════════════════════════════════════════════════════
# 3. SCORE TABLE
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoreTable:
    """SCORE_TABLE[combo_idx][cat_idx] must match calculate_score()."""

    def test_yahtzee_scores_50(self):
        """All-same-value combos score 50 in Yahtzee category."""
        cat_idx = list(Category).index(Category.YAHTZEE)
        for val in range(1, 7):
            combo = (val,) * 5
            idx = COMBO_TO_INDEX[combo]
            assert SCORE_TABLE[idx][cat_idx] == 50

    def test_chance_equals_sum(self):
        """Every combo's Chance score equals sum of its values."""
        cat_idx = list(Category).index(Category.CHANCE)
        for i, combo in enumerate(ALL_COMBOS):
            assert SCORE_TABLE[i][cat_idx] == sum(combo)

    def test_large_straight(self):
        """(1,2,3,4,5) scores 40 in Large Straight."""
        cat_idx = list(Category).index(Category.LARGE_STRAIGHT)
        idx = COMBO_TO_INDEX[(1, 2, 3, 4, 5)]
        assert SCORE_TABLE[idx][cat_idx] == 40


# ═══════════════════════════════════════════════════════════════════════════════
# 4. UNIQUE HOLDS
# ═══════════════════════════════════════════════════════════════════════════════

class TestUniqueHolds:
    """unique_holds() enumerates all distinct sub-multisets of a dice combo."""

    def test_all_same_dice_6_holds(self):
        """(1,1,1,1,1) has 6 unique holds: hold 0, 1, 2, 3, 4, or 5 dice."""
        holds = unique_holds((1, 1, 1, 1, 1))
        assert len(holds) == 6
        # Should be: (), (1,), (1,1), (1,1,1), (1,1,1,1), (1,1,1,1,1)
        expected = {(), (1,), (1, 1), (1, 1, 1), (1, 1, 1, 1), (1, 1, 1, 1, 1)}
        assert set(holds) == expected

    def test_all_different_32_holds(self):
        """(1,2,3,4,5) has 32 unique holds (every subset is distinct)."""
        holds = unique_holds((1, 2, 3, 4, 5))
        assert len(holds) == 32

    def test_holds_are_sorted_tuples(self):
        """Each hold is a sorted tuple."""
        for combo in [(1, 2, 3, 4, 5), (3, 3, 3, 3, 3), (1, 1, 2, 2, 3)]:
            for hold in unique_holds(combo):
                assert isinstance(hold, tuple)
                assert hold == tuple(sorted(hold))

    def test_empty_hold_included(self):
        """() (hold nothing) is always in the result."""
        for combo in [(1, 2, 3, 4, 5), (6, 6, 6, 6, 6), (1, 1, 2, 3, 4)]:
            holds = unique_holds(combo)
            assert () in holds


# ═══════════════════════════════════════════════════════════════════════════════
# 5. CATEGORY EVs
# ═══════════════════════════════════════════════════════════════════════════════

class TestCategoryEV:
    """CATEGORY_EV gives expected score for a dedicated 3-roll optimal turn."""

    def test_chance_ev_range(self):
        """Chance EV should be ~21-22 (always scores, high baseline from rerolling low dice)."""
        assert 20.0 < CATEGORY_EV[Category.CHANCE] < 23.0

    def test_yahtzee_ev_low(self):
        """Yahtzee EV < 5 (very rare to achieve even with optimal play)."""
        assert CATEGORY_EV[Category.YAHTZEE] < 5.0

    def test_all_categories_positive(self):
        """Every category has EV > 0."""
        for cat in Category:
            assert CATEGORY_EV[cat] > 0, f"{cat} has non-positive EV"

    def test_large_straight_ev_reasonable(self):
        """Large Straight EV should be in 5-15 range."""
        assert 5.0 < CATEGORY_EV[Category.LARGE_STRAIGHT] < 15.0
