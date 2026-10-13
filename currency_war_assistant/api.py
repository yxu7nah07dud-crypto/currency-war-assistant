from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import threading
import time
import urllib.request
import uuid

from .paths import read_json, write_json
from . import __version__
from .share import find_guide_by_code, normalize_share_code, trait_hints

BASE = "https://act-api-takumi.miyoushe.com/event/rpgcurrencywar"
WEB = "https://act.miyoushe.com/sr/event/currency-wars/index.html"
ORDERS = ("Hot", "CreatedTime")


class GuideClient:
    def __init__(self, cache: Path):
        self.cache = cache
        self.cache.mkdir(parents=True, exist_ok=True)
        self.headers = {
            "Content-Type": "application/json", "x-rpc-platform": "pc",
            "x-rpc-lang": "zh-cn", "x-rpc-currencywar-tourn": "tourn",
            "x-rpc-device_id": str(uuid.uuid4()), "Referer": "https://act.miyoushe.com/",
            "User-Agent": f"CurrencyWarAssistant/{__version__}",
        }
        self.online = False
        self.error = ""
        self.updated_at = 0.0
        self._lock = threading.RLock()
        self._scan_lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._guides = None
        self.coverage = {"state": "partial", "orders": {}}
        self._saved_at = 0.0
        self.page_delay = .35

    def request(self, path, body=None):
        payload = json.dumps(body).encode("utf8") if body is not None else None
        request = urllib.request.Request(BASE + path, data=payload, headers=self.headers)
        with urllib.request.urlopen(request, timeout=12) as response:
            value = json.load(response)
        if value.get("retcode") != 0 or value.get("data") is None:
            raise RuntimeError(value.get("message", "攻略读取失败"))
        return value["data"]

    def cached_config(self):
        return read_json(self.cache / "config.json", {}) or {}

    def config(self):
        try:
            config = self.request("/game/config?game=hkrpg")
            with self._lock:
                write_json(self.cache / "config.json", config)
            self.online, self.error = True, ""
            return config
        except Exception as error:
            self.online, self.error = False, str(error)
            return self.cached_config()

    def cached_guides(self):
        with self._lock:
            if self._guides is None:
                saved = read_json(self.cache / "guides.json", {}) or {}
                self.updated_at = saved.get("at", 0)
                self._guides = {g["id"]: g for g in saved.get("guides", []) if g.get("id")}
                for guide in self._guides.values():
                    guide.setdefault("last_seen",time.time())
                    guide.setdefault("missing_full_syncs",0)
                self.coverage = saved.get("coverage") or {"state": "partial", "orders": {}}
                if self.coverage.get("state") == "running":
                    self.coverage["state"] = "interrupted"
            return list(self._guides.values())

    def summary(self):
        with self._lock:
            guides = self.cached_guides()
            return {"count": len(guides), "codes": sum(bool(g.get("tourn_detail", {}).get("share_code")) for g in guides),
                    "coverage": deepcopy(self.coverage)}

    def _merge(self, items):
        with self._lock:
            self.cached_guides()
            for guide in items:
                identifier = guide.get("id")
                if not identifier:
                    continue
                old = self._guides.get(identifier, {})
                merged = {**old, **guide}
                merged["tourn_detail"] = {**old.get("tourn_detail", {}), **guide.get("tourn_detail", {})}
                if not merged.get("description"):
                    merged["description"] = old.get("description", "")
                self._guides[identifier] = merged

    def _save(self, force=False):
        with self._write_lock:
            with self._lock:
                if not force and time.monotonic() - self._saved_at < 10:
                    return
                snapshot={"at":self.updated_at,"guides":self.cached_guides(),
                          "coverage":deepcopy(self.coverage)}
                self._saved_at = time.monotonic()
            # Serialise large guide lists without blocking the UI's cache reads.
            write_json(self.cache / "guides.json", snapshot)

    def list_page(self, order="Hot", page=1, token="", role_ids=None, trait_ids=None):
        # Ordinary-mode public recommendation filters from the official site.
        # Server caps each page at ten. Larger requested limits cannot fix this.
        return self.request("/game/lineup/index", {
            "game": "hkrpg", "page": str(page), "limit": "10", "lineup_type": "Tourn",
            "next_page_token": token, "role_ids": role_ids or [], "trait_ids": trait_ids or [],
            "match_change_job": False, "match_hard": False, "order": order,
        })

    def detail(self, identifier):
        from urllib.parse import urlencode
        return self.request("/game/lineup/detail?" + urlencode({"id": identifier, "game": "hkrpg"}))["lineup"]

    def refresh(self, role_ids=None, pages=None, *, progress=None, cancel=None, stop_when=None, full=False, protected_ids=()):
        """Read both unfiltered public sort orders to their end, with resume.

        A page budget or early code match never constitutes complete coverage.
        Role-specific searches cannot establish completeness of the public list.
        """
        stopped = cancel or (lambda: False)
        while not self._scan_lock.acquire(timeout=.2):
            if stopped() or (stop_when and stop_when(self.cached_guides())):
                return self.cached_guides()
        try:
            guides = self.cached_guides()
            if stop_when and stop_when(guides):
                return guides
            # Recent complete coverage is a baseline, not a new completeness claim.
            # Refresh ranking heads and stop the latest stream on an entirely known page.
            with self._lock:
                recent = (not full and self.coverage.get("state") == "complete" and
                          time.time() - self.coverage.get("completed_at", 0) < 86400)
            if recent:
                known = {g["id"] for g in guides}
                try:
                    for order in ORDERS:
                        token, page, tokens = "", 1, set()
                        while True:
                            if stopped() or (stop_when and stop_when(self.cached_guides())):
                                return self.cached_guides()
                            if pages is not None and page > pages:
                                return self.cached_guides()
                            result = self.list_page(order, page, token)
                            items = result.get("list", [])
                            next_token = result.get("next_page_token", "")
                            self._merge(items)
                            self.online, self.error = True, ""
                            self.updated_at = time.time()
                            if progress:
                                progress(self.summary())
                            if (not items or not next_token or
                                (order == "Hot" and page >= 3) or
                                (order == "CreatedTime" and all(g.get("id") in known for g in items))):
                                break
                            if next_token == token or next_token in tokens:
                                raise RuntimeError("公开列表分页重复，增量更新已停止。")
                            tokens.add(next_token)
                            token, page = next_token, page + 1
                            time.sleep(self.page_delay)
                except Exception as error:
                    self.online, self.error = False, str(error)
                return self.cached_guides()
            with self._lock:
                resume = self.coverage.get("state") in ("running", "interrupted", "partial")
                previous = self.coverage.get("orders", {}) if resume else {}
                self.coverage = {"state": "running", "started_at": self.coverage.get("started_at", time.time()) if resume else time.time(),
                                 "orders": deepcopy(previous), "scope": "public-normal-recommendations"}
                self.error = ""
            try:
                for order in ORDERS:
                    stream = self.coverage["orders"].setdefault(order, {"page": 0, "token": "", "done": False,"seen":[]})
                    if stream.get("done"):
                        continue
                    tokens, fingerprints = set(), set()
                    processed = 0
                    restarted = False
                    while not stream["done"]:
                        if stopped() or (stop_when and stop_when(self.cached_guides())):
                            self.coverage["state"] = "interrupted"
                            return self.cached_guides()
                        if pages is not None and processed >= pages:
                            self.coverage["state"] = "partial"
                            return self.cached_guides()
                        token = stream.get("token", "")
                        page = stream.get("page", 0) + 1
                        try:
                            result = self.list_page(order, page, token)
                        except Exception:
                            if not token or restarted:
                                raise
                            # Persist the reset so a subsequent attempt cannot keep
                            # resuming the same invalid cursor. Retry this stream once.
                            restarted = True
                            with self._lock:
                                stream.update(page=0, token="", done=False,seen=[])
                            tokens.clear(); fingerprints.clear()
                            continue
                        items = result.get("list", [])
                        next_token = result.get("next_page_token", "")
                        fingerprint = tuple(g.get("id") for g in items)
                        if next_token and (next_token == token or next_token in tokens or (items and fingerprint in fingerprints)):
                            raise RuntimeError("公开列表分页重复，未将本次同步标记为完整；请重新同步。")
                        tokens.add(next_token)
                        fingerprints.add(fingerprint)
                        self._merge(items)
                        stream["seen"]=list(set(stream.get("seen",[]))|{g["id"] for g in items if g.get("id")})
                        self.online, self.error = True, ""
                        self.updated_at = time.time()
                        stream.update(page=page, token=next_token, done=not items or not next_token)
                        processed += 1
                        self._save()
                        if progress:
                            progress(self.summary())
                        if not stream["done"]:
                            time.sleep(self.page_delay)
                with self._lock:
                    seen=set().union(*(set(s.get("seen",[])) for s in self.coverage["orders"].values()))
                    # Legacy resumed streams lack seen IDs: do not age unseen
                    # records until a complete scan with both streams tracked.
                    tracked=all("seen" in s for s in self.coverage["orders"].values())
                    protected=set(protected_ids() if callable(protected_ids) else protected_ids)
                    self._finish_retention(seen,protected,tracked)
                    self.coverage.update(state="complete", completed_at=time.time())
            except Exception as error:
                self.online, self.error = False, str(error)
                with self._lock:
                    self.coverage.update(state="interrupted", error=str(error))
            return self.cached_guides()
        finally:
            try:
                self._save(force=True)
            finally:
                self._scan_lock.release()
            if progress:
                progress(self.summary())

    def _finish_retention(self,seen,protected,tracked=True):
        """Only successful full snapshots age absent guides; partial reads never do."""
        now=time.time()
        for identifier,guide in list(self._guides.items()):
            if identifier in seen:
                self._guides[identifier]={**guide,"last_seen":now,"missing_full_syncs":0}
            elif tracked:
                missing=guide.get("missing_full_syncs",0)+1
                if missing>=2 and identifier not in protected:
                    del self._guides[identifier]
                else:self._guides[identifier]={**guide,"last_seen":guide.get("last_seen",now),"missing_full_syncs":missing}

    def _resolved_detail(self, guide, code):
        try:
            full = self.detail(guide["id"])
        except Exception as error:
            self.online, self.error = False, str(error)
            if not guide.get("description") or not guide.get("tourn_detail", {}).get("role_stages"):
                raise
            return guide
        if find_guide_by_code([full], code) is None:
            raise RuntimeError("官方详情的攻略码不一致，未锁定该攻略。")
        self._merge([full])
        self.online, self.error = True, ""
        self.updated_at = time.time()
        self._save(force=True)
        return full

    def resolve_code(self, value, *, progress=None, cancel=None, protected_ids=()):
        """Find exact share code through official lists and validate detail.

        No unsupported share-code endpoint or decoder is assumed. A readable
        title can narrow trait filters; raw codes still search every page.
        """
        code = normalize_share_code(value)
        if not code:
            return None
        stopped = cancel or (lambda: False)
        guide = find_guide_by_code(self.cached_guides(), code)
        if guide:
            return None if stopped() else self._resolved_detail(guide, code)
        hints = trait_hints(value, self.cached_config())
        if hints:
            token = ""
            page, tokens = 1, set()
            while True:
                if stopped():
                    return None
                try:
                    result = self.list_page(trait_ids=hints, page=page, token=token)
                    self._merge(result.get("list", []))
                    self.updated_at=time.time()
                    self._save()
                    if progress:
                        summary=self.summary()
                        summary["lookup_pages"]=page
                        progress(summary)
                    guide = find_guide_by_code(self.cached_guides(), code)
                    if guide:
                        return self._resolved_detail(guide, code)
                    next_token = result.get("next_page_token", "")
                    if not result.get("list") or not next_token:
                        break
                    if next_token==token or next_token in tokens:
                        break
                    tokens.add(next_token)
                    token=next_token
                    page+=1
                except Exception:
                    break
                time.sleep(self.page_delay)
        while self._scan_lock.locked():
            if stopped():
                return None
            guide = find_guide_by_code(self.cached_guides(), code)
            if guide:
                return self._resolved_detail(guide, code)
            if progress:
                progress(self.summary())
            time.sleep(.5)
        guide = find_guide_by_code(self.cached_guides(), code)
        recent_complete=(self.coverage.get("state")=="complete" and
                         time.time()-self.coverage.get("completed_at",0)<300)
        if not guide and not recent_complete:
            self.refresh(progress=progress, cancel=stopped,
                         stop_when=lambda guides: find_guide_by_code(guides, code) is not None,
                         full=True, protected_ids=protected_ids)
            guide = find_guide_by_code(self.cached_guides(), code)
        if stopped():
            return None
        if guide:
            return self._resolved_detail(guide, code)
        if self.error:
            raise RuntimeError(self.error)
        return None

    def enrich(self, guides, ids):
        # Do not overwrite a code lookup's new guides with a stale list snapshot.
        with self._lock:
            known = {g["id"] for g in self.cached_guides()}
            self._merge([g for g in guides if g.get("id") not in known])
        for identifier in ids:
            try:
                self._merge([self.detail(identifier)])
            except Exception as error:
                self.error, self.online = str(error), False
                break
            time.sleep(.1)
        self._save(force=True)
        return self.cached_guides()


def guide_url(identifier):
    return WEB + "#/lineup/" + identifier
