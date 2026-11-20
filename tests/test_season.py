"""Season 2 upgrade and confirmation regressions using authored fixtures."""
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

from currency_war_assistant.api import GuideClient
from currency_war_assistant.encounter import advice, rule_description, rule_id
from currency_war_assistant.models import Catalog, GameState, Seen
from currency_war_assistant.paths import write_json
from currency_war_assistant.season import ACTIVE
from currency_war_assistant.season_data import AFFIXES
from currency_war_assistant.selection import InvestmentSelection
from currency_war_assistant.strategy import Adviser, target_level
from currency_war_assistant.vision import Recognizer, StateTracker


META = dict(zip(("rpg_game_big_version", "season_id", "sub_season_id"), ACTIVE))
SHAPE = (1080, 1920, 3)
CACHE = Path(__file__).parent / "_cache"
CACHE.mkdir(exist_ok=True)


def row(name, x, y):
    return {"text": name, "box": (x, y, x + 135, y + 30), "confidence": .99}


def catalog():
    return Catalog({**META, "role_list": [
        {"id": "a", "name": "员工甲", "rarity": 1},
        {"id": "b", "name": "员工乙", "rarity": 2},
        {"id": "s", "name": "特别员工", "rarity": 7},
    ], "portal_list": [{"id": i, "title": i} for i in ("e1","e2")],
        "spot_light_list": [{"id": "light", "name": "测试光环", "desc": "行动提前",
                             "suitable_role_list": ["a"]}]}, season=ACTIVE)


def guide(identifier="first", carry="a", portal="e1", **detail):
    return {"id": identifier, "title": identifier, "tourn_detail": {
        **META, "portals": [{"id": portal}], "share_code": "AbCDeFGhijk=",
        "role_stages": [{"stage":"Final", "carry_list":[carry],
                         "front_roles":[{"id":carry}]}], **detail,
    }}


class SeasonTests(unittest.TestCase):
    def test_season_cache_filters_old_invalid_and_future_rows(self):
        path=CACHE/f"season-{uuid4().hex}"
        current=guide()
        write_json(path/"guides.json",{"guides":[current,guide("old",season_id="1"),
                                                 guide("next",sub_season_id="2"),guide("expired",is_sub_expired=True)]})
        client=GuideClient(path,season=ACTIVE)
        self.assertEqual([current["id"]],[g["id"] for g in client.cached_guides()])
        self.assertIsNone(Adviser(catalog()).match(guide(season_id="1"),GameState()))
        client._merge([guide(is_sub_expired=True)])
        self.assertEqual([],client.cached_guides())

    def test_mismatched_config_cannot_overwrite_valid_offline_cache(self):
        client=GuideClient(CACHE/f"season-{uuid4().hex}",season=ACTIVE)
        write_json(client.cache/"config.json",META)
        with patch.object(client,"request",return_value={**META,"sub_season_id":"2"}):
            self.assertEqual(META,client.config())
        self.assertTrue(client.version_mismatch)
        self.assertFalse(client.online)
        with self.assertRaises(RuntimeError):
            client.list_page()

    def test_two_candidates_follow_selected_environment_and_confirmed_ownership(self):
        a=Seen("a","员工甲","角色","备战",confidence=1)
        b=Seen("b","员工乙","角色","商店",confidence=1)
        environment=Seen("e2","e2","环境","已选",confidence=1)
        s=GameState(roles=[a],shop=[b],environment=environment)
        adviser=Adviser(catalog())
        candidates=[guide(),guide("second","b","e2")]
        self.assertEqual("first",adviser.rank(candidates,s)[0].guide["id"])
        s.roles.append(Seen("b","员工乙","角色","备战",confidence=1))
        self.assertEqual("second",adviser.rank(candidates,s)[0].guide["id"])
        environment.id="e1"
        self.assertEqual("first",adviser.rank(candidates,s)[0].guide["id"])
        s.mode="超频博弈"
        self.assertEqual([],adviser.rank(candidates,s))

    def test_shop_levels_use_new_weights_and_special_roles_have_no_normal_target(self):
        self.assertEqual((6,"搜牌"),target_level(guide(carry="b"),catalog()))
        self.assertEqual((None,"特殊来源"),target_level(guide(carry="s"),catalog()))

    def test_all_current_affixes_format_and_absorb_in_display_order(self):
        for language in ("zh","en","ja"):
            for name,_ in AFFIXES.values():
                with self.subTest(language=language,name=name):
                    effect=rule_description(name,language,True)
                    self.assertNotIn("{",effect)
                    self.assertNotIn("enc_",effect)
                    self.assertNotIn("未匹配",effect)
        self.assertIsNone(rule_id("形单影只",True))
        self.assertIn("20%",rule_description("侵蚀·第一位面强化","zh",True))
        state=GameState(enemy_difficulty=120,debuffs=["融资危机","吸星魔王","霸占舞台"])
        report=dict(advice(catalog(),state))
        self.assertIn("已被禁用",report["融资危机"])
        self.assertIn("70%",report["敌人基础倍率"])
        self.assertIn("105%",report["霸占舞台"])

    def test_rank_and_voyage_are_independent_of_the_enemy_number(self):
        recognizer=object.__new__(Recognizer)
        recognizer.catalog=catalog()
        state=recognizer.parse_rows([row("奇遇伙伴",850,90),row("汪汪丹",850,300),
            row("财富造物主12",105,325),row("敌人难度85",75,955)],SHAPE)
        self.assertEqual(("奇遇","A8·12",85,"汪汪丹"),
                         (state.scene,state.difficulty,state.enemy_difficulty,state.voyage.name))
        self.assertEqual("",state.voyage.id)

    def test_spotlight_offer_cannot_become_selected_without_game_confirmation(self):
        recognizer=object.__new__(Recognizer)
        recognizer.catalog=catalog()
        rows=[row("主角光环",880,95),row("1-8",610,20),
              row("测试光环",870,380),row("员工甲",865,480),row("确认",985,965)]
        offered=recognizer.parse_rows(rows,SHAPE)
        self.assertEqual(("光环选择","a"),(offered.scene,offered.spotlight_choices[0].equipped_to))
        self.assertEqual({},offered.spotlights)
        for confirm in (False,True):
            tracker=InvestmentSelection()
            tracker.observe(offered,rows,SHAPE,hwnd=1,now=1)
            tracker.click((.48,.48),now=2)
            if confirm:
                tracker.click((.55,.91),now=3)
            result=tracker.observe(GameState(scene="战斗"),[],SHAPE,hwnd=1,now=4)
            self.assertEqual(bool(result),confirm)
            if result:
                self.assertEqual((1,"a","已选"),(result.slot,result.equipped_to,result.zone))
                run=StateTracker()
                run.merge(GameState(spotlights={1:result}))
                self.assertEqual(result,run.merge(GameState(scene="准备")).spotlights[1])
                run.reset()
                self.assertFalse(run.state.spotlights)


if __name__ == "__main__":
    unittest.main()
