import copy
import unittest

from unified_system import physical_acceptance as physical


class PhysicalAcceptanceTests(unittest.TestCase):
    def records(self, nodes):
        return [dict(node_id=node, scenario=scenario, release_sha='a' * 40,
                     run_id='office-acceptance-1', result='PASS', environment='PHYSICAL_WINDOWS',
                     evidence_sha256='b' * 64)
                for node in nodes for scenario in physical.SCENARIOS]

    def assess(self, nodes, records):
        return physical.assess(nodes, records, release_sha='a' * 40, run_id='office-acceptance-1')

    def test_all_five_or_six_nodes_required_but_claims_never_authenticate_themselves(self):
        for count in (5, 6):
            nodes = [f'pc-{i}' for i in range(count)]
            report = self.assess(nodes, self.records(nodes))
            self.assertEqual(report['status'], 'RECORDED_UNVERIFIED')
            self.assertEqual(report['recorded_cases'], count * 15)
            self.assertFalse(report['physical_acceptance_confirmed'])
            self.assertFalse(report['deployment_authorized'])

    def test_no_records_means_not_run(self):
        report = self.assess(['pc-' + str(i) for i in range(6)], [])
        self.assertEqual(report['status'], 'NOT_RUN')
        self.assertEqual(len(report['missing']), 90)

    def test_two_nodes_never_satisfy_six_node_acceptance(self):
        nodes = ['pc-' + str(i) for i in range(6)]
        report = self.assess(nodes, self.records(nodes[:2]))
        self.assertEqual(report['status'], 'BLOCKED')
        self.assertEqual(len(report['missing']), 60)

    def test_duplicate_wrong_release_wrong_run_or_cloud_cannot_qualify(self):
        nodes = ['pc-' + str(i) for i in range(5)]
        for field, value in [('release_sha', 'c' * 40), ('run_id', 'stale-run'),
                             ('environment', 'CLOUD'), ('evidence_sha256', 'invalid'),
                             ('result', 'SKIPPED'), ('node_id', 'unknown'),
                             ('scenario', 'invented'), ('result', True)]:
            records = self.records(nodes)
            records[0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.assess(nodes, records)
        records = self.records(nodes)
        # Stay inside the case bound so the duplicate-case check must run.
        records[1] = copy.deepcopy(records[0])
        with self.assertRaises(ValueError):
            self.assess(nodes, records)

    def test_failure_remains_failure(self):
        nodes = ['pc-' + str(i) for i in range(6)]
        records = self.records(nodes)
        records[0]['result'] = 'FAIL'
        report = self.assess(nodes, records)
        self.assertEqual(report['status'], 'BLOCKED')
        self.assertEqual(len(report['failed']), 1)

    def test_inventory_is_explicit_unique_and_five_or_six(self):
        for nodes in ([], ['pc'], ['pc'] * 5, [f'pc-{i}' for i in range(7)],
                      ['a', 'b', 'c', 'd', 'A'], ['a', 'b', 'c', 'd', '../path']):
            with self.subTest(nodes=nodes), self.assertRaises(ValueError):
                self.assess(nodes, [])


if __name__ == '__main__':
    unittest.main()
