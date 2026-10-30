import unittest
from unified_system.fleet_policy import FleetPolicyError, topology, plan_placement

NOW=1800000000000

def node(i,**kw):
    out=dict(id=f"PC{i}",state="ACTIVE",cpu=.2,memory=.25,disk=.4,
             modules=["grid","strattester","math","terminan","unified-system"],
             zone=f"room{i%2}",last_heartbeat_ms=NOW-500,epoch=1)
    out.update(kw)
    return out

def job(i,module="math",**kw):
    out=dict(id=f"task{i}",module=module,cpu_cost=.1,memory_cost=.1,zone_avoid=[])
    out.update(kw)
    return out

class FleetPolicyTests(unittest.TestCase):
    def test_initial_six(self):
        x=topology([node(i) for i in range(1,7)],NOW)
        self.assertEqual(len(x),6)
    def test_add_remove(self):
        self.assertEqual(len(topology([node(i) for i in range(1,8)],NOW)),7)
        self.assertEqual(len(topology([node(i) for i in range(1,6)],NOW)),5)
    def test_stale_not_assigned(self):
        nodes=[node(1,last_heartbeat_ms=NOW-90000),node(2)]
        p=plan_placement(nodes,[job(1)],NOW,quorum=True)
        self.assertEqual(p["proposed"][0]["candidate"],"PC2")
        self.assertEqual(topology(nodes,NOW)[0]["state"],"SUSPECT")
    def test_quorum_fail_closed(self):
        p=plan_placement([node(1)],[job(1)],NOW)
        self.assertIsNone(p["proposed"][0]["candidate"])
        self.assertEqual(p["proposed"][0]["state"],"NO_QUORUM")
        self.assertFalse(p["execution_authorized"])
    def test_overload(self):
        p=plan_placement([node(1,cpu=.9)],[job(1)],NOW,quorum=True)
        self.assertEqual(p["proposed"][0]["state"],"NO_CAPACITY")
    def test_missing_module(self):
        p=plan_placement([node(1,modules=["grid"])],[job(1)],NOW,quorum=True)
        self.assertIsNone(p["proposed"][0]["candidate"])
    def test_invalid_utilization(self):
        with self.assertRaises(FleetPolicyError):
            topology([node(1,cpu=float("nan"))],NOW)
    def test_duplicate(self):
        with self.assertRaises(FleetPolicyError):
            topology([node(1),node(1)],NOW)
    def test_drain(self):
        p=plan_placement([node(1,state="DRAINING"),node(2)],[job(1)],NOW,quorum=True)
        self.assertEqual(p["proposed"][0]["candidate"],"PC2")
    def test_allows_math_only(self):
        p=plan_placement([node(1,modules=["math"])],[job(1)],NOW,quorum=True)
        self.assertEqual(p["proposed"][0]["candidate"],"PC1")
if __name__=="__main__":unittest.main()
