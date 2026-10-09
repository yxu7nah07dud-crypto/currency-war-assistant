from __future__ import annotations

import ctypes
import logging
import sys
from pathlib import Path


def main():
    if sys.platform != "win32":
        raise RuntimeError("这个助手需要 Windows 10/11")
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass
    from currency_war_assistant.paths import data_dir
    data=data_dir()
    logging.basicConfig(filename=data / "assistant.log",level=logging.WARNING,encoding="utf8",format="%(asctime)s %(levelname)s %(message)s")
    import tkinter as tk
    from currency_war_assistant.ui import Assistant
    root=tk.Tk()
    def callback_error(kind,value,tb):
        logging.error("window callback failed",exc_info=(kind,value,tb))
    root.report_callback_exception=callback_error
    app=Assistant(root,data)
    if "--diagnostic-autostart" in sys.argv:
        def auto():
            app.refresh_windows()
            app.start()
        root.after(1000,auto)
    def report():
        app.controller.export_report(data / "last_observation.json")
        root.after(5000,report)
    root.after(5000,report)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        from currency_war_assistant.paths import data_dir
        import traceback
        (data_dir() / "startup_error.txt").write_text(traceback.format_exc(),encoding="utf8")
        try:
            ctypes.windll.user32.MessageBoxW(None,"助手启动失败。请查看 CurrencyWarAssistantData/startup_error.txt。","Currency War Assistant",0x10)
        except Exception:
            pass
        raise
