"""
executor.py — Jarvis Execution Layer

Single responsibility: translate a structured ParsedIntent into a domain
module call and return the response string to main.py.

Position in the pipeline:
    main.py → intent_parser.parse() → executor.execute() → browser / memory

Contract:
  • Input:  ParsedIntent (frozen dataclass — never mutated here)
  • Output: str — human-readable response, always; never None, never raises
  • "raw" intent is explicitly excluded — main.py owns that dispatch path

Scaling:
  INTENT_HANDLERS is a flat dict[str, Callable[[ParsedIntent], str]].
  Adding a new parameterised intent = one entry in that dict.
  execute() itself never changes.
"""

from __future__ import annotations

import logging
from typing import Callable

import browser
import memory
from intent_parser import ParsedIntent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# INTENT HANDLERS
# Each handler receives the full ParsedIntent so it can access target/value
# without the dispatch layer needing to know the arity of each action.
# ---------------------------------------------------------------------------

def _execute_open(intent: ParsedIntent) -> str:
    if not intent.target:
        return "Usage: open <site>."
    result = browser.open_site(intent.target)
    return f"Opening {intent.target}." if result else f"Could not open {intent.target!r}: {result.error}"


def _execute_search(intent: ParsedIntent) -> str:
    if not intent.target:
        return "Usage: search <query>."
    result = browser.search_google(intent.target)
    return f"Searching Google for '{intent.target}'." if result else f"Search failed: {result.error}"


def _execute_remember(intent: ParsedIntent) -> str:
    if not intent.target or not intent.value:
        return "Usage: remember <key> is <value>."
    return memory.remember(intent.target, intent.value)


def _execute_recall(intent: ParsedIntent) -> str:
    if not intent.target:
        return "Usage: recall <key>."
    return memory.recall(intent.target)


def _execute_forget(intent: ParsedIntent) -> str:
    if not intent.target:
        return "Usage: forget <key>."
    return memory.forget(intent.target)


# ---------------------------------------------------------------------------
# DISPATCH TABLE
# Flat O(1) lookup — add a row to extend; execute() is never touched.
# ---------------------------------------------------------------------------

INTENT_HANDLERS: dict[str, Callable[[ParsedIntent], str]] = {
    "open":     _execute_open,
    "search":   _execute_search,
    "remember": _execute_remember,
    "recall":   _execute_recall,
    "forget":   _execute_forget,
}


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def execute(intent: ParsedIntent) -> str | None:
    """
    Dispatch a structured ParsedIntent to the appropriate domain module.

    Returns a response string for all handled intents, or None for "raw"
    (signalling main.py to handle it via its own dispatch table).

    Never raises — domain errors surface as human-readable return strings.

    Args:
        intent: A ParsedIntent produced by intent_parser.parse().

    Returns:
        Response string, or None if the intent is "raw" / unrecognised here.
    """
    if intent.intent == "raw":
        return None  # Explicitly delegated back to main.py

    handler = INTENT_HANDLERS.get(intent.intent)

    if handler is None:
        logger.warning("executor: unknown intent %r.", intent.intent)
        return f"Unknown executable intent: {intent.intent}"

    try:
        return handler(intent)
    except Exception as exc:
        logger.exception("executor: handler for %r raised unexpectedly.", intent.intent)
        return f"Internal error while handling '{intent.intent}': {exc}"
