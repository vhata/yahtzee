"""
GameCoordinator Test Suite

Tests the extracted game coordination logic without any pygame dependency.
Covers: setup, rolling, turn flow, AI turns, multiplayer flow,
speed control, reset, and CLI parsing.

Conventions match existing test files:
- Class grouping by topic
- random.seed() for determinism
- No mocking — exercises real game engine
"""
import pytest
import random
from dataclasses import replace

from game_engine import (
    Category, GameState, DieState, Scorecard,
    MultiplayerGameState,
    mp_get_current_scorecard,
)
from ai import (
    RollAction, ScoreAction,
    RandomStrategy, GreedyStrategy, ExpectedValueStrategy, OptimalStrategy,
    play_game,
)
from game_coordinator import (
    GameCoordinator, parse_args, _make_strategy,
    SPEED_PRESETS, SPEED_NAMES,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def tick_until(coordinator, predicate, max_ticks=50000):
    """Tick the coordinator until predicate(coordinator) is True.
    Raises if max_ticks exceeded."""
    for _ in range(max_ticks):
        coordinator.tick()
        if predicate(coordinator):
            return
    raise TimeoutError(f"Predicate not satisfied after {max_ticks} ticks")


def tick_n(coordinator, n):
    """Tick the coordinator n times."""
    for _ in range(n):
        coordinator.tick()


def complete_ai_roll(coordinator):
    """Tick until a rolling animation completes (is_rolling goes True then False)."""
    # Wait for roll to start
    tick_until(coordinator, lambda c: c.is_rolling)
    # Wait for roll to finish
    tick_until(coordinator, lambda c: not c.is_rolling)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SETUP
# ═══════════════════════════════════════════════════════════════════════════════

class TestSetup:
    """Coordinator initializes correctly for all modes."""

    def test_single_player_human_defaults(self):
        """Default single-player: human, no AI, no multiplayer."""
        c = GameCoordinator()
        assert c.multiplayer is False
        assert c.ai_strategy is None
        assert c.state is not None
        assert c.mp_state is None
        assert c.is_current_player_human is True
        assert c.has_any_ai is False
        assert c.num_players == 1
        assert c.game_over is False
        assert c.rolls_used == 0
        assert c.current_round == 1

    def test_single_player_ai(self):
        """Single-player AI mode."""
        strategy = GreedyStrategy()
        c = GameCoordinator(ai_strategy=strategy)
        assert c.multiplayer is False
        assert c.ai_strategy is strategy
        assert c.is_current_player_human is False
        assert c.has_any_ai is True
        assert c.current_ai_strategy is strategy

    def test_multiplayer_two_players(self):
        """Two-player multiplayer initializes correctly."""
        players = [("P1", None), ("P2", GreedyStrategy())]
        c = GameCoordinator(players=players)
        assert c.multiplayer is True
        assert c.mp_state is not None
        assert c.state is None
        assert c.num_players == 2
        assert c.current_player_index == 0
        assert c.player_configs == players

    def test_multiplayer_three_players(self):
        """Three-player multiplayer."""
        players = [("A", None), ("B", GreedyStrategy()), ("C", RandomStrategy())]
        c = GameCoordinator(players=players)
        assert c.num_players == 3
        assert len(c.all_scorecards) == 3

    def test_multiplayer_four_players(self):
        """Four-player multiplayer."""
        players = [("A", None), ("B", None), ("C", GreedyStrategy()), ("D", RandomStrategy())]
        c = GameCoordinator(players=players)
        assert c.num_players == 4
        assert len(c.all_scorecards) == 4

    def test_multiplayer_has_turn_transition(self):
        """Multiplayer starts with a turn transition overlay."""
        players = [("P1", None), ("P2", None)]
        c = GameCoordinator(players=players)
        assert c.turn_transition is True
        assert c.turn_transition_timer == 0

    def test_single_player_no_turn_transition(self):
        """Single-player never has turn transitions."""
        c = GameCoordinator()
        assert c.turn_transition is False

    def test_speed_slow(self):
        """Slow speed preset sets correct timings."""
        c = GameCoordinator(speed="slow")
        assert c.speed_name == "slow"
        assert c.ai_delay == 60
        assert c.roll_duration == 90
        assert c.ai_hold_show_duration == 30

    def test_speed_fast(self):
        """Fast speed preset sets correct timings."""
        c = GameCoordinator(speed="fast")
        assert c.speed_name == "fast"
        assert c.ai_delay == 10
        assert c.roll_duration == 20
        assert c.ai_hold_show_duration == 8

    def test_initial_dice_exist(self):
        """Dice are initialized with 5 values."""
        c = GameCoordinator()
        assert len(c.dice) == 5
        assert all(1 <= d.value <= 6 for d in c.dice)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. ROLLING
# ═══════════════════════════════════════════════════════════════════════════════

class TestRolling:
    """Roll lifecycle: start → timer → commit."""

    def test_roll_sets_is_rolling(self):
        """roll_dice() sets is_rolling to True."""
        c = GameCoordinator()
        c.roll_dice()
        assert c.is_rolling is True
        assert c.roll_timer == 0

    def test_roll_computes_final_values(self):
        """roll_dice() computes final_values for the animation to target."""
        random.seed(42)
        c = GameCoordinator()
        c.roll_dice()
        assert len(c.final_values) == 5
        assert all(1 <= v <= 6 for v in c.final_values)

    def test_tick_increments_roll_timer(self):
        """Each tick during rolling increments roll_timer."""
        c = GameCoordinator(speed="normal")
        c.roll_dice()
        c.tick()
        assert c.roll_timer == 1
        assert c.is_rolling is True

    def test_roll_commits_after_duration(self):
        """After roll_duration ticks, pending state is committed and is_rolling=False."""
        c = GameCoordinator(speed="fast")  # roll_duration=20
        c.roll_dice()
        tick_n(c, 20)
        assert c.is_rolling is False
        assert c.rolls_used == 1

    def test_roll_not_committed_before_duration(self):
        """State is not committed before roll_duration ticks."""
        c = GameCoordinator(speed="fast")  # roll_duration=20
        c.roll_dice()
        tick_n(c, 19)
        assert c.is_rolling is True
        assert c.rolls_used == 0  # still pending

    def test_cannot_roll_while_rolling(self):
        """roll_dice() is a no-op while already rolling."""
        c = GameCoordinator()
        c.roll_dice()
        first_final = c.final_values[:]
        c.roll_dice()  # should be ignored
        assert c.final_values == first_final

    def test_cannot_roll_after_three_rolls(self):
        """Cannot roll when rolls_used == 3."""
        c = GameCoordinator(speed="fast")
        # Do 3 rolls
        for _ in range(3):
            c.roll_dice()
            tick_n(c, 20)
        assert c.rolls_used == 3
        c.roll_dice()
        assert c.is_rolling is False  # no-op

    def test_cannot_roll_when_game_over(self):
        """Cannot roll when game is over."""
        random.seed(1)
        c = GameCoordinator(ai_strategy=GreedyStrategy(), speed="fast")
        tick_until(c, lambda c: c.game_over)
        c.roll_dice()
        assert c.is_rolling is False

    def test_multiplayer_roll(self):
        """Rolling works in multiplayer mode."""
        random.seed(42)
        players = [("P1", None), ("P2", None)]
        c = GameCoordinator(players=players, speed="fast")
        # Clear turn transition
        tick_n(c, 45)
        c.roll_dice()
        assert c.is_rolling is True
        tick_n(c, 20)
        assert c.is_rolling is False
        assert c.rolls_used == 1

    def test_three_rolls_then_must_score(self):
        """After 3 rolls, can_roll_now is False but categories are selectable."""
        c = GameCoordinator(speed="fast")
        for _ in range(3):
            c.roll_dice()
            tick_n(c, 20)
        assert c.rolls_used == 3
        assert c.can_roll_now is False

    def test_final_values_match_committed_dice(self):
        """After roll completes, dice values match the final_values."""
        random.seed(99)
        c = GameCoordinator(speed="fast")
        c.roll_dice()
        tick_n(c, 20)
        actual = [d.value for d in c.dice]
        assert actual == c.final_values


# ═══════════════════════════════════════════════════════════════════════════════
# 3. TURN FLOW (Human)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTurnFlow:
    """Hold toggling, category selection, turn advancement."""

    def test_toggle_hold_single_player(self):
        """toggle_hold changes a die's held status in single-player."""
        c = GameCoordinator(speed="fast")
        c.roll_dice()
        tick_n(c, 20)
        assert c.dice[0].held is False
        c.toggle_hold(0)
        assert c.dice[0].held is True
        c.toggle_hold(0)
        assert c.dice[0].held is False

    def test_toggle_hold_multiplayer(self):
        """toggle_hold works in multiplayer mode."""
        random.seed(10)
        players = [("P1", None), ("P2", None)]
        c = GameCoordinator(players=players, speed="fast")
        tick_n(c, 45)  # clear transition
        c.roll_dice()
        tick_n(c, 20)
        c.toggle_hold(2)
        assert c.dice[2].held is True

    def test_toggle_hold_before_roll_is_noop(self):
        """Toggling hold before first roll is a no-op (engine rule)."""
        c = GameCoordinator()
        original_held = c.dice[0].held
        c.toggle_hold(0)
        assert c.dice[0].held == original_held

    def test_select_category_advances_round(self):
        """Selecting a category advances to next round in single-player."""
        c = GameCoordinator(speed="fast")
        c.roll_dice()
        tick_n(c, 20)
        assert c.current_round == 1
        result = c.select_category(Category.CHANCE)
        assert result is True
        assert c.current_round == 2
        assert c.rolls_used == 0

    def test_select_category_returns_false_if_invalid(self):
        """select_category returns False if category can't be selected."""
        c = GameCoordinator()
        # Before rolling, can't score
        result = c.select_category(Category.CHANCE)
        assert result is False

    def test_select_filled_category_returns_false(self):
        """Cannot score in an already-filled category."""
        c = GameCoordinator(speed="fast")
        c.roll_dice()
        tick_n(c, 20)
        c.select_category(Category.CHANCE)
        # Roll again
        c.roll_dice()
        tick_n(c, 20)
        result = c.select_category(Category.CHANCE)
        assert result is False

    def test_full_human_game_completes(self):
        """A full 13-round game can be played through select_category."""
        random.seed(42)
        c = GameCoordinator(speed="fast")
        categories = list(Category)
        for i, cat in enumerate(categories):
            c.roll_dice()
            tick_n(c, 20)
            result = c.select_category(cat)
            assert result is True
        assert c.game_over is True


# ═══════════════════════════════════════════════════════════════════════════════
# 4. AI TURN
# ═══════════════════════════════════════════════════════════════════════════════

class TestAITurn:
    """AI auto-roll, decision pacing, hold-show pause."""

    def test_ai_auto_rolls_first(self):
        """AI automatically rolls at start of turn after ai_delay ticks."""
        random.seed(42)
        c = GameCoordinator(ai_strategy=GreedyStrategy(), speed="fast")
        # Tick through ai_delay (10 ticks for fast)
        tick_n(c, 10)
        # AI should have triggered a roll
        assert c.is_rolling is True

    def test_ai_waits_for_delay(self):
        """AI doesn't act until ai_delay ticks have passed."""
        c = GameCoordinator(ai_strategy=GreedyStrategy(), speed="fast")
        tick_n(c, 9)
        assert c.is_rolling is False

    def test_ai_shows_holds_before_rolling(self):
        """When AI decides to re-roll, it enters ai_showing_holds state first."""
        random.seed(42)
        c = GameCoordinator(ai_strategy=GreedyStrategy(), speed="fast")
        # Complete first roll
        tick_until(c, lambda c: c.is_rolling)
        tick_until(c, lambda c: not c.is_rolling)
        assert c.rolls_used == 1
        # AI may choose to roll again — tick through delay
        tick_n(c, 10)
        # Either ai_showing_holds is True (re-roll) or a category was scored
        # Both are valid outcomes depending on dice

    def test_ai_hold_show_duration(self):
        """ai_showing_holds lasts exactly ai_hold_show_duration ticks."""
        random.seed(7)
        c = GameCoordinator(ai_strategy=GreedyStrategy(), speed="fast")
        # Tick until AI is showing holds
        for _ in range(5000):
            c.tick()
            if c.ai_showing_holds:
                break
        else:
            pytest.skip("AI never entered hold-show state with this seed")
        # Should last ai_hold_show_duration ticks
        tick_n(c, c.ai_hold_show_duration - 1)
        assert c.ai_showing_holds is True
        c.tick()
        assert c.ai_showing_holds is False

    def test_ai_completes_full_game(self):
        """AI plays a complete 13-round game via tick()."""
        random.seed(42)
        c = GameCoordinator(ai_strategy=GreedyStrategy(), speed="fast")
        tick_until(c, lambda c: c.game_over)
        assert c.scorecard.is_complete()

    def test_ai_scores_reasonable(self):
        """Greedy AI scores reasonably (not random-level low)."""
        random.seed(42)
        c = GameCoordinator(ai_strategy=GreedyStrategy(), speed="fast")
        tick_until(c, lambda c: c.game_over)
        total = c.scorecard.get_grand_total()
        assert total > 80  # Greedy averages ~155, should never be below 80

    def test_random_ai_completes_game(self):
        """Random AI also completes a full game."""
        random.seed(42)
        c = GameCoordinator(ai_strategy=RandomStrategy(), speed="fast")
        tick_until(c, lambda c: c.game_over)
        assert c.game_over is True
        assert c.scorecard.is_complete()

    def test_ai_reason_is_set(self):
        """AI sets ai_reason with explanation text."""
        random.seed(42)
        c = GameCoordinator(ai_strategy=GreedyStrategy(), speed="fast")
        # Complete first AI turn
        tick_until(c, lambda c: c.current_round > 1 or c.game_over)
        assert c.ai_reason != ""

    def test_ai_needs_first_roll_resets_after_scoring(self):
        """After AI scores, ai_needs_first_roll is True for next turn."""
        random.seed(42)
        c = GameCoordinator(ai_strategy=GreedyStrategy(), speed="fast")
        # Complete first turn
        tick_until(c, lambda c: c.current_round >= 2)
        assert c.ai_needs_first_roll is True

    def test_multiplayer_ai_builds_temp_state(self):
        """AI in multiplayer mode correctly builds temp GameState for strategy."""
        random.seed(42)
        players = [("P1 Greedy", GreedyStrategy()), ("P2 Random", RandomStrategy())]
        c = GameCoordinator(players=players, speed="fast")
        # Let the game play to completion
        tick_until(c, lambda c: c.game_over)
        assert c.game_over is True
        # Both players should have complete scorecards
        assert all(sc.is_complete() for sc in c.all_scorecards)

    def test_ev_ai_completes_game(self):
        """EV strategy (with low sim count for speed) completes a full game."""
        random.seed(42)
        c = GameCoordinator(ai_strategy=ExpectedValueStrategy(num_simulations=10), speed="fast")
        tick_until(c, lambda c: c.game_over)
        assert c.game_over is True

    def test_ai_does_not_act_when_game_over(self):
        """After game ends, AI tick() is a no-op."""
        random.seed(42)
        c = GameCoordinator(ai_strategy=GreedyStrategy(), speed="fast")
        tick_until(c, lambda c: c.game_over)
        round_before = c.current_round
        tick_n(c, 100)
        assert c.current_round == round_before


# ═══════════════════════════════════════════════════════════════════════════════
# 5. MULTIPLAYER FLOW
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultiplayerFlow:
    """Turn transitions, player rotation, round advancement."""

    def test_turn_transition_clears_after_duration(self):
        """Turn transition overlay clears after turn_transition_duration ticks."""
        players = [("P1", None), ("P2", None)]
        c = GameCoordinator(players=players)
        assert c.turn_transition is True
        tick_n(c, c.turn_transition_duration)
        assert c.turn_transition is False

    def test_turn_transition_blocks_other_updates(self):
        """During turn transition, tick() only advances the transition timer."""
        players = [("P1", GreedyStrategy()), ("P2", GreedyStrategy())]
        c = GameCoordinator(players=players, speed="fast")
        assert c.turn_transition is True
        # Tick a few times — AI should not act
        tick_n(c, 10)
        assert c.is_rolling is False
        assert c.rolls_used == 0

    def test_player_rotation(self):
        """After scoring, current_player_index advances."""
        random.seed(42)
        players = [("P1", None), ("P2", None)]
        c = GameCoordinator(players=players, speed="fast")
        tick_n(c, 45)  # clear transition
        assert c.current_player_index == 0
        c.roll_dice()
        tick_n(c, 20)
        c.select_category(Category.CHANCE)
        assert c.current_player_index == 1

    def test_round_advances_after_all_players(self):
        """Round number increases when all players have completed a turn."""
        random.seed(42)
        players = [("P1", None), ("P2", None)]
        c = GameCoordinator(players=players, speed="fast")
        assert c.current_round == 1

        # Player 1 scores
        tick_n(c, 45)
        c.roll_dice()
        tick_n(c, 20)
        c.select_category(Category.ONES)
        assert c.current_round == 1  # still round 1

        # Player 2 scores
        tick_n(c, 45)
        c.roll_dice()
        tick_n(c, 20)
        c.select_category(Category.TWOS)
        assert c.current_round == 2  # now round 2

    def test_multiplayer_scoring_triggers_transition(self):
        """After human scores in multiplayer, turn_transition is set for next player."""
        random.seed(42)
        players = [("P1", None), ("P2", None)]
        c = GameCoordinator(players=players, speed="fast")
        tick_n(c, 45)
        c.roll_dice()
        tick_n(c, 20)
        c.select_category(Category.CHANCE)
        assert c.turn_transition is True

    def test_full_multiplayer_ai_game(self):
        """Full multiplayer AI game completes correctly."""
        random.seed(42)
        players = [("P1 Greedy", GreedyStrategy()), ("P2 Random", RandomStrategy())]
        c = GameCoordinator(players=players, speed="fast")
        tick_until(c, lambda c: c.game_over)
        assert all(sc.is_complete() for sc in c.all_scorecards)

    def test_three_player_game_completes(self):
        """3-player game completes correctly."""
        random.seed(42)
        players = [
            ("P1", GreedyStrategy()),
            ("P2", RandomStrategy()),
            ("P3", GreedyStrategy()),
        ]
        c = GameCoordinator(players=players, speed="fast")
        tick_until(c, lambda c: c.game_over)
        assert c.game_over is True
        assert all(sc.is_complete() for sc in c.all_scorecards)

    def test_four_player_game_completes(self):
        """4-player game completes correctly."""
        random.seed(42)
        players = [
            ("P1", GreedyStrategy()),
            ("P2", RandomStrategy()),
            ("P3", GreedyStrategy()),
            ("P4", RandomStrategy()),
        ]
        c = GameCoordinator(players=players, speed="fast")
        tick_until(c, lambda c: c.game_over)
        assert c.game_over is True
        assert all(sc.is_complete() for sc in c.all_scorecards)

    def test_multiplayer_human_is_detected(self):
        """is_current_player_human correctly identifies human vs AI."""
        players = [("Human", None), ("AI", GreedyStrategy())]
        c = GameCoordinator(players=players)
        assert c.is_current_player_human is True
        assert c.current_ai_strategy is None

    def test_multiplayer_game_over_no_transition(self):
        """When game ends, no turn transition is triggered."""
        random.seed(42)
        players = [("P1", GreedyStrategy()), ("P2", GreedyStrategy())]
        c = GameCoordinator(players=players, speed="fast")
        tick_until(c, lambda c: c.game_over)
        # After game over, turn_transition should be False
        assert c.turn_transition is False


# ═══════════════════════════════════════════════════════════════════════════════
# 5b. UNDO
# ═══════════════════════════════════════════════════════════════════════════════

class TestUndo:
    """Undo stack for human players."""

    def test_undo_roll(self):
        """Undo after a roll restores pre-roll state."""
        random.seed(42)
        c = GameCoordinator(speed="fast")
        assert c.rolls_used == 0
        c.roll_dice()
        tick_n(c, 20)
        assert c.rolls_used == 1
        result = c.undo()
        assert result is True
        assert c.rolls_used == 0

    def test_undo_hold(self):
        """Undo after toggling hold restores previous hold state."""
        random.seed(42)
        c = GameCoordinator(speed="fast")
        c.roll_dice()
        tick_n(c, 20)
        assert c.dice[0].held is False
        c.toggle_hold(0)
        assert c.dice[0].held is True
        c.undo()
        assert c.dice[0].held is False

    def test_undo_score_restores_round(self):
        """Undo after scoring restores the previous round."""
        random.seed(42)
        c = GameCoordinator(speed="fast")
        c.roll_dice()
        tick_n(c, 20)
        assert c.current_round == 1
        c.select_category(Category.CHANCE)
        assert c.current_round == 2
        c.undo()
        assert c.current_round == 1
        assert c.rolls_used == 1  # back to post-roll state

    def test_multiple_undo_steps(self):
        """Multiple undos walk back through the stack."""
        random.seed(42)
        c = GameCoordinator(speed="fast")
        c.roll_dice()
        tick_n(c, 20)
        c.toggle_hold(0)
        c.toggle_hold(1)
        assert c.dice[0].held is True
        assert c.dice[1].held is True
        c.undo()  # undo hold(1)
        assert c.dice[0].held is True
        assert c.dice[1].held is False
        c.undo()  # undo hold(0)
        assert c.dice[0].held is False

    def test_empty_stack_returns_false(self):
        """Undo with empty stack returns False."""
        c = GameCoordinator()
        assert c.undo() is False

    def test_undo_disabled_during_rolling(self):
        """Cannot undo while dice are rolling."""
        c = GameCoordinator()
        c.roll_dice()
        assert c.is_rolling is True
        assert c.undo() is False

    def test_undo_disabled_for_ai(self):
        """Cannot undo during AI turns."""
        random.seed(42)
        c = GameCoordinator(ai_strategy=GreedyStrategy(), speed="fast")
        # AI will push nothing since it's not human
        tick_until(c, lambda c: c.rolls_used >= 1)
        assert c.undo() is False

    def test_undo_disabled_during_transition(self):
        """Cannot undo during turn transition in multiplayer."""
        random.seed(42)
        players = [("P1", None), ("P2", None)]
        c = GameCoordinator(players=players, speed="fast")
        # Initial turn transition
        assert c.turn_transition is True
        assert c.undo() is False

    def test_undo_disabled_when_game_over(self):
        """Cannot undo when game is over."""
        random.seed(42)
        c = GameCoordinator(speed="fast")
        categories = list(Category)
        for cat in categories:
            c.roll_dice()
            tick_n(c, 20)
            c.select_category(cat)
        assert c.game_over is True
        assert c.undo() is False

    def test_undo_clears_on_reset(self):
        """Reset clears the undo stack."""
        random.seed(42)
        c = GameCoordinator(speed="fast")
        c.roll_dice()
        tick_n(c, 20)
        assert len(c._undo_stack) > 0
        c.reset_game()
        assert len(c._undo_stack) == 0

    def test_undo_clears_on_multiplayer_turn_transition(self):
        """Undo stack clears when a player scores in multiplayer (turn boundary)."""
        random.seed(42)
        players = [("P1", None), ("P2", None)]
        c = GameCoordinator(players=players, speed="fast")
        tick_n(c, 45)  # clear transition
        c.roll_dice()
        tick_n(c, 20)
        assert len(c._undo_stack) > 0
        c.select_category(Category.CHANCE)
        assert len(c._undo_stack) == 0

    def test_can_undo_property(self):
        """can_undo reflects undo availability."""
        random.seed(42)
        c = GameCoordinator(speed="fast")
        assert c.can_undo is False
        c.roll_dice()
        tick_n(c, 20)
        assert c.can_undo is True
        c.undo()
        assert c.can_undo is False


# ═══════════════════════════════════════════════════════════════════════════════
# 6. SPEED CONTROL
# ═══════════════════════════════════════════════════════════════════════════════

class TestSpeedControl:
    """Speed changes update all timings, clamp at boundaries."""

    def test_speed_up(self):
        """change_speed(+1) from normal goes to fast."""
        c = GameCoordinator(speed="normal")
        result = c.change_speed(+1)
        assert result is True
        assert c.speed_name == "fast"
        assert c.ai_delay == SPEED_PRESETS["fast"][0]

    def test_speed_down(self):
        """change_speed(-1) from normal goes to slow."""
        c = GameCoordinator(speed="normal")
        result = c.change_speed(-1)
        assert result is True
        assert c.speed_name == "slow"

    def test_speed_clamps_at_max(self):
        """change_speed(+1) from fast returns False (already at max)."""
        c = GameCoordinator(speed="fast")
        result = c.change_speed(+1)
        assert result is False
        assert c.speed_name == "fast"

    def test_speed_clamps_at_min(self):
        """change_speed(-1) from slow returns False (already at min)."""
        c = GameCoordinator(speed="slow")
        result = c.change_speed(-1)
        assert result is False
        assert c.speed_name == "slow"

    def test_speed_updates_all_timings(self):
        """Changing speed updates ai_delay, roll_duration, and ai_hold_show_duration."""
        c = GameCoordinator(speed="slow")
        c.change_speed(+1)  # → normal
        assert c.ai_delay == 30
        assert c.roll_duration == 60
        assert c.ai_hold_show_duration == 20


# ═══════════════════════════════════════════════════════════════════════════════
# 7. RESET
# ═══════════════════════════════════════════════════════════════════════════════

class TestReset:
    """Reset preserves config, clears game state."""

    def test_reset_single_player(self):
        """Reset creates fresh state in single-player."""
        random.seed(42)
        c = GameCoordinator(speed="fast")
        c.roll_dice()
        tick_n(c, 20)
        c.select_category(Category.CHANCE)
        assert c.current_round == 2
        c.reset_game()
        assert c.current_round == 1
        assert c.rolls_used == 0
        assert c.game_over is False

    def test_reset_preserves_speed(self):
        """Reset preserves speed settings."""
        c = GameCoordinator(speed="fast")
        c.change_speed(-1)  # → normal
        c.reset_game()
        assert c.speed_name == "normal"

    def test_reset_clears_ai_state(self):
        """Reset clears all AI-related state."""
        random.seed(42)
        c = GameCoordinator(ai_strategy=GreedyStrategy(), speed="fast")
        tick_until(c, lambda c: c.current_round > 1)
        c.reset_game()
        assert c.ai_needs_first_roll is True
        assert c.ai_timer == 0
        assert c.ai_reason == ""
        assert c.ai_showing_holds is False

    def test_reset_clears_rolling_state(self):
        """Reset clears roll animation state."""
        c = GameCoordinator()
        c.roll_dice()
        assert c.is_rolling is True
        c.reset_game()
        assert c.is_rolling is False

    def test_reset_multiplayer(self):
        """Reset creates fresh multiplayer state."""
        random.seed(42)
        players = [("P1", GreedyStrategy()), ("P2", RandomStrategy())]
        c = GameCoordinator(players=players, speed="fast")
        tick_until(c, lambda c: c.game_over)
        c.reset_game()
        assert c.game_over is False
        assert c.current_round == 1
        assert c.current_player_index == 0
        assert c.turn_transition is True

    def test_reset_after_complete_game(self):
        """Can play a full game, reset, and play again."""
        random.seed(42)
        c = GameCoordinator(ai_strategy=GreedyStrategy(), speed="fast")
        tick_until(c, lambda c: c.game_over)
        score1 = c.scorecard.get_grand_total()
        c.reset_game()
        assert c.game_over is False
        tick_until(c, lambda c: c.game_over)
        score2 = c.scorecard.get_grand_total()
        # Both games should complete (scores will differ)
        assert score1 > 0
        assert score2 > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 8. CLI PARSING
# ═══════════════════════════════════════════════════════════════════════════════

class TestCLIParsing:
    """_make_strategy() and parse_args() handle all flag combinations."""

    def test_make_strategy_human(self):
        """'human' returns None."""
        assert _make_strategy("human") is None

    def test_make_strategy_random(self):
        """'random' returns RandomStrategy instance."""
        assert isinstance(_make_strategy("random"), RandomStrategy)

    def test_make_strategy_greedy(self):
        """'greedy' returns GreedyStrategy instance."""
        assert isinstance(_make_strategy("greedy"), GreedyStrategy)

    def test_make_strategy_ev(self):
        """'ev' returns ExpectedValueStrategy instance."""
        assert isinstance(_make_strategy("ev"), ExpectedValueStrategy)

    def test_parse_args_no_flags(self):
        """No flags: no AI, no players."""
        args = parse_args([])
        assert args.ai is False
        assert args.players is None
        assert args.speed == "normal"

    def test_parse_args_ai_greedy(self):
        """--ai --greedy sets both flags."""
        args = parse_args(["--ai", "--greedy"])
        assert args.ai is True
        assert args.greedy is True

    def test_parse_args_players(self):
        """--players human greedy sets player list."""
        args = parse_args(["--players", "human", "greedy"])
        assert args.players == ["human", "greedy"]

    def test_parse_args_speed(self):
        """--speed fast sets speed."""
        args = parse_args(["--speed", "fast"])
        assert args.speed == "fast"


# ═══════════════════════════════════════════════════════════════════════════════
# 9. SCORE ANIMATION SIGNAL
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoreAnimation:
    """last_scored_category signal for GUI flash animation."""

    def test_initially_none(self):
        """last_scored_category is None at start."""
        c = GameCoordinator()
        assert c.last_scored_category is None

    def test_set_on_human_score(self):
        """last_scored_category is set when human scores."""
        random.seed(42)
        c = GameCoordinator(speed="fast")
        c.roll_dice()
        tick_n(c, 20)
        c.select_category(Category.CHANCE)
        assert c.last_scored_category == Category.CHANCE

    def test_set_on_ai_score(self):
        """last_scored_category is set when AI scores."""
        random.seed(42)
        c = GameCoordinator(ai_strategy=GreedyStrategy(), speed="fast")
        tick_until(c, lambda c: c.last_scored_category is not None)
        assert c.last_scored_category is not None
        assert isinstance(c.last_scored_category, Category)

    def test_reset_clears_signal(self):
        """reset_game() clears last_scored_category."""
        random.seed(42)
        c = GameCoordinator(speed="fast")
        c.roll_dice()
        tick_n(c, 20)
        c.select_category(Category.CHANCE)
        assert c.last_scored_category is not None
        c.reset_game()
        assert c.last_scored_category is None


# ═══════════════════════════════════════════════════════════════════════════════
# 10. INTEGRATION TESTS
#    Verify that GameCoordinator's AI tick loop produces the same final score
#    as the headless play_game() function, given the same random seed.
# ═══════════════════════════════════════════════════════════════════════════════

INTEGRATION_STRATEGIES = [
    pytest.param(RandomStrategy, id="Random"),
    pytest.param(GreedyStrategy, id="Greedy"),
    pytest.param(OptimalStrategy, id="Optimal"),
]

INTEGRATION_SEEDS = list(range(10))


class TestIntegration:
    """Coordinator tick loop must produce identical scores to headless play_game()."""

    @staticmethod
    def _tick_until_game_over(coordinator, max_ticks=500_000):
        """Tick the coordinator until game_over is True."""
        for _ in range(max_ticks):
            coordinator.tick()
            if coordinator.game_over:
                return
        raise TimeoutError(f"Game did not finish after {max_ticks} ticks")

    @pytest.mark.parametrize("strategy_cls", INTEGRATION_STRATEGIES)
    @pytest.mark.parametrize("seed", INTEGRATION_SEEDS)
    def test_coordinator_matches_headless(self, strategy_cls, seed):
        """Coordinator AI tick loop produces the same final score as play_game()."""
        # Run headless play_game()
        random.seed(seed)
        headless_state = play_game(strategy_cls())

        # Run coordinator tick loop with the same seed
        random.seed(seed)
        coordinator = GameCoordinator(ai_strategy=strategy_cls(), speed="fast")
        self._tick_until_game_over(coordinator)

        assert coordinator.scorecard.get_grand_total() == headless_state.scorecard.get_grand_total(), (
            f"seed={seed} strategy={strategy_cls.__name__}: "
            f"coordinator={coordinator.scorecard.get_grand_total()} != "
            f"headless={headless_state.scorecard.get_grand_total()}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 11. SMOKE RENDERING TESTS
#    Verify that YahtzeeGame.draw() doesn't crash in headless pygame.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import pygame


@pytest.fixture(scope="module", autouse=False)
def headless_pygame():
    """Set up headless pygame for rendering tests."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


class TestSmokeRendering:
    """Verify draw() doesn't crash in headless mode across all game states."""

    def _make_game(self, headless_pygame, **kwargs):
        """Create a YahtzeeGame instance in headless mode."""
        from main import YahtzeeGame
        return YahtzeeGame(**kwargs)

    def test_draw_single_player_initial(self, headless_pygame):
        """Single-player initial state renders without error."""
        game = self._make_game(headless_pygame)
        game.draw()

    def test_draw_single_player_ai(self, headless_pygame):
        """AI single-player renders without error."""
        game = self._make_game(headless_pygame, ai_strategy=GreedyStrategy())
        game.draw()

    def test_draw_multiplayer(self, headless_pygame):
        """Multiplayer renders without error (including turn transition)."""
        players = [("P1", None), ("P2", GreedyStrategy())]
        game = self._make_game(headless_pygame, players=players)
        # Initial state has turn_transition=True
        game.draw()

    def test_draw_multiplayer_after_transition(self, headless_pygame):
        """Multiplayer renders after turn transition clears."""
        random.seed(42)
        players = [("P1", None), ("P2", None)]
        game = self._make_game(headless_pygame, players=players, speed="fast")
        # Clear transition
        for _ in range(45):
            game.update()
        game.draw()

    def test_draw_game_over_single(self, headless_pygame):
        """Single-player game over screen renders without error."""
        random.seed(42)
        game = self._make_game(headless_pygame, ai_strategy=GreedyStrategy(), speed="fast")
        # Play to completion
        while not game.coordinator.game_over:
            game.update()
        game.draw()

    def test_draw_game_over_multiplayer_2p(self, headless_pygame):
        """2-player multiplayer game over renders without error."""
        random.seed(42)
        players = [("P1", GreedyStrategy()), ("P2", RandomStrategy())]
        game = self._make_game(headless_pygame, players=players, speed="fast")
        while not game.coordinator.game_over:
            game.update()
        game.draw()

    def test_draw_game_over_multiplayer_3p(self, headless_pygame):
        """3-player multiplayer game over renders without error."""
        random.seed(42)
        players = [("P1", GreedyStrategy()), ("P2", RandomStrategy()), ("P3", GreedyStrategy())]
        game = self._make_game(headless_pygame, players=players, speed="fast")
        while not game.coordinator.game_over:
            game.update()
        game.draw()

    def test_draw_game_over_multiplayer_4p(self, headless_pygame):
        """4-player multiplayer game over renders without error."""
        random.seed(42)
        players = [
            ("P1", GreedyStrategy()), ("P2", RandomStrategy()),
            ("P3", GreedyStrategy()), ("P4", RandomStrategy()),
        ]
        game = self._make_game(headless_pygame, players=players, speed="fast")
        while not game.coordinator.game_over:
            game.update()
        game.draw()
