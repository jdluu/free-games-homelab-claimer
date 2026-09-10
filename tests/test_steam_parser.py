from src.stores.steam import SteamClaimer


def parse(html: str) -> list[dict]:
    claimer = SteamClaimer.__new__(SteamClaimer)
    return claimer._parse_steamdb_html(html)


def card(badge: str, app_id: int, title: str) -> str:
    return (
        '<div class="span4 panel-sale">'
        f'<div class="cat {badge}"></div>'
        f'<a href="https://store.steampowered.com/app/{app_id}/test/"><b>{title}</b></a>'
        '</div>'
    )


def test_only_free_to_keep_cards_are_claimed():
    html = card("cat-play-for-free", 1, "Weekend Game") + card(
        "cat-free-to-keep", 2, "Permanent Game"
    )
    games = parse(html)
    assert [(g["app_id"], g["title"]) for g in games] == [("2", "Permanent Game")]


def test_footer_text_cannot_make_weekend_card_claimable():
    html = card("cat-play-for-free", 3, "Weekend Game") + (
        '<div class="cat cat-free-to-keep">What is Free to Keep?</div>'
    )
    assert parse(html) == []


def test_missing_structured_badge_is_skipped():
    html = (
        '<div class="span4 panel-sale">'
        '<a href="https://store.steampowered.com/app/4/test/"><b>Unknown</b></a>'
        'Free to Keep 100%'
        '</div>'
    )
    assert parse(html) == []
