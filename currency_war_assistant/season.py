"""Release compatibility for the standard mode of Currency Wars."""

ACTIVE = ("4.7", "2", "1")
DIRECTORY = "season-2-1-v4.7"
PENDING_RANK = "职级待确认"


def season_key(record):
    return tuple(str(record.get(field, "")) for field in
                 ("rpg_game_big_version", "season_id", "sub_season_id"))


def current_guide(guide, season):
    detail = guide.get("tourn_detail") or {}
    return not (guide.get("is_deleted") or detail.get("is_expired")
                or detail.get("is_sub_expired")) and season_key(detail) == season


def rank_label(rank, ordinal=None):
    return rank if ordinal is None else f"{rank}·{ordinal}"
