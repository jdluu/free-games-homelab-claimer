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
