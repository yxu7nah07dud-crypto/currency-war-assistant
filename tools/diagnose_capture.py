from pathlib import Path
import sys
import time
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from currency_war_assistant.capture import find_game_windows, WindowCapture


def main():
    import cv2
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "work/assistant-check")
    out.mkdir(parents=True, exist_ok=True)
    windows = find_game_windows()
    print("游戏窗口", windows)
    if len(windows) != 1:
        raise RuntimeError("需要唯一的游戏窗口")
    capture = WindowCapture()
    try:
        capture.start(windows[0])
        until = time.monotonic() + 15
        while time.monotonic() < until:
            try:
                image, at = capture.latest()
                cv2.imencode(".png", image)[1].tofile(str(out / "game.png"))
                print("画面", image.shape, "对比度", float(image.std()))
                break
            except RuntimeError:
                time.sleep(.25)
        else:
            raise RuntimeError("15秒内未捕获到画面")
    finally:
        capture.stop()
    if "--ocr" in sys.argv:
        from rapidocr import RapidOCR
        ocr = RapidOCR(params={"EngineConfig.onnxruntime.intra_op_num_threads": 2})
        started = time.monotonic()
        result = ocr(image)
        rows = []
        if result.txts is not None:
            rows = [{"text": t, "confidence": float(c), "box": b.tolist()} for b,t,c in zip(result.boxes,result.txts,result.scores)]
        (out / "ocr.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf8")
        print("识别耗时", round(time.monotonic()-started,2), "文本", len(rows))
        print(json.dumps(rows, ensure_ascii=False)[:9000])


if __name__ == "__main__":
    main()
