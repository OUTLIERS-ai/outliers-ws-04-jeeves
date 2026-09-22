# -*- coding: utf-8 -*-
"""Start (or stop) Jeeves.

    python start.py            start on the port in config.json and open your browser
    python start.py --no-open  start without opening a browser (used by the logon launcher)
    python start.py --stop     stop the copy that is running
    python start.py --port 4041

It listens on 127.0.0.1 only: this computer, never your network.
"""

import argparse
import os
import signal
import sys

import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from jeeves import config as C  # noqa: E402
from jeeves.server import make_server  # noqa: E402


def pid_file():
    return C.state_dir() / "jeeves.pid"


def stop():
    p = pid_file()
    if not p.exists():
        print("  Jeeves is not running (no record of it).")
        return 0
    try:
        pid = int(p.read_text().split()[0])
    except (OSError, ValueError, IndexError):
        p.unlink(missing_ok=True)
        return 0
    try:
        os.kill(pid, signal.SIGTERM)
        print("  Stopped Jeeves (process %d)." % pid)
    except OSError:
        print("  Jeeves was not running any more.")
    p.unlink(missing_ok=True)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Start the Jeeves cockpit.")
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--config", default=None, help="another config.json (tests, demos)")
    ap.add_argument("--no-open", action="store_true", help="do not open a browser")
    ap.add_argument("--stop", action="store_true", help="stop the running copy")
    a = ap.parse_args(argv)
    if a.stop:
        return stop()
    cfg_file = a.config or os.environ.get("JEEVES_CONFIG")
    cfg = C.load(cfg_file)
    if not cfg.get("second_brain"):
        print("  No config.json yet. Run:  python install.py")
        return 1
    try:
        srv = make_server(a.port, cfg_file)
    except OSError as exc:
        print("  Could not listen on port %s: %s" % (a.port or cfg.get("port"), exc))
        print("  Something else is using it. Try:  python start.py --port 4041")
        return 1
    port = srv.server_address[1]
    C.atomic_write(pid_file(), "%d %d\n" % (os.getpid(), port))
    url = "http://127.0.0.1:%d/" % port
    print("  %s is running at %s  (Ctrl+C to stop)" % (cfg.get("name", "Jeeves"), url))
    if not a.no_open:
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        try:
            if pid_file().read_text().split()[0] == str(os.getpid()):
                pid_file().unlink()
        except (OSError, IndexError):
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
