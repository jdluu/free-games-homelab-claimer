"""Regression tests for the browser-startup page-target race.

nodriver's Browser.get() picks the first page target with a bare
``next(filter(...))``, so calling it before Chrome registers its initial tab
raises StopIteration, which asyncio re-raises as
``RuntimeError: coroutine raised StopIteration`` and kills the whole run.

Written with unittest so it runs under BOTH test runners in CI:
``python -m unittest discover -s tests`` (Notification Tests workflow, which
installs only requirements.txt and has no pytest) and pytest.
"""

import asyncio
import unittest

from src.core.claimer import BaseClaimer


class _FakeBrowser:
    """Minimal stand-in for nodriver's Browser, reproducing the race."""

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


class InitialPageRaceTests(unittest.TestCase):
    def test_waits_for_page_target_before_calling_get(self):
        # No tab exists until the second target refresh: get() must not be
        # called while tabs is empty, or nodriver raises StopIteration.
        browser = _FakeBrowser(populate_after=2)
        page = asyncio.run(_Base(browser)._open_initial_page(timeout=5))

        self.assertIs(page, browser.page)
        self.assertEqual(browser.get_calls, 1)
        self.assertGreaterEqual(browser._updates, 2)

    def test_retries_when_get_loses_the_race(self):
        # tabs is non-empty but get() still raises once, as it can when the
        # target disappears between the check and the call.
        browser = _FakeBrowser(populate_after=0, get_failures=1)
        page = asyncio.run(_Base(browser)._open_initial_page(timeout=5))

        self.assertIs(page, browser.page)
        self.assertEqual(browser.get_calls, 2)

    def test_raises_when_no_page_target_ever_appears(self):
        browser = _FakeBrowser(populate_after=None)

        with self.assertRaisesRegex(RuntimeError, "no usable page target"):
            asyncio.run(_Base(browser)._open_initial_page(timeout=0.4))

        self.assertEqual(browser.get_calls, 0)


if __name__ == "__main__":
    unittest.main()
