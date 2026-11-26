"""Synthetic offline negative tests only; never native installed Grid acceptance."""
import base64
import csv
import hashlib
import io
import pathlib
import tempfile
import unittest
import zipfile
from f_wheel_qualification import qualify_wheel

DIST = "market_data-0.2.0.dev0.dist-info"
MOD = "market_data/__init__.py"
META = f"{DIST}/METADATA"
WHEEL = f"{DIST}/WHEEL"
ENTRY = f"{DIST}/entry_points.txt"
RECORD = f"{DIST}/RECORD"
SRC = b"ident = 'synthetic_fixture'\n"

def digest(data):
    return hashlib.sha256(data).hexdigest()

def rec_hash(data):
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")

class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = pathlib.Path(self.tmp.name)
        self.install = self.base / "install"
        self.install.mkdir()
        self.wheel = self.base / "market_data-0.2.0.dev0-py3-none-any.whl"
        self.files = {
            MOD: SRC,
            META: b"Metadata-Version: 2.1\nName: market-data\nVersion: 0.2.0.dev0\n",
            WHEEL: b"Wheel-Version: 1.0\nGenerator: F synthetic\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
            ENTRY: b"[console_scripts]\nmarket-data = market_data.cli:main\n",
        }
        self.make_wheel()

    def make_wheel(self, *, record_override=None, extra_members=()):
        rows = io.StringIO(newline="")
        writer = csv.writer(rows)
        for name, data in self.files.items():
            if name != RECORD:
                writer.writerow((name, rec_hash(data), len(data)))
        writer.writerow((RECORD, "", ""))
        self.files[RECORD] = rows.getvalue().encode() if record_override is None else record_override
        for path in sorted(self.install.rglob("*"), reverse=True):
            if path.is_file() or path.is_symlink(): path.unlink()
            elif path.is_dir(): path.rmdir()
        with zipfile.ZipFile(self.wheel, "w") as z:
            for name, data in self.files.items():
                z.writestr(zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0)), data)
            for name, data in extra_members:
                z.writestr(zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0)), data)
        for name, data in self.files.items():
            target = self.install / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    def scan(self, **overrides):
        args = dict(expected_sha256=digest(self.wheel.read_bytes()), source_files={MOD: digest(SRC)},
                    expected_distribution="market-data", expected_version="0.2.0.dev0",
                    expected_entrypoints={"market-data": "market_data.cli:main"})
        args.update(overrides)
        return qualify_wheel(self.wheel, self.install, **args)

    def deny(self, **overrides):
        with self.assertRaises(ValueError): self.scan(**overrides)

    def test_fixture_verified_bytes_but_never_grants_authority(self):
        result = self.scan()
        self.assertTrue(result["installed_record_verified"])
        self.assertTrue(result["entrypoint_metadata_match"])
        for k in ("release_authenticated", "root_admitted", "writer_admitted", "import_origin_verified", "runtime_entrypoint_verified"):
            self.assertFalse(result[k])

    def test_pinned_wheel_hash_mismatch(self): self.deny(expected_sha256="0"*64)
    def test_missing_source_runtime_module(self): self.deny(source_files={"market_data/absent.py": digest(SRC)})
    def test_changed_source_hash(self): self.deny(source_files={MOD: "a"*64})
    def test_source_hash_malformed(self): self.deny(source_files={MOD: "g"*64})
    def test_missing_source_pin(self): self.deny(source_files={})
    def test_installed_module_tamper(self):
        (self.install / MOD).write_bytes(b"tampered")
        self.deny()
    def test_missing_installed_record(self):
        (self.install / RECORD).unlink()
        self.deny()
    def test_installed_record_tamper(self):
        (self.install / RECORD).write_bytes(b"tampered")
        self.deny()
    def test_installed_symlink(self):
        target = self.base / "outside"; target.write_bytes(SRC)
        (self.install / MOD).unlink()
        try: (self.install / MOD).symlink_to(target)
        except (OSError, NotImplementedError): self.skipTest("symlinks unavailable")
        self.deny()
    def test_record_hash_corrupt(self):
        text = self.files[RECORD].decode().replace("sha256=", "sha256=BAD", 1)
        self.make_wheel(record_override=text.encode())
        self.deny()
    def test_record_self_hash_forbidden(self):
        text = self.files[RECORD].decode().replace(f"{RECORD},,", f"{RECORD},sha256=x,0")
        self.make_wheel(record_override=text.encode())
        self.deny()
    def test_record_duplicate_row(self):
        text = self.files[RECORD].decode()
        text += text.splitlines(keepends=True)[0]
        self.make_wheel(record_override=text.encode())
        self.deny()
    def test_wheel_unrecorded_archive_member(self):
        self.make_wheel(extra_members=[("market_data/unlisted.py", b"x")])
        self.deny()
    def test_archive_duplicate_zip_name(self):
        self.make_wheel(extra_members=[(MOD, SRC)])
        self.deny()
    def test_archive_case_collision(self):
        self.make_wheel(extra_members=[("MARKET_DATA/__init__.py", SRC)])
        self.deny()
    def test_archive_path_traversal(self):
        self.make_wheel(extra_members=[("../../evil.py", SRC)])
        self.deny()
    def test_archive_windows_drive(self):
        self.make_wheel(extra_members=[("C:/evil.py", SRC)])
        self.deny()
    def test_archive_reserved_windows_name(self):
        self.make_wheel(extra_members=[("CON", SRC)])
        self.deny()
    def test_distribution_mismatch(self):
        self.deny(expected_distribution="other-data")
    def test_version_mismatch(self):
        self.deny(expected_version="9.0")
    def test_entrypoint_mismatch(self):
        self.deny(expected_entrypoints={"market-data": "other.module:main"})
    def test_metadata_replaced(self):
        self.files[META] = b"Metadata-Version: 2.1\nName: adversary\nVersion: 0.2.0.dev0\n"
        self.make_wheel()
        self.deny()
    def test_actual_pip_target_install_succeeds_diagnostic_only(self):
        import subprocess
        import sys
        target = self.base / "pip_target"
        target.mkdir()
        result = subprocess.run([sys.executable, "-m", "pip", "install",
                                 "--disable-pip-version-check", "--no-index",
                                 "--no-deps", "--target", str(target), str(self.wheel)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.install = target
        report = self.scan()
        self.assertTrue(report["installed_record_verified"])
        self.assertGreaterEqual(report["unhashed_install_auxiliary_count"], 1)
        self.assertFalse(report["all_installed_bytes_authenticated"])
        self.assertFalse(report["release_authenticated"])
        self.assertFalse(report["writer_admitted"])

    def test_actual_pip_target_script_tamper_denied(self):
        import subprocess
        import sys
        target = self.base / "pip_target"
        target.mkdir()
        result = subprocess.run([sys.executable, "-m", "pip", "install",
                                 "--disable-pip-version-check", "--no-index",
                                 "--no-deps", "--target", str(target), str(self.wheel)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.install = target
        (self.install / "bin" / "market-data").write_bytes(b"tampered")
        self.deny()

    def test_wheel_reproducible_synthetic_fixture(self):
        first = self.wheel.read_bytes()
        self.make_wheel()
        self.assertEqual(first, self.wheel.read_bytes())

if __name__ == "__main__": unittest.main()
