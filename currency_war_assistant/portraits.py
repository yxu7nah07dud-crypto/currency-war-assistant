"""Private, on-demand public portrait cache; no game artwork ships in releases."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
from urllib.parse import urlsplit
import urllib.request
import uuid

import cv2
import numpy as np

from .paths import read_json,write_json

HOSTS={'act-webstatic.mihoyo.com','act-webstatic.hoyoverse.com'}


def sync_portraits(data,catalog,fetch=None):
    folder=Path(data)/'official_portraits';folder.mkdir(parents=True,exist_ok=True)
    sources={}
    for role in catalog.roles.values():sources.setdefault(role.get('icon',''),[]).append(str(role['id']))
    def load(url):
        if urlsplit(url).scheme!='https' or urlsplit(url).hostname not in HOSTS:return None
        filename=hashlib.sha256(url.encode()).hexdigest()+'.png';path=folder/filename
        try:
            if not path.exists():
                if fetch is None:
                    with urllib.request.urlopen(url,timeout=12) as response:
                        if urlsplit(response.geturl()).hostname not in HOSTS:return None
                        content=response.read(2_000_001)
                else:content=fetch(url)
                if len(content)>2_000_000:return None
                image=cv2.imdecode(np.frombuffer(content,dtype=np.uint8),cv2.IMREAD_UNCHANGED)
                if image is None or len(image.shape)!=3 or image.shape[2]!=4 or max(image.shape[:2])>1024:return None
                temporary=folder/(filename+'.'+uuid.uuid4().hex+'.tmp')
                temporary.write_bytes(content);temporary.replace(path)
            return {'url':url,'file':filename}
        except (OSError,ValueError,cv2.error):return None
    with ThreadPoolExecutor(max_workers=4) as pool:
        entries=[{**value,'id':identifier} for value in pool.map(load,sources) if value
                 for identifier in sources[value['url']]]
    write_json(folder/'manifest.json',{'entries':entries})
    return len(entries)


class PortraitBank:
    def __init__(self,data):
        self.references=[]
        self.sift=None
        folder=Path(data)/'official_portraits'
        entries=read_json(folder/'manifest.json',{}).get('entries',[])
        groups={}
        for entry in entries:
            filename=entry.get('file','')
            if not filename or Path(filename).name!=filename:continue
            path=folder/filename
            if not path.is_file():continue
            content=path.read_bytes();digest=hashlib.sha256(content).hexdigest()
            if digest in groups:
                groups[digest]['ids'].append(str(entry['id']));continue
            image=cv2.imdecode(np.frombuffer(content,dtype=np.uint8),cv2.IMREAD_UNCHANGED)
            if image is None or len(image.shape)!=3 or image.shape[2]!=4:continue
            if self.sift is None:self.sift=cv2.SIFT_create(nfeatures=700,contrastThreshold=.02)
            gray=cv2.cvtColor(image[:,:,:3],cv2.COLOR_BGR2GRAY)
            points,desc=self.sift.detectAndCompute(gray,(image[:,:,3]>128).astype(np.uint8)*255)
            if desc is None:continue
            groups[digest]={'ids':[str(entry['id'])],'points':points,'desc':desc,'shape':image.shape[:2]}
        self.references=list(groups.values())

    def bench(self,image,region,valid_ids):
        if not self.references:return []
        h,w=image.shape[:2];a,b,c,d=region
        left,top,right,bottom=round(a*w),round(b*h),round(c*w),round(d*h)
        step=(right-left)/9
        bf=cv2.BFMatcher(cv2.NORM_L2);found=[]
        for slot in range(9):
            x1,x2=round(left+slot*step),round(left+(slot+1)*step)
            crop=image[top:bottom,x1:x2]
            if not crop.size:continue
            scale=max(1,125/crop.shape[1])
            small=cv2.resize(crop,None,fx=scale,fy=scale) if scale>1 else crop
            points,desc=self.sift.detectAndCompute(cv2.cvtColor(small,cv2.COLOR_BGR2GRAY),None)
            if desc is None or len(points)<8:continue
            candidates=[]
            for reference in self.references:
                ids=[i for i in reference['ids'] if i in valid_ids]
                if not ids:continue
                pairs=bf.knnMatch(reference['desc'],desc,k=2)
                good=[p[0] for p in pairs if len(p)==2 and p[0].distance<.72*p[1].distance and p[0].distance<260]
                if len(good)<8:continue
                src=np.float32([reference['points'][m.queryIdx].pt for m in good])
                dst=np.float32([points[m.trainIdx].pt for m in good])
                matrix,mask=cv2.findHomography(src,dst,cv2.RANSAC,3)
                if matrix is None or mask is None:continue
                count=int(mask.sum())
                if count<8 or count/len(good)<.55:continue
                inliers=dst[mask.ravel().astype(bool)]
                center=inliers.mean(axis=0)
                # A tiny overlap from the neighboring card is not another copy.
                if not .15*small.shape[1]<center[0]<.85*small.shape[1]:continue
                if np.ptp(inliers[:,0])<.20*small.shape[1] or np.ptp(inliers[:,1])<.15*small.shape[0]:continue
                candidates.append((count,ids))
            candidates.sort(key=lambda value:value[0],reverse=True)
            if not candidates:continue
            score,ids=candidates[0]
            if len(candidates)>1 and score-candidates[1][0]<4:continue
            found.append({'kind':'角色','ids':ids,'box':(x1,top,x2,bottom),'zone_hint':'备战',
                          'confidence':min(.99,.80+score*.006),'source':'官方图标','slot':slot})
        return found
