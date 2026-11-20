"""Explain the effects recorded in each supported season's tables."""
from collections import Counter

from .encounter_data import AFFIXES, ENEMY_SCALING, RULE_VERSION, TRAIT_THRESHOLDS
from .localization import translate
from .models import normalize
from . import season_data

# Rule ID -> authored effect template and operational implication. The same
# template is reused for rules that only differ in their numerical parameters.
RULES = {
    1001: ('strength', 'tempo'), 1002: ('strength', 'tempo'),
    1003: ('strength', 'tempo'), 1004: ('strength', 'tempo'), 1005: ('strength', 'tempo'),
    1006: ('strength', 'tempo'), 1007: ('strength', 'tempo'),
    1008: ('strength', 'tempo'), 1009: ('strength', 'tempo'),
    2002: ('delay', 'delay'), 2003: ('empty_gear', 'gear'),
    2004: ('revenge', 'revenge'), 2005: ('first_advance', 'advance'),
    2006: ('bully', 'stars'),
    3001: ('shutdown', 'shutdown'), 3002: ('shutdown', 'shutdown'),
    3003: ('three_gear', 'gear'), 3007: ('leader', 'leader'),
    3004: ('timers', 'timer'), 3005: ('timers', 'timer'),
    3006: ('fatal_freeze', 'freeze'), 3008: ('survival', 'survival'),
    4011: ('luck', 'luck'), 4010: ('hp_advance', 'advance'),
    4001: ('hit_advance', 'advance'), 4002: ('counter', 'counter'),
    4003: ('energy', 'energy'), 4005: ('sustain', 'sustain'),
    4006: ('cleanse', 'cleanse'), 4007: ('sp_freeze', 'sp_freeze'),
    4008: ('sync', 'sync'), 4009: ('trauma', 'health'),
    4012: ('burn', 'burn'), 4013: ('assassin', 'timer'),
    4015: ('speed', 'speed'), 4016: ('trap', 'control'),
    4017: ('heal', 'heal'), 4018: ('exp_cost', 'exp_cost'),
    4019: ('trash', 'trash'),
    40140: ('shutdown', 'shutdown'), 40141: ('shutdown', 'shutdown'),
    40142: ('shutdown', 'shutdown'), 40143: ('shutdown', 'shutdown'),
    40144: ('shutdown', 'shutdown'), 40145: ('shutdown', 'shutdown'),
    40146: ('shutdown', 'shutdown'),
    4020: ('start_hp', 'health'), 4021: ('unbroken', 'break'),
    4022: ('mitigation', 'mitigation'), 4023: ('base_damage', 'base_damage'),
    4024: ('star_damage', 'stars'), 4025: ('cost_damage', 'cost'),
    4026: ('rust', 'rust'), 4027: ('inactive_traits', 'traits'),
    4028: ('cost_damage', 'cost'),
}
NAME_IDS = {normalize(name): identifier for identifier, (name, _) in AFFIXES.items()}
SEASON_NAMES = {normalize(name): identifier for identifier, (name, _) in season_data.AFFIXES.items()}
SEASON_RULES = {**RULES,
    4029: ('overheat', 'freeze'), 4030: ('break_advance', 'tempo'),
    4031: ('memosprite_time', 'timer'), 4032: ('punchline_loss', 'tempo'),
    4033: ('repeat_shutdown', 'tempo'), 4034: ('siege', 'tempo'),
    4035: ('hp_assassin', 'health'), 4036: ('frenzy', 'tempo'),
    4037: ('spotlight_damage', 'spotlight'), 4039: ('refresh_price', 'refresh_price'),
    4040: ('sold_out', 'sold_out'), 4041: ('absorption', 'tempo'),
}


def rule_id(name, seasonal=False):
    return (SEASON_NAMES if seasonal else NAME_IDS).get(normalize(name))


def canonical_debuff(name, seasonal=False):
    identifier = rule_id(name, seasonal)
    affixes = season_data.AFFIXES if seasonal else AFFIXES
    return affixes[identifier][0] if identifier is not None else name.strip()


def effect_values(identifier, language, seasonal=False):
    t = lambda key, **v: translate(language, key, **v)
    _, params = (season_data.AFFIXES if seasonal else AFFIXES)[identifier]
    values = {}
    for index, value in enumerate(params, 1):
        values['n' + str(index)] = f'{value:g}'
        values['p' + str(index)] = f'{value * 100:g}'
    scope = {1001: 'boss', 1002: 'followers', 1003: 'plane1', 1004: 'plane2',
             1005: 'plane3', 1006: 'followers', 1007: 'plane1', 1008: 'plane2',
             1009: 'plane3', 3001: 'front', 3002: 'back',
             40140: 'wind', 40141: 'fire', 40142: 'ice', 40143: 'lightning',
             40144: 'physical', 40145: 'quantum', 40146: 'imaginary'}
    if identifier in scope:
        values['scope'] = t('enc_scope_' + scope[identifier])
    if identifier in (3004, 3005):
        values['short'] = t('enc_scope_boss' if identifier == 3004 else 'enc_scope_combat')
        values['long'] = t('enc_scope_encounter' if identifier == 3004 else 'enc_scope_boss')
    return values


def rule_description(name, language='zh', seasonal=False):
    identifier = rule_id(name, seasonal)
    rules = SEASON_RULES if seasonal else RULES
    if identifier not in rules:
        return translate(language, 'enc_unknown_rule')
    effect, _ = rules[identifier]
    result = translate(language, 'enc_effect_' + effect, **effect_values(identifier, language, seasonal))
    if 1006 <= identifier <= 1009:
        result += ' ' + translate(language, 'enc_erosion')
    return result


def inactive_trait_estimates(catalog, state):
    """Count unique deployed characters only; bench copies cannot activate traits.

    This intentionally remains an estimate: unrecognized units, emblems and
    investment changes are not part of the confirmed character records.
    """
    deployed = {r.id: r for r in state.roles
                if r.confidence >= .8 and r.zone in ('前台', '后台')}
    counts = Counter(b for identifier in deployed for b in catalog.role_bonds(identifier))
    thresholds = season_data.TRAIT_THRESHOLDS if catalog.season else TRAIT_THRESHOLDS
    result = []
    for identifier, role in deployed.items():
        bonds = catalog.role_bonds(identifier)
        if not bonds or any(b not in thresholds for b in bonds):
            continue
        missing = [b for b in bonds if counts[b] < thresholds[b]]
        if missing:
            result.append((role.name, len(missing)))
    return result


def active_affix_ids(names, seasonal=False):
    identifiers = [rule_id(name, seasonal) for name in names]
    absorbed = identifiers.index(4041) if 4041 in identifiers else 0
    return set(identifiers[absorbed:])


def advice(catalog, state, language='zh'):
    t = lambda key, **v: translate(language, key, **v)
    if state.enemy_difficulty is None and not state.debuffs:
        return []
    seasonal = bool(catalog.season)
    rules = SEASON_RULES if seasonal else RULES
    affixes = season_data.AFFIXES if seasonal else AFFIXES
    version = catalog.season[0] if seasonal else RULE_VERSION
    difficulty = state.enemy_difficulty
    header = t('enc_difficulty', value=t('pending') if difficulty is None else difficulty)
    if state.debuffs:
        header += '\n' + t('enc_debuff_list', names='、'.join(state.debuffs))
    scaling_text = ''
    scaling = (season_data.ENEMY_SCALING if seasonal else ENEMY_SCALING).get(difficulty)
    if scaling:
        # Round chapters identify planes, not the Early/Middle/Final economy stage.
        plane = int(state.round.split('-')[0]) if state.round else None
        planes = (plane,) if plane in (1, 2, 3) else (1, 2, 3)
        scaling_text = t('enc_base_scaling')
        for p in planes:
            attack, hp, speed, *mitigation = scaling[p - 1]
            scaling_text += '\n' + t('enc_scaling', plane=p, attack=attack, hp=hp, speed=speed)
            if mitigation and mitigation[0]:
                scaling_text += ' · ' + t('enc_base_reduction', value=mitigation[0] * 100)
        scaling_text += '\n' + t('enc_scaling_limit')
    elif difficulty is not None:
        scaling_text = t('enc_scaling_missing')
    if not state.debuffs:
        header += '\n' + t('enc_no_debuffs')
    ids = active_affix_ids(state.debuffs, seasonal)
    if 4016 in ids and ids & {2005, 4010, 4001, 4008}:
        header += '\n' + t('enc_control_advance_combo')
    if 4002 in ids and 4005 in ids:
        header += '\n' + t('enc_counter_sustain_combo')
    result = [(t('match_analysis'), header)]
    for name in dict.fromkeys(state.debuffs):
        identifier = rule_id(name, seasonal)
        body = rule_description(name, language, seasonal)
        if identifier not in ids:
            body = t('enc_absorbed') + '\n' + body
        if identifier in rules and identifier in ids:
            _, action = rules[identifier]
            body += '\n' + t('enc_tip_' + action)
            scoped_plane = {1003: 1, 1004: 2, 1005: 3, 1007: 1, 1008: 2, 1009: 3}.get(identifier)
            if scoped_plane and state.round:
                current_plane = int(state.round.split('-')[0])
                if current_plane != scoped_plane:
                    body += '\n' + t('enc_other_plane', plane=scoped_plane)
            if identifier == 4027:
                estimates = inactive_trait_estimates(catalog, state)
                if estimates:
                    factors = affixes[identifier][1]
                    parts = [t('enc_trait_role', name=n, count=count,
                               percent=f'{factors[min(count, 3)-1]*100:g}')
                             for n, count in estimates]
                    body += '\n' + t('enc_trait_estimate', roles='；'.join(parts))
            if identifier == 4026:
                count = min(10, sum(e.copies for e in state.equipment
                                   if e.zone == '库存' and e.confidence >= .8))
                body += '\n' + t('enc_inventory_estimate', count=count,
                                  attack=count * 3, reduction=count * 4)
            if identifier in (4025, 4028):
                params = affixes[identifier][1]
                affected = [r.name for r in state.roles if r.zone in ('前台', '后台')
                            and r.confidence >= .8 and catalog.cost(r.id) > 0
                            and params[0 if catalog.cost(r.id) <= 3 else 1] < 1]
                if affected:
                    body += '\n' + t('enc_affected_roles', roles='、'.join(dict.fromkeys(affected)))
        result.append((canonical_debuff(name, seasonal), body))
    if state.hp is not None and state.hp <= 25:
        result.append((t('enc_priority'), t('enc_low_hp')))
    if scaling_text:
        result.append((t('enc_scaling_heading'), scaling_text))
    basis = t('enc_rules_source', version=version)
    if re_version := getattr(catalog, 'version', ''):
        if re_version not in (version, '未知', 'unknown'):
            basis += '\n' + t('enc_rules_version', current=re_version, version=version)
    result.append((t('enc_rules_heading'), basis))
    return result
