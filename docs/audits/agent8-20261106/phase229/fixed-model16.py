"""UNEXECUTED Windows mode compatibility proposal: actual functions/inert readers.

Separate Root allocation required. Does not call controller.main/capture, Git,
the committed test, PowerShell, native APIs, project fixtures or any subprocess.
"""
import builtins
from contextlib import ExitStack
import copy
import hashlib
import io
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

CONTROLLER = Path('C:/Users/LS-5/.codex/native-output-cap-prerequisite-756a670-successor-20261111/controller.py')
CONTROLLER_SHA = 'ee5612610e0f77a4244c8ea2c5bcb8f6a32004a23ad711ba0d29d440729141ae'
MODEL_PATH = Path('C:/INERT-CONTROLLER-METADATA/entry.json')
RAW = b'{"unit":true}' + b' ' * (475327 - len(b'{"unit":true}'))
COMMON_FIELDS = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_nlink')
SAME_API_FIELDS = ('st_mode',) + COMMON_FIELDS
LSTAT_CTIME = 1794349922903157200
FSTAT_CTIME = 1794349922904162400
ERRORS = {
    'pinned_json': {'open': 'PREPARATION_INPUT_OPEN_CHANGED', 'read': 'PREPARATION_INPUT_READ_CHANGED',
                    'path': 'PREPARATION_INPUT_PATH_CHANGED', 'raw': 'PREPARATION_INPUT_CHANGED'},
    'hash_file': {'open': 'FILE_OPEN_CHANGED', 'read': 'FILE_READ_CHANGED',
                  'path': 'FILE_CHANGED', 'raw': 'RAW_FILE_MISMATCH'},
}


def deny(*args, **kwargs):
    raise AssertionError('MODEL_IO_OR_PROCESS_FORBIDDEN')


def observations(different_ctime=False, birth=False):
    before = types.SimpleNamespace(st_mode=33206, st_dev=7417695763057267443,
                                  st_ino=844424935181080, st_size=len(RAW),
                                  st_mtime_ns=1794349922904162400,
                                  st_ctime_ns=LSTAT_CTIME, st_nlink=1)
    opened = copy.copy(before)
    if different_ctime:
        opened.st_ctime_ns = FSTAT_CTIME
    if birth:
        before.st_birthtime_ns = 1794000000000000000
        opened.st_birthtime_ns = before.st_birthtime_ns
    return [before, opened, copy.copy(opened), copy.copy(before)]


def windows_mode_observations():
    """Root-observed path/descriptor permission pair, same regular file kind."""
    stats = observations(different_ctime=True, birth=True)
    stats[0].st_mode = stats[3].st_mode = 33279  # 0o100777: path API
    stats[1].st_mode = stats[2].st_mode = 33206  # 0o100666: descriptor API
    return stats


def load_actual_controller():
    # Future model allocation reads/hash-binds ONCE, then compiles that SAME
    # trusted Python source buffer. This loader is not executed during prep.
    with CONTROLLER.open('rb') as stream:
        raw = stream.read(131073)
    if len(raw) > 131072 or hashlib.sha256(raw).hexdigest() != CONTROLLER_SHA:
        raise AssertionError('MODEL_CONTROLLER_SOURCE_CHANGED')
    module = types.ModuleType('controller_metadata_model_subject')
    module.__file__ = str(CONTROLLER)
    # All imported modules are stdlib and already explicitly part of model scope.
    # __name__ is not __main__; controller entrypoint is never invoked.
    exec(compile(raw, str(CONTROLLER), 'exec'), module.__dict__)
    return module


def make_suite():
    class ControllerMetadataModels(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.subject = load_actual_controller()

        def call_actual(self, api, stats, raw=RAW):
            subject = self.subject
            before, opened, after, current = stats
            descriptor = 700001  # inert integer only; never an OS descriptor

            class Reader(io.BytesIO):
                def fileno(self):
                    return descriptor

                def read(self, size=-1):
                    if type(size) is not int or not 0 <= size <= 65536:
                        raise AssertionError('MODEL_UNBOUNDED_READ')
                    return super().read(size)

            stream = Reader(raw)
            fstats = iter((opened, after))
            ordinary_stats = iter((before, current))

            def fake_ordinary(path, **kwargs):
                if path != MODEL_PATH:
                    deny()
                return next(ordinary_stats)

            def fake_open(path, *args, **kwargs):
                if path != MODEL_PATH:
                    deny()
                return stream

            def fake_os_open(path, flags):
                if path != MODEL_PATH:
                    deny()
                return descriptor

            def fake_fdopen(fd, *args, **kwargs):
                if fd != descriptor:
                    deny()
                return stream

            def fake_fstat(fd):
                if fd != descriptor:
                    deny()
                return next(fstats)

            def fake_lstat(path, *args, **kwargs):
                if path != MODEL_PATH:
                    deny()
                return current

            # Every actual-function invocation has the same tripwires. No case
            # relies on another case's patches or uses an unguarded positive call.
            with ExitStack() as guards:
                for name in ('Popen', 'run', 'check_output', 'check_call', 'call'):
                    guards.enter_context(patch.object(subprocess, name, side_effect=deny))
                for name in ('socket', 'create_connection', 'getaddrinfo', 'gethostbyname'):
                    guards.enter_context(patch.object(socket, name, side_effect=deny))
                for name in ('system', 'startfile', 'spawnl', 'spawnv', 'execv'):
                    if hasattr(os, name):
                        guards.enter_context(patch.object(os, name, side_effect=deny))
                guards.enter_context(patch.object(builtins, 'open', side_effect=deny))
                guards.enter_context(patch.object(io, 'open', side_effect=deny))
                for name in ('stat', 'read_bytes', 'read_text', 'write_bytes', 'write_text',
                             'mkdir', 'unlink', 'iterdir', 'glob', 'rglob'):
                    guards.enter_context(patch.object(Path, name, side_effect=deny))
                guards.enter_context(patch.object(Path, 'open', fake_open))
                guards.enter_context(patch.object(Path, 'lstat', fake_lstat))
                guards.enter_context(patch.object(subject.os, 'open', fake_os_open))
                guards.enter_context(patch.object(subject.os, 'fdopen', fake_fdopen))
                guards.enter_context(patch.object(subject.os, 'fstat', fake_fstat))
                guards.enter_context(patch.object(subject, 'ordinary', fake_ordinary))
                guards.enter_context(patch.object(subject, 'clock', return_value=0))
                guards.enter_context(patch.object(subject, 'BASE', MODEL_PATH.parent))
                if api == 'pinned_json':
                    return subject.pinned_json(MODEL_PATH.name, hashlib.sha256(RAW).hexdigest())
                entry = {'bytes': len(RAW), 'sha256': hashlib.sha256(RAW).hexdigest()}
                return subject.hash_file(MODEL_PATH, entry, single=True)

        def accepts(self, stats):
            for api in ERRORS:
                with self.subTest(api=api):
                    result = self.call_actual(api, copy.deepcopy(stats))
                    if api == 'pinned_json':
                        self.assertEqual(result, {'unit': True})
                    else:
                        self.assertEqual(result['sha256'], hashlib.sha256(RAW).hexdigest())
                        self.assertEqual(result['bytes'], len(RAW))

        def rejects(self, stats, stage, raw=RAW):
            for api in ERRORS:
                with self.subTest(api=api):
                    with self.assertRaises(AssertionError) as caught:
                        self.call_actual(api, copy.deepcopy(stats), raw)
                    # A tripwire/setup exception cannot masquerade as metadata RED.
                    self.assertEqual(caught.exception.args, (ERRORS[api][stage],))

        def test_valid_windows_cross_api_ctime_difference(self):
            self.accepts(observations(different_ctime=True))

        def test_common_fields_cross_api_mismatch_denied(self):
            # Cross-API mode+1 was a permission-only difference, not a kind
            # mismatch. Kind/permission semantics now have explicit cases below.
            for name in COMMON_FIELDS:
                with self.subTest(field=name):
                    stats = observations()
                    setattr(stats[1], name, getattr(stats[1], name) + 1)
                    self.rejects(stats, 'open')

        def test_fstat_before_after_ctime_mutation_denied(self):
            stats = observations()
            stats[2].st_ctime_ns += 1
            self.rejects(stats, 'read')

        def test_lstat_before_after_ctime_mutation_denied(self):
            stats = observations()
            stats[3].st_ctime_ns += 1
            self.rejects(stats, 'path')

        def test_common_fields_same_api_mutation_denied(self):
            for index, stage in ((2, 'read'), (3, 'path')):
                for name in SAME_API_FIELDS:
                    with self.subTest(api_stage=stage, field=name):
                        stats = observations()
                        setattr(stats[index], name, getattr(stats[index], name) + 1)
                        self.rejects(stats, stage)

        def test_equal_birthtime_is_accepted(self):
            self.accepts(observations(birth=True))

        def test_cross_api_birthtime_mismatch_denied(self):
            stats = observations(birth=True)
            stats[1].st_birthtime_ns += 1
            self.rejects(stats, 'open')

        def test_same_api_birthtime_mutation_denied(self):
            for index, stage in ((2, 'read'), (3, 'path')):
                with self.subTest(api_stage=stage):
                    stats = observations(birth=True)
                    stats[index].st_birthtime_ns += 1
                    self.rejects(stats, stage)

        def test_cross_api_missing_birthtime_does_not_alias_ctime(self):
            stats = observations(different_ctime=True, birth=True)
            del stats[1].st_birthtime_ns
            del stats[2].st_birthtime_ns
            self.accepts(stats)

        def test_same_api_birthtime_availability_drift_denied(self):
            for index, stage in ((2, 'read'), (3, 'path')):
                with self.subTest(api_stage=stage):
                    stats = observations(birth=True)
                    del stats[index].st_birthtime_ns
                    self.rejects(stats, stage)

        def test_raw_hash_tampering_still_denied(self):
            self.rejects(observations(), 'raw', raw=RAW[:-1] + b'\n')

        def test_windows_observed_permission_pair_is_accepted(self):
            self.accepts(windows_mode_observations())

        def test_windows_cross_api_permission_only_bit_is_accepted(self):
            # Explicit replacement for the old cross-API mode+1 rejection.
            # Full mode remains stable within each API's own before/after pair.
            stats = observations(birth=True)
            stats[1].st_mode += 1
            stats[2].st_mode = stats[1].st_mode
            self.accepts(stats)

        def test_cross_api_file_kind_mismatch_is_denied(self):
            for kind in (stat.S_IFDIR, stat.S_IFLNK, stat.S_IFCHR, stat.S_IFIFO):
                with self.subTest(kind=kind):
                    stats = windows_mode_observations()
                    stats[1].st_mode = kind | stat.S_IMODE(stats[1].st_mode)
                    self.rejects(stats, 'open')

        def test_same_api_full_permission_changes_are_denied(self):
            for index, stage in ((2, 'read'), (3, 'path')):
                with self.subTest(api_stage=stage):
                    stats = observations(birth=True)
                    stats[index].st_mode ^= stat.S_IXUSR
                    self.rejects(stats, stage)

        def test_same_api_file_kind_changes_are_denied(self):
            for index, stage in ((2, 'read'), (3, 'path')):
                with self.subTest(api_stage=stage):
                    stats = observations(birth=True)
                    stats[index].st_mode = stat.S_IFDIR | stat.S_IMODE(stats[index].st_mode)
                    self.rejects(stats, stage)

    ControllerMetadataModels.__module__ = 'controller_windows_mode_models'
    ControllerMetadataModels.__qualname__ = 'ControllerMetadataModels'
    return unittest.defaultTestLoader.loadTestsFromTestCase(ControllerMetadataModels)


if __name__ == '__main__':
    if sys.argv[1:] != ['--allocated-windows-mode-models'] or not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise SystemExit('EXPLICIT_MODEL_ALLOCATION_REQUIRED')
    outcome = unittest.TextTestRunner(verbosity=2).run(make_suite())
    raise SystemExit(0 if outcome.wasSuccessful() and outcome.testsRun == 16 and not outcome.skipped else 1)
