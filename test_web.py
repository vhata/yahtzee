"""Tests for web.py — action dispatch and category lookup."""


from frontend_adapter import FrontendAdapter, NullSound
from game_coordinator import GameCoordinator
from game_engine import Category
from web import _category_by_name, _handle_action

# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_adapter(ai_strategy=None, speed="normal", players=None):
    """Create an adapter with a fresh coordinator."""
    coord = GameCoordinator(ai_strategy=ai_strategy, speed=speed, players=players)
    return FrontendAdapter(coord, sound=NullSound())


def _roll_once(adapter):
    """Roll dice once so rolls_used > 0."""
    adapter.do_roll()
    coord = adapter.coordinator
    coord.roll_timer = coord.roll_duration
    coord.tick()


# ── _category_by_name ────────────────────────────────────────────────────────

class TestCategoryByName:
    """Test category lookup by display name."""

    def test_ones(self):
        assert _category_by_name("Ones") == Category.ONES

    def test_twos(self):
        assert _category_by_name("Twos") == Category.TWOS

    def test_threes(self):
        assert _category_by_name("Threes") == Category.THREES

    def test_fours(self):
        assert _category_by_name("Fours") == Category.FOURS

    def test_fives(self):
        assert _category_by_name("Fives") == Category.FIVES

    def test_sixes(self):
        assert _category_by_name("Sixes") == Category.SIXES

    def test_three_of_kind(self):
        assert _category_by_name("3 of a Kind") == Category.THREE_OF_KIND

    def test_four_of_kind(self):
        assert _category_by_name("4 of a Kind") == Category.FOUR_OF_KIND

    def test_full_house(self):
        assert _category_by_name("Full House") == Category.FULL_HOUSE

    def test_small_straight(self):
        assert _category_by_name("Small Straight") == Category.SMALL_STRAIGHT

    def test_large_straight(self):
        assert _category_by_name("Large Straight") == Category.LARGE_STRAIGHT

    def test_yahtzee(self):
        assert _category_by_name("Yahtzee") == Category.YAHTZEE

    def test_chance(self):
        assert _category_by_name("Chance") == Category.CHANCE

    def test_invalid_name_returns_none(self):
        assert _category_by_name("Bogus") is None

    def test_empty_string_returns_none(self):
        assert _category_by_name("") is None

    def test_case_sensitive(self):
        assert _category_by_name("ones") is None

    def test_partial_name(self):
        assert _category_by_name("Full") is None


# ── _handle_action ───────────────────────────────────────────────────────────

class TestHandleActionRoll:
    """Test the roll action."""

    def test_roll_starts_rolling(self):
        adapter = _make_adapter()
        _handle_action(adapter, {"action": "roll"})
        assert adapter.coordinator.is_rolling

    def test_roll_when_already_rolling_is_noop(self):
        adapter = _make_adapter()
        _handle_action(adapter, {"action": "roll"})
        assert adapter.coordinator.is_rolling
        # Second roll while still rolling should not crash
        _handle_action(adapter, {"action": "roll"})
        assert adapter.coordinator.is_rolling


class TestHandleActionHold:
    """Test the hold action."""

    def test_hold_toggles_die(self):
        adapter = _make_adapter()
        _roll_once(adapter)
        assert not adapter.coordinator.dice[0].held
        _handle_action(adapter, {"action": "hold", "die_index": 0})
        assert adapter.coordinator.dice[0].held

    def test_hold_toggles_back(self):
        adapter = _make_adapter()
        _roll_once(adapter)
        _handle_action(adapter, {"action": "hold", "die_index": 2})
        assert adapter.coordinator.dice[2].held
        _handle_action(adapter, {"action": "hold", "die_index": 2})
        assert not adapter.coordinator.dice[2].held

    def test_hold_invalid_index_negative(self):
        adapter = _make_adapter()
        _roll_once(adapter)
        # Should not crash
        _handle_action(adapter, {"action": "hold", "die_index": -1})

    def test_hold_invalid_index_too_high(self):
        adapter = _make_adapter()
        _roll_once(adapter)
        _handle_action(adapter, {"action": "hold", "die_index": 5})

    def test_hold_non_integer_index(self):
        adapter = _make_adapter()
        _roll_once(adapter)
        _handle_action(adapter, {"action": "hold", "die_index": "abc"})

    def test_hold_missing_index(self):
        adapter = _make_adapter()
        _roll_once(adapter)
        _handle_action(adapter, {"action": "hold"})


class TestHandleActionScore:
    """Test the score action."""

    def test_score_valid_category(self):
        adapter = _make_adapter()
        _roll_once(adapter)
        # Score in Chance (always valid with any dice)
        _handle_action(adapter, {"action": "score", "category": "Chance"})
        scorecard = adapter.coordinator.scorecard
        assert scorecard.is_filled(Category.CHANCE)

    def test_score_invalid_category(self):
        adapter = _make_adapter()
        _roll_once(adapter)
        # Should not crash
        _handle_action(adapter, {"action": "score", "category": "Bogus"})

    def test_score_empty_category(self):
        adapter = _make_adapter()
        _roll_once(adapter)
        _handle_action(adapter, {"action": "score", "category": ""})

    def test_score_missing_category(self):
        adapter = _make_adapter()
        _roll_once(adapter)
        _handle_action(adapter, {"action": "score"})


class TestHandleActionConfirmZero:
    """Test confirm zero yes/no actions."""

    def test_confirm_zero_yes_clears_confirm(self):
        adapter = _make_adapter()
        adapter.confirm_zero_category = Category.YAHTZEE
        _roll_once(adapter)
        _handle_action(adapter, {"action": "confirm_zero_yes"})
        assert adapter.confirm_zero_category is None

    def test_confirm_zero_no_clears_confirm(self):
        adapter = _make_adapter()
        adapter.confirm_zero_category = Category.YAHTZEE
        _handle_action(adapter, {"action": "confirm_zero_no"})
        assert adapter.confirm_zero_category is None

    def test_confirm_zero_yes_when_no_pending(self):
        adapter = _make_adapter()
        # Should not crash
        _handle_action(adapter, {"action": "confirm_zero_yes"})

    def test_confirm_zero_no_when_no_pending(self):
        adapter = _make_adapter()
        _handle_action(adapter, {"action": "confirm_zero_no"})


class TestHandleActionNavigate:
    """Test category navigation."""

    def test_navigate_forward(self):
        adapter = _make_adapter()
        _handle_action(adapter, {"action": "navigate_category", "direction": 1})
        assert adapter.kb_selected_index == 0

    def test_navigate_backward(self):
        adapter = _make_adapter()
        _handle_action(adapter, {"action": "navigate_category", "direction": -1})
        assert adapter.kb_selected_index == 12

    def test_navigate_default_direction(self):
        adapter = _make_adapter()
        _handle_action(adapter, {"action": "navigate_category"})
        assert adapter.kb_selected_index == 0


class TestHandleActionHover:
    """Test hover and clear_hover actions."""

    def test_hover_valid_category(self):
        adapter = _make_adapter()
        _handle_action(adapter, {"action": "hover", "category": "Ones"})
        assert adapter.hovered_category == Category.ONES

    def test_hover_invalid_clears(self):
        adapter = _make_adapter()
        adapter.hovered_category = Category.ONES
        _handle_action(adapter, {"action": "hover", "category": "Bogus"})
        assert adapter.hovered_category is None

    def test_clear_hover(self):
        adapter = _make_adapter()
        adapter.hovered_category = Category.TWOS
        _handle_action(adapter, {"action": "clear_hover"})
        assert adapter.hovered_category is None


class TestHandleActionUndo:
    """Test undo action."""

    def test_undo_with_nothing_to_undo(self):
        adapter = _make_adapter()
        # Should not crash
        _handle_action(adapter, {"action": "undo"})


class TestHandleActionReset:
    """Test reset action."""

    def test_reset_restarts_game(self):
        adapter = _make_adapter()
        _roll_once(adapter)
        _handle_action(adapter, {"action": "reset"})
        assert adapter.coordinator.rolls_used == 0


class TestHandleActionToggles:
    """Test toggle actions (help, history, replay, dark_mode, colorblind, sound)."""

    def test_toggle_help(self):
        adapter = _make_adapter()
        assert not adapter.showing_help
        _handle_action(adapter, {"action": "toggle_help"})
        assert adapter.showing_help

    def test_toggle_history(self):
        adapter = _make_adapter()
        assert not adapter.showing_history
        _handle_action(adapter, {"action": "toggle_history"})
        assert adapter.showing_history

    def test_toggle_replay_requires_game_over(self):
        adapter = _make_adapter()
        _handle_action(adapter, {"action": "toggle_replay"})
        assert not adapter.showing_replay

    def test_toggle_dark_mode(self):
        adapter = _make_adapter()
        assert not adapter.dark_mode
        _handle_action(adapter, {"action": "toggle_dark_mode"})
        assert adapter.dark_mode

    def test_toggle_colorblind(self):
        adapter = _make_adapter()
        assert not adapter.colorblind_mode
        _handle_action(adapter, {"action": "toggle_colorblind"})
        assert adapter.colorblind_mode

    def test_toggle_sound(self):
        adapter = _make_adapter()
        assert not adapter.sound.enabled
        _handle_action(adapter, {"action": "toggle_sound"})
        assert adapter.sound.enabled


class TestHandleActionSpeed:
    """Test speed up/down actions."""

    def test_speed_up(self):
        adapter = _make_adapter(speed="normal")
        _handle_action(adapter, {"action": "speed_up"})
        assert adapter.coordinator.speed_name == "fast"

    def test_speed_down(self):
        adapter = _make_adapter(speed="normal")
        _handle_action(adapter, {"action": "speed_down"})
        assert adapter.coordinator.speed_name == "slow"

    def test_speed_up_at_max(self):
        adapter = _make_adapter(speed="fast")
        _handle_action(adapter, {"action": "speed_up"})
        assert adapter.coordinator.speed_name == "fast"

    def test_speed_down_at_min(self):
        adapter = _make_adapter(speed="slow")
        _handle_action(adapter, {"action": "speed_down"})
        assert adapter.coordinator.speed_name == "slow"


class TestHandleActionFilters:
    """Test history filter cycling."""

    def test_cycle_player_filter(self):
        adapter = _make_adapter()
        assert adapter.history_filter_player == "all"
        _handle_action(adapter, {"action": "cycle_player_filter"})
        assert adapter.history_filter_player == "human"

    def test_cycle_mode_filter(self):
        adapter = _make_adapter()
        assert adapter.history_filter_mode == "all"
        _handle_action(adapter, {"action": "cycle_mode_filter"})
        assert adapter.history_filter_mode == "single"


class TestHandleActionEdgeCases:
    """Test edge cases in action dispatch."""

    def test_unknown_action(self):
        adapter = _make_adapter()
        # Should not crash
        _handle_action(adapter, {"action": "nonexistent"})

    def test_empty_action(self):
        adapter = _make_adapter()
        _handle_action(adapter, {"action": ""})

    def test_missing_action_key(self):
        adapter = _make_adapter()
        _handle_action(adapter, {})

    def test_action_with_extra_keys(self):
        adapter = _make_adapter()
        _handle_action(adapter, {"action": "roll", "extra": "ignored"})
        assert adapter.coordinator.is_rolling
