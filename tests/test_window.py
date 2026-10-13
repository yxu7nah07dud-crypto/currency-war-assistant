"""Windows integration checks for saved borderless mode and window controls."""
import json
import queue
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from currency_war_assistant.capture import (
    CaptureDependencyUnavailable, Window, WindowCapture, load_capture_backend)


class CaptureFailureTests(unittest.TestCase):
    def test_missing_native_backend_reports_component_problem(self):
        with patch('currency_war_assistant.capture.importlib.import_module',
                   side_effect=ModuleNotFoundError("windows_capture.windows_capture")):
            with self.assertRaises(CaptureDependencyUnavailable):
                load_capture_backend()

    def test_failure_to_start_does_not_leave_capture_active(self):
        capture=WindowCapture()
        backend=MagicMock()
        backend.return_value.start_free_threaded.side_effect=RuntimeError('cannot start')
        with patch('currency_war_assistant.capture.load_capture_backend',return_value=backend):
            with self.assertRaises(RuntimeError):
                capture.start(Window(1,'synthetic window',360,200))
        self.assertTrue(capture.closed)
        self.assertIsNone(capture._control)
        self.assertIsNone(capture._capture)


@unittest.skipUnless(sys.platform=='win32','Requires Windows window styles')
class WindowTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from currency_war_assistant.ui import Assistant
        self.root=tk.Tk()
        self.controller_patch=patch('currency_war_assistant.ui.Controller')
        controller=self.controller_patch.start().return_value
        controller.client.updated_at=0
        controller.client.online=False
        controller.client.summary.return_value={"count":0,"codes":0,"coverage":{"state":"partial","orders":{}}}
        controller.lookup={"state":"idle"}
        controller.guides=[]
        controller.catalog.version='fixture'
        controller.events=queue.Queue()
        self.directory=Path(__file__).parent/'_cache'/'window-test'
        self.directory.mkdir(parents=True,exist_ok=True)
        self.settings=self.directory/'settings.json'
        if self.settings.exists():self.settings.unlink()
        self.app=Assistant(self.root,self.directory)
        self.root.update()

    def tearDown(self):
        for task in self.root.tk.call('after','info'):
            self.root.after_cancel(task)
        self.root.destroy()
        self.controller_patch.stop()

    def test_window_keeps_borderless_after_minimize_restore_and_rebuild(self):
        original=self.app.chrome.style()
        self.app.borderless.set(True)
        self.app.set_borderless()
        self.root.update()
        self.assertEqual(0,self.app.chrome.style() & self.app.chrome.FRAME_BITS)
        # Taskbar/system-menu and minimize permissions are retained.
        self.assertEqual(original & 0x000A0000,self.app.chrome.style() & 0x000A0000)
        self.root.iconify();self.root.update()
        self.root.deiconify();self.root.update()
        self.assertEqual(0,self.app.chrome.style() & self.app.chrome.FRAME_BITS)
        for language in ('en','ja','zh'):
            self.app.language=language
            self.app._rebuild_ui();self.root.update()
            self.assertEqual(0,self.app.chrome.style() & self.app.chrome.FRAME_BITS)
            self.app.open_settings();self.root.update()
            self.assertTrue(self.app.footer.winfo_ismapped())
            self.assertLessEqual(self.app.footer.winfo_rooty()+self.app.footer.winfo_height(),
                                 self.root.winfo_rooty()+self.root.winfo_height())
            self.app.open_settings()
        self.app.restore_frame();self.root.update()
        self.assertEqual(original & self.app.chrome.FRAME_BITS,
                         self.app.chrome.style() & self.app.chrome.FRAME_BITS)
        self.assertFalse(self.app.chrome.borderless)

    def test_investment_choices_are_visible_and_editable_in_recognized_tree(self):
        from currency_war_assistant.models import GameState,Seen
        state=GameState(scene='投资选择',investment_choices=[
            Seen(str(i),f'测试候选{i}','环境','待选',slot=i,confidence=1) for i in range(3)])
        self.app.controller.locked_title=''
        self.app.controller.locked=''
        self.app.render({'state':state,'matches':[],'advice':[('投资环境','测试选择建议')]})
        self.root.update()
        names=[self.app.tree.item(i,'text') for i in self.app.tree.get_children()]
        self.assertEqual(['测试候选0','测试候选1','测试候选2'],names)
        self.assertIn('测试选择建议',self.app.advice_text.get('1.0','end'))
        self.assertTrue(all(item.zone=='待选' for item in self.app.entries))

    def test_recognition_selection_survives_unchanged_frame_and_reorder(self):
        from currency_war_assistant.models import GameState,Seen
        a=Seen('a','A','角色','备战');b=Seen('b','B','角色','后台')
        self.app._render_entries(GameState(roles=[a,b]))
        self.app.tree.selection_set('1');self.root.update()
        with patch.object(self.app.tree,'delete',wraps=self.app.tree.delete) as delete:
            self.app._render_entries(GameState(roles=[a,b]))
            delete.assert_not_called()
        self.app._render_entries(GameState(roles=[b,a]))
        self.assertEqual(('0',),self.app.tree.selection())
        self.assertEqual(('角色','b','后台'),self.app._selected_key)

    def test_enum_selector_displays_translations_but_keeps_internal_values(self):
        import tkinter as tk
        from currency_war_assistant.models import GameState,Seen
        self.app.language='en';self.app._rebuild_ui()
        variable=tk.StringVar(value='备战')
        box=self.app.enum_box(self.root,variable,['备战','前台'],state='readonly')
        self.assertEqual('Bench',box.get())
        box.current(1);box.event_generate('<<ComboboxSelected>>')
        self.assertEqual('前台',variable.get())
        self.app._render_entries(GameState(roles=[Seen('r','ROLE','角色','备战',star=2,source='手动')]))
        self.assertEqual(('Bench','2 stars','Manual'),self.app.tree.item('0','values'))
        box.destroy()

    def test_correction_controls_stay_visible_at_default_height_with_wrapped_guide(self):
        for language in ('zh','en','ja'):
            with self.subTest(language=language):
                self.app.language=language
                self.app._rebuild_ui()
                self.root.geometry('980x650')
                self.app.lookup_summary.set('A long locked guide title / 锁定的攻略标题很长，需要两行显示\n作者版本 4.4 / 当前 4.6')
                self.app.metric_vars['locked'].set('【5欢愉4量子同频】星核猎手加阿哈无限动的超绝时停')
                self.app.notebook.select(self.app.state_tab)
                self.root.update()
                for widget in (self.app.correction_button,self.app.state_correct_button,self.app.state_preview_button):
                    self.assertTrue(widget.winfo_ismapped())
                    self.assertGreater(widget.winfo_height(),15)
                    self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),self.root.winfo_rooty()+self.root.winfo_height())
                self.assertLessEqual(self.app.state_preview_button.winfo_rootx()+self.app.state_preview_button.winfo_width(),self.root.winfo_rootx()+self.root.winfo_width())
                self.assertGreater(self.app.tree.winfo_height(),20)
                # It must be reachable directly even while the advice tab is open.
                self.app.notebook.select(self.app.advice_tab)
                self.root.update()
                self.assertTrue(self.app.correction_button.winfo_ismapped())

    def test_borderless_setting_restores_on_next_launch(self):
        self.app.borderless.set(True);self.app.set_borderless()
        self.app.opacity.set(.84);self.app.topmost.set(False)
        self.app.save_settings()
        saved=json.loads(self.settings.read_text(encoding='utf8'))
        self.assertTrue(saved['borderless'])
        self.assertEqual(.84,saved['opacity'])
        self.assertFalse(saved['topmost'])
        from currency_war_assistant.ui import Assistant
        other=self.root.__class__()
        try:
            restored=Assistant(other,self.directory)
            other.update()
            self.assertTrue(restored.borderless.get())
            self.assertEqual(0,restored.chrome.style() & restored.chrome.FRAME_BITS)
        finally:
            for task in other.tk.call('after','info'):other.after_cancel(task)
            other.destroy()

    def test_header_drag_and_corner_resize_are_usable_without_native_frame(self):
        self.app.borderless.set(True);self.app.set_borderless();self.root.update()
        chrome=self.app.chrome
        x,y=self.root.winfo_x(),self.root.winfo_y()
        chrome.begin_drag(SimpleNamespace(x_root=100,y_root=100))
        chrome.drag(SimpleNamespace(x_root=125,y_root=140));chrome.end_drag()
        self.root.update()
        self.assertEqual((x+25,y+40),(self.root.winfo_x(),self.root.winfo_y()))
        w,h=self.root.winfo_width(),self.root.winfo_height()
        chrome.begin_resize(SimpleNamespace(x_root=100,y_root=100))
        chrome.resize(SimpleNamespace(x_root=145,y_root=135));chrome.end_resize()
        self.root.update()
        self.assertEqual((w+45,h+35),(self.root.winfo_width(),self.root.winfo_height()))
        size=(self.root.winfo_width(),self.root.winfo_height())
        self.app.toggle();self.root.update()
        self.app._rebuild_ui();self.root.update()
        self.assertFalse(self.app.body.winfo_ismapped())
        self.assertEqual(0,self.app.chrome.style() & self.app.chrome.FRAME_BITS)
        self.app.toggle();self.root.update()
        self.assertEqual(size,(self.root.winfo_width(),self.root.winfo_height()))


if __name__=='__main__':unittest.main()
