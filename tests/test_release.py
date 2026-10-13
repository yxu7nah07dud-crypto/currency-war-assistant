from pathlib import Path
from contextlib import contextmanager
import shutil
import uuid
from types import SimpleNamespace
import unittest

from tools.release_licenses import collect_license,validate_manifest,include_distribution


@contextmanager
def TemporaryDirectory(dir):
    # Windows sandbox ACLs reject tempfile's private 0700 directory mode.
    parent=Path(dir).resolve();target=parent/('release-'+uuid.uuid4().hex)
    target.mkdir(parents=True)
    try:yield str(target)
    finally:
        assert target.resolve().parent==parent
        shutil.rmtree(target)


class LicenseTests(unittest.TestCase):
    def test_unused_dev_licenses_are_excluded_but_frozen_code_is_checked(self):
        internal=Path('tests/_cache/absent')
        self.assertFalse(include_distribution('pip',[],internal))
        self.assertFalse(include_distribution('setuptools',[],internal))
        self.assertTrue(include_distribution('setuptools',['setuptools._distutils'],internal))
        self.assertTrue(include_distribution('pyinstaller',[],internal))

    def test_package_directory_notices_are_collected(self):
        with TemporaryDirectory(dir=Path(__file__).parent/'_cache') as temp:
            root=Path(temp);source=root/'installed/onnxruntime/LICENSE'
            source.parent.mkdir(parents=True);source.write_text('Original notice',encoding='utf8')
            dist=SimpleNamespace(metadata={'Name':'onnxruntime'},version='fixture',files=[Path('onnxruntime/LICENSE')],locate_file=lambda p:root/'installed'/p)
            manifest=collect_license(dist,root/'release');validate_manifest([manifest])
            self.assertEqual('Original notice',(root/'release'/manifest['licenses'][0]).read_text())

    def test_official_versioned_fallback_and_missing_notices_fail_closed(self):
        with TemporaryDirectory(dir=Path(__file__).parent/'_cache') as temp:
            dist=SimpleNamespace(metadata={'Name':'flatbuffers'},version='25.12.19',files=[])
            result=collect_license(dist,Path(temp),fetch=lambda url:b'Original license fixture. '*10)
            self.assertIn('/v25.12.19/',result['upstream_sources'][0]['url'])
            with self.assertRaises(RuntimeError):collect_license(dist,Path(temp),fetch=lambda url:b'bad')
            with self.assertRaises(RuntimeError):validate_manifest([{'name':'empty','licenses':[]}])

    def test_capture_metadata_patch_notice_is_retained_in_release(self):
        with TemporaryDirectory(dir=Path(__file__).parent/'_cache') as temp:
            root=Path(temp);notice=Path('windows_capture-fixture.dist-info/CWA-PATCH.txt')
            source=root/'installed'/notice
            source.parent.mkdir(parents=True);source.write_text('Local dependency metadata patch',encoding='utf8')
            dist=SimpleNamespace(metadata={'Name':'windows-capture'},version='fixture',files=[notice],locate_file=lambda p:root/'installed'/p)
            manifest=collect_license(dist,root/'release')
            self.assertEqual('Local dependency metadata patch',(root/'release'/manifest['licenses'][0]).read_text())

    def test_license_directory_python_helpers_are_not_collected_as_notices(self):
        with TemporaryDirectory(dir=Path(__file__).parent/'_cache') as temp:
            root=Path(temp)
            files=[Path('packaging/LICENSE'),Path('packaging/licenses/__init__.py'),Path('packaging/licenses/__pycache__/helper.pyc')]
            for file in files:
                source=root/'installed'/file;source.parent.mkdir(parents=True,exist_ok=True);source.write_bytes(b'fixture')
            dist=SimpleNamespace(metadata={'Name':'packaging'},version='fixture',files=files,locate_file=lambda p:root/'installed'/p)
            manifest=collect_license(dist,root/'release')
            self.assertEqual(['licenses/packaging/packaging/LICENSE'],manifest['licenses'])


class CaptureWheelTests(unittest.TestCase):
    def test_patch_changes_metadata_only_and_retains_original_binary_and_license(self):
        import zipfile
        from tools.prepare_capture_wheel import patch_wheel,LOCAL
        with TemporaryDirectory(dir=Path(__file__).parent/'_cache') as temp:
            root=Path(temp);source=root/'upstream.whl';target=root/'patched.whl'
            with zipfile.ZipFile(source,'w') as z:
                z.writestr('windows_capture-2.0.1.dist-info/METADATA','Name: windows-capture\nVersion: 2.0.1\nRequires-Dist: opencv-python\n')
                z.writestr('windows_capture-2.0.1.dist-info/LICENSE','Original MIT notice')
                z.writestr('windows_capture/native.pyd',b'original binary bytes')
            patch_wheel(source,target)
            with zipfile.ZipFile(target) as z:
                metadata=z.read(f'windows_capture-{LOCAL}.dist-info/METADATA').decode()
                self.assertIn('Requires-Dist: opencv-python-headless',metadata)
                self.assertEqual(b'original binary bytes',z.read('windows_capture/native.pyd'))
                self.assertEqual(b'Original MIT notice',z.read(f'windows_capture-{LOCAL}.dist-info/LICENSE'))
                self.assertIn(b'native.pyd,sha256=',z.read(f'windows_capture-{LOCAL}.dist-info/RECORD'))
