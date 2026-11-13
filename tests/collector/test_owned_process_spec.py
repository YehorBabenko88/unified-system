"""Neutral ABI tests; native allocation and all WinAPI boundaries are inert."""
import ctypes
from dataclasses import FrozenInstanceError
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch
from unified_system import service_postgres as pg, runtime_process


class Function:
    def __call__(self, *args):
        return 3


def inert_dll(name, **kwargs):
    if name != 'kernel32':
        raise AssertionError('NO NATIVE DLL')
    return type('InertDriveTypeOnly', (), {'GetDriveTypeW': Function()})()


class OwnedProcessSpecTests(unittest.TestCase):
    def setUp(self):
        native = patch.object(ctypes, 'WinDLL', side_effect=inert_dll, create=True)
        native.start()
        self.addCleanup(native.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.data = self.root/'data'
        self.code = self.root/'code'
        self.data.mkdir()
        self.code.mkdir()
        self.raw = b'class WindowsJob:\n def terminate_and_wait(self,timeout=5):return True\n'
        self.helper = self.code/'sources/grid/grid/ml_windows_job.py'
        self.helper.parent.mkdir(parents=True)
        self.helper.write_bytes(self.raw)
        self.spec = lambda: pg.OwnedProcessSpec(str(self.data), str(self.code), hashlib.sha256(self.raw).hexdigest())

    def test_frozen_exact_layout_and_existing_job_source_loader(self):
        spec = self.spec()
        with self.assertRaises(FrozenInstanceError):
            spec.data_root = 'other'
        self.assertTrue(callable(pg._job_class(spec).terminate_and_wait))
        self.helper.write_bytes(self.raw+b'# changed')
        with self.assertRaises(pg.PostgresBlocked):
            pg._job_class(spec)

    def test_existing_non_dict_mapping_job_source_contract_remains_accepted(self):
        values = {'service_plan': {'code': str(self.code)}, 'job_sha256': hashlib.sha256(self.raw).hexdigest()}
        reads = []
        class LegacyMapping:
            def __getitem__(self, key):
                reads.append(key)
                return values[key]
        self.assertTrue(callable(pg._job_class(LegacyMapping()).terminate_and_wait))
        self.assertEqual(reads, ['service_plan', 'job_sha256'])

    def test_relative_overlapping_missing_and_invalid_hash_layouts_reject(self):
        for data, code, pin in [('relative', str(self.code), 'a'*64),
                                (str(self.code), str(self.code), 'a'*64),
                                (str(self.code/'state'), str(self.code), 'a'*64),
                                (str(self.root/'missing'), str(self.code), 'a'*64),
                                (str(self.data), str(self.code), 'A'*64)]:
            with self.subTest(data=data, code=code), self.assertRaises(ValueError):
                pg.OwnedProcessSpec(data, code, pin)

    def test_pg_only_launch_modes_and_spec_subclasses_reject_before_allocation(self):
        spec = self.spec()
        class Ambiguous(pg.OwnedProcessSpec):
            pass
        with self.assertRaises(pg.PostgresBlocked):
            Ambiguous(str(self.data), str(self.code), 'a'*64)
        for candidate, restricted, launch in [(spec, True, None), (spec, False, object())]:
            with patch('subprocess.Popen') as spawn, patch('tempfile.TemporaryFile') as temp:
                with self.assertRaises(pg.PostgresBlocked):
                    pg.OwnedJobProcess(candidate, ['inert.exe'], {}, capture=True, restricted=restricted, launch=launch)
                spawn.assert_not_called()
                temp.assert_not_called()

    def test_changed_layout_rejects_at_consumption_before_any_allocation(self):
        spec = self.spec()
        self.data.rmdir()
        with patch('subprocess.Popen') as spawn, patch('tempfile.TemporaryFile') as temp:
            with self.assertRaises(ValueError):
                pg.OwnedJobProcess(spec, ['inert.exe'], {}, capture=True)
            spawn.assert_not_called()
            temp.assert_not_called()

    def test_existing_constructor_assigns_before_resume_and_synchronously_closes(self):
        spec = self.spec()
        exe = str(self.code/'inert.exe')
        identity = ['creation', exe]
        calls = []
        proc = Mock(pid=123, stdin=None)
        proc.poll.return_value = None
        job = Mock()
        job.terminate_and_wait.return_value = True
        def spawn(*args, **kwargs):
            calls.append('spawn')
            self.assertEqual(kwargs['cwd'], str(self.data))
            self.assertEqual(kwargs['creationflags'], 0x00000004|subprocess.CREATE_NO_WINDOW)
            self.assertEqual(pg._CREATE_SUSPENDED, 0x00000004)
            self.assertFalse(kwargs['shell'])
            return proc
        def assign(pid, **kwargs):
            calls.append('assign')
            self.assertEqual(kwargs, {'resume_primary_thread': False})
            return job
        with patch('subprocess.Popen', side_effect=spawn), patch.object(runtime_process, '_identity', return_value=identity), patch.object(pg, '_job_class', return_value=assign), patch.object(pg, '_resume_owned_primary', side_effect=lambda *a: calls.append('resume')):
            owner = pg.OwnedJobProcess(spec, [exe], {'EXPLICIT': 'inert'})
            self.assertEqual(calls, ['spawn', 'assign', 'resume'])
            owner.close()
        job.terminate_and_wait.assert_called_once_with(timeout=5)
        self.assertTrue(owner.confirmed_quiescent)

    def test_resume_fault_uses_existing_job_quiescence_and_poison_contract(self):
        spec = self.spec()
        exe = str(self.code/'inert.exe')
        proc = Mock(pid=123, stdin=None)
        job = Mock()
        job.terminate_and_wait.return_value = False
        with patch('subprocess.Popen', return_value=proc), patch.object(runtime_process, '_identity', return_value=['creation', exe]), patch.object(pg, '_job_class', return_value=lambda *a, **k: job), patch.object(pg, '_resume_owned_primary', side_effect=ValueError('inert failure')):
            with self.assertRaises(pg.PostgresBlocked) as error:
                pg.OwnedJobProcess(spec, [exe], {})
        self.assertEqual(error.exception.code, 'POSTGRES_POISONED')
        job.terminate_and_wait.assert_called_once_with(timeout=5)
        job.close.assert_not_called()


if __name__ == '__main__':
    unittest.main()
