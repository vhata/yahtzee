"""
Score History Test Suite

Tests for persistent score recording and retrieval.

Sections:
    1. Recording & Retrieval — basic round-trip of scores
    2. Sorting & Filtering — descending order, player_type filter, limit
    3. Edge Cases — missing file, corrupt file, max entries cap
    4. Multiplayer — multi-player score recording
    5. Entry Shape — required fields present on each entry
"""
import pytest
import json
from pathlib import Path

from score_history import (
    record_score,
    record_multiplayer_scores,
    get_high_scores,
    get_all_scores,
    MAX_ENTRIES,
)


# ── 1. Recording & Retrieval ────────────────────────────────────────────────


def test_record_and_retrieve(tmp_path):
    """Record a single score and verify it round-trips with the correct fields."""
    path = tmp_path / "scores.json"
    record_score(250, player_type="human", path=path)

    entries = get_all_scores(path=path)
    assert len(entries) == 1

    entry = entries[0]
    assert entry["score"] == 250
    assert entry["player_type"] == "human"
    assert entry["mode"] == "single"
    assert "date" in entry


# ── 2. Sorting & Filtering ──────────────────────────────────────────────────


def test_sorted_descending(tmp_path):
    """Scores returned by get_high_scores are sorted highest-first."""
    path = tmp_path / "scores.json"
    for s in (100, 300, 200):
        record_score(s, player_type="human", path=path)

    top = get_high_scores(path=path)
    assert [e["score"] for e in top] == [300, 200, 100]


def test_filter_by_player_type(tmp_path):
    """Filtering by player_type returns only matching entries."""
    path = tmp_path / "scores.json"
    record_score(150, player_type="human", path=path)
    record_score(220, player_type="optimal", path=path)
    record_score(180, player_type="human", path=path)

    human_scores = get_high_scores(player_type="human", path=path)
    assert len(human_scores) == 2
    assert all(e["player_type"] == "human" for e in human_scores)


def test_top_n_limit(tmp_path):
    """get_high_scores(limit=N) returns at most N entries."""
    path = tmp_path / "scores.json"
    for s in (10, 20, 30, 40, 50):
        record_score(s, player_type="human", path=path)

    top3 = get_high_scores(limit=3, path=path)
    assert len(top3) == 3
    # Should be the highest 3
    assert [e["score"] for e in top3] == [50, 40, 30]


# ── 3. Edge Cases ───────────────────────────────────────────────────────────


def test_missing_file(tmp_path):
    """get_all_scores on a nonexistent path returns an empty list."""
    path = tmp_path / "does_not_exist.json"
    assert get_all_scores(path=path) == []


def test_corrupt_file(tmp_path):
    """A corrupt (non-JSON) file is handled gracefully, returning empty list."""
    path = tmp_path / "scores.json"
    path.write_text("this is not valid json {{{")

    assert get_all_scores(path=path) == []


def test_max_entries_cap(tmp_path):
    """Storage is capped at MAX_ENTRIES; oldest entries are dropped first."""
    path = tmp_path / "scores.json"
    total = MAX_ENTRIES + 10
    for i in range(total):
        record_score(i, player_type="human", path=path)

    entries = get_all_scores(path=path)
    assert len(entries) == MAX_ENTRIES

    # The oldest 10 entries (scores 0-9) should have been dropped.
    scores_present = {e["score"] for e in entries}
    for dropped in range(10):
        assert dropped not in scores_present


# ── 4. Multiplayer ──────────────────────────────────────────────────────────


def test_multiplayer_records(tmp_path):
    """record_multiplayer_scores stores one entry per player with correct metadata."""
    path = tmp_path / "scores.json"
    results = [
        {"name": "Alice", "score": 280, "player_type": "human"},
        {"name": "Bot", "score": 210, "player_type": "optimal"},
    ]
    record_multiplayer_scores(results, path=path)

    entries = get_all_scores(path=path)
    assert len(entries) == 2
    assert all(e["mode"] == "multiplayer" for e in entries)

    names = {e["name"] for e in entries}
    assert names == {"Alice", "Bot"}


# ── 5. Entry Shape ──────────────────────────────────────────────────────────


def test_entry_has_date(tmp_path):
    """Every recorded entry contains a non-empty ISO date string."""
    path = tmp_path / "scores.json"
    record_score(100, player_type="human", path=path)

    entry = get_all_scores(path=path)[0]
    assert "date" in entry
    assert isinstance(entry["date"], str)
    assert len(entry["date"]) > 0


# ── 6. Recent Scores ──────────────────────────────────────────────────────

from score_history import get_recent_scores


def test_recent_scores_newest_first(tmp_path):
    """get_recent_scores returns entries most-recent first."""
    path = tmp_path / "scores.json"
    record_score(100, player_type="human", path=path)
    record_score(200, player_type="human", path=path)
    record_score(300, player_type="human", path=path)

    recent = get_recent_scores(path=path)
    scores = [e["score"] for e in recent]
    assert scores == [300, 200, 100]


def test_recent_scores_respects_limit(tmp_path):
    """get_recent_scores(limit=N) returns at most N entries."""
    path = tmp_path / "scores.json"
    for s in range(10):
        record_score(s * 10, player_type="human", path=path)

    recent = get_recent_scores(limit=3, path=path)
    assert len(recent) == 3
    # Should be the 3 most recent (highest numbered scores since we added them in order)
    assert recent[0]["score"] == 90
    assert recent[1]["score"] == 80
    assert recent[2]["score"] == 70
