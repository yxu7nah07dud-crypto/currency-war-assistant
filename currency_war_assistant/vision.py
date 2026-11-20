from __future__ import annotations

from difflib import SequenceMatcher
import threading
import time
import re

import cv2
import numpy as np

from .models import Seen, Catalog, GameState, normalize
from .paths import read_json, write_json
from .encounter import canonical_debuff, rule_id
from .portraits import PortraitBank
from .season import PENDING_RANK
from .season_play import observe_rank, observe_voyage, spotlight_items


DEFAULT_REGIONS = {
    "商店": [.19, .045, .88, .31],
    "备战": [.195, .78, .79, .91],
    "前台": [.26, .39, .72, .54],
    "后台": [.26, .59, .73, .72],
    "库存": [.93, .21, .985, .60],
}


def detect_a8_difficulty(rows, shape):
    """Read the number shown under the game's A8 difficulty banner.

    The banner is on the game canvas (upper-left), while the assistant's own
    status line may also contain an A8 number. Restrict candidates to the
    upper-left game area and choose the nearest numeric row below the A8
    heading so the overlay's default value cannot be mistaken for the game
    value.
    """
    h, w = shape[:2]
    banners = []
    # Do not use a trailing ``\b``: OCR often returns ``A8财富造物主``
    # without a space, and both the digit and the following Han characters
    # are word characters to Python's Unicode regular-expression engine.
    inline = re.compile(r"(?i)A\s*8\s*[·•.\-:：]?\s*(\d{2})(?!\d)")
    a8 = re.compile(r"(?i)A\s*8(?!\d)")
    wealth=[]
    for row in rows:
        if row.get("confidence", 0) < .70:
            continue
        box = row["box"]
        cx = (box[0] + box[2]) / 2 / w
        cy = (box[1] + box[3]) / 2 / h
        if not .02 <= cx <= .45 or cy > .65:
            continue
        text = row["text"].replace("O", "0")
        if text.startswith(('普通','Normal','通常')) or '待确认' in text:
            continue
        match=re.search(r'财富造物主\s*([0-9]{1,2})(?![0-9])',text)
        if match and 1<=int(match[1])<=99:
            wealth.append((cx,cy,int(match[1])))
        match = inline.search(text)
        if match:
            return int(match.group(1))
        if a8.search(text):
            banners.append((cx, cy))
    if not banners:
        return None

    # The resume screen places “财富造物主50” beside or below an A8 label.
    # Require the game label nearby, so guide text cannot set the difficulty.
    paired=[(abs(cx-bx)+abs(cy-by),value) for cx,cy,value in wealth
            for bx,by in banners if abs(cx-bx)<=.22 and abs(cy-by)<=.12]
    if paired:
        return min(paired)[1]

    candidates = []
    for row in rows:
        if row.get("confidence", 0) < .70 or not row["text"].strip().isdigit():
            continue
        value = int(row["text"].strip())
        if not 10 <= value <= 99:
            continue
        box = row["box"]
        cx = (box[0] + box[2]) / 2 / w
        cy = (box[1] + box[3]) / 2 / h
        if not .02 <= cx <= .45 or cy > .72:
            continue
        for bx, by in banners:
            dy = cy - by
            if 0.02 <= dy <= .20 and abs(cx - bx) <= .16:
                candidates.append((dy + abs(cx - bx) * .1, value))
    return min(candidates)[1] if candidates else None


def detect_enemy_modifiers(rows, shape, seasonal=False):
    """Read the bottom game strip anchored to its enemy-difficulty label.

    Unanchored text (shop names, UID, and the assistant's own summary) is never
    treated as a modifier. Coordinates are relative to the game capture.
    """
    h, w = shape[:2]
    panel = [r for r in rows if r.get('confidence', 0) >= .80
             and .76 <= (r['box'][1] + r['box'][3]) / 2 / h <= .96]
    anchors = [r for r in panel if '敌人难度' in normalize(r['text'])
               and r['box'][0] / w < .23]
    if not anchors:
        return None, []
    anchor = min(anchors, key=lambda r: r['box'][0])
    ay = (anchor['box'][1] + anchor['box'][3]) / 2
    inline = re.search(r'敌\s*人\s*难\s*度\s*[:：]?\s*([0-9]{1,3})(?![0-9])', anchor['text'])
    difficulty = int(inline[1]) if inline else None
    # A value split into its own OCR box must sit immediately to the right of
    # the label, on the same baseline. Unrelated values below are excluded.
    if difficulty is None:
        candidates = [r for r in panel if r['text'].strip().isdigit()
                      and 0 <= r['box'][0] - anchor['box'][2] <= .045 * w
                      and abs((r['box'][1] + r['box'][3]) / 2 - ay) <= .02 * h]
        if candidates:
            difficulty = int(min(candidates, key=lambda r: r['box'][0])['text'])
    if difficulty is not None and not 0 <= difficulty <= 999:
        difficulty = None
    labels = []
    for row in sorted(panel, key=lambda r: r['box'][0]):
        if abs((row['box'][1] + row['box'][3]) / 2 - ay) > .022 * h:
            continue
        if row['box'][0] < anchor['box'][0]:
            continue
        if seasonal and row['box'][0] / w >= .73:
            continue
        text = row['text'].strip()
        if row is anchor:
            text = text[inline.end():] if inline else ''
        parts = [text] if rule_id(text, seasonal) is not None else re.split(r'[\s、;；|]+', text)
        for part in parts:
            name = canonical_debuff(part, seasonal)
            if not name or not 2 <= len(name) <= 40:
                continue
            if rule_id(name, seasonal) is None and (not re.fullmatch(r'[\u4e00-\u9fff·]+', name)
                                         or any(v in name for v in ('下一步', '开始对局', '难度', '标准博弈', '晋升点'))):
                continue
            if name not in labels:
                labels.append(name)
    return difficulty, labels


def region_contains(box, rect, shape):
    h,w = shape[:2]
    x,y = (box[0]+box[2])/2/w, (box[1]+box[3])/2/h
    a,b,c,d = rect
    return a <=x<=c and b<=y<=d


def investment_detail_headers(rows,shape):
    """Owned-investment tooltip on the preparation HUD, not the choice page."""
    h,w=shape[:2]
    hud=any('购买经验' in r['text'] and r['box'][1]/h>.70 and r['box'][0]/w<.32
            and r['confidence']>=.8 for r in rows)
    if not hud:return []
    return [r for r in rows if normalize(r['text']) in ('投资环境','投资策略')
            and r['confidence']>=.85 and .13<(r['box'][1]+r['box'][3])/2/h<.50]


def selected_investments(rows,catalog,scene,shape):
    """Accept explicit owned-investment labels, never unconfirmed card titles."""
    if scene=='投资选择':return []
    result=[]
    h,w=shape[:2]
    for header in investment_detail_headers(rows,shape):
        kind='环境' if normalize(header['text'])=='投资环境' else '策略'
        hx=(header['box'][0]+header['box'][2])/2
        hy=header['box'][3]
        titles=[r for r in rows if r['confidence']>=.85 and .005*h<r['box'][1]-hy<.09*h
                and abs((r['box'][0]+r['box'][2])/2-hx)<.20*w]
        matches=[(identifier,r) for r in titles for identifier,item in catalog.pool(kind).items()
                 if normalize(item.get('name',''))==normalize(r['text'])]
        if len(matches)==1:
            identifier,r=matches[0]
            result.append(Seen(identifier,catalog.name(identifier,kind),kind,'已选',
                               confidence=r['confidence'],source='文字',box=r['box']))
    for kind,prefixes in (('环境',('已选投资环境','当前投资环境','已选环境')),
                          ('策略',('已选投资策略','已选策略'))):
        for row in rows:
            if row['confidence']<.85:continue
            token=normalize(row['text'])
            prefix=next((p for p in prefixes if token.startswith(p)),None)
            if not prefix:continue
            remainder=token[len(prefix):]
            candidates=[row] if remainder else [r for r in rows if r['confidence']>=.85
                        and abs((r['box'][1]+r['box'][3]-row['box'][1]-row['box'][3])/2)<=45
                        and 0<=r['box'][0]-row['box'][2]<=100]
            for candidate in candidates:
                name=remainder if remainder else normalize(candidate['text'])
                matches=[i for i,item in catalog.pool(kind).items() if normalize(item.get('name',''))==name]
                if len(matches)==1:
                    identifier=matches[0]
                    result.append(Seen(identifier,catalog.name(identifier,kind),kind,'已选',
                                       confidence=candidate['confidence'],source='文字',box=candidate['box']))
    return result


class IconMatcher:
    def __init__(self, data):
        self.portraits=PortraitBank(data)
        self.templates = []
        self.equipment_templates=[]
        # Official role/equipment art is deliberately not bundled in the public
        # repository. Recognition uses OCR and user-confirmed crops by default.
        # Users who have the right to use local templates can place them in their
        # private data directory; these are never part of the source release.
        self.custom = []
        for entry in read_json(data / "custom_icons.json", []):
            target = data / entry["path"]
            if target.exists():
                image = cv2.imdecode(np.fromfile(target,dtype=np.uint8),cv2.IMREAD_COLOR)
                if image is not None:
                    self.custom.append((entry,image))
        self.bf = cv2.BFMatcher(cv2.NORM_L2)
        self.set_portraits(self.portraits)

    def set_portraits(self,bank):
        self.portraits=bank
        self.templates=[([{'id':i,'kind':'角色'} for i in reference['ids']],reference['shape'],
                         reference['points'],reference['desc']) for reference in bank.references]

    def find(self, image, kinds=None):
        height,width=image.shape[:2]
        scale=min(1,1280/width)
        small=cv2.resize(image,None,fx=scale,fy=scale) if scale<1 else image
        gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
        found=[]
        applicable=[t for t in self.templates if not kinds or t[0][0]["kind"] in kinds]
        if applicable:
            kp,desc=cv2.SIFT_create(nfeatures=2400).detectAndCompute(gray,None)
            for items,(th,tw),tpoints,tdesc in (applicable if desc is not None else []):
                if kinds and items[0]["kind"] not in kinds:
                    continue
                pairs=self.bf.knnMatch(tdesc,desc,k=2)
                good=[a for a,b in pairs if a.distance<.70*b.distance and a.distance<250]
                if len(good)<8:
                    continue
                src=np.float32([tpoints[m.queryIdx].pt for m in good])
                dst=np.float32([kp[m.trainIdx].pt for m in good])
                matrix,mask=cv2.findHomography(src,dst,cv2.RANSAC,3)
                if matrix is None or mask is None or mask.sum()<8 or mask.sum()/len(good)<.55:
                    continue
                corners=np.float32([[0,0],[tw,0],[tw,th],[0,th]]).reshape(-1,1,2)
                pts=cv2.perspectiveTransform(corners,matrix).reshape(-1,2)/scale
                left,top=pts.min(axis=0); right,bottom=pts.max(axis=0)
                bw,bh=right-left,bottom-top
                polygon_area=abs(cv2.contourArea(pts))
                if min(bw,bh)<18 or max(bw,bh)>max(180,width*.16) or min(bw,bh)/max(bw,bh)<.45 or polygon_area < bw*bh*.55:
                    continue
                if left < -8 or top < -8 or right>width+8 or bottom>height+8:
                    continue
                confidence=min(.98,.72+.025*int(mask.sum()))
                found.append({"kind":items[0]["kind"],"ids":[v["id"] for v in items],"box":(int(left),int(top),int(right),int(bottom)),"confidence":confidence,"source":"官方图标"})
        # User-confirmed crops cover skins and tiny HUD icons that differ from official art.
        for entry,reference in self.custom:
            if kinds and entry["kind"] not in kinds:continue
            rh,rw=reference.shape[:2]
            for factor in (.75,1,1.25):
                template=cv2.resize(reference,(max(8,int(rw*factor*scale)),max(8,int(rh*factor*scale))))
                if template.shape[0]>small.shape[0] or template.shape[1]>small.shape[1]:
                    continue
                scores=cv2.matchTemplate(small,template,cv2.TM_CCOEFF_NORMED)
                _,maximum,_,point=cv2.minMaxLoc(scores)
                if maximum>=.92:
                    x,y=point
                    found.append({"kind":entry["kind"],"ids":[entry["id"]],"box":(int(x/scale),int(y/scale),int((x+template.shape[1])/scale),int((y+template.shape[0])/scale)),"confidence":float(maximum),"source":"已确认图标"})
                    break
        return found

    def has_templates(self,kinds=None):
        return any(not kinds or t[0][0]['kind'] in kinds for t in self.templates) or any(
            not kinds or e['kind'] in kinds for e,_ in self.custom)

    def inventory(self,image):
        """Match each separate inventory cell, retaining duplicate material copies."""
        if not self.equipment_templates:return []
        h,w=image.shape[:2]
        factor=w/1920
        result=[]
        for slot in range(6):
            top=int((237+76*slot)*h/1080)
            bottom=min(h,top+int(79*h/1080))
            left,right=int(.941*w),int(.981*w)
            roi=image[top:bottom,left:right]
            if roi.size==0:continue
            candidates=[]
            for identifier,reference in self.equipment_templates:
                best=0.0
                for size in (48,56,64,70):
                    edge=max(8,int(size*factor))
                    if edge>=min(roi.shape[:2]):continue
                    small=cv2.resize(reference,(edge,edge))
                    mask=(small[:,:,3]>96).astype(np.uint8)*255
                    scores=cv2.matchTemplate(roi,small[:,:,:3],cv2.TM_CCORR_NORMED,mask=mask)
                    scores[~np.isfinite(scores)]=0
                    best=max(best,float(scores.max()))
                candidates.append((best,identifier))
            candidates.sort(reverse=True)
            if len(candidates)>1 and candidates[0][0]>.94 and candidates[0][0]-candidates[1][0]>.04:
                score,identifier=candidates[0]
                result.append({"kind":"装备","ids":[identifier],"box":(left,top,right,bottom),"confidence":score,"source":"库存图标","zone_hint":"库存","slot":slot})
        return result


def visible_stars(image,box):
    left,top,right,bottom=box
    bh,bw=bottom-top,right-left
    x1=max(0,int(left+.18*bw));x2=min(image.shape[1],int(right-.18*bw))
    y1=max(0,int(top+.74*bh));y2=min(image.shape[0],bottom+4)
    crop=image[y1:y2,x1:x2]
    if not crop.size:return None
    mask=cv2.inRange(cv2.cvtColor(crop,cv2.COLOR_BGR2HSV),(5,70,210),(40,255,255))
    _,_,stats,centers=cv2.connectedComponentsWithStats(mask)
    scale=image.shape[1]/1920
    valid=[]
    for s,c in zip(stats[1:],centers[1:]):
        x,y,w,h,area=s
        if 5*scale<=w<=18*scale and 5*scale<=h<=19*scale and 15*scale*scale<=area<=100*scale*scale and .12<area/max(1,w*h)<.55:
            if y<=0 or y+h>=mask.shape[0]:return None
            valid.append(c)
    if not 1<=len(valid)<=4:return None
    if max(c[1] for c in valid)-min(c[1] for c in valid)>4*scale:return None
    if abs(sum(c[0] for c in valid)/len(valid)-crop.shape[1]/2)>max(12*scale,bw*.12):return None
    return len(valid)


class Recognizer:
    def __init__(self,catalog:Catalog,data):
        self.catalog=catalog
        self.data=data
        saved=read_json(data / "regions.json",{})
        self.regions={**DEFAULT_REGIONS,**saved.get("regions",{})}
        self.calibrated=set(saved.get("calibrated",[]))
        self.regions_calibrated=bool(self.calibrated)
        self.matcher=IconMatcher(data)
        self.ocr=None
        self._ocr_lock=threading.Lock()

    def read_text(self,image):
        scale=min(1,1280/image.shape[1])
        if scale<1:image=cv2.resize(image,None,fx=scale,fy=scale)
        with self._ocr_lock:
            if self.ocr is None:
                from rapidocr import RapidOCR
                self.ocr=RapidOCR(params={"Global.log_level":"warning","EngineConfig.onnxruntime.intra_op_num_threads":2,"EngineConfig.onnxruntime.inter_op_num_threads":1,"Global.use_cls":False})
            result=self.ocr(image)
        if result.txts is None:
            return []
        return [{"text":t,"confidence":float(c),"box":(round(b[:,0].min()/scale),round(b[:,1].min()/scale),round(b[:,0].max()/scale),round(b[:,1].max()/scale))} for b,t,c in zip(result.boxes,result.txts,result.scores)]

    def zone(self,kind,box,shape,scene,rows):
        h,w=shape[:2]
        x,y=(box[0]+box[2])/2/w,(box[1]+box[3])/2/h
        if scene=="战斗":
            if kind=="角色" and .04<x<.58 and .71<y<.84:
                return "前台"
            if kind=="角色" and x<.20 and y>.90:
                return "后台"
            if kind=="装备" and ((.07<x<.56 and .83<y<.89) or (x<.2 and .92<y<.97)):
                return "已装备"
            return "待确认"
        if kind=="角色" and scene=="准备":
            if self.regions_calibrated:
                for zone in ("商店","备战","后台","前台"):
                    if zone in self.calibrated and region_contains(box,self.regions[zone],shape):
                        return zone
            # Current PC card layout was calibrated against actual 1920x1080 game capture.
            standard=any("购买经验" in r["text"] for r in rows) and any("后台区域" in r["text"] for r in rows)
            if standard:
                for zone in ("商店","备战","后台","前台"):
                    if zone not in self.calibrated and region_contains(box,DEFAULT_REGIONS[zone],shape):
                        return zone
        if kind=="装备" and "库存" in self.calibrated and region_contains(box,self.regions["库存"],shape) and scene=="准备":
            return "库存"
        if kind=="装备" and scene=="准备" and any("后台区域" in r["text"] for r in rows):
            if region_contains(box,DEFAULT_REGIONS["库存"],shape):return "库存"
            if .30<x<.65 and (.485<y<.535 or .675<y<.735):return "已装备"
        if kind in ("策略","环境"):
            return "待选" if scene=="投资选择" else "待确认"
        return "待确认"

    def parse_rows(self,rows,shape):
        joined=" ".join(r["text"] for r in rows)
        catalog = getattr(self,"catalog",None)
        seasonal = bool(catalog and catalog.season)
        enemy_difficulty, debuffs = detect_enemy_modifiers(rows, shape, seasonal)
        confident = [r for r in rows if r["confidence"]>=.8]
        headings = {normalize(r["text"]) for r in confident if r["box"][1] < .28*shape[0]}
        voyage_heading = seasonal and bool(headings & {"奇遇","奇遇伙伴","奇遇效果","本局奇遇"})
        spotlight_heading = seasonal and bool(headings & {"主角光环","选择主角","选择主角光环","选择一名员工成为主角"})
        spotlight_confirmed = seasonal and bool(headings & {"已获得主角光环","已选主角光环","当前主角光环"})
        enemy_page = (enemy_difficulty is not None or debuffs) and any(
            normalize(r['text']) in (('下一步','下一') if seasonal else ('下一步',))
            and r['confidence'] >= .8
            and r['box'][0] / shape[1] > .65 and r['box'][1] / shape[0] > .80 for r in rows)
        if seasonal and enemy_difficulty is not None and sum(rule_id(name,True) is not None for name in debuffs)>=2:
            enemy_page = enemy_page or not any(label in joined for label in ('购买经验','商店'))
        # Investment descriptions can contain damage, refresh and upgrade terms.
        # Use the actual page heading before interpreting those words as scenes.
        investment_heading=any(normalize(r["text"]) in ("投资策略","投资环境","选择投资")
                               and (r["box"][1]+r["box"][3])/2/shape[0]<.20 for r in rows)
        investment_detail=bool(investment_detail_headers(rows,shape))
        resume_page=any('继续进度' in r['text'] for r in rows) and any('结束并结算' in r['text'] for r in rows)
        if resume_page:
            scene='对局菜单'
        elif seasonal and headings & {"标准博弈","超频博弈"} and any(
            normalize(r["text"])=="开始对局" and r["box"][1]>.8*shape[0] for r in confident
        ):
            scene='开局菜单'
        elif voyage_heading:
            scene='奇遇'
        elif spotlight_heading:
            scene='光环选择'
        elif spotlight_confirmed:
            scene='光环详情'
        elif investment_detail:
            scene='准备'
        elif enemy_page:
            scene="敌人情报"
        elif investment_heading:
            scene="投资选择"
        elif any(word in joined for word in ("我方行动中","敌方行动中","自动战斗")) or ("伤害" in joined and "刷新" not in joined and "开始战斗" not in joined):
            scene="战斗"
        elif any(normalize(r['text']).startswith(('投资策略','投资环境','选择投资')) for r in rows) and "刷新商店" not in joined:
            scene="投资选择"
        elif any(word in joined for word in ("商店","开始战斗","购买经验","刷新","备战","升级")):
            scene="准备"
        else:
            scene="其他"
        state=GameState(scene=scene,at=time.time())
        if seasonal:
            state.difficulty = observe_rank(rows, shape) or PENDING_RANK
            if headings & {"超频博弈"} and not headings & {"标准博弈"}:
                state.mode = "超频博弈"
            elif headings & {"标准博弈"} and not headings & {"超频博弈"}:
                state.mode = "标准博弈"
            if voyage_heading:
                state.voyage = observe_voyage(confident)
            if spotlight_heading or spotlight_confirmed:
                state.spotlight_choices = spotlight_items(confident,catalog,shape,spotlight_confirmed)
        else:
            difficulty = detect_a8_difficulty(rows, shape)
            if difficulty is not None:
                state.difficulty = f"普通 A8·{difficulty}"
        state.enemy_difficulty, state.debuffs = enemy_difficulty, debuffs
        if resume_page:
            for row in rows:
                match=re.search(r'当前进度\s*([1-5])\s*[-一]\s*(\d{1,2})',row['text'])
                if match and row['confidence']>=.85:state.round=f'{match[1]}-{match[2]}'
            return state
        if scene=="投资选择":
            headings={normalize(r["text"]) for r in rows if (r["box"][1]+r["box"][3])/2/shape[0]<.20}
            state.investment_kind="环境" if "投资环境" in headings else "策略" if "投资策略" in headings else ""
        h,w=shape[:2]
        for row in rows:
            text=row["text"]; box=row["box"]; x,y=(box[0]+box[2])/2/w,(box[1]+box[3])/2/h
            if row["confidence"]<.85:
                continue
            if y<.075:
                round_match=re.fullmatch(r"([1-5])\s*[-一]\s*(\d{1,2})",text)
                if round_match and .27<x<.45:
                    state.round=f"{round_match[1]}-{round_match[2]}"
                if text.isdigit():
                    number=int(text)
                    if .523<x<.553 and number<=999:
                        state.hp=number
                    elif .565<x<.598 and number<=999:
                        state.gold=number
            if scene=="准备" and .128<x<.17 and .077<y<.13:
                round_match=re.fullmatch(r"([1-5])\s*[-一]\s*(\d{1,2})",text)
                if round_match:state.round=f"{round_match[1]}-{round_match[2]}"
            if scene=="准备" and text.isdigit() and .844<x<.875 and .829<y<.88:
                state.gold=int(text)
            level_match=re.search(r"(?:等级|Lv\.?|LV\.?)\s*(10|[1-9])\b",text) if scene != '敌人情报' else None
            if level_match:
                state.level=int(level_match[1])
            if text.isdigit() and scene=="准备" and .15<x<.27 and .78<y<.93 and 1<=int(text)<=10:
                # This is only a candidate; isolated card prices must not become team level.
                nearby=any("等级" in r["text"] and abs((r["box"][1]+r["box"][3])/2-(box[1]+box[3])/2)<45 for r in rows)
                if nearby:
                    state.level=int(text)
            if re.fullmatch(r"\d{1,3}/\d{1,3}",text) and .1<x<.32 and y>.72 and scene=="准备":
                state.xp=text
        if spotlight_confirmed:
            plane = int(state.round[0]) if state.round else None
            if plane is None:
                planes = {"一":1,"二":2,"1":1,"2":2}
                plane = next((planes[m[1]] for label in headings
                              if (m := re.fullmatch(r"第?([一二12])位面", label))),None)
            if plane in (1,2) and len(state.spotlight_choices)==1:
                item = state.spotlight_choices[0]
                item.slot = plane
                state.spotlights[plane] = item
            state.spotlight_choices = []
        return state

    def analyze(self,image):
        rows=self.read_text(image)
        state=self.parse_rows(rows,image.shape)
        selected=selected_investments(rows,self.catalog,state.scene,image.shape)
        for item in selected:
            if item.kind=='环境':state.environment=item
            else:state.strategies.append(item)
        if state.scene in ('敌人情报','奇遇','光环选择','光环详情','对局菜单','开局菜单'):
            # Opponent portraits are never player-owned roles or shop cards.
            return state, rows
        standard_layout=state.scene=="准备" and any("购买经验" in r["text"] for r in rows) and any("后台区域" in r["text"] for r in rows)
        if standard_layout:
            state.visible_zones={"前台","后台","备战","库存"}
        if state.scene=="准备" and any("购买经验" in r["text"] for r in rows):
            h,w=image.shape[:2]
            crop=image[int(h*.8287):int(h*.8658),int(w*.13125):int(w*.1771)]
            if crop.size:
                for row in self.read_text(cv2.resize(crop,None,fx=4,fy=4)):
                    if row["confidence"]>=.9:
                        match=re.fullmatch(r"(?:Lv\.?|LV\.?)\s*(10|[1-9])",row["text"])
                        if match:state.level=int(match[1])
        entities=[]
        if state.scene=='准备' and any('购买经验' in r['text'] for r in rows):
            entities.extend(self.matcher.portraits.bench(image,self.regions['备战'],set(self.catalog.roles)))
        for row in rows:
            if row["confidence"]<.80:
                continue
            token=normalize(row["text"])
            for kind in ("角色","装备","策略","环境"):
                if state.scene=="投资选择":
                    # Only card titles are choices. Names inside effects are not
                    # owned roles, equipment, or additional selectable cards.
                    if kind not in ("策略","环境") or not .22<(row["box"][1]+row["box"][3])/2/image.shape[0]<.41:
                        continue
                    if state.investment_kind and kind!=state.investment_kind:
                        continue
                matching=[identifier for identifier,item in self.catalog.pool(kind).items() if normalize(item.get("name",""))==token and len(token)>=2]
                if matching:
                    entities.append({"kind":kind,"ids":matching,"box":row["box"],"confidence":row["confidence"],"source":"文字"})
                    break
        if state.scene in ("准备","战斗") and self.matcher.has_templates():
            entities.extend(self.matcher.find(image))
        if state.scene=="准备" and any("后台区域" in r["text"] for r in rows):
            h,w=image.shape[:2]
            for zone in ("前台","后台","备战","库存"):
                kinds={"装备"} if zone=="库存" else {"角色"}
                if not self.matcher.has_templates(kinds):continue
                a,b,c,d=self.regions[zone] if zone in self.calibrated else DEFAULT_REGIONS[zone]
                x,y,x2,y2=int(a*w),int(b*h),int(c*w),int(d*h)
                for found in self.matcher.find(image[y:y2,x:x2],kinds=kinds):
                    l,t,r,bt=found["box"]
                    found["box"]=(l+x,t+y,r+x,bt+y)
                    found["zone_hint"]=zone
                    entities.append(found)
            if "库存" not in self.calibrated:
                entities.extend(self.matcher.inventory(image))
        used=[]
        for entity in sorted(entities,key=lambda e:(e["source"]=="库存图标",e["confidence"]),reverse=True):
            box=entity["box"]
            kind=entity["kind"]
            if any(old["kind"]==kind and set(old["ids"])&set(entity["ids"]) and abs(sum(box[::2])/2-sum(old["box"][::2])/2)<45 and abs(sum(box[1::2])/2-sum(old["box"][1::2])/2)<65 for old in used):
                continue
            used.append(entity)
            zone=entity.get("zone_hint") or self.zone(kind,box,image.shape,state.scene,rows)
            if len(entity["ids"])!=1:
                state.unresolved.append({**entity,"zone":zone,"reason":"同一头像对应多个玩法形态，请确认费用或名称"})
                continue
            identifier=entity["ids"][0]
            item=Seen(identifier,self.catalog.name(identifier,kind),kind,zone,confidence=entity["confidence"],source=entity["source"],box=box)
            if state.scene=="投资选择" and kind in ("策略","环境"):
                item.slot=min(2,max(0,int((box[0]+box[2])/2/image.shape[1]*3)))
                state.investment_choices.append(item)
                continue
            if kind=="角色" and zone in ("前台","后台","备战") and state.scene=="准备":
                item.star=visible_stars(image,box)
            if kind=="装备":item.slot=entity.get("slot",-1)
            if kind=="角色":
                if zone=="商店":
                    item.slot=min(4,max(0,int(((box[0]+box[2])/2/image.shape[1]-.19)/.14)))
                    state.shop.append(item)
                elif zone in ("前台","后台","备战"):
                    state.roles.append(item)
                else:
                    state.unresolved.append({**entity,"zone":zone,"reason":"已识别名称，持有位置待确认"})
            elif kind=="装备":
                if zone in ("库存","已装备"):
                    state.equipment.append(item)
                else:
                    state.unresolved.append({**entity,"zone":zone,"reason":"装备已识别，库存或穿戴状态待确认"})
            elif kind=="策略":
                if not any(s.id==item.id and s.zone=='已选' for s in state.strategies):
                    state.strategies.append(item)
            elif kind=="环境" and (not state.environment or state.environment.zone!='已选'):
                state.environment=item
        # A shop card may be found by both its title and its portrait. Count the slot once.
        by_slot={}
        for item in state.shop:
            previous=by_slot.get(item.slot)
            if previous is None or item.confidence>previous.confidence:
                by_slot[item.slot]=item
        state.shop=[by_slot[s] for s in sorted(by_slot)]
        choice_slots={}
        for item in state.investment_choices:
            previous=choice_slots.get(item.slot)
            if previous is None or item.confidence>previous.confidence:
                choice_slots[item.slot]=item
        state.investment_choices=[choice_slots[s] for s in sorted(choice_slots)]
        if state.scene=="投资选择" and len(state.investment_choices)<3:
            state.warning="投资卡片未识别完整；请在“已识别”中纠正待选项，确认后再选择。"
        inventory_slots=[e for e in state.equipment if e.source=="库存图标"]
        if inventory_slots:
            state.equipment=inventory_slots+[e for e in state.equipment if e.zone!="库存"]
        for equipment in state.equipment:
            if equipment.zone=="已装备":
                ex=(equipment.box[0]+equipment.box[2])/2
                ey=(equipment.box[1]+equipment.box[3])/2
                valid=[r for r in state.roles if r.box and r.box[3]<=ey+30 and abs((r.box[0]+r.box[2])/2-ex)<140]
                if valid:
                    equipment.equipped_to=min(valid,key=lambda r:abs((r.box[0]+r.box[2])/2-ex)).id
        if not self.regions_calibrated and state.scene=="准备":
            state.warning="使用已验证的PC卡片布局；若位置不符，请校准。隐藏信息或星级不清楚时需要确认。"
        return state,rows

    def save_crop(self,image,box,kind,identifier):
        left,top,right,bottom=[max(0,int(v)) for v in box]
        crop=image[top:bottom,left:right]
        if crop.size<100 or crop.std()<5:
            raise ValueError("请框选完整的头像或装备图标")
        target=self.data / "custom_icons" / f"{kind}-{identifier}-{int(time.time())}.png"
        target.parent.mkdir(parents=True,exist_ok=True)
        cv2.imencode(".png",crop)[1].tofile(str(target))
        entries=read_json(self.data / "custom_icons.json",[])
        entries.append({"kind":kind,"id":identifier,"path":str(target.relative_to(self.data))})
        write_json(self.data / "custom_icons.json",entries[-150:])
        self.matcher.custom.append((entries[-1],crop))


class StateTracker:
    """Visible shop is transient; hidden inventory is retained as last observed, never guessed."""
    def __init__(self, difficulty="普通 A8·待确认"):
        self.default_difficulty = difficulty
        self.state=GameState(difficulty=difficulty)
        self.manual=[]
        self.manual_shop=None
        self.manual_equipment=None
        self.ignored=set()
        self.last_shop_signature=None
        self.pending_signature=None
        self.pending_at=0
        self.last_investment_signature=None

    def merge(self,observed:GameState):
        old=self.state
        # Keep the last confirmed A8 variant while the banner is temporarily
        # covered by a transition or the assistant overlay.
        if observed.difficulty not in ("普通 A8·待确认",PENDING_RANK) and 'difficulty' not in old.manual_fields:
            old.difficulty = observed.difficulty
        if observed.mode:
            old.mode = observed.mode
        if observed.voyage and "voyage" not in old.manual_fields:
            if not old.voyage or old.voyage.name != observed.voyage.name or observed.voyage.id:
                old.voyage = observed.voyage
        old.spotlight_choices = observed.spotlight_choices if observed.scene=="光环选择" else []
        for plane,item in observed.spotlights.items():
            if f"spotlight_{plane}" not in old.manual_fields:
                old.spotlights[plane] = item
        if observed.enemy_difficulty is not None and 'enemy_difficulty' not in old.manual_fields:
            old.enemy_difficulty = observed.enemy_difficulty
        if observed.debuffs and 'debuffs' not in old.manual_fields:
            old.debuffs = list(observed.debuffs)
        # Corrections last until a reliably observed value changes or a new round starts.
        if observed.round and observed.round!=old.round:
            old.manual_fields.difference_update(('round','gold','level','hp','xp','capacity'))
        for field in ("round","gold","level","xp","hp","capacity"):
            value=getattr(observed,field)
            if value is not None:
                old.manual_fields.discard(field)
                setattr(old,field,value)
        old.scene=observed.scene; old.at=observed.at; old.warning=observed.warning
        old.unresolved=observed.unresolved
        old.visible_zones=observed.visible_zones
        old.investment_kind=observed.investment_kind
        # Choices are transient, separate from investments confirmed as selected.
        # Leaving the page never implies which of the three cards was selected.
        if observed.scene=="投资选择":
            manual=[s for s in old.investment_choices if s.source=="手动"]
            signature=tuple(sorted((s.kind,s.id,s.slot) for s in observed.investment_choices))
            if self.last_investment_signature is not None and signature!=self.last_investment_signature:
                manual=[]
            self.last_investment_signature=signature
            old.investment_choices=manual+[s for s in observed.investment_choices
                                          if (s.kind,s.id,s.zone) not in self.ignored
                                          and s.slot not in {v.slot for v in manual}
                                          and (s.kind,s.id) not in {(v.kind,v.id) for v in manual}]
        else:
            old.investment_choices=[]
            self.last_investment_signature=None
        # Fully visible panels replace automatic records, including an empty inventory.
        # A missed icon becomes unknown rather than a phantom owned unit after a sale.
        previous=list(old.roles)
        matched=set()
        fresh=[]
        def near(a,b):
            if not a.box or not b.box:
                return None
            dx=abs((a.box[0]+a.box[2]-b.box[0]-b.box[2])/2)
            dy=abs((a.box[1]+a.box[3]-b.box[1]-b.box[3])/2)
            return dx*dx+dy*dy if dx<45 and dy<65 else None
        for seen in observed.roles:
            if (seen.kind,seen.id,seen.zone) in self.ignored:continue
            if any(r.id==seen.id and r.zone==seen.zone and r.source=="手动" for r in previous):
                continue
            candidates=[(distance,i) for i,r in enumerate(previous)
                        if i not in matched and r.source!="手动" and r.id==seen.id and r.zone==seen.zone
                        and (distance:=near(r,seen)) is not None]
            if candidates:
                _,i=min(candidates)
                matched.add(i)
                if observed.scene!="准备":seen.star=seen.star or previous[i].star
            fresh.append(seen)
        old.roles=[r for i,r in enumerate(previous) if r.source=="手动" or
                   (i not in matched and r.zone not in observed.visible_zones)]+fresh
        old.roles=[r for r in old.roles if r.source=="手动" or time.time()-r.at<180]
        if "库存" in observed.visible_zones or any(e.source=="库存图标" for e in observed.equipment):
            old.equipment=[e for e in old.equipment if e.zone!="库存" or e.source=="手动"]
        for seen in observed.equipment:
            if (seen.kind,seen.id,seen.zone) in self.ignored:continue
            if not any(e.id==seen.id and e.zone==seen.zone and e.equipped_to==seen.equipped_to and e.source=="手动" for e in old.equipment):
                old.equipment=[e for e in old.equipment if not(e.id==seen.id and e.zone==seen.zone and e.equipped_to==seen.equipped_to and e.slot==seen.slot and e.source!="手动")]
                old.equipment.append(seen)
        old.equipment=[e for e in old.equipment if e.source=="手动" or time.time()-e.at<180]
        if observed.scene=="准备":
            old.shop=observed.shop
        else:
            old.shop=[]
        if self.manual_shop is not None and observed.scene=="准备":
            old.shop=self.manual_shop
            old.warning=(old.warning+" 商店为手动记录；刷新后请清除手动商店。").strip()
        chosen=[s for s in old.strategies if s.zone=="已选"]
        old.strategies=chosen+[s for s in observed.strategies if s.zone!="待选" and s.id not in {v.id for v in chosen}]
        if old.environment and old.environment.zone=="待选":
            old.environment=None
        if observed.environment and (observed.environment.zone=='已选' or not old.environment or old.environment.zone!="已选"):
            old.environment=observed.environment
        return old

    def reset(self):
        self.__init__(self.default_difficulty)
