"""
Settings Test Suite

Tests for persistent settings load/save.

Sections:
    1. Load — missing file, corrupt file, partial, unknown keys
    2. Save — round-trip, bad path
"""
import json

from settings import DEFAULTS, load_settings, save_settings

# ── 1. Load ──────────────────────────────────────────────────────────────────


def test_load_missing_file_returns_defaults(tmp_path):
    """Loading from a nonexistent file returns DEFAULTS."""
    path = tmp_path / "no_such_file.json"
    result = load_settings(path=path)
    assert result == DEFAULTS


def test_load_corrupt_file_returns_defaults(tmp_path):
    """Loading from a corrupt (non-JSON) file returns DEFAULTS."""
    path = tmp_path / "bad.json"
    path.write_text("not json at all {{{")
    result = load_settings(path=path)
    assert result == DEFAULTS


def test_save_load_round_trip(tmp_path):
    """Settings survive a save/load round trip."""
    path = tmp_path / "settings.json"
    settings = {"colorblind_mode": True, "sound_enabled": False, "speed": "fast", "dark_mode": True}
    save_settings(settings, path=path)
    loaded = load_settings(path=path)
    assert loaded == settings


def test_partial_file_fills_missing_keys(tmp_path):
    """A file with only some keys gets missing ones filled from DEFAULTS."""
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"colorblind_mode": True}))
    result = load_settings(path=path)
    assert result["colorblind_mode"] is True
    assert result["sound_enabled"] == DEFAULTS["sound_enabled"]
    assert result["speed"] == DEFAULTS["speed"]
    assert result["dark_mode"] == DEFAULTS["dark_mode"]


def test_unknown_keys_ignored(tmp_path):
    """Unknown keys in the file are dropped, not passed through."""
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"colorblind_mode": True, "unknown_key": 42}))
    result = load_settings(path=path)
    assert "unknown_key" not in result
    assert result["colorblind_mode"] is True


def test_save_to_bad_path_does_not_raise(tmp_path):
    """Writing to an invalid path silently fails."""
    bad_path = tmp_path / "nonexistent_dir" / "nested" / "settings.json"
    # Should not raise
    save_settings({"colorblind_mode": True}, path=bad_path)


# ── 3. Atomic Writes ────────────────────────────────────────────────────────


def test_atomic_write_preserves_existing_settings(tmp_path):
    """Existing settings survive even if a .tmp file is left over from a crash."""
    path = tmp_path / "settings.json"
    save_settings({"colorblind_mode": True, "sound_enabled": False, "speed": "fast", "dark_mode": True}, path=path)

    # Simulate a crashed partial write
    tmp_file = tmp_path / "settings.json.tmp"
    tmp_file.write_text("corrupted garbage")

    # Original should still load correctly
    loaded = load_settings(path=path)
    assert loaded["colorblind_mode"] is True
    assert loaded["speed"] == "fast"
