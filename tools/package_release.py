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
sys.path.insert(0,str(root))
from currency_war_assistant import __version__
from tools.release_licenses import collect_license, validate_manifest, include_distribution
from PyInstaller.archive.readers import CArchiveReader
release=root/'outputs/CurrencyWarAssistant'
program=release/'CurrencyWarAssistant.exe'
if not program.exists():raise RuntimeError('Please build CurrencyWarAssistant.exe first')
capture_files=release/'_internal'/'windows_capture'
if not (capture_files/'__init__.py').is_file() or not list(capture_files.glob('*.pyd')):
    raise RuntimeError('Release is missing windows_capture Python/native files')
for name in ('README.md','README.en.md','README.ja.md','QUICKSTART.md','CHANGELOG.md','REVIEW-CHECKLIST.md','LICENSE','NOTICE.md'):
    shutil.copyfile(root/name,release/name)
for old in ('使用说明.md','先读我.txt','.gitignore'):
    path=release/old
    if path.exists():path.unlink()
old_licenses=release/'第三方许可'
if old_licenses.exists():
    if old_licenses.is_symlink() or old_licenses.resolve().parent!=release.resolve():raise RuntimeError('Unsafe generated license path')
    shutil.rmtree(old_licenses)
licenses=release/'licenses'
if licenses.exists():
    if licenses.is_symlink() or licenses.resolve().parent!=release.resolve():raise RuntimeError('Unsafe generated license path')
    shutil.rmtree(licenses)
licenses.mkdir(exist_ok=True)
manifest=[]
frozen_modules=CArchiveReader(str(program)).open_embedded_archive('PYZ.pyz').toc.keys()
for dist in importlib.metadata.distributions():
    if not include_distribution(dist.metadata['Name'],frozen_modules,release/'_internal'):continue
    manifest.append(collect_license(dist,release))
python_license=Path(sys.base_prefix)/'LICENSE.txt'
if python_license.exists():shutil.copyfile(python_license,licenses/'Python-LICENSE.txt')
validate_manifest(manifest)
(licenses/'dependencies.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
source_zip=root/f'outputs/CurrencyWarAssistant-source-v{__version__}.zip'
selected=[root/f for f in ('main.py','assistant.spec','requirements.txt','requirements-dev.txt','requirements-lock.txt','README.md','README.en.md','README.ja.md','QUICKSTART.md','CHANGELOG.md','REVIEW-CHECKLIST.md','.gitignore','LICENSE','NOTICE.md')]
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
release_zip=root/f'outputs/CurrencyWarAssistant-v{__version__}-windows-x64.zip'
with zipfile.ZipFile(release_zip,'w',zipfile.ZIP_DEFLATED) as archive:
    for path in release.rglob('*'):
        relative=path.relative_to(release)
        if not path.is_file() or '__pycache__' in relative.parts or 'CurrencyWarAssistantData' in relative.parts:continue
        archive.write(path,relative.as_posix())
print(json.dumps({'source':str(source_zip),'release':str(release_zip),'source_files':len(selected),'dependency_licenses':len(manifest),'program':str(program)},ensure_ascii=False))
