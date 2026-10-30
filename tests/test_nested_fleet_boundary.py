import json
import copy
import tempfile
import unittest
from pathlib import Path
from unified_system.fleet_control import FleetControl
from unified_system.lifecycle import Lifecycle
from unified_system.lifecycle_api import ReadOnlyLifecycleApp


class NestedFleetBoundaryTests(unittest.TestCase):
    def test_forged_node_observations_are_rejected_at_both_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            fleet = FleetControl(Path(tmp)/'fleet.db', ['v'])
            fleet.approve_node('node', 1, 'zone', 'software-test-only')
            valid = fleet.status_snapshot(0)
            mutations = [lambda f: f.update(trading_authorized=True),
                         lambda f: f['nodes'][0].update(cpu=30),
                         lambda f: f['nodes'][0].update(db_sizes={'private':123}),
                         lambda f: f['nodes'][0].update(identity_verified=True),
                         lambda f: f['nodes'][0].update(execution_authorized=True),
                         lambda f: f['nodes'].append(copy.deepcopy(f['nodes'][0])),
                         lambda f: f['nodes'][0].update(epoch=True),
                         lambda f: f['nodes'][0].update(epoch=2**53),
                         lambda f: f['nodes'][0].update(sequence=2**53),
                         lambda f: f['nodes'][0].update(last_heartbeat_ms=2**53),
                         lambda f: f['nodes'][0].update(available_resources={'cpu':10**400,'memory':1,'disk':1})]
            life = Lifecycle(Path(tmp)/'life.db', [])
            life.initialize()
            for mutate in mutations:
                with self.subTest(mutation=mutate):
                    forged = copy.deepcopy(valid); mutate(forged)
                    life.fleet_provider = lambda: forged
                    self.assertEqual(life.snapshot()['fleet']['status'], 'UNAVAILABLE')
                    snapshot = life.snapshot(); snapshot['fleet'] = forged
                    codes = []
                    b''.join(ReadOnlyLifecycleApp(lambda: snapshot)(
                        {'REQUEST_METHOD':'GET','PATH_INFO':'/internal/v1/lifecycle'},
                        lambda code, headers: codes.append(code)))
                    self.assertEqual(codes, ['503 Service Unavailable'])

    def test_provider_cannot_publish_nested_execution_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            fleet = FleetControl(Path(tmp)/'fleet.db', ['v'])
            forged = fleet.status_snapshot(0)
            forged['execution_authorized'] = True
            life = Lifecycle(Path(tmp)/'life.db', [], fleet_provider=lambda: forged)
            self.assertEqual(life.initialize()['fleet']['status'], 'UNAVAILABLE')

    def test_http_revalidates_nested_fleet_from_arbitrary_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            life = Lifecycle(Path(tmp)/'life.db', [])
            snapshot = life.initialize()
            snapshot['fleet'] = {'nodes': [], 'execution_authorized': True}
            codes = []
            app = ReadOnlyLifecycleApp(lambda: snapshot)
            body = b''.join(app({'REQUEST_METHOD':'GET', 'PATH_INFO':'/internal/v1/lifecycle'}, lambda code, headers: codes.append(code)))
            self.assertEqual(codes, ['503 Service Unavailable'])
            self.assertIs(json.loads(body)['execution_authorized'], False)
