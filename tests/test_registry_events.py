import unittest
from unified_system.contracts import ContractError
from unified_system.registry import negotiate
from unified_system.events import EventCursor

class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.d={"module_id":"grid","api_major":1,"api_minor":0,"source_sha":"a"*64,"capabilities":["read_only_health"]}
    def test_valid(self):
        self.assertEqual(negotiate(self.d,expected_id="grid")["verified"],"SCHEMA_ONLY")
    def test_wrong_module(self):
        with self.assertRaises(ContractError):negotiate(self.d,expected_id="terminan")
    def test_boolean_major(self):
        self.d["api_major"]=True
        with self.assertRaises(ContractError):negotiate(self.d,expected_id="grid")
    def test_duplicate_capability(self):
        self.d["capabilities"]=["read_only_health"]*2
        with self.assertRaises(ContractError):negotiate(self.d,expected_id="grid")

class EventTests(unittest.TestCase):
    def test_sequence_and_gap(self):
        c=EventCursor()
        self.assertEqual(c.ingest({"epoch":"e1","sequence":10,"payload":{}}),"SNAPSHOT_REQUIRED")
        self.assertEqual(c.ingest({"epoch":"e1","sequence":11,"payload":{}}),"APPLIED")
        self.assertEqual(c.ingest({"epoch":"e1","sequence":11,"payload":{}}),"DUPLICATE_OR_OLD")
        self.assertEqual(c.ingest({"epoch":"e1","sequence":13,"payload":{}}),"GAP_SNAPSHOT_REQUIRED")
        self.assertEqual(c.ingest({"epoch":"e2","sequence":1,"payload":{}}),"SNAPSHOT_REQUIRED")
    def test_boolean_sequence(self):
        with self.assertRaises(ContractError):EventCursor().ingest({"epoch":"e","sequence":True,"payload":{}})
if __name__=="__main__":unittest.main()
