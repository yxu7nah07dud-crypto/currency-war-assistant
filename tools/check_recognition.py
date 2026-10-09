"""Repeatable local validation on user-provided diagnostic frames; never uploads."""
from pathlib import Path
import json
import sys
import time
import cv2

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from currency_war_assistant.models import Catalog
from currency_war_assistant.paths import read_json
from currency_war_assistant.vision import Recognizer

root=Path(__file__).resolve().parent.parent
cache=root/'CurrencyWarAssistantData'/'cache'
catalog=Catalog(read_json(cache/'config.json',{}),{})
recognizer=Recognizer(catalog,root/'CurrencyWarAssistantData'/'recognition-validation')
image=cv2.imread(str(root/sys.argv[1]))
if image is None:raise ValueError('诊断图片不存在')
if len(sys.argv)>2:
    width=int(sys.argv[2]);image=cv2.resize(image,(width,round(image.shape[0]*width/image.shape[1])))
original=recognizer.read_text
def reduced(image):
    h,w=image.shape[:2]
    if w<=1280:return original(image)
    factor=1280/w
    rows=original(cv2.resize(image,None,fx=factor,fy=factor))
    return [{**row,'box':tuple(round(x/factor) for x in row['box'])} for row in rows]
recognizer.read_text=reduced
times=[]
for _ in range(3):
    started=time.monotonic()
    state,rows=recognizer.analyze(image)
    times.append(round(time.monotonic()-started,3))
report={'times':times,'state':state.snapshot()}
(root/'work/recognition-validation').mkdir(parents=True,exist_ok=True)
(root/f'work/recognition-validation/result-{image.shape[1]}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'width':image.shape[1],'times':times,'round':state.round,'level':state.level,'gold':state.gold,'shop':[r.name for r in state.shop],'inventory':[e.name for e in state.equipment],'owned':[r.name for r in state.roles]},ensure_ascii=False))
