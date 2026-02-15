"""Game log for Yahtzee — records all actions for post-game replay.

Pure Python, no pygame dependency. Captures rolls, holds, and scoring
decisions for each turn.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from game_engine import Category


@dataclass
class LogEntry:
    """A single logged game event."""
    turn: int                                   # 1-13
    player_index: int                           # 0 for single-player
    event_type: str                             # "roll", "hold", "score"
    dice_values: Tuple[int, ...]
    held_indices: Optional[Tuple[int, ...]] = None
    category: Optional[Category] = None
    score: Optional[int] = None
    roll_number: int = 0                        # 1-3 for rolls


class GameLog:
    """Accumulates LogEntry records during a game."""

    def __init__(self):
        self.entries: List[LogEntry] = []

    def log_roll(self, turn, player_index, roll_number, dice_values):
        """Record a dice roll."""
        self.entries.append(LogEntry(
            turn=turn,
            player_index=player_index,
            event_type="roll",
            dice_values=tuple(dice_values),
            roll_number=roll_number,
        ))

    def log_hold_change(self, turn, player_index, held_indices, dice_values):
        """Record a hold/unhold change."""
        self.entries.append(LogEntry(
            turn=turn,
            player_index=player_index,
            event_type="hold",
            dice_values=tuple(dice_values),
            held_indices=tuple(held_indices),
        ))

    def log_score(self, turn, player_index, category, score, dice_values):
        """Record a scoring decision."""
        self.entries.append(LogEntry(
            turn=turn,
            player_index=player_index,
            event_type="score",
            dice_values=tuple(dice_values),
            category=category,
            score=score,
        ))

    def get_turn_entries(self, turn, player_index=0):
        """Return all entries for a specific turn and player."""
        return [e for e in self.entries
                if e.turn == turn and e.player_index == player_index]

    def get_score_entries(self, player_index=0):
        """Return only scoring entries for a player."""
        return [e for e in self.entries
                if e.event_type == "score" and e.player_index == player_index]

    def clear(self):
        """Remove all entries."""
        self.entries = []
