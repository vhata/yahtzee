"""Game log for Yahtzee — records all actions for post-game replay.

Pure Python, no pygame dependency. Captures rolls, holds, and scoring
decisions for each turn.
"""
from __future__ import annotations

from dataclasses import dataclass

from game_engine import Category


@dataclass
class LogEntry:
    """A single logged game event."""
    turn: int                                   # 1-13
    player_index: int                           # 0 for single-player
    event_type: str                             # "roll", "hold", "score"
    dice_values: tuple[int, ...]
    held_indices: tuple[int, ...] | None = None
    category: Category | None = None
    score: int | None = None
    roll_number: int = 0                        # 1-3 for rolls


class GameLog:
    """Accumulates LogEntry records during a game."""

    def __init__(self) -> None:
        self.entries: list[LogEntry] = []

    def log_roll(self, turn: int, player_index: int, roll_number: int, dice_values: list[int]) -> None:
        """Record a dice roll."""
        self.entries.append(LogEntry(
            turn=turn,
            player_index=player_index,
            event_type="roll",
            dice_values=tuple(dice_values),
            roll_number=roll_number,
        ))

    def log_hold_change(self, turn: int, player_index: int, held_indices: list[int], dice_values: list[int]) -> None:
        """Record a hold/unhold change."""
        self.entries.append(LogEntry(
            turn=turn,
            player_index=player_index,
            event_type="hold",
            dice_values=tuple(dice_values),
            held_indices=tuple(held_indices),
        ))

    def log_score(self, turn: int, player_index: int, category: Category, score: int, dice_values: list[int]) -> None:
        """Record a scoring decision."""
        self.entries.append(LogEntry(
            turn=turn,
            player_index=player_index,
            event_type="score",
            dice_values=tuple(dice_values),
            category=category,
            score=score,
        ))

    def get_turn_entries(self, turn: int, player_index: int = 0) -> list[LogEntry]:
        """Return all entries for a specific turn and player."""
        return [e for e in self.entries
                if e.turn == turn and e.player_index == player_index]

    def get_score_entries(self, player_index: int = 0) -> list[LogEntry]:
        """Return only scoring entries for a player."""
        return [e for e in self.entries
                if e.event_type == "score" and e.player_index == player_index]

    def clear(self) -> None:
        """Remove all entries."""
        self.entries = []
