"""
memory.py — Jarvis Persistent Memory Module

Responsibilities:
  • Read/write a flat key-value store backed by a JSON file.
  • Enforce the entry cap defined in config.MEMORY_MAX_ENTRIES (LRU eviction).
  • Expose get_command_entries() so main.py can merge memory commands into
    the dispatch table with zero coupling.

Storage contract:
  • The JSON file is a single object: { "key": "value", ... }
  • Ordering is insertion-order (Python 3.7+ dict guarantee), which is all
    we need for LRU eviction without an OrderedDict.
  • Writes are atomic: data is flushed to a .tmp sibling then os.replace()'d,
    so a crash mid-write never corrupts the store.

What lives here vs. main.py:
  • Handlers that need access to the store live here.
  • respond() is NOT called here — handlers return strings, main.py speaks them.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Callable

import config

logger = logging.getLogger(__name__)

# Ensure the data directory exists at import time.
config.DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# INTERNAL I/O PRIMITIVES
# ---------------------------------------------------------------------------

def _load() -> dict[str, str]:
    """Read the JSON store from disk.  Returns {} if the file is absent or corrupt."""
    path: Path = config.MEMORY_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to load memory store: %s", exc)
        return {}


def _save(store: dict[str, str]) -> None:
    """
    Atomically write *store* to disk.

    Uses a .tmp sibling + os.replace() so a crash mid-write never leaves
    a half-written or empty JSON file.
    """
    path: Path = config.MEMORY_FILE
    tmp: Path = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
    except OSError as exc:
        logger.error("Failed to save memory store: %s", exc)


def _evict_if_needed(store: dict[str, str]) -> None:
    """
    Evict the oldest entries in-place when the store exceeds the configured cap.
    Mutates *store* directly — caller is responsible for saving afterward.
    """
    cap = config.MEMORY_MAX_ENTRIES
    if cap is None:
        return
    while len(store) > cap:
        oldest_key = next(iter(store))
        del store[oldest_key]
        logger.debug("Evicted oldest memory entry: %r", oldest_key)


# ---------------------------------------------------------------------------
# PUBLIC API
# (These are the only symbols main.py or other modules should call.)
# ---------------------------------------------------------------------------

def remember(key: str, value: str) -> str:
    """
    Persist *value* under *key*.  Returns a confirmation string for the caller
    to pass to respond().

    Args:
        key:   Lookup key (case-preserved; callers normalise before passing).
        value: Arbitrary string value to store.

    Returns:
        Human-readable confirmation or error message.
    """
    if not key or not value:
        return "Nothing to remember — key and value must both be non-empty."

    store = _load()
    store[key] = value
    _evict_if_needed(store)
    _save(store)
    logger.info("Stored memory: %r → %r", key, value)
    return f"Got it. I'll remember that {key} is {value}."


def recall(key: str) -> str:
    """
    Retrieve the value for *key*.

    Returns:
        The stored value, or a 'not found' message.
    """
    store = _load()
    value = store.get(key)
    if value is None:
        return f"I don't have anything stored for '{key}'."
    return f"{key} is {value}."


def forget(key: str) -> str:
    """
    Delete *key* from the store.

    Returns:
        Confirmation or 'not found' message.
    """
    store = _load()
    if key not in store:
        return f"No memory found for '{key}'."
    del store[key]
    _save(store)
    logger.info("Deleted memory entry: %r", key)
    return f"Forgotten: {key}."


def list_memories() -> str:
    """
    Return a human-readable summary of all stored keys.

    Returns:
        Comma-separated key list, or a message if the store is empty.
    """
    keys = list(_load().keys())
    if not keys:
        return "Memory is empty."
    return "I remember: " + ", ".join(keys) + "."


def clear_all() -> str:
    """Wipe the entire store.  Irreversible."""
    _save({})
    logger.warning("Memory store cleared.")
    return "All memories cleared."


# ---------------------------------------------------------------------------
# COMMAND REGISTRATION
# Called by main._build_dispatch_table() — see main.py for the protocol.
#
# Memory commands that require arguments (remember, recall, forget) are handled
# via intent_parser.py extracting the key/value before dispatch.  The handlers
# registered here are for the argument-free meta-commands only.
# ---------------------------------------------------------------------------

def get_command_entries() -> dict[str, Callable[[], str]]:
    """
    Return this module's slice of the flat O(1) dispatch table.

    Keys are fully-normalised trigger strings (lowercase, stripped).
    Values are zero-argument callables that return a response string.

    Parameterised commands (remember X is Y, recall X, forget X) are not
    registered here — intent_parser resolves them and calls the public API
    functions directly.
    """
    return {
        "list memories":   list_memories,
        "what do you know": list_memories,
        "clear memory":    clear_all,
        "forget everything": clear_all,
    }
