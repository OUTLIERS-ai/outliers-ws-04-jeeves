# -*- coding: utf-8 -*-
"""proc.py - end a program and everything it started, and check whether a program is running.

Why this exists: Claude Code installed with npm is started through `claude.cmd`,
which runs the real Claude as a child program. Ending only the program Jeeves
started (cmd.exe) left the real Claude working, unseen, for up to 10 minutes.
So Stop ends the whole family: on Windows `taskkill /T /F`, elsewhere the whole
process group (Jeeves starts Claude in a group of its own for this reason).

No window ever opens: every call passes CREATE_NO_WINDOW.
"""

import os
import signal
import subprocess

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def popen_group_kwargs():
    """Extra Popen arguments so that kill_tree can later end every child too."""
    if os.name == "nt":
        return {}
    return {"start_new_session": True}


def kill_tree(pid):
    """End the program with this number and every program it started. Returns True if sent."""
    if not pid:
        return False
    if os.name == "nt":
        r = subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True,
                           creationflags=NO_WINDOW)
        return r.returncode == 0
    try:
        os.killpg(os.getpgid(pid), signal.SIGKILL)
        return True
    except (OSError, AttributeError):
        try:
            os.kill(pid, signal.SIGKILL)
            return True
        except OSError:
            return False


def alive(pid):
    """Is a program with this number running? Never sends it any signal on Windows."""
    if not pid:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        h = k32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            code = wintypes.DWORD()
            if not k32.GetExitCodeProcess(h, ctypes.byref(code)):
                return False
            return code.value == 259  # STILL_ACTIVE
        finally:
            k32.CloseHandle(h)
    try:
        os.kill(int(pid), 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False
