"""Regression tests for the browser-startup page-target race.

nodriver's Browser.get() picks the first page target with a bare
``next(filter(...))``, so calling it before Chrome registers its initial tab
raises StopIteration and asyncio re-raises it as
``RuntimeError: coroutine raised StopIteration``, killing the whole run.
"""

import asyncio

import pytest

from src.core.claimer import BaseClaimer


class _FakeBrowser:
    def __init__(self, *, populate_after=None, get_failures=0):
        self._populate_after = populate_after
        self._updates = 0
        self._get_failures = get_failures
        self._tabs = []
        self.get_calls = 0
        self.page = object()

    @property
    def tabs(self):
        return self._tabs

    async def update_targets(self):
        self._updates += 1
        if self._populate_after is not None and self._updates >= self._populate_after:
            self._tabs = [object()]

    async def get(self, url):
        self.get_calls += 1
        if self._get_failures:
            self._get_failures -= 1
            raise RuntimeError("coroutine raised StopIteration")
        return self.page


class _Base(BaseClaimer):
    store_name = "epic"

    def __init__(self, browser):
        self.browser = browser


def test_waits_for_page_target_before_calling_get():
    # No tab exists until the second target refresh: get() must not be called
    # while tabs is empty, or nodriver raises StopIteration.
    browser = _FakeBrowser(populate_after=2)
    page = asyncio.run(_Base(browser)._open_initial_page(timeout=5))

    assert page is browser.page
    assert browser.get_calls == 1
    assert browser._updates >= 2


def test_retries_when_get_loses_the_race():
    # tabs is non-empty but get() still raises once, as it can when the target
    # disappears between the check and the call.
    browser = _FakeBrowser(populate_after=0, get_failures=1)
    page = asyncio.run(_Base(browser)._open_initial_page(timeout=5))

    assert page is browser.page
    assert browser.get_calls == 2


def test_raises_when_no_page_target_ever_appears():
    browser = _FakeBrowser(populate_after=None)

    with pytest.raises(RuntimeError, match="no usable page target"):
        asyncio.run(_Base(browser)._open_initial_page(timeout=0.4))

    assert browser.get_calls == 0
