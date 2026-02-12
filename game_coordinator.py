"""
GameCoordinator — All non-pygame game coordination logic.

Owns game state, timers, AI pacing, and the per-frame state machine.
The GUI layer (main.py) delegates to this and only handles rendering + events.
"""
import argparse
import sys

from game_engine import (
    Category, Scorecard, calculate_score,
    GameState, DieState,
    roll_dice as engine_roll_dice,
    toggle_die_hold as engine_toggle_die,
    select_category as engine_select_category,
    can_roll, can_select_category,
    reset_game as engine_reset_game,
    MultiplayerGameState,
    mp_roll_dice, mp_toggle_die_hold, mp_select_category,
    mp_can_roll, mp_can_select_category, mp_get_current_scorecard,
)
from ai import (
    RollAction, ScoreAction,
    RandomStrategy, GreedyStrategy, ExpectedValueStrategy,
)

# Speed presets for AI playback: (ai_delay, roll_duration, hold_show_duration) in frames
SPEED_PRESETS = {
    "slow":   (60, 90, 30),
    "normal": (30, 60, 20),
    "fast":   (10, 20, 8),
}
SPEED_NAMES = ["slow", "normal", "fast"]


class GameCoordinator:
    """Coordinates game state, AI decisions, and turn management without any pygame dependency.

    The GUI reads coordinator properties to decide what to render, and calls
    coordinator action methods in response to user input.
    """

    def __init__(self, ai_strategy=None, speed="normal", players=None):
        """Initialize the coordinator.

        Args:
            ai_strategy: Optional AI strategy instance for single-player AI mode.
            speed: Speed preset name ("slow", "normal", "fast").
            players: Optional list of (name, strategy_or_None) tuples for multiplayer.
                     None means single-player mode.
        """
        # Multiplayer mode
        self.multiplayer = players is not None
        if self.multiplayer:
            self.player_configs = players
            self.mp_state = MultiplayerGameState.create_initial(len(players))
            self.state = None
            self.turn_transition = True
            self.turn_transition_timer = 0
            self.turn_transition_duration = 45
        else:
            self.player_configs = None
            self.mp_state = None
            self.state = GameState.create_initial()
            self.turn_transition = False

        # AI state
        self.ai_strategy = ai_strategy
        self.ai_timer = 0
        self.speed_name = speed
        self.ai_delay, self.roll_duration, self.ai_hold_show_duration = SPEED_PRESETS[self.speed_name]
        self.ai_needs_first_roll = True
        self.ai_reason = ""
        self.ai_showing_holds = False
        self.ai_hold_timer = 0

        # Roll animation lifecycle (coordinator owns timing; GUI owns display randomization)
        self.is_rolling = False
        self.roll_timer = 0
        self.final_values = []
        self._pending_state = None
        self._pending_mp_state = None

    # ── Properties (uniform interface for single/multiplayer) ─────────────

    @property
    def dice(self):
        """Current dice tuple from the active game state."""
        return self.mp_state.dice if self.multiplayer else self.state.dice

    @property
    def rolls_used(self):
        """Current rolls_used from the active game state."""
        return self.mp_state.rolls_used if self.multiplayer else self.state.rolls_used

    @property
    def game_over(self):
        """Whether the game is over."""
        return self.mp_state.game_over if self.multiplayer else self.state.game_over

    @property
    def current_round(self):
        """Current round number (1-13)."""
        return self.mp_state.current_round if self.multiplayer else self.state.current_round

    @property
    def scorecard(self):
        """Current player's scorecard."""
        if self.multiplayer:
            return mp_get_current_scorecard(self.mp_state)
        return self.state.scorecard

    @property
    def is_current_player_human(self):
        """Whether the current player is human."""
        if not self.multiplayer:
            return self.ai_strategy is None
        _, strategy = self.player_configs[self.mp_state.current_player_index]
        return strategy is None

    @property
    def current_ai_strategy(self):
        """Current player's AI strategy (or None if human)."""
        if not self.multiplayer:
            return self.ai_strategy
        _, strategy = self.player_configs[self.mp_state.current_player_index]
        return strategy

    @property
    def has_any_ai(self):
        """Whether any player is AI (for speed control display)."""
        if self.multiplayer:
            return any(s is not None for _, s in self.player_configs)
        return self.ai_strategy is not None

    @property
    def current_player_index(self):
        """Current player index (multiplayer) or 0 (single-player)."""
        if self.multiplayer:
            return self.mp_state.current_player_index
        return 0

    @property
    def all_scorecards(self):
        """Tuple of all scorecards (multiplayer) or single-element tuple (single-player)."""
        if self.multiplayer:
            return self.mp_state.scorecards
        return (self.state.scorecard,)

    @property
    def num_players(self):
        """Number of players."""
        if self.multiplayer:
            return self.mp_state.num_players
        return 1

    @property
    def can_roll_now(self):
        """Whether dice can be rolled right now."""
        if self.is_rolling:
            return False
        if self.multiplayer:
            return mp_can_roll(self.mp_state)
        return can_roll(self.state)

    # ── Action methods (called by GUI on input) ──────────────────────────

    def roll_dice(self):
        """Start a dice roll. Sets is_rolling=True and computes pending state.

        The roll completes after roll_duration ticks (committed during tick()).
        """
        if self.multiplayer:
            if not self.is_rolling and mp_can_roll(self.mp_state):
                self.is_rolling = True
                self.roll_timer = 0
                new_mp_state = mp_roll_dice(self.mp_state)
                self.final_values = [die.value for die in new_mp_state.dice]
                self._pending_mp_state = new_mp_state
        else:
            if not self.is_rolling and can_roll(self.state):
                self.is_rolling = True
                self.roll_timer = 0
                new_state = engine_roll_dice(self.state)
                self.final_values = [die.value for die in new_state.dice]
                self._pending_state = new_state

    def toggle_hold(self, die_index):
        """Toggle hold on a die (for human players)."""
        if self.multiplayer:
            self.mp_state = mp_toggle_die_hold(self.mp_state, die_index)
        else:
            self.state = engine_toggle_die(self.state, die_index)

    def select_category(self, category):
        """Score a category (for human players)."""
        if self.multiplayer:
            if mp_can_select_category(self.mp_state, category):
                self.mp_state = mp_select_category(self.mp_state, category)
                self._on_turn_scored()
                return True
        else:
            if can_select_category(self.state, category):
                self.state = engine_select_category(self.state, category)
                return True
        return False

    def reset_game(self):
        """Reset to start a new game, preserving speed settings."""
        if self.multiplayer:
            self.mp_state = MultiplayerGameState.create_initial(len(self.player_configs))
            self.turn_transition = True
            self.turn_transition_timer = 0
        else:
            self.state = engine_reset_game()
        self.ai_needs_first_roll = True
        self.ai_timer = 0
        self.ai_reason = ""
        self.ai_showing_holds = False
        self.ai_hold_timer = 0
        self.is_rolling = False
        self.roll_timer = 0

    def change_speed(self, direction):
        """Change AI speed. direction=+1 for faster, -1 for slower.

        Returns True if speed actually changed, False if already at limit.
        """
        idx = SPEED_NAMES.index(self.speed_name)
        new_idx = idx + direction
        if 0 <= new_idx < len(SPEED_NAMES):
            self.speed_name = SPEED_NAMES[new_idx]
            self.ai_delay, self.roll_duration, self.ai_hold_show_duration = SPEED_PRESETS[self.speed_name]
            return True
        return False

    # ── Frame update ─────────────────────────────────────────────────────

    def tick(self):
        """Advance one frame of the state machine.

        Handles: turn transitions, roll timer, AI hold-show pause, AI decisions.
        No pygame, no animation display values — purely deterministic game logic.
        """
        # Handle turn transition overlay (multiplayer only)
        if self.turn_transition:
            self.turn_transition_timer += 1
            if self.turn_transition_timer >= self.turn_transition_duration:
                self.turn_transition = False
            return

        # Handle roll timer — commit pending state when animation duration is reached
        if self.is_rolling:
            self.roll_timer += 1
            if self.roll_timer >= self.roll_duration:
                if self.multiplayer:
                    self.mp_state = self._pending_mp_state
                else:
                    self.state = self._pending_state
                self.is_rolling = False
            return

        # AI hold-showing pause — briefly display held dice before rolling
        if self.ai_showing_holds:
            self.ai_hold_timer += 1
            if self.ai_hold_timer >= self.ai_hold_show_duration:
                self.ai_showing_holds = False
                self.roll_dice()
            return

        # AI controller — paces decisions with a timer
        current_strategy = self.current_ai_strategy
        if current_strategy and not self.game_over:
            self.ai_timer += 1
            if self.ai_timer < self.ai_delay:
                return
            self.ai_timer = 0

            # First roll of the turn (mandatory)
            if self.ai_needs_first_roll:
                self.roll_dice()
                self.ai_needs_first_roll = False
                return

            # Build a temporary single-player GameState for the AI strategy
            if self.multiplayer:
                temp_state = GameState(
                    dice=self.mp_state.dice,
                    scorecard=mp_get_current_scorecard(self.mp_state),
                    rolls_used=self.mp_state.rolls_used,
                    current_round=self.mp_state.current_round,
                    game_over=self.mp_state.game_over,
                )
                action = current_strategy.choose_action(temp_state)
            else:
                action = current_strategy.choose_action(self.state)
            self.ai_reason = action.reason

            if isinstance(action, ScoreAction):
                if self.multiplayer:
                    self.mp_state = mp_select_category(self.mp_state, action.category)
                    self._on_turn_scored()
                else:
                    self.state = engine_select_category(self.state, action.category)
                    self.ai_needs_first_roll = True
            elif isinstance(action, RollAction):
                # Apply holds: set each die to match the strategy's request
                if self.multiplayer:
                    for i in range(5):
                        should_hold = i in action.hold
                        is_held = self.mp_state.dice[i].held
                        if should_hold != is_held:
                            self.mp_state = mp_toggle_die_hold(self.mp_state, i)
                else:
                    for i in range(5):
                        should_hold = i in action.hold
                        is_held = self.state.dice[i].held
                        if should_hold != is_held:
                            self.state = engine_toggle_die(self.state, i)
                # Pause to show the held dice before rolling
                self.ai_showing_holds = True
                self.ai_hold_timer = 0

    # ── Internal ─────────────────────────────────────────────────────────

    def _on_turn_scored(self):
        """Called after any player (human or AI) scores in multiplayer.
        Triggers turn transition and resets AI state for the next player."""
        if not self.multiplayer:
            return
        self.ai_needs_first_roll = True
        self.ai_timer = 0
        self.ai_reason = ""
        self.ai_showing_holds = False
        self.ai_hold_timer = 0
        if not self.mp_state.game_over:
            self.turn_transition = True
            self.turn_transition_timer = 0


def _make_strategy(token):
    """Create a strategy instance from a CLI token, or None for 'human'."""
    if token == "human":
        return None
    elif token == "random":
        return RandomStrategy()
    elif token == "greedy":
        return GreedyStrategy()
    elif token == "ev":
        return ExpectedValueStrategy()


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv: Optional list of args (for testing). None uses sys.argv.

    Returns:
        Parsed argparse.Namespace.
    """
    parser = argparse.ArgumentParser(description="Yahtzee Game")
    # Single-player AI mode (backward compatible)
    parser.add_argument("--ai", action="store_true", help="Enable AI player")
    parser.add_argument("--random", action="store_true", help="Use Random strategy (with --ai)")
    parser.add_argument("--greedy", action="store_true", help="Use Greedy strategy (with --ai)")
    parser.add_argument("--ev", action="store_true", help="Use ExpectedValue strategy (with --ai)")
    # Multiplayer mode
    parser.add_argument("--players", nargs="+", choices=["human", "random", "greedy", "ev"],
                        metavar="TYPE",
                        help="Multiplayer: list player types (human, random, greedy, ev)")
    parser.add_argument("--speed", choices=["slow", "normal", "fast"], default="normal",
                        help="AI playback speed (default: normal)")
    return parser.parse_args(argv)
