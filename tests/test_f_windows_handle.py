"""ROUND26 F native Windows handle tests: genuine target gates, not OS-skip proof.

Synthetic disposable data only. Test results on non-Windows are SKIP/NOT_RUN
for Win32 mechanisms. All positive checks are forensic; never Root/Writer GO.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from f_windows_handle import _segments, WindowsInstalledRoot, wheel_snapshot


class WindowsPathSyntaxTests(unittest.TestCase):
    def test_rejects_unsafe_windows_spelling_before_native_open(self):
        for path in (
            r"C:\safe\..\escape", r"C:\safe\CON", r"C:\safe\file:stream",
            r"C:\safe\trailing.", r"C:\safe\bad?name",
            r"\\server\share\package", r"\??\C:\safe", r"C:relative",
        ):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    _segments(path)

    def test_canonical_drive_path_has_bounded_parts(self):
        drive, parts = _segments(r"C:\isolated\wheel.whl")
        self.assertEqual(drive, "C:\\")
        self.assertEqual(parts, ["isolated", "wheel.whl"])


@unittest.skipUnless(os.name == "nt", "genuine Win32 kernel handles required")
class NativeWindowsRetainedHandleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="f-round26-windows-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.install = self.base / "install"
        self.install.mkdir()
        self.file = self.install / "module.py"
        self.file.write_bytes(b"secure = False\n")

    def test_real_win32_read_and_closure_retains_original_id(self):
        with WindowsInstalledRoot(self.install) as root:
            self.assertEqual(root.read(("module.py",)), b"secure = False\n")
            self.assertEqual(root.closure(), {"module.py"})
        # No call to issue any security or operation permit.

    def test_wheel_original_handle_reads_actual_bytes(self):
        wheel = self.base / "candidate.whl"
        wheel.write_bytes(b"original-frozen-source")
        self.assertEqual(wheel_snapshot(wheel), b"original-frozen-source")

    def test_hardlink_is_denied_at_win32_file_information_gate(self):
        alias = self.install / "alias.py"
        os.link(self.file, alias)
        with WindowsInstalledRoot(self.install) as root:
            with self.assertRaisesRegex(ValueError, "hardlink"):
                root.read(("module.py",))

    def test_untrusted_import_hook_rejected_inside_win32_closure(self):
        (self.install / "evil.pth").write_bytes(b"import os\n")
        with WindowsInstalledRoot(self.install) as root:
            with self.assertRaisesRegex(ValueError, "import hook"):
                root.closure()

    def test_real_reparse_symlink_file_never_read(self):
        outside = self.base / "outside"
        outside.write_bytes(b"foreign")
        self.file.unlink()
        try:
            self.file.symlink_to(outside)
        except (OSError, NotImplementedError) as exc:
            self.skipTest("native symlink creation unavailable: " + str(exc))
        with WindowsInstalledRoot(self.install) as root:
            with self.assertRaises(ValueError):
                root.read(("module.py",))

    def test_real_junction_never_traversed(self):
        outside = self.base / "outside-dir"
        outside.mkdir()
        (outside / "bad.py").write_bytes(b"untrusted\n")
        link = self.install / "mount"
        proc = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)],
                              capture_output=True, text=True, timeout=20)
        if proc.returncode != 0:
            self.skipTest("native junction creation unavailable: " + proc.stderr[-120:])
        with WindowsInstalledRoot(self.install) as root:
            with self.assertRaises(ValueError):
                root.closure()

    def test_mutation_rejected_while_original_file_handle_is_retained(self):
        with WindowsInstalledRoot(self.install) as root:
            self.assertEqual(root.read(("module.py",)), b"secure = False\n")
            with self.assertRaises(OSError):
                self.file.write_bytes(b"mutated after handle open")

    def test_installed_root_symlink_never_admitted(self):
        linked = self.base / "linked"
        try:
            linked.symlink_to(self.install, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest("native symlink creation unavailable: " + str(exc))
        with self.assertRaises(ValueError):
            with WindowsInstalledRoot(linked):
                pass


if __name__ == "__main__":
    unittest.main()
