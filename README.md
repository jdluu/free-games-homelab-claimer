# free-games-claimer-remaster

## Personal fork additions

This personal homelab fork retains the upstream functionality while adding targeted reliability improvements: a structured Steam **Free to Keep** parser that avoids temporary free-weekend offers, persistent tracking of claimed and skipped Steam entitlements, automatic handling of free DLC whose base game is free, BWS-backed runtime credentials, and a pinned GHCR deployment with health checks and automatic restarts. Interactive login support can notify Discord with a private noVNC link; the device opening it must be connected to the Tailscale tailnet.

---

<p align="center">
  <img alt="logo-free-games-claimer" src="https://user-images.githubusercontent.com/493741/214588518-a4c89998-127e-4a8c-9b1e-ee4a9d075715.png" />
</p>

> **Not a fork** – a complete ground-up Python remaster inspired by [vogler/free-games-claimer](https://github.com/vogler/free-games-claimer). 
>
> ℹ️ **Are you coming from the original Node.js version?**  
> For a comprehensive, file-by-file breakdown of what changed, dropped features, stealth automation upgrades, and architectural differences, **please read [MODIFICATIONS.md](./MODIFICATIONS.md).**

Automatically claims free games on:

- <img alt="logo steam" src="https://store.steampowered.com/favicon.ico" width="20" align="middle" /> **Steam** – via [SteamDB](https://steamdb.info/upcoming/free/) scraping (only *Free to Keep*, not *Play for Free*)
- <img alt="logo epic-games" src="https://github.com/user-attachments/assets/82e9e9bf-b6ac-4f20-91db-36d2c8429cb6" width="20" align="middle" /> **Epic Games Store** – weekly free games
- <img alt="logo prime-gaming" src="https://github.com/user-attachments/assets/7627a108-20c6-4525-a1d8-5d221ee89d6e" width="20" align="middle" /> **Amazon Prime Gaming** – monthly Prime Gaming catalogue + GOG key redemption
- <img alt="logo gog" src="https://github.com/user-attachments/assets/49040b50-ee14-4439-8e3c-e93cafd7c3a5" width="20" align="middle" /> **GOG** – periodic free giveaways

**Gamerpower API** routing to indirect stores:
- <img alt="logo fanatical" src="https://www.fanatical.com/favicon.ico" width="20" align="middle" /> **Fanatical** – auto-bypasses cookie banners and hooks Steam accounts to grab weekly PC drops.
- <img alt="logo itchio" src="https://itch.io/favicon.ico" width="20" align="middle" /> **Itch.io** – DRM-free indie giveaways
- <img alt="logo indiegala" src="https://www.indiegala.com/favicon.ico" width="20" align="middle" /> **IndieGala** – free Steam keys & DRM-free games
- <img alt="logo alienware" src="https://www.alienwarearena.com/favicon.ico" width="20" align="middle" /> **Alienware Arena** – (Notify-only) ARP point giveaways

Runs as a Docker container with a built-in scheduler (every 12 hours by default, with optional fixed daily run times). Login via **VNC in browser** or automated credentials. If Epic presents hCaptcha, Discord can request manual verification through the private noVNC interface; the phone, laptop, or PC opening that link must be connected to Tailscale.

---

## Quick start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose

> 🟢 **New to Docker on Windows?** Read the step-by-step [**WINDOWS_BEGINNER_GUIDE.md**](./WINDOWS_BEGINNER_GUIDE.md) to set up Docker Desktop, optimize RAM limits, and use Dockhand to deploy this flawlessly.

### 1. Clone and configure

```bash
git clone https://github.com/P-Adamiec/free-games-claimer-remaster.git
cd free-games-claimer-remaster
cp .env.example .env  # or edit the existing .env
```

Edit `.env` with your credentials:

```ini
# Epic Games
EG_EMAIL=your@email.com
EG_PASSWORD=your_password

# Prime Gaming (Amazon)
PG_EMAIL=your@email.com
PG_PASSWORD=your_password

# GOG
GOG_EMAIL=your@email.com
GOG_PASSWORD=your_password

# Steam
STEAM_USERNAME=your_username
STEAM_PASSWORD=your_password

# Notifications
DISCORD_WEBHOOK=https://discord.com/api/webhooks/...

# Run only specific stores (comma-separated)
# Leave commented to run ALL
# STORES=steam,prime,gog
```

### 2. Run container

```bash
docker compose up -d
```

> 💡 **Want to test experimental development features?** Add `FGC_TAG=dev` to your `.env` file before running Docker to automatically download our pre-release build!

### 3. Login (first run)

Open **http://localhost:7080** in your browser to access the VNC session.

Each store will wait for you to login manually on the first run if you don't supply credentials. After that, session cookies are natively restored using persistent browser profiles!

### 4. Monitor

To see what the bot is doing in real-time regardless of your current terminal folder, inspect the container directly:
```bash
docker logs -f fgc-remaster
```

---

## Configuration

Options are set via environment variables in `.env`:

| Variable | Default | Description |
|---|---|---|
| `FGC_TAG` | `latest` | Docker image tag to run (set to `dev` to test experimental pre-release builds). |
| `SHOW` | `1` | Show browser window (VNC). |
| `WIDTH` | `1280` | Browser/VNC screen width. |
| `HEIGHT` | `720` | Browser/VNC screen height. |
| `NOVNC_PORT` | `7080` | noVNC web access port. |
| `VNC_IP` | `localhost`| Custom IP/Hostname for VNC notification links. |
| `SCHEDULER_HOURS`| `12` | Hours interval for the built-in scheduler runs. |
| `SCHEDULER_TIMEZONE` | `UTC` | IANA timezone used for fixed daily scheduler times. |
| `SCHEDULER_FIXED_TIMES` | | Optional comma-separated daily run times in 24-hour `HH:MM` format. Example: `17:00,21:30`. |
| `SCHEDULER_STORE_TIMES` | | Optional store-specific fixed daily run times. Example: `epic=17:10,22:30;steam=19:10,22:30;gog=10:10,14:10,17:10,21:10`. |
| `RUN_ON_STARTUP` | `true` | Run once immediately when the container/application starts. |
| `VNC_LOGIN_TIMEOUT`| `180` | Seconds to wait for you to log in via VNC manually. |
| `EG_EMAIL` | | Epic Games login email. |
| `EG_PASSWORD` | | Epic Games login password. |
| `EG_OTPKEY` | | Epic Games 2FA OTP key. |
| `EG_PARENTALPIN` | | Epic Games Parental Controls PIN. |
| `PG_EMAIL` | | Prime Gaming (Amazon) email. |
| `PG_PASSWORD` | | Prime Gaming password. |
| `PG_OTPKEY` | | Prime Gaming 2FA OTP key. |
| `PG_FORCE_CHECK_COLLECTED` | `0` | Force re-check already marked 'claimed' games. |
| `PG_REDEEM` | `0` | Try to redeem keys automatically on external stores. |
| `GOG_EMAIL` | | GOG login email. |
| `GOG_PASSWORD` | | GOG login password. |
| `GOG_NEWSLETTER` | `0` | Keep newsletter sub after claiming (1 = keep). |
| `GOG_FORCE_REDEEM` | `0` | Force re-redeem old GOG codes from Prime Gaming. |
| `GOG_OTP_ENABLE` | `false`| Use backup codes for GOG 2FA. |
| `GOG_OTP_CODES` | | Comma-separated list of GOG backup codes. |
| `STEAM_USERNAME` | | Steam username. |
| `STEAM_PASSWORD` | | Steam password. |
| `STORES` | *(all)* | Comma-separated list of stores to run. |
| `RESET_DB_GAMES` | `false` | Retroactively erase any database claims recorded within the last 7 days upon execution. Assists in clearing false positives. |
| `FANATICAL_ENABLE`| `false`| Enable Fanatical claiming via GamerPower. |
| `FANATICAL_EMAIL` | | Fanatical account email. |
| `FANATICAL_PASSWORD`| | Fanatical account password. |
| `ALIENWARE_ENABLE`| `false`| Enable Alienware Arena notifications via GamerPower. |
| `ITCHIO_ENABLE`| `false`| Enable Itch.io claiming via GamerPower. |
| `ITCHIO_EMAIL` | | Itch.io account email. |
| `ITCHIO_PASSWORD` | | Itch.io account password. |
| `INDIEGALA_ENABLE`| `false`| Enable IndieGala claiming via GamerPower. |
| `INDIEGALA_EMAIL` | | IndieGala account email. |
| `INDIEGALA_PASSWORD`| | IndieGala account password. |
| `UNKNOWN_STORES_ENABLE`| `false`| Open unsupported external stores for manual claiming via VNC. |
| `BROWSER_DIR` | `data/browser` | Browser profile directory (persists cookies/sessions). |
| `DEBUG` | `0` | Shows verbose actions the bot takes. |
| `DRYRUN`| `0` | Click "claim" buttons but do not submit / perform final purchase. |
| `DISCORD_WEBHOOK` | | Discord webhook URL for notifications. |
| `NOTIFY_ERRORS_ONLY` | `0` | Set to 1 to suppress successful claims; keep enabled error and action alerts. |
| `NOTIFY_SUMMARY` | `1` | Set to 0 to disable successful claim summaries (failures remain independent). |
| `NOTIFY_ERRORS` | `1` | Set to 0 to disable fatal error alerts. |
| `NOTIFY_CLAIM_FAILS`| `1` | Set to 0 to disable alerts for unclaimable games. |
| `NOTIFY_MISSING_BASE` | `1` | Set to 0 to hide missing-base-game failures only (Steam and Epic Games). |
| `NOTIFY_LOGIN_REQUEST`| `1` | Set to 0 to disable VNC login request pings. |

### Scheduler

The application can run on an interval and optionally at fixed daily times.

```ini
SCHEDULER_HOURS=12
SCHEDULER_TIMEZONE=UTC
SCHEDULER_FIXED_TIMES=17:00,21:30
SCHEDULER_STORE_TIMES=epic=17:10,22:30;steam=19:10,22:30;gog=10:10,14:10,17:10,21:10
RUN_ON_STARTUP=true
```

`SCHEDULER_HOURS` runs the claim process every configured number of hours.

`SCHEDULER_FIXED_TIMES` adds optional daily runs at specific 24-hour `HH:MM` times. Multiple times can be separated by commas. This is useful for running shortly after known free-game release windows.

`SCHEDULER_STORE_TIMES` adds optional daily runs for individual stores. This is useful when each store has different release windows. Multiple times per store can be separated by commas. Store names use the same aliases as `STORES`.

`SCHEDULER_TIMEZONE` controls the timezone used for fixed daily times. Use an IANA timezone name. Examples: `Europe/Berlin`, `America/New_York`, `Asia/Tokyo`. See the IANA Time Zone Database or Python `zoneinfo` documentation for valid names. Local wall-clock schedules follow the configured timezone, including DST transitions.

Example for Germany:

```ini
SCHEDULER_TIMEZONE=Europe/Berlin
SCHEDULER_FIXED_TIMES=17:00
```

This runs once per day at 17:00 Berlin time. If `SCHEDULER_HOURS` is also configured, interval runs continue as well.

### Selective module execution

Run only specific stores using accepted module aliases (`steam`, `epic`, `prime`, `gog`, `amazon`):

```bash
# Method 1: Via environment variable (recommended)
# Edit .env: STORES=steam,amazon

# Method 2: Temporary execution via Docker Compose
STORES=epic,gog docker compose up -d

# Method 3: One-off immediate run inside Docker (ignores scheduler)
docker compose run --rm app python main.py steam gog --once
```

---

## Architecture

```
free-games-claimer-remaster/
├── main.py                 # Entry point + scheduler + CLI
├── docker-compose.yml      # Container configuration
├── Dockerfile              # Ubuntu + Chrome + TurboVNC + Python
├── MODIFICATIONS.md        # Codebase overhaul technical reference
├── WINDOWS_BEGINNER_GUIDE.md
├── .env                    # Your local configuration (gitignored)
├── .env.example            # Configuration template
└── src/
    ├── version.py          # Version string
    ├── core/               # Shared engine components
    │   ├── claimer.py      # BaseClaimer & CDP stealth patches
    │   ├── config.py       # Typed configuration loader (.env → Python)
    │   ├── database.py     # SQLAlchemy models & SQLite engine
    │   └── notifier.py     # Modular Discord/Apprise webhooks
    └── stores/             # Store-specific claiming modules
        ├── epic.py         # Epic Games Store
        ├── prime.py        # Amazon Prime Gaming
        ├── gog.py          # GOG (+ GOG code redemption from Prime)
        ├── steam.py        # Steam (SteamDB scraping)
        └── gamerpower.py   # GamerPower API (Fanatical, Itch.io, IndieGala, Alienware)
```

### How it works

1. **Scheduler** (`main.py`) runs on the configured interval and optional fixed daily times
2. Each store module **starts its own browser** with an isolated profile, securely recalling session cookies (`--restore-last-session`).
3. **Login detection** checks the page DOM (not just cookies/DB).
4. **Stealth profiles** are injected via `nodriver` directly via Official Chrome binaries before any page loads.
5. **Game discovery** utilizes specialized scrapers (like reading SteamDB to circumvent typical lists).
6. **Robust Database Storage** verifies historical success in `fgc.db` (SQLite) to block aggressive overlapping.
7. **Clean Notifications** dispatch to you dynamically based on the toggles configured in the `.env` settings.

---

## Notifications

Set `DISCORD_WEBHOOK` in `.env` for Discord notifications about claimed games and errors. Game results start directly with one plain-text line per game, for example:

```text
Luftrausers - Claimed - Epic Games
Astral Ascent - Claimed - Epic Games
```

Failures show their actual status, such as `Game title - Failed - Epic Games`, and manual steps use `Action required`, without a success headline or duplicate store heading. Already owned and skipped games remain silent.

Keep `NOTIFY_ERRORS_ONLY=0` (the default) while monitoring successful claims. Later, set `NOTIFY_ERRORS_ONLY=1` in `.env` and restart/recreate the service to receive only problems and required actions, including manual login requests. Leave `NOTIFY_ERRORS`, `NOTIFY_CLAIM_FAILS`, and `NOTIFY_LOGIN_REQUEST` enabled for these alerts. These individual flags still control their respective categories; `NOTIFY_SUMMARY=0` only suppresses successful results. Discord and Apprise use the same filtering.

For other services, [apprise](https://github.com/caronc/apprise) natively supports sending to Telegram, Slack, Matrix and more – just set the `NOTIFY` variable!

To silence repeated DLC failures caused by a missing base game, set `NOTIFY_MISSING_BASE=false` and keep `NOTIFY_CLAIM_FAILS=true`. This excludes Steam's `failed:missing_base` and Epic's equivalent missing-base statuses from notifications. Other failures and successful claims still follow their usual settings, including in errors-only mode. The default is `true`; this filter does not enable alerts disabled by other flags. It only affects notifications: DLC checks are still retried, so acquiring the base game can allow a later claim. Restart/recreate the service after changing the environment.

Notification regression tests run without sending real messages or opening a browser:

```bash
python -m unittest discover -s tests -v
```

Use Python 3.11, matching CI and the Docker base image. The current `nodriver 0.50.3` package fails to import under Python 3.14 because of an [upstream source-encoding issue](https://github.com/ultrafunkamsterdam/nodriver/issues/35). The notification test workflow runs on pushes and pull requests affecting the application or tests.


---

## Troubleshooting

| Issue | Solution |
|---|---|
| Store not logging in | Open VNC (`http://localhost:7080`) and login manually. Your credentials or session logic persist beautifully after first login. |
| Steam game not detected | Check that the game is listed on [SteamDB Free](https://steamdb.info/upcoming/free/). |
| GamerPower missing games | Certain platforms (Itch.io, IndieGala, Alienware, Fanatical) require explicit `{STORE}_ENABLE=true` toggles in configuration to activate their respective handlers. |
| Epic captcha | The stealth patches prevent 99% of captchas. EU 'Right of withdrawal' overlays are automatically accepted. If a rigorous manual prompt arrives, solve it once via VNC. |
| False positive claims | Set `RESET_DB_GAMES=true` in your `.env`, reboot the container, and the bot will forget the last 7 days of claims, allowing the logic to try claiming them again. |
| Container crashes on start | Check logs: `docker compose logs app --tail=50`. A clean restart purges `.X1-lock` bugs. |

---

## Credits

Inspired by [vogler/free-games-claimer](https://github.com/vogler/free-games-claimer) – the original Node.js project.
This remaster is a **completely independent rewrite** in Python, not a fork.

---

## License

[AGPL-3.0](./LICENSE)

---

## Analytics

[![Star History Chart](https://api.star-history.com/svg?repos=P-Adamiec/Free-Games-Claimer-Remaster&type=Date)](https://www.star-history.com/?repos=P-Adamiec%2FFree-Games-Claimer-Remaster&type=date&legend=bottom-right)

![Alt](https://repobeats.axiom.co/api/embed/5c6416eef2d3371808c7d1d50418546103b351f4.svg "Repobeats analytics image")

---

<p align="center">
<img alt="logo-fgc-remaster" src="logo.png" width="256" />
</p>
