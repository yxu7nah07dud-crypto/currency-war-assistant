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
from .models import Catalog, Seen
from .paths import write_json,read_json
from .localization import translate
from .strategy import Adviser
from .vision import Recognizer, StateTracker
from .share import normalize_share_code, find_guide_by_code
from .selection import InvestmentSelection,game_pointer
from .season import ACTIVE, DIRECTORY, PENDING_RANK, rank_label
from .season_data import DIVISIONS, PARTNERS


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
        self.profile=data / DIRECTORY
        self.client=GuideClient(self.profile / "cache", season=ACTIVE)
        # The public source distribution contains no copied game/wiki database.
        # The catalog is populated from the read-only public endpoint after startup.
        self.catalog=Catalog(self.client.cached_config(), season=ACTIVE)
        self.guides=self.client.cached_guides()
        self.language=read_json(data / "settings.json",{}).get("language","zh")
        self.adviser=Adviser(self.catalog,self.language)
        self.capture=WindowCapture()
        self.tracker=StateTracker(difficulty=PENDING_RANK)
        self.selection=InvestmentSelection()
        saved=read_json(self.profile/'difficulty.json',{}) or {}
        rank, ordinal = saved.get('rank'), saved.get('ordinal')
        if rank in DIVISIONS and (ordinal is None or ordinal in DIVISIONS[rank]):
            self.tracker.state.difficulty=rank_label(rank, ordinal)
            self.tracker.state.manual_fields.add('difficulty')
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
        self._portraits_busy=False
        self._mutex=threading.RLock()
        self.times=deque(maxlen=20)
        self.last_result={}
        threading.Thread(target=self._loop,daemon=True,name="local-observer").start()
        threading.Thread(target=self._selection_loop,daemon=True,name="investment-selection").start()

    def emit(self,kind,value):
        self.events.put((kind,value))

    def initialize(self):
        self.refresh_guides()
        self.refresh_portraits()

    def start(self,window):
        self.running=False
        previous = self.capture.window
        self.capture.start(window)
        if previous and previous.hwnd != window.hwnd:
            self.new_game(keep_rank=True)
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
                catalog=Catalog(config,self.catalog.knowledge, season=ACTIVE)
                self.catalog=catalog
                self.adviser=Adviser(catalog,self.language)
                if self.recognizer:
                    self.recognizer.catalog=catalog
            self.refresh_portraits()

    def refresh_portraits(self):
        from .portraits import sync_portraits,PortraitBank
        with self._mutex:
            if self._portraits_busy or not self.catalog.roles or self.closing:return
            self._portraits_busy=True;catalog=self.catalog
        def worker():
            try:
                count=sync_portraits(self.profile,catalog)
                bank=PortraitBank(self.profile)
                with self._mutex:
                    if self.recognizer:self.recognizer.matcher.set_portraits(bank)
                if not self.closing:
                    self.emit('status',translate(self.language,'portraits_loaded',count=count))
                    self._wake.set()
            except Exception:
                logging.exception('local public portrait cache refresh failed')
            finally:
                with self._mutex:self._portraits_busy=False
        threading.Thread(target=worker,daemon=True,name='public-portrait-cache').start()

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
            self.last_result={"state":state.snapshot(),"matches":[{"id":m.guide["id"],"score":round(m.score,1),"blocked":m.blocked,'provisional':m.provisional,'environment_fit':m.environment_fit} for m in self.matches],"locked_guide":{"id":self.locked,"code":self.locked_code,"title":self.locked_title} if self.locked else None,"processing_seconds":round(self.times[-1],2) if self.times else None,"guide_updated_at":self.client.updated_at}
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

    def save_difficulty(self,value):
        import re
        text=str(value).strip().upper()
        if text.isdecimal():
            text = f'A8·{text}'
        match = re.fullmatch(r'(A[0-8])(?:[.·\s-]+([0-9]{1,2}))?', text)
        if text and not match:
            raise ValueError(translate(self.language,'rank_invalid'))
        rank = match[1] if match else None
        ordinal = int(match[2]) if match and match[2] else None
        if rank and ordinal is not None and ordinal not in DIVISIONS[rank]:
            raise ValueError(translate(self.language,'rank_invalid'))
        with self._mutex:
            write_json(self.profile/'difficulty.json',{'rank':rank, 'ordinal':ordinal})
            state=self.tracker.state
            state.difficulty=rank_label(rank,ordinal) if rank else PENDING_RANK
            if rank is None:state.manual_fields.discard('difficulty')
            else:state.manual_fields.add('difficulty')
        self.recalculate(enrich=False)

    def investment_options(self):
        with self._mutex:
            return deepcopy(self.tracker.state.investment_choices or list(self.selection.choices.values()))

    def new_game(self, keep_rank=False):
        with self._mutex:
            old = self.tracker.state
            self.tracker.reset();self.selection=InvestmentSelection();self._signature=None
            if keep_rank and 'difficulty' in old.manual_fields:
                self.tracker.state.difficulty=old.difficulty
                self.tracker.state.manual_fields.add('difficulty')
            elif not keep_rank:
                write_json(self.profile/'difficulty.json',{'rank':None,'ordinal':None})
        self.clear_guide_lock()

    def save_voyage(self, name, identifier=""):
        with self._mutex:
            if name and (name not in PARTNERS or identifier and
                         identifier not in {str(i) for i in PARTNERS[name]}):
                raise ValueError(translate(self.language, "invalid_name"))
            state = self.tracker.state
            state.voyage = Seen(identifier, name, "奇遇", "已选", confidence=1, source="手动") if name else None
            state.manual_fields.add("voyage")
        self.recalculate(enrich=False)

    def save_spotlight(self, plane, identifier, target):
        with self._mutex:
            effect = self.catalog.spotlights.get(identifier)
            if plane not in (1, 2) or (identifier and (not effect or target not in self.catalog.roles)):
                raise ValueError(translate(self.language, "invalid_name"))
            state = self.tracker.state
            if effect:
                state.spotlights[plane] = Seen(identifier, effect["name"], "主角光环", "已选",
                                               confidence=1, source="手动", equipped_to=target, slot=plane)
            else:
                state.spotlights.pop(plane, None)
            state.manual_fields.add(f"spotlight_{plane}")
        self.recalculate(enrich=False)

    def _selection_loop(self):
        previous=None
        while not self.closing:
            with self._mutex:
                window=self.capture.window
                active=self.running and self.selection.active and window and not self.capture.closed
            if not active:
                previous=None
                time.sleep(.04)
                continue
            try:
                down,point=game_pointer(window.hwnd)
                if down and previous is False:
                    with self._mutex:
                        if self.selection.hwnd==window.hwnd:self.selection.click(point)
                previous=down
            except Exception:
                # Display/manual confirmation remains available when Windows
                # cannot expose a pointer (for example a secure desktop).
                previous=None
            time.sleep(.025)

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

    def save_encounter(self, difficulty, names):
        """Correct recognized conditions atomically; effects stay rule-derived."""
        from .encounter import canonical_debuff
        from .localization import translate
        text = str(difficulty).strip()
        try:
            number = int(text) if text else None
            if number is not None and not 0 <= number <= 300:
                raise ValueError()
        except ValueError:
            raise ValueError(translate(self.language, 'enc_invalid_difficulty')) from None
        raw = [line.strip() for line in str(names).splitlines() if line.strip()]
        if len(raw) > 12 or any(len(name) > 40 for name in raw):
            raise ValueError(translate(self.language, 'enc_invalid_debuffs'))
        debuffs = list(dict.fromkeys(canonical_debuff(name, bool(getattr(getattr(self,'catalog',None),'season',None))) for name in raw))
        with self._mutex:
            self.tracker.state.enemy_difficulty = number
            self.tracker.state.debuffs = debuffs
            self.tracker.state.manual_fields.update(('enemy_difficulty', 'debuffs'))
        self.recalculate(enrich=False)

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
                    self.recognizer=Recognizer(self.catalog,self.profile)
                observed,rows=self.recognizer.analyze(second)
                with self._mutex:
                    previous_state = self.tracker.state
                    if observed.scene=='开局菜单' and previous_state.scene!='开局菜单' and (
                        previous_state.round or previous_state.voyage or previous_state.spotlights
                    ):
                        self.new_game(keep_rank=True)
                    self.image=second
                    self.rows=rows
                    selection=getattr(self,'selection',None)
                    if selection is not None:
                        if observed.scene=='光环选择' and observed.round is None:
                            observed.round=self.tracker.state.round
                        picked=selection.observe(observed,rows,second.shape,self.capture.window.hwnd)
                        if picked:
                            if picked.kind=='环境':observed.environment=picked
                            elif picked.kind=='主角光环' and picked.slot in (1, 2):
                                observed.spotlights.setdefault(picked.slot,picked)
                            elif picked.kind=='策略':observed.strategies.append(picked)
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
