# -*- coding: utf-8 -*-
"""Faults found on 2026-09-22 by a cold walk-through, a usability audit and a security
audit. Each test was written to FAIL on the old code first, then the fix made it pass.
No AI is called: Claude Code is played by tools/fake_claude.py.
"""
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

import pytest

from conftest import ROOT, events, get_json, post

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _log(tmp_path, monkeypatch):
    p = tmp_path / "fake-claude-calls.jsonl"
    monkeypatch.setenv("FAKE_CLAUDE_LOG", str(p))
    return p


def _calls(p):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()]


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


# ---------------------------------------------------------------- chat is read-only

READ_ONLY_BLOCK = {"Bash", "PowerShell", "Write", "Edit", "NotebookEdit", "WebFetch", "WebSearch"}


def _blocked(argv):
    if "--disallowedTools" not in argv:
        return set()
    return set(argv[argv.index("--disallowedTools") + 1].replace(",", " ").split())


def test_chat_cannot_run_commands_edit_files_or_go_online_by_default(server, tmp_path, monkeypatch):
    """Security audit row 1: dontAsk alone still uses any tool the member allowed elsewhere."""
    log = _log(tmp_path, monkeypatch)
    post(server[0] + "/api/chat", {"message": "hi"})
    a = _calls(log)[0]["argv"]
    assert READ_ONLY_BLOCK <= _blocked(a)
    # the value is 1 argument, so it can never swallow the flags after it
    assert a[a.index("--disallowedTools") + 1].count(" ") == 0
    # the same rules as deny rules, which Claude Code applies to subagents as well
    rules = json.loads(Path(a[a.index("--settings") + 1]).read_text(encoding="utf-8"))
    assert READ_ONLY_BLOCK <= set(rules["permissions"]["deny"])
    assert "--strict-mcp-config" in a          # no add-on servers that could act elsewhere


def test_allow_actions_in_config_lifts_the_block(server, tmp_path, monkeypatch):
    log = _log(tmp_path, monkeypatch)
    cfg = json.loads(server[1].read_text(encoding="utf-8"))
    cfg["allow_actions"] = True
    server[1].write_text(json.dumps(cfg), encoding="utf-8")
    post(server[0] + "/api/chat", {"message": "hi"})
    a = _calls(log)[0]["argv"]
    assert _blocked(a) == set() and "--settings" not in a and "--strict-mcp-config" not in a


def test_public_config_says_whether_chat_is_read_only(server):
    assert get_json(server[0] + "/api/config")["read_only"] is True


# ---------------------------------------------------------------- failed runs

def test_login_error_is_shown_once_and_its_conversation_is_not_saved(server, tmp_path, monkeypatch):
    """Walk stuck point 2: after 'Not logged in', every later message failed with
    'No conversation found with session ID', because the failed run's id was saved."""
    log = _log(tmp_path, monkeypatch)
    monkeypatch.setenv("FAKE_CLAUDE_RESULT_ERROR", "Not logged in · Please run /login")
    ev = events(post(server[0] + "/api/chat", {"message": "x"})[1])
    texts = [e.get("text", "") for e in ev]
    assert sum("Not logged in" in t for t in texts) == 1, ev   # once, not twice
    assert ev[-1]["type"] == "error"
    monkeypatch.delenv("FAKE_CLAUDE_RESULT_ERROR")
    post(server[0] + "/api/chat", {"message": "y"})
    assert "--session-id" in _calls(log)[1]["argv"], "the failed conversation must not be resumed"


def test_a_conversation_claude_cannot_find_is_forgotten(server, tmp_path, monkeypatch):
    log = _log(tmp_path, monkeypatch)
    post(server[0] + "/api/chat", {"message": "one"})                 # saved
    monkeypatch.setenv("FAKE_CLAUDE_RESULT_ERROR", "No conversation found with session ID: abc")
    post(server[0] + "/api/chat", {"message": "two"})                 # resume fails
    monkeypatch.delenv("FAKE_CLAUDE_RESULT_ERROR")
    post(server[0] + "/api/chat", {"message": "three"})
    assert "--resume" in _calls(log)[1]["argv"]
    assert "--session-id" in _calls(log)[2]["argv"], "a lost conversation must start fresh"


# ---------------------------------------------------------------- 1 run at a time

def test_a_second_message_while_answering_is_refused(server, tmp_path, monkeypatch):
    """Critic finding 2: Enter sent a 2nd message mid-answer; 2 runs, 1 conversation lost."""
    log = _log(tmp_path, monkeypatch)
    monkeypatch.setenv("FAKE_CLAUDE_DELAY", "0.05")
    first = {}
    t = threading.Thread(target=lambda: first.update(r=post(server[0] + "/api/chat", {"message": "slow"})))
    t.start()
    deadline = time.time() + 10
    while time.time() < deadline and not (log.exists() and log.read_text(encoding="utf-8")):
        time.sleep(0.05)
    ev = events(post(server[0] + "/api/chat", {"message": "impatient"})[1])
    t.join(30)
    assert ev and ev[-1]["type"] == "error" and "Still answering" in ev[-1]["text"]
    assert len(_calls(log)) == 1, "the second message must never start Claude"
    assert events(first["r"][1])[-1]["type"] == "done"


# ---------------------------------------------------------------- Stop

def _alive(pid):
    from jeeves import proc
    return proc.alive(pid)


def test_stop_ends_claude_started_through_a_cmd_file(server, tmp_path, monkeypatch):
    """Security audit row 2: npm's claude.cmd runs the real Claude as a child; Stop ended
    only the parent and Claude kept working for up to 10 minutes."""
    pidfile = tmp_path / "child.pid"
    monkeypatch.setenv("FAKE_CLAUDE_CHILD", str(pidfile))
    out = {}
    t = threading.Thread(target=lambda: out.update(r=post(server[0] + "/api/chat", {"message": "go"})))
    t.start()
    deadline = time.time() + 15
    while time.time() < deadline and not (pidfile.exists() and pidfile.read_text()):
        time.sleep(0.05)
    child = int(pidfile.read_text())
    assert _alive(child)
    assert json.loads(post(server[0] + "/api/chat/stop", {})[1])["stopped"] is True
    deadline = time.time() + 8
    while time.time() < deadline and _alive(child):
        time.sleep(0.1)
    t.join(20)
    assert not _alive(child), "Claude's own process was still working after Stop"
    ev = events(out["r"][1])
    assert ev[-1]["type"] == "stopped", ev          # grey "Stopped", not a red crash
    assert not any(e["type"] == "error" for e in ev)


# ---------------------------------------------------------------- 1 copy per port

def test_a_second_copy_cannot_share_the_port(world):
    """Walk stuck point 1: on Windows 2 copies both listened on 4040."""
    from jeeves.server import make_server
    port = _free_port()
    a = make_server(port, str(world))
    try:
        with pytest.raises(OSError):
            make_server(port, str(world))
    finally:
        a.server_close()


def test_health_names_jeeves_and_its_process(server):
    h = get_json(server[0] + "/api/health")
    assert h["ok"] is True and h["app"] == "jeeves" and h["pid"] == os.getpid()


def test_start_says_jeeves_is_already_running(server, capsys):
    import start
    port = int(server[0].rsplit(":", 1)[1])
    rc = start.main(["--port", str(port), "--no-open", "--config", str(server[1])])
    assert rc == 0
    assert "already running" in capsys.readouterr().out


# ---------------------------------------------------------------- --stop and stale numbers

def test_stop_never_kills_an_unrelated_program(tmp_path, capsys):
    """Security audit row 3: a stale jeeves.pid made --stop kill whatever now had that number."""
    import start
    from jeeves import config as C
    bystander = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"],
                                 creationflags=NO_WINDOW)
    try:
        C.atomic_write(start.pid_file(), "%d %d\n" % (bystander.pid, _free_port()))
        start.stop()
        time.sleep(0.5)
        assert bystander.poll() is None, "an unrelated program was killed"
        assert not start.pid_file().exists()
    finally:
        bystander.kill()


def test_stop_stops_a_real_jeeves(world, tmp_path):
    import start
    port = _free_port()
    env = dict(os.environ)
    p = subprocess.Popen([sys.executable, str(ROOT / "start.py"), "--no-open", "--port", str(port),
                          "--config", str(world)], env=env, creationflags=NO_WINDOW,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/api/health" % port, timeout=1)
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.2)
        start.stop()
        p.wait(10)
        assert p.returncode is not None
    finally:
        if p.poll() is None:
            p.kill()


# ---------------------------------------------------------------- [[links]] in either vault

def test_a_link_name_is_found_in_whichever_vault_has_it(server):
    """Critic finding 3: a [[link]] clicked while the CRM tab showed looked in the wrong vault."""
    base = server[0]
    assert get_json(base + "/api/vault/resolve?name=Pricing%20review") == \
        {"key": "brain", "path": "Projects/Pricing review.md"}
    assert get_json(base + "/api/vault/resolve?name=Marcus%20Webb") == \
        {"key": "crm", "path": "People/Marcus Webb.md"}
    assert get_json(base + "/api/vault/resolve?name=Nobody%20Here") == {"key": None, "path": None}


# ---------------------------------------------------------------- installer

def test_installer_asks_again_when_the_port_is_not_a_number(world, tmp_path, monkeypatch):
    import importlib
    monkeypatch.setenv("JEEVES_CONFIG", str(tmp_path / "o" / "config.json"))
    import install
    importlib.reload(install)
    w = json.loads(world.read_text(encoding="utf-8"))
    answers = iter([w["second_brain"], "", "", "forty", "4556", "n"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    assert install.main(["--skip-claude-check"]) == 0
    assert json.loads((tmp_path / "o" / "config.json").read_text(encoding="utf-8"))["port"] == 4556


def test_mac_logon_file_gives_claude_a_path(monkeypatch, tmp_path):
    import importlib
    monkeypatch.setenv("JEEVES_CONFIG", str(tmp_path / "config.json"))
    import install
    importlib.reload(install)
    text = install.plist_text()
    assert "<key>EnvironmentVariables</key>" in text and "<key>PATH</key>" in text
    assert "/opt/homebrew/bin" in text and ".local/bin" in text


def test_claude_is_found_in_its_usual_folder_when_not_on_path(tmp_path, monkeypatch):
    from jeeves import chat
    bindir = tmp_path / "fakehome" / ".local" / "bin"
    bindir.mkdir(parents=True)
    exe = bindir / ("claude.exe" if os.name == "nt" else "claude")
    exe.write_text("")
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    got = chat.resolve_command({"claude_command": "claude"})
    assert got and Path(got[-1]) == exe


def test_a_person_from_the_crm_list_opens_their_crm_note(server):
    base = server[0]
    # Priya Shah has a note in both vaults; from the CRM's list the CRM note is wanted
    assert get_json(base + "/api/vault/resolve?name=Priya%20Shah")["key"] == "brain"
    assert get_json(base + "/api/vault/resolve?name=Priya%20Shah&prefer=crm") == \
        {"key": "crm", "path": "People/Priya Shah.md"}


def test_a_failed_login_run_adds_no_odd_rows(server):
    """Walk: after a failed login, Activity showed '(untitled)' and Tokens a '<synthetic> 0' model."""
    from datetime import datetime, timezone
    from jeeves import sessions
    cfg = json.loads(server[1].read_text(encoding="utf-8"))
    folder = Path(cfg["claude_home"]) / "projects" / "failed-run"
    folder.mkdir(parents=True)
    ts = datetime.now(timezone.utc).isoformat()
    lines = [{"type": "user", "cwd": cfg["second_brain"], "timestamp": ts,
              "message": {"role": "user", "content": "hello"}},
             {"type": "assistant", "timestamp": ts, "message": {
                 "id": "m1", "model": "<synthetic>", "content": [{"type": "text", "text": "Not logged in"}],
                 "usage": {"input_tokens": 0, "output_tokens": 0}}}]
    (folder / "abc.jsonl").write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
    sessions.clear_cache()
    assert "<synthetic>" not in get_json(server[0] + "/api/tokens")["by_model"]
    assert all(s["id"] != "abc" for s in get_json(server[0] + "/api/activity")["sessions"])
