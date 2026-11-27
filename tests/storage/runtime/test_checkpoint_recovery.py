from pathlib import Path
import tempfile
import unittest

from unified_system.storage.checkpoints import inspect_checkpoint_object
from unified_system.storage.contracts import StorageBlocked
from unified_system.storage.object_store import ObjectStore


class CheckpointRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="checkpoint-owned-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/"objects"
        self.store = ObjectStore.create(self.root, store_id="00000000-0000-4000-8000-000000000087")

    def test_readback_does_not_establish_checkpoint_or_cursor_authority(self):
        raw = b'{"committed_at_utc":null,"commit_time_status":"UNKNOWN_COMMIT_INSTANT"}'
        obj = self.store.put(raw)
        observation = inspect_checkpoint_object(self.store, obj.sha256)
        self.assertEqual(observation.raw_bytes, raw)
        self.assertFalse(observation.publication_confirmed)
        self.assertFalse(observation.checkpoint_schema_verified)
        with self.assertRaisesRegex(StorageBlocked, "CHECKPOINT_PROOF_ADAPTER_UNAVAILABLE"):
            observation.require_recovery_cursor()

    def test_missing_and_corrupted_checkpoint_objects_never_resume(self):
        with self.assertRaises(StorageBlocked):
            inspect_checkpoint_object(self.store, "a"*64)
        obj = self.store.put(b'fixture checkpoint')
        (self.root/"objects"/obj.sha256).write_bytes(b'corrupt fixture')
        with self.assertRaises(StorageBlocked):
            inspect_checkpoint_object(self.store, obj.sha256)
