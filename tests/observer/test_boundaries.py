import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from unified_system import observer as o

NOW = dt.datetime(2026, 11, 11, 19, tzinfo=dt.timezone.utc)
HEAD = 'bfa3b24d8f209d5e91acfa64819d3ebed4967af7'


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def store(self):
        store = o.ObserverStore(self.root / 'state'); self.addCleanup(store.close); return store

    def test_clock_rollback_cannot_make_future_stored_pass_online(self):
        policy = o.SourcePolicy('health', 'snapshot', HEAD, admitted_axes=frozenset(('API_HEALTHY',)))
        raw = json.dumps({'schema':'unified.observer.source.v1','source_version':HEAD,
            'observed_at':NOW.isoformat(),'facts':[{'section':'computers','subject':'LS5',
            'field':'API_HEALTHY','scope':'API_HEALTHY','status':'PASS','value':None}]}).encode()
        store = self.store(); store.ingest(o.parse_snapshot(raw, policy, NOW), NOW)
        self.assertEqual(store.snapshot(NOW - dt.timedelta(minutes=1))['computers']['LS5']['API_HEALTHY']['status'], 'UNKNOWN')

    def test_evidence_scope_cannot_disclose_secret_or_private_path(self):
        policy = o.SourcePolicy('health', 'snapshot', HEAD)
        for scope in ('token=SECRET', 'C:/Users/private', '192.168.2.104'):
            raw = json.dumps({'schema':'unified.observer.source.v1','source_version':HEAD,
                'observed_at':NOW.isoformat(),'facts':[{'section':'computers','subject':'LS5',
                'field':'API_HEALTHY','scope':scope,'status':'UNKNOWN','value':None}]}).encode()
            with self.subTest(scope=scope):
                with self.assertRaises(o.ObserverError): o.parse_snapshot(raw, policy, NOW)

    def test_credentials_in_identifier_are_rejected_before_persistence(self):
        for identity in ('ghp_' + 'x' * 36, 'sk-' + 'x' * 40, '123456:' + 'x' * 30):
            with self.subTest(identity=identity[:4]):
                with self.assertRaises(o.ObserverError): o.SourcePolicy(identity, 'snapshot', HEAD)

    def test_telegram_refuses_arbitrary_prefixed_private_message(self):
        token = '123456:' + 'x' * 30
        transport = o.TelegramTestTransport(token, '123', test_credentials_confirmed=True,
            network_admitted=True, request=lambda body:b'{"ok":true}')
        with self.assertRaises(o.ObserverError): transport.send('Unified Observer: token=SECRET at 192.168.2.104')

    def test_telegram_mock_request_proves_payload_not_live_delivery(self):
        payloads = []; token = '123456:' + 'x' * 30
        transport = o.TelegramTestTransport(token, '123', test_credentials_confirmed=True,
            network_admitted=True, request=lambda body:(payloads.append(json.loads(body)) or b'{"ok":true}'))
        self.assertEqual(transport.send('Unified Observer: CI_FAILURE | unified-system | FAIL | source bfa3b24'), 'SENT')
        self.assertEqual(payloads[0]['chat_id'], '123')
        self.assertNotIn(token, repr(transport)); self.assertNotIn(token, json.dumps(payloads))
        with self.assertRaises(o.ObserverError): o.TelegramTestTransport(token, '123')

    def test_telegram_ambiguous_response_remains_unknown(self):
        def lost(_): raise TimeoutError('PRIVATE_URL_WITH_TOKEN')
        transport = o.TelegramTestTransport('123456:' + 'x' * 30, '123',
            test_credentials_confirmed=True, network_admitted=True, request=lost)
        self.assertEqual(transport.send('Unified Observer: CI_FAILURE | unified-system | FAIL | source bfa3b24'), 'UNKNOWN')

    def test_github_adapter_retains_exact_target_head_and_original_input_digest(self):
        raw = json.dumps({'workflow_runs':[{'id':42,'head_sha':'a'*40,'status':'completed','conclusion':'failure'}]}).encode()
        urls = []
        class Client:
            def get(self, url): urls.append(url); return raw
        policy = o.SourcePolicy('github-unified', 'github', HEAD,
            admitted_axes=frozenset(('RUN_STATUS',)), mode='UNQUALIFIED')
        source = o.GitHubSource(policy, 'YehorBabenko88/unified-system', client=Client())
        facts = source.read(NOW)
        self.assertEqual(facts[0].version, 'a'*40)
        self.assertEqual(facts[0].digest, hashlib.sha256(raw).hexdigest())
        self.assertEqual(facts[0].status, 'FAIL')
        self.assertEqual(len(urls), 1); self.assertIn('/actions/runs?', urls[0])
        with self.assertRaises(o.ObserverError): o.GitHubSource(policy, 'YehorBabenko88/unified-system').read(NOW)

    def test_network_transport_requires_admission_and_exact_get_source_urls(self):
        with self.assertRaises(o.ObserverError): o.ReadOnlyHTTPS(frozenset(('https://api.github.com/user',)))
        with self.assertRaises(o.ObserverError): o.ReadOnlyHTTPS(frozenset(('https://api.bybit.com/v5/market/time',)), network_admitted=True)
        with self.assertRaises(o.ObserverError): o.ReadOnlyHTTPS(frozenset(('https://api.github.com/user',)), network_admitted=True)

    def test_supervisor_available_unverified_is_not_node_admission(self):
        policy = o.SourcePolicy('supervisor', 'supervisor_status', HEAD,
            admitted_axes=frozenset(('API_HEALTHY',)))
        raw = json.dumps({'producer':'unified-system','read_only':True,'status':'AVAILABLE',
            'provenance':'UNVERIFIED','trading_authorized':False,'physical_acceptance':'NOT_RUN'}).encode()
        facts = o.SupervisorStatusSource(policy, reader=lambda:raw).read(NOW)
        self.assertEqual(facts[0].status, 'UNKNOWN')
        self.assertEqual(facts[0].scope, 'UNVERIFIED_CONTROL_PLANE_OBSERVATION')

    def test_mission_projection_is_export_read_only_never_sqlite(self):
        source = self.root / 'mission-export.json'
        raw = json.dumps({'schema':'unified.observer.mission-export.v1','source_version':HEAD,
            'observed_at':NOW.isoformat(),'projection':{'sequence':273,'tasks':{'Root':{'status':'COMPLETE'}}}}).encode()
        source.write_bytes(raw)
        policy = o.SourcePolicy('mission', 'mission_projection', HEAD)
        facts = o.MissionProjectionSource(policy, source).read(NOW)
        self.assertEqual(source.read_bytes(), raw)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['mission-export.json'])
        self.assertEqual(facts[0].value, 273); self.assertEqual(facts[0].status, 'UNKNOWN')

    def test_source_and_poll_bounds_fail_closed(self):
        policy = o.SourcePolicy('source', 'snapshot', HEAD)
        with self.assertRaises(o.ObserverError): o.SourcePolicy('source', 'snapshot', HEAD, interval_seconds=1)
        with self.assertRaises(o.ObserverError): o.ObserverEngine(self.store(), [o.SnapshotSource(policy, self.root/'x')] * 17)
        with self.assertRaises(o.ObserverError): o.parse_snapshot(b'x' * 1048577, policy, NOW)

    def test_health_reports_unavailable_when_own_state_provider_fails(self):
        def failed(): raise o.ObserverError('OWN_STATE_UNAVAILABLE')
        response = []; app = o.ObserverApp(failed)
        body = b''.join(app({'REQUEST_METHOD':'GET','PATH_INFO':'/healthz','QUERY_STRING':''}, lambda s,h:response.append(s)))
        self.assertTrue(response[0].startswith('503'))
        self.assertNotIn(b'OWN_STATE', body)

    def test_foreground_cli_exists_independently_from_codex(self):
        self.assertIsNotNone(importlib.util.find_spec('unified_system.observer.__main__'))

    def test_daily_summary_deduplicates_same_day(self):
        store = self.store(); engine = o.ObserverEngine(store, [])
        self.assertTrue(engine.daily_summary(NOW, HEAD))
        self.assertFalse(engine.daily_summary(NOW + dt.timedelta(hours=1), HEAD))
        self.assertTrue(engine.daily_summary(NOW + dt.timedelta(days=1), HEAD))

    def test_github_query_is_small_and_explicitly_bounded(self):
        policy=o.SourcePolicy('github','github',HEAD)
        self.assertTrue(o.GitHubSource(policy,'YehorBabenko88/unified-system').url.endswith('per_page=10'))

    def test_ci_retention_is_bounded_without_erasing_node_last_success(self):
        store=self.store();policy=o.SourcePolicy('github','github',HEAD,admitted_axes=frozenset(('RUN_STATUS',)))
        for i in range(32):
            raw=json.dumps({'schema':'unified.observer.source.v1','source_version':HEAD,
                'observed_at':(NOW+dt.timedelta(seconds=i)).isoformat(),'facts':[{'section':'ci',
                'subject':'unified-system#'+str(i),'field':'RUN_STATUS','scope':'RUN_STATUS','status':'PASS','value':'SUCCESS'}]}).encode()
            store.ingest(o.parse_snapshot(raw,policy,NOW+dt.timedelta(seconds=i)),NOW+dt.timedelta(seconds=i))
        rows=store.snapshot(NOW+dt.timedelta(seconds=32))['ci']
        self.assertLessEqual(len(rows),16);self.assertIn('unified-system#31',{r['subject'] for r in rows})

    def test_stop_prevents_starting_another_source(self):
        calls=[];engine=None
        class Source:
            def __init__(self,name):self.policy=o.SourcePolicy(name,'snapshot',HEAD)
            def read(self,now):
                calls.append(self.policy.source_id)
                engine.stop()
                return []
        engine=o.ObserverEngine(self.store(),[Source('first'),Source('second')])
        engine.poll_once(NOW)
        self.assertEqual(calls,['first'])

    def test_mission_export_progress_counts_do_not_grant_runtime(self):
        path=self.root/'mission.json'
        projection={'sequence':277,'tasks':{'ROOT.LEVEL2.LS5':{'axes':{
            'source':'PASS','tested':'PASS','integrated':'BLOCKED','windows':'UNKNOWN','physical':'BLOCKED'}}},
            'continuations':{'ROOT.LEVEL2.LS5':{'metadata':{'status':'BLOCKED','source_head':HEAD,
                'next_executable_step':{'step_id':'OFFLINE_IMPORT_GATE','description':'PRIVATE_DIAGNOSTIC'},
                'evidence':[{'reference':'C:/Users/private','sha256':'a'*64}],
                'required_authorization':['PRIVATE_OPERATOR_DETAIL']}}}}
        path.write_text(json.dumps({'schema':'unified.observer.mission-export.v1',
            'source_version':HEAD,'observed_at':NOW.isoformat(),'projection':projection}))
        facts=o.MissionProjectionSource(o.SourcePolicy('mission','mission_projection',HEAD),path).read(NOW)
        self.assertEqual(len(facts),2)
        value=facts[1].value
        self.assertEqual(value['task_count'],1);self.assertEqual(value['continuation_counts']['BLOCKED'],1)
        self.assertEqual(value['root_task']['next_milestone'],'OFFLINE_IMPORT_GATE')
        self.assertEqual(value['root_task']['evidence_sha256'],'a'*64)
        self.assertEqual(facts[1].status,'UNKNOWN')
        self.assertNotIn('PRIVATE',json.dumps(value));self.assertNotIn('C:/',json.dumps(value))

    def test_mission_export_continuation_sequence_mismatch_is_rejected(self):
        path=self.root/'mission.json'
        path.write_text(json.dumps({'schema':'unified.observer.mission-export.v1',
            'source_version':HEAD,'observed_at':NOW.isoformat(),
            'projection':{'sequence':277,'tasks':{},'continuation_sequence':276,'continuations':{}}}))
        with self.assertRaises(o.ObserverError):
            o.MissionProjectionSource(o.SourcePolicy('mission','mission_projection',HEAD),path).read(NOW)


if __name__ == '__main__': unittest.main(verbosity=2)
