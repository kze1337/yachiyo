"""
db.py — Shared data layer for all cogs.

Structure of data.json:
{
    "<guild_id>": {
        "<user_id>": {
            "bal":        int,
            "xp":         int,
            "level":      int,
            "last_daily": float,
            "last_fish":  float
        }
    }
}
"""

import json
import os
from typing import Any

_DATA_FILE = "data.json"
_DEFAULTS  = {"bal": 1000, "xp": 0, "level": 1, "last_daily": 0, "last_fish": 0}


def load() -> dict:
    """Load and return the full data dict from disk."""
    try:
        with open(_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save(data: dict) -> None:
    """Atomically write data to disk (write to temp file then rename)."""
    tmp = _DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    os.replace(tmp, _DATA_FILE)


def get_user(data: dict, guild_id: int | str, user_id: int | str) -> dict:
    """
    Return the user sub-dict, creating it with defaults if absent.
    Mutates `data` in place — call save(data) afterwards.
    """
    gid = str(guild_id)
    uid = str(user_id)

    if gid not in data:
        data[gid] = {}

    if uid not in data[gid]:
        data[gid][uid] = dict(_DEFAULTS)
    else:
        # Back-fill any missing keys added in later versions
        for k, v in _DEFAULTS.items():
            data[gid][uid].setdefault(k, v)

    return data[gid][uid]
