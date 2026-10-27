import copy
import unittest
from unified_system.contracts import ContractError, seal, validate_handoff
from unified_system.supervisor import Supervisor

class Contracts(unittest.TestCase):
    def setUp(self):
        self.dataset="a"*64
        self.envelope={"schema_version":1,"producer":"strattester","run_id":"r-1","dataset_fingerprint":self.dataset,"status":"SEALED","capabilities":["historical_research"],"payload":{"result":1}}
        self.envelope["sha256"]=seal(self.envelope)

    def test_valid(self):
        self.assertEqual(validate_handoff(self.envelope,self.dataset)["status"],"VERIFIED_SYNTHETIC")

    def test_tamper(self):
        e=copy.deepcopy(self.envelope);e["payload"]["result"]=2
        with self.assertRaises(ContractError): validate_handoff(e,self.dataset)

    def test_mismatch(self):
        with self.assertRaises(ContractError): validate_handoff(self.envelope,"b"*64)

    def test_nonfinite(self):
        e=copy.deepcopy(self.envelope);e["payload"]["bad"]=float("nan")
        with self.assertRaises(ContractError): validate_handoff(e,self.dataset)

    def test_unsealed(self):
        e=copy.deepcopy(self.envelope);e["status"]="RUNNING";e["sha256"]=seal({k:v for k,v in e.items() if k!="sha256"})
        with self.assertRaises(ContractError): validate_handoff(e,self.dataset)

    def test_missing_modules(self):
        s=Supervisor(("strattester",));s.preflight();s.accept_research(self.envelope,self.dataset)
        self.assertEqual(s.observe()["state"],"DEGRADED")
        self.assertFalse(s.snapshot()["trading_authorized"])

    def test_no_producer(self):
        s=Supervisor(("grid","terminan"));s.preflight()
        with self.assertRaises(ContractError):s.accept_research(self.envelope,self.dataset)
        self.assertEqual(s.state,"BLOCKED")

    def test_requires_preflight(self):
        s=Supervisor(("strattester",))
        with self.assertRaises(ContractError):s.accept_research(self.envelope,self.dataset)

if __name__=="__main__": unittest.main()
