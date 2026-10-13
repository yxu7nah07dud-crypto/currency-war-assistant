"""Parse official share text without guessing a guide identifier."""
import re


def normalize_share_code(value):
    text = str(value or "").strip().strip('`\"\'')
    wrapped = re.search(r"##\s*([A-Za-z0-9+/=\s]+?)\s*##", text)
    if wrapped:
        text = wrapped.group(1)
    else:
        for marker in ("攻略码：", "攻略码:", "分享码：", "分享码:", "Guide code:", "Code:", "code:", "攻略コード：", "攻略コード:"):
            if marker in text:
                text = text.split(marker, 1)[1]
                break
        text = text.split("##", 1)[0]
    return "".join(text.split()).strip('`\"\'')


def find_guide_by_code(guides, code):
    wanted = normalize_share_code(code)
    if not wanted:
        return None
    return next((g for g in guides if normalize_share_code(
        g.get("tourn_detail", {}).get("share_code", "")) == wanted), None)


def trait_hints(value, config):
    # Only the human-readable title before ## supplies supported search hints.
    title = str(value or "").split("##", 1)[0]
    if title == str(value or ""):
        return []
    traits = config.get("trait_info_list", [])
    if isinstance(traits, dict):
        traits = traits.values()
    return [str(t["trait_id"]) for t in traits
            if t.get("trait_id") is not None and len(t.get("trait_name", "")) >= 2
            and t["trait_name"] in title]
