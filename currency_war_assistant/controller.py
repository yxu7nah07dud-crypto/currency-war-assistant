from __future__ import annotations

from collections import deque
import logging
import queue
import threading
import time

import cv2

from .api import GuideClient
from .capture import WindowCapture, CaptureUnavailable
from .models import Catalog
from .paths import write_json
from .strategy import Adviser
from .vision import Recognizer, StateTracker


def normalize_share_code(value):
    """Guide codes are often copied with line breaks or spaces from a browser."""
    text = str(value or "").strip().strip('`\"\'')
    for marker in ("攻略码：", "攻略码:", "分享码：", "分享码:", "Code:", "code:"):
        if marker in text:
            text = text.split(marker, 1)[1]
    return "".join(text.split()).strip('`\"\'')


def find_guide_by_code(guides, code):
    wanted = normalize_share_code(code)
    if not wanted:
        return None
    for guide in guides:
        actual = normalize_share_code(guide.get("tourn_detail", {}).get("share_code", ""))
        if actual and actual == wanted:
            return guide
    return None


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
        self.adviser=Adviser(self.catalog)
        self.capture=WindowCapture()
        self.tracker=StateTracker()
        self.recognizer=None
        self.image=None
        self.rows=[]
        self.matches=[]
        self.locked=""
        self.locked_code=""
        self.locked_title=""
        self.running=False
        self.closing=False
        self._wake=threading.Event()
        self._network_busy=False
        self._network_at=0
        self._signature=None
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
        guide = find_guide_by_code(self.guides, code)
        if guide is None:
            self.emit("status", "缓存中没有找到这条攻略码；请先更新攻略，或确认复制的是完整攻略码。")
            return False
        self.locked = guide["id"]
        self.locked_code = normalize_share_code(code)
        self.locked_title = guide.get("title", "已粘贴攻略")
        self.recalculate()
        self.emit("status", f"已锁定本局攻略：{self.locked_title}")
        return True

    def clear_guide_lock(self):
        self.locked = ""
        self.locked_code = ""
        self.locked_title = ""
        self.recalculate()
        self.emit("status", "已解除本局攻略锁定，恢复自动匹配。")

    def refresh_guides(self,force=False):
        if self._network_busy or (not force and time.monotonic()-self._network_at<300):
            return
        self._network_busy=True
        self._network_at=time.monotonic()
        def worker():
            try:
                config=self.client.config()
                if config:
                    catalog=Catalog(config,self.catalog.knowledge)
                    with self._mutex:
                        self.catalog=catalog
                        self.adviser=Adviser(catalog)
                        if self.recognizer:
                            self.recognizer.catalog=catalog
                ids=sorted(self.tracker.state.owned_ids(),key=lambda r:-self.catalog.cost(r))
                guides=self.client.refresh(ids,pages=3)
                ranked=self.adviser.rank(guides,self.tracker.state)
                guides=self.client.enrich(guides,[m.guide["id"] for m in ranked])
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

    def recalculate(self):
        with self._mutex:
            state=self.tracker.state
            self.matches=self.adviser.rank(self.guides,state,self.locked)
            self.last_result={"state":state.snapshot(),"matches":[{"id":m.guide["id"],"score":round(m.score,1),"blocked":m.blocked} for m in self.matches],"locked_guide":{"id":self.locked,"code":self.locked_code,"title":self.locked_title} if self.locked else None,"processing_seconds":round(self.times[-1],2) if self.times else None,"guide_updated_at":self.client.updated_at}
            advice=self.adviser.advice(state,self.matches[0] if self.matches else None)
            if self.locked and not any(m.guide["id"]==self.locked for m in self.matches):
                advice.insert(0,("锁定失效","原攻略已失效或角色不兼容，当前显示有效备选。请重新锁定。"))
            self.emit("result",{"state":state,"matches":self.matches,"advice":advice})

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
                    self.refresh_guides()
                self._wake.wait(timeout=max(.1,2-duration))
            except CaptureUnavailable as error:
                self.emit("status",str(error))
                self._wake.wait(timeout=2)
            except Exception:
                logging.exception("local observation failed")
                self.emit("status","本地识别暂时失败，可继续手动纠正；详细原因已保存到助手日志。")
                self._wake.wait(timeout=3)

    def export_report(self,path):
        write_json(path,self.last_result)

    def close(self):
        self.closing=True
        self.running=False
        self._wake.set()
        self.capture.stop()
