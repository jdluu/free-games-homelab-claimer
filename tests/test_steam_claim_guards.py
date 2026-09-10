import asyncio

from src.stores import steam


class _Result:
    def scalars(self):
        return self

    def first(self):
        return object()


class _Session:
    async def execute(self, statement):
        return _Result()


class _SessionContext:
    async def __aenter__(self):
        return _Session()

    async def __aexit__(self, *args):
        return False


class _Page:
    def __init__(self):
        self.visited = False

    async def get(self, url):
        self.visited = True


class _Claimer(steam.SteamClaimer):
    def __init__(self):
        self.user = "tester"
        self.page = _Page()
        self.notify_games = []

    async def sleep(self, seconds):
        pass


def test_recorded_claim_is_not_retried(monkeypatch):
    monkeypatch.setattr(steam, "async_session", _SessionContext)
    claimer = _Claimer()
    asyncio.run(claimer._claim_game({"app_id": "123", "title": "Owned", "url": "https://example.test"}))
    assert claimer.page.visited is False
