import tempfile
import unittest
from pathlib import Path
from unified_system.contracts import ContractError,seal
from unified_system.coordinator import Coordinator

class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"journal.sqlite"
        self.c=Coordinator(self.path,("strattester","grid","terminan"))
        self.dataset="a"*64
        self.env={"schema_version":1,"producer":"strattester","run_id":"r1","dataset_fingerprint":self.dataset,"status":"SEALED","capabilities":["historical_research"],"payload":{}}
        self.env["sha256"]=seal(self.env)
    def test_lifecycle(self):
        self.c.initialize();self.c.preflight();self.c.accept(self.env,self.dataset)
        self.assertEqual(self.c.observe()["state"],"OBSERVING")
        self.assertEqual(self.c.snapshot()["journal_records"],4)
    def test_reboot_fail_closed(self):
        self.c.initialize();self.c.preflight()
        second=Coordinator(self.path,("strattester","grid","terminan"))
        self.assertEqual(second.initialize()["state"],"BLOCKED")
        with self.assertRaises(ContractError):second.preflight()
    def test_bad_handoff_persists_block(self):
        self.c.initialize();self.c.preflight();self.env["payload"]["bad"]=1
        with self.assertRaises(ContractError):self.c.accept(self.env,self.dataset)
        self.assertEqual(self.c.snapshot()["state"],"BLOCKED")
        self.assertEqual(Coordinator(self.path,()).initialize()["state"],"BLOCKED")
    def test_absent_grid_degrades(self):
        c=Coordinator(self.path,("strattester","terminan"))
        c.initialize();c.preflight();c.accept(self.env,self.dataset)
        self.assertEqual(c.observe()["state"],"DEGRADED")
if __name__=="__main__":unittest.main()
