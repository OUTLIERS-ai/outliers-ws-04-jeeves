# -*- coding: utf-8 -*-
"""chat.py - every message is answered by your own Claude Code, in your second brain.

Jeeves has no brain of its own. It runs `claude -p` (Claude Code's one-shot
mode) inside your second-brain folder, with your CRM folder added, and streams
the answer back word by word. So it knows every agent, skill and rulebook you
already have, and it costs nothing beyond your Claude subscription.

Choices made on purpose:
- The message goes in on standard input, never on the command line, so quotes,
  new lines and long pastes arrive intact.
- Each chat keeps one Claude Code session id and resumes it, so Jeeves
  remembers the conversation across messages and restarts.
- The permission mode comes from config.json. The default, "dontAsk", lets
  Claude read your notes and refuses anything that needs your approval
  (editing files, running commands). Change it when you decide to.
- No window ever opens: the process is started with CREATE_NO_WINDOW.
"""

import json
import shutil
import subprocess
import threading
import uuid
from datetime import datetime

from . import config as C

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_LOCK = threading.Lock()
_RUNNING = {}

PERSONA = (
    "You are {name}, a personal assistant working through a chat panel in a local web page. "
    "Today is {date}. The person's second brain (an Obsidian vault of their notes) is the "
    "folder you are in: {brain}. {crm_line}"
    "Answer from their own notes whenever you can and name the note you used. "
    "Keep replies short and plain. If something would change a file or reach another person, "
    "say what you would do and wait for them to agree."
)


def _sessions_file():
    return C.state_dir() / "chat-sessions.json"


def _load_sessions():
    try:
        return json.loads(_sessions_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_sessions(d):
    C.atomic_write(_sessions_file(), json.dumps(d, indent=1))


def forget(session_key):
    with _LOCK:
        d = _load_sessions()
        d.pop(session_key, None)
        _save_sessions(d)


def resolve_command(cfg):
    """The Claude Code command as a list, or None if it cannot be found."""
    cmd = cfg.get("claude_command") or "claude"
    if isinstance(cmd, list):
        return list(cmd)
    exe = shutil.which(cmd)
    if not exe:
        return None
    if exe.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", exe]
    return [exe]


def build_args(cfg, model_key, session_key):
    """The full command line, plus the session id and whether it is new."""
    models = cfg.get("models") or {}
    model = models.get(model_key) or models.get(cfg.get("default_model", "best")) or "opus"
    base = resolve_command(cfg)
    if base is None:
        return None, None, None
    sessions = _load_sessions()
    rec = sessions.get(session_key)
    args = base + ["-p", "--output-format", "stream-json", "--include-partial-messages",
                   "--verbose", "--model", model]
    if cfg.get("permission_mode"):
        args += ["--permission-mode", cfg["permission_mode"]]
    crm = cfg.get("crm_vault")
    if crm:
        args += ["--add-dir", str(crm)]
    if rec:
        sid = rec["sid"]
        args += ["--resume", sid]
        new = False
    else:
        sid = str(uuid.uuid4())
        persona = PERSONA.format(
            name=cfg.get("name", "Jeeves"), date=datetime.now().strftime("%A %d %B %Y"),
            brain=cfg.get("second_brain") or "(not set)",
            crm_line=("Their CRM is a separate vault at %s. " % crm) if crm else "")
        args += ["--session-id", sid, "--append-system-prompt", persona]
        new = True
    return args, sid, new


def _activity(name, inp):
    inp = inp or {}
    for k in ("file_path", "path", "pattern", "command", "query", "url", "description"):
        if inp.get(k):
            return "%s: %s" % (name, str(inp[k])[:120])
    return name or "tool"


def stream(cfg, message, model_key="best", session_key="main"):
    """A generator of events: activity / delta / done / error."""
    message = (message or "").strip()
    if not message:
        yield {"type": "done", "text": "You did not type anything."}
        return
    args, sid, new = build_args(cfg, model_key, session_key)
    if args is None:
        yield {"type": "error", "text": "Claude Code was not found. Install it, log in once "
                                        "by typing `claude` in a terminal, then restart Jeeves."}
        return
    cwd = cfg.get("second_brain") or None
    final, parts = "", []
    try:
        proc = subprocess.Popen(
            args, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
            bufsize=1, creationflags=NO_WINDOW)
    except OSError as exc:
        yield {"type": "error", "text": "Could not start Claude Code: %s" % exc}
        return
    with _LOCK:
        _RUNNING[session_key] = proc
    # Read the error channel on its own thread, so a chatty error stream can
    # never fill up and freeze the reply stream.
    errbuf = []
    drain = threading.Thread(target=lambda: errbuf.append(proc.stderr.read()), daemon=True)
    drain.start()
    timer = threading.Timer(float(cfg.get("chat_timeout_seconds") or 600), proc.kill)
    timer.start()
    try:
        try:
            proc.stdin.write(message)
            proc.stdin.close()
        except OSError:
            pass
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            t = ev.get("type")
            if t == "stream_event":
                e = ev.get("event") or {}
                d = e.get("delta") or {}
                if e.get("type") == "content_block_delta" and d.get("type") == "text_delta":
                    parts.append(d.get("text", ""))
                    yield {"type": "delta", "text": d.get("text", "")}
            elif t == "assistant":
                for block in (ev.get("message") or {}).get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        yield {"type": "activity",
                               "text": _activity(block.get("name"), block.get("input"))}
            elif t == "result":
                final = (ev.get("result") or "").strip()
                if ev.get("is_error"):
                    yield {"type": "error", "text": final or "Claude Code reported an error."}
        proc.wait(timeout=15)
        drain.join(timeout=5)
        err = "".join(x or "" for x in errbuf).strip()
    except Exception as exc:  # noqa: BLE001 - reported to the panel, never swallowed
        yield {"type": "error", "text": "The reply was cut short: %s" % exc}
        err = ""
    finally:
        timer.cancel()
        with _LOCK:
            _RUNNING.pop(session_key, None)
    if proc.returncode not in (0, None) and not final:
        yield {"type": "error", "text": (err[-600:] or "Claude Code stopped with code %s."
                                          % proc.returncode)}
        return
    with _LOCK:
        d = _load_sessions()
        d[session_key] = {"sid": sid, "updated": datetime.now().isoformat(timespec="seconds")}
        _save_sessions(d)
    yield {"type": "done", "text": final or "".join(parts)}


def stop(session_key="main"):
    with _LOCK:
        p = _RUNNING.get(session_key)
    if p and p.poll() is None:
        p.kill()
        return True
    return False
