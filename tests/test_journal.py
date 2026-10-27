import os
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from unified_system.journal import Journal
from unified_system.contracts import ContractError

class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"state.db"
        self.j=Journal(self.path)
        self.j.initialize()
    def test_recovery(self):
        self.j.append("INSTALLED")
        self.j.append("INFRA_READY",{"mode":"synthetic"})
        self.assertEqual([x["state"] for x in Journal(self.path).read()],["INSTALLED","INFRA_READY"])
    def test_tamper(self):
        self.j.append("INSTALLED")
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("UPDATE transitions SET state=\'OBSERVING\'")
            db.commit()
        with self.assertRaises(ContractError):self.j.read()
    def test_long_chain_latest_digest_not_lexical_max(self):
        for _ in range(32):
            self.j.append("INFRA_READY", {"iteration": _})
        self.assertEqual(len(self.j.read()), 32)

    def test_append_after_reopen(self):
        self.j.append("INSTALLED")
        other=Journal(self.path)
        other.append("INFRA_READY")
        self.assertEqual(len(self.j.read()), 2)

    def test_unknown_state(self):
        with self.assertRaises(ContractError):self.j.append("TRADING")
    def test_empty(self):self.assertEqual(self.j.read(),[])
    def test_no_implicit_creation(self):
        other=Journal(Path(self.temp.name)/"missing.db")
        self.assertEqual(other.read(),[])
        self.assertFalse(other.path.exists())
if __name__=="__main__":unittest.main()
