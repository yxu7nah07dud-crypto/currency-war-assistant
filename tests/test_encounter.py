"""Encounter OCR and rule regressions using text/geometry, never game artwork."""
import copy
import threading
import unittest
from unittest.mock import Mock

from currency_war_assistant.controller import Controller
from currency_war_assistant.encounter import (
    RULES, advice, inactive_trait_estimates, rule_description, rule_id,
)
from currency_war_assistant.encounter_data import AFFIXES, ENEMY_SCALING
from currency_war_assistant.models import Catalog, GameState, Seen
from currency_war_assistant.strategy import Adviser
from currency_war_assistant.vision import Recognizer, StateTracker, detect_enemy_modifiers


NAMES = ['侵蚀·第一位面强化', '坠入陷阱', '形单影只', '忍无可忍']


def row(text, box, confidence=.99):
    return {'text': text, 'box': box, 'confidence': confidence}


def screenshot_rows():
    return [row(text, box) for text, box in (
        ('敌人难度120', (78, 964, 249, 998)),
        (NAMES[0], (310, 964, 519, 998)),
        (NAMES[1], (567, 964, 680, 999)),
        (NAMES[2], (710, 964, 849, 999)),
        (NAMES[3], (886, 966, 1016, 996)),
        ('下一步', (1470, 963, 1557, 1004)),
        ('UID:101003693', (34, 1042, 159, 1062)),
        ('请停留在准备界面并打开商店', (905, 580, 1500, 610)),
        ('敌人难度30', (905, 200, 1140, 230)),
    )]


class EncounterRecognitionTests(unittest.TestCase):
    def test_supplied_layout_detects_four_affixes_without_uid_or_overlay(self):
        recognizer = object.__new__(Recognizer)
        observed = recognizer.parse_rows(screenshot_rows(), (1080, 1920, 3))
        self.assertEqual((120, NAMES, '敌人情报'),
                         (observed.enemy_difficulty, observed.debuffs, observed.scene))
        self.assertEqual('普通 A8·待确认', observed.difficulty)

    def test_half_resolution_and_split_numeric_label(self):
        rows = screenshot_rows()
        rows[0] = row('敌人难度', (78, 964, 195, 998))
        rows.append(row('120', (199, 964, 249, 998)))
        scaled = [{**r, 'box': tuple(v / 2 for v in r['box'])} for r in rows]
        self.assertEqual((120, NAMES), detect_enemy_modifiers(scaled, (540, 960, 3)))

    def test_names_require_bottom_difficulty_anchor_and_same_baseline(self):
        rows = screenshot_rows()[1:]
        self.assertEqual((None, []), detect_enemy_modifiers(rows, (1080, 1920, 3)))
        rows = screenshot_rows()
        rows.append(row('商店角色', (300, 900, 400, 930)))
        rows.append(row('2700', (180, 1010, 250, 1040)))
        self.assertEqual((120, NAMES), detect_enemy_modifiers(rows, (1080, 1920, 3)))
        rows[0]['confidence'] = .4
        self.assertEqual((None, []), detect_enemy_modifiers(rows, (1080, 1920, 3)))

    def test_split_spaces_and_merged_baseline_keep_erosion_distinct(self):
        rows = [row('敌人难度120 侵蚀·第一位面强化 坠入陷阱', (78, 964, 680, 998)),
                row('形 单 影 只', (710, 964, 849, 999))]
        values = detect_enemy_modifiers(rows, (1080, 1920, 3))
        self.assertEqual((120, NAMES[:3]), values)
        self.assertNotEqual(rule_id('第一位面强化'), rule_id('侵蚀第一位面强化'))

    def test_conditions_survive_rounds_hidden_panels_and_reset(self):
        tracker = StateTracker()
        tracker.merge(GameState(difficulty='普通 A8·50', enemy_difficulty=120,
                                debuffs=list(NAMES), scene='敌人情报'))
        for observed in (GameState(scene='投资选择'), GameState(scene='准备', round='1-1'),
                         GameState(scene='战斗'), GameState(scene='准备', round='2-1')):
            state = tracker.merge(observed)
            self.assertEqual((120, NAMES, '普通 A8·50'),
                             (state.enemy_difficulty, state.debuffs, state.difficulty))
        tracker.merge(GameState(enemy_difficulty=126))
        self.assertEqual(126, tracker.state.enemy_difficulty)
        tracker.reset()
        self.assertIsNone(tracker.state.enemy_difficulty)
        self.assertEqual([], tracker.state.debuffs)


class EncounterRuleTests(unittest.TestCase):
    def test_all_55_rules_have_formatted_effects_and_responses_in_three_languages(self):
        self.assertEqual(set(AFFIXES), set(RULES))
        for language in ('zh', 'en', 'ja'):
            for name, _ in AFFIXES.values():
                with self.subTest(language=language, name=name):
                    output = advice(Catalog({}), GameState(debuffs=[name]), language)
                    effect = output[1][1]
                    self.assertNotIn('enc_', effect)
                    self.assertNotIn('{', effect)
                    self.assertIn('\n', effect)

    def test_screenshot_rules_use_actual_parameters(self):
        self.assertIn('16%', rule_description(NAMES[0]))
        self.assertNotIn('20%', rule_description(NAMES[0]))
        for text in ('40%', '20%', '1回合'):
            self.assertIn(text, rule_description(NAMES[1]))
        for text in ('85%', '60%', '30%'):
            self.assertIn(text, rule_description(NAMES[2]))
        for text in ('7次攻击', '100%'):
            self.assertIn(text, rule_description(NAMES[3]))
        self.assertNotIn('待确认', '\n'.join(rule_description(name) for name in NAMES))

    def test_enemy_120_uses_table_for_current_plane_and_never_a8_number(self):
        state = GameState(difficulty='普通 A8·50', enemy_difficulty=120, round='1-1')
        output = dict(advice(Catalog({}), state))
        self.assertIn('敌人难度 120', output['对局分析'])
        self.assertIn('生命 ×97.9', output['敌人基础倍率'])
        self.assertNotIn('第2位面', output['敌人基础倍率'])
        self.assertEqual((2.1152, 97.88758, 1.96), ENEMY_SCALING[120][0])
        unknown_plane = dict(advice(Catalog({}), GameState(enemy_difficulty=120)))['敌人基础倍率']
        self.assertIn('第3位面', unknown_plane)

    def test_first_plane_erosion_not_applied_to_later_plane(self):
        state = GameState(enemy_difficulty=120, debuffs=[NAMES[0]], round='2-1')
        output = advice(Catalog({}), state)[1][1]
        self.assertIn('当前位面不计', output)

    def test_opening_control_and_enemy_advance_explain_combined_risk(self):
        state = GameState(debuffs=['坠入陷阱', '忍无可忍'])
        self.assertIn('组合风险', advice(Catalog({}), state)[0][1])
        state.debuffs = ['坠入陷阱']
        self.assertNotIn('组合风险', advice(Catalog({}), state)[0][1])

    def test_enemy_page_needs_no_owned_roles_or_locked_guide(self):
        state = GameState(scene='敌人情报', enemy_difficulty=120, debuffs=list(NAMES))
        output = Adviser(Catalog({})).advice(state, None)
        self.assertIn('忍无可忍', dict(output))
        self.assertNotIn('打开商店', str(output))
        for scene in ('准备', '战斗', '投资选择'):
            state.scene = scene
            self.assertIn('对局分析', dict(Adviser(Catalog({})).advice(state, None)))

    def test_trait_estimate_ignores_bench_and_duplicate_copies(self):
        catalog = Catalog({'role_list': [
            {'id': 'a', 'name': 'A', 'trait_details': [{'id': '1001'}]},
            {'id': 'b', 'name': 'B', 'trait_details': [{'id': '1001'}]},
        ]})
        a = Seen('a', 'A', '角色', '前台', confidence=1)
        state = GameState(roles=[a, copy.deepcopy(a), Seen('b', 'B', '角色', '备战', confidence=1)])
        self.assertEqual([('A', 1)], inactive_trait_estimates(catalog, state))
        state.roles[-1].zone = '后台'
        self.assertEqual([], inactive_trait_estimates(catalog, state))

    def test_unknown_affix_is_not_given_an_invented_effect(self):
        output = rule_description('不存在的词缀')
        self.assertIn('未匹配', output)
        self.assertNotIn('%', output)


class EncounterCorrectionTests(unittest.TestCase):
    def setUp(self):
        self.c = object.__new__(Controller)
        self.c._mutex = threading.RLock()
        self.c.tracker = StateTracker()
        self.c.recalculate = Mock()
        self.c.language = 'zh'

    def test_atomic_validation_clear_and_canonicalization(self):
        self.c.save_encounter('120', '侵蚀第一位面强化\n坠入陷阱\n坠入陷阱')
        snapshot = self.c.snapshot()
        self.assertEqual(NAMES[:2], snapshot['debuffs'])
        with self.assertRaises(ValueError):
            self.c.save_encounter('120.5', '忍无可忍')
        self.assertEqual(snapshot, self.c.snapshot())
        self.c.save_encounter('', '')
        self.assertIsNone(self.c.get_state().enemy_difficulty)
        self.assertEqual([], self.c.get_state().debuffs)


if __name__ == '__main__':
    unittest.main()
