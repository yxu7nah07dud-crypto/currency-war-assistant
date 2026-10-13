"""Collect original upstream notices; fail closed when a license is missing."""
from pathlib import Path
import hashlib
import urllib.request

OFFICIAL = {
    ('antlr4-python3-runtime','4.9.3'): 'https://raw.githubusercontent.com/antlr/antlr4/4.9.3/LICENSE.txt',
    ('flatbuffers','25.12.19'): 'https://raw.githubusercontent.com/google/flatbuffers/v25.12.19/LICENSE',
}


def collect_license(dist,release,fetch=None):
    name=dist.metadata['Name'];version=dist.version
    files=[];origins=[]
    for relative in dist.files or []:
        # License texts can live in dist-info OR the installed package itself.
        if not relative.parts or '..' in relative.parts or '__pycache__' in relative.parts:continue
        if relative.suffix.lower() in ('.py','.pyc','.pyo','.pyd','.dll','.so'):continue
        if not any(part.lower().startswith(('license','copying','notice','authors','thirdpartynotice','cwa-patch')) for part in relative.parts):continue
        source=Path(dist.locate_file(relative))
        if not source.is_file():continue
        parts=relative.parts[1:] if relative.parts[0].endswith('.dist-info') else relative.parts
        target=release/'licenses'/name/Path(*parts)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(source.read_bytes())
        files.append(target.relative_to(release).as_posix())
    if not files:
        url=OFFICIAL.get((name.lower(),version))
        if not url:raise RuntimeError(f'Missing license for {name} {version}; provide the original upstream notice before packaging')
        try:
            if fetch is None:
                with urllib.request.urlopen(url,timeout=20) as response:data=response.read()
            else:data=fetch(url)
            if len(data)<100 or b'<html' in data.lower():raise ValueError('Not an upstream license text')
        except Exception as error:
            raise RuntimeError(f'Cannot obtain {name} license from {url}; provide it manually before packaging') from error
        target=release/'licenses'/name/'LICENSE-upstream.txt'
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        files.append(target.relative_to(release).as_posix())
        origins.append({'url':url,'sha256':hashlib.sha256(data).hexdigest()})
    return {'name':name,'version':version,'licenses':files,'upstream_sources':origins}


def validate_manifest(manifest):
    empty=[item['name'] for item in manifest if not item.get('licenses')]
    if empty:raise RuntimeError('Missing dependency licenses: '+', '.join(empty))


def include_distribution(name,modules,internal):
    # PyInstaller's frozen archive may contain code absent from the file tree.
    # Keep setuptools if either its code or resources are bundled. Always retain
    # PyInstaller's licensing exception even though it is a build dependency.
    normalized=name.lower().replace('_','-')
    if normalized not in ('pip','setuptools'):return True
    module=normalized.replace('-','_')
    return (internal/module).exists() or any(m==module or m.startswith(module+'.') for m in modules)
