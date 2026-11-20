"""Smoke tests that also run inside the frozen release, without game input."""
from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
import time
import traceback

from . import __version__


def run_encounter_test(output: Path, image_path: Path):
    """Replay a supplied encounter image inside either source or frozen build."""
    from .models import Catalog
    from .paths import write_json
    from .vision import Recognizer
    from .strategy import Adviser
    from .encounter import rule_id
    from .season import ACTIVE
    import cv2
    import numpy as np
    report = {'version': __version__, 'frozen': bool(getattr(sys, 'frozen', False)), 'ok': False}
    try:
        image = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError('Screenshot could not be loaded')
        catalog = Catalog({}, season=ACTIVE)
        recognizer = Recognizer(catalog, output.parent / 'encounter-check-data')
        started = time.monotonic()
        state, _ = recognizer.analyze(image)
        report.update(state=state.snapshot(), advice=Adviser(catalog).advice(state, None),
                      rule_ids=[rule_id(name, True) for name in state.debuffs],
                      seconds=round(time.monotonic() - started, 2))
        report['ok'] = (state.scene == '敌人情报' and state.enemy_difficulty is not None
                        and bool(state.debuffs) and all(report['rule_ids']))
    except Exception:
        report['error'] = traceback.format_exc()
    write_json(output, report)
    return 0 if report['ok'] else 1


def run_investment_test(output: Path, image_path: Path, config_path: Path):
    """Opt-in offline OCR replay of a user-supplied investment screenshot."""
    from .models import Catalog
    from .paths import read_json,write_json
    from .vision import Recognizer
    from .strategy import Adviser
    import cv2
    import numpy as np
    report={"version":__version__,"frozen":bool(getattr(sys,"frozen",False)),"ok":False}
    try:
        catalog=Catalog(read_json(config_path,{}))
        if not catalog.environments and not catalog.strategies:
            raise ValueError("Investment config is empty")
        image=cv2.imdecode(np.fromfile(image_path,dtype=np.uint8),cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Screenshot could not be loaded")
        recognizer=Recognizer(catalog,output.parent/'recognition-check-data')
        started=time.monotonic()
        state,rows=recognizer.analyze(image)
        advice=Adviser(catalog).advice(state,None)
        report.update(state=state.snapshot(),advice=advice,seconds=round(time.monotonic()-started,2))
        report['ok']=state.scene=='投资选择' and bool(state.investment_choices) and bool(advice)
    except Exception:
        report['error']=traceback.format_exc()
    write_json(output,report)
    return 0 if report['ok'] else 1


def run_guide_test(output: Path, share_text: str):
    """Opt-in network test of exact-code lookup and the actual lock workflow."""
    from .controller import Controller
    from .share import normalize_share_code
    from .paths import write_json
    controller=Controller(output.parent/'guide-check-data')
    report={"version":__version__,"frozen":bool(getattr(sys,"frozen",False)),"ok":False}
    try:
        controller.apply_guide_code(share_text)
        deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            if controller.lookup.get('state') in ('locked','error','not_found','invalid'):
                break
            time.sleep(.1)
        report.update(lookup=controller.lookup, id=controller.locked,
                      exact_code=controller.locked_code==normalize_share_code(share_text),
                      cache=controller.client.summary())
        report['ok']=bool(controller.locked and report['exact_code'])
    except Exception:
        report['error']=traceback.format_exc()
    finally:
        controller.close()
        write_json(output,report)
    return 0 if report['ok'] else 1


def run_matching_test(output: Path,image_path: Path,data: Path):
    """Offline matching replay; use saved environment, never saved owned roles."""
    from .models import Catalog,Seen
    from .paths import read_json,write_json
    from .vision import Recognizer
    from .strategy import Adviser,role_ids
    import cv2
    import numpy as np
    report={'version':__version__,'frozen':bool(getattr(sys,'frozen',False)),'ok':False,'replays':[]}
    try:
        catalog=Catalog(read_json(data/'cache/config.json',{}))
        guides=read_json(data/'cache/guides.json',{}).get('guides',[])
        saved=read_json(data/'last_observation.json',{}).get('state',{}).get('environment')
        recognizer=Recognizer(catalog,data);adviser=Adviser(catalog)
        image=cv2.imdecode(np.fromfile(image_path,dtype=np.uint8),cv2.IMREAD_COLOR)
        if image is None:raise ValueError('Screenshot could not be loaded')
        for factor in (1,.5):
            frame=cv2.resize(image,None,fx=factor,fy=factor) if factor<1 else image
            started=time.monotonic();state,_=recognizer.analyze(frame)
            if saved:state.environment=Seen(**saved)
            matches=adviser.rank(guides,state)
            report['replays'].append({'factor':factor,'state':state.snapshot(),
                'matches':[{'id':m.guide['id'],'title':m.guide.get('title',''),'score':round(m.score,2),
                            'provisional':m.provisional,'environment_fit':m.environment_fit,'blocked':m.blocked,
                            'reasons':m.reasons,'owned_overlap':sorted(state.owned_ids()&(role_ids(m.guide)|role_ids(m.guide,state.stage())))}
                           for m in matches],
                'seconds':round(time.monotonic()-started,2)})
        report['ok']=all(r['state']['roles'] and r['matches'] and not r['matches'][0]['provisional']
                         and r['matches'][0]['environment_fit']>=2 and r['matches'][0]['owned_overlap'] for r in report['replays'])
    except Exception:
        report['error']=traceback.format_exc()
    write_json(output,report)
    return 0 if report['ok'] else 1


def run_context_test(output: Path,image_path: Path,config_path: Path):
    """Replay a resume image and simulate selection events without sending input."""
    from .models import Catalog,GameState,Seen
    from .paths import read_json,write_json
    from .selection import InvestmentSelection
    from .vision import Recognizer,StateTracker
    from .controller import Controller
    import cv2
    import numpy as np
    report={'version':__version__,'frozen':bool(getattr(sys,'frozen',False)),'ok':False}
    controllers=[]
    try:
        catalog=Catalog(read_json(config_path,{}))
        image=cv2.imdecode(np.fromfile(image_path,dtype=np.uint8),cv2.IMREAD_COLOR)
        if image is None:raise ValueError('Screenshot could not be loaded')
        data=output.parent/'context-check-data'
        started=time.monotonic()
        state,_=Recognizer(catalog,data).analyze(image)
        report['state']=state.snapshot()
        report['seconds']=round(time.monotonic()-started,2)
        from .strategy import Adviser
        report['advice']=Adviser(catalog).advice(state,None)
        reader=InvestmentSelection()
        options=[Seen(str(index),f'Test {index}','环境','待选',slot=index,confidence=1) for index in range(3)]
        page=GameState(scene='投资选择',investment_choices=options)
        rows=[{'text':'确认','box':(950,970,1170,1010),'confidence':1}]
        reader.observe(page,rows,(1080,1920,3),1,now=1)
        reader.click((.5,.5),now=2);reader.click((.55,.916),now=3)
        picked=reader.observe(GameState(scene='准备'),[],(1080,1920,3),1,now=4)
        tracker=StateTracker();tracker.merge(GameState(scene='准备',environment=picked))
        report['simulated_selection']={'id':tracker.state.environment.id,'zone':tracker.state.environment.zone,
                                       'sent_input':False}
        first=Controller(data/'manual');controllers.append(first);first.save_difficulty('A8·12');first.close()
        second=Controller(data/'manual');controllers.append(second)
        report['manual_restart']=second.get_state().difficulty
        from .season import PENDING_RANK
        second.new_game();report['new_game_clears']=second.get_state().difficulty==PENDING_RANK
        image_ok=(state.difficulty=='普通 A8·50' and state.scene=='对局菜单') or (
                    state.scene=='准备' and state.environment and state.environment.zone=='已选')
        report['ok']=bool(image_ok
                      and picked.id=='1' and picked.zone=='已选'
                      and report['manual_restart']=='A8·12' and report['new_game_clears'])
    except Exception:
        report['error']=traceback.format_exc()
    finally:
        for controller in controllers:controller.close()
        write_json(output,report)
    return 0 if report['ok'] else 1


def run_self_test(output: Path, check_game=False):
    result = {"version": __version__, "frozen": bool(getattr(sys,"frozen",False)),
              "executable": sys.executable, "ok": False, "checks": {}}
    root = None
    capture = None
    try:
        from .capture import Window, WindowCapture, load_capture_backend, find_game_windows
        from .window import WindowChrome
        load_capture_backend()
        native = importlib.import_module("windows_capture.windows_capture")
        result["checks"]["capture_import"] = str(native.__file__)
        # Import the app UI too, to catch an incomplete bundle before delivery.
        importlib.import_module("currency_war_assistant.ui")
        import tkinter as tk
        root = tk.Tk()
        root.title(f"CurrencyWarAssistant v{__version__} self-test")
        root.geometry("360x210+80+80")
        canvas = tk.Canvas(root, bg="#17133a", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        canvas.create_rectangle(20, 20, 180, 120, fill="#61e4ff")
        label = canvas.create_text(180, 150, fill="#ffffff", text="Capture test")
        root.update()
        chrome = WindowChrome(root)
        original = chrome.style()
        chrome.set_borderless(True)
        root.update()
        if chrome.style() & chrome.FRAME_BITS:
            raise RuntimeError("Borderless window still has a native frame")
        chrome.set_borderless(False)
        root.update()
        if (chrome.style() & chrome.FRAME_BITS) != (original & chrome.FRAME_BITS):
            raise RuntimeError("Window frame could not be restored")
        result["checks"]["window_mode"] = "borderless and framed passed"
        # Capture only the synthetic window created above. No game screenshots
        # or user information are written by this test.
        capture = WindowCapture()
        capture.start(Window(chrome.hwnd(), root.title(), 360, 210))
        deadline = time.monotonic() + 8
        tick = 0
        while time.monotonic() < deadline:
            tick += 1
            canvas.itemconfigure(label, text=f"Capture test {tick}")
            root.update()
            try:
                image, _ = capture.latest()
                if image.shape[0] < 100 or image.shape[1] < 200:
                    raise RuntimeError("Captured image is unexpectedly small")
                result["checks"]["window_capture"] = {
                    "shape": list(image.shape), "contrast": round(float(image.std()), 2)}
                break
            except RuntimeError:
                time.sleep(.05)
        else:
            raise RuntimeError("No window frame received within 8 seconds")
        if check_game:
            capture.stop()
            root.withdraw()
            root.update()
            windows = find_game_windows()
            if len(windows) != 1:
                raise RuntimeError("Game capture check requires one running game window")
            capture.start(windows[0])
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                root.update()
                try:
                    image, _ = capture.latest()
                    result["checks"]["game_window_capture"] = {
                        "shape": list(image.shape), "contrast": round(float(image.std()), 2)}
                    break
                except RuntimeError:
                    time.sleep(.05)
            else:
                raise RuntimeError("No game frame received within 8 seconds")
        result["ok"] = True
    except Exception:
        result["error"] = traceback.format_exc()
    finally:
        try:
            if capture: capture.stop()
            if root: root.destroy()
        except Exception:
            result["ok"] = False
            result["cleanup_error"] = traceback.format_exc()
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
    return 0 if result["ok"] else 1
