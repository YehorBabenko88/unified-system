"""Local capability disclosure only; unsupported bounds never qualify admission."""
import json
from pathlib import Path
import unittest
from unified_system.gateway_worker import GatewayWorker

class ResourceCapabilities(unittest.TestCase):
    def test_all_bounds_explicitly_unsupported_for_admission(self):
        raw=GatewayWorker.resource_capabilities()
        self.assertIs(type(raw),bytes)
        value=json.loads(raw)
        self.assertEqual(value['admitted_fields'],[])
        expected={'cpu_millicores','cpu_share','resident_memory_bytes','committed_memory_bytes',
                  'available_commit_bytes','available_physical_bytes'}
        self.assertEqual(set(value['unsupported_fields']),expected)
        self.assertEqual(set(value['fields']),expected)
        self.assertFalse(value['dispatch_authorized'])
        for field in value['fields'].values():
            self.assertEqual(field['admission'],'UNSUPPORTED')
            self.assertTrue(field['gap'])
        self.assertEqual(raw,json.dumps(value,sort_keys=True,separators=(',',':')).encode('ascii'))
        value['admitted_fields'].append('resident_memory_bytes')
        self.assertEqual(json.loads(GatewayWorker.resource_capabilities())['admitted_fields'],[])

    def test_documented_machine_report_exactly_matches_runtime_disclosure(self):
        path=Path(__file__).parents[2]/'docs/intelligence/jobs/worker-resource-capabilities.v1.json'
        self.assertEqual(json.loads(path.read_bytes()),json.loads(GatewayWorker.resource_capabilities()))
