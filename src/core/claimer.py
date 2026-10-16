"""Base claimer – the foundation that all store modules build on.

This file contains the BaseClaimer class which provides shared functionality
that every store claimer (Steam, Epic, Prime Gaming, GOG) inherits:

  - Browser management: Launches Google Chrome with stealth anti-detection patches
    so websites don't realise they're talking to an automated bot.
  - Session persistence: Each store gets its own browser profile directory, so
    cookies and login sessions survive Docker container restarts.
  - Screenshot capture: Can save screenshots for debugging or notifications.
  - VNC login fallback: If automatic login fails, waits for you to log in
    manually through the VNC web interface.

The stealth JavaScript patches (injected before any page loads) spoof:
  - navigator.webdriver (hides automation flag)
  - WebGL renderer (fakes a real GPU to avoid captcha)
  - Browser plugins, languages, hardware specs (mimics a real desktop PC)
  - Passkeys (prevents passkey dialogs from blocking login forms)
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone

import nodriver as uc

from src.core.config import cfg

logger = logging.getLogger("fgc.claimer")


# Looks for a human-check (hCaptcha / Arkose / Cloudflare Turnstile / reCAPTCHA /
# DataDome) that is actually *visible and clickable*. Epic keeps a full-size
# hCaptcha iframe on the page at all times, hidden by style, until it is really
# needed — matching on the iframe alone produces constant false positives.
CHALLENGE_JS = r"""
(() => {
    const t = (document.title || '').toLowerCase();
    if (t.includes('just a moment') || t.includes('attention required') || t.includes('one more step')) return true;
    if (document.querySelector('#challenge-form, #challenge-running, #cf-challenge-running')) return true;
    const seen = el => {
        const r = el.getBoundingClientRect();
        if (r.width < 60 || r.height < 40) return false;
        for (let n = el; n; n = n.parentElement) {
            const st = getComputedStyle(n);
            if (st.visibility === 'hidden' || st.display === 'none' || parseFloat(st.opacity) < 0.1) return false;
        }
        const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
        if (cx < 0 || cy < 0 || cx > innerWidth || cy > innerHeight) return false;
        const at = document.elementFromPoint(cx, cy);
        return !!at && (at === el || el.contains(at) || at.contains(el));
    };
    const rx = /hcaptcha|arkoselabs|funcaptcha|arkose|px-captcha|geetest|turnstile|recaptcha\/(api2|enterprise)\/(anchor|bframe)|datadome|captcha-delivery/i;
    const badge = f => /recaptcha\/(api2|enterprise)\/anchor/i.test(f.getAttribute('src') || '') && /[?&]size=invisible/i.test(f.getAttribute('src') || '');
    const frames = [...document.querySelectorAll('iframe')];
    if (frames.some(f => rx.test((f.getAttribute('src') || '') + ' ' + (f.getAttribute('title') || '')) && !badge(f) && seen(f))) return true;
    const widgets = [...document.querySelectorAll('.cf-turnstile, #h_captcha, #talon_frame_login_prod, #FunCaptcha, [id*="arkose" i], #datadome')];
    if (widgets.some(seen)) return true;
    const b = (document.body ? (document.body.innerText || '') : '').toLowerCase();
    if (b.includes('verify you are human') || b.includes('checking your browser') || b.includes('complete a security check') || b.includes('needs to review the security of your connection')) return true;
    if (b.includes("check that you're a real person") || b.includes('check that you are a real person') || b.includes('geo.captcha-delivery.com')) return true;
    return false;
})()
"""


def now_str() -> str:
    """Return a human-readable UTC timestamp string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def filenamify(s: str) -> str:
    """Sanitise a string for use as a filename."""
    import re
    return re.sub(r'[^a-zA-Z0-9 _\-.]', '_', s.replace(":", "."))


class BaseClaimer:
    """Abstract base for all store claimers.

    Subclasses must implement:
        ``store_name``  – class-level string (e.g. ``"epic"``)
        ``run()``       – main claiming coroutine
    """

    store_name: str = "base"

    @property
    def logger(self):
        return logging.getLogger(f"fgc.{self.store_name}")

    def __init__(self) -> None:
        self.browser: uc.Browser | None = None
        self.page: uc.Tab | None = None
        self.user: str | None = None
        self.notify_games: list[dict] = []

    # ------------------------------------------------------------------
    # Browser lifecycle
    # ------------------------------------------------------------------

    # Stealth JS injected BEFORE every page load via CDP
    # (addScriptToEvaluateOnNewDocument ensures it runs before any site JS)
    _STEALTH_JS = """
    // --- navigator.webdriver ---
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
    });

    // --- Realistic plugins ---
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
            { name: 'Native Client', filename: 'internal-nacl-plugin' },
        ],
    });

    // --- Languages (sometimes empty in headless) ---
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],
    });

    // --- Hardware concurrency (must be realistic) ---
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 4,
    });

    // --- Device memory (must be realistic) ---
    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => 8,
    });

    // --- Platform (must stay consistent with the real User-Agent) ---
    // The UA here is a Linux Chrome UA and navigator.userAgentData also reports
    // Linux, so claiming 'Win32' would be a self-contradiction anti-bot vendors
    // flag. Keep the real platform value.
    Object.defineProperty(navigator, 'platform', {
        get: () => 'Linux x86_64',
    });

    // --- WebGL vendor/renderer spoofing ---
    // Epic's anti-bot checks WebGL capabilities; the container renders through
    // Mesa llvmpipe (software), which is a loud bot signal. Report a plausible
    // GPU that matches the Linux UA: an NVIDIA card driven by ANGLE/OpenGL.
    const _GPU_VENDOR = 'Google Inc. (NVIDIA Corporation)';
    const _GPU_RENDERER = 'ANGLE (NVIDIA Corporation, NVIDIA GeForce GTX 1650/PCIe/SSE2, OpenGL 4.5.0 NVIDIA 535.183.01)';
    const _getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {
        // UNMASKED_VENDOR_WEBGL
        if (param === 0x9245) return _GPU_VENDOR;
        // UNMASKED_RENDERER_WEBGL
        if (param === 0x9246) return _GPU_RENDERER;
        return _getParameter.call(this, param);
    };
    if (typeof WebGL2RenderingContext !== 'undefined') {
        const _getParameter2 = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(param) {
            if (param === 0x9245) return _GPU_VENDOR;
            if (param === 0x9246) return _GPU_RENDERER;
            return _getParameter2.call(this, param);
        };
    }

    // --- Disable passkeys (prevents passkey dialogs blocking login) ---
    if (navigator.credentials) {
        navigator.credentials.create = async () => Promise.reject(
            new Error('Passkeys disabled')
        );
        navigator.credentials.get = async () => Promise.reject(
            new Error('Passkeys disabled')
        );
    }

    // --- Permissions API (hide "denied" automation fingerprint) ---
    const _query = window.Permissions?.prototype?.query;
    if (_query) {
        window.Permissions.prototype.query = function(params) {
            if (params?.name === 'notifications') {
                return Promise.resolve({ state: Notification.permission });
            }
            return _query.call(this, params);
        };
    }
    """

    async def start_browser(
        self,
        *,
        force_headful: bool = False,
        extra_args: list[str] | None = None,
    ) -> uc.Browser:
        """Launch a nodriver browser instance with full stealth.

        Args:
            force_headful: If True, always run with a visible window
                           (Epic needs this to avoid captcha).
            extra_args: Additional Chromium flags.
        """
        import shutil

        # Ensure persistent browser profile directory exists (per store)
        store_browser_dir = cfg.browser_dir / self.store_name
        store_browser_dir.mkdir(parents=True, exist_ok=True)

        # Disable Chrome's "Save password?" popup by setting profile preferences
        prefs_dir = store_browser_dir / "Default"
        prefs_dir.mkdir(parents=True, exist_ok=True)
        prefs_file = prefs_dir / "Preferences"
        try:
            import json as _json
            prefs = {}
            if prefs_file.exists():
                prefs = _json.loads(prefs_file.read_text(encoding="utf-8"))
            prefs["credentials_enable_service"] = False
            prefs["credentials_enable_autosignin"] = False
            prefs.setdefault("profile", {})
            prefs["profile"]["password_manager_enabled"] = False
            prefs_file.write_text(_json.dumps(prefs), encoding="utf-8")
        except Exception:
            pass  # Non-critical

        # Cleanup Chrome lock files to prevent crashes when container hostname changes
        # Note: We must use unlink(missing_ok=True) because these are often broken
        # symlinks pointing to non-existent PIDs, and .exists() evaluates to False for them!
        for lock_file in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
            lock_path = store_browser_dir / lock_file
            try:
                if lock_path.is_symlink() or lock_path.exists():
                    lock_path.unlink()
                    self.logger.debug("Removed old %s", lock_file)
            except Exception as e:
                self.logger.warning("Failed to remove %s: %s", lock_file, e)

        # Auto-detect chrome binary
        chrome_path = (
            shutil.which("google-chrome-stable")
            or shutil.which("google-chrome")
            or shutil.which("chromium-browser")
            or shutil.which("chromium")
        )
        self.logger.debug("Chrome: %s", chrome_path)

        headless = False if force_headful else (not cfg.show)

        # --- Browser args ---
        # IMPORTANT: Do NOT add `--disable-blink-features=AutomationControlled`
        # nodriver already handles this internally, and the flag itself is a
        # well-known signal that sophisticated anti-bot systems detect.
        args = [
            f"--window-size={cfg.width},{cfg.height}",
            "--hide-crash-restore-bubble",
            "--restore-last-session",
            "--lang=en-US",
            "--accept-lang=en-US,en",  # no q-values: Chrome copies this verbatim into navigator.languages
            "--disable-dev-shm-usage",     # Docker shared memory fix
            "--disable-smooth-scrolling",  # CPU optimization
            "--disable-extensions",        # CPU optimization
            "--mute-audio",                # CPU optimization
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-breakpad",
            "--disable-component-update",
            "--disable-features=AudioServiceOutOfProcess,Translate,TranslateUI",
            "--disable-translate",
            "--disable-ipc-flooding-protection",
            "--disable-renderer-backgrounding",
            "--metrics-recording-only",
            "--no-first-run",
            "--password-store=basic",
            "--use-mock-keychain",
        ]
        # Only disable GPU when running headless (non-Epic).
        # For headful mode (Epic), GPU must stay enabled so that WebGL reports
        # hardware-accelerated rendering, which is checked by hCaptcha/anti-bot.
        if not force_headful:
            args.append("--disable-gpu")

        if extra_args:
            args.extend(extra_args)

        # Forcefully disable Google Translate at the Chromium profile level
        try:
            import json
            store_browser_dir.mkdir(parents=True, exist_ok=True)
            default_dir = store_browser_dir / "Default"
            default_dir.mkdir(exist_ok=True)
            prefs_file = default_dir / "Preferences"
            prefs = {}
            if prefs_file.exists():
                prefs = json.loads(prefs_file.read_text("utf-8"))
            if "translate" not in prefs:
                prefs["translate"] = {}
            prefs["translate"]["enabled"] = False
            prefs_file.write_text(json.dumps(prefs), "utf-8")
        except Exception as e:
            self.logger.debug("Failed to seed Chrome preferences: %s", e)

        browser_kwargs = dict(
            headless=headless,
            sandbox=False,  # required when running as root in Docker
            browser_executable_path=chrome_path,
            browser_args=args,
            user_data_dir=str(store_browser_dir),
        )
        try:
            self.browser = await uc.start(**browser_kwargs)
        except Exception as first_error:
            # A GPU/WebGL startup failure must not take down both stores. Keep
            # the preferred GPU path for Epic, but retry once with software
            # rendering when Chrome never exposes its DevTools endpoint.
            if "--disable-gpu" in args:
                raise
            self.logger.warning(
                "Chrome startup failed; retrying once with GPU disabled: %s",
                first_error,
            )
            fallback_args = [*args, "--disable-gpu"]
            self.browser = await uc.start(
                **{**browser_kwargs, "browser_args": fallback_args}
            )

        # Get the main tab
        self.page = await self.browser.get("about:blank")

        # --- Inject stealth patches via CDP (runs BEFORE any page JS) ---
        # Unlike page.evaluate(), addScriptToEvaluateOnNewDocument ensures
        # our patches are active when the WAF/anti-bot first evaluates the
        # browser fingerprint on navigation.
        #
        # The Page domain MUST be enabled first: without it Chrome accepts
        # Page.addScriptToEvaluateOnNewDocument and returns a script id, but the
        # script is silently never run on subsequent documents — so the whole
        # stealth layer was a no-op and Epic saw the raw llvmpipe/Linux
        # fingerprint. Verify this stays true after any nodriver/Chrome upgrade.
        page = self.page
        assert page is not None  # set by browser.get() above
        try:
            await page.send(uc.cdp.page.enable())
        except Exception as e:
            self.logger.debug("Page.enable failed: %s", e)
        try:
            await page.send(
                uc.cdp.page.add_script_to_evaluate_on_new_document(
                    source=self._STEALTH_JS,
                )
            )
            self.logger.debug("Stealth JS injected via CDP.")
        except Exception:
            # Fallback: inject directly on current page
            self.logger.debug("CDP injection failed, using evaluate fallback.")
            await self.page.evaluate(self._STEALTH_JS)

        self.log_browser_ready()
        return self.browser

    def log_browser_ready(self) -> None:
        """Standardised log for browser ready state."""
        self.logger.info("🌐 [bold yellow]Browser ready[/bold yellow]")

    def log_signed_in(self, username: str | None = None) -> None:
        """Standardised log for successful login."""
        user = username or self.user or "unknown"
        self.user = user
        self.logger.info("🔓 [bold green]Signed in as:[/bold green] %s", user)

    async def close_browser(self) -> None:
        """Gracefully close the browser."""
        if self.browser:
            self.browser.stop()

    # ------------------------------------------------------------------
    # Screenshot helper
    # ------------------------------------------------------------------

    def screenshot_path(self, *parts: str) -> Path:
        """Build a screenshot path inside ``data/screenshots/<store>/``."""
        p = cfg.screenshots_dir / self.store_name
        p.mkdir(parents=True, exist_ok=True)
        return p.joinpath(*parts)

    async def take_screenshot(self, name: str) -> Path | None:
        """Take a screenshot and return its path."""
        if not self.page:
            return None
        p = self.screenshot_path(f"{filenamify(name)}.png")
        try:
            await self.page.save_screenshot(str(p))
            self.logger.debug("Screenshot saved: %s", p)
            return p
        except Exception:
            self.logger.exception("Failed to save screenshot")
            return None

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    async def wait_for(self, selector: str, timeout: int | None = None) -> uc.Element | None:
        """Wait for an element matching the CSS selector to appear."""
        timeout = timeout or (cfg.timeout // 1000)
        try:
            element = await self.page.find(selector, timeout=timeout)
            return element
        except Exception:
            return None

    async def _human_challenge_present(self) -> bool:
        """True when the current page is showing a human-check we cannot solve.

        Covers hCaptcha / Arkose (FunCaptcha) / Cloudflare Turnstile / reCAPTCHA
        and DataDome. None of these can be answered automatically, so detecting
        one lets a store hand it to the user for a one-time solve over VNC
        instead of silently giving up. Only *visible, clickable* widgets count,
        so a hidden challenge frame does not produce a false positive.
        """
        if not self.page:
            return False
        try:
            return bool(await self.page.evaluate(CHALLENGE_JS))
        except Exception:
            return False

    async def _wait_out_challenge(
        self, label: str, *, settle: int = 12, present_fn=None, ask: bool = True
    ) -> bool:
        """Clear a human-check: let it auto-pass, else ask the user to solve it.

        Waits up to ``settle`` seconds for a managed/invisible challenge to clear
        on its own (so the user is not pinged needlessly). If it is still
        blocking, sends one VNC alert and polls until it clears or the login
        timeout is hit. ``present_fn`` lets a caller check somewhere other than
        the page itself, e.g. inside the checkout iframe. ``ask=False`` only
        waits for the auto-pass and never notifies, for a re-check on a
        challenge the user has already been told about. Returns True when the
        challenge is gone.
        """
        present = present_fn or self._human_challenge_present

        waited = 0
        while waited < settle:
            if not await present():
                return True
            await asyncio.sleep(2)
            waited += 2

        if not ask:
            return False

        self.logger.warning(
            "%s is behind a captcha human-check – requesting a manual solve via VNC.", label
        )
        target = ""
        if cfg.novnc_port:
            target = cfg.vnc_remote_url.rstrip("/") if cfg.vnc_remote_url else f"http://{cfg.vnc_ip}:{cfg.novnc_port}"
        custom_msg = (
            f"ACTION REQUIRED: {label} checkout needs human verification.\n"
            f"A captcha must be solved before the game can be claimed.\n"
            + (f"Open {target} from a device on Tailscale, solve it, and leave the browser open. "
               if target else "Open the FGC VNC window, solve it, and leave the browser open. ")
            + f"The claimer resumes automatically (waiting {cfg.vnc_login_timeout}s)."
        )

        async def _cleared() -> bool:
            return not await present()

        return await self._wait_for_vnc_login(_cleared, custom_msg=custom_msg)

    async def _wait_for_vnc_login(self, check_fn, *, timeout: int | None = None, interval: int = 5, log_interval: int = 60, custom_msg: str | None = None) -> bool:
        """Wait for manual VNC login.
        
        Polls every `interval` seconds, but only logs a waiting message every `log_interval` seconds.
        """
        timeout = timeout or cfg.vnc_login_timeout
        from src.core.notifier import notify
        
        if custom_msg:
            msg = custom_msg
            self.logger.info(custom_msg.replace("**", "").replace("!", ""))
        else:
            if cfg.novnc_port:
                if cfg.vnc_remote_url:
                    url = cfg.vnc_remote_url.rstrip("/")
                    self.logger.info("Open %s to login manually (waiting %ds).", url, timeout)
                    msg = (f"ACTION REQUIRED: {self.store_name} needs human verification.\n"
                           f"Open {url} from a device connected to Tailscale, complete the CAPTCHA/login, "
                           f"and leave the browser open. The claimer will resume automatically (waiting {timeout}s).")
                else:
                    self.logger.info("Open http://%s:%s to login manually (waiting %ds).", cfg.vnc_ip, cfg.novnc_port, timeout)
                    msg = f"ACTION REQUIRED: {self.store_name} manual login required. Open http://{cfg.vnc_ip}:{cfg.novnc_port} to login via VNC (waiting {timeout}s)."
            else:
                self.logger.info("Please login via VNC (waiting %ds).", timeout)
                msg = f"ACTION REQUIRED: {self.store_name} manual login required via VNC (waiting {timeout}s)."

        if cfg.notify_login_request:
            await notify(msg)

        elapsed = 0
        last_log = 0
        while elapsed < timeout:
            await asyncio.sleep(interval)
            elapsed += interval
            if await check_fn():
                return True
            
            if elapsed - last_log >= log_interval:
                last_log = elapsed
                remaining = timeout - elapsed
                if remaining > 0:
                    self.logger.info("Still waiting for login… %ds left.", remaining)
        return False

    async def sleep(self, seconds: float) -> None:
        """Async sleep wrapper."""
        await asyncio.sleep(seconds)

    # ------------------------------------------------------------------
    # Entry point (to be overridden)
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Override in subclasses to implement the claiming logic."""
        raise NotImplementedError
