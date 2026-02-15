"""FrontendAdapter — Shared UI state management for all Yahtzee frontends.

Owns overlay state, zero-score confirmation, keyboard category navigation,
score flash animation, settings persistence, score saving, and history filters.
Pure Python — no pygame or other frontend dependency.

Each frontend (pygame, TUI, web) creates a FrontendAdapter wrapping a
GameCoordinator and delegates UI-state logic here, keeping only rendering
and input translation frontend-specific.
"""

from abc import ABC, abstractmethod

from game_engine import Category, calculate_score_in_context
from score_history import (
    record_score, record_multiplayer_scores,
    get_high_scores, get_recent_scores_filtered,
)
from settings import load_settings, save_settings


# ── Shared constants (moved from main.py) ────────────────────────────────────

OPTIMAL_EXPECTED_TOTAL = 223.0

CATEGORY_ORDER = [
    Category.ONES, Category.TWOS, Category.THREES,
    Category.FOURS, Category.FIVES, Category.SIXES,
    Category.THREE_OF_KIND, Category.FOUR_OF_KIND,
    Category.FULL_HOUSE, Category.SMALL_STRAIGHT,
    Category.LARGE_STRAIGHT, Category.YAHTZEE, Category.CHANCE,
]

CATEGORY_TOOLTIPS = {
    Category.ONES: "Sum of all dice showing 1",
    Category.TWOS: "Sum of all dice showing 2",
    Category.THREES: "Sum of all dice showing 3",
    Category.FOURS: "Sum of all dice showing 4",
    Category.FIVES: "Sum of all dice showing 5",
    Category.SIXES: "Sum of all dice showing 6",
    Category.THREE_OF_KIND: "3 of the same, score = sum of all dice",
    Category.FOUR_OF_KIND: "4 of the same, score = sum of all dice",
    Category.FULL_HOUSE: "3 of one + 2 of another = 25",
    Category.SMALL_STRAIGHT: "4 consecutive dice = 30",
    Category.LARGE_STRAIGHT: "5 consecutive dice = 40",
    Category.YAHTZEE: "All 5 dice the same = 50",
    Category.CHANCE: "Sum of all dice, no pattern needed",
}


# ── Sound interface ───────────────────────────────────────────────────────────

class SoundInterface(ABC):
    """Abstract sound interface — each frontend provides its own implementation."""

    @abstractmethod
    def play_roll(self): ...

    @abstractmethod
    def play_click(self): ...

    @abstractmethod
    def play_score(self): ...

    @abstractmethod
    def play_fanfare(self): ...

    @abstractmethod
    def toggle(self): ...

    @property
    @abstractmethod
    def enabled(self) -> bool: ...


class NullSound(SoundInterface):
    """No-op sound for frontends without audio (TUI, server-side web)."""

    def __init__(self):
        self._enabled = False

    def play_roll(self): pass
    def play_click(self): pass
    def play_score(self): pass
    def play_fanfare(self): pass

    def toggle(self):
        self._enabled = not self._enabled
        return self._enabled

    @property
    def enabled(self):
        return self._enabled


# ── Frontend Adapter ──────────────────────────────────────────────────────────

class FrontendAdapter:
    """Shared UI state management for all Yahtzee frontends.

    Wraps a GameCoordinator and manages overlay state, zero-confirm flow,
    keyboard navigation, score flash, settings, and score saving.
    """

    def __init__(self, coordinator, sound=None):
        self.coordinator = coordinator
        self.sound = sound or NullSound()

        # Overlay state
        self.showing_help = False
        self.showing_history = False
        self.showing_replay = False

        # Zero-score confirmation
        self.confirm_zero_category = None

        # Keyboard category navigation
        self.kb_selected_index = None
        self.hovered_category = None

        # Score flash (frontend-agnostic progress 0.0-1.0)
        self.score_flash_category = None
        self.score_flash_timer = 0
        self.score_flash_duration = 30  # frames (0.5s at 60 FPS)

        # Settings
        self.colorblind_mode = False
        self.dark_mode = False

        # History filters
        self.history_filter_player = "all"
        self.history_filter_mode = "all"
        self._player_filter_options = ["all", "human", "greedy", "ev", "optimal"]
        self._mode_filter_options = ["all", "single", "multiplayer"]

        # One-shot flags for game-over handling
        self._game_over_sound_played = False
        self._scores_saved = False

    # ── Overlay management ────────────────────────────────────────────────

    def toggle_help(self):
        """Toggle help overlay. Closes other overlays when opening."""
        if self.coordinator.is_rolling or self.coordinator.game_over:
            return
        self.showing_help = not self.showing_help
        if self.showing_help:
            self.showing_history = False
            self.showing_replay = False
            self.kb_selected_index = None

    def toggle_history(self):
        """Toggle history overlay. Closes other overlays when opening."""
        if self.coordinator.is_rolling or self.coordinator.game_over or self.showing_help:
            return
        self.showing_history = not self.showing_history
        if self.showing_history:
            self.showing_replay = False
            self.kb_selected_index = None
        else:
            self.history_filter_player = "all"
            self.history_filter_mode = "all"

    def toggle_replay(self):
        """Toggle replay overlay (only available when game is over)."""
        if not self.coordinator.game_over:
            return
        self.showing_replay = not self.showing_replay

    def close_top_overlay(self):
        """Close the topmost overlay. Returns True if an overlay was closed."""
        if self.showing_help:
            self.showing_help = False
            return True
        if self.showing_replay:
            self.showing_replay = False
            return True
        if self.showing_history:
            self.showing_history = False
            self.history_filter_player = "all"
            self.history_filter_mode = "all"
            return True
        return False

    @property
    def has_active_overlay(self):
        """Whether any overlay is currently showing."""
        return self.showing_help or self.showing_history or self.showing_replay

    @property
    def is_input_blocked(self):
        """Whether game input should be blocked (overlay or confirm dialog)."""
        return self.has_active_overlay or self.confirm_zero_category is not None

    # ── Zero-score confirmation ───────────────────────────────────────────

    def try_score_category(self, cat):
        """Attempt to score a category. Shows confirm dialog if score is 0.

        Returns True if scoring happened immediately, False otherwise.
        """
        coord = self.coordinator
        if coord.scorecard.is_filled(cat) or coord.rolls_used == 0:
            return False
        score = calculate_score_in_context(cat, coord.dice, coord.scorecard)
        if score == 0:
            self.confirm_zero_category = cat
            return False
        if coord.select_category(cat):
            self.sound.play_score()
            self.kb_selected_index = None
            return True
        return False

    def confirm_zero_yes(self):
        """Confirm scoring 0 in the pending category. Returns True if scored."""
        cat = self.confirm_zero_category
        if cat is None:
            return False
        self.confirm_zero_category = None
        if self.coordinator.select_category(cat):
            self.sound.play_score()
            self.kb_selected_index = None
            return True
        return False

    def confirm_zero_no(self):
        """Cancel the zero-score confirmation."""
        self.confirm_zero_category = None

    # ── Keyboard category navigation ──────────────────────────────────────

    def navigate_category(self, direction):
        """Move keyboard selection to next/previous unfilled category.

        Args:
            direction: +1 for forward, -1 for backward
        """
        scorecard = self.coordinator.scorecard
        unfilled = [i for i, cat in enumerate(CATEGORY_ORDER)
                     if not scorecard.is_filled(cat)]
        if not unfilled:
            return

        if self.kb_selected_index is None:
            self.kb_selected_index = unfilled[0] if direction > 0 else unfilled[-1]
        else:
            if direction > 0:
                candidates = [i for i in unfilled if i > self.kb_selected_index]
                self.kb_selected_index = candidates[0] if candidates else unfilled[0]
            else:
                candidates = [i for i in unfilled if i < self.kb_selected_index]
                self.kb_selected_index = candidates[-1] if candidates else unfilled[-1]

        self.hovered_category = None

    def set_hovered_category(self, cat):
        """Set mouse-hovered category (clears keyboard selection)."""
        self.hovered_category = cat
        self.kb_selected_index = None

    def clear_hover(self):
        """Clear mouse hover state."""
        self.hovered_category = None

    # ── Settings ──────────────────────────────────────────────────────────

    def load_settings(self):
        """Load persisted settings and apply to adapter + coordinator."""
        settings = load_settings()
        self.colorblind_mode = settings.get("colorblind_mode", False)
        self.sound._enabled = settings.get("sound_enabled", True)
        self.dark_mode = settings.get("dark_mode", False)
        saved_speed = settings.get("speed", "normal")
        if saved_speed in ("slow", "normal", "fast"):
            from game_coordinator import SPEED_PRESETS
            if saved_speed in SPEED_PRESETS:
                self.coordinator.speed_name = saved_speed
                self.coordinator.ai_delay, self.coordinator.roll_duration, \
                    self.coordinator.ai_hold_show_duration = SPEED_PRESETS[saved_speed]

    def _save_settings(self):
        """Persist current settings to disk."""
        save_settings({
            "colorblind_mode": self.colorblind_mode,
            "sound_enabled": self.sound.enabled,
            "speed": self.coordinator.speed_name,
            "dark_mode": self.dark_mode,
        })

    def toggle_colorblind(self):
        """Toggle colorblind mode and save."""
        self.colorblind_mode = not self.colorblind_mode
        self._save_settings()

    def toggle_dark_mode(self):
        """Toggle dark mode and save."""
        self.dark_mode = not self.dark_mode
        self._save_settings()

    def toggle_sound(self):
        """Toggle sound and save."""
        self.sound.toggle()
        self._save_settings()

    def change_speed(self, direction):
        """Change AI speed. Returns True if speed changed."""
        if self.coordinator.change_speed(direction):
            self._save_settings()
            return True
        return False

    # ── Game actions ──────────────────────────────────────────────────────

    def do_roll(self):
        """Roll dice. Plays roll sound if roll started. Returns True if rolling."""
        self.coordinator.roll_dice()
        if self.coordinator.is_rolling:
            self.sound.play_roll()
            return True
        return False

    def do_hold(self, die_index):
        """Toggle hold on a die. Plays click sound."""
        self.coordinator.toggle_hold(die_index)
        self.sound.play_click()

    def do_undo(self):
        """Undo last action. Returns True if successful."""
        return self.coordinator.undo()

    def do_reset(self):
        """Reset game. Saves scores first if game was over."""
        self._save_scores()
        self.coordinator.reset_game()
        self._game_over_sound_played = False
        self._scores_saved = False
        self.showing_replay = False
        self.confirm_zero_category = None
        self.kb_selected_index = None

    # ── Per-frame update ──────────────────────────────────────────────────

    def update(self):
        """Consume coordinator signals, advance flash, handle game-over.

        Returns dict of events that occurred this frame:
            roll_started, roll_ended, scored, game_over_triggered
        """
        coord = self.coordinator
        events = {
            "roll_started": False,
            "roll_ended": False,
            "scored": False,
            "game_over_triggered": False,
        }

        was_rolling = coord.is_rolling
        round_before = coord.current_round
        was_game_over = coord.game_over

        # Tick the coordinator
        coord.tick()

        # Detect roll start (AI)
        if coord.is_rolling and not was_rolling:
            events["roll_started"] = True
            if not coord.is_current_player_human:
                self.sound.play_roll()

        # Detect roll end
        if was_rolling and not coord.is_rolling:
            events["roll_ended"] = True

        # Detect AI scoring
        if not coord.is_current_player_human:
            if (coord.current_round != round_before or
                    (coord.game_over and not was_game_over)):
                events["scored"] = True
                self.sound.play_score()

        # Game over handling (once)
        if coord.game_over and not self._game_over_sound_played:
            self.sound.play_fanfare()
            self._game_over_sound_played = True
            self._save_scores()
            events["game_over_triggered"] = True

        # Score flash: consume signal from coordinator
        if coord.last_scored_category is not None:
            self.score_flash_category = coord.last_scored_category
            self.score_flash_timer = 0
            coord.last_scored_category = None
            self.kb_selected_index = None
            self.confirm_zero_category = None

        # Advance flash timer
        if self.score_flash_category is not None:
            self.score_flash_timer += 1
            if self.score_flash_timer >= self.score_flash_duration:
                self.score_flash_category = None

        return events

    # ── Score flash progress ──────────────────────────────────────────────

    @property
    def score_flash_progress(self):
        """Return flash progress 0.0-1.0, or None if no flash active."""
        if self.score_flash_category is None:
            return None
        return self.score_flash_timer / self.score_flash_duration

    # ── History filters ───────────────────────────────────────────────────

    def cycle_player_filter(self):
        """Cycle through player type filters for history overlay."""
        idx = self._player_filter_options.index(self.history_filter_player)
        self.history_filter_player = self._player_filter_options[
            (idx + 1) % len(self._player_filter_options)
        ]

    def cycle_mode_filter(self):
        """Cycle through mode filters for history overlay."""
        idx = self._mode_filter_options.index(self.history_filter_mode)
        self.history_filter_mode = self._mode_filter_options[
            (idx + 1) % len(self._mode_filter_options)
        ]

    # ── Data helpers ──────────────────────────────────────────────────────

    def get_filtered_history(self, limit=20):
        """Return filtered score history entries."""
        p_filter = None if self.history_filter_player == "all" else self.history_filter_player
        m_filter = None if self.history_filter_mode == "all" else self.history_filter_mode
        return get_recent_scores_filtered(
            limit=limit, player_type=p_filter, mode=m_filter
        )

    def get_high_scores(self, limit=5):
        """Return top human high scores."""
        return get_high_scores(player_type="human", limit=limit)

    # ── Score saving ──────────────────────────────────────────────────────

    def _save_scores(self):
        """Persist game results (idempotent — only saves once per game)."""
        if self._scores_saved:
            return
        if not self.coordinator.game_over:
            return
        self._scores_saved = True
        coord = self.coordinator

        if coord.multiplayer:
            results = []
            for i in range(coord.num_players):
                name, strategy = coord.player_configs[i]
                player_type = ("human" if strategy is None
                               else strategy.__class__.__name__.replace("Strategy", "").lower())
                score = coord.all_scorecards[i].get_grand_total()
                results.append({"name": name, "score": score, "player_type": player_type})
            record_multiplayer_scores(results)
        else:
            score = coord.scorecard.get_grand_total()
            if coord.ai_strategy:
                player_type = coord.ai_strategy.__class__.__name__.replace("Strategy", "").lower()
            else:
                player_type = "human"
            record_score(score, player_type=player_type)

    # ── Full state snapshot (for web frontend) ────────────────────────────

    def get_game_snapshot(self):
        """Return a complete JSON-serializable dict of game + UI state.

        Used by the web frontend to push full state over WebSocket.
        """
        coord = self.coordinator

        # Dice state
        dice = [{"value": d.value, "held": d.held} for d in coord.dice]

        # Current scorecard
        scorecard = coord.scorecard
        scores = {}
        for cat in Category:
            val = scorecard.scores.get(cat)
            if val is not None:
                scores[cat.value] = val

        # Potential scores for unfilled categories
        potential_scores = {}
        if coord.rolls_used > 0 and not coord.game_over:
            for cat in Category:
                if not scorecard.is_filled(cat):
                    potential_scores[cat.value] = calculate_score_in_context(
                        cat, coord.dice, scorecard
                    )

        # All scorecards (for multiplayer)
        all_scorecards = []
        for sc in coord.all_scorecards:
            sc_data = {}
            for cat in Category:
                val = sc.scores.get(cat)
                if val is not None:
                    sc_data[cat.value] = val
            all_scorecards.append({
                "scores": sc_data,
                "upper_total": sc.get_upper_section_total(),
                "upper_bonus": sc.get_upper_section_bonus(),
                "lower_total": sc.get_lower_section_total(),
                "grand_total": sc.get_grand_total(),
                "yahtzee_bonus_count": sc.yahtzee_bonus_count,
            })

        # Player configs
        player_configs = []
        if coord.multiplayer:
            for name, strategy in coord.player_configs:
                player_configs.append({
                    "name": name,
                    "is_human": strategy is None,
                    "strategy": ("human" if strategy is None
                                 else strategy.__class__.__name__.replace("Strategy", "").lower()),
                })

        # Score flash
        flash = {"category": None, "progress": None}
        if self.score_flash_category is not None:
            flash["category"] = self.score_flash_category.value
            flash["progress"] = self.score_flash_progress

        # AI score choice preview
        ai_score_choice = None
        if coord.ai_showing_score_choice and coord.ai_score_choice_category:
            ai_score_choice = coord.ai_score_choice_category.value

        return {
            "dice": dice,
            "rolls_used": coord.rolls_used,
            "current_round": coord.current_round,
            "game_over": coord.game_over,
            "is_rolling": coord.is_rolling,
            "can_roll": coord.can_roll_now,
            "is_human_turn": coord.is_current_player_human,
            "ai_reason": coord.ai_reason,
            "can_undo": coord.can_undo,
            "scorecard": {
                "scores": scores,
                "upper_total": scorecard.get_upper_section_total(),
                "upper_bonus": scorecard.get_upper_section_bonus(),
                "lower_total": scorecard.get_lower_section_total(),
                "grand_total": scorecard.get_grand_total(),
                "yahtzee_bonus_count": scorecard.yahtzee_bonus_count,
            },
            "potential_scores": potential_scores,
            "multiplayer": coord.multiplayer,
            "num_players": coord.num_players,
            "current_player_index": coord.current_player_index,
            "player_configs": player_configs,
            "all_scorecards": all_scorecards,
            "turn_transition": coord.turn_transition,
            "speed": coord.speed_name,
            "has_any_ai": coord.has_any_ai,
            "ai_score_choice": ai_score_choice,
            "showing_help": self.showing_help,
            "showing_history": self.showing_history,
            "showing_replay": self.showing_replay,
            "confirm_zero_category": (self.confirm_zero_category.value
                                       if self.confirm_zero_category else None),
            "kb_selected_index": self.kb_selected_index,
            "score_flash": flash,
            "colorblind_mode": self.colorblind_mode,
            "dark_mode": self.dark_mode,
            "sound_enabled": self.sound.enabled,
        }
