# -*- coding: utf-8 -*-
"""
Outliers Workspace - Piece 4 - Jeeves

A personal-assistant cockpit that sits on top of your second brain and your CRM:
chat with your own Claude Code, today's list, both vaults, your agents, your
token use and your other apps, each in a panel you can move, tab and pop out.

    python install.py

It asks where your second brain, your CRM and your agents are, checks Claude
Code is installed, and writes config.json next to this file. On Windows it also
writes "Start Jeeves (hidden).vbs" here, and when an answer changes it keeps
the old settings as config.json.bak-<date>. Running it again with the same
answers changes nothing.

    python install.py --uninstall     removes the logon launcher, if it made one

Nothing here runs on a timer. Nothing starts Claude unless you type a message.

Needs: Python 3.8 or newer and Claude Code. Nothing to pip install.
"""

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
# JEEVES_CONFIG lets the tests install into a temporary folder instead of this one.
if os.environ.get("JEEVES_CONFIG"):
    CONFIG = Path(os.environ["JEEVES_CONFIG"]).expanduser()
else:
    CONFIG = HERE / "config.json"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
LAUNCHER_NAME = "Jeeves.vbs"
PLIST_NAME = "ai.outliers.jeeves.plist"


def say(*lines):
    for ln in lines:
        print("  " + ln if ln else "")


def ask(q, default="", a=None):
    if a is not None and a.yes:
        return default
    try:
        got = input("  " + q + (" [%s]: " % default if default else ": ")).strip()
    except EOFError:
        got = ""
    return got or default


def yes(q, default, a):
    if a.yes:
        return default
    got = ask("%s (%s)" % (q, "Y/n" if default else "y/N")).lower()
    return default if not got else got.startswith("y")


def home():
    return Path(os.path.expanduser("~"))


def claude_home():
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(env).expanduser() if env else home() / ".claude"


def pointer(name):
    """The folder an earlier Outliers installer recorded, if it did."""
    p = home() / name
    try:
        val = p.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return val if val and Path(val).is_dir() else ""


def guess_brain():
    return pointer(".outliers-sb") or next(
        (str(p) for p in (home() / "Documents" / "Second Brain", home() / "Second Brain")
         if p.is_dir()), "")


def guess_crm():
    return pointer(".outliers-crm") or next(
        (str(p) for p in (home() / "CRM", home() / "Documents" / "CRM") if p.is_dir()), "")


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(tmp, path)


def port_free(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


# ------------------------------------------------------------------ launchers

def startup_dir():
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def pythonw():
    pw = Path(sys.executable).with_name("pythonw.exe")
    return str(pw if pw.exists() else sys.executable)


def vbs_text():
    # Run ..., 0, False : 0 = no window at all, False = do not wait for it.
    cmd = '"%s" "%s" --no-open' % (pythonw(), HERE / "start.py")
    if CONFIG != HERE / "config.json":
        cmd += ' --config "%s"' % CONFIG
    return ('\' Starts Jeeves with no window. Made by install.py; remove with\n'
            '\' python install.py --uninstall\n'
            'Set sh = CreateObject("WScript.Shell")\n'
            'sh.CurrentDirectory = "%s"\n'
            'sh.Run "%s", 0, False\n') % (HERE, cmd.replace('"', '""'))


def mac_path():
    """A logon job on a Mac starts with almost no PATH, so Claude Code would not be found.
    Give it the folders Claude Code's installers use, then the usual system ones."""
    h = str(home())
    return ":".join([h + "/.local/bin", h + "/.claude/local", "/opt/homebrew/bin",
                     "/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"])


def plist_text():
    return """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>ai.outliers.jeeves</string>
  <key>ProgramArguments</key><array>
    <string>%s</string><string>%s</string><string>--no-open</string></array>
  <key>WorkingDirectory</key><string>%s</string>
  <key>EnvironmentVariables</key><dict>
    <key>PATH</key><string>%s</string></dict>
  <key>RunAtLoad</key><true/>
</dict></plist>
""" % (sys.executable, HERE / "start.py", HERE, mac_path())


def install_launcher():
    if os.name == "nt":
        d = startup_dir()
        if d is None:
            return "Could not find your Startup folder, so no launcher was made."
        target = d / LAUNCHER_NAME
        text = vbs_text()
        if target.exists() and target.read_text(encoding="utf-8") == text:
            return "The logon launcher is already in place: %s" % target
        atomic_write(target, text)
        return "Jeeves will start hidden when you log in: %s" % target
    if sys.platform == "darwin":
        target = home() / "Library" / "LaunchAgents" / PLIST_NAME
        atomic_write(target, plist_text())
        return ("Wrote %s. To switch it on now run:\n     launchctl load %s" % (target, target))
    return ("On Linux, add this line to 'crontab -e' to start Jeeves at boot:\n"
            "     @reboot cd %s && %s start.py --no-open" % (HERE, sys.executable))


def remove_launcher():
    done = []
    d = startup_dir()
    for p in ([d / LAUNCHER_NAME] if d else []) + [home() / "Library" / "LaunchAgents" / PLIST_NAME]:
        if p.exists():
            p.unlink()
            done.append(str(p))
    return done


def hidden_start_file():
    """A double-click file in this folder that starts Jeeves with no window (Windows)."""
    if os.name != "nt":
        return None
    target = CONFIG.parent / "Start Jeeves (hidden).vbs"
    text = vbs_text()
    if target.exists() and target.read_text(encoding="utf-8") == text:
        return target, False
    atomic_write(target, text)
    return target, True


# ------------------------------------------------------------------ main

def uninstall():
    say("", "Removing the logon launcher (your config.json and vaults are not touched).", "")
    try:
        sys.path.insert(0, str(HERE))
        from start import stop
        stop()
    except Exception:  # noqa: BLE001
        pass
    gone = remove_launcher()
    if gone:
        for g in gone:
            say("removed  %s" % g)
    else:
        say("There was no launcher to remove.")
    say("", "To remove Jeeves completely, delete this folder: %s" % HERE, "")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Install Jeeves.")
    ap.add_argument("--vault", help="your second-brain folder")
    ap.add_argument("--crm", help="your CRM folder (optional)")
    ap.add_argument("--agents", help="a folder of Claude Code agents")
    ap.add_argument("--port", type=int)
    ap.add_argument("--launcher", action="store_true", help="start hidden at logon")
    ap.add_argument("--yes", action="store_true", help="accept every default, ask nothing")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--skip-claude-check", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)

    say("", "=" * 66, "  OUTLIERS WORKSPACE - PIECE 4 - JEEVES", "=" * 66, "")
    if a.uninstall:
        return uninstall()

    # 1. What it needs. If anything is missing, stop and change nothing.
    if sys.version_info < (3, 8):
        say("Jeeves needs Python 3.8 or newer. This is %s." % sys.version.split()[0],
            "Nothing has been changed.", "")
        return 1
    claude = shutil.which("claude")
    if not claude and not a.skip_claude_check:
        say("Claude Code is not installed, or not on your PATH.", "",
            "Jeeves has no brain of its own: every answer comes from your Claude Code.",
            "Install it from https://code.claude.com/docs/en/setup ,",
            "open a new terminal, type  claude  once to log in, then run this again.", "",
            "Nothing has been changed.", "")
        return 1
    if claude:
        try:
            v = subprocess.run([claude, "--version"], capture_output=True, text=True,
                               timeout=30, creationflags=NO_WINDOW).stdout.strip()
        except Exception:  # noqa: BLE001
            v = ""
        say("Found Claude Code %s" % (v or "(version unknown)"))
    say("Python %s - nothing to pip install." % sys.version.split()[0], "")

    old = {}
    if CONFIG.exists():
        try:
            old = json.loads(CONFIG.read_text(encoding="utf-8"))
        except ValueError:
            old = {}

    # 2. Where your folders are.
    brain = a.vault or ask("Where is your second brain (the folder)?",
                           old.get("second_brain") or guess_brain(), a)
    brain = str(Path(os.path.expanduser(brain)).resolve()) if brain else ""
    if not brain or not Path(brain).is_dir():
        say("", "I cannot find a second brain at %r." % brain,
            "Install it first (outliers-sb-01-memory), or give the right folder.",
            "Nothing has been changed.", "")
        return 1
    crm = a.crm if a.crm is not None else ask(
        "Where is your CRM (the folder)? Leave blank if you do not have one",
        old.get("crm_vault") or guess_crm(), a)
    crm = str(Path(os.path.expanduser(crm)).resolve()) if crm else ""
    if crm and not Path(crm).is_dir():
        say("", "There is no folder at %s. Leave it blank or give the right one." % crm,
            "Nothing has been changed.", "")
        return 1
    default_agents = (old.get("agents_dirs") or [str(claude_home() / "agents")])[0]
    agents = a.agents or ask("Where are your agents?", default_agents, a)
    agents = str(Path(os.path.expanduser(agents)).resolve()) if agents else ""
    port = a.port
    while not port:
        got = ask("Which port should Jeeves use?", str(old.get("port", 4040)), a)
        try:
            port = int(got)
            if not 1024 <= port <= 65535:
                raise ValueError
        except ValueError:
            port = None
            say("Please type a number between 1024 and 65535, for example 4040.")
            if a.yes:
                return 1

    # 3. Nice to have, never required.
    say("", "Optional extras:")
    say("  ccusage (shows your 5-hour usage window): %s"
        % ("found" if shutil.which("ccusage") else "not found - needs Node.js, then: npm install -g ccusage"))
    try:
        import playwright  # noqa: F401
        pw = "found"
    except ImportError:
        pw = "not found"
    say("  playwright (only needed to retake the guide's pictures): %s" % pw)
    if not port_free(port) and old.get("port") != port:
        say("  Port %d is busy right now. Jeeves will say so when it starts; pick another "
            "with python install.py --port 4041" % port)

    # 4. One config file. Keep anything you added by hand.
    cfg = dict(old)
    cfg.update({"second_brain": brain, "crm_vault": crm,
                "agents_dirs": [agents] if agents else [], "port": port})
    cfg.setdefault("name", "Jeeves")
    cfg.setdefault("models", {"best": "opus", "deep": "sonnet", "fast": "haiku"})
    cfg.setdefault("default_model", "best")
    cfg.setdefault("permission_mode", "dontAsk")
    cfg.setdefault("allow_actions", False)
    cfg.setdefault("claude_command", "claude")
    cfg.setdefault("apps", {
        "projectforge": {"url": "http://127.0.0.1:3020",
                         "repo": "https://github.com/OUTLIERS-ai/outliers-ws-03-projectforge"},
        "fleetview": {"url": "http://127.0.0.1:3010",
                      "repo": "https://github.com/OUTLIERS-ai/outliers-ws-02-fleetview"}})
    say("")
    if cfg == old:
        say("config.json already says exactly this. Nothing changed.")
    else:
        if CONFIG.exists():
            backup = CONFIG.with_name("config.json.bak-%s" % date.today().isoformat())
            shutil.copy2(CONFIG, backup)
            say("Kept a copy of your old settings: %s" % backup.name)
        atomic_write(CONFIG, json.dumps(cfg, indent=2) + "\n")
        say("Wrote config.json")

    hs = hidden_start_file()
    if hs:
        say(("Made %s - double-click it to start Jeeves with no window." if hs[1] else
             "%s is already in place (double-click it to start Jeeves with no window).")
            % hs[0].name)

    # 5. Start at logon? Off unless you say yes.
    if a.launcher or yes("Start Jeeves hidden every time you log in?", False, a):
        say(install_launcher())
    else:
        say("Not starting at logon. Start it yourself with:  python start.py")

    say("", "-" * 66,
        "Done. Start it now:", "",
        "    python start.py", "",
        "Your browser opens http://127.0.0.1:%d/ . You should see the orb top left," % port,
        "Chat on the left, Today in the middle and your agents in a tab below it.",
        "Leave the terminal open while you use it; Ctrl+C in it stops Jeeves.",
        "Chat can read your 2 vaults. It cannot run commands, change files or use",
        "the internet unless you set \"allow_actions\": true in config.json.",
        "Nothing runs on a timer: Claude is only used when you send a message.", "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
