"""Prospective inert cleanup controls. No DB, path, process or backup effects.

Root must admit exact source before import/execution; no discovery/main.
"""
from types import SimpleNamespace
import unittest
from unittest.mock import patch


def make_suite(admitted_phases):
    class IndependentCloseCases(unittest.TestCase):
        def exercise(self, primary, dst_failure, src_failure):
            state = dict(events=[], reserved=False, partial=None)
            seal = dict(sha256='a'*64, bytes=512, file_identity=(1, 2))
            class Context:
                def __enter__(self): return self
                def __exit__(self, *_): return False
            class Destination:
                parent = 'INERT_PARENT_NOT_FILESYSTEM'
                def open(self, mode):
                    if mode != 'xb': raise AssertionError('exclusive create expected')
                    state['reserved'] = True
                    return Context()
                def as_uri(self): return 'file:///INERT_DESTINATION_NOT_OPENED'
            class Cursor:
                def __init__(self, value): self.value = value
                def fetchone(self): return (self.value,)
            class Connection:
                def __init__(self, role): self.role = role
                def execute(self, sql):
                    if sql == 'PRAGMA page_count': return Cursor(1)
                    if sql == 'PRAGMA page_size': return Cursor(512)
                def backup(self, destination, *, pages, progress, sleep):
                    if self.role != 'src' or destination.role != 'dst':
                        raise AssertionError('distinct source/destination required')
                    state['events'].append('backup')
                    state['partial'] = b'INERT_PARTIAL_BYTES_NOT_A_FILE'
                    if primary is not None: raise primary
                    progress(admitted_phases.sqlite3.SQLITE_DONE, 0, 1)
                def close(self):
                    state['events'].append('close_'+self.role)
                    failure = dst_failure if self.role == 'dst' else src_failure
                    if failure is not None: raise failure
            connections = iter((Connection('src'), Connection('dst')))
            source = SimpleNamespace(as_uri=lambda: 'file:///INERT_SOURCE_NOT_OPENED')
            with patch.object(admitted_phases, '_snapshot_db_seal', lambda *_: seal), \
                 patch.object(admitted_phases, '_parents', lambda *_: None), \
                 patch.object(admitted_phases, '_plain', lambda *_a, **_k: SimpleNamespace(st_dev=1, st_ino=2)), \
                 patch.object(admitted_phases.sqlite3, 'connect', lambda *_a, **_k: next(connections)), \
                 patch.object(admitted_phases.time, 'monotonic_ns', lambda: 1):
                try:
                    result = admitted_phases._snapshot_copy_db(source, Destination(), seal, 1, 2)
                    error = None
                except BaseException as caught:
                    error, result = caught, None
            self.assertEqual(state['events'], ['backup', 'close_dst', 'close_src'])
            self.assertTrue(state['reserved'])
            self.assertEqual(state['partial'], b'INERT_PARTIAL_BYTES_NOT_A_FILE')
            return result, error, seal

        def test_primary_and_destination_close_failures_are_both_retained(self):
            primary, close = ValueError('inert primary backup failure'), OSError('inert dst close failure')
            result, error, _ = self.exercise(primary, close, None)
            self.assertIsNone(result)
            self.assertIsInstance(error, BaseExceptionGroup)
            self.assertEqual(error.exceptions, (primary, close))

        def test_successful_backup_destination_close_failure_still_closes_source(self):
            close = OSError('inert dst close failure')
            result, error, _ = self.exercise(None, close, None)
            self.assertIsNone(result)
            self.assertIsInstance(error, BaseExceptionGroup)
            self.assertEqual(error.exceptions, (close,))

        def test_source_close_failure_is_explicit_uncertainty(self):
            close = OSError('inert src close failure')
            result, error, _ = self.exercise(None, None, close)
            self.assertIsNone(result)
            self.assertIsInstance(error, BaseExceptionGroup)
            self.assertEqual(error.exceptions, (close,))

        def test_clean_inert_backup_returns_only_after_both_close_attempts(self):
            result, error, seal = self.exercise(None, None, None)
            self.assertIsNone(error)
            self.assertEqual(result, seal)

    return unittest.defaultTestLoader.loadTestsFromTestCase(IndependentCloseCases)
