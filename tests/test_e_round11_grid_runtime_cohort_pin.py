"""E current exact B9e0 four-module cohort integrity tests; synthetic files only.

Real Grid source bytes/PG18/Root/OS are NOT executed here. This checks that
four manifest-pinned files, Git blob hashes and source lease cannot be
replaced while the protected Root code binds a current source tree.
"""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from unified_system.grid_writer_fence_model import ResourceFenceBlocked
from unified_system.grid_writer_lab_bridge import (
    GRID_RUNTIME_LAB_SHA, GRID_REPOSITORY, _GRID_RUNTIME_BLOBS,
    verified_grid_runtime_cohort_pin,
)


class FakeScopedSource:
    def __init__(self, root):
        self.root=root
        self.active=True
    def require_current(self):
        return self.active
    def source_scope(self,module,root,commit):
        if module!="market_data" or root!=self.root or commit!=GRID_RUNTIME_LAB_SHA:
            raise ValueError("SOURCE_REJECTED")
        return self.root


class RuntimeCohortPinTests(unittest.TestCase):
    def setUp(self):
        tmp=TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name).resolve()
        self.source=FakeScopedSource(self.root)
        self.manifest={
            "sources":{"market_data":{
                "repository":GRID_REPOSITORY,
                "commit":GRID_RUNTIME_LAB_SHA,
                "root":"sources/market_data"}},
            "files":{},
        }
        self.blobs={}
        for relative in _GRID_RUNTIME_BLOBS:
            raw=("inert synthetic file "+relative).encode()
            path=self.root/relative
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(raw)
            self.manifest["files"]["sources/market_data/"+relative]={
                "sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)}
            self.blobs[relative]=hashlib.sha1(
                b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

    def test_exact_b9e0_cohort_is_pinned_without_native_authority(self):
        self.assertEqual(
            GRID_RUNTIME_LAB_SHA,
            "9e0d57c4c0f2d01bc381ada090b62d23566b32aa",
        )
        self.assertEqual(_GRID_RUNTIME_BLOBS, {
            "grid/canonical_lab_fenced_writer.py":
                "247d7fab2738e1892a05979e407f637f9df62784",
            "grid/canonical_lab_continuous_collector.py":
                "873e83839bee9ceb1cca710a5291ba2cf5f7f038",
            "grid/c_lab_journal_adapter.py":
                "ab93c6d421c3d3f0232060f6ded7ac01bf8eeda0",
            "grid/c_async_fenced_writer.py":
                "35bf202bb1674238d53b74f962af966d2a699fa2",
        })

    def test_all_four_exact_pins_are_checked_but_do_not_grant(self):
        with patch.dict(_GRID_RUNTIME_BLOBS,self.blobs,clear=True):
            evidence=verified_grid_runtime_cohort_pin(
                self.source,self.manifest,self.root)
        self.assertEqual(set(evidence["verified_files"]),set(self.blobs))
        self.assertEqual(evidence["source_commit"],GRID_RUNTIME_LAB_SHA)
        self.assertFalse(evidence["native_admitted"])
        self.assertFalse(evidence["trading_authorized"])

    def test_altered_file_bytes_are_rejected(self):
        relative=next(iter(self.blobs))
        (self.root/relative).write_bytes(b"changed after manifest")
        with patch.dict(_GRID_RUNTIME_BLOBS,self.blobs,clear=True):
            with self.assertRaises(ResourceFenceBlocked):
                verified_grid_runtime_cohort_pin(self.source,self.manifest,self.root)

    def test_changed_git_blob_pin_is_rejected(self):
        bad=self.blobs.copy()
        bad[next(iter(bad))]="0"*40
        with patch.dict(_GRID_RUNTIME_BLOBS,bad,clear=True):
            with self.assertRaises(ResourceFenceBlocked):
                verified_grid_runtime_cohort_pin(self.source,self.manifest,self.root)

    def test_source_revision_mismatch_is_rejected(self):
        self.manifest["sources"]["market_data"]["commit"]="0"*40
        with patch.dict(_GRID_RUNTIME_BLOBS,self.blobs,clear=True):
            with self.assertRaises(ResourceFenceBlocked):
                verified_grid_runtime_cohort_pin(self.source,self.manifest,self.root)

    def test_revocation_fails_closed(self):
        self.source.active=False
        with patch.dict(_GRID_RUNTIME_BLOBS,self.blobs,clear=True):
            with self.assertRaises(ResourceFenceBlocked):
                verified_grid_runtime_cohort_pin(self.source,self.manifest,self.root)


if __name__=="__main__":
    unittest.main()
