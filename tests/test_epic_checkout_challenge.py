import asyncio

from src.core import claimer as claimer_module
from src.core import notifier
from src.core.claimer import BaseClaimer
from src.stores import epic


class _Page:
    def __init__(self, challenge=False):
        self.challenge = challenge

    async def evaluate(self, script):
        return self.challenge


class _Base(BaseClaimer):
    store_name = "epic"

    def __init__(self, page):
        self.page = page


def test_human_challenge_present_reads_the_page():
    assert asyncio.run(_Base(_Page(True))._human_challenge_present()) is True
    assert asyncio.run(_Base(_Page(False))._human_challenge_present()) is False


def test_wait_out_challenge_returns_immediately_when_absent():
    async def absent():
        return False

    assert asyncio.run(
        _Base(_Page(False))._wait_out_challenge("Epic", settle=0, present_fn=absent)
    ) is True


def test_wait_out_challenge_ask_false_never_notifies(monkeypatch):
    calls = []

    async def fake_wait(self, check_fn, **kwargs):
        calls.append(kwargs)
        return True

    monkeypatch.setattr(claimer_module.BaseClaimer, "_wait_for_vnc_login", fake_wait)

    async def always():
        return True

    result = asyncio.run(
        _Base(_Page(True))._wait_out_challenge("Epic", settle=0, present_fn=always, ask=False)
    )
    assert result is False
    assert calls == []


def test_wait_out_challenge_notifies_with_the_vnc_url(monkeypatch):
    monkeypatch.setattr(claimer_module.cfg, "novnc_port", "7080")
    monkeypatch.setattr(
        claimer_module.cfg, "vnc_remote_url", "https://debian.tail38ae82.ts.net:9443/"
    )
    monkeypatch.setattr(claimer_module.cfg, "vnc_login_timeout", 180)

    seen = {}

    async def fake_wait(self, check_fn, **kwargs):
        seen.update(kwargs)
        return True

    monkeypatch.setattr(claimer_module.BaseClaimer, "_wait_for_vnc_login", fake_wait)

    async def always():
        return True

    result = asyncio.run(
        _Base(_Page(True))._wait_out_challenge("Epic", settle=0, present_fn=always)
    )
    assert result is True
    assert "debian.tail38ae82.ts.net:9443" in seen["custom_msg"]
    assert "Epic" in seen["custom_msg"]


def test_clear_checkout_challenge_is_a_noop_without_a_challenge():
    claimer = epic.EpicGamesClaimer()
    claimer.page = _Page(False)

    claimer._checkout_challenge_present = lambda: asyncio.sleep(0, result=False)
    assert asyncio.run(claimer._clear_checkout_challenge("Test game")) is True
