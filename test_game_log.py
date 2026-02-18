"""
Game Log Test Suite

Tests for the game log recording system.

Sections:
    1. Individual logging — roll, hold, score field verification
    2. Filtering — get_turn_entries, get_score_entries
    3. Clear — empties all entries
    4. Ordering — multiple turns stay in order
    5. Multiplayer — entries with different player_index
"""

from game_engine import Category
from game_log import GameLog

# ── 1. Individual logging ────────────────────────────────────────────────────


def test_log_roll():
    """log_roll creates an entry with correct fields."""
    log = GameLog()
    log.log_roll(turn=1, player_index=0, roll_number=1, dice_values=[1, 2, 3, 4, 5])
    assert len(log.entries) == 1
    e = log.entries[0]
    assert e.turn == 1
    assert e.player_index == 0
    assert e.event_type == "roll"
    assert e.dice_values == (1, 2, 3, 4, 5)
    assert e.roll_number == 1
    assert e.category is None
    assert e.score is None


def test_log_score():
    """log_score creates an entry with category and score."""
    log = GameLog()
    log.log_score(turn=3, player_index=0, category=Category.FULL_HOUSE,
                  score=25, dice_values=[2, 2, 3, 3, 3])
    assert len(log.entries) == 1
    e = log.entries[0]
    assert e.event_type == "score"
    assert e.category == Category.FULL_HOUSE
    assert e.score == 25
    assert e.dice_values == (2, 2, 3, 3, 3)


def test_log_hold_change():
    """log_hold_change records held indices and dice values."""
    log = GameLog()
    log.log_hold_change(turn=2, player_index=0, held_indices=[0, 2, 4],
                        dice_values=[5, 1, 5, 2, 5])
    assert len(log.entries) == 1
    e = log.entries[0]
    assert e.event_type == "hold"
    assert e.held_indices == (0, 2, 4)
    assert e.dice_values == (5, 1, 5, 2, 5)


# ── 2. Filtering ─────────────────────────────────────────────────────────────


def test_get_turn_entries():
    """get_turn_entries returns only entries for the specified turn."""
    log = GameLog()
    log.log_roll(turn=1, player_index=0, roll_number=1, dice_values=[1, 1, 1, 1, 1])
    log.log_score(turn=1, player_index=0, category=Category.ONES,
                  score=5, dice_values=[1, 1, 1, 1, 1])
    log.log_roll(turn=2, player_index=0, roll_number=1, dice_values=[2, 2, 2, 2, 2])

    turn1 = log.get_turn_entries(1)
    assert len(turn1) == 2
    assert all(e.turn == 1 for e in turn1)


def test_get_score_entries():
    """get_score_entries returns only score events for the specified player."""
    log = GameLog()
    log.log_roll(turn=1, player_index=0, roll_number=1, dice_values=[1, 2, 3, 4, 5])
    log.log_score(turn=1, player_index=0, category=Category.CHANCE,
                  score=15, dice_values=[1, 2, 3, 4, 5])
    log.log_roll(turn=2, player_index=0, roll_number=1, dice_values=[6, 6, 6, 6, 6])
    log.log_score(turn=2, player_index=0, category=Category.YAHTZEE,
                  score=50, dice_values=[6, 6, 6, 6, 6])

    scores = log.get_score_entries(player_index=0)
    assert len(scores) == 2
    assert scores[0].category == Category.CHANCE
    assert scores[1].category == Category.YAHTZEE


# ── 3. Clear ──────────────────────────────────────────────────────────────────


def test_clear():
    """clear() empties the log."""
    log = GameLog()
    log.log_roll(turn=1, player_index=0, roll_number=1, dice_values=[1, 2, 3, 4, 5])
    log.log_score(turn=1, player_index=0, category=Category.ONES,
                  score=1, dice_values=[1, 2, 3, 4, 5])
    assert len(log.entries) == 2
    log.clear()
    assert len(log.entries) == 0


# ── 4. Ordering ───────────────────────────────────────────────────────────────


def test_multiple_turns_ordering():
    """Entries preserve insertion order across multiple turns."""
    log = GameLog()
    for t in range(1, 4):
        log.log_roll(turn=t, player_index=0, roll_number=1, dice_values=[t]*5)
        log.log_score(turn=t, player_index=0, category=Category.CHANCE,
                      score=t*5, dice_values=[t]*5)

    turns = [e.turn for e in log.entries]
    assert turns == [1, 1, 2, 2, 3, 3]


# ── 5. Multiplayer ────────────────────────────────────────────────────────────


def test_multiplayer_entries():
    """Entries with different player_index are correctly filtered."""
    log = GameLog()
    log.log_roll(turn=1, player_index=0, roll_number=1, dice_values=[1, 2, 3, 4, 5])
    log.log_score(turn=1, player_index=0, category=Category.ONES,
                  score=1, dice_values=[1, 2, 3, 4, 5])
    log.log_roll(turn=1, player_index=1, roll_number=1, dice_values=[6, 6, 6, 6, 6])
    log.log_score(turn=1, player_index=1, category=Category.SIXES,
                  score=30, dice_values=[6, 6, 6, 6, 6])

    p0_scores = log.get_score_entries(player_index=0)
    p1_scores = log.get_score_entries(player_index=1)
    assert len(p0_scores) == 1
    assert len(p1_scores) == 1
    assert p0_scores[0].score == 1
    assert p1_scores[0].score == 30

    p0_turn = log.get_turn_entries(1, player_index=0)
    p1_turn = log.get_turn_entries(1, player_index=1)
    assert len(p0_turn) == 2
    assert len(p1_turn) == 2
