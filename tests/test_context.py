"""Difficulty corrections and actual investment confirmations stay distinct."""
from collections import deque
from copy import deepcopy
from pathlib import Path
import threading
import unittest
import uuid
from unittest.mock import Mock,patch

import numpy as np

from currency_war_assistant.controller import Controller
from currency_war_assistant.models import Catalog,GameState,Seen
from currency_war_assistant.selection import InvestmentSelection
from currency_war_assistant.vision import Recognizer,StateTracker,detect_a8_difficulty


def row(text,box):return {'text':text,'box':box,'confidence':.99}


def choices(kind='环境'):
    return [Seen(str(i),f'候选{i}',kind,'待选',slot=i,confidence=.99,
                 box=(int((.23+.27*i)*1920)-60,370,int((.23+.27*i)*1920)+60,410))
            for i in range(3)]


CONFIRM=[row('确认',(950,970,1170,1010))]


class DifficultyTests(unittest.TestCase):
    def test_resume_screen_reads_joined_or_split_wealth_number_at_two_resolutions(self):
        rows=[row('A8',(592,212,631,249)),row('财富造物主50',(591,252,897,301)),
              row('继续进度',(1622,940,1760,978)),row('结束并结算',(1330,940,1484,978)),
              row('当前进度1-1',(1536,854,1707,892)),row('普通 A8·30',(225,650,450,678))]
        for factor in (1,.5):
            scaled=[{**r,'box':tuple(int(v*factor) for v in r['box'])} for r in rows]
            state=Recognizer.parse_rows(object.__new__(Recognizer),scaled,(int(1080*factor),int(1920*factor),3))
            self.assertEqual(('普通 A8·50','对局菜单','1-1'),(state.difficulty,state.scene,state.round))
            self.assertIsNone(state.level);self.assertIsNone(state.gold)
        self.assertEqual(50,detect_a8_difficulty([row('当前职级 A8 财富造物主50',(70,320,420,355))],(1080,1920,3)))

    def test_no_anchor_or_assistant_status_cannot_set_difficulty(self):
        self.assertIsNone(detect_a8_difficulty([row('财富造物主50',(590,252,900,301))],(1080,1920,3)))
        self.assertIsNone(detect_a8_difficulty([row('普通 A8·30',(220,200,460,230))],(1080,1920,3)))

    def test_manual_difficulty_survives_ocr_and_round_changes_until_reset(self):
        tracker=StateTracker();tracker.state.difficulty='普通 A8·50'
        tracker.state.manual_fields.update(('difficulty','gold'))
        tracker.merge(GameState(round='2-1',difficulty='普通 A8·30',gold=14))
        self.assertEqual('普通 A8·50',tracker.state.difficulty)
        self.assertEqual({'difficulty'},tracker.state.manual_fields)
        tracker.reset();self.assertEqual('普通 A8·待确认',tracker.state.difficulty)


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.reader=InvestmentSelection()
        self.state=GameState(scene='投资选择',investment_kind='环境',investment_choices=choices())
        self.reader.observe(self.state,CONFIRM,(1080,1920,3),1,now=10)

    def test_card_confirm_and_exit_record_actual_choice_once(self):
        self.reader.click((.77,.5),now=11)
        self.assertIsNone(self.reader.observe(self.state,CONFIRM,(1080,1920,3),1,now=12))
        self.reader.click((.55,.916),now=13)
        picked=self.reader.observe(GameState(scene='准备'),[],(1080,1920,3),1,now=14)
        self.assertEqual(('2','已选','选择记录'),(picked.id,picked.zone,picked.source))
        self.assertIsNone(self.reader.observe(GameState(scene='准备'),[],(1080,1920,3),1,now=15))

    def test_exit_or_confirm_without_card_never_implies_recommended_choice(self):
        self.reader.click((.55,.916),now=11)
        self.assertIsNone(self.reader.observe(GameState(scene='准备'),[],(1080,1920,3),1,now=12))
        self.reader.observe(self.state,CONFIRM,(1080,1920,3),1,now=13)
        self.reader.click((.23,.5),now=14)
        self.assertIsNone(self.reader.observe(GameState(scene='准备'),[],(1080,1920,3),1,now=15))

    def test_refresh_window_change_or_expired_page_discard_pending_confirmation(self):
        for mode in ('refresh','window','expiry','back'):
            with self.subTest(mode=mode):
                self.setUp();self.reader.click((.23,.5),now=11);self.reader.click((.55,.916),now=12)
                next_window=1;now=13
                if mode=='refresh':
                    updated=deepcopy(self.state);updated.investment_choices[0].id='new'
                    self.reader.observe(updated,CONFIRM,(1080,1920,3),1,now=13)
                elif mode=='window':next_window=2
                elif mode=='expiry':now=40
                elif mode=='back':self.reader.click((.97,.07),now=12.5)
                self.assertIsNone(self.reader.observe(GameState(scene='其他'),[],(1080,1920,3),next_window,now=now))

    def test_partial_ocr_keeps_same_selection_and_missing_confirm_button_cannot_commit(self):
        self.reader.click((.5,.5),now=11)
        partial=deepcopy(self.state);partial.investment_choices=partial.investment_choices[:2]
        self.reader.observe(partial,CONFIRM,(1080,1920,3),1,now=12)
        self.reader.click((.55,.916),now=13)
        self.assertEqual('1',self.reader.observe(GameState(scene='准备'),[],(1080,1920,3),1,now=14).id)
        self.reader.observe(self.state,[],(1080,1920,3),1,now=15)
        self.reader.click((.5,.5),now=16);self.reader.click((.55,.916),now=17)
        self.assertIsNone(self.reader.observe(GameState(scene='准备'),[],(1080,1920,3),1,now=18))

    def test_explicit_owned_label_works_without_clicks_but_card_title_does_not(self):
        catalog=Catalog({'portal_list':[{'id':'a','title':'测试环境','desc':'获得1金币。'}]})
        recognizer=Recognizer(catalog,Path('tests/_cache/selected-investment'))
        for selected in (False,True):
            rows=[row('已选投资环境：测试环境' if selected else '测试环境',(1300,500,1750,540))]
            with patch.object(recognizer,'read_text',return_value=rows):
                state,_=recognizer.analyze(np.zeros((1080,1920,3),dtype=np.uint8))
            self.assertEqual(selected,bool(state.environment and state.environment.zone=='已选'))

    def test_owned_environment_tooltip_is_preparation_and_automatically_selected(self):
        catalog=Catalog({'portal_list':[{'id':'own','title':'测试概念股','desc':'开局获得测试角色。'}]})
        rows=[row('购买经验',(235,833,385,875)),row('Lv.3',(270,897,350,929)),
              row('投资环境',(918,185,1006,210)),row('测试概念股',(815,233,1010,261)),
              row('开局获得测试角色。',(815,270,1210,311))]
        recognizer=Recognizer(catalog,Path('tests/_cache/owned-tooltip'))
        for factor in (1,.5):
            scaled=[{**r,'box':tuple(int(v*factor) for v in r['box'])} for r in rows]
            with patch.object(recognizer,'read_text',return_value=scaled):
                state,_=recognizer.analyze(np.zeros((int(1080*factor),int(1920*factor),3),dtype=np.uint8))
            self.assertEqual('准备',state.scene)
            self.assertEqual(('own','已选'),(state.environment.id,state.environment.zone))
            self.assertEqual([],state.investment_choices)
        # The ordinary three-choice heading cannot be treated as owned.
        rows[0]=row('剩余次数：1',(600,970,790,1015));rows[2]=row('投资环境',(900,80,1020,110))
        with patch.object(recognizer,'read_text',return_value=rows):
            state,_=recognizer.analyze(np.zeros((1080,1920,3),dtype=np.uint8))
        self.assertEqual('投资选择',state.scene);self.assertIsNone(state.environment)

    def test_confirmed_environment_replaces_old_one_and_persists_when_hidden(self):
        tracker=StateTracker();tracker.state.environment=Seen('old','旧环境','环境','已选',confidence=1)
        tracker.merge(GameState(environment=Seen('new','新环境','环境','已选',confidence=1)))
        tracker.merge(GameState(scene='战斗'))
        self.assertEqual('new',tracker.state.environment.id)
        tracker.reset();self.assertIsNone(tracker.state.environment)

    def test_selected_environment_effect_and_prerequisite_status_are_visible(self):
        from currency_war_assistant.strategy import Adviser
        catalog=Catalog({'portal_list':[{'id':'a','title':'测试环境','desc':'花费金币刷新30次后，获得20金币。'}]})
        state=GameState(scene='准备',environment=Seen('a','测试环境','环境','已选',confidence=1))
        for language in ('zh','en','ja'):
            result=Adviser(catalog,language).advice(state,None)
            self.assertIn('测试环境',result[0][0]);self.assertIn('30次',result[0][1])

    def test_observation_loop_applies_the_confirmed_card_to_game_state(self):
        c=object.__new__(Controller)
        c.closing=False;c.running=True;c._wake=Mock();c._mutex=threading.RLock()
        c.data=Path('tests/_cache/absent');c.tracker=StateTracker();c._signature=()
        c.selection=InvestmentSelection();c.recalculate=Mock();c.emit=Mock();c.times=deque()
        c.capture=Mock();c.capture.window.hwnd=1
        c.capture.latest.return_value=(np.zeros((1080,1920,3),dtype=np.uint8),0)
        c.recognizer=Mock();count=0
        def observe(image):
            nonlocal count
            count+=1
            if count==2:
                c.selection.click((.5,.5));c.selection.click((.55,.916))
            if count==3:
                c.closing=True
                return GameState(scene='准备'),[]
            return deepcopy(self.state),CONFIRM
        c.recognizer.analyze.side_effect=observe
        with patch('currency_war_assistant.controller.frames_stable',return_value=True),patch('currency_war_assistant.controller.time.sleep'):
            c._loop()
        self.assertEqual(('1','已选'),(c.get_state().environment.id,c.get_state().environment.zone))


class ContextPersistenceTests(unittest.TestCase):
    def test_manual_difficulty_persists_restart_and_new_game_clears_it(self):
        directory=Path(__file__).parent/'_cache'/('context-'+uuid.uuid4().hex)
        directory.mkdir(parents=True)
        with patch('currency_war_assistant.controller.threading.Thread'):
            first=Controller(Path(directory));first.recalculate=Mock()
            first.save_difficulty('12')
            with self.assertRaises(ValueError):first.save_difficulty('A8·21')
            self.assertEqual('A8·12',first.get_state().difficulty)
            second=Controller(Path(directory));second.recalculate=Mock()
            self.assertEqual('A8·12',second.get_state().difficulty)
            second.new_game();second.close()
            third=Controller(Path(directory));third.recalculate=Mock()
            self.assertEqual('职级待确认',third.get_state().difficulty)
            third.save_difficulty('A6·3');third.save_difficulty('')
            self.assertNotIn('difficulty',third.get_state().manual_fields)
            first.close();third.close()


if __name__=='__main__':unittest.main()
