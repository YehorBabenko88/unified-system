import copy
import unittest
from unified_system.contracts import ContractError, seal, validate_handoff
from unified_system.supervisor import Supervisor

class Contracts(unittest.TestCase):
    def setUp(self):
        self.dataset="a"*64
        self.envelope={"schema_version":1,"producer":"terminan","run_id":"r-1","dataset_fingerprint":self.dataset,"status":"SEALED","capabilities":["historical_research"],"payload":{"result":1}}
        self.envelope["sha256"]=seal(self.envelope)

    def test_valid(self):
        self.assertEqual(validate_handoff(self.envelope,self.dataset)["status"],"VERIFIED_SYNTHETIC")

    def test_retired_producer_refused_even_with_valid_digest(self):
        for producer in ("strattester", "grid", "meta_analyse"):
            e=copy.deepcopy(self.envelope);e["producer"]=producer
            e["sha256"]=seal({k:v for k,v in e.items() if k!="sha256"})
            with self.subTest(producer=producer),self.assertRaises(ContractError):
                validate_handoff(e,self.dataset)

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
        s=Supervisor(("terminan",));s.preflight();s.accept_research(self.envelope,self.dataset)
        self.assertEqual(s.observe()["state"],"DEGRADED")
        self.assertFalse(s.snapshot()["trading_authorized"])

    def test_no_producer(self):
        s=Supervisor(("market_data",));s.preflight()
        with self.assertRaises(ContractError):s.accept_research(self.envelope,self.dataset)
        self.assertEqual(s.state,"BLOCKED")

    def test_requires_preflight(self):
        s=Supervisor(("terminan",))
        with self.assertRaises(ContractError):s.accept_research(self.envelope,self.dataset)

if __name__=="__main__": unittest.main()
