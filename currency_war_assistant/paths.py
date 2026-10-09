from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
ASSETS = ROOT / "assets"
DATA = (Path(sys.executable).parent if getattr(sys, "frozen", False) else ROOT) / "助手数据"


def data_dir() -> Path:
    global DATA
    try:
        DATA.mkdir(parents=True, exist_ok=True)
        probe = DATA / ".write-test"
        probe.write_text("", encoding="utf8")
        probe.unlink()
    except OSError:
        DATA = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "CurrencyWarAssistant"
        DATA.mkdir(parents=True, exist_ok=True)
    return DATA


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf8"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf8")
    tmp.replace(path)
