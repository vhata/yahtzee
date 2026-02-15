"""Persistent settings for Yahtzee.

Stores user preferences in ~/.yahtzee_settings.json.
No pygame dependency — follows the same pattern as score_history.py.
"""

import json
from pathlib import Path

DEFAULTS = {
    "colorblind_mode": False,
    "sound_enabled": True,
    "speed": "normal",
    "dark_mode": False,
}


def _default_path():
    """Return the default path for the settings file."""
    return Path.home() / ".yahtzee_settings.json"


def load_settings(path=None):
    """Load settings from JSON file. Returns DEFAULTS on missing/corrupt.

    Merges with DEFAULTS so missing keys get default values.
    Unknown keys are ignored.
    """
    if path is None:
        path = _default_path()
    path = Path(path)
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            return dict(DEFAULTS)
        # Merge: only keep known keys, fill missing from defaults
        result = dict(DEFAULTS)
        for key in DEFAULTS:
            if key in data:
                result[key] = data[key]
        return result
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return dict(DEFAULTS)


def save_settings(settings, path=None):
    """Write settings dict to JSON. Silently ignores write errors."""
    if path is None:
        path = _default_path()
    path = Path(path)
    try:
        path.write_text(json.dumps(settings, indent=2))
    except OSError:
        pass
