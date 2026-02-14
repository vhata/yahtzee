"""Score history persistence for Yahtzee.

Stores game results in ~/.yahtzee_scores.json as a JSON list,
capped at 1000 entries. No pygame dependency.
"""

import json
from datetime import datetime
from pathlib import Path

MAX_ENTRIES = 1000


def _default_path():
    """Return the default path for the scores file."""
    return Path.home() / ".yahtzee_scores.json"


def _load_scores(path=None):
    """Load scores from the JSON file. Returns empty list on missing/corrupt."""
    if path is None:
        path = _default_path()
    path = Path(path)
    try:
        data = json.loads(path.read_text())
        if isinstance(data, list):
            return data
        return []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def _save_scores(entries, path=None):
    """Write score entries to the JSON file."""
    if path is None:
        path = _default_path()
    path = Path(path)
    path.write_text(json.dumps(entries, indent=2))


def record_score(score, player_type="human", path=None):
    """Record a single-player game score.

    Creates an entry with score, player_type, date (ISO format), and
    mode="single". Appends to the scores file, dropping oldest entries
    if the list exceeds MAX_ENTRIES.
    """
    entries = _load_scores(path)
    entry = {
        "score": score,
        "player_type": player_type,
        "date": datetime.now().isoformat(),
        "mode": "single",
    }
    entries.append(entry)
    if len(entries) > MAX_ENTRIES:
        entries = entries[-MAX_ENTRIES:]
    _save_scores(entries, path)


def record_multiplayer_scores(results, path=None):
    """Record multiplayer game results.

    Args:
        results: list of dicts with keys 'name', 'score', 'player_type'.

    Creates one entry per player sharing the same date, with mode="multiplayer".
    """
    entries = _load_scores(path)
    date = datetime.now().isoformat()
    for result in results:
        entry = {
            "score": result["score"],
            "player_type": result["player_type"],
            "name": result["name"],
            "date": date,
            "mode": "multiplayer",
        }
        entries.append(entry)
    if len(entries) > MAX_ENTRIES:
        entries = entries[-MAX_ENTRIES:]
    _save_scores(entries, path)


def get_high_scores(player_type=None, limit=10, path=None):
    """Return top scores sorted descending.

    Args:
        player_type: if given, filter to only this player type.
        limit: maximum number of entries to return (default 10).

    Returns:
        List of score entry dicts, highest scores first.
    """
    entries = _load_scores(path)
    if player_type is not None:
        entries = [e for e in entries if e.get("player_type") == player_type]
    entries.sort(key=lambda e: e.get("score", 0), reverse=True)
    return entries[:limit]


def get_all_scores(path=None):
    """Return all score entries."""
    return _load_scores(path)
