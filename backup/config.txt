"""
config.py — Jarvis Central Configuration

Single source of truth for every tunable in the system.
Modules import what they need; nothing is hardcoded elsewhere.

Design rules:
  • Plain module-level constants only — no classes, no argparse, no env-var
    magic unless a value genuinely must differ between environments.
  • Grouped by owning subsystem so the file is grep-friendly.
  • All paths are pathlib.Path objects so callers never do string joins.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# FILESYSTEM
# ---------------------------------------------------------------------------

# Project root — everything else is relative to this.
ROOT_DIR: Path = Path(__file__).parent.resolve()

# Persistent storage lives here; created at runtime if absent.
DATA_DIR: Path = ROOT_DIR / "data"

# ---------------------------------------------------------------------------
# MEMORY
# ---------------------------------------------------------------------------

MEMORY_FILE: Path = DATA_DIR / "memory.json"

# Maximum number of entries kept in the store before the oldest is evicted.
# Set to None to disable eviction entirely.
MEMORY_MAX_ENTRIES: int | None = 1000

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

LOG_LEVEL: str = "INFO"   # DEBUG | INFO | WARNING | ERROR | CRITICAL
LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# ---------------------------------------------------------------------------
# AGENT RUNTIME
# ---------------------------------------------------------------------------

EXIT_SIGNAL: str = "__EXIT__"

# Printed once on startup.
BANNER: str = "Jarvis online. Type 'exit' to shut down."
