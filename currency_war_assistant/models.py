from __future__ import annotations

from dataclasses import dataclass, field, asdict
import time
import unicodedata


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return "".join(c for c in text if c.isalnum() or c=='+')


@dataclass
class Seen:
    id: str
    name: str
    kind: str
    zone: str = "待确认"
    slot: int = -1
    star: int | None = None
    confidence: float = 0.0
    source: str = "画面"
    box: tuple = ()
    at: float = field(default_factory=time.time)
    equipped_to: str = ""
    copies: int = 1


@dataclass
class GameState:
    difficulty: str = "普通 A8·30"
    scene: str = "未观察"
    round: str | None = None
    gold: int | None = None
    level: int | None = None
    xp: str | None = None
    hp: int | None = None
    capacity: int | None = None
    roles: list[Seen] = field(default_factory=list)
    shop: list[Seen] = field(default_factory=list)
    equipment: list[Seen] = field(default_factory=list)
    strategies: list[Seen] = field(default_factory=list)
    environment: Seen | None = None
    unresolved: list[dict] = field(default_factory=list)
    at: float = 0.0
    warning: str = ""
    manual_fields: set = field(default_factory=set)
    visible_zones: set = field(default_factory=set)

    def stage(self):
        if self.level is not None:
            return "Early" if self.level <=5 else "Middle" if self.level<=7 else "Final"
        if self.round:
            chapter = int(self.round.split("-")[0])
            return "Early" if chapter <= 1 else "Middle" if chapter == 2 else "Final"
        return "Early" if self.level is None or self.level <= 5 else "Middle" if self.level <= 7 else "Final"

    def owned_ids(self):
        return {r.id for r in self.roles if r.id and r.confidence >= .8 and r.zone in ("前台", "后台", "备战")}

    def snapshot(self):
        value = asdict(self)
        value["manual_fields"] = list(self.manual_fields)
        value["visible_zones"] = list(self.visible_zones)
        return value


class Catalog:
    def __init__(self, config: dict, knowledge: dict | None = None):
        self.config = config
        self.version = config.get("rpg_game_big_version", "未知")
        self.roles = {str(r["id"]): r for r in config.get("role_list", [])}
        self.equipment = {str(r["id"]): r for r in config.get("equipment_list", [])}
        def include_components(item):
            for recipe in item.get("compose_list", []):
                for component in recipe.get("childrens", []):
                    self.equipment.setdefault(str(component["id"]), component)
                    include_components(component)
        for item in config.get("equipment_list", []):
            include_components(item)
        self.strategies = {str(r["id"]): r for r in config.get("fight_augment_list", [])}
        self.environments = {str(r["id"]): {**r,"name":r.get("name") or r.get("title") or str(r["id"])} for r in config.get("portal_list", [])}
        self.bonds = {str(r["trait_id"]): r for r in config.get("trait_info_list", [])}
        self.knowledge = knowledge or {}
        self.kroles = {str(r["id"]): r for r in self.knowledge.get("roles", [])}
        self.kequipment = {normalize(r.get("name", "")): r for r in self.knowledge.get("equipment", [])}

    def pool(self, kind):
        return {"角色": self.roles, "装备": self.equipment, "策略": self.strategies, "环境": self.environments}[kind]

    def name(self, identifier: str):
        for pool in (self.roles, self.equipment, self.strategies, self.environments):
            if identifier in pool:
                return pool[identifier].get("name", identifier)
        return identifier

    def role_bonds(self, identifier):
        role = self.roles.get(identifier, {})
        return {str(b["id"]) for b in role.get("trait_details", [])}

    def cost(self, identifier):
        r = self.roles.get(identifier, {})
        return int(r.get("rarity", 0) or 0)
