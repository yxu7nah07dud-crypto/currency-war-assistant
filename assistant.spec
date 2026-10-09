from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

root=Path(SPECPATH)
ocr_data,ocr_binaries,ocr_hidden=collect_all('rapidocr')
a=Analysis([str(root/'main.py')],pathex=[str(root)],
    binaries=ocr_binaries+collect_dynamic_libs('onnxruntime'),
    datas=ocr_data,
    hiddenimports=ocr_hidden+['windows_capture.windows_capture'],
    hookspath=[],hooksconfig={},runtime_hooks=[],
    excludes=['pytest','IPython','matplotlib','paddle','torch','tensorflow'],
    noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='CurrencyWarAssistant',debug=False,
    bootloader_ignore_signals=False,strip=False,upx=False,console=False,
    disable_windowed_traceback=False)
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='CurrencyWarAssistant')
