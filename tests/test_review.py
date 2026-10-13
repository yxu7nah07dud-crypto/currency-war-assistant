"""Regression fixtures for external review; no game assets or public guide text."""
import unittest
import threading
from unittest.mock import Mock,patch
from currency_war_assistant.controller import Controller
from currency_war_assistant.models import Catalog,GameState,Seen
from currency_war_assistant.vision import StateTracker


class DuplicateRoleTests(unittest.TestCase):
    def card(self,x):
        return Seen('r','Synthetic role','角色','备战',box=(x,100,x+60,160),confidence=1)

    def test_copies_remain_separate_across_frames_and_sale(self):
        tracker=StateTracker()
        for positions in ((100,200),(102,202),(102,)):
            state=tracker.merge(GameState(scene='准备',roles=[self.card(x) for x in positions],visible_zones={'备战'}))
            self.assertEqual(len(positions),len(state.roles))
        state.roles.append(Seen('manual','Manual','角色','前台',source='手动',confidence=1))
        tracker.merge(GameState(scene='准备',visible_zones={'前台','备战'}))
        self.assertEqual(['manual'],[r.id for r in state.roles])

    def test_nearest_box_preserves_individual_star_when_hidden(self):
        tracker=StateTracker()
        first,second=self.card(100),self.card(200)
        first.star=1;second.star=2
        tracker.merge(GameState(scene='准备',roles=[first,second],visible_zones={'备战'}))
        state=tracker.merge(GameState(scene='战斗',roles=[self.card(202),self.card(102)]))
        self.assertEqual([2,1],[r.star for r in state.roles])


class CorrectionThreadTests(unittest.TestCase):
    def setUp(self):
        self.c=object.__new__(Controller)
        self.c._mutex=threading.RLock();self.c.tracker=StateTracker();self.c.recalculate=Mock()

    def test_corrections_and_snapshots_are_serialized_and_detached(self):
        errors=[]
        def edits():
            try:
                for i in range(100):
                    self.c.save_numbers({'gold':str(i),'round':'1-1'})
                    self.c.correct_item(Seen('r','R','角色','备战',source='手动',confidence=1))
                    self.c.clear_manual_shop()
            except Exception as e:errors.append(e)
        worker=threading.Thread(target=edits);worker.start()
        while worker.is_alive():self.c.snapshot()
        worker.join();self.assertEqual([],errors)
        detached=self.c.get_state();detached.roles.clear()
        self.assertEqual(1,len(self.c.get_state().roles))
        self.c.remove_item(self.c.get_state().roles[0])
        self.assertEqual([],self.c.get_state().roles)

    def test_numbers_validation_is_atomic(self):
        with self.assertRaises(ValueError):self.c.save_numbers({'gold':'40','level':'100'})
        self.assertIsNone(self.c.get_state().gold)


class PrerequisiteTests(unittest.TestCase):
    def test_html_is_cleaned_and_single_character_role_is_not_inferred(self):
        from currency_war_assistant.strategy import required_start
        catalog=Catalog({'role_list':[{'id':'f','name':'流萤'},{'id':'b','name':'刃'}]})
        self.assertEqual({'f'},required_start({'description':'开局<span>确定</span>有流萤。'},catalog))
        self.assertEqual(set(),required_start({'description':'开局必须有刃。'},catalog))

    def test_role_equipment_collision_names_and_advice(self):
        from currency_war_assistant.strategy import Adviser,Match
        catalog=Catalog({'role_list':[{'id':'7','name':'ROLE','rarity':1}],
                         'equipment_list':[{'id':'7','name':'GEAR'}]})
        with self.assertLogs(level='WARNING'):self.assertEqual('ROLE',catalog.name('7'))
        self.assertEqual('GEAR',catalog.name('7','装备'))
        guide={'id':'g','tourn_detail':{'role_stages':[{'stage':'Final','front_roles':[{'id':'7','first_equipments':[{'id':'7'}]}]}]}}
        state=GameState(scene='准备',roles=[Seen('7','ROLE','角色','前台',confidence=1)],equipment=[Seen('7','GEAR','装备','库存',confidence=1)])
        output=str(Adviser(catalog).advice(state,Match(guide,10)))
        self.assertIn('GEAR 给 ROLE',output)


class EmptyTemplateTests(unittest.TestCase):
    def test_empty_templates_skip_sift_but_learned_crop_still_matches(self):
        import numpy as np
        from pathlib import Path
        from currency_war_assistant.vision import IconMatcher
        matcher=IconMatcher(Path('tests/_cache/absent'))
        image=np.random.default_rng(1).integers(0,255,(120,180,3),dtype=np.uint8)
        with patch('currency_war_assistant.vision.cv2.SIFT_create',side_effect=AssertionError('unnecessary SIFT')):
            self.assertEqual([],matcher.find(image));self.assertEqual([],matcher.inventory(image))
            matcher.custom=[({'id':'r','kind':'角色'},image[20:50,40:70].copy())]
            found=matcher.find(image,{'角色'})
            self.assertEqual('r',found[0]['ids'][0])
            self.assertEqual([],matcher.find(image,{'装备'}))

    def test_analyze_skips_all_icon_scans_without_templates(self):
        import numpy as np
        from pathlib import Path
        from currency_war_assistant.vision import Recognizer
        recognizer=Recognizer(Catalog({}),Path('tests/_cache/absent'))
        with patch.object(recognizer,'read_text',return_value=[{'text':'后台区域','box':(500,600,600,630),'confidence':1}]),patch.object(recognizer.matcher,'find',side_effect=AssertionError('unnecessary scan')):
            recognizer.analyze(np.zeros((1080,1920,3),dtype=np.uint8))


class ReportTests(unittest.TestCase):
    def test_empty_or_unchanged_report_is_not_rewritten(self):
        from pathlib import Path
        c=object.__new__(Controller);c._mutex=threading.RLock();c.last_result={}
        with patch('currency_war_assistant.controller.write_json') as write:
            self.assertFalse(c.export_report(Path('tests/_cache/report.json')))
            c.last_result={'state':{'gold':20}}
            self.assertTrue(c.export_report(Path('tests/_cache/report.json')))
            self.assertFalse(c.export_report(Path('tests/_cache/report.json')))
            c.last_result={'state':{'gold':21}}
            self.assertTrue(c.export_report(Path('tests/_cache/report.json')))
            self.assertEqual(2,write.call_count)

    def test_schedule_survives_failed_write_and_cli_reports_missing_parameters(self):
        from main import schedule_reports,validate_cli
        root=Mock();c=Mock();c.export_report.side_effect=OSError('disk fixture')
        callback=schedule_reports(root,c,'test.json')
        with self.assertLogs(level='ERROR'):callback()
        self.assertEqual(2,root.after.call_count)
        for flag in ('--self-test','--verify-guide','--verify-investment','--guide-code'):
            with self.assertRaisesRegex(ValueError,'Usage:'):validate_cli([flag])
        validate_cli(['--verify-investment','out.json','image.png','config.json'])


class DeadCodeTests(unittest.TestCase):
    def test_default_stage_and_capture_module_remain_available(self):
        from currency_war_assistant import capture,paths
        self.assertEqual('Early',GameState().stage())
        self.assertEqual('Middle',GameState(round='2-1').stage())
        self.assertFalse(hasattr(paths,'ASSETS'))
        self.assertFalse(hasattr(capture,'set_overlay_capture_exclusion'))


class EconomyTests(unittest.TestCase):
    def test_confirmed_general_estimates_are_unchanged_and_labeled(self):
        from currency_war_assistant.economy import RESERVE_GOLD,REFRESH_COST,TARGET_LEVEL_BY_COST,estimated_interest
        from currency_war_assistant.strategy import Adviser,Match
        self.assertEqual(50,RESERVE_GOLD);self.assertEqual(2,REFRESH_COST)
        self.assertEqual({1:5,2:6,3:7,4:9,5:9},dict(TARGET_LEVEL_BY_COST))
        self.assertEqual([0,1,5,5],[estimated_interest(x) for x in (9,10,50,100)])
        catalog=Catalog({'role_list':[{'id':'r','name':'R','rarity':1}]})
        guide={'id':'g','tourn_detail':{'role_stages':[{'stage':'Final','front_roles':[{'id':'r'}]}]}}
        state=GameState(scene='准备',gold=53,level=5,roles=[Seen('r','R','角色','前台',confidence=1)])
        advice=Adviser(catalog).advice(state,Match(guide,1))
        self.assertTrue(next(body for title,body in advice if title=='经济').startswith('按通用规则估算'))


class LanguageTests(unittest.TestCase):
    def test_generated_advice_is_translated_without_changing_match_or_enums(self):
        from currency_war_assistant.strategy import Adviser
        from currency_war_assistant.localization import enum_label
        from currency_war_assistant.capture import unsupported_client_title
        catalog=Catalog({'role_list':[{'id':'r','name':'ROLE','rarity':1}],
                         'equipment_list':[{'id':'e','name':'GEAR'}],
                         'fight_augment_list':[{'id':'a','name':'OPTION','desc':'获得10金币。'}]})
        guide={'id':'g','tourn_detail':{'role_stages':[{'stage':'Final','front_roles':[{'id':'r','first_equipments':[{'id':'e'}]}]}]}}
        state=GameState(scene='准备',gold=53,level=5,roles=[Seen('r','ROLE','角色','前台',confidence=1)],shop=[Seen('r','ROLE','角色','商店',confidence=1)],equipment=[Seen('e','GEAR','装备','库存',confidence=1)])
        scores=[]
        for language,heading in [('zh','买人'),('en','Buy'),('ja','購入')]:
            adviser=Adviser(catalog,language);match=adviser.match(guide,state);scores.append(match.score)
            advice=adviser.advice(state,match)
            self.assertIn(heading,[title for title,body in advice])
            if language!='zh':self.assertNotIn('按通用规则估算',str(advice))
            self.assertEqual('前台',state.roles[0].zone)
        self.assertEqual(1,len(set(scores)))
        investment=GameState(scene='投资选择',investment_kind='策略',investment_choices=[Seen('a','OPTION','策略','待选',confidence=1)])
        en=str(Adviser(catalog,'en').advice(investment,None))
        self.assertIn('Investment strategy',en);self.assertIn('Provides economy resources',en)
        self.assertIn('获得10金币。',en)  # Source effect is deliberately not translated.
        self.assertNotIn('提供经济资源',en)
        self.assertEqual('Bench',enum_label('en','备战'))
        self.assertEqual('手動',enum_label('ja','手动'))
        self.assertTrue(unsupported_client_title('Honkai: Star Rail'))
        self.assertTrue(unsupported_client_title('崩壞：星穹鐵道'))
        self.assertFalse(unsupported_client_title('崩坏：星穹铁道'))

    def test_translation_parameters_match_all_three_languages(self):
        import string
        from currency_war_assistant.localization import ADVICE
        for key,translations in ADVICE.items():
            fields=[{f for _,f,_,_ in string.Formatter().parse(text) if f is not None} for text in translations]
            self.assertEqual(fields[0],fields[1],key);self.assertEqual(fields[0],fields[2],key)


if __name__=='__main__':unittest.main()
