from __future__ import annotations

import ctypes
import logging
import sys
from pathlib import Path


def validate_cli(arguments):
    usage={"--self-test":(1,"--self-test OUTPUT.json [--check-game]"),
           "--verify-guide":(2,"--verify-guide OUTPUT.json GUIDE_CODE"),
           "--verify-investment":(3,"--verify-investment OUTPUT.json IMAGE CONFIG.json"),
           "--guide-code":(1,"--guide-code GUIDE_CODE")}
    for flag,(count,example) in usage.items():
        if flag not in arguments:continue
        index=arguments.index(flag)
        values=arguments[index+1:index+1+count]
        if len(values)!=count or any(value.startswith('--') for value in values):
            raise ValueError('Usage: CurrencyWarAssistant.exe '+example)


def schedule_reports(root,controller,path):
    def report():
        try:controller.export_report(path)
        except Exception:logging.exception("observation report could not be saved")
        finally:root.after(5000,report)
    root.after(5000,report)
    return report


def main():
    try:validate_cli(sys.argv[1:])
    except ValueError as error:
        if sys.stderr is not None:print(str(error),file=sys.stderr)
        else:ctypes.windll.user32.MessageBoxW(None,str(error),"Currency War Assistant",0x10)
        return 2
    if sys.platform != "win32":
        raise RuntimeError("这个助手需要 Windows 10/11")
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass
    if "--self-test" in sys.argv:
        from currency_war_assistant.diagnostics import run_self_test
        result_path=Path(sys.argv[sys.argv.index("--self-test")+1])
        return run_self_test(result_path, check_game="--check-game" in sys.argv)
    if "--verify-guide" in sys.argv:
        from currency_war_assistant.diagnostics import run_guide_test
        index=sys.argv.index("--verify-guide")
        return run_guide_test(Path(sys.argv[index+1]),sys.argv[index+2])
    if "--verify-investment" in sys.argv:
        from currency_war_assistant.diagnostics import run_investment_test
        index=sys.argv.index("--verify-investment")
        return run_investment_test(Path(sys.argv[index+1]),Path(sys.argv[index+2]),Path(sys.argv[index+3]))
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
    if "--guide-code" in sys.argv:
        code=sys.argv[sys.argv.index("--guide-code")+1]
        def apply_startup_code():
            app.guide_code.set(code)
            app.apply_guide_code()
        root.after(500,apply_startup_code)
    if "--diagnostic-autostart" in sys.argv:
        def auto():
            app.refresh_windows()
            app.start()
        root.after(1000,auto)
    schedule_reports(root,app.controller,data / "last_observation.json")
    root.mainloop()


if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except Exception:
        from currency_war_assistant.paths import data_dir
        import traceback
        (data_dir() / "startup_error.txt").write_text(traceback.format_exc(),encoding="utf8")
        try:
            ctypes.windll.user32.MessageBoxW(None,"助手启动失败。请查看 CurrencyWarAssistantData/startup_error.txt。","Currency War Assistant",0x10)
        except Exception:
            pass
        raise
