from __future__ import annotations

from collections import deque
from copy import deepcopy
import logging
import json
import queue
import threading
import time

import cv2

from .api import GuideClient
from .capture import WindowCapture, CaptureUnavailable
from .models import Catalog
from .paths import write_json,read_json
from .localization import translate
from .strategy import Adviser
from .vision import Recognizer, StateTracker
from .share import normalize_share_code, find_guide_by_code


def frames_stable(first,second):
    if first.shape!=second.shape:return False
    a=cv2.resize(first,(192,108));b=cv2.resize(second,(192,108))
    delta=cv2.absdiff(a,b)
    # Include the upper shop cards as well as the lower formation area.
    return float(delta[70:].mean())<=16 and float(delta[5:34,35:169].mean())<=12


class Controller:
    def __init__(self,data):
        self.data=data
        self.events=queue.Queue()
        self.client=GuideClient(data / "cache")
        # The public source distribution contains no copied game/wiki database.
        # The catalog is populated from the read-only public endpoint after startup.
        self.catalog=Catalog(self.client.cached_config(),{})
        self.guides=self.client.cached_guides()
        self.language=read_json(data / "settings.json",{}).get("language","zh")
        self.adviser=Adviser(self.catalog,self.language)
        self.capture=WindowCapture()
        self.tracker=StateTracker()
        self.recognizer=None
        self.image=None
        self.rows=[]
        self.matches=[]
        self.locked=""
        self.locked_code=""
        self.locked_title=""
        self.lookup={"state":"idle"}
        self._lookup_generation=0
        self.running=False
        self.closing=False
        self._wake=threading.Event()
        self._network_busy=False
        self._network_at=0
        self._signature=None
        self._enrich_busy=set()
        self._enrich_at={}
        self._mutex=threading.RLock()
        self.times=deque(maxlen=20)
        self.last_result={}
        threading.Thread(target=self._loop,daemon=True,name="local-observer").start()

    def emit(self,kind,value):
        self.events.put((kind,value))

    def initialize(self):
        self.refresh_guides()

    def start(self,window):
        self.running=False
        self.capture.start(window)
        self.running=True
        self._wake.set()
        self.emit("status","正在初始化本地识别…")

    def pause(self):
        self.running=False
        self.emit("status","已暂停观察；保留当前记录。")

    def resume(self):
        if not self.capture.window or self.capture.closed:
            self.emit("status","请先选择正在运行的游戏窗口。")
            return
        self.running=True
        self._wake.set()

    def immediate(self):
        if self.capture.window and not self.capture.closed:
            self.running=True
            self._wake.set()
        else:
            self.emit("status","请先选择游戏窗口并开始观察。")

    def apply_guide_code(self, code):
        with self._mutex:
            self._lookup_generation += 1
            generation = self._lookup_generation
        def cancelled():
            return self.closing or generation != self._lookup_generation
        def publish(state, **values):
            with self._mutex:
                if cancelled():
                    return
                self.lookup={"state":state,**values}
            self.emit("guide_lookup",None)
        publish("searching",pages=0)
        def progress(summary):
            pages=sum(s.get("page",0) for s in summary["coverage"].get("orders",{}).values())+summary.get("lookup_pages",0)
            publish("searching",pages=pages)
            self.emit("network",None)
        def worker():
            try:
                if not self.catalog.roles:
                    self._update_catalog(self.client.config())
                guide=self.client.resolve_code(code,progress=progress,cancel=cancelled,
                                               protected_ids=lambda:{self.locked} if self.locked else set())
                with self._mutex:
                    if cancelled():
                        return
                    self.guides=self.client.cached_guides()
                    if guide is None:
                        publish("not_found")
                    elif self.adviser.match(guide,self.tracker.state) is None:
                        publish("invalid",title=guide.get("title",""))
                    else:
                        self.locked=guide["id"]
                        self.locked_code=normalize_share_code(code)
                        self.locked_title=guide.get("title","已粘贴攻略")
                        publish("locked",title=self.locked_title,
                                version=guide.get("tourn_detail",{}).get("rpg_game_big_version","?"),
                                current=self.catalog.version)
                self.recalculate()
            except Exception as error:
                publish("error",error=str(error))
                logging.exception("guide code lookup failed")
            finally:
                self.emit("network",None)
        threading.Thread(target=worker,daemon=True,name="guide-code-lookup").start()
        return True

    def clear_guide_lock(self):
        with self._mutex:
            self._lookup_generation += 1
            self.lookup={"state":"idle"}
            self.locked = ""
            self.locked_code = ""
            self.locked_title = ""
        self.emit("guide_lookup",None)
        self.recalculate()
        self.emit("status", "已解除本局攻略锁定，恢复自动匹配。")

    def lock_guide(self,guide):
        code=guide.get("tourn_detail",{}).get("share_code","")
        if code:return self.apply_guide_code(code)
        with self._mutex:
            if not guide.get("id") or self.adviser.match(guide,self.tracker.state) is None:
                self.lookup={"state":"invalid","title":guide.get("title","")}
                accepted=False
            else:
                self._lookup_generation+=1
                self.locked=guide["id"];self.locked_code="";self.locked_title=guide.get("title","")
                if not any(g.get("id")==guide["id"] for g in self.guides):self.guides.append(guide)
                self.lookup={"state":"locked","title":self.locked_title,
                             "version":guide.get("tourn_detail",{}).get("rpg_game_big_version","?"),"current":self.catalog.version}
                accepted=True
        self.emit("guide_lookup",None);self.recalculate(enrich=False)
        return accepted

    def _update_catalog(self,config):
        if config:
            with self._mutex:
                catalog=Catalog(config,self.catalog.knowledge)
                self.catalog=catalog
                self.adviser=Adviser(catalog,self.language)
                if self.recognizer:
                    self.recognizer.catalog=catalog

    def refresh_guides(self,force=False):
        if self._network_busy or (not force and time.monotonic()-self._network_at<300):
            self.emit("network",None)
            return
        self._network_busy=True
        self._network_at=time.monotonic()
        def worker():
            try:
                self._update_catalog(self.client.config())
                last_render=0.0
                def progress(summary):
                    nonlocal last_render
                    self.emit("network",None)
                    if time.monotonic()-last_render>=10 or summary["coverage"].get("state")!="running":
                        with self._mutex:
                            self.guides=self.client.cached_guides()
                        self.recalculate()
                        last_render=time.monotonic()
                guides=self.client.refresh(progress=progress,cancel=lambda:self.closing,
                                           protected_ids=lambda:{self.locked} if self.locked else set())
                if self.closing:
                    return
                with self._mutex:
                    self.guides=guides
                self.recalculate()
                self.emit("network",None)
            except Exception:
                logging.exception("guide refresh failed")
                self.emit("status","攻略网络暂不可用，继续使用本地缓存。")
            finally:
                self._network_busy=False
        threading.Thread(target=worker,daemon=True,name="public-guide-reader").start()

    def recalculate(self,enrich=True):
        with self._mutex:
            state=self.tracker.state
            self.matches=self.adviser.rank(self.guides,state,self.locked)
            self.last_result={"state":state.snapshot(),"matches":[{"id":m.guide["id"],"score":round(m.score,1),"blocked":m.blocked} for m in self.matches],"locked_guide":{"id":self.locked,"code":self.locked_code,"title":self.locked_title} if self.locked else None,"processing_seconds":round(self.times[-1],2) if self.times else None,"guide_updated_at":self.client.updated_at}
            advice=self.adviser.advice(state,self.matches[0] if self.matches else None,locked=bool(self.locked))
            self.last_result["advice"]=advice
            if self.locked and not any(m.guide["id"]==self.locked for m in self.matches):
                advice.insert(0,(translate(self.language,"locked_invalid_heading"),translate(self.language,"locked_invalid_body")))
            self.emit("result",{"state":deepcopy(state),"matches":self.matches,"advice":advice})
        if enrich:self.enrich_current()

    def enrich_current(self):
        """Fetch missing current details independently of public-list refreshes."""
        with self._mutex:
            now=time.monotonic()
            ids=[m.guide["id"] for m in self.matches if not m.guide.get("description")
                 and m.guide["id"] not in self._enrich_busy
                 and now-self._enrich_at.get(m.guide["id"],float('-inf'))>=60]
            if not ids or self.closing:return
            self._enrich_busy.update(ids)
            for identifier in ids:self._enrich_at[identifier]=now
            guides=list(self.guides)
        def worker():
            try:
                refreshed=self.client.enrich(guides,ids)
                with self._mutex:self.guides=refreshed
            except Exception:
                logging.exception("current guide detail enrichment failed")
            finally:
                with self._mutex:self._enrich_busy.difference_update(ids)
            if not self.closing:
                self.recalculate()
                self.emit("network",None)
        threading.Thread(target=worker,daemon=True,name="current-guide-detail-reader").start()

    def get_state(self):
        with self._mutex:
            return deepcopy(self.tracker.state)

    def set_language(self,language,recalculate=True):
        with self._mutex:
            self.language=language if language in ('zh','en','ja') else 'zh'
            self.adviser.language=self.language
        if recalculate:self.recalculate()

    def snapshot(self):
        with self._mutex:
            return self.tracker.state.snapshot()

    def save_numbers(self,values):
        import re
        parsed={}
        for key,value in values.items():
            if key not in ("round","gold","level","hp"):raise ValueError("未知数值字段")
            value=str(value).strip()
            if key=="round":
                if value and not re.fullmatch(r"[1-5]-\d{1,2}",value):raise ValueError("阶段格式应为1-6")
                parsed[key]=value or None
            else:
                number=int(value) if value else None
                if number is not None and not (1 if key=="level" else 0)<=number<=(10 if key=="level" else 999):raise ValueError("数值超出范围")
                parsed[key]=number
        with self._mutex:
            for key,value in parsed.items():setattr(self.tracker.state,key,value)
            self.tracker.state.manual_fields.update(parsed)
            self.tracker.state.warning="经济数值为手动纠正；再次读取到可靠数值或进入新阶段后会更新。"
        self.recalculate()

    def correct_item(self,item,original=None):
        with self._mutex:
            state=self.tracker.state
            item=deepcopy(item)
            self.tracker.ignored.discard((item.kind,item.id,item.zone))
            if original and original.id!=item.id and original.kind==item.kind:
                self.tracker.ignored.add((original.kind,original.id,original.zone))
                for pool in (state.roles,state.shop,state.equipment,state.strategies,state.investment_choices):
                    pool[:]=[r for r in pool if not(r.id==original.id and r.zone==original.zone)]
            if item.kind in ("环境","策略") and item.zone=="待选":
                pool=state.investment_choices
                if item.slot<0:
                    used={r.slot for r in pool}
                    item.slot=next((s for s in range(3) if s not in used),-1)
                if item.slot>=0:pool[:]=[r for r in pool if r.slot!=item.slot]
            else:
                pool=state.roles if item.kind=="角色" and item.zone!="商店" else state.shop if item.kind=="角色" else state.equipment if item.kind=="装备" else state.strategies if item.kind=="策略" else None
                if item.kind in ("环境","策略") and item.zone=="已选":
                    state.investment_choices[:]=[r for r in state.investment_choices if not(r.kind==item.kind and r.id==item.id)]
            if pool is not None:
                pool[:]=[r for r in pool if not(r.id==item.id and r.zone==item.zone)]
                pool.append(item)
            else:state.environment=item
            if item.zone=="商店":self.tracker.manual_shop=list(state.shop)
        self.recalculate()

    def remove_item(self,item):
        with self._mutex:
            state=self.tracker.state
            self.tracker.ignored.add((item.kind,item.id,item.zone))
            for pool in (state.roles,state.shop,state.equipment,state.strategies,state.investment_choices):
                found=next((r for r in pool if (r.kind,r.id,r.zone,r.slot,r.box)==(item.kind,item.id,item.zone,item.slot,item.box)),None)
                if found is not None:pool.remove(found)
            if state.environment and (state.environment.kind,state.environment.id)==(item.kind,item.id):state.environment=None
            if item.zone=="商店":self.tracker.manual_shop=list(state.shop)
        self.recalculate()

    def clear_manual_shop(self):
        with self._mutex:
            self.tracker.manual_shop=None
            self.tracker.state.shop=[]
        self.recalculate()

    def _loop(self):
        while not self.closing:
            self._wake.wait(timeout=.2)
            self._wake.clear()
            if not self.running:
                continue
            started=time.monotonic()
            try:
                image,_=self.capture.latest()
                # Animated shop/card transitions cannot become authoritative observations.
                time.sleep(.28)
                second,_=self.capture.latest()
                if image.shape!=second.shape:
                    self.emit("status","窗口尺寸正在变化，等待画面稳定…")
                    time.sleep(.5)
                    continue
                if not frames_stable(image,second):
                    self.emit("status","画面正在切换，暂不更新购买建议…")
                    time.sleep(.5)
                    continue
                if self.recognizer is None:
                    self.recognizer=Recognizer(self.catalog,self.data)
                observed,rows=self.recognizer.analyze(second)
                with self._mutex:
                    self.image=second
                    self.rows=rows
                    self.tracker.merge(observed)
                duration=time.monotonic()-started
                self.times.append(duration)
                self.recalculate()
                self.emit("status",f"观察中 · 本次分析 {duration:.1f}秒 · {observed.scene}")
                self.emit("preview",None)
                signature=tuple(sorted(self.tracker.state.owned_ids()))
                if signature!=self._signature:
                    self._signature=signature
                    # Recalculation handles detail enrichment; observed purchases
                    # must never start a public-list crawl.
                self._wake.wait(timeout=max(.1,2-duration))
            except CaptureUnavailable as error:
                self.emit("status",str(error))
                self._wake.wait(timeout=2)
            except Exception:
                logging.exception("local observation failed")
                self.emit("status","本地识别暂时失败，可继续手动纠正；详细原因已保存到助手日志。")
                self._wake.wait(timeout=3)

    def export_report(self,path):
        with self._mutex:
            if not self.last_result:return False
            serialized=json.dumps(self.last_result,ensure_ascii=False,sort_keys=True)
            previous=getattr(self,"_exported",{})
            key=str(path.resolve())
            if previous.get(key)==serialized:return False
            write_json(path,self.last_result)
            previous[key]=serialized
            self._exported=previous
            return True

    def close(self):
        self.closing=True
        self.running=False
        self._wake.set()
        self.capture.stop()
