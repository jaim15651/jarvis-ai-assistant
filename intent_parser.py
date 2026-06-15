# """
# intent_parser.py — Jarvis Natural Language Intent Parser

# Responsibility (single):
#   Convert a raw user string into a structured ParsedIntent that the dispatch
#   engine in main.py can act on without any further string inspection.

# What this is NOT:
#   • Not an NLP library wrapper — no NLTK, spaCy, or transformers.
#   • Not a command router — it produces intents, main.py consumes them.
#   • Not a fuzzy matcher — that belongs in a future embeddings layer.

# Architecture:
#   Parsing is a two-stage pipeline:
#     1. Normalise  → strip, lowercase, collapse whitespace, drop filler words.
#     2. Match      → check against an ordered list of pattern rules.

#   Each rule is a (matcher_fn, intent_builder_fn) pair.  matcher_fn takes the
#   normalised string and returns a match object or None.  intent_builder_fn
#   takes the match and returns a ParsedIntent.

#   Rules are ordered most-specific → least-specific so greedier patterns win.

# Extending the parser:
#   Add a new _Rule entry to RULES.  Zero changes to any other file.

# ParsedIntent fields:
#   intent    — canonical verb (open, search, remember, recall, forget, raw)
#   target    — primary noun/object extracted from the phrase, or None
#   value     — secondary payload (e.g. the value in "remember X is Y"), or None
#   raw       — the original, unnormalised user string (for logging / AI fallback)
# """

# from __future__ import annotations

# import re
# from dataclasses import dataclass, field
# from typing import Callable, NamedTuple, Optional


# # ---------------------------------------------------------------------------
# # OUTPUT TYPE
# # ---------------------------------------------------------------------------

# @dataclass(frozen=True, slots=True)
# class ParsedIntent:
#     intent: str               # canonical verb
#     target: Optional[str]     # primary object, lowercased and stripped
#     value:  Optional[str]     # secondary payload
#     raw:    str               # original user string, unmodified

#     def __repr__(self) -> str:
#         return (
#             f"ParsedIntent(intent={self.intent!r}, "
#             f"target={self.target!r}, value={self.value!r})"
#         )


# # ---------------------------------------------------------------------------
# # NORMALISATION
# # ---------------------------------------------------------------------------

# # Filler words that add no semantic content and should be stripped before
# # pattern matching.  Keep this list short — over-stemming breaks recall.
# _FILLERS: frozenset[str] = frozenset({
#     "please", "can you", "could you", "would you", "jarvis",
#     "hey", "just", "now", "for me",
# })

# _WHITESPACE_RE = re.compile(r"\s+")


# def _normalise(raw: str) -> str:
#     """
#     Lowercase, strip outer whitespace, collapse internal runs, remove fillers.

#     Runs in O(W) where W = word count.  No heap allocations beyond the
#     final join — filler removal is a single-pass generator filter.
#     """
#     lowered = raw.strip().lower()
#     tokens  = _WHITESPACE_RE.split(lowered)
#     cleaned = [t for t in tokens if t and t not in _FILLERS]
#     return " ".join(cleaned)


# # ---------------------------------------------------------------------------
# # PATTERN RULES
# # ---------------------------------------------------------------------------
# # Each Rule pairs a compiled regex with a factory that builds a ParsedIntent
# # from the match groups.  Rules are evaluated in declaration order;
# # put more specific patterns before more general ones.
# # ---------------------------------------------------------------------------

# class _Rule(NamedTuple):
#     pattern: re.Pattern
#     builder: Callable[[re.Match], ParsedIntent]


# def _rule(pattern: str, builder: Callable[[re.Match], ParsedIntent]) -> _Rule:
#     """Compile *pattern* with IGNORECASE and wrap in a _Rule."""
#     return _Rule(re.compile(pattern, re.IGNORECASE), builder)


# RULES: list[_Rule] = [

#     # -- MEMORY: "remember <key> is <value>" / "remember <key> as <value>" ----
#     _rule(
#         r"^remember\s+(?P<key>.+?)\s+(?:is|as)\s+(?P<val>.+)$",
#         lambda m: ParsedIntent("remember", m.group("key").strip(),
#                                m.group("val").strip(), m.string),
#     ),

#     # -- MEMORY: "recall <key>" / "what is <key>" ----------------------------
#     _rule(
#         r"^(?:recall|what is|what's)\s+(?P<key>.+)$",
#         lambda m: ParsedIntent("recall", m.group("key").strip(), None, m.string),
#     ),

#     # -- MEMORY: "forget <key>" ----------------------------------------------
#     _rule(
#         r"^forget\s+(?P<key>.+)$",
#         lambda m: ParsedIntent("forget", m.group("key").strip(), None, m.string),
#     ),

#     # -- BROWSER: "open <site>" / "go to <site>" / "launch <site>" -----------
#     _rule(
#         r"^(?:open|go to|launch|navigate to)\s+(?P<site>\S+)$",
#         lambda m: ParsedIntent("open", m.group("site").strip(), None, m.string),
#     ),

#     # -- BROWSER: "search <query>" / "search for <query>" / "google <query>" -
#     _rule(
#         r"^(?:search(?: for)?|google)\s+(?P<query>.+)$",
#         lambda m: ParsedIntent("search", m.group("query").strip(), None, m.string),
#     ),

#     # -- SYSTEM: bare keywords routed as-is (time, date, exit, …) -----------
#     # These pass through unchanged so the dispatch table handles them without
#     # special-casing here.  Intent "raw" signals "look this up in DISPATCH directly."
#     _rule(
#         r"^(?P<cmd>\S[\w\s]*)$",
#         lambda m: ParsedIntent("raw", m.group("cmd").strip(), None, m.string),
#     ),
# ]


# # ---------------------------------------------------------------------------
# # PUBLIC API
# # ---------------------------------------------------------------------------

# def parse(raw: str) -> ParsedIntent:
#     """
#     Parse a raw user utterance into a structured ParsedIntent.

#     Always returns a valid ParsedIntent — never raises.  If no rule matches
#     (which shouldn't happen given the catch-all "raw" rule), falls back to
#     intent="raw", target=None.

#     Args:
#         raw: Unprocessed user input string.

#     Returns:
#         ParsedIntent with intent, target, value, and raw fields set.
#     """
#     normalised = _normalise(raw)

#     for rule in RULES:
#         m = rule.pattern.match(normalised)
#         if m:
#             return rule.builder(m)

#     # Unreachable under current RULES, but safe fallback for future rule edits.
#     return ParsedIntent(intent="raw", target=normalised or None, value=None, raw=raw)


"""
intent_parser.py — Jarvis Natural Language Intent Parser

Responsibility (single):
  Convert a raw user string into a structured ParsedIntent that the dispatch
  engine in main.py can act on without any further string inspection.

What this is NOT:
  • Not an NLP library wrapper — no NLTK, spaCy, or transformers.
  • Not a command router — it produces intents, main.py consumes them.
  • Not a fuzzy matcher — that belongs in a future embeddings layer.

Architecture:
  Parsing is a two-stage pipeline:
    1. Normalise  → strip, lowercase, collapse whitespace, drop filler words.
    2. Match      → check against an ordered list of pattern rules.

  Each rule is a (matcher_fn, intent_builder_fn) pair.  matcher_fn takes the
  normalised string and returns a match object or None.  intent_builder_fn
  takes the match and returns a ParsedIntent.

  Rules are ordered most-specific → least-specific so greedier patterns win.

Extending the parser:
  Add a new _Rule entry to RULES.  Zero changes to any other file.

ParsedIntent fields:
  intent    — canonical verb (open, search, remember, recall, forget, raw)
  target    — primary noun/object extracted from the phrase, or None
  value     — secondary payload (e.g. the value in "remember X is Y"), or None
  raw       — the original, unnormalised user string (for logging / AI fallback)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, NamedTuple, Optional


# ---------------------------------------------------------------------------
# OUTPUT TYPE
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ParsedIntent:
    intent: str               # canonical verb
    target: Optional[str]     # primary object, lowercased and stripped
    value:  Optional[str]     # secondary payload
    raw:    str               # original user string, unmodified

    def __repr__(self) -> str:
        return (
            f"ParsedIntent(intent={self.intent!r}, "
            f"target={self.target!r}, value={self.value!r})"
        )


# ---------------------------------------------------------------------------
# NORMALISATION
# ---------------------------------------------------------------------------

# Filler words that add no semantic content and should be stripped before
# pattern matching.  Keep this list short — over-stemming breaks recall.
_FILLERS: frozenset[str] = frozenset({
    "please", "can you", "could you", "would you", "jarvis",
    "hey", "just", "now", "for me",
})

_WHITESPACE_RE = re.compile(r"\s+")

_CANONICAL_REPLACEMENTS = {
    "start ": "open ",
    "run ": "open ",
    "opening ": "open ",
    "take me to ": "open ",

    "who is ": "recall ",
    "tell me ": "recall ",
    "show me ": "recall ",
    "show ": "recall ",

    "save ": "remember ",
    "store ": "remember ",
}


def _normalise(raw: str) -> str:

    lowered = raw.strip().lower()

    for old, new in _CANONICAL_REPLACEMENTS.items():
        if lowered.startswith(old):
            lowered = lowered.replace(old, new, 1)
            break

    tokens = _WHITESPACE_RE.split(lowered)

    cleaned = [t for t in tokens if t and t not in _FILLERS]

    return " ".join(cleaned)

# ---------------------------------------------------------------------------
# PATTERN RULES
# ---------------------------------------------------------------------------
# Each Rule pairs a compiled regex with a factory that builds a ParsedIntent
# from the match groups.  Rules are evaluated in declaration order;
# put more specific patterns before more general ones.
# ---------------------------------------------------------------------------

class _Rule(NamedTuple):
    pattern: re.Pattern
    builder: Callable[[re.Match], ParsedIntent]


def _rule(pattern: str, builder: Callable[[re.Match], ParsedIntent]) -> _Rule:
    """Compile *pattern* with IGNORECASE and wrap in a _Rule."""
    return _Rule(re.compile(pattern, re.IGNORECASE), builder)


RULES: list[_Rule] = [

    # -- MEMORY: "remember <key> is <value>" / "remember <key> as <value>" ----
    _rule(
        r"^remember\s+(?:that\s+)?(?P<key>.+?)\s+(?:is|as)\s+(?P<val>.+)$",
        lambda m: ParsedIntent("remember", m.group("key").strip(),
                               m.group("val").strip(), m.string),
    ),

    # -- MEMORY: "recall <key>" / "what is <key>" ----------------------------
    _rule(
        r"^(?:recall|what is|what's)\s+(?P<key>.+)$",
        lambda m: ParsedIntent("recall", m.group("key").strip(), None, m.string),
    ),

    # -- MEMORY: "forget <key>" ----------------------------------------------
    _rule(
        r"^forget\s+(?P<key>.+)$",
        lambda m: ParsedIntent("forget", m.group("key").strip(), None, m.string),
    ),

    # -- BROWSER: "open <site>" / "go to <site>" / "launch <site>" -----------
    _rule(
        r"^(?:open|go to|launch|navigate to|start|run|opening)\s+(?P<site>\S+)$",
        lambda m: ParsedIntent("open", m.group("site").strip(), None, m.string),
    ),

    # -- BROWSER: "search <query>" / "search for <query>" / "google <query>" -
    _rule(
        r"^(?:search(?: for)?|google)\s+(?P<query>.+)$",
        lambda m: ParsedIntent("search", m.group("query").strip(), None, m.string),
    ),

    # -- SYSTEM: bare keywords routed as-is (time, date, exit, …) -----------
    # These pass through unchanged so the dispatch table handles them without
    # special-casing here.  Intent "raw" signals "look this up in DISPATCH directly."
    _rule(
        r"^(?P<cmd>\S[\w\s]*)$",
        lambda m: ParsedIntent("raw", m.group("cmd").strip(), None, m.string),
    ),
]


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def parse(raw: str) -> ParsedIntent:
    """
    Parse a raw user utterance into a structured ParsedIntent.

    Always returns a valid ParsedIntent — never raises.  If no rule matches
    (which shouldn't happen given the catch-all "raw" rule), falls back to
    intent="raw", target=None.

    Args:
        raw: Unprocessed user input string.

    Returns:
        ParsedIntent with intent, target, value, and raw fields set.
    """
    normalised = _normalise(raw)

    for rule in RULES:
        m = rule.pattern.match(normalised)
        if m:
            return rule.builder(m)

    # Unreachable under current RULES, but safe fallback for future rule edits.
    return ParsedIntent(intent="raw", target=normalised or None, value=None, raw=raw)
