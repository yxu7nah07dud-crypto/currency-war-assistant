"""Explainable local ranking and advice. Scores are compatibility, not win chances."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import html
import re

from .models import Catalog, GameState, normalize


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
    text = guide.get("description", "")
    conditions = []
    patterns = [r"开局(?:确定|保证|必定|已经|必须|需要)[^。\n，,]{0,22}", r"(?:必须|需要先|只有)[^。\n，,]{0,16}(?:才能|才适合)"]
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            segment = normalize(match.group())
            for identifier, role in catalog.roles.items():
                if normalize(role["name"]) in segment:
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


def role_explanation(catalog,guide,identifier,stage):
    stage_data=next((s for s in stages(guide) if s.get('stage')==stage),{})
    position='Back' if any(str(r['id'])==identifier for r in stage_data.get('back_roles',[])) else 'Front'
    skill=next((s for s in catalog.roles.get(identifier,{}).get('skills',[]) if s.get('front_back_type')==position),{})
    stars=skill.get('skill_stars',[])
    desc=clean(stars[0].get('desc','')) if stars else ''
    if not desc:return ''
    return ('后台' if position=='Back' else '前台')+'作用：'+desc[:150]


def equipment_explanation(catalog,identifier):
    description=clean(catalog.equipment.get(identifier,{}).get('desc',''))
    return ' 当前效果：'+description[:150] if description else ''


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
    return ({1:5,2:6,3:7,4:9,5:9}.get(cost,9), "搜牌" if cost <=3 else "升级")


@dataclass
class Match:
    guide: dict
    score: float
    reasons: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    cautions: list[str] = field(default_factory=list)
    blocked: bool = False


class Adviser:
    def __init__(self, catalog: Catalog):
        self.catalog = catalog

    def match(self, guide, state: GameState):
        catalog = self.catalog
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
        missing = [catalog.name(r) for r in sorted((core | required)-owned)]
        missing += [catalog.name(i)+'（'+kind+'需确认已选）' for kind,i in sorted(missing_context)]
        cautions = []
        blocked = bool(required-owned or missing_context)
        if blocked:
            score = min(25, score-20)
            conditions=[catalog.name(r) for r in required-owned]+[catalog.name(i)+'（'+kind+'需确认已选）' for kind,i in missing_context]
            cautions.append("必需前提未满足：" + "、".join(conditions))
        if not owned:
            score = min(score, 10)
            cautions.append("已持有角色还未确认，当前仅供候选参考")
        if owned and not owned & (final | current):
            score = min(score, 12)
            cautions.append("现有角色与目标阵容没有直接衔接，转型成本高")
        if overlap:
            reasons.append("本阶段已有 " + "、".join(catalog.name(r) for r in sorted(overlap)))
        if compatible:
            reasons.append(f"已有装备或材料可衔接 {compatible:g} 项目标装备")
        if shop & (current-owned):
            reasons.append("当前商店有补强角色：" + "、".join(catalog.name(r) for r in shop & (current-owned)))
        if not state.equipment:
            cautions.append("装备库存尚未确认，装备适配分暂不计入")
        if version != catalog.version:
            cautions.append(f"作者版本 {version}；已核对角色可用性，正文中的旧倍率需按现行规则确认")
        if not reasons:
            reasons.append("可用的攻略候选；确认角色、装备和经济后再决定")
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

    def advice(self, state, match: Match | None):
        c = self.catalog
        if state.scene == "战斗":
            return [("当前", "战斗进行中，保留阵容记录；准备阶段再更新买人和经济建议。")]
        if state.scene in ("未观察", "其他", "投资选择"):
            if state.scene == "投资选择" and match:
                wanted = _ids(match.guide.get("tourn_detail", {}).get("first_fight_augments", []))
                candidates = [s.name for s in state.strategies if s.zone == "待选" and s.id in wanted]
                if candidates:
                    return [("投资", "作者优选中当前可选：" + "、".join(candidates) + "。结合具体效果和现有队伍选择。")]
            return [("当前", "请停留在货币战争准备界面并打开商店；投资页面中的选项需确认是否已选。")]
        if not match or not state.owned_ids():
            return [("先确认", "确认已持有角色与库存装备后生成建议。可以在“识别纠正”中补充未显示的角色。")]
        g = match.guide
        current, final = role_ids(g, state.stage()), role_ids(g)
        core, owned = core_ids(g), state.owned_ids()
        result = []
        if match.blocked:
            result.append(("阵容前提", match.cautions[0] + "；暂不为该攻略花钱搜核心，查看备选。"))
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
            reason = "可补齐升星份数" if counts[r.id] %3 ==2 else "是攻略核心" if r.id in core else "能补本阶段阵容"
            explanation=role_explanation(c,g,r.id,state.stage())
            if state.gold is None:
                result.append(("买人", f"优先关注 {r.name}（{price}费），{reason}；金币待确认，先核对是否买得起。"))
            elif price <= state.gold:
                result.append(("买人", f"优先买 {r.name}（{price}金币），{reason}。买后余 {state.gold-price}；其他目标按现有格位购买。"))
            else:
                result.append(("买人", f"目标 {r.name} 需要 {price}金币，目前不足；可以手动锁店等待收入。"))
            if explanation:result[-1]=(result[-1][0],result[-1][1]+'\n'+explanation)
        else:
            result.append(("买人", "当前确认的商店没有明显的阵容补强；不为无关角色消耗金币。" if state.shop else "商店未读取完整，请打开商店或纠正五个商店格位。"))
        available = Counter()
        for e in state.equipment:
            if e.confidence >= .8 and e.zone == "库存":
                available[e.id] += e.copies
        equipped = {(e.equipped_to,e.id) for e in state.equipment if e.zone == "已装备"}
        for r, e in recommended_equipment(g):
            if r not in owned or (r,e) in equipped:
                continue
            name = c.name(e)
            if available[e]:
                result.append(("装备", f"可将 {name} 给 {c.name(r)}：这是作者的优选装备。核对该角色空余装备格。"+equipment_explanation(c,e)))
                break
            complete = next((p for p in recipes(c,e) if not p-available), None)
            if complete:
                material = "＋".join(c.name(x)+(f"×{n}" if n>1 else "") for x,n in complete.items())
                result.append(("合成", f"{material} → {name}，优先考虑给 {c.name(r)}。配方来自当前官方配置。"+equipment_explanation(c,e)))
                break
        else:
            result.append(("装备", "尚未确认可完成的目标装备；打开装备详情或补充库存，再判断给谁和是否合成。"))
        target, operation = target_level(g,c)
        if match.blocked:
            result.append(("经济", "攻略必需前提缺失，保留金币；先选适配备选或补充确认信息，再决定升级和刷新。"))
        elif state.gold is None or state.level is None:
            result.append(("经济", f"金币或等级待确认。该攻略运营方向：{target}级{operation}；暂不建议具体花费。"))
        elif state.hp is not None and state.hp <=25:
            result.append(("经济", "生命已低于25，先补当前阵容质量，优先购买可升星或立刻上场的角色；不要为了长期利息忽略眼前战斗。"))
        elif state.level < target:
            result.append(("经济", f"目标 {target}级{operation}。先存钱并升级；仅买阵容补强，避免低等级反复花2金币刷新搜高费核心。"))
        elif operation == "搜牌" and any(counts[r] <9 for r in core if c.cost(r)<=3):
            budget = max(0, state.gold-50)
            result.append(("经济", f"已到搜牌等级；正常经济下先保留50金币，以超出部分搜核心。当前保留50后可用 {budget}金币。投资有特殊利息规则时需按其效果调整。"))
        else:
            result.append(("经济", f"已达到{target}级。先补核心和关键羁绊；正常经济下 {state.gold}金币约产生 {min(5,state.gold//10)}利息，刷新每次花2金币。特殊投资规则会改变收益。"))
        next_ids = sorted((current-owned) or (final-owned), key=lambda r:(r not in core,c.cost(r)))[:4]
        if next_ids:
            result.append(("下一步", "补强目标：" + "、".join(c.name(r) for r in next_ids)))
        return result
