"""Investment choices stay distinct from selected context and remain actionable."""
from pathlib import Path
from unittest.mock import patch
import unittest

import numpy as np

from currency_war_assistant.models import Catalog,GameState,Seen
from currency_war_assistant.strategy import Adviser
from currency_war_assistant.investment import evaluate
from currency_war_assistant.vision import Recognizer,StateTracker


def catalog():
    return Catalog({
        "role_list":[{"id":"shared","name":"名字冲突的角色","rarity":3,"trait_details":[{"id":"bond"}]}],
        "portal_list":[
            {"id":"shared","title":"物资选项","desc":"第二位面开始时，获得1个武装箱。"},
            {"id":"emblem","title":"羁绊选项","desc":"获得一个【测试羁绊星徽】。"},
            {"id":"encounter","title":"节点选项","desc":"第三位面的战斗节点替换为遭遇节点。"}],
        "fight_augment_list":[
            {"id":"money","name":"资源选项","desc":"获得8金币。"},
            {"id":"condition","name":"条件选项","desc":"花费金币刷新30次后，获得20金币。"},
            {"id":"unknown","name":"未知选项"}],
        "trait_info_list":[{"trait_id":"bond","trait_name":"测试羁绊"}]
    })


def choices(c,kind="环境"):
    return [Seen(i,item["name"],kind,"待选",slot=s,confidence=.99,box=(100+s*600,360,350+s*600,410))
            for s,(i,item) in enumerate(c.pool(kind).items())]


class InvestmentTests(unittest.TestCase):
    def setUp(self):
        self.catalog=catalog()
        self.adviser=Adviser(self.catalog)
        self.state=GameState(scene="投资选择",investment_kind="环境",investment_choices=choices(self.catalog))

    def test_no_guide_or_owned_roles_still_compares_all_three(self):
        result=self.adviser.advice(self.state,None)
        self.assertIn("主推荐：物资选项",result[0][1])
        self.assertEqual(3,len([title for title,_ in result if title[:1].isdigit()]))
        self.assertNotIn("商店",result[0][1])
        self.assertIn("尚未锁定攻略",result[0][1])
        self.assertIn("对应位面",result[1][1])

    def test_author_portal_is_used_when_locked_without_owned_roles(self):
        guide={"id":"g","tourn_detail":{"role_stages":[{"stage":"Final","front_roles":[{"id":"shared"}]}],
                                          "portals":[{"id":"emblem"}]}}
        match=self.adviser.match(guide,self.state)
        result=self.adviser.advice(self.state,match,locked=True)
        self.assertIn("主推荐：羁绊选项",result[0][1])
        self.assertIn("锁定攻略作者优选",result[0][1])
        # A random cached candidate cannot define an unknown opening lineup.
        self.assertIn("主推荐：物资选项",self.adviser.advice(self.state,match)[0][1])

    def test_secondary_strategy_can_be_recommended(self):
        state=GameState(scene="投资选择",investment_kind="策略",investment_choices=choices(self.catalog,"策略"))
        guide={"id":"g","tourn_detail":{"role_stages":[{"stage":"Final","front_roles":[{"id":"shared"}]}],
                                          "second_fight_augments":[{"id":"condition"}]}}
        result=self.adviser.advice(state,self.adviser.match(guide,state),locked=True)
        self.assertIn("主推荐：条件选项",result[0][1])
        self.assertIn("作者次选",result[0][1])
        self.assertIn("不能把奖励当作已经获得","\n".join(body for _,body in result))

    def test_unrecognized_partial_cards_are_never_a_final_pick(self):
        self.state.investment_choices=self.state.investment_choices[:1]
        result=self.adviser.advice(self.state,None)
        self.assertIn("1/3",result[0][1])
        self.assertIn("暂优先",result[0][1])
        self.assertNotIn("主推荐",result[0][1])
        self.state.investment_choices=[]
        self.assertIn("无需返回商店",self.adviser.advice(self.state,None)[0][1])

    def test_unknown_effects_do_not_get_an_invented_pick(self):
        self.state.investment_choices=[Seen("unknown","未知选项","策略","待选",confidence=1)]
        self.assertIn("不足以",self.adviser.advice(self.state,None)[0][1])

    def test_pending_context_does_not_satisfy_required_environment(self):
        guide={"id":"g","description":"必须选择物资选项。","tourn_detail":{
            "role_stages":[{"stage":"Final","front_roles":[{"id":"shared"}]}]}}
        self.assertTrue(self.adviser.match(guide,self.state).blocked)
        self.state.environment=Seen("shared","物资选项","环境","已选",confidence=1)
        self.assertFalse(self.adviser.match(guide,self.state).blocked)

    def test_card_refresh_and_exit_drop_old_choices_but_keep_selected_context(self):
        tracker=StateTracker()
        selected=Seen("emblem","羁绊选项","环境","已选",confidence=1)
        tracker.state.environment=selected
        tracker.merge(self.state)
        self.assertEqual(3,len(tracker.state.investment_choices))
        tracker.merge(GameState(scene="投资选择",investment_choices=self.state.investment_choices[:1]))
        self.assertEqual(1,len(tracker.state.investment_choices))
        tracker.merge(GameState(scene="准备"))
        self.assertEqual([],tracker.state.investment_choices)
        self.assertIs(selected,tracker.state.environment)

    def test_manual_choice_correction_survives_same_frame_and_expires_on_refresh(self):
        tracker=StateTracker()
        tracker.merge(self.state)
        correction=Seen("money","资源选项","策略","待选",slot=0,source="手动",confidence=1)
        tracker.state.investment_choices[0]=correction
        tracker.merge(self.state)
        self.assertIn(correction,tracker.state.investment_choices)
        tracker.merge(GameState(scene="投资选择",investment_choices=[]))
        self.assertEqual([],tracker.state.investment_choices)

    def test_investment_heading_beats_damage_and_refresh_effect_text(self):
        recognizer=object.__new__(Recognizer)
        rows=[{"text":t,"confidence":1,"box":b} for t,b in (
            ("投资策略",(900,70,1050,110)),("造成更多伤害；刷新30次获得金币",(750,420,1160,480)))]
        state=recognizer.parse_rows(rows,(1080,1920,3))
        self.assertEqual(("投资选择","策略"),(state.scene,state.investment_kind))

    def test_all_three_titles_recognized_with_namespaced_ids_at_two_resolutions(self):
        rows=[{"text":t,"confidence":1,"box":b} for t,b in (
            ("投资环境",(900,70,1050,110)),("物资选项",(380,360,500,410)),
            ("羁绊选项",(900,360,1020,410)),("节点选项",(1420,360,1540,410)),
            # A name within the effect or an assistant overlay is not a title.
            ("资源选项",(900,500,1020,535)),("名字冲突的角色",(340,420,600,455)))]
        for factor in (1,.5):
            with self.subTest(factor=factor):
                directory=Path(__file__).parent/"_cache"/"investment"
                recognizer=Recognizer(self.catalog,directory)
                scaled=[{**r,"box":tuple(round(x*factor) for x in r["box"])} for r in rows]
                with patch.object(recognizer,"read_text",return_value=scaled):
                    state,_=recognizer.analyze(np.zeros((int(1080*factor),int(1920*factor),3),dtype=np.uint8))
                self.assertEqual(["物资选项","羁绊选项","节点选项"],[s.name for s in state.investment_choices])
                self.assertEqual([0,1,2],[s.slot for s in state.investment_choices])
                self.assertEqual([],state.roles)
                self.assertEqual([],state.strategies)
                self.assertIsNone(state.environment)


if __name__=="__main__":
    unittest.main()
