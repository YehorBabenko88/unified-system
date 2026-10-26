import os
import sqlite3
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
        with sqlite3.connect(self.path) as db:db.execute("UPDATE transitions SET state='OBSERVING'")
        with self.assertRaises(ContractError):self.j.read()
    def test_unknown_state(self):
        with self.assertRaises(ContractError):self.j.append("TRADING")
    def test_empty(self):self.assertEqual(self.j.read(),[])
    def test_no_implicit_creation(self):
        other=Journal(Path(self.temp.name)/"missing.db")
        self.assertEqual(other.read(),[])
        self.assertFalse(other.path.exists())
if __name__=="__main__":unittest.main()
