import unittest
from unified_system.infra_inventory import summarize_fleet
from unified_system.fleet_policy import FleetPolicyError

NOW=1800000000000
def node(i):
    return dict(id="PC"+str(i),state="ACTIVE",cpu=.2,memory=.25,disk=.4,
        modules=["grid","strattester","math","terminan","unified-system"],
        zone="room1",last_heartbeat_ms=NOW-500,epoch=1)

class InventoryTests(unittest.TestCase):
    def test_six_pc_db_sizes(self):
        r=summarize_fleet([node(i) for i in range(1,7)],NOW,
            [{"id":"grid","engine":"postgresql","size_bytes":2048,"status":"OBSERVED","owner":"grid"},
             {"id":"research","engine":"sqlite","size_bytes":None,"status":"UNAVAILABLE","owner":"strattester"}])
        self.assertEqual(r["active_nodes"],6)
        self.assertEqual(r["database_total_bytes_observed"],2048)
        self.assertEqual(r["unknown_database_sizes"],1)
        self.assertEqual(r["network_topology_status"],"NOT_ATTESTED")
    def test_no_fake_links(self):
        self.assertEqual(summarize_fleet([],NOW)["network_links"],[])
    def test_duplicate_database(self):
        db={"id":"one","engine":"sqlite","size_bytes":1,"status":"OBSERVED","owner":"math"}
        with self.assertRaises(FleetPolicyError):summarize_fleet([],NOW,[db,db])
    def test_unknown_size_negative(self):
        with self.assertRaises(FleetPolicyError):
            summarize_fleet([],NOW,[{"id":"x","engine":"postgresql","size_bytes":-1,"status":"OBSERVED","owner":"grid"}])
if __name__=="__main__":unittest.main()
