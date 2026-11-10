"""Bounded original-byte custody using the EXISTING non-authorizing Journal.

ROOT must provide a private initialized journal and owned ObjectStore. No second
registry, consensus, sender, receipt reconstruction, retry or cleanup lives here.
An attempt marker is written BEFORE a future admitted send and does not establish
whether anything was sent. A recovered original always has native outcome UNKNOWN.
"""
import base64
import binascii
import sqlite3
import stat
import threading

from ..contracts import ContractError
from ..journal import Journal
from .contracts import StorageBlocked, require
from .object_store import ObjectStore, _parents
from .publication_records import (RetainedPublicationIntent, PendingPublicationObservation,
                                  publication_identifier, MAX_ORIGINAL_BYTES)

MAX_RECORDS = 64
MAX_JOURNAL_BYTES = 2*1024*1024
SCHEMA = 'unified.storage.pending-original.v1'


class PendingPublicationJournal:
    def __init__(self, journal, owned_store):
        require(type(journal) is Journal and type(owned_store) is ObjectStore,
                'OWNED_JOURNAL_AND_STORE_REQUIRED')
        self._journal = journal
        self._store = owned_store
        self._mutex = threading.RLock()
        self._records()

    def _path_check(self):
        path = self._journal.path.absolute()
        _parents(path.parent)
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and not path.is_symlink() and info.st_nlink == 1
                and not getattr(info, 'st_file_attributes', 0) & 1024
                and info.st_size <= MAX_JOURNAL_BYTES, 'PENDING_JOURNAL_UNAVAILABLE')
        for suffix in ('-wal', '-shm', '-journal'):
            sidecar = path.with_name(path.name+suffix)
            require(not sidecar.exists() and not sidecar.is_symlink(), 'PENDING_JOURNAL_RECOVERY_REQUIRED')
        return info.st_dev, info.st_ino

    def _records(self):
        try:
            before = self._path_check()
            records = Journal.read(self._journal)
            require(self._path_check() == before, 'PENDING_JOURNAL_IDENTITY_CHANGED')
            require(len(records) <= MAX_RECORDS, 'PENDING_JOURNAL_CAPACITY')
            originals, latest = {}, {}
            for row in records:
                value = row['receipt']
                require(row['state'] == 'OBSERVING' and type(value) is dict and set(value) == {
                    'schema', 'publication_id', 'intent_base64', 'intent_sha256', 'intent_bytes', 'phase'})
                require(value['schema'] == SCHEMA and type(value['intent_base64']) is str)
                require(len(value['intent_base64']) <= 4*((MAX_ORIGINAL_BYTES+2)//3))
                raw = base64.b64decode(value['intent_base64'], validate=True)
                require(base64.b64encode(raw).decode('ascii') == value['intent_base64'])
                original = RetainedPublicationIntent(value['publication_id'], raw)
                require(value['intent_sha256'] == original.sha256 and value['intent_bytes'] == str(len(raw)))
                require(value['phase'] in ('RETAINED', 'ATTEMPT_UNCERTAIN'))
                key = original.publication_id
                if key not in originals:
                    require(value['phase'] == 'RETAINED', 'PENDING_ORIGINAL_NOT_RETAINED')
                    originals[key] = original
                else:
                    require(originals[key] == original and latest[key] == 'RETAINED'
                            and value['phase'] == 'ATTEMPT_UNCERTAIN', 'PENDING_ORIGINAL_CONFLICT')
                latest[key] = value['phase']
            return records, originals, latest
        except StorageBlocked:
            raise
        except (ContractError, OSError, ValueError, TypeError, KeyError, binascii.Error, sqlite3.Error):
            raise StorageBlocked('PENDING_ORIGINAL_UNAVAILABLE') from None

    def _append(self, original, phase, records):
        require(len(records) < MAX_RECORDS, 'PENDING_JOURNAL_CAPACITY')
        value = dict(schema=SCHEMA, publication_id=original.publication_id,
            intent_base64=base64.b64encode(original.raw_bytes).decode('ascii'),
            intent_sha256=original.sha256, intent_bytes=str(len(original.raw_bytes)), phase=phase)
        try:
            Journal.append(self._journal, 'OBSERVING', value, expected_sequence=len(records))
            self._records()
        except StorageBlocked:
            raise
        except (ContractError, OSError, ValueError, TypeError, KeyError, sqlite3.Error):
            # An append may already have committed. Retain original identity and
            # reconcile this same journal; never erase, replace or infer failure.
            raise StorageBlocked('PENDING_APPEND_OUTCOME_UNKNOWN') from None

    def retain(self, original):
        require(type(original) is RetainedPublicationIntent, 'EXACT_ORIGINAL_RECORD_REQUIRED')
        original = RetainedPublicationIntent(original.publication_id, original.raw_bytes)
        with self._mutex:
            records, originals, _ = self._records()
            if original.publication_id in originals:
                require(originals[original.publication_id] == original, 'PENDING_ORIGINAL_CONFLICT')
                self.verify_staged_original(original.publication_id)
                return self.observation(original.publication_id)
            require(len(records) < MAX_RECORDS, 'PENDING_JOURNAL_CAPACITY')
            ObjectStore.put(self._store, original.raw_bytes, max_bytes=MAX_ORIGINAL_BYTES)
            require(ObjectStore.read(self._store, original.sha256, max_bytes=MAX_ORIGINAL_BYTES) == original.raw_bytes)
            self._append(original, 'RETAINED', records)
            return self.observation(original.publication_id)

    def mark_attempt_uncertain(self, publication_id):
        key = publication_identifier(publication_id)
        with self._mutex:
            records, originals, latest = self._records()
            require(key in originals, 'PENDING_ORIGINAL_NOT_RETAINED')
            self.verify_staged_original(key)
            if latest[key] == 'RETAINED':
                self._append(originals[key], 'ATTEMPT_UNCERTAIN', records)
            return self.observation(key)

    def recover_original(self, publication_id):
        key = publication_identifier(publication_id)
        with self._mutex:
            _, originals, _ = self._records()
            require(key in originals, 'PENDING_ORIGINAL_NOT_RETAINED')
            return originals[key]

    def verify_staged_original(self, publication_id):
        with self._mutex:
            original = self.recover_original(publication_id)
            require(ObjectStore.read(self._store, original.sha256, max_bytes=MAX_ORIGINAL_BYTES)
                    == original.raw_bytes, 'STAGED_ORIGINAL_BYTES_MISMATCH')
            return original

    def observation(self, publication_id):
        key = publication_identifier(publication_id)
        with self._mutex:
            _, originals, latest = self._records()
            require(key in originals, 'PENDING_ORIGINAL_NOT_RETAINED')
            return PendingPublicationObservation(key, originals[key].sha256, latest[key])
