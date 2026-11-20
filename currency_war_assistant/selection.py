"""Observe investment card clicks in the selected game window; never send input.

An offered/highlighted card is not an owned investment. A card click, the game's
Confirm button, and a subsequent page exit are required to record selection.
Only the active game's investment-page mouse position/button is inspected.
"""
from __future__ import annotations

from copy import deepcopy
import ctypes
from ctypes import wintypes
import time

from .models import normalize


def game_pointer(hwnd):
    """Return primary-button state and a point relative to the captured window.

    No keyboard keys are queried. Points over the assistant or other windows
    are excluded, including when a topmost overlay covers a game card.
    """
    user=ctypes.WinDLL('user32',use_last_error=True)
    user.GetAsyncKeyState.argtypes=[ctypes.c_int];user.GetAsyncKeyState.restype=ctypes.c_short
    user.GetForegroundWindow.restype=wintypes.HWND
    user.WindowFromPoint.argtypes=[wintypes.POINT];user.WindowFromPoint.restype=wintypes.HWND
    user.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT];user.GetAncestor.restype=wintypes.HWND
    user.GetCursorPos.argtypes=[ctypes.POINTER(wintypes.POINT)]
    user.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
    button=2 if user.GetSystemMetrics(23) else 1
    down=bool(user.GetAsyncKeyState(button)&0x8000)
    if user.GetForegroundWindow()!=hwnd:return down,None
    point=wintypes.POINT()
    if not user.GetCursorPos(ctypes.byref(point)):return down,None
    under=user.WindowFromPoint(point)
    if not under or user.GetAncestor(under,2)!=hwnd:return down,None
    rect=wintypes.RECT()
    dwm=ctypes.WinDLL('dwmapi',use_last_error=True)
    dwm.DwmGetWindowAttribute.argtypes=[wintypes.HWND,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD]
    if dwm.DwmGetWindowAttribute(hwnd,9,ctypes.byref(rect),ctypes.sizeof(rect))!=0:
        if not user.GetWindowRect(hwnd,ctypes.byref(rect)):return down,None
    width,height=rect.right-rect.left,rect.bottom-rect.top
    if width<=0 or height<=0:return down,None
    x,y=(point.x-rect.left)/width,(point.y-rect.top)/height
    return down,(x,y) if 0<=x<=1 and 0<=y<=1 else None


class InvestmentSelection:
    def __init__(self):
        self.active=False
        self.choices={}
        self.centers={}
        self.confirm_box=None
        self.candidate=None
        self.confirmed_at=None
        self.last_page_at=0
        self.hwnd=None
        self.page=""
        self.plane=None

    def observe(self,state,rows,shape,hwnd=None,now=None):
        now=time.monotonic() if now is None else now
        if self.hwnd is not None and hwnd!=self.hwnd:
            self.__init__()
        self.hwnd=hwnd
        if state.scene not in ('投资选择','光环选择') or self.page and state.scene!=self.page:
            picked=deepcopy(self.candidate) if (self.active and self.confirmed_at is not None
                        and now-self.confirmed_at<=15) else None
            if picked and picked.kind=='主角光环':
                if self.plane not in (1,2) or not picked.equipped_to or state.scene not in ('准备','战斗','光环详情'):
                    picked=None
                else:
                    picked.slot=self.plane
            self.active=False;self.candidate=None;self.confirmed_at=None
            self.page=""
            if picked:
                picked.zone='已选';picked.confidence=1;picked.source='选择记录';picked.at=time.time()
            return picked
        self.page=state.scene
        if state.scene=='光环选择' and state.round:
            self.plane=int(state.round.split('-')[0])
        h,w=shape[:2]
        choices=state.investment_choices if state.scene=='投资选择' else state.spotlight_choices
        observed={(item.kind,item.slot):item for item in choices
                  if item.slot>=0 and item.confidence>=.8
                  and (state.scene=='光环选择' or item.slot<3)}
        # A refresh invalidates the previous click, while partial OCR may keep
        # the same still-visible candidates. A new page always starts clean.
        if not self.active or (observed and {k[0] for k in observed}!={k[0] for k in self.choices}) or any(key in self.choices and self.choices[key].id!=item.id
                                  or key in self.choices and self.choices[key].equipped_to!=item.equipped_to
                                  for key,item in observed.items()):
            self.choices={};self.centers={};self.candidate=None;self.confirmed_at=None
        self.choices.update({key:deepcopy(item) for key,item in observed.items()})
        self.centers={}
        for key,item in observed.items():
            self.centers[key]=(item.box[0]+item.box[2])/2/w if item.box else .23+item.slot*.27
        self.confirm_box=None
        for row in rows:
            x1,y1,x2,y2=row['box']
            if normalize(row['text'])=='确认' and row['confidence']>=.8 and y1/h>.82 and .35<(x1+x2)/2/w<.7:
                self.confirm_box=(max(.35,x1/w-.08),max(.82,y1/h-.025),
                                  min(.7,x2/w+.08),min(.98,y2/h+.025))
        self.active=bool(observed)
        if not self.active:self.candidate=None;self.confirmed_at=None
        self.last_page_at=now
        return None

    def click(self,point,now=None):
        now=time.monotonic() if now is None else now
        if not self.active or point is None or now-self.last_page_at>8:return
        x,y=point
        if self.confirm_box:
            a,b,c,d=self.confirm_box
            if a<=x<=c and b<=y<=d:
                if self.candidate:self.confirmed_at=now
                return
        if .18<=y<=.80:
            matches=[(abs(x-center),key) for key,center in self.centers.items() if abs(x-center)<=.125]
            if matches:
                self.candidate=deepcopy(self.choices[min(matches)[1]])
                self.confirmed_at=None
                return
        # Refresh, Back and unrelated clicks cancel a pending choice.
        self.candidate=None;self.confirmed_at=None
