"""
main.py — Jarvis Agent Core

Responsibilities (and only these):
  1. Configure logging and bootstrap the runtime.
  2. Build and own the flat O(1) dispatch table.
  3. Run the REPL: read → parse intent → dispatch → respond.

Dispatch model
──────────────
DISPATCH is a flat dict[str, Callable[[], str]] materialised once at startup.
Lookup is a single dict.get() — O(1) regardless of command count.

  raw trigger string  →  zero-arg callable returning a response string

intent_parser.py sits in front of dispatch and converts natural language into
a (intent, target, value) triple.  Main only sees structured intents.

Parameterised intents (remember, recall, forget, search, open) are handled
by _dispatch_intent(), which calls module APIs directly with extracted args.
Argument-free intents fall through to the flat DISPATCH table.

Adding commands
───────────────
  • Argument-free: add to get_command_entries() in the owning module.
  • Parameterised: add a branch in _dispatch_intent() and a rule in
    intent_parser.RULES.  Nothing else changes.

Signal protocol
───────────────
Handlers return config.EXIT_SIGNAL to terminate the loop.
No module ever calls sys.exit() or raises SystemExit.
"""

from __future__ import annotations

import datetime
import logging
import sys
from typing import Callable

import config
import browser
import memory
import intent_parser
import executor
from intent_parser import ParsedIntent
from speak import speak

# ---------------------------------------------------------------------------
# LOGGING  (configured once, here, before any module uses a logger)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format=config.LOG_FORMAT,
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OUTPUT  — the only place in the entire codebase allowed to call print() or speak()
# ---------------------------------------------------------------------------

def respond(text: str) -> None:
    """Unified output gate.  No module other than main.py may call print() or speak()."""
    print(f"Jarvis: {text}\n")
    speak(text)


# ---------------------------------------------------------------------------
# CORE HANDLERS  (stateless, no side-effects beyond returning a string)
# ---------------------------------------------------------------------------

def _handle_hello() -> str:
    return "Hello. Jarvis online. All systems nominal."

def _handle_time() -> str:
    return f"Current time: {datetime.datetime.now().strftime('%H:%M:%S')}."

def _handle_date() -> str:
    return f"Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')}."

def _handle_exit() -> str:
    return config.EXIT_SIGNAL

def _handle_help() -> str:
    keys = sorted(DISPATCH.keys())
    return "Known commands: " + ", ".join(keys) + "."


# ---------------------------------------------------------------------------
# DISPATCH TABLE ASSEMBLY
# ──────────────────────────────────────────────────────────────────────────
# Flat dict[str, Callable[[], str]].
#   • One key per trigger string — no frozensets, no iteration at lookup time.
#   • Each module exposes get_command_entries() → dict[str, Callable].
#   • Collision policy: last writer wins; log a warning so duplicates surface.
# ---------------------------------------------------------------------------

def _build_dispatch_table() -> dict[str, Callable[[], str]]:
    core_entries: dict[str, Callable[[], str]] = {
        "hello":           _handle_hello,
        "hi":              _handle_hello,
        "hey":             _handle_hello,
        "time":            _handle_time,
        "what time is it": _handle_time,
        "date":            _handle_date,
        "what day is it":  _handle_date,
        "exit":            _handle_exit,
        "quit":            _handle_exit,
        "shutdown":        _handle_exit,
        "help":            _handle_help,
        "commands":        _handle_help,
    }

    dispatch: dict[str, Callable[[], str]] = {}

    for source in (core_entries, browser.get_command_entries(), memory.get_command_entries()):
        for key, handler in source.items():
            if key in dispatch:
                logger.warning("Dispatch collision on key %r — overwriting.", key)
            dispatch[key] = handler

    logger.info("Dispatch table built: %d entries.", len(dispatch))
    return dispatch


# Materialised once — O(1) per lookup for the lifetime of the process.
DISPATCH: dict[str, Callable[[], str]] = _build_dispatch_table()


# ---------------------------------------------------------------------------
# INTENT DISPATCHER
# Bridges ParsedIntent → response string.
# Parameterised intents (open, search, remember, recall, forget) are handled
# explicitly; all others fall through to the flat DISPATCH table.
# ---------------------------------------------------------------------------

# Replace the entire match/case block in _dispatch_intent() with:
def _dispatch_intent(intent: ParsedIntent) -> str:
    response = executor.execute(intent)   # handles open/search/remember/recall/forget
    if response is not None:
        return response
    # "raw" falls through to the flat DISPATCH table — unchanged
    token = (intent.target or "").strip().lower()
    handler = DISPATCH.get(token)
    if handler:
        return handler()
    return f"Unknown command: '{intent.raw}'. Type 'help' for a list of commands."

# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------

def main() -> None:
    print(config.BANNER + "\n")

    while True:
        try:
            raw = input("You: ")

            if not raw.strip():
                continue

            intent   = intent_parser.parse(raw)
            response = _dispatch_intent(intent)

            if not response:
                continue

            if response == config.EXIT_SIGNAL:
                respond("Shutting down. Goodbye.")
                break

            respond(response)

        except KeyboardInterrupt:
            respond("Interrupted. Shutting down.")
            break

        except Exception:
            logger.exception("Unhandled exception in REPL — loop continues.")
            print("Jarvis: An internal error occurred. Check logs.\n")


if __name__ == "__main__":
    main()
