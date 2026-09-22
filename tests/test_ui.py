# -*- coding: utf-8 -*-
"""The cockpit in a real (headless, invisible) browser, on made-up data.

Skipped when the Python `playwright` package or its Chromium is not installed:
members do not need it to use Jeeves, only to run these checks.
These guard the usability faults found on 2026-09-22 so they cannot come back.
"""
import time

import pytest

pw = pytest.importorskip("playwright.sync_api")


@pytest.fixture
def page(server, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_DELAY", "0.02")
    try:
        p = pw.sync_playwright().start()
        b = p.chromium.launch(headless=True)
    except Exception as exc:  # noqa: BLE001 - no Chromium: skip, do not fail
        pytest.skip("Chromium for playwright is not installed: %s" % exc)
    ctx = b.new_context(viewport={"width": 1366, "height": 768})
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(server[0] + "/")
    pg.wait_for_function("window.__jeevesReady === true", timeout=15000)
    time.sleep(0.8)
    yield pg, errors
    b.close()
    p.stop()


def _send(pg, text):
    pg.fill(".composer textarea", text)
    pg.click(".composer .send")
    pg.wait_for_function("!document.querySelector('.composer .send').disabled", timeout=30000)


def test_text_box_stays_on_screen_after_3_replies_on_a_laptop(page):
    """Critic finding 1: after 1 reply at 1366x768 the Send button slid off the screen."""
    pg, errors = page
    for i in range(3):
        _send(pg, "Question %d?" % i)
    box = pg.locator(".composer .send").bounding_box()
    assert box["y"] + box["height"] <= 768
    assert not errors


def test_enter_while_answering_does_not_send(page, monkeypatch):
    pg, _ = page
    monkeypatch.setenv("FAKE_CLAUDE_DELAY", "0.05")
    pg.fill(".composer textarea", "slow")
    pg.click(".composer .send")
    time.sleep(0.3)
    pg.fill(".composer textarea", "impatient")
    pg.focus(".composer textarea")
    pg.keyboard.press("Enter")
    time.sleep(0.2)
    assert pg.evaluate("document.querySelectorAll('.msg.you').length") == 1
    assert "Still answering" in pg.inner_text("#status-line")
    pg.wait_for_function("!document.querySelector('.composer .send').disabled", timeout=30000)


def test_the_conversation_is_still_there_after_a_reload(page):
    pg, _ = page
    _send(pg, "Remember me")
    pg.reload()
    pg.wait_for_function("window.__jeevesReady === true", timeout=15000)
    time.sleep(0.5)
    assert "Remember me" in pg.inner_text(".log")
    assert "Carrying on the conversation" in pg.inner_text(".log")


def test_a_link_opens_in_the_vault_that_has_it_and_the_tab_agrees(server):
    """Critic finding 3: a [[link]] clicked with the CRM tab lit broke the Vaults panel."""
    try:
        p = pw.sync_playwright().start()
        b = p.chromium.launch(headless=True)
    except Exception as exc:  # noqa: BLE001
        pytest.skip("Chromium for playwright is not installed: %s" % exc)
    try:
        pg = b.new_page(viewport={"width": 1600, "height": 1000})
        pg.goto(server[0] + "/")
        pg.wait_for_function("window.__jeevesReady === true", timeout=15000)
        time.sleep(0.8)
        pg.click(".vb-tabs button[data-k=crm]")
        time.sleep(0.3)
        pg.evaluate("""(() => { const s = document.createElement('span'); s.className = 'wl';
            s.dataset.note = 'Pricing review'; document.querySelector('.log').appendChild(s);
            s.dispatchEvent(new MouseEvent('click', {bubbles: true})); })()""")
        pg.wait_for_function("document.querySelector('.vb-path') && document.querySelector('.vb-path').innerText.includes('Pricing review')", timeout=5000)
        lit = pg.evaluate("[...document.querySelectorAll('.vb-tabs button.on')].map(b => b.dataset.k)")
        assert lit == ["brain"]
        pg.click(".vb-tabs button[data-k=crm]")
        time.sleep(0.3)
        pg.click(".vb-file >> text=Marcus Webb")
        pg.wait_for_function("document.querySelector('.vb-path').innerText.includes('Marcus Webb')", timeout=5000)
    finally:
        b.close()
        p.stop()


def test_every_panel_can_be_closed_and_the_empty_screen_says_what_to_do(page):
    pg, errors = page
    for _ in range(15):
        closers = pg.locator(".dv-tab .dv-default-tab-action")
        if not closers.count():
            break
        closers.first.click(force=True)
        time.sleep(0.1)
    assert pg.locator(".dv-watermark-jeeves").count() == 1
    pg.click(".dv-watermark-jeeves [data-reset]")
    time.sleep(0.5)
    assert pg.evaluate("document.querySelectorAll('.dv-tab').length") == 10
    assert not errors
