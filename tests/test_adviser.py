import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from currency_war_assistant.models import Catalog, GameState, Seen, normalize
from currency_war_assistant.strategy import Adviser, recipes, required_start
from currency_war_assistant.vision import Recognizer, StateTracker
from currency_war_assistant.api import GuideClient
from currency_war_assistant.controller import frames_stable, normalize_share_code, find_guide_by_code
from currency_war_assistant.capture import WindowCapture, Window, CaptureUnavailable

TMP_ROOT = Path(__file__).resolve().parent / "_cache"
TMP_ROOT.mkdir(exist_ok=True)


def cache_dir(name):
    path = TMP_ROOT / name
    path.mkdir(parents=True, exist_ok=True)
    for filename in ("config.json", "guides.json"):
        candidate = path / filename
        if candidate.exists():
            candidate.unlink()
    return path


def fixture_catalog():
    return Catalog({
        "rpg_game_big_version": "public-fixture",
        "role_list": [
            {"id": "core", "name": "核心角色", "rarity": 3,
             "trait_details": [{"id": "bond"}],
             "skills": [{"front_back_type": "Front", "skill_stars": [{"desc": "提供稳定输出"}]}]},
            {"id": "support", "name": "辅助角色", "rarity": 2, "trait_details": [{"id": "bond"}]},
            {"id": "tank", "name": "坦克角色", "rarity": 2, "trait_details": []},
            {"id": "shop", "name": "商店角色", "rarity": 1, "trait_details": []},
        ],
        "equipment_list": [
            {"id": "target-gear", "name": "目标装备", "compose_list": [
                {"childrens": [{"id": "material-a", "name": "材料甲"},
                                {"id": "material-a", "name": "材料甲"}]}
            ]},
            {"id": "material-a", "name": "材料甲", "compose_list": []},
        ],
        "fight_augment_list": [{"id": "invest", "name": "稳健投资"}],
        "portal_list": [{"id": "arena", "name": "平衡环境"}],
        "trait_info_list": [{"trait_id": "bond", "name": "同心"}],
    }, {})


def fixture_guide():
    return {
        "id": "fixture-guide",
        "title": "公开示例阵容",
        "description": "开局确定有核心角色。必须选择稳健投资。",
        "tourn_detail": {
            "share_code": "PUBLIC-FIXTURE-001",
            "rpg_game_big_version": "public-fixture",
            "role_stages": [
                {"stage": "Early", "front_roles": [{"id": "core", "name": "核心角色", "rarity": 3}], "back_roles": []},
                {"stage": "Final", "front_roles": [{"id": "core", "name": "核心角色", "rarity": 3, "is_carry": True, "first_equipments": [{"id": "target-gear"}]}],
                 "back_roles": [{"id": "support", "name": "辅助角色", "rarity": 2}]},
            ],
            "first_fight_augments": [{"id": "invest", "name": "稳健投资"}],
            "portals": [{"id": "arena", "name": "平衡环境"}],
        },
    }


class AdviserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = fixture_catalog()
        cls.guides = [fixture_guide()]
        cls.guide = cls.guides[0]
        cls.adviser = Adviser(cls.catalog)

    def owned(self, identifier, zone="备战", star=1):
        return Seen(identifier, self.catalog.name(identifier), "角色", zone, star=star, confidence=1, source="手动")

    def test_expired_is_never_recommended_even_if_locked(self):
        guide = copy.deepcopy(self.guide)
        guide["tourn_detail"]["is_sub_expired"] = True
        self.assertEqual([], self.adviser.rank([guide], GameState(), guide["id"]))

    def test_explicit_prerequisite_is_not_satisfied_by_other_roles(self):
        state = GameState(scene="准备", gold=20, level=5,
                          roles=[self.owned("support"), self.owned("tank", "后台")])
        match = self.adviser.match(self.guide, state)
        self.assertTrue(match.blocked)
        self.assertIn("core", required_start(self.guide, self.catalog))
        self.assertLessEqual(match.score, 25)
        self.assertIn("核心角色", match.missing)

    def test_prerequisite_requires_owned_not_shop_only(self):
        guide = copy.deepcopy(self.guide)
        guide["description"] = "开局确定有核心角色。"
        state = GameState(shop=[self.owned("core", "商店")])
        self.assertTrue(self.adviser.match(guide, state).blocked)
        state.roles = [self.owned("core", "前台")]
        self.assertFalse(self.adviser.match(guide, state).blocked)

    def test_unknown_economy_cannot_issue_specific_spend(self):
        guide = copy.deepcopy(self.guide)
        guide["description"] = "开局确定有核心角色。"
        state = GameState(scene="准备", roles=[self.owned("core", "前台")])
        advice = dict(self.adviser.advice(state, self.adviser.match(guide, state)))
        self.assertIn("待确认", advice["经济"])

    def test_unknown_position_is_not_owned(self):
        self.assertEqual(set(), GameState(roles=[self.owned("core", "待确认")]).owned_ids())

    def test_names_do_not_conflate_similar_names(self):
        self.assertNotEqual(normalize("花火"), normalize("火花"))
        self.assertNotEqual(normalize("特战资金"), normalize("特战资金+"))
        ids = {r["name"]: i for i, r in self.catalog.roles.items()}
        self.assertNotEqual(ids["核心角色"], ids["辅助角色"])

    def test_pasted_guide_code_ignores_spaces_and_newlines(self):
        code = self.guide["tourn_detail"]["share_code"]
        spaced = "  ".join(code[i:i + 8] for i in range(0, len(code), 8))
        self.assertEqual(code.replace(" ", ""), normalize_share_code(spaced))
        self.assertEqual(code, normalize_share_code("攻略码：" + code))
        self.assertIs(find_guide_by_code(self.guides, spaced), self.guide)
        self.assertIsNone(find_guide_by_code(self.guides, "not-a-guide-code"))

    def test_duplicate_material_recipe_requires_two_copies(self):
        self.assertTrue(any(recipe.get("material-a") == 2 for recipe in recipes(self.catalog, "target-gear")))

    def test_battle_does_not_advise_shop_actions(self):
        advice = self.adviser.advice(GameState(scene="战斗"), None)
        self.assertEqual(1, len(advice))
        self.assertIn("战斗", advice[0][1])

    def test_shop_is_cleared_when_not_visible(self):
        tracker = StateTracker()
        tracker.merge(GameState(scene="准备", shop=[self.owned("core", "商店")]))
        tracker.merge(GameState(scene="战斗"))
        self.assertEqual([], tracker.state.shop)

    def test_manual_inventory_survives_hidden_panels(self):
        tracker = StateTracker()
        tracker.state.roles = [self.owned("core", "前台")]
        tracker.merge(GameState(scene="战斗"))
        self.assertIn("core", tracker.state.owned_ids())

    def test_new_game_clears_previous_gold_shop_and_inventory(self):
        tracker = StateTracker()
        tracker.state.gold = 90
        tracker.state.roles = [self.owned("core")]
        tracker.manual_shop = [self.owned("core", "商店")]
        tracker.reset()
        self.assertIsNone(tracker.state.gold)
        self.assertEqual([], tracker.state.roles)
        self.assertIsNone(tracker.manual_shop)

    def test_ocr_numeric_positions_and_resolution_scaling(self):
        recognizer = object.__new__(Recognizer)
        rows = [{"text": t, "confidence": .99, "box": b} for t, b in [
            ("1-6", (696, 9, 757, 43)), ("88", (1019, 13, 1055, 41)), ("14", (1092, 14, 1124, 39)),
            ("5206.1万", (1702, 260, 1800, 288)), ("我方行动中", (1721, 982, 1834, 1012)), ("101003693", (33, 1040, 160, 1063))]]
        state = recognizer.parse_rows(rows, (1080, 1920, 3))
        self.assertEqual(("1-6", 88, 14, "战斗"), (state.round, state.hp, state.gold, state.scene))
        scaled = [{**r, "box": tuple(x // 2 for x in r["box"])} for r in rows]
        state = recognizer.parse_rows(scaled, (540, 960, 3))
        self.assertEqual((88, 14), (state.hp, state.gold))

    def test_offline_cache_uses_only_user_cache(self):
        directory = cache_dir("offline")
        client = GuideClient(directory)
        (directory / "config.json").write_text(json.dumps({"rpg_game_big_version": "public-fixture"}), encoding="utf8")
        (directory / "guides.json").write_text(json.dumps({"at": 1, "guides": self.guides}), encoding="utf8")
        with patch.object(client, "request", side_effect=OSError("offline")):
            config = client.config()
            guides = client.refresh(pages=1)
        self.assertEqual("public-fixture", config["rpg_game_big_version"])
        self.assertEqual(len(self.guides), len(guides))
        self.assertFalse(client.online)
        self.assertTrue(guides[0]["tourn_detail"]["share_code"])

    def test_no_cache_starts_empty_instead_of_bundled_game_data(self):
        client = GuideClient(cache_dir("empty"))
        self.assertEqual({}, client.cached_config())
        self.assertEqual([], client.cached_guides())

    def test_normal_mode_does_not_request_overclock_filter(self):
        client = GuideClient(cache_dir("normal"))
        with patch.object(client, "request", return_value={"list": []}) as request:
            client.list_page(role_ids=["core"])
        body = request.call_args.args[1]
        self.assertFalse(body["match_hard"])
        self.assertEqual("Tourn", body["lineup_type"])

    def test_inventory_duplicates_replace_and_empty_visible_inventory_clears(self):
        tracker = StateTracker()
        items = [Seen("material-a", "材料甲", "装备", "库存", slot=i, source="库存图标", confidence=.99) for i in (0, 1)]
        tracker.merge(GameState(scene="准备", equipment=items, visible_zones={"库存"}))
        self.assertEqual(2, len(tracker.state.equipment))
        tracker.merge(GameState(scene="准备", equipment=items[:1], visible_zones={"库存"}))
        self.assertEqual(1, len(tracker.state.equipment))
        tracker.merge(GameState(scene="准备", visible_zones={"库存"}))
        self.assertEqual([], tracker.state.equipment)

    def test_sold_auto_unit_is_not_kept_when_panel_is_visible(self):
        tracker = StateTracker()
        auto = self.owned("core")
        auto.source = "文字"
        tracker.merge(GameState(scene="准备", roles=[auto]))
        tracker.merge(GameState(scene="准备", visible_zones={"备战"}))
        self.assertNotIn("core", tracker.state.owned_ids())

    def test_corrected_false_icon_is_suppressed_for_this_game(self):
        tracker = StateTracker()
        tracker.ignored.add(("角色", "core", "备战"))
        auto = self.owned("core")
        auto.source = "文字"
        tracker.merge(GameState(scene="准备", roles=[auto]))
        self.assertEqual([], tracker.state.roles)
        tracker.reset()
        tracker.merge(GameState(scene="准备", roles=[auto]))
        self.assertIn("core", tracker.state.owned_ids())

    def test_shop_animation_and_resolution_change_are_not_stable_frames(self):
        first = np.zeros((1080, 1920, 3), dtype=np.uint8)
        second = first.copy()
        second[50:340, 350:1690] = 255
        self.assertFalse(frames_stable(first, second))
        self.assertFalse(frames_stable(first, first[::2, ::2]))
        self.assertTrue(frames_stable(first, first.copy()))

    def test_minimized_closed_or_stale_capture_never_produces_frame(self):
        capture = WindowCapture()
        capture.window = Window(1, "test", 1920, 1080)
        capture.closed = False
        with patch("currency_war_assistant.capture._user32") as user:
            user.return_value.IsWindow.return_value = True
            user.return_value.IsIconic.return_value = True
            with self.assertRaises(CaptureUnavailable):
                capture.latest()
            user.return_value.IsIconic.return_value = False
            capture._at = 0
            capture._frame = np.arange(300, dtype=np.uint8).reshape(10, 10, 3)
            with self.assertRaises(CaptureUnavailable):
                capture.latest()
            user.return_value.IsWindow.return_value = False
            with self.assertRaises(CaptureUnavailable):
                capture.latest()

    def test_blocked_guide_never_recommends_spending_to_force_its_core(self):
        state = GameState(scene="准备", gold=90, level=5, roles=[self.owned("support")])
        match = self.adviser.match(self.guide, state)
        advice = dict(self.adviser.advice(state, match))
        self.assertIn("保留金币", advice["经济"])

    def test_required_strategy_is_not_met_by_visible_unselected_choice(self):
        identifier, item = next(iter(self.catalog.strategies.items()))
        guide = copy.deepcopy(self.guide)
        guide["description"] = "必须选择" + item["name"] + "。"
        state = GameState(roles=[self.owned("core")], strategies=[Seen(identifier, item["name"], "策略", "待选", confidence=1)])
        self.assertTrue(self.adviser.match(guide, state).blocked)
        state.strategies[0].zone = "已选"
        self.assertFalse(self.adviser.match(guide, state).blocked)

    def test_required_environment_is_downgraded_until_confirmed(self):
        identifier, item = next(iter(self.catalog.environments.items()))
        guide = copy.deepcopy(self.guide)
        guide["description"] = "前提是" + item["name"] + "。"
        state = GameState(roles=[self.owned("core")])
        self.assertTrue(self.adviser.match(guide, state).blocked)
        state.environment = Seen(identifier, item["name"], "环境", "已选", confidence=1)
        self.assertFalse(self.adviser.match(guide, state).blocked)


if __name__ == "__main__":
    unittest.main()
