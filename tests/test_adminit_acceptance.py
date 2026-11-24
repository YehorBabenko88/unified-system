import copy
import unittest
from unified_system import adminit_acceptance as adminit


class AdminitPreparationTests(unittest.TestCase):
    def plan(self):
        return adminit.prepare(release_sha='a'*40, publisher_sha256='b'*64,run_id='adminit-run-1')

    def test_preparation_has_no_grant_or_execution_and_all_phases_missing(self):
        plan=self.plan()
        self.assertIsNone(plan['owner_grant'])
        self.assertFalse(plan['physical_execution'])
        self.assertEqual(set(plan['phases']),set('ABCDEFG'))
        report=adminit.assess(plan,[])
        self.assertEqual(report['status'],'NOT_RUN')
        self.assertEqual(report['missing'],list('ABCDEFG'))
        self.assertFalse(report['multi_node_ha_confirmed'])

    def test_plan_rejects_release_pin_namespace_or_authority_mutation(self):
        for field,value in [('release_sha','bad'),('publisher_sha256','bad'),
                            ('isolated_root','C:\\Windows'),('owner_grant',{}),
                            ('physical_execution',True),('node','PC4')]:
            plan=self.plan();plan[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):adminit.assess(plan,[])

    def test_complete_claims_remain_unverified_and_any_failure_blocks(self):
        plan=self.plan()
        records=[dict(phase=p,result='PASS',release_sha=plan['release_sha'],
                      node='ADMINIT',run_id=plan['run_id'],observed_at_ms=1000,
                      evidence_sha256='c'*64,signature_sha256='d'*64) for p in 'ABCDEFG']
        report=adminit.assess(plan,records)
        self.assertEqual(report['status'],'RECORDED_UNVERIFIED')
        self.assertFalse(report['physical_acceptance_confirmed'])
        self.assertFalse(report['physical_execution'])
        records[0]['result']='FAIL'
        self.assertEqual(adminit.assess(plan,records)['status'],'BLOCKED')
        with self.assertRaises(ValueError):adminit.assess(plan,[records[0],records[0]])
        records[0]['phase']='H'
        with self.assertRaises(ValueError):adminit.assess(plan,records)

    def test_instruments_require_ten_unique_public_evidence_bound_real_windows(self):
        evidence=[dict(symbol='COIN'+str(i)+'USDT',category='linear',quote_coin='USDT',
                       contract_type='LinearPerpetual',status='Trading',origin='AUTHENTICATED',
                       source='https://api.bybit.com/v5/market/instruments-info',
                       observed_at_ms=1000,response_sha256='e'*64,
                       historical_source='https://api.bybit.com/v5/market/kline',
                       historical_response_sha256='f'*64,start_ms=0,end_ms=60000,
                       first_available_ms=0,last_available_ms=60000,coverage='OBSERVED_COMPLETE') for i in range(10)]
        result=adminit.validate_instruments(evidence,start_ms=0,end_ms=60000)
        self.assertEqual(result['count'],10)
        self.assertEqual(result['authenticity'],'UNVERIFIED')
        for mutate in (lambda x:x.pop(),lambda x:x[0].update(origin='SYNTHETIC'),
                       lambda x:x[0].update(symbol=x[1]['symbol']),
                       lambda x:x[0].update(last_available_ms=0),
                       lambda x:x[0].update(status='Settling')):
            bad=copy.deepcopy(evidence);mutate(bad)
            with self.assertRaises(ValueError):adminit.validate_instruments(bad,start_ms=0,end_ms=60000)

    def test_inventory_and_network_preparation_never_claim_actual_results(self):
        plan=self.plan()
        self.assertEqual(plan['inventory_status'],'NOT_RUN')
        self.assertEqual(plan['instruments_status'],'NOT_RUN')
        self.assertEqual(plan['rollback_policy'],'RESTORE_ONLY_TEST_NAMESPACE')
        self.assertIn('api.bybit.com',adminit.PUBLIC_NETWORK)

    def test_inventory_blocks_conflicts_missing_dependencies_and_resources(self):
        inventory=dict(node='ADMINIT',logical_processors=8,memory_bytes=16*1024**3,
                       free_bytes=50*1024**3,service_names=[],root_exists=False,
                       postgres_data_exists=False,linked_namespace=False,
                       os=dict(caption='Windows test',edition='48',build='26100',version='10.0',architecture='64-bit'),
                       dependencies={name:dict(path='C:\\Test\\'+name+'.exe',file_version='1.0') for name in ('python','node','postgres','git')})
        report=adminit.check_inventory(inventory)
        self.assertEqual(report['status'],'RECORDED_UNVERIFIED')
        self.assertFalse(report['deployment_authorized'])
        for key,value in [('logical_processors',1),('memory_bytes',0),('free_bytes',0),
                          ('service_names',['unifiedadminittest-grid']),('root_exists',True),
                          ('linked_namespace',True),('dependencies',{}),('os',{}),
                          ('dependencies',{name:None for name in ('python','node','postgres','git')})]:
            bad=copy.deepcopy(inventory);bad[key]=value
            with self.subTest(key=key):self.assertEqual(adminit.check_inventory(bad)['status'],'BLOCKED')

    def test_local_collector_has_no_remote_or_mutation_entry_points(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1]/'scripts/Collect-AdminitInventory.ps1').read_text()
        for forbidden in ('-ComputerName','Invoke-Command','Enter-PSSession','New-PSSession',
                          'ssh ','tailscale ','Start-Service','Stop-Service','New-Service',
                          'Remove-Item','Set-Content','Out-File','Start-Process'):
            self.assertNotIn(forbidden,source)
        self.assertIn('if ($args.Count -ne 0)',source)
        self.assertIn('ConvertTo-Json',source)

    def test_phase_record_requires_current_run_node_time_and_evidence(self):
        plan=self.plan()
        record=dict(phase='A',result='PASS',release_sha=plan['release_sha'],node='ADMINIT',
                    run_id=plan['run_id'],observed_at_ms=1000,evidence_sha256='c'*64,signature_sha256='d'*64)
        self.assertEqual(adminit.assess(plan,[record])['status'],'BLOCKED')
        for field,value in [('run_id','stale-run'),('node','PC4'),('observed_at_ms',True),
                            ('release_sha','e'*40),('evidence_sha256','bad'),('signature_sha256',None)]:
            bad=copy.deepcopy(record);bad[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):adminit.assess(plan,[bad])

    def test_collector_stops_before_link_descendants_and_never_searches_path(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1]/'scripts/Collect-AdminitInventory.ps1').read_text()
        self.assertNotIn('Get-Command',source)
        self.assertNotIn('Test-Path',source)
        self.assertIn("$drive.DriveType -ne 3",source)
        self.assertIn("function Get-LocalPathState",source)
        self.assertIn("return 'BLOCKED'",source)
        self.assertIn("if ($state -ne 'REGULAR')",source)
        self.assertIn('VersionInfo.FileVersion',source)
        self.assertIn('OSArchitecture',source)
        self.assertNotIn('foreach ($path in',source)
