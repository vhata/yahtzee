"""Tests for frontend_adapter.py — shared UI state management."""

import json
import random
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest

from frontend_adapter import (
    CATEGORY_ORDER,
    CATEGORY_TOOLTIPS,
    OPTIMAL_EXPECTED_TOTAL,
    FrontendAdapter,
    NullSound,
    SoundInterface,
)
from game_coordinator import GameCoordinator
from game_engine import Category

# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_adapter(ai_strategy=None, speed="normal", players=None):
    """Create an adapter with a fresh coordinator."""
    coord = GameCoordinator(ai_strategy=ai_strategy, speed=speed, players=players)
    return FrontendAdapter(coord, sound=NullSound())


def _roll_once(adapter):
    """Roll dice once so rolls_used > 0."""
    adapter.do_roll()
    # Complete the roll animation immediately
    coord = adapter.coordinator
    coord.roll_timer = coord.roll_duration
    coord.tick()


# ── NullSound ────────────────────────────────────────────────────────────────

class TestNullSound:
    def test_implements_interface(self):
        s = NullSound()
        assert isinstance(s, SoundInterface)

    def test_toggle(self):
        s = NullSound()
        assert not s.enabled
        s.toggle()
        assert s.enabled
        s.toggle()
        assert not s.enabled

    def test_play_methods_are_noop(self):
        s = NullSound()
        s.play_roll()
        s.play_click()
        s.play_score()
        s.play_fanfare()


# ── Overlay stacking and ESC ─────────────────────────────────────────────────

class TestOverlays:
    def test_toggle_help(self):
        adapter = _make_adapter()
        assert not adapter.showing_help
        adapter.toggle_help()
        assert adapter.showing_help
        adapter.toggle_help()
        assert not adapter.showing_help

    def test_help_closes_history(self):
        adapter = _make_adapter()
        adapter.showing_history = True
        adapter.toggle_help()
        assert adapter.showing_help
        assert not adapter.showing_history

    def test_history_blocked_when_help_showing(self):
        adapter = _make_adapter()
        adapter.showing_help = True
        adapter.toggle_history()
        assert not adapter.showing_history

    def test_close_top_overlay_priority(self):
        """Help closes first, then replay, then history."""
        adapter = _make_adapter()
        adapter.showing_help = True
        adapter.showing_history = True
        assert adapter.close_top_overlay()
        assert not adapter.showing_help
        assert adapter.showing_history

        assert adapter.close_top_overlay()
        assert not adapter.showing_history

        assert not adapter.close_top_overlay()  # Nothing to close

    def test_replay_only_when_game_over(self):
        adapter = _make_adapter()
        adapter.toggle_replay()
        assert not adapter.showing_replay

    def test_has_active_overlay(self):
        adapter = _make_adapter()
        assert not adapter.has_active_overlay
        adapter.showing_help = True
        assert adapter.has_active_overlay

    def test_help_blocked_during_rolling(self):
        adapter = _make_adapter()
        adapter.coordinator.is_rolling = True
        adapter.toggle_help()
        assert not adapter.showing_help

    def test_help_clears_kb_selection(self):
        adapter = _make_adapter()
        adapter.kb_selected_index = 3
        adapter.toggle_help()
        assert adapter.kb_selected_index is None


# ── Zero-score confirmation ──────────────────────────────────────────────────

class TestZeroConfirm:
    def test_zero_score_triggers_confirm(self):
        random.seed(42)
        adapter = _make_adapter()
        _roll_once(adapter)
        # Find a category that scores 0
        coord = adapter.coordinator
        from game_engine import calculate_score_in_context
        zero_cat = None
        for cat in CATEGORY_ORDER:
            score = calculate_score_in_context(cat, coord.dice, coord.scorecard)
            if score == 0 and not coord.scorecard.is_filled(cat):
                zero_cat = cat
                break
        if zero_cat is None:
            pytest.skip("No zero-scoring category with this seed")
        result = adapter.try_score_category(zero_cat)
        assert not result
        assert adapter.confirm_zero_category == zero_cat

    def test_confirm_yes_scores(self):
        random.seed(42)
        adapter = _make_adapter()
        _roll_once(adapter)
        from game_engine import calculate_score_in_context
        coord = adapter.coordinator
        zero_cat = None
        for cat in CATEGORY_ORDER:
            score = calculate_score_in_context(cat, coord.dice, coord.scorecard)
            if score == 0 and not coord.scorecard.is_filled(cat):
                zero_cat = cat
                break
        if zero_cat is None:
            pytest.skip("No zero-scoring category with this seed")
        adapter.try_score_category(zero_cat)
        assert adapter.confirm_zero_category is not None
        result = adapter.confirm_zero_yes()
        assert result
        assert adapter.confirm_zero_category is None
        assert coord.scorecard.is_filled(zero_cat)

    def test_confirm_no_cancels(self):
        adapter = _make_adapter()
        adapter.confirm_zero_category = Category.ONES
        adapter.confirm_zero_no()
        assert adapter.confirm_zero_category is None

    def test_confirm_yes_when_none(self):
        adapter = _make_adapter()
        assert not adapter.confirm_zero_yes()

    def test_try_score_filled_category(self):
        adapter = _make_adapter()
        _roll_once(adapter)
        # Manually fill a category
        adapter.coordinator.scorecard.set_score(Category.CHANCE, 20)
        result = adapter.try_score_category(Category.CHANCE)
        assert not result

    def test_try_score_before_rolling(self):
        adapter = _make_adapter()
        result = adapter.try_score_category(Category.CHANCE)
        assert not result


# ── Category navigation ──────────────────────────────────────────────────────

class TestCategoryNavigation:
    def test_navigate_forward_from_none(self):
        adapter = _make_adapter()
        adapter.navigate_category(+1)
        assert adapter.kb_selected_index == 0

    def test_navigate_backward_from_none(self):
        adapter = _make_adapter()
        adapter.navigate_category(-1)
        assert adapter.kb_selected_index == len(CATEGORY_ORDER) - 1

    def test_navigate_skips_filled(self):
        adapter = _make_adapter()
        adapter.coordinator.scorecard.set_score(Category.ONES, 3)
        adapter.navigate_category(+1)
        assert adapter.kb_selected_index == 1  # Twos, not Ones

    def test_navigate_wraps(self):
        adapter = _make_adapter()
        adapter.kb_selected_index = len(CATEGORY_ORDER) - 1
        adapter.navigate_category(+1)
        assert adapter.kb_selected_index == 0

    def test_set_hovered_clears_kb(self):
        adapter = _make_adapter()
        adapter.kb_selected_index = 5
        adapter.set_hovered_category(Category.TWOS)
        assert adapter.kb_selected_index is None
        assert adapter.hovered_category == Category.TWOS

    def test_navigate_empty_unfilled(self):
        """Navigate when all categories are filled should be a no-op."""
        adapter = _make_adapter()
        for cat in Category:
            adapter.coordinator.scorecard.set_score(cat, 0)
        adapter.navigate_category(+1)
        assert adapter.kb_selected_index is None


# ── Score flash lifecycle ────────────────────────────────────────────────────

class TestScoreFlash:
    def test_flash_starts_on_scored(self):
        adapter = _make_adapter()
        adapter.coordinator.last_scored_category = Category.ONES
        adapter.update()
        assert adapter.score_flash_category == Category.ONES
        assert adapter.score_flash_timer == 1  # Advanced once

    def test_flash_progress(self):
        adapter = _make_adapter()
        adapter.score_flash_category = Category.TWOS
        adapter.score_flash_timer = 15
        assert adapter.score_flash_progress == pytest.approx(0.5)

    def test_flash_expires(self):
        adapter = _make_adapter()
        adapter.score_flash_category = Category.ONES
        adapter.score_flash_timer = 29
        adapter.update()  # Timer goes to 30 = duration
        assert adapter.score_flash_category is None

    def test_no_flash_progress_when_inactive(self):
        adapter = _make_adapter()
        assert adapter.score_flash_progress is None


# ── Settings ─────────────────────────────────────────────────────────────────

class TestSettings:
    def test_toggle_colorblind(self):
        adapter = _make_adapter()
        assert not adapter.colorblind_mode
        adapter.toggle_colorblind()
        assert adapter.colorblind_mode

    def test_toggle_dark_mode(self):
        adapter = _make_adapter()
        assert not adapter.dark_mode
        adapter.toggle_dark_mode()
        assert adapter.dark_mode

    def test_toggle_sound(self):
        adapter = _make_adapter()
        assert not adapter.sound.enabled
        adapter.toggle_sound()
        assert adapter.sound.enabled

    def test_change_speed(self):
        adapter = _make_adapter()
        assert adapter.coordinator.speed_name == "normal"
        assert adapter.change_speed(+1)
        assert adapter.coordinator.speed_name == "fast"
        assert not adapter.change_speed(+1)  # Already at max

    def test_settings_round_trip(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            from settings import load_settings, save_settings
            adapter = _make_adapter()
            adapter.colorblind_mode = True
            adapter.dark_mode = True
            save_settings({
                "colorblind_mode": True,
                "sound_enabled": False,
                "speed": "fast",
                "dark_mode": True,
            }, path=path)
            loaded = load_settings(path=path)
            assert loaded["colorblind_mode"] is True
            assert loaded["dark_mode"] is True
            assert loaded["speed"] == "fast"
        finally:
            path.unlink(missing_ok=True)


# ── Score saving (idempotency) ───────────────────────────────────────────────

class TestScoreSaving:
    def test_saves_only_once(self):
        """Calling _save_scores multiple times should only save once."""
        random.seed(10)
        adapter = _make_adapter()
        # Fast-forward to game over
        coord = adapter.coordinator
        for cat in Category:
            coord.state = replace(coord.state, rolls_used=1)
            coord.select_category(cat)

        assert coord.game_over
        adapter._save_scores()
        assert adapter._scores_saved
        # Calling again should be a no-op
        adapter._save_scores()

    def test_no_save_when_not_over(self):
        adapter = _make_adapter()
        adapter._save_scores()
        assert not adapter._scores_saved


# ── Game actions ─────────────────────────────────────────────────────────────

class TestGameActions:
    def test_do_roll(self):
        adapter = _make_adapter()
        result = adapter.do_roll()
        assert result
        assert adapter.coordinator.is_rolling

    def test_do_hold(self):
        random.seed(42)
        adapter = _make_adapter()
        _roll_once(adapter)
        was_held = adapter.coordinator.dice[0].held
        adapter.do_hold(0)
        assert adapter.coordinator.dice[0].held != was_held

    def test_do_undo(self):
        random.seed(42)
        adapter = _make_adapter()
        _roll_once(adapter)
        adapter.do_hold(0)
        assert adapter.do_undo()

    def test_do_reset(self):
        adapter = _make_adapter()
        _roll_once(adapter)
        adapter.do_reset()
        assert adapter.coordinator.rolls_used == 0
        assert not adapter._scores_saved
        assert not adapter._game_over_sound_played


# ── Snapshot serialization ───────────────────────────────────────────────────

class TestSnapshot:
    def test_snapshot_is_json_serializable(self):
        random.seed(42)
        adapter = _make_adapter()
        _roll_once(adapter)
        snapshot = adapter.get_game_snapshot()
        # Should not raise
        serialized = json.dumps(snapshot)
        parsed = json.loads(serialized)
        assert parsed["rolls_used"] == 1
        assert len(parsed["dice"]) == 5
        assert isinstance(parsed["potential_scores"], dict)

    def test_snapshot_multiplayer(self):
        random.seed(42)
        from ai import GreedyStrategy
        players = [("Alice", None), ("Bot", GreedyStrategy())]
        adapter = _make_adapter(players=players)
        snapshot = adapter.get_game_snapshot()
        serialized = json.dumps(snapshot)
        parsed = json.loads(serialized)
        assert parsed["multiplayer"] is True
        assert parsed["num_players"] == 2
        assert len(parsed["player_configs"]) == 2
        assert parsed["player_configs"][0]["name"] == "Alice"
        assert parsed["player_configs"][0]["is_human"] is True

    def test_snapshot_overlay_state(self):
        adapter = _make_adapter()
        adapter.showing_help = True
        adapter.dark_mode = True
        snapshot = adapter.get_game_snapshot()
        assert snapshot["showing_help"] is True
        assert snapshot["dark_mode"] is True

    def test_snapshot_score_flash(self):
        adapter = _make_adapter()
        adapter.score_flash_category = Category.ONES
        adapter.score_flash_timer = 10
        snapshot = adapter.get_game_snapshot()
        assert snapshot["score_flash"]["category"] == "Ones"
        assert snapshot["score_flash"]["progress"] is not None

    def test_snapshot_confirm_zero(self):
        adapter = _make_adapter()
        adapter.confirm_zero_category = Category.SIXES
        snapshot = adapter.get_game_snapshot()
        assert snapshot["confirm_zero_category"] == "Sixes"


# ── History filters ──────────────────────────────────────────────────────────

class TestHistoryFilters:
    def test_cycle_player_filter(self):
        adapter = _make_adapter()
        assert adapter.history_filter_player == "all"
        adapter.cycle_player_filter()
        assert adapter.history_filter_player == "human"
        adapter.cycle_player_filter()
        assert adapter.history_filter_player == "greedy"

    def test_cycle_mode_filter(self):
        adapter = _make_adapter()
        assert adapter.history_filter_mode == "all"
        adapter.cycle_mode_filter()
        assert adapter.history_filter_mode == "single"
        adapter.cycle_mode_filter()
        assert adapter.history_filter_mode == "multiplayer"
        adapter.cycle_mode_filter()
        assert adapter.history_filter_mode == "all"


# ── Constants ────────────────────────────────────────────────────────────────

class TestConstants:
    def test_category_order_complete(self):
        assert len(CATEGORY_ORDER) == 13
        assert set(CATEGORY_ORDER) == set(Category)

    def test_tooltips_complete(self):
        assert set(CATEGORY_TOOLTIPS.keys()) == set(Category)

    def test_optimal_expected_total(self):
        assert OPTIMAL_EXPECTED_TOTAL == 223.0
