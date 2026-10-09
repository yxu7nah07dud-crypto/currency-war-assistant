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
release=root/'outputs/CurrencyWarAssistant'
program=release/'CurrencyWarAssistant.exe'
if not program.exists():raise RuntimeError('Please build CurrencyWarAssistant.exe first')
for name in ('README.md','README.en.md','README.ja.md','QUICKSTART.md','LICENSE','NOTICE.md','.gitignore'):
    shutil.copyfile(root/name,release/name)
for old in ('使用说明.md','先读我.txt'):
    path=release/old
    if path.exists():path.unlink()
old_licenses=release/'第三方许可'
if old_licenses.exists():shutil.rmtree(old_licenses)
licenses=release/'licenses'
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
(licenses/'dependencies.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
source_zip=root/'outputs/CurrencyWarAssistant-source-v1.0.0.zip'
selected=[root/f for f in ('main.py','assistant.spec','requirements.txt','requirements-lock.txt','README.md','README.en.md','README.ja.md','QUICKSTART.md','.gitignore','LICENSE','NOTICE.md')]
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
    for path in selected:archive.write(path,'CurrencyWarAssistant-source/'+str(path.relative_to(root)))
print(json.dumps({'source':str(source_zip),'source_files':len(selected),'dependency_licenses':len(manifest),'program':str(program)},ensure_ascii=False))
