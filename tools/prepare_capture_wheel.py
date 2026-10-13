"""Rebuild upstream capture wheel metadata for one shared headless OpenCV.

No Python source or native binary is changed. The local version marks the patch;
the original wheel, patch notice, RECORD hashes, and licenses remain auditable.
"""
from pathlib import Path
import argparse
import base64
import copy
import csv
import hashlib
import io
import re
import subprocess
import sys
import zipfile

UPSTREAM='2.0.1'
LOCAL=UPSTREAM+'+cwa.headless1'


def patch_wheel(source,destination):
    with zipfile.ZipFile(source) as archive:
        metadata=next(n for n in archive.namelist() if n.endswith('.dist-info/METADATA'))
        prefix=metadata.rsplit('/',1)[0]
        renamed='windows_capture-'+LOCAL+'.dist-info'
        original=archive.read(metadata).decode('utf8')
        if f'Version: {UPSTREAM}\n' not in original:raise ValueError('Unexpected upstream capture version')
        changed,n=re.subn(r'(?m)^(Requires-Dist: )opencv-python(?=[\s(<>=;]|$)',r'\1opencv-python-headless',original)
        if n!=1:raise ValueError('Unexpected OpenCV dependency; inspect upstream metadata')
        changed=changed.replace(f'Version: {UPSTREAM}\n',f'Version: {LOCAL}\n')
        entries=[]
        for info in archive.infolist():
            if info.filename==prefix+'/RECORD':continue
            data=changed.encode('utf8') if info.filename==metadata else archive.read(info.filename)
            target=copy.copy(info)
            if target.filename.startswith(prefix+'/'):target.filename=renamed+target.filename[len(prefix):]
            entries.append((target,data))
        notice=(f'CurrencyWarAssistant local metadata patch: {UPSTREAM} -> {LOCAL}\n'
                'Only Requires-Dist opencv-python -> opencv-python-headless and distribution version were changed.\n'
                'Upstream Python sources and native binaries are byte-identical. Original notices are retained.\n')
        entries.append((zipfile.ZipInfo(renamed+'/CWA-PATCH.txt',date_time=(2026,10,12,0,0,0)),notice.encode()))
        record=io.StringIO(newline='');writer=csv.writer(record,lineterminator='\n')
        for info,data in entries:
            digest=base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
            writer.writerow((info.filename,'sha256='+digest,len(data)))
        writer.writerow((renamed+'/RECORD','',''))
        destination.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as out:
            for info,data in entries:out.writestr(info,data)
            out.writestr(zipfile.ZipInfo(renamed+'/RECORD',date_time=(2026,10,12,0,0,0)),record.getvalue())
    return destination


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--install',action='store_true')
    args=parser.parse_args();root=Path(__file__).resolve().parent.parent
    folder=root/'outputs/wheels';upstream=folder/'upstream';upstream.mkdir(parents=True,exist_ok=True)
    subprocess.run([sys.executable,'-m','pip','download','--no-deps','--only-binary=:all:',f'windows-capture=={UPSTREAM}','-d',str(upstream)],check=True)
    source=next(upstream.glob(f'windows_capture-{UPSTREAM}-*.whl'))
    target=folder/source.name.replace('-'+UPSTREAM+'-','-'+LOCAL+'-')
    patch_wheel(source,target)
    if args.install:
        subprocess.run([sys.executable,'-m','pip','uninstall','-y','windows-capture','opencv-python','opencv-python-headless'],check=True)
        subprocess.run([sys.executable,'-m','pip','install','--no-deps','opencv-python-headless==5.0.0.93',str(target)],check=True)
    print(target)


if __name__=='__main__':main()
