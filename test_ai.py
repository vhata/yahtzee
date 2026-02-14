"""
AI Strategy Test Suite

Tests:
    1. Legality — parametrized across all strategies: games complete without errors,
       strategies never make illegal moves
    2. Quality — greedy > random, EV > greedy, determinism
"""
import pytest
import random

from game_engine import (
    Category, GameState, DieState, Scorecard,
    roll_dice, can_roll, can_select_category, calculate_score,
)
from ai import (
    RollAction, ScoreAction,
    YahtzeeStrategy, RandomStrategy, GreedyStrategy, ExpectedValueStrategy,
    OptimalStrategy,
    play_turn, play_game,
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def all_strategies():
    """Return instances of all available strategies for parametrized tests."""
    return [RandomStrategy(), GreedyStrategy(), ExpectedValueStrategy(num_simulations=50),
            OptimalStrategy()]


def strategy_ids():
    """Return readable names for parametrize IDs."""
    return ["Random", "Greedy", "EV", "Optimal"]


# ═══════════════════════════════════════════════════════════════════════════════
# 1. LEGALITY TESTS — parametrized across all strategies
# ═══════════════════════════════════════════════════════════════════════════════

class TestLegality:
    """Every strategy must produce legal moves that complete a full game."""

    @pytest.fixture(params=all_strategies(), ids=strategy_ids())
    def strategy(self, request):
        return request.param

    def test_completes_full_game(self, strategy):
        """Strategy plays 13 rounds and game ends properly."""
        random.seed(42)
        state = play_game(strategy)
        assert state.game_over is True
        assert state.scorecard.is_complete()

    def test_never_rolls_when_out_of_rolls(self, strategy):
        """Strategy never returns RollAction when rolls_used == 3."""
        random.seed(99)
        state = GameState.create_initial()

        for _ in range(13):
            # Play turn manually to inspect each decision
            state = roll_dice(state)

            while True:
                action = strategy.choose_action(state)

                if state.rolls_used >= 3:
                    # Must be a ScoreAction
                    assert isinstance(action, ScoreAction), (
                        f"Strategy returned RollAction with rolls_used={state.rolls_used}"
                    )

                if isinstance(action, ScoreAction):
                    assert can_select_category(state, action.category), (
                        f"Strategy tried to score filled category {action.category}"
                    )
                    from game_engine import select_category
                    state = select_category(state, action.category)
                    break

                # RollAction
                assert isinstance(action, RollAction)
                assert can_roll(state), "Strategy tried to roll when not allowed"

                # Apply holds and roll
                from game_engine import toggle_die_hold
                for i in range(5):
                    should_hold = i in action.hold
                    is_held = state.dice[i].held
                    if should_hold != is_held:
                        state = toggle_die_hold(state, i)
                state = roll_dice(state)

        assert state.game_over is True

    def test_never_picks_filled_category(self, strategy):
        """Strategy never returns a ScoreAction for an already-filled category."""
        random.seed(77)
        state = GameState.create_initial()
        filled_cats = set()

        for _ in range(13):
            state = roll_dice(state)

            while True:
                action = strategy.choose_action(state)

                if isinstance(action, ScoreAction):
                    assert action.category not in filled_cats, (
                        f"Strategy tried to score already-filled {action.category}"
                    )
                    assert not state.scorecard.is_filled(action.category)
                    filled_cats.add(action.category)
                    from game_engine import select_category
                    state = select_category(state, action.category)
                    break

                # Apply holds and roll
                from game_engine import toggle_die_hold
                for i in range(5):
                    should_hold = i in action.hold
                    is_held = state.dice[i].held
                    if should_hold != is_held:
                        state = toggle_die_hold(state, i)
                state = roll_dice(state)

    def test_hold_indices_in_range(self, strategy):
        """All hold indices in RollAction are between 0 and 4."""
        random.seed(55)
        state = GameState.create_initial()

        for _ in range(13):
            state = roll_dice(state)

            while True:
                action = strategy.choose_action(state)

                if isinstance(action, RollAction):
                    for idx in action.hold:
                        assert 0 <= idx <= 4, f"Hold index {idx} out of range"

                if isinstance(action, ScoreAction):
                    from game_engine import select_category
                    state = select_category(state, action.category)
                    break

                from game_engine import toggle_die_hold
                for i in range(5):
                    should_hold = i in action.hold
                    is_held = state.dice[i].held
                    if should_hold != is_held:
                        state = toggle_die_hold(state, i)
                state = roll_dice(state)

    def test_stress_100_games(self, strategy):
        """Run 100 games with different seeds — none should error."""
        for seed in range(100):
            random.seed(seed)
            state = play_game(strategy)
            assert state.game_over is True
            assert state.scorecard.is_complete()
            assert state.scorecard.get_grand_total() >= 0


# ═══════════════════════════════════════════════════════════════════════════════
# 2. QUALITY TESTS — strategy ranking and determinism
# ═══════════════════════════════════════════════════════════════════════════════

def _average_score(strategy, num_games=50, start_seed=0):
    """Play num_games and return the average grand total."""
    scores = []
    for seed in range(start_seed, start_seed + num_games):
        random.seed(seed)
        state = play_game(strategy)
        scores.append(state.scorecard.get_grand_total())
    return sum(scores) / len(scores)


class TestQuality:
    """Verify that more sophisticated strategies score higher on average."""

    def test_greedy_beats_random(self):
        """Greedy should average significantly higher than Random over 50 games."""
        random_avg = _average_score(RandomStrategy(), num_games=50)
        greedy_avg = _average_score(GreedyStrategy(), num_games=50)
        assert greedy_avg > random_avg + 30, (
            f"Greedy ({greedy_avg:.1f}) should beat Random ({random_avg:.1f}) by >30"
        )

    def test_ev_beats_greedy(self):
        """ExpectedValue should average higher than Greedy over 50 games."""
        greedy_avg = _average_score(GreedyStrategy(), num_games=50)
        ev_avg = _average_score(ExpectedValueStrategy(num_simulations=50), num_games=50)
        assert ev_avg > greedy_avg, (
            f"EV ({ev_avg:.1f}) should beat Greedy ({greedy_avg:.1f})"
        )

    def test_determinism_same_seed_same_score(self):
        """Same seed should produce the exact same final score for each strategy."""
        for strategy in [RandomStrategy(), GreedyStrategy(),
                         ExpectedValueStrategy(num_simulations=50)]:
            random.seed(12345)
            score1 = play_game(strategy).scorecard.get_grand_total()
            random.seed(12345)
            score2 = play_game(strategy).scorecard.get_grand_total()
            assert score1 == score2, (
                f"{strategy.__class__.__name__} not deterministic: {score1} != {score2}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. OPTIMAL STRATEGY TESTS — quality and behavior
# ═══════════════════════════════════════════════════════════════════════════════

class TestOptimalStrategy:
    """Tests specific to the OptimalStrategy."""

    def test_optimal_beats_ev(self):
        """Optimal should average higher than EV(n=50) over 50 games."""
        ev_avg = _average_score(ExpectedValueStrategy(num_simulations=50), num_games=50)
        optimal_avg = _average_score(OptimalStrategy(), num_games=50)
        assert optimal_avg > ev_avg, (
            f"Optimal ({optimal_avg:.1f}) should beat EV ({ev_avg:.1f})"
        )

    def test_optimal_deterministic(self):
        """Same seed → same score (no randomness in strategy)."""
        strategy = OptimalStrategy()
        random.seed(12345)
        score1 = play_game(strategy).scorecard.get_grand_total()
        random.seed(12345)
        score2 = play_game(strategy).scorecard.get_grand_total()
        assert score1 == score2

    def test_optimal_prefers_yahtzee(self):
        """With dice (3,3,3,3,3) and Yahtzee available, scores Yahtzee."""
        dice = tuple(DieState(value=3) for _ in range(5))
        state = GameState(
            dice=dice, scorecard=Scorecard(), rolls_used=1,
            current_round=1, game_over=False,
        )
        strategy = OptimalStrategy()
        action = strategy.choose_action(state)
        assert isinstance(action, ScoreAction)
        assert action.category == Category.YAHTZEE

    def test_optimal_holds_four_of_kind(self):
        """With dice (4,4,4,4,2) and rolls left, holds the four 4s."""
        dice = (DieState(value=4), DieState(value=4), DieState(value=4),
                DieState(value=4), DieState(value=2))
        state = GameState(
            dice=dice, scorecard=Scorecard(), rolls_used=1,
            current_round=1, game_over=False,
        )
        strategy = OptimalStrategy()
        action = strategy.choose_action(state)
        assert isinstance(action, RollAction)
        # Should hold the four 4s (indices 0,1,2,3) and reroll the 2 (index 4)
        held_values = sorted(dice[i].value for i in action.hold)
        assert held_values == [4, 4, 4, 4]

    def test_optimal_takes_large_straight(self):
        """With (1,2,3,4,5) and Large Straight available, scores it."""
        dice = tuple(DieState(value=v) for v in [1, 2, 3, 4, 5])
        state = GameState(
            dice=dice, scorecard=Scorecard(), rolls_used=1,
            current_round=1, game_over=False,
        )
        strategy = OptimalStrategy()
        action = strategy.choose_action(state)
        assert isinstance(action, ScoreAction)
        assert action.category == Category.LARGE_STRAIGHT
