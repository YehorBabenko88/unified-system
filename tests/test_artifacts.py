import hashlib
import tempfile
import unittest
from pathlib import Path
from unified_system.artifacts import verify_artifact
from unified_system.contracts import ContractError

class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.path=Path(self.t.name)/"sample.bin"
        self.path.write_bytes(b"safe offline fixture")
        self.digest=hashlib.sha256(self.path.read_bytes()).hexdigest()
    def test_valid(self):
        self.assertEqual(verify_artifact(self.path,self.digest)["status"],"BYTES_VERIFIED_ONLY")
    def test_wrong_digest(self):
        with self.assertRaises(ContractError):verify_artifact(self.path,"0"*64)
    def test_bounded(self):
        with self.assertRaises(ContractError):verify_artifact(self.path,self.digest,max_bytes=2)
    def test_invalid_digest(self):
        with self.assertRaises(ContractError):verify_artifact(self.path,"BAD")
    def test_symlink(self):
        link=Path(self.t.name)/"link.bin"
        try:link.symlink_to(self.path)
        except (OSError,NotImplementedError):self.skipTest("symlink unavailable")
        with self.assertRaises(ContractError):verify_artifact(link,self.digest)
if __name__=="__main__":unittest.main()
