"""Archive staging must reject ambiguous Windows namespaces before any writes."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('capsule_namespace_builder', Path(__file__).resolve().parents[1] / 'scripts/prepare_lab_capsule.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

class ArchiveNamespaceTests(unittest.TestCase):
    def rejected(self, names):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            archive, target = root / 'fixture.zip', root / 'target'
            with zipfile.ZipFile(archive, 'w') as z:
                for name in names:
                    z.writestr(name, b'' if name.endswith('/') else b'inert')
            with self.assertRaisesRegex(ValueError, 'ARCHIVE_(ALIAS|NAMESPACE_CONFLICT)'):
                builder.extract(archive, target, 'tools/')
            self.assertFalse(target.exists(), 'Rejected archive must not create the output tree')

    def test_implicit_parent_case_alias_rejected_before_creation(self):
        self.rejected(['tools/Lib/a.py', 'tools/lib/b.py'])

    def test_file_parent_conflict_rejected_before_creation(self):
        self.rejected(['tools/Lib', 'tools/Lib/a.py'])

    def test_reverse_file_parent_conflict_rejected_before_creation(self):
        self.rejected(['tools/Lib/a.py', 'tools/Lib'])

    def test_explicit_directory_and_implicit_parent_are_compatible(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            archive, target = root / 'fixture.zip', root / 'target'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('tools/Lib/a.py', b'inert')
                z.writestr('tools/Lib/', b'')
                z.writestr('tools/Lib/b.py', b'other')
            builder.extract(archive, target, 'tools/')
            self.assertEqual((target / 'Lib/a.py').read_bytes(), b'inert')
            self.assertEqual((target / 'Lib/b.py').read_bytes(), b'other')

if __name__ == '__main__':
    unittest.main()
