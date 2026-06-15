"""
browser.py — Jarvis Browser Module

Public API (stable — callers must not break when internals change):
  open_site(alias)     → BrowserResult
  open_url(url)        → BrowserResult
  search_google(query) → BrowserResult
  list_sites()         → list[str]
  SITE_REGISTRY        → dict[str, str]
  get_command_entries() → dict[str, Callable]

Changes from v1:
  • All print() calls removed; module logs only via logging.
  • config imported for any future path/tunable needs.
  • get_command_entries() keys are flat strings (O(1) lookup in main.py).
"""

from __future__ import annotations

import logging
import webbrowser
from dataclasses import dataclass, field
from typing import Callable, Optional
from urllib.parse import quote_plus, urlparse

import config  # noqa: F401 — imported for future tunables; keeps the import surface consistent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# RESULT TYPE
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class BrowserResult:
    ok:    bool
    url:   str
    error: Optional[str] = field(default=None)

    def __bool__(self) -> bool:
        return self.ok


# ---------------------------------------------------------------------------
# SITE REGISTRY — single source of truth for all known URLs.
# Add a row here; nothing else in the codebase needs to change.
# ---------------------------------------------------------------------------

SITE_REGISTRY: dict[str, str] = {
    "youtube":   "https://www.youtube.com",
    "google":    "https://www.google.com",
    "github":    "https://www.github.com",
    "gmail":     "https://mail.google.com",
    "maps":      "https://www.google.com/maps",
    "reddit":    "https://www.reddit.com",
    "wikipedia": "https://www.wikipedia.org",
    "claude":    "https://claude.ai",
    "chatgpt":   "https://chat.openai.com",
    "spotify":   "https://open.spotify.com/",
}


# ---------------------------------------------------------------------------
# INTERNAL LAUNCH PRIMITIVE
# All public functions funnel here.  Swap this body for Playwright/CDP/etc.
# without touching any public signature.
# ---------------------------------------------------------------------------

def _launch(url: str) -> BrowserResult:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        msg = f"Malformed URL rejected: {url!r}"
        logger.error(msg)
        return BrowserResult(ok=False, url=url, error=msg)

    try:
        launched = webbrowser.open(url)
        if not launched:
            msg = "webbrowser.open() reported no browser available."
            logger.warning(msg)
            return BrowserResult(ok=False, url=url, error=msg)

        logger.info("Opened %s", url)
        return BrowserResult(ok=True, url=url)

    except Exception as exc:
        msg = f"Unexpected launch failure: {exc}"
        logger.exception(msg)
        return BrowserResult(ok=False, url=url, error=msg)


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def open_site(alias: str) -> BrowserResult:
    """Resolve *alias* in SITE_REGISTRY and open it."""
    url = SITE_REGISTRY.get(alias.strip().lower())
    if url is None:
        msg = f"Unknown site alias: {alias!r}."
        logger.warning(msg)
        return BrowserResult(ok=False, url="", error=msg)
    return _launch(url)


def open_url(url: str) -> BrowserResult:
    """Open an arbitrary URL; auto-prepends https:// when scheme is missing."""
    if not url or not isinstance(url, str):
        return BrowserResult(ok=False, url="", error="Empty or non-string URL.")
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return _launch(url)


def search_google(query: str) -> BrowserResult:
    """Open a Google search for *query*."""
    if not query or not query.strip():
        return BrowserResult(ok=False, url="", error="Empty search query.")
    return _launch(f"https://www.google.com/search?q={quote_plus(query.strip())}")


def list_sites() -> list[str]:
    """Sorted list of registered site aliases — for respond() in main.py."""
    return sorted(SITE_REGISTRY.keys())


# ---------------------------------------------------------------------------
# COMMAND REGISTRATION
# Flat string keys → O(1) lookup.  One entry per trigger phrase; no frozensets.
# _make_handler() factory captures alias at definition time (no closure bug).
# ---------------------------------------------------------------------------

def _make_handler(alias: str) -> Callable[[], str]:
    def _handler() -> str:
        result = open_site(alias)
        return f"Opening {alias}." if result else f"Could not open {alias}: {result.error}"
    return _handler


def get_command_entries() -> dict[str, Callable[[], str]]:
    """
    Return this module's slice of the flat dispatch table.

    Browser commands are auto-generated from SITE_REGISTRY, so adding a site
    there automatically registers both 'open <alias>' and bare '<alias>' as
    dispatch keys — no manual work required.
    """
    entries: dict[str, Callable[[], str]] = {
        "list sites":  lambda: "Registered sites: " + ", ".join(list_sites()) + ".",
        "what sites":  lambda: "Registered sites: " + ", ".join(list_sites()) + ".",
    }
    for alias in SITE_REGISTRY:
        handler = _make_handler(alias)
        entries[f"open {alias}"] = handler
        entries[alias]           = handler   # bare alias also dispatches
    return entries
