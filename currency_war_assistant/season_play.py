"""Read and explain season 2 choices without interpreting offers as selections."""

import hashlib
import re

from .localization import translate
from .models import Seen, normalize
from .season import rank_label
from .season_data import DIVISIONS, PARTNERS, RANKS, SPOTLIGHT_DIFFICULTY, VOYAGE_EFFECT_KEYS


# Short labels describe rule facts and allow manual correction without an OCR match.
VOYAGE_LABELS = {
    102001: "从第一位面起挽救一次败局", 102002: "从第二位面起挽救一次败局",
    102003: "从第三位面起挽救一次败局", 102007: "各位面各挽救一次败局",
    102004: "第一位面茶歇可随机移除一项敌方词缀",
    102005: "第一位面茶歇可降低敌人难度", 102006: "第一位面茶歇可降低敌人星级",
    103001: "学习当前最高层羁绊并穿戴对应星徽",
    103002: "第二位面每次买经验额外加 1 点", 103004: "第三位面每次买经验额外加 1 点",
    103006: "第一位面茶歇记录上场员工并在后续提供复制",
    103007: "第二位面茶歇记录上场员工并在后续提供复制",
    103005: "第一位面茶歇后由伙伴刷新商店并买人",
    103008: "第二位面茶歇可引入汪汪丹",
    104001: "第一位面茶歇可选择咖啡效果", 104002: "第二位面茶歇可选择咖啡效果",
    104003: "第一位面茶歇可选特殊咖啡", 104004: "第二位面茶歇可选特殊咖啡",
    105001: "开局得坍缩奇点，连胜成长，败局减属性",
    105002: "备战黑洞格可把员工换成同费用员工",
    105003: "买下人才黑洞格员工后出现同费员工",
    105004: "买下人才黑洞格员工后按位面出现 3/4/5 费员工",
    105005: "机器人攻击全体并让本场伤害最高的员工立即行动",
    105006: "指定节点获得机械支援", 105007: "指定节点获得强化机械支援",
    106001: "投资策略节点提前", 106002: "投资策略节点提前", 106007: "投资策略节点提前",
    106005: "拉条未触发，获得补偿", 106006: "茶歇拉条未触发，获得补偿",
    106003: "第一位面茶歇可提前后续奖励节点", 106004: "第二位面茶歇可提前后续奖励节点",
    106008: "第一位面茶歇可提前后续补给", 106009: "第二位面茶歇可提前后续补给",
    107001: "第一位面茶歇可触发其他伙伴的随机效果",
    107002: "第一位面指定节点每 4 秒强制刷新商店，共 7 次",
    107003: "第二位面指定节点每 4 秒强制刷新商店，共 7 次",
    107004: "第三位面指定节点每 4 秒强制刷新商店，共 7 次",
    107005: "各位面首次刷新投资策略时提升品质",
    108001: "第一位面开始接委托", 108002: "第二位面开始接委托", 108003: "第三位面开始接委托",
    108004: "第一位面茶歇可接高难委托", 108005: "第二位面茶歇可接高难委托",
    109001: "第一位面补给装备改为星徽", 109002: "第一位面补给装备改为两枚随机星徽",
    109003: "第二位面补给装备改为星徽", 109004: "各位面补给改给 2 星员工",
    109005: "前两个位面补给改给 1 费 3 星员工",
    109006: "第一位面补给员工改为 4 费", 109007: "第二位面补给员工改为 5 费",
    110001: "各位面首次合成返还一件简易装备", 110002: "简易装备改由武装箱发放",
    110003: "补给中的员工改为装备箱", 110004: "补给中的员工改为装备箱",
    111001: "第一位面茶歇可提高强光环的出现机会并取消其加难",
    111002: "狂化节点改为弱化节点", 111004: "获得乱流简易装备",
    111005: "本局投资策略改造", 111003: "茶歇后战斗节点可能出现扑满",
    111006: "第一位面茶歇可额外选一次策略", 111007: "第二位面茶歇可额外选一次策略",
    112002: "第一位面茶歇可得 3 个实习生投影仪",
    112003: "第二位面茶歇可得 2 个员工投影仪",
    112004: "第三位面茶歇可得 1 个完美投影仪",
    112001: "首领前茶歇可得上场员工的 1 星复制",
    112005: "第二位面末个奖励节点换成珠珠鱼的宝库", 112006: "第三位面末个奖励节点换成珠珠鱼的宝库",
    112007: "第二位面末个奖励节点换成珠珠鱼的宝库", 112008: "第三位面末个奖励节点换成珠珠鱼的宝库",
}

VOYAGE_TIPS = {
    102: "voyage_protection", 103: "voyage_roster", 104: "voyage_choices",
    105: "voyage_roster", 106: "voyage_route", 107: "voyage_shop",
    108: "voyage_choices", 109: "voyage_supply", 110: "voyage_supply",
    111: "voyage_choices", 112: "voyage_supply",
}

def observe_rank(rows, shape):
    h, w = shape[:2]
    records = [r for r in rows if r["confidence"] >= .80 and r["box"][0] < .67*w
               and r["box"][1] < .68*h and not r["text"].startswith(("普通", "敌人难度"))]
    partial = None
    for row in records:
        label = row["text"].strip()
        for name, rank in RANKS.items():
            match = re.fullmatch(rf"(?:当前职级|对局难度)?\s*(?:{rank}\s*)?{name}\s*([0-9]{{1,2}})?", label)
            if not match:
                continue
            ordinal = int(match[1]) if match[1] else None
            if ordinal in DIVISIONS[rank]:
                return rank_label(rank, ordinal)
            if ordinal is None:
                partial = rank
        match = re.fullmatch(r"(A[0-8])\s*[·.\-:]\s*([0-9]{1,2})", label)
        if match and int(match[2]) in DIVISIONS[match[1]]:
            return rank_label(match[1],int(match[2]))
    return partial


def observe_voyage(rows):
    names = {name for name in PARTNERS if any(normalize(r["text"]) == name for r in rows)}
    if len(names) != 1:
        return None
    name = names.pop()
    target_ids = PARTNERS[name]
    labels = {VOYAGE_EFFECT_KEYS[i] for i in target_ids}
    for start in range(len(rows)):
        value = ""
        for row in rows[start:start+8]:
            value += "".join(c for c in normalize(row["text"]) if c.isalnum())
            key = hashlib.sha256(value.encode("utf8")).hexdigest()
            if key in labels:
                candidates = [i for i in target_ids if VOYAGE_EFFECT_KEYS[i] == key]
                if len(candidates)==1:
                    return Seen(str(candidates[0]), name, "奇遇", "已选", confidence=1)
    return Seen("", name, "奇遇", "已选", confidence=.9)


def spotlight_items(rows, catalog, shape, chosen=False):
    by_name = {}
    for identifier, item in catalog.spotlights.items():
        by_name.setdefault(normalize(item["name"]), []).append(identifier)
    roles = {}
    for identifier, item in catalog.roles.items():
        roles.setdefault(normalize(item["name"]), []).append(identifier)
    h, w = shape[:2]
    options = []
    for row in sorted(rows, key=lambda r: r["box"][0]):
        identifiers = by_name.get(normalize(row["text"]), ())
        if len(identifiers) != 1 or not .14*h < row["box"][1] < .85*h:
            continue
        left = (row["box"][0]+row["box"][2])/2
        nearby = {i for r in rows if abs((r["box"][0]+r["box"][2])/2-left)<.09*w
                  and abs(r["box"][1]-row["box"][1])<.24*h
                  and len(ids := roles.get(normalize(r["text"]), ()))==1 for i in ids}
        recipient = next(iter(nearby)) if len(nearby)==1 else ""
        if chosen and not recipient:
            continue
        identifier = identifiers[0]
        options.append(Seen(identifier,catalog.name(identifier,"主角光环"),"主角光环",
                            "已选" if chosen else "待选",confidence=row["confidence"],
                            box=row["box"],slot=len(options),equipped_to=recipient))
    return options


def advice(catalog, state, core, language):
    t = lambda key, **values: translate(language, key, **values)
    result = []
    if state.scene == "光环选择":
        from .encounter import active_affix_ids
        from .strategy import clean
        deployed = {r.id for r in state.roles if r.zone in ("前台","后台") and r.confidence>=.8}
        options = []
        for seen in state.spotlight_choices:
            entry = catalog.spotlights.get(seen.id)
            if not entry:
                continue
            fits = set(map(str, entry.get("suitable_role_list", ())))
            current = deployed & fits
            proposed = {seen.equipped_to} if seen.equipped_to in deployed else current
            priority = 2 if proposed & core & fits else 1 if proposed & fits else 0
            effect = clean(entry.get("desc", "")) or t("pending")
            if proposed & fits:
                names = "、".join(catalog.name(i,"角色") for i in sorted(proposed & fits))
                effect += "\n"+t("spot_fit", names=names)
            difficulty = SPOTLIGHT_DIFFICULTY.get(seen.id,0)
            if difficulty:
                effect += "\n"+t("spot_extra_difficulty",value=difficulty)
            options.append((priority, difficulty, seen.name, effect))
        options.sort(key=lambda entry: (-entry[0],entry[1]))
        result.append((t("spot_heading"),t("spot_compare") if options else t("spot_missing")))
        for index, (priority, difficulty, name, effect) in enumerate(options):
            best = index==0 and priority>0 and len(options)>1 and (
                priority,-difficulty) > (options[1][0],-options[1][1])
            result.append((t("spot_preferred", name=name) if best and len(options)>1 else name, effect))
        if 4037 in active_affix_ids(state.debuffs,True):
            result.append((t("spot_heading"),t("enc_tip_spotlight")))
    if state.voyage:
        identifier = int(state.voyage.id) if state.voyage.id.isdigit() else 0
        known = VOYAGE_LABELS.get(identifier)
        description = known or t("voyage_effect_missing")
        if known and identifier//1000 in VOYAGE_TIPS:
            description += "\n"+t(VOYAGE_TIPS[identifier//1000])
        result.append((t("voyage_context", name=state.voyage.name),description))
    for plane, seen in sorted(state.spotlights.items()):
        name = catalog.name(seen.equipped_to,"角色")
        from .strategy import clean
        effect = clean(catalog.spotlights.get(seen.id,{}).get("desc","")) or t("pending")
        result.append((t("spot_selected", plane=plane, name=name, effect=seen.name),effect))
    return result
