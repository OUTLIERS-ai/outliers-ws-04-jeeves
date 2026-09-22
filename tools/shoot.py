# -*- coding: utf-8 -*-
"""Photograph a running Jeeves for the guide, headless (no window ever appears).

    python tools/shoot.py http://127.0.0.1:4099 guide/img

Needs the Python `playwright` package with Chromium installed
(pip install playwright && python -m playwright install chromium).
Run it against the made-up demo (tools/demo.py), never against your real vaults.
"""

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def wait_ready(page):
    page.wait_for_function("window.__jeevesReady === true", timeout=15000)
    time.sleep(1.2)


def main(base, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    base = base.rstrip("/")
    shots = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1600, "height": 1000}, device_scale_factor=1)
        page = ctx.new_page()
        page.goto(base + "/")
        page.evaluate("localStorage.clear()")
        page.goto(base + "/")
        wait_ready(page)
        # 1. the cockpit before anything is asked
        page.screenshot(path=str(out / "cockpit-start.png"))
        shots.append("cockpit-start.png")
        # 2. ask a question; the fake Claude streams a made-up answer
        page.fill(".composer textarea", "Who should I speak to first today, and why?")
        page.click(".composer .send")
        page.wait_for_function(
            "document.querySelector('.msg.bot') && document.querySelector('.msg.bot').innerText.includes('Pricing review')",
            timeout=30000)
        time.sleep(0.8)
        page.screenshot(path=str(out / "cockpit-chat.png"))
        shots.append("cockpit-chat.png")
        # 3. the orb, close up, at double resolution
        # A narrow window at double zoom: the whole chat header and its suggestion
        # buttons fit uncut, and the picture comes out 1800px wide.
        ctx2 = b.new_context(viewport={"width": 900, "height": 700}, device_scale_factor=2)
        p2 = ctx2.new_page()
        p2.goto(base + "/?only=chat")
        wait_ready(p2)
        head = p2.locator(".chat-head").bounding_box()
        chips = p2.locator(".chips").bounding_box()
        top = head["y"] + 2  # below the panel toolbar, so no half-cut line of text
        p2.screenshot(path=str(out / "orb.png"), clip={
            "x": 0, "y": top, "width": 900,
            "height": chips["y"] + chips["height"] + 12 - top})
        shots.append("orb.png")
        ctx2.close()
        # 4. each panel on its own, as a popped-out window shows it
        solo = b.new_context(viewport={"width": 1400, "height": 860})
        sp = solo.new_page()
        for name in ["vaults", "agents", "activity", "tokens", "overview", "today", "inbox", "board"]:
            sp.goto(base + "/?only=" + name)
            wait_ready(sp)
            if name == "vaults":
                sp.click(".vb-file >> text=Pricing review")
                time.sleep(0.8)
            if name == "board":
                sp.wait_for_selector(".pbody .empty, .pbody iframe", timeout=15000)
            sp.screenshot(path=str(out / ("panel-%s.png" % name)))
            shots.append("panel-%s.png" % name)
        b.close()
    for s in shots:
        print(out / s)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
