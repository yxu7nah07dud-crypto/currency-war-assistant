"""Explainable local ranking and advice. Scores are compatibility, not win chances."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import html
import re

from .localization import translate,enum_label
from .models import Catalog, GameState, normalize
from .economy import RESERVE_GOLD,REFRESH_COST,TARGET_LEVEL_BY_COST,estimated_interest


def clean(text):
    return html.unescape(re.sub(r"<[^>]+>", "", str(text or ""))).replace("\\n", "\n")


def stages(guide):
    return guide.get("tourn_detail", {}).get("role_stages", [])


def stage_roles(guide, stage="Final"):
    stage_data = next((s for s in stages(guide) if s.get("stage") == stage), {})
    return stage_data.get("front_roles", []) + stage_data.get("back_roles", [])


def role_ids(guide, stage="Final"):
    return {str(r["id"]) for r in stage_roles(guide, stage)}


def core_ids(guide):
    detail = guide.get("tourn_detail", {})
    final = next((s for s in stages(guide) if s.get("stage") == "Final"), {})
    carries = final.get("carry_list", [])
    found = {str(x.get("id", "")) if isinstance(x, dict) else str(x) for x in carries}
    found |= {str(r["id"]) for r in stage_roles(guide) if r.get("is_carry")}
    if not found:
        fronts = final.get("front_roles", [])
        maximum = max((int(r.get("rarity", 1)) for r in fronts), default=1)
        found = {str(r["id"]) for r in fronts if int(r.get("rarity", 1)) == maximum}
    return found - {""}


def required_start(guide, catalog):
    """Only explicit prerequisite phrasing; mere mention of a hero is not a constraint."""
    text = clean(guide.get("description", ""))
    conditions = []
    patterns = [r"开局(?:确定|保证|必定|已经|必须|需要)[^。\n，,]{0,22}", r"(?:必须|需要先|只有)[^。\n，,]{0,16}(?:才能|才适合)"]
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            segment = normalize(match.group())
            for identifier, role in catalog.roles.items():
                name=normalize(role["name"])
                if len(name)>=2 and name in segment:
                    conditions.append(identifier)
    return set(conditions)


def required_context(guide,catalog):
    """Recognize only explicit mandatory investment/environment wording."""
    text=clean(guide.get('description',''))
    segments=re.findall(r'(?:必须(?:拿到|拥有|选择|有|获得)|需要先(?:拿到|获得|选择|有)|开局(?:必须|确定|已经)有|前提(?:是|为))[^。\n，,；;]{0,40}',text)
    required=set()
    for kind,pool in (('策略',catalog.strategies),('环境',catalog.environments)):
        for identifier,item in pool.items():
            name=normalize(item.get('name',''))
            if len(name)>=3 and any(re.search(re.escape(name)+r'(?![+A-Za-z0-9])',normalize(segment)) for segment in segments):
                required.add((kind,identifier))
    return required


def recipes(catalog, identifier):
    equipment = catalog.equipment.get(identifier, {})
    return [Counter(str(c["id"]) for c in recipe.get("childrens", [])) for recipe in equipment.get("compose_list", []) if recipe.get("childrens")]


def recommended_equipment(guide):
    result = []
    for role in stage_roles(guide):
        options = role.get("first_equipments") or role.get("second_equipments") or []
        for equipment in options:
            identifier = str(equipment.get("id", "")) if isinstance(equipment, dict) else str(equipment)
            if identifier:
                result.append((str(role["id"]), identifier))
    return result


def role_explanation(catalog,guide,identifier,stage,language="zh"):
    stage_data=next((s for s in stages(guide) if s.get('stage')==stage),{})
    position='Back' if any(str(r['id'])==identifier for r in stage_data.get('back_roles',[])) else 'Front'
    skill=next((s for s in catalog.roles.get(identifier,{}).get('skills',[]) if s.get('front_back_type')==position),{})
    stars=skill.get('skill_stars',[])
    desc=clean(stars[0].get('desc','')) if stars else ''
    if not desc:return ''
    return translate(language,'role_effect',zone=enum_label(language,'后台' if position=='Back' else '前台'),effect=desc[:150])


def equipment_explanation(catalog,identifier,language="zh"):
    description=clean(catalog.equipment.get(identifier,{}).get('desc',''))
    return translate(language,'gear_effect',effect=description[:150]) if description else ''


def _ids(items):
    return {str(x.get("id", "")) if isinstance(x, dict) else str(x) for x in items}


def target_level(guide, catalog):
    labels = guide.get("tourn_detail", {}).get("labels", [])
    text = " ".join(str(x) for x in labels) + " " + guide.get("title", "")
    match = re.search(r"([4-9]|10)级搜", text)
    if match:
        return int(match.group(1)), "搜牌"
    match = re.search(r"速升\s*([4-9]|10)", text)
    if match:
        return int(match.group(1)), "升级"
    cost = max((catalog.cost(r) for r in core_ids(guide)), default=1)
    return (TARGET_LEVEL_BY_COST.get(cost,9), "搜牌" if cost <=3 else "升级")


@dataclass
class Match:
    guide: dict
    score: float
    reasons: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    cautions: list[str] = field(default_factory=list)
    blocked: bool = False


class Adviser:
    def __init__(self, catalog: Catalog, language="zh"):
        self.catalog = catalog
        self.language = language

    def t(self,key,**values):
        return translate(self.language,key,**values)

    def match(self, guide, state: GameState):
        catalog = self.catalog
        t = self.t
        detail = guide.get("tourn_detail", {})
        if guide.get("is_deleted") or detail.get("is_expired") or detail.get("is_sub_expired"):
            return None
        final = role_ids(guide)
        if not final or final - catalog.roles.keys():
            return None
        owned = state.owned_ids()
        required = required_start(guide, catalog)
        context_required=required_context(guide,catalog)
        context_owned={('策略',s.id) for s in state.strategies if s.zone=='已选'}
        if state.environment and state.environment.zone=='已选':context_owned.add(('环境',state.environment.id))
        missing_context=context_required-context_owned
        core = core_ids(guide)
        current = role_ids(guide, state.stage()) or final
        weights = {r: 3 if r in core else 1 for r in current}
        overlap = owned & current
        role_score = 27 * sum(weights[r] for r in overlap) / max(1, sum(weights.values()))
        wanted_bonds = set().union(*(catalog.role_bonds(r) for r in current))
        have_bonds = set().union(*(catalog.role_bonds(r) for r in owned))
        role_score += 8 * len(wanted_bonds & have_bonds) / max(1, len(wanted_bonds))
        wanted_gear = {e for _, e in recommended_equipment(guide)}
        gear = Counter()
        for e in state.equipment:
            if e.confidence >= .8 and e.zone in ("库存", "已装备"):gear[e.id]+=e.copies
        compatible = 0
        for e in wanted_gear:
            if gear[e]:
                compatible += 1
            elif any(not (recipe - gear) for recipe in recipes(catalog, e)):
                compatible += .9
            elif any(set(recipe) & gear.keys() for recipe in recipes(catalog, e)):
                compatible += .3
        gear_score = 30 * compatible / max(1, len(wanted_gear))
        level, _ = target_level(guide, catalog)
        economy = 0
        if state.level is not None:
            economy += max(0, 12 - abs(level-state.level)*2)
        if state.gold is not None:
            missing_cost = sum(catalog.cost(r) for r in current - owned)
            economy += 8 * min(1, state.gold/max(1, missing_cost))
        augments = _ids(detail.get("first_fight_augments", [])) | _ids(detail.get("second_fight_augments", []))
        environments = _ids(detail.get("portals", []))
        context = (5 if any(s.id in augments and s.zone == "已选" for s in state.strategies) else 0)
        context += 5 if state.environment and state.environment.zone == "已选" and state.environment.id in environments else 0
        version = detail.get("rpg_game_big_version", "未知")
        freshness = 5 if version == catalog.version else 2
        score = role_score + gear_score + economy + context + freshness
        shop = {r.id for r in state.shop if r.confidence >= .8}
        if state.gold is not None:
            score += min(3, sum(1 for r in shop & (current-owned) if catalog.cost(r) <= state.gold))
        reasons = []
        missing = [catalog.name(r,"角色") for r in sorted((core | required)-owned)]
        missing += [t('missing_context',name=catalog.name(i,kind),kind=enum_label(self.language,kind)) for kind,i in sorted(missing_context)]
        cautions = []
        blocked = bool(required-owned or missing_context)
        if blocked:
            score = min(25, score-20)
            conditions=[catalog.name(r,"角色") for r in required-owned]+[t('missing_context',name=catalog.name(i,kind),kind=enum_label(self.language,kind)) for kind,i in missing_context]
            cautions.append(t('prerequisites_missing',conditions='、'.join(conditions)))
        if not owned:
            score = min(score, 10)
            cautions.append(t('owned_unknown'))
        if owned and not owned & (final | current):
            score = min(score, 12)
            cautions.append(t('transition_high'))
        if overlap:
            reasons.append(t('stage_owned',names='、'.join(catalog.name(r,'角色') for r in sorted(overlap))))
        if compatible:
            reasons.append(t('gear_compatible',count=(compatible)))
        if shop & (current-owned):
            reasons.append(t('shop_strengthening',names='、'.join(catalog.name(r,'角色') for r in shop & (current-owned))))
        if not state.equipment:
            cautions.append(t('gear_unknown'))
        if version != catalog.version:
            cautions.append(t('old_version',version=(version)))
        if not reasons:
            reasons.append(t('candidate_confirm'))
        return Match(guide, max(0, min(100, score)), reasons, missing, cautions, blocked)

    def rank(self, guides, state, locked_id=""):
        matched = [m for g in guides if (m := self.match(g, state)) is not None]
        matched.sort(key=lambda m: (not m.blocked, m.score, len(state.owned_ids() & role_ids(m.guide))), reverse=True)
        if locked_id:
            locked = next((m for m in matched if m.guide["id"] == locked_id), None)
            if locked:
                matched.remove(locked)
                matched.insert(0, locked)
        return matched[:3]

    def advice(self, state, match: Match | None, locked=False):
        c = self.catalog
        t = self.t
        if state.scene == "战斗":
            return [(t('current_heading'), t('battle_advice'))]
        if state.scene == "投资选择":
            from .investment import advice
            return advice(c,state,match,locked,self.language)
        if state.scene in ("未观察", "其他"):
            return [(t('current_heading'), t('open_shop_advice'))]
        if not match or not state.owned_ids():
            return [(t('confirm_heading'), t('confirm_owned_advice'))]
        g = match.guide
        current, final = role_ids(g, state.stage()), role_ids(g)
        core, owned = core_ids(g), state.owned_ids()
        result = []
        if match.blocked:
            result.append((t('prerequisite_heading'), t('blocked_advice',condition=match.cautions[0])))
        counts = Counter()
        for r in state.roles:
            if r.id in owned:
                counts[r.id] += (3 if r.star == 2 else 9 if r.star and r.star >=3 else 1) * r.copies
        candidates = []
        for r in state.shop:
            if r.confidence < .8 or r.id not in current | final or counts[r.id] >=9:
                continue
            if match.blocked and r.id not in owned:
                continue
            priority = (8 if r.id in core else 4 if r.id in current else 1) + (6 if counts[r.id] %3 ==2 else 0)
            if match.blocked and r.id not in current:
                priority -= 10
            candidates.append((priority, r, c.cost(r.id)))
        candidates.sort(key=lambda v:v[0], reverse=True)
        if candidates and candidates[0][0] > 0:
            _, r, price = candidates[0]
            reason = t('buy_pair_reason') if counts[r.id] %3 ==2 else t('buy_core_reason') if r.id in core else t('buy_stage_reason')
            explanation=role_explanation(c,g,r.id,state.stage(),self.language)
            if state.gold is None:
                result.append((t('buy_heading'), t('buy_unknown_gold',name=(r.name),price=(price),reason=(reason))))
            elif price <= state.gold:
                result.append((t('buy_heading'), t('buy_affordable',name=(r.name),price=(price),reason=(reason),remaining=(state.gold-price))))
            else:
                result.append((t('buy_heading'), t('buy_unaffordable',name=(r.name),price=(price))))
            if explanation:result[-1]=(result[-1][0],result[-1][1]+'\n'+explanation)
        else:
            result.append((t('buy_heading'), t('shop_no_targets') if state.shop else t('shop_incomplete')))
        available = Counter()
        for e in state.equipment:
            if e.confidence >= .8 and e.zone == "库存":
                available[e.id] += e.copies
        equipped = {(e.equipped_to,e.id) for e in state.equipment if e.zone == "已装备"}
        for r, e in recommended_equipment(g):
            if r not in owned or (r,e) in equipped:
                continue
            name = c.name(e,"装备")
            if available[e]:
                result.append((t('equipment'), t('equip_target',gear=(name),role=(c.name(r,"角色")))+equipment_explanation(c,e,self.language)))
                break
            complete = next((p for p in recipes(c,e) if not p-available), None)
            if complete:
                material = "＋".join(c.name(x,"装备")+(f"×{n}" if n>1 else "") for x,n in complete.items())
                result.append((t('combine_heading'), t('combine_target',materials=(material),gear=(name),role=(c.name(r,"角色")))+equipment_explanation(c,e,self.language)))
                break
        else:
            result.append((t('equipment'), t('gear_incomplete')))
        target, operation = target_level(g,c)
        if match.blocked:
            result.append((t('economy_heading'), t('economy_blocked')))
        elif state.gold is None or state.level is None:
            result.append((t('economy_heading'), t('economy_unknown',target=(target),operation=(enum_label(self.language,operation)))))
        elif state.hp is not None and state.hp <=25:
            result.append((t('economy_heading'), t('economy_low_hp')))
        elif state.level < target:
            result.append((t('economy_heading'), t('economy_level',target=(target),operation=(enum_label(self.language,operation)),refresh=(REFRESH_COST))))
        elif operation == "搜牌" and any(counts[r] <9 for r in core if c.cost(r)<=3):
            budget = max(0, state.gold-RESERVE_GOLD)
            result.append((t('economy_heading'), t('economy_search',reserve=(RESERVE_GOLD),budget=(budget))))
        else:
            result.append((t('economy_heading'), t('economy_reached',target=(target),gold=(state.gold),interest=(estimated_interest(state.gold)),refresh=(REFRESH_COST))))
        next_ids = sorted((current-owned) or (final-owned), key=lambda r:(r not in core,c.cost(r)))[:4]
        if next_ids:
            result.append((t('next_heading'), t('next_targets',names='、'.join(c.name(r,'角色') for r in next_ids))))
        return [(title,t('general_estimate',body=body) if title==t('economy_heading') else body) for title,body in result]
