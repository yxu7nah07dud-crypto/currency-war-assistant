from __future__ import annotations

from difflib import SequenceMatcher
import threading
import time
import re

import cv2
import numpy as np

from .models import Seen, Catalog, GameState, normalize
from .paths import read_json, write_json


DEFAULT_REGIONS = {
    "商店": [.19, .045, .88, .31],
    "备战": [.195, .78, .79, .91],
    "前台": [.26, .39, .72, .54],
    "后台": [.26, .59, .73, .72],
    "库存": [.93, .21, .985, .60],
}


def region_contains(box, rect, shape):
    h,w = shape[:2]
    x,y = (box[0]+box[2])/2/w, (box[1]+box[3])/2/h
    a,b,c,d = rect
    return a <=x<=c and b<=y<=d


class IconMatcher:
    def __init__(self, data):
        self.sift = cv2.SIFT_create(nfeatures=120)
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

    def find(self, image, kinds=None):
        height,width=image.shape[:2]
        scale=min(1,1280/width)
        small=cv2.resize(image,None,fx=scale,fy=scale) if scale<1 else image
        gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
        kp,desc=cv2.SIFT_create(nfeatures=2400).detectAndCompute(gray,None)
        found=[]
        if desc is None:
            return found
        for items,(th,tw),tpoints,tdesc in self.templates:
            if kinds and items[0]["kind"] not in kinds:
                continue
            pairs=self.bf.knnMatch(tdesc,desc,k=2)
            good=[a for a,b in pairs if a.distance<.70*b.distance and a.distance<250]
            if len(good)<5:
                continue
            src=np.float32([tpoints[m.queryIdx].pt for m in good])
            dst=np.float32([kp[m.trainIdx].pt for m in good])
            matrix,mask=cv2.findHomography(src,dst,cv2.RANSAC,3)
            if matrix is None or mask is None or mask.sum()<5:
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

    def inventory(self,image):
        """Match each separate inventory cell, retaining duplicate material copies."""
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
        if any(word in joined for word in ("我方行动中","敌方行动中","自动战斗")) or ("伤害" in joined and "刷新" not in joined and "开始战斗" not in joined):
            scene="战斗"
        elif any(word in joined for word in ("投资策略","投资环境","选择投资")) and "刷新商店" not in joined:
            scene="投资选择"
        elif any(word in joined for word in ("商店","开始战斗","购买经验","刷新","备战","升级")):
            scene="准备"
        else:
            scene="其他"
        state=GameState(scene=scene,at=time.time())
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
            level_match=re.search(r"(?:等级|Lv\.?|LV\.?)\s*(10|[1-9])\b",text)
            if level_match:
                state.level=int(level_match[1])
            if text.isdigit() and scene=="准备" and .15<x<.27 and .78<y<.93 and 1<=int(text)<=10:
                # This is only a candidate; isolated card prices must not become team level.
                nearby=any("等级" in r["text"] and abs((r["box"][1]+r["box"][3])/2-(box[1]+box[3])/2)<45 for r in rows)
                if nearby:
                    state.level=int(text)
            if re.fullmatch(r"\d{1,3}/\d{1,3}",text) and .1<x<.32 and y>.72 and scene=="准备":
                state.xp=text
        return state

    def analyze(self,image):
        rows=self.read_text(image)
        state=self.parse_rows(rows,image.shape)
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
        for row in rows:
            if row["confidence"]<.80:
                continue
            token=normalize(row["text"])
            for kind in ("角色","装备","策略","环境"):
                matching=[identifier for identifier,item in self.catalog.pool(kind).items() if normalize(item.get("name",""))==token and len(token)>=2]
                if matching:
                    entities.append({"kind":kind,"ids":matching,"box":row["box"],"confidence":row["confidence"],"source":"文字"})
                    break
        if state.scene in ("准备","战斗"):
            entities.extend(self.matcher.find(image))
        if state.scene=="准备" and any("后台区域" in r["text"] for r in rows):
            h,w=image.shape[:2]
            for zone in ("前台","后台","备战","库存"):
                a,b,c,d=self.regions[zone] if zone in self.calibrated else DEFAULT_REGIONS[zone]
                x,y,x2,y2=int(a*w),int(b*h),int(c*w),int(d*h)
                for found in self.matcher.find(image[y:y2,x:x2],kinds={"装备"} if zone=="库存" else {"角色"}):
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
            item=Seen(identifier,self.catalog.name(identifier),kind,zone,confidence=entity["confidence"],source=entity["source"],box=box)
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
                state.strategies.append(item)
            elif kind=="环境":
                state.environment=item
        # A shop card may be found by both its title and its portrait. Count the slot once.
        by_slot={}
        for item in state.shop:
            previous=by_slot.get(item.slot)
            if previous is None or item.confidence>previous.confidence:
                by_slot[item.slot]=item
        state.shop=[by_slot[s] for s in sorted(by_slot)]
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
        target=self.data / "自定义图标" / f"{kind}-{identifier}-{int(time.time())}.png"
        target.parent.mkdir(parents=True,exist_ok=True)
        cv2.imencode(".png",crop)[1].tofile(str(target))
        entries=read_json(self.data / "custom_icons.json",[])
        entries.append({"kind":kind,"id":identifier,"path":str(target.relative_to(self.data))})
        write_json(self.data / "custom_icons.json",entries[-150:])
        self.matcher.custom.append((entries[-1],crop))


class StateTracker:
    """Visible shop is transient; hidden inventory is retained as last observed, never guessed."""
    def __init__(self):
        self.state=GameState()
        self.manual=[]
        self.manual_shop=None
        self.manual_equipment=None
        self.ignored=set()
        self.last_shop_signature=None
        self.pending_signature=None
        self.pending_at=0

    def merge(self,observed:GameState):
        old=self.state
        # Corrections last until a reliably observed value changes or a new round starts.
        if observed.round and observed.round!=old.round:
            old.manual_fields.clear()
        for field in ("round","gold","level","xp","hp","capacity"):
            value=getattr(observed,field)
            if value is not None:
                old.manual_fields.discard(field)
                setattr(old,field,value)
        old.scene=observed.scene; old.at=observed.at; old.warning=observed.warning
        old.unresolved=observed.unresolved
        old.visible_zones=observed.visible_zones
        # Fully visible panels replace automatic records, including an empty inventory.
        # A missed icon becomes unknown rather than a phantom owned unit after a sale.
        old.roles=[r for r in old.roles if r.source=="手动" or r.zone not in observed.visible_zones]
        # Fresh round overrides manual economic values: they cannot silently survive purchases.
        for seen in observed.roles:
            if (seen.kind,seen.id,seen.zone) in self.ignored:continue
            same=[r for r in old.roles if r.id==seen.id and r.zone==seen.zone and r.source!="手动"]
            if same:
                if observed.scene!="准备":seen.star=seen.star or same[0].star
                old.roles[old.roles.index(same[0])]=seen
            elif not any(r.id==seen.id and r.zone==seen.zone and r.source=="手动" for r in old.roles):
                old.roles.append(seen)
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
        if observed.strategies:
            chosen=[s for s in old.strategies if s.zone=="已选"]
            old.strategies=chosen+[s for s in observed.strategies if s.id not in {v.id for v in chosen}]
        if observed.environment and (not old.environment or old.environment.zone!="已选"):
            old.environment=observed.environment
        return old

    def reset(self):
        self.__init__()
