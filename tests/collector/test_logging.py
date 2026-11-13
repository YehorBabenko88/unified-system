"""Real NEW owned scratch only; no sockets, SQLite, processes or service APIs."""
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('collector_logging_under_test', ROOT/'unified_system/collector_logging.py')
Q = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = Q
SPEC.loader.exec_module(Q)
NOW = datetime(2026, 11, 12, 20, 0, 0, 123000, tzinfo=timezone.utc)


class CollectorLoggingTests(unittest.TestCase):
    def setUp(self):
        parent = os.environ.get('COLLECTOR_LOG_TEST_SCRATCH')
        if parent:
            self.base = Path(parent)/self._testMethodName
            self.base.mkdir(exist_ok=False)
        else:
            self.base = Path(tempfile.mkdtemp(prefix='collector-logging-'))
        self.state = self.base/'state'; self.state.mkdir()
        self.code = self.base/'code'; self.code.mkdir()
        (self.code/'sentinel.py').write_bytes(b'# immutable code sentinel\n')
        self.root = self.state/'logs'
        self.args = dict(state_root=self.state, code_root=self.code, context_id='1'*32,
                         limits=Q.LogLimits(file_bytes=1024, file_count=2), clock=lambda: NOW)

    def create(self): return Q.CollectorLog.create(self.root, **self.args)
    def reopen(self): return Q.CollectorLog.open(self.root, **self.args)
    def records(self):
        return [json.loads(line) for p in sorted(self.root.glob('events-*.jsonl')) for line in p.read_bytes().splitlines()]
    def snapshot(self): return {p.name: p.read_bytes() for p in self.root.iterdir()}

    def test_record_fields_UTC_digest_and_receipt(self):
        with self.create() as log:
            receipt = log.emit(event='CAPTURE', state='RUNNING', count=3, bytes_count=11, digest='a'*64)
        files = list(self.root.glob('events-*.jsonl')); self.assertEqual(len(files), 1)
        raw = files[0].read_bytes(); record = json.loads(raw)
        self.assertEqual(set(record), {'schema','sequence','at_utc','event','state','error_code','count','bytes','digest'})
        self.assertEqual(record['schema'], 'unified.collector.logging.v1')
        self.assertEqual(record['at_utc'], '2026-11-12T20:00:00.123Z')
        self.assertEqual((record['sequence'], record['count'], record['bytes']), (1,3,11))
        self.assertEqual(receipt.sequence, 1)
        self.assertEqual(receipt.record_sha256, hashlib.sha256(raw).hexdigest())
        self.assertLessEqual(len(raw), 2048)

    def test_clean_restart_recovers_next_sequence(self):
        with self.create() as log:
            log.emit(event='STARTUP', state='STARTING')
            log.emit(event='READY', state='RUNNING')
        with self.reopen() as log: self.assertEqual(log.emit(event='SHUTDOWN', state='STOPPED').sequence, 3)
        self.assertEqual([r['sequence'] for r in self.records()], [1,2,3])

    def test_rotation_bounded_and_restart_never_resets(self):
        with self.create() as log:
            for i in range(24): self.assertEqual(log.emit(event='CAPTURE', state='RUNNING', count=i).sequence, i+1)
        files = list(self.root.glob('events-*.jsonl'))
        self.assertLessEqual(len(files), 2)
        self.assertTrue(all(p.stat().st_size <= 1024 for p in files))
        self.assertGreater(self.records()[0]['sequence'], 1)
        with self.reopen() as log: self.assertEqual(log.emit(event='CHECKPOINT', state='RUNNING').sequence, 25)
        self.assertEqual((self.code/'sentinel.py').read_bytes(), b'# immutable code sentinel\n')

    def test_closed_vocabulary_rejects_secrets_without_stdout_fallback(self):
        secret = 'https://private.invalid/?token=TOPSECRET'
        captured = io.StringIO()
        with self.create() as log, redirect_stdout(captured), redirect_stderr(captured):
            for kwargs in [dict(event=secret,state='RUNNING'),dict(event='ERROR',state=secret),
                           dict(event='ERROR',state='BLOCKED',error_code=secret),
                           dict(event='CAPTURE',state='RUNNING',digest=secret)]:
                with self.assertRaises(Q.LogBlocked): log.emit(**kwargs)
            with self.assertRaises(TypeError): log.emit(event='ERROR', state='BLOCKED', message=secret)
            self.assertEqual(log.emit(event='ERROR',state='BLOCKED',error_code='DATABASE_FAILED').sequence, 1)
        self.assertEqual(captured.getvalue(), '')
        self.assertNotIn(secret.encode(), b''.join(self.snapshot().values()))

    def test_counts_have_exact_finite_integer_bounds(self):
        with self.create() as log:
            for value in (True, -1, 2**63, 1.5, float('nan'), float('inf')):
                with self.assertRaises(Q.LogBlocked): log.emit(event='CAPTURE',state='RUNNING',count=value)
                with self.assertRaises(Q.LogBlocked): log.emit(event='CAPTURE',state='RUNNING',bytes_count=value)
            self.assertEqual(log.emit(event='CAPTURE',state='RUNNING',count=2**63-1).sequence,1)

    def test_profile_narrowed_bounds(self):
        for kwargs in ({'file_bytes':1023},{'file_bytes':1048577},{'file_bytes':True},
                       {'file_count':1},{'file_count':5},{'record_bytes':2047},{'record_bytes':2049}):
            with self.subTest(kwargs=kwargs), self.assertRaises(Q.LogBlocked): Q.LogLimits(**kwargs)

    def test_extended_fixed_events_and_codes(self):
        with self.create() as log:
            for event in ('SOURCE','RETRY','RECOVERY','RESOURCE','QUALITY','ERROR'):
                log.emit(event=event,state='UNKNOWN',error_code='CHECKPOINT_UNKNOWN')
            for code in ('DATABASE_FAILED','QUALITY_GAP','RESOURCE_LIMIT'):
                log.emit(event='ERROR',state='BLOCKED',error_code=code)

    def test_second_writer_denied_existing_own_lock(self):
        with self.create() as first:
            before=self.snapshot()
            with self.assertRaises(Q.LogBlocked): self.reopen()
            self.assertEqual(self.snapshot(),before)
            self.assertEqual(first.emit(event='READY',state='RUNNING').sequence,1)

    def test_foreign_existing_context_not_adopted_or_modified(self):
        self.root.mkdir(); (self.root/'foreign.log').write_bytes(b'private supplied data')
        before=self.snapshot()
        for call in (self.create,self.reopen):
            with self.assertRaises(Q.LogBlocked): call()
            self.assertEqual(self.snapshot(),before)

    def test_code_root_and_outside_state_paths_denied(self):
        for root in (self.code/'logs',self.base/'logs'):
            with self.assertRaises(Q.LogBlocked): Q.CollectorLog.create(root, **self.args)
            self.assertFalse(root.exists())

    def test_marker_context_and_limits_are_not_mutable_reopen_options(self):
        with self.create(): pass
        before=self.snapshot()
        for kwargs in ({'context_id':'2'*32},{'limits':Q.LogLimits(file_bytes=2048,file_count=2)}):
            args={**self.args,**kwargs}
            with self.assertRaises(Q.LogBlocked): Q.CollectorLog.open(self.root, **args)
            self.assertEqual(self.snapshot(),before)

    def test_partial_line_reopen_blocks_without_repair(self):
        with self.create() as log: log.emit(event='STARTUP',state='STARTING')
        path=next(self.root.glob('events-*.jsonl'))
        with path.open('ab') as f: f.write(b'{"partial":')
        before=self.snapshot()
        with self.assertRaises(Q.LogBlocked): self.reopen()
        self.assertEqual(self.snapshot(),before)

    def test_deleted_latest_log_does_not_reset_sequence(self):
        with self.create() as log: log.emit(event='READY',state='RUNNING')
        next(self.root.glob('events-*.jsonl')).unlink()
        before=self.snapshot()
        with self.assertRaises(Q.LogBlocked): self.reopen()
        self.assertEqual(self.snapshot(),before)

    def test_foreign_extra_file_blocks_rotation_not_deleted(self):
        with self.create() as log:
            log.emit(event='READY',state='RUNNING')
            (self.root/'not-managed.log').write_bytes(b'keep me')
            before=self.snapshot()
            with self.assertRaises(Q.LogBlocked): log.emit(event='CAPTURE',state='RUNNING')
            self.assertEqual(self.snapshot(),before)

    def test_actual_hardlinked_record_rejected(self):
        with self.create() as log: log.emit(event='READY',state='RUNNING')
        path=next(self.root.glob('events-*.jsonl')); os.link(path,self.base/'owned-alias')
        with self.assertRaises(Q.LogBlocked): self.reopen()

    def test_reparse_ancestor_rejected_before_context_creation(self):
        original=Path.lstat
        def modeled(path):
            s=original(path)
            if path==self.state:
                return SimpleNamespace(st_mode=s.st_mode,st_file_attributes=1024,st_reparse_tag=1,st_nlink=s.st_nlink)
            return s
        with patch.object(Path,'lstat',modeled), patch.object(Q.os,'mkdir') as mkdir:
            with self.assertRaises(Q.LogBlocked): self.create()
        mkdir.assert_not_called()

    def test_symlink_ancestor_mode_rejected_without_OS_symlink_privilege(self):
        original=Path.lstat
        def modeled(path):
            if path==self.state: return SimpleNamespace(st_mode=stat.S_IFLNK,st_file_attributes=0,st_reparse_tag=0,st_nlink=1)
            return original(path)
        with patch.object(Path,'lstat',modeled):
            with self.assertRaises(Q.LogBlocked): self.create()
        self.assertFalse(self.root.exists())

    def test_invalid_clock_does_not_mutate_or_consume_sequence(self):
        ticks=iter((datetime(2026,11,12),NOW));args={**self.args,'clock':lambda:next(ticks)}
        with Q.CollectorLog.create(self.root,**args) as log:
            before=self.snapshot()
            with self.assertRaises(Q.LogBlocked): log.emit(event='STARTUP',state='STARTING')
            self.assertEqual(self.snapshot(),before)
            self.assertEqual(log.emit(event='STARTUP',state='STARTING').sequence,1)

    def test_fsync_error_latches_unknown_and_no_exception_text(self):
        log=self.create()
        with patch.object(Q.os,'fsync',side_effect=OSError('PRIVATE TOKEN URL')):
            with self.assertRaises(Q.LogBlocked) as blocked: log.emit(event='READY',state='RUNNING')
        self.assertNotIn('PRIVATE',str(blocked.exception))
        before=self.snapshot()
        with self.assertRaises(Q.LogBlocked): log.emit(event='READY',state='RUNNING')
        self.assertEqual(self.snapshot(),before)
        log.close()
        with self.assertRaises(Q.LogBlocked): self.reopen()

    def test_cursor_replace_error_preserves_completed_but_unknown_tail(self):
        log=self.create();log.emit(event='READY',state='RUNNING')
        with patch.object(Q.os,'replace',side_effect=OSError('PRIVATE')):
            with self.assertRaises(Q.LogBlocked): log.emit(event='CHECKPOINT',state='RUNNING')
        self.assertEqual(self.records()[-1]['sequence'],2)
        log.close();before=self.snapshot()
        with self.assertRaises(Q.LogBlocked): self.reopen()
        self.assertEqual(self.snapshot(),before)

    def test_partial_write_is_retained_and_not_adopted_after_close(self):
        log=self.create(); original=Q.os.write; calls=[]
        def fail(fd,raw):
            if not calls: calls.append(True);return original(fd,raw[:7])
            raise OSError('PRIVATE')
        with patch.object(Q.os,'write',side_effect=fail):
            with self.assertRaises(Q.LogBlocked): log.emit(event='READY',state='RUNNING')
        log.close();path=next(self.root.glob('events-*.jsonl'))
        self.assertEqual(path.stat().st_size,7)
        before=self.snapshot()
        with self.assertRaises(Q.LogBlocked): self.reopen()
        self.assertEqual(self.snapshot(),before)

    def test_failed_lock_close_does_not_release_context_to_new_writer(self):
        log=self.create(); original=Q.os.close; held=[]; unlink_attempts=[]
        def fail(fd): held.append(fd);raise OSError('PRIVATE_CLOSE_ERROR')
        try:
            with patch.object(Q.os,'close',side_effect=fail), patch.object(Path,'unlink',autospec=True,side_effect=lambda path:unlink_attempts.append(path)):
                with self.assertRaises(Q.LogBlocked): log.close()
            self.assertEqual(unlink_attempts,[])
            self.assertTrue((self.root/'writer.lock').exists())
            self.assertTrue(log.blocked)
            with self.assertRaises(Q.LogBlocked): self.reopen()
            with patch.object(Q.os,'close') as retry:
                with self.assertRaises(Q.LogBlocked): log.close()
            retry.assert_not_called()
        finally:
            # The inert failure did NOT close this known owned fd; retire it
            # after restoring the seam, without deleting or adopting the lock.
            for fd in set(held): original(fd)

    def test_unrecognized_error_constructor_cannot_export_freeform_text(self):
        error=Q.LogBlocked('https://private.invalid/?credential=TOPSECRET')
        self.assertEqual(error.code,'INTERNAL_DENIED')
        self.assertEqual(str(error),'INTERNAL_DENIED')

    def test_missing_private_root_is_closed_error_not_raw_os_exception(self):
        args={**self.args,'state_root':self.base/'PRIVATE_MISSING_STATE'}
        for factory in (Q.CollectorLog.create,Q.CollectorLog.open):
            caught=None
            try: factory(self.root,**args)
            except BaseException as exc: caught=exc
            self.assertIsInstance(caught,Q.LogBlocked)
            self.assertNotIn('PRIVATE',str(caught))

    def test_close_failure_cannot_mask_callers_original_error(self):
        log=self.create()
        with patch.object(log,'close',side_effect=Q.LogBlocked('LOG_IO_UNKNOWN')):
            with self.assertRaisesRegex(RuntimeError,'ORIGINAL_APPLICATION_ERROR'):
                with log: raise RuntimeError('ORIGINAL_APPLICATION_ERROR')
        self.assertTrue(log.blocked)
        log.close()

    def test_reentrant_writer_is_nonblocking_and_does_not_consume_sequence(self):
        holder=[]; nested=[]
        def clock():
            try: holder[0].emit(event='CAPTURE',state='RUNNING')
            except Q.LogBlocked as exc: nested.append(exc.code)
            return NOW
        with Q.CollectorLog.create(self.root,**{**self.args,'clock':clock}) as log:
            holder.append(log)
            self.assertEqual(log.emit(event='STARTUP',state='STARTING').sequence,1)
        self.assertEqual(nested,['LOG_BUSY'])

    def test_duplicate_sequence_with_relinked_cursor_is_not_adopted(self):
        with self.create() as log: log.emit(event='READY',state='RUNNING')
        path=next(self.root.glob('events-*.jsonl'));raw=path.read_bytes()*2;path.write_bytes(raw)
        cursor=self.root/'cursor.json';value=json.loads(cursor.read_bytes())
        value['files'][0]['bytes']=len(raw);value['files'][0]['sha256']=hashlib.sha256(raw).hexdigest()
        cursor.write_bytes((json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode())
        before=self.snapshot()
        with self.assertRaises(Q.LogBlocked): self.reopen()
        self.assertEqual(self.snapshot(),before)

    def test_oversized_cursor_is_not_read_or_repaired(self):
        with self.create(): pass
        (self.root/'cursor.json').write_bytes(b'x'*4097);before=self.snapshot()
        with self.assertRaises(Q.LogBlocked): self.reopen()
        self.assertEqual(self.snapshot(),before)

    def test_rotation_delete_error_keeps_managed_files_and_blocks_writer(self):
        with self.create() as log:
            # Reach the real byte boundary, not an assumed records-per-file.
            for _ in range(30):
                files=sorted(self.root.glob('events-*.jsonl'))
                if len(files)==2:
                    raw=files[-1].read_bytes();line=raw.splitlines(keepends=True)[-1]
                    seq=json.loads(line)['sequence']
                    next_size=len(line)+len(str(seq+1))-len(str(seq))
                    if len(raw)+next_size>1024: break
                log.emit(event='READY',state='RUNNING')
            else: self.fail('rotation byte boundary was not reached')
            before=self.snapshot();original=Path.unlink
            def deny(path,*args,**kwargs):
                if path.name.startswith('events-'): raise OSError('PRIVATE_DELETE_FAILURE')
                return original(path,*args,**kwargs)
            with patch.object(Path,'unlink',deny):
                with self.assertRaises(Q.LogBlocked): log.emit(event='READY',state='RUNNING')
            self.assertTrue(log.blocked);self.assertEqual(self.snapshot(),before)


if __name__=='__main__': unittest.main()
