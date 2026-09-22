# -*- coding: utf-8 -*-
"""config.py - one file of settings, read in one place.

The installer writes `config.json` next to `start.py`. Nothing else in Jeeves
knows where your vaults are: every module asks this file. A test can point the
whole program somewhere else by setting JEEVES_CONFIG to another file.
"""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULTS = {
    "name": "Jeeves",
    "port": 4040,
    "second_brain": "",
    "crm_vault": "",
    "agents_dirs": [],
    "claude_home": "",
    "claude_command": "claude",
    "models": {"best": "opus", "deep": "sonnet", "fast": "haiku"},
    "default_model": "best",
    "permission_mode": "dontAsk",
    "chat_timeout_seconds": 600,
    "inbox_file": "",
    "daily_note_folders": ["Daily", "Daily Notes", "Journal", "Diary", "Calendar"],
    "apps": {
        "projectforge": {"url": "http://127.0.0.1:3020",
                         "repo": "https://github.com/OUTLIERS-ai/outliers-ws-03-projectforge"},
        "fleetview": {"url": "http://127.0.0.1:3010",
                      "repo": "https://github.com/OUTLIERS-ai/outliers-ws-02-fleetview"},
    },
    "ccusage": "auto",
    "orb": {"inner": "At your service", "outer": "Your second brain is listening"},
}


def config_path():
    env = os.environ.get("JEEVES_CONFIG")
    if env:
        return Path(env).expanduser()
    return ROOT / "config.json"


def _merge(base, extra):
    out = dict(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load(path=None):
    """Your settings, with every missing value filled from DEFAULTS."""
    p = Path(path) if path else config_path()
    data = {}
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
    return _merge(DEFAULTS, data)


def claude_home(cfg):
    """Where Claude Code keeps its own files (session logs, agents)."""
    if cfg.get("claude_home"):
        return Path(cfg["claude_home"]).expanduser()
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".claude"


def vaults(cfg):
    """The two vaults Jeeves reads, as (key, label, path). Missing ones are skipped."""
    out = []
    if cfg.get("second_brain"):
        out.append(("brain", "Second brain", Path(cfg["second_brain"]).expanduser()))
    if cfg.get("crm_vault"):
        out.append(("crm", "CRM", Path(cfg["crm_vault"]).expanduser()))
    return out


def state_dir():
    """Jeeves's own working files (chat session ids, the running server's number)."""
    env = os.environ.get("JEEVES_STATE")
    d = Path(env).expanduser() if env else ROOT / "state"
    d.mkdir(parents=True, exist_ok=True)
    return d


def atomic_write(path, text):
    """Write a file without ever leaving a half-written one behind."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
