from pathlib import Path
from importlib.util import find_spec
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

root=Path(SPECPATH)
ocr_data,ocr_binaries,ocr_hidden=collect_all('rapidocr')
capture_data,capture_binaries,capture_hidden=collect_all('windows_capture')
# Include the native extension explicitly: collecting Python sources alone does
# not verify that the frozen application can load its window-capture backend.
capture_path=Path(find_spec('windows_capture').origin).parent
capture_binaries += [(str(path),'windows_capture') for path in capture_path.glob('*.pyd')]
a=Analysis([str(root/'main.py')],pathex=[str(root)],
    binaries=ocr_binaries+capture_binaries+collect_dynamic_libs('onnxruntime'),
    datas=ocr_data+capture_data,
    hiddenimports=ocr_hidden+capture_hidden,
    hookspath=[],hooksconfig={},runtime_hooks=[],
    excludes=['pytest','IPython','matplotlib','paddle','torch','tensorflow'],
    noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='CurrencyWarAssistant',debug=False,
    bootloader_ignore_signals=False,strip=False,upx=False,console=False,
    disable_windowed_traceback=False)
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='CurrencyWarAssistant')
