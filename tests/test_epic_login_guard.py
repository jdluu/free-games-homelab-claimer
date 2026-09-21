import asyncio

from src.stores import epic


class _Page:
    async def get(self, url):
        pass

    async def evaluate(self, script):
        return None


class _Claimer(epic.EpicGamesClaimer):
    def __init__(self, result):
        self.result = result
        self.claimed = False
        self.page = _Page()

    async def start_browser(self, **kwargs):
        pass

    async def _set_cookies(self):
        pass

    async def _ensure_logged_in(self):
        return self.result

    async def _detect_free_games(self):
        return [{"title": "Test game", "url": "https://example.test/game"}]

    async def _claim_game(self, url):
        self.claimed = True

    async def close_browser(self):
        pass


def test_epic_does_not_claim_when_login_is_unverified():
    claimer = _Claimer(False)
    asyncio.run(claimer.run())
    assert claimer.claimed is False


def test_epic_claims_only_after_login_is_verified():
    claimer = _Claimer(True)
    asyncio.run(claimer.run())
    assert claimer.claimed is True


def test_remote_vnc_prompt_requires_tailscale(monkeypatch):
    from src.core import claimer as claimer_module

    monkeypatch.setattr(claimer_module.cfg, "novnc_port", "7080")
    monkeypatch.setattr(claimer_module.cfg, "vnc_remote_url", "https://debian.tail38ae82.ts.net:9443/")
    monkeypatch.setattr(claimer_module.cfg, "notify_login_request", True)

    import logging
    from src.core import notifier
    messages = []

    async def capture(message, **kwargs):
        messages.append(message)

    monkeypatch.setattr(notifier, "notify", capture)

    class _Base:
        store_name = "epic"
        logger = logging.getLogger("test.remote_vnc")

    async def never_logged_in():
        return False

    obj = _Base()
    asyncio.run(claimer_module.BaseClaimer._wait_for_vnc_login(obj, never_logged_in, timeout=1, interval=1))
    assert any("debian.tail38ae82.ts.net:9443" in m for m in messages)
    assert any("connected to Tailscale" in m for m in messages)
