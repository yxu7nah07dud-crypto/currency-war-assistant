"""Package the assistant's public source files and dependency licenses.

The source archive intentionally excludes game artwork, copied wiki/guide data,
local caches, screenshots and research captures. Those materials are not needed
to review the code and must not be redistributed with it.
"""
from pathlib import Path
import importlib.metadata
import json
import shutil
import sys
import zipfile

root=Path(__file__).resolve().parent.parent
release=root/'outputs/货币战争实时助手'
if not (release/'货币战争助手.exe').exists():raise RuntimeError('请先打包程序')
shutil.copyfile(root/'README.md',release/'使用说明.md')
(release/'先读我.txt').write_text('货币战争实时助手\n\n双击“货币战争助手.exe”，选择游戏窗口，点击“开始观察”。\n在“已识别”中核对角色、星级和装备；漏读时点“识别纠正”。\n攻略与备选提供真实攻略码、锁定阵容和官方原文。\n\n请保留整个文件夹，exe与_internal不能分开。\n不需要安装Python、不需要密钥。截图仅在本机识别。\n普通A8·30是默认分析场景，识别与建议仍需核对；详见使用说明.md。\n',encoding='utf-8-sig')
licenses=release/'第三方许可'
licenses.mkdir(exist_ok=True)
manifest=[]
for dist in importlib.metadata.distributions():
    name=dist.metadata['Name'];version=dist.version
    files=[]
    for relative in dist.files or []:
        if not relative.parts or not relative.parts[0].endswith('.dist-info'):continue
        if not any(x.lower().startswith(('license','copying','notice','authors')) for x in relative.parts):continue
        source=Path(dist.locate_file(relative))
        if source.is_file():
            target=licenses/name/Path(*relative.parts[1:])
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
            files.append(str(target.relative_to(release)))
    manifest.append({'name':name,'version':version,'licenses':files})
python_license=Path(sys.base_prefix)/'LICENSE.txt'
if python_license.exists():shutil.copyfile(python_license,licenses/'Python-LICENSE.txt')
(licenses/'依赖清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
source_zip=root/'outputs/货币战争助手源码.zip'
selected=[root/f for f in ('main.py','assistant.spec','requirements.txt','requirements-lock.txt','README.md','README.en.md','README.ja.md','.gitignore','LICENSE','NOTICE.md')]
for folder in ('currency_war_assistant','tests','tools'):
    for path in (root/folder).rglob('*'):
        if not path.is_file() or '__pycache__' in path.parts:continue
        if folder=='tests' and (path.parent!=root/'tests' or path.suffix!='.py'):continue
        if folder=='tools' and path.name in {'inspect_official_routes.py','prepare_assets.py'}:continue
        selected.append(path)
# Keep only the short policy note, never generated game data.
asset_note=root/'assets'/'README.md'
if asset_note.exists():
    selected.append(asset_note)
with zipfile.ZipFile(source_zip,'w',zipfile.ZIP_DEFLATED) as archive:
    for path in selected:archive.write(path,'货币战争助手源码/'+str(path.relative_to(root)))
print(json.dumps({'source':str(source_zip),'source_files':len(selected),'dependency_licenses':len(manifest),'program':str(release/'货币战争助手.exe')},ensure_ascii=False))
