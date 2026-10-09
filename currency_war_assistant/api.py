from __future__ import annotations

import json
from pathlib import Path
import threading
import time
import urllib.request
import uuid

from .paths import read_json, write_json

BASE = "https://act-api-takumi.miyoushe.com/event/rpgcurrencywar"
WEB = "https://act.miyoushe.com/sr/event/currency-wars/index.html"


class GuideClient:
    def __init__(self, cache: Path):
        self.cache = cache
        self.cache.mkdir(parents=True, exist_ok=True)
        self.headers = {
            "Content-Type": "application/json", "x-rpc-platform": "pc",
            "x-rpc-lang": "zh-cn", "x-rpc-currencywar-tourn": "tourn",
            "x-rpc-device_id": str(uuid.uuid4()), "Referer": "https://act.miyoushe.com/",
            "User-Agent": "CurrencyWarCompanion/1.0",
        }
        self.online = False
        self.error = ""
        self.updated_at = 0.0
        self._lock = threading.Lock()

    def request(self, path, body=None):
        payload = json.dumps(body).encode("utf8") if body is not None else None
        request = urllib.request.Request(BASE + path, data=payload, headers=self.headers)
        with urllib.request.urlopen(request, timeout=12) as response:
            value = json.load(response)
        if value.get("retcode") != 0 or value.get("data") is None:
            raise RuntimeError(value.get("message", "攻略读取失败"))
        return value["data"]

    def cached_config(self):
        # The public source distribution intentionally contains no game data.
        # Offline data is created by the user after a normal online refresh.
        return read_json(self.cache / "config.json", {}) or {}

    def config(self):
        try:
            config = self.request("/game/config?game=hkrpg")
            write_json(self.cache / "config.json", config)
            self.online = True
            return config
        except Exception as error:
            self.online = False
            self.error = str(error)
            return self.cached_config()

    def cached_guides(self):
        saved = read_json(self.cache / "guides.json", {}) or {}
        self.updated_at = saved.get("at", 0)
        return saved.get("guides", [])

    def list_page(self, order="Hot", page=1, token="", role_ids=None, trait_ids=None):
        # These are read-only search fields from the public site's own client.
        return self.request("/game/lineup/index", {
            "game": "hkrpg", "page": str(page), "limit": "10", "lineup_type": "Tourn",
            "next_page_token": token, "role_ids": role_ids or [], "trait_ids": trait_ids or [],
            "match_change_job": False, "match_hard": False, "order": order,
        })

    def detail(self, identifier):
        from urllib.parse import urlencode
        data = self.request("/game/lineup/detail?" + urlencode({"id": identifier, "game": "hkrpg"}))
        return data["lineup"]

    def refresh(self, role_ids=None, pages=5):
        with self._lock:
            guides = {g["id"]: g for g in self.cached_guides()}
            success = 0
            try:
                queries = [("Hot", []), ("CreatedTime", [])]
                queries += [("Hot", [r]) for r in (role_ids or [])[:3]]
                for order, roles in queries:
                    token = ""
                    for page in range(1, (pages if not roles else 2) + 1):
                        result = self.list_page(order, page, token, role_ids=roles)
                        items = result.get("list", [])
                        success += 1
                        for guide in items:
                            old = guides.get(guide["id"], {})
                            # Keep the richer detail, but never overwrite a newly reported expiry flag.
                            merged = {**old, **guide}
                            merged["tourn_detail"] = {**old.get("tourn_detail", {}), **guide.get("tourn_detail", {})}
                            if not merged.get("description"):
                                merged["description"] = old.get("description", "")
                            guides[guide["id"]] = merged
                        token = result.get("next_page_token", "")
                        if not items or not token:
                            break
                        time.sleep(.12)
                self.online = True
                self.error = ""
            except Exception as error:
                self.online = False
                self.error = str(error)
            if success:
                self.updated_at = time.time()
                write_json(self.cache / "guides.json", {"at": self.updated_at, "guides": list(guides.values())})
            return list(guides.values())

    def enrich(self, guides, ids):
        by_id = {g["id"]: g for g in guides}
        for identifier in ids:
            try:
                by_id[identifier] = self.detail(identifier)
            except Exception as error:
                self.error = str(error)
                self.online = False
                break
            time.sleep(.1)
        result = list(by_id.values())
        write_json(self.cache / "guides.json", {"at": self.updated_at, "guides": result})
        return result


def guide_url(identifier):
    return WEB + "#/lineup/" + identifier
