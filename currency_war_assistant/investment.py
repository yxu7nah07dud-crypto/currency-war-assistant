"""Conservative choice advice derived from current official effect descriptions.

No bundled game database or per-name tier list. Weights only order local advice;
they are never exposed as win probabilities. Unknown effects remain unranked.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import html
import re

from .localization import translate
from .models import normalize


def text(value):
    return html.unescape(re.sub(r"<[^>]+>", "", str(value or ""))).replace("\\n", "\n")


def ids(items):
    return {str(x.get("id", "")) if isinstance(x, dict) else str(x) for x in items}


@dataclass
class Choice:
    seen: object
    effect: str
    priority: int = 0
    reasons: list[str] = field(default_factory=list)
    limits: list[str] = field(default_factory=list)
    evidence: bool = False


def evaluate(catalog, state, match=None, locked=False,language="zh"):
    t=lambda key,**values:translate(language,key,**values)
    # An arbitrary top cached guide must not decide an unknown opening lineup.
    guide=match.guide if match and (locked or state.owned_ids()) else {}
    detail=guide.get("tourn_detail", {})
    final=next((s for s in detail.get("role_stages", []) if s.get("stage")=="Final"), {})
    target=ids(final.get("front_roles", [])+final.get("back_roles", [])) or state.owned_ids()
    bonds=Counter(b for role in target for b in catalog.role_bonds(role))
    result=[]
    for seen in state.investment_choices:
        if seen.zone!="待选" or seen.confidence<.8 or seen.kind not in ("环境","策略"):
            continue
        item=catalog.pool(seen.kind).get(seen.id)
        if not item:
            continue
        effect=text(item.get("desc", ""))
        choice=Choice(seen,effect)
        field_name="portals" if seen.kind=="环境" else "first_fight_augments"
        preferred=seen.id in ids(detail.get(field_name, []))
        secondary=seen.kind=="策略" and seen.id in ids(detail.get("second_fight_augments", []))
        if preferred or secondary:
            choice.priority+=80 if preferred else 55
            choice.evidence=True
            choice.reasons.append(t('investment_author_preferred' if preferred else 'investment_author_secondary',guide=t('investment_locked' if locked else 'investment_candidate')))
        if guide and effect:
            # Explicit prerequisites must be met by a confirmed choice, not by
            # merely recognizing a card on this screen.
            from .strategy import required_context
            if (seen.kind,seen.id) in required_context(guide,catalog):
                choice.priority+=120
                choice.evidence=True
                choice.reasons.append(t('investment_required'))
        if effect:
            relevant=[catalog.name(r,"角色") for r in target if len(normalize(catalog.name(r,"角色")))>=2
                      and normalize(catalog.name(r,"角色")) in normalize(effect)]
            related=[catalog.bonds[b].get("trait_name") or catalog.bonds[b].get("name", "")
                     for b,count in bonds.items() if b in catalog.bonds and count>=2]
            related=[b for b in related if len(normalize(b))>=2 and normalize(b) in normalize(effect)]
            if relevant:
                choice.priority+=22
                choice.evidence=True
                choice.reasons.append(t('investment_roles',names='、'.join(sorted(set(relevant)))))
                choice.limits.append(t('investment_roles_limit'))
            if related:
                choice.priority+=16
                choice.evidence=True
                choice.reasons.append(t('investment_bonds',names='、'.join(sorted(set(related)))))
            # Only affirmative resource benefits are generalized. Spending,
            # loss streaks and conditional triggers cannot become free rewards.
            money=bool(re.search(r"(?:获得|提供|给予|增加)[^。；]{0,24}(?:金币|利息)",effect))
            boxes=bool(re.search(r"(?:获得|拥有)[^。；]{0,22}(?:武装箱|装备箱)",effect))
            if money or boxes:
                choice.priority+=10
                choice.evidence=True
                choice.reasons.append(t('investment_money') if money else t('investment_equipment'))
                if boxes and re.search(r"第[二三2-3]位面",effect):
                    choice.limits.append(t('investment_delayed'))
            if re.search(r"(?:额外|一次|一个)[^。；]{0,10}投资策略",effect):
                choice.priority+=6
                choice.evidence=True
                choice.reasons.append(t('investment_extra'))
            if "星徽" in effect and not related:
                choice.limits.append(t('investment_emblem'))
            conditions=re.search(r"(?:每|累计|连胜|连败|消灭|花费|刷新\d|计数|穿戴|升星|参与|拥有\d|每陷入)",effect)
            if conditions:
                choice.priority-=5
                choice.limits.append(t('investment_conditional'))
            if "遭遇" in effect and "替换" in effect:
                choice.priority-=8
                choice.limits.append(t('investment_encounter'))
            if not choice.reasons:
                choice.reasons.append(t('investment_unmatched'))
        else:
            choice.limits.append(t('investment_unknown'))
        if match and guide and match.blocked:
            choice.limits.append(t('investment_other_missing'))
        result.append(choice)
    result.sort(key=lambda c:(c.priority,c.evidence,-c.seen.slot),reverse=True)
    return result


def advice(catalog,state,match=None,locked=False,language="zh"):
    t=lambda key,**values:translate(language,key,**values)
    choices=evaluate(catalog,state,match,locked,language)
    kind=t('investment_environment') if state.investment_kind=="环境" or any(s.kind=="环境" for s in state.investment_choices) else t('investment_strategy')
    if not choices:
        return [(kind,t('investment_no_cards'))]
    full=len(choices)==3
    prefix="" if full else t('investment_partial',count=(len(choices)))
    leader=choices[0]
    if leader.evidence and leader.priority>0 and (len(choices)<2 or leader.priority>choices[1].priority):
        header=t('main_pick') if full else t('investment_tentative')
        overview=t('investment_overview',header=header,name=leader.seen.name,reasons='; '.join(leader.reasons))
    else:
        overview=t('investment_no_leader')
    if not locked and not state.owned_ids():
        overview+=t('investment_generic')
    result=[(kind,prefix+overview)]
    for index,choice in enumerate(choices):
        position=t('investment_position',slot=(choice.seen.slot+1)) if choice.seen.slot>=0 else t('investment_position_unknown')
        body=t('investment_body',position=position,effect=choice.effect or t('pending'),reasons='; '.join(choice.reasons or [t('investment_check_effect')]))
        if choice.limits:
            body+=t('investment_limits',limits='; '.join(choice.limits))
        result.append((f"{index+1}. {choice.seen.name}",body))
    result.append((t('investment_after_heading'),t('investment_after')))
    return result
