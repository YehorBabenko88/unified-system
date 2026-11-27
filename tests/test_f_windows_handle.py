"""ROUND26 F native Windows handle tests: genuine target gates, not OS-skip proof.

Synthetic disposable data only. Test results on non-Windows are SKIP/NOT_RUN
for Win32 mechanisms. All positive checks are forensic; never Root/Writer GO.
"""
import os
import sys
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

    def test_import_shadow_forgery_cannot_replace_exact_sibling_backend(self):
        from unittest.mock import patch
        from f_wheel_qualification import _win_backend
        with tempfile.TemporaryDirectory(prefix="f-shadow-refusal-") as hostile:
            Path(hostile, "f_windows_handle.py").write_text(
                "raise AssertionError('AMBIENT_SHADOW_EXECUTED')\n")
            _win_backend.cache_clear()
            try:
                with patch.object(sys, "path", [hostile] + list(sys.path)):
                    module = _win_backend()
                    self.assertTrue(hasattr(module, "WindowsInstalledRoot"))
                    self.assertTrue(hasattr(module, "wheel_snapshot"))
            finally:
                _win_backend.cache_clear()

    def test_canonical_drive_path_has_bounded_parts(self):
        drive, parts = _segments(r"C:\isolated\wheel.whl")
        self.assertEqual(drive, "C:\\")
        self.assertEqual(parts, ["isolated", "wheel.whl"])


    def test_final_handle_path_exact_drive_anchor_synthetic(self):
        """Exercise original final-path match logic without claiming a Win32 run."""
        from f_windows_handle import _final_path_matches

        class RecordedKernel32:
            def __init__(self, final_path):
                self.final_path = final_path

            def GetFinalPathNameByHandleW(self, handle, buffer, capacity, flags):
                if len(self.final_path) >= capacity:
                    raise AssertionError("test buffer unexpectedly undersized")
                buffer.value = self.final_path
                return len(self.final_path)

        expected = r"C:\isolated\wheel.whl"
        _final_path_matches(
            RecordedKernel32(r"\\?\C:\isolated\wheel.whl"), None, expected
        )
        for alien in (
            r"\\?\D:\isolated\wheel.whl",
            r"\\?\C:\isolated\other.whl",
            r"\\?\UNC\server\isolated\wheel.whl",
            r"C:\isolated\wheel.whl",
        ):
            with self.subTest(alien=alien):
                with self.assertRaises(ValueError):
                    _final_path_matches(RecordedKernel32(alien), None, expected)


    def test_root_ancestor_component_substitution_denied(self):
        """Original Win32 traversal must compare retained and reopened ancestor IDs."""
        from unittest.mock import patch
        import f_windows_handle

        class FakeKernel:
            def __init__(self):
                self.closed = []
            def CloseHandle(self, h):
                self.closed.append(h)
                return True

        root = WindowsInstalledRoot(r"C:\disposable\install")
        kernel = FakeKernel()
        baseline = (7, bytes.fromhex("11" * 16), 0, 40)
        changed = (7, bytes.fromhex("22" * 16), 0, 40)
        retained = {}
        probes = []

        def open_directory(dll, path, *, directory):
            self.assertTrue(directory)
            probes.append(path)
            count = sum(item == path for item in probes)
            # C:\disposable is a retained ancestor: second open is a
            # different kernel FileId even though the pathname is unchanged.
            ident = changed if path == r"C:\disposable" and count == 2 else baseline
            return object(), ident

        def retain(path):
            if path not in retained:
                retained[path] = open_directory(kernel, path, directory=True)
            return retained[path]

        root._retain_dir = retain
        with patch("f_windows_handle._api", return_value=kernel), \
                patch("f_windows_handle._open", side_effect=open_directory):
            with self.assertRaisesRegex(ValueError, "root ancestor path substituted"):
                root.__enter__()
        self.assertIn(r"C:\disposable", probes)
        self.assertIsNone(root.dll)
        self.assertEqual(root._dirs, {})

    def test_install_identity_observation_never_grants_deletion(self):
        """The F receipt remains an observation, regardless of 128-bit IDs."""
        from unittest.mock import patch
        state = {"id": bytes.fromhex("21" * 16)}
        root = WindowsInstalledRoot(r"C:\disposable")
        root.dll = type("FakeKernel", (), {"CloseHandle": lambda self, h: True})()
        parent = (9, bytes.fromhex("31" * 16), 0, 10)
        root._parent = lambda parts: r"C:\disposable"
        root._retain_dir = lambda path: ("parent", parent)
        with patch("f_windows_handle._open",
                   side_effect=lambda dll, path, *, directory:
                   ("file", (9, state["id"], 12, 20))), \
                patch("f_windows_handle._info",
                      side_effect=lambda dll, handle, *, directory:
                      parent if directory else (9, state["id"], 12, 20)):
            proof = root.readonly_identity_receipt(("module.py",))
        self.assertIs(proof["installation_ownership_attested"], False)
        self.assertIs(proof["physical_delete_authorized"], False)

    def test_readonly_file_id_receipt_synthetic_denies_substituted_identity(self):
        """Run the original receipt logic, not any claimed native Win32 API."""
        from unittest.mock import patch
        class FakeKernel:
            def __init__(self):
                self.closed = []
            def CloseHandle(self, handle):
                self.closed.append(handle)
                return True
        kernel = FakeKernel()
        root = WindowsInstalledRoot(r"C:\disposable")
        root.dll = kernel
        directory_info = (7, bytes.fromhex("11" * 16), 0, 44)
        state = {"file_id": bytes.fromhex("22" * 16)}
        root._parent = lambda parts: r"C:\disposable"
        root._retain_dir = lambda path: ("dir-handle", directory_info)
        def file_info():
            return (7, state["file_id"], 10, 55)
        def fake_open(dll, path, *, directory):
            self.assertFalse(directory)
            self.assertEqual(path, r"C:\disposable\module.py")
            return "file-handle", file_info()
        def fake_info(dll, handle, *, directory):
            return directory_info if directory else file_info()
        with patch("f_windows_handle._open", side_effect=fake_open), \
                patch("f_windows_handle._info", side_effect=fake_info):
            receipt = root.readonly_identity_receipt(("module.py",))
            self.assertEqual(receipt["schema"], "f-win32-file-identity-observation.v1")
            self.assertEqual(receipt["file_id128"], "22" * 16)
            self.assertEqual(receipt["parent_file_id128"], "11" * 16)
            self.assertEqual(receipt["root_file_id128"], "11" * 16)
            self.assertFalse(receipt["installation_ownership_attested"])
            self.assertFalse(receipt["physical_delete_authorized"])
            self.assertEqual(root.verify_readonly_identity_receipt(("module.py",), receipt), receipt)
            state["file_id"] = bytes.fromhex("33" * 16)
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                root.verify_readonly_identity_receipt(("module.py",), receipt)
        self.assertEqual(kernel.closed, ["file-handle", "file-handle", "file-handle"])

    def test_retained_ancestor_does_not_grant_deletion(self):
        """F's original retained Win32 handle is read-only forensic evidence."""
        import inspect
        import f_windows_handle
        source = inspect.getsource(f_windows_handle.WindowsInstalledRoot)
        self.assertIn("self._retain_dir(drive)", source)
        self.assertIn("self._retain_dir(current)", source)
        self.assertIn('"physical_delete_authorized": False', source)
        self.assertIn('"installation_ownership_attested": False', source)
        self.assertNotIn("SetFileInformationByHandle", source)

    def test_install_receipt_requires_uninterrupted_ancestor_identity(self):
        """Document the owner's fail-closed gate, not a simulated OS race."""
        import ast
        import hashlib
        from pathlib import Path
        owner_file = os.environ.get("F_I_V2_OWNER_SOURCE")
        p = (Path(owner_file) if owner_file else
             Path(__file__).resolve().parents[1] / "unified_system" / "installation_service.py")
        if not p.is_file():
            self.skipTest("I owner V2 source not supplied")
        raw = p.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + bytes([0]) + raw).hexdigest()
        expected = "9ddaebbb8c0d24e19e595654f316e8646d0d675e"
        if not owner_file and blob != expected:
            self.skipTest("F checkout contains pre-I-V2 installer; owner source not supplied")
        self.assertEqual(blob, expected, "I R35 HEAD source drift; re-pin before qualification")
        source = raw.decode("utf-8")
        tree = ast.parse(source)
        names = {node.name:node for node in tree.body if isinstance(node, ast.FunctionDef)}
        self.assertIn("_capture_native_roster", names)
        self.assertIn("_native_file_identity", names)
        capture = ast.get_source_segment(source, names["_capture_native_roster"])
        helper = ast.get_source_segment(source, names["_native_file_identity"])
        self.assertIn("first==second", capture)
        self.assertIn("CloseHandle(h)", helper)
        # Two sequential observations cannot prove retained ancestor handles.
        self.assertNotIn("retained_ancestor_handles", capture)

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

    def test_directory_member_path_substitution_is_denied_by_fileid(self):
        # Verify the target security check is reached, without trying to
        # replace a live protected Windows handle on the runner.
        from unittest.mock import patch
        import f_windows_handle
        with WindowsInstalledRoot(self.install) as root:
            original_open = f_windows_handle._open
            count = {"n": 0}

            def forged_reopen(dll, path, *, directory):
                handle, ident = original_open(dll, path, directory=directory)
                if path == str(self.file) and not directory:
                    count["n"] += 1
                    if count["n"] == 2:
                        ident = (ident[0], b"Z" * 16, ident[2], ident[3])
                return handle, ident

            with patch.object(f_windows_handle, "_open", side_effect=forged_reopen):
                with self.assertRaisesRegex(ValueError, "path substituted"):
                    root.read(("module.py",))
            self.assertEqual(count["n"], 2)

    def test_nested_directory_path_substitution_is_denied_by_fileid(self):
        from unittest.mock import patch
        import f_windows_handle
        folder = self.install / "nested"
        folder.mkdir()
        (folder / "file.py").write_bytes(b"nested=True\n")
        with WindowsInstalledRoot(self.install) as root:
            original_open = f_windows_handle._open
            count = {"n": 0}

            def forged_reopen(dll, path, *, directory):
                handle, ident = original_open(dll, path, directory=directory)
                if path == str(folder) and directory:
                    count["n"] += 1
                    if count["n"] == 2:
                        ident = (ident[0], b"Q" * 16, ident[2], ident[3])
                return handle, ident

            with patch.object(f_windows_handle, "_open", side_effect=forged_reopen):
                with self.assertRaisesRegex(ValueError, "parent directory path substituted"):
                    root.read(("nested", "file.py"))
            self.assertEqual(count["n"], 2)

    def test_real_win32_read_and_closure_retains_original_id(self):
        with WindowsInstalledRoot(self.install) as root:
            self.assertEqual(root.read(("module.py",)), b"secure = False\n")
            self.assertEqual(root.closure(), {"module.py"})
        # No call to issue any security or operation permit.

    def test_wheel_original_handle_reads_actual_bytes(self):
        wheel = self.base / "candidate.whl"
        wheel.write_bytes(b"original-frozen-source")
        self.assertEqual(wheel_snapshot(wheel), b"original-frozen-source")

    def test_real_win32_readonly_file_id_receipt_denies_same_bytes_replacement(self):
        """Original OS 128-bit FileId readback, still NO install-time authority."""
        with WindowsInstalledRoot(str(self.install)) as root:
            proof = root.readonly_identity_receipt(("module.py",))
            self.assertEqual(len(proof["file_id128"]), 32)
            self.assertEqual(len(proof["parent_file_id128"]), 32)
            self.assertEqual(len(proof["root_file_id128"]), 32)
            self.assertFalse(proof["installation_ownership_attested"])
            self.assertFalse(proof["physical_delete_authorized"])
            self.assertEqual(
                root.verify_readonly_identity_receipt(("module.py",), proof),
                proof)
        previous = self.install / "detached-original.py"
        self.file.rename(previous)
        original = previous.read_bytes()
        self.file.write_bytes(original)
        with WindowsInstalledRoot(str(self.install)) as root:
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                root.verify_readonly_identity_receipt(("module.py",), proof)
        self.assertEqual(previous.read_bytes(), original)
        self.assertEqual(self.file.read_bytes(), original)

    def test_retained_ancestor_directory_blocks_rename(self):
        """Native kernel deny: an already-open retained ancestor cannot be swapped."""
        nested = self.install / "nested"
        nested.mkdir()
        (nested / "module.py").write_bytes(b"module = 1\\n")
        with WindowsInstalledRoot(str(self.install)) as root:
            self.assertEqual(root.read(("nested", "module.py")), b"module = 1\\n")
            with self.assertRaises(OSError):
                nested.rename(self.install / "substituted")
        self.assertTrue(nested.is_dir())

    def test_same_bytes_ancestor_replacement_denies_observed_receipt(self):
        """Original FileId parent pin must reject an equal-byte new namespace."""
        original = self.install / "nested"
        original.mkdir()
        (original / "module.py").write_bytes(b"module = 1\\n")
        with WindowsInstalledRoot(str(self.install)) as root:
            proof = root.readonly_identity_receipt(("nested", "module.py"))
        detached = self.install / "detached-nested"
        original.rename(detached)
        original.mkdir()
        (original / "module.py").write_bytes(b"module = 1\\n")
        with WindowsInstalledRoot(str(self.install)) as root:
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                root.verify_readonly_identity_receipt(("nested", "module.py"), proof)
        self.assertEqual((detached / "module.py").read_bytes(), b"module = 1\\n")

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
