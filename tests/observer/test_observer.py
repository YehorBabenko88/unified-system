import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

NOW = dt.datetime(2026, 11, 11, 19, 0, tzinfo=dt.timezone.utc)
HEAD = 'bfa3b24d8f209d5e91acfa64819d3ebed4967af7'


class ObserverTests(unittest.TestCase):
    def setUp(self):
        if importlib.util.find_spec('unified_system.observer') is None:
            self.fail('Independent Observer implementation is absent')
        from unified_system import observer
        self.o = observer
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def policy(self, **extra):
        return self.o.SourcePolicy('fixture', 'snapshot', HEAD,
            admitted_axes=frozenset(('SSH_AUTHENTICATED', 'API_HEALTHY', 'RUN_STATUS',
                                     'AGENT_STATE', 'VERIFIED_PUBLICATION')),
            ttl_seconds=60, **extra)

    def raw(self, field='SSH_AUTHENTICATED', status='PASS', value=None, **changes):
        fact = dict(section='computers', subject='PC3', field=field,
                    status=status, scope=field, value=value)
        fact.update(changes)
        return json.dumps(dict(schema='unified.observer.source.v1', source_version=HEAD,
            observed_at=NOW.isoformat(), facts=[fact])).encode()

    def facts(self, **kwargs):
        return self.o.parse_snapshot(self.raw(**kwargs), self.policy(), NOW)

    def store(self):
        store = self.o.ObserverStore(self.root / 'state')
        self.addCleanup(store.close)
        return store

    def test_axes_are_independent_unknown_by_default(self):
        store = self.store(); store.ingest(self.facts(), NOW)
        node = store.snapshot(NOW)['computers']['PC3']
        self.assertEqual(node['SSH_AUTHENTICATED']['status'], 'PASS')
        self.assertEqual(node['LAN_REACHABLE']['status'], 'UNKNOWN')
        self.assertEqual(node['TOKEN_QUALIFIED']['status'], 'UNKNOWN')
        self.assertEqual(node['INSTALLED']['status'], 'UNKNOWN')
        self.assertEqual(node['PHYSICAL_ACCEPTED']['status'], 'UNKNOWN')

    def test_historical_pass_becomes_stale_with_last_success(self):
        store = self.store(); store.ingest(self.facts(), NOW)
        value = store.snapshot(NOW + dt.timedelta(seconds=61))['computers']['PC3']['SSH_AUTHENTICATED']
        self.assertEqual(value['status'], 'STALE')
        self.assertEqual(value['last_status'], 'PASS')
        self.assertIsNotNone(value['last_successful_observation'])

    def test_unqualified_pass_is_unknown(self):
        policy = self.o.SourcePolicy('fixture', 'snapshot', HEAD)
        facts = self.o.parse_snapshot(self.raw(), policy, NOW)
        self.assertEqual(facts[0].status, 'UNKNOWN')

    def test_synthetic_physical_pass_is_never_accepted(self):
        policy = self.o.SourcePolicy('fixture', 'a8_acceptance', HEAD,
            admitted_axes=frozenset(('PHYSICAL_ACCEPTED',)), mode='SYNTHETIC')
        fact = self.o.parse_snapshot(self.raw(field='PHYSICAL_ACCEPTED'), policy, NOW)[0]
        self.assertEqual(fact.status, 'BLOCKED')

    def test_local_unattested_never_promotes_to_committed(self):
        fact = self.facts(field='VERIFIED_PUBLICATION', value='LOCAL_UNATTESTED',
                          section='market_data', subject='datasets')[0]
        self.assertEqual(fact.status, 'BLOCKED')

    def test_future_naive_timestamp_wrong_head_and_duplicate_keys_rejected(self):
        original = json.loads(self.raw())
        for key, value in (('observed_at', '2026-11-11T19:00:00'),
                           ('observed_at', (NOW + dt.timedelta(minutes=1)).isoformat()),
                           ('source_version', 'a' * 40)):
            with self.subTest(key=key, value=value):
                raw = dict(original); raw[key] = value
                with self.assertRaises(self.o.ObserverError):
                    self.o.parse_snapshot(json.dumps(raw).encode(), self.policy(), NOW)
        with self.assertRaises(self.o.ObserverError):
            self.o.parse_snapshot(b'{"schema":1,"schema":2}', self.policy(), NOW)

    def test_wrong_axis_scope_does_not_grant_pass(self):
        self.assertEqual(self.facts(scope='LAN_REACHABLE')[0].status, 'UNKNOWN')

    def test_raw_input_digest_and_exact_version_are_retained(self):
        import hashlib
        raw = self.raw(); fact = self.o.parse_snapshot(raw, self.policy(), NOW)[0]
        self.assertEqual(fact.digest, hashlib.sha256(raw).hexdigest())
        self.assertEqual(fact.version, HEAD)
        self.assertEqual(fact.source, 'fixture')

    def test_out_of_order_observation_cannot_replace_current_failure(self):
        store = self.store(); store.ingest(self.facts(), NOW)
        raw = json.loads(self.raw(status='FAIL')); raw['observed_at'] = (NOW + dt.timedelta(seconds=1)).isoformat()
        newer = self.o.parse_snapshot(json.dumps(raw).encode(), self.policy(), NOW + dt.timedelta(seconds=1))
        store.ingest(newer, NOW + dt.timedelta(seconds=1)); store.ingest(self.facts(), NOW + dt.timedelta(seconds=2))
        self.assertEqual(store.snapshot(NOW + dt.timedelta(seconds=2))['computers']['PC3']['SSH_AUTHENTICATED']['status'], 'FAIL')

    def test_foreign_state_directory_is_not_modified(self):
        path = self.root / 'foreign'; path.mkdir(); (path / 'production.sqlite').write_bytes(b'KEEP')
        with self.assertRaises(self.o.ObserverError): self.o.ObserverStore(path)
        self.assertEqual(list(p.name for p in path.iterdir()), ['production.sqlite'])
        self.assertEqual((path / 'production.sqlite').read_bytes(), b'KEEP')

    def test_restart_preserves_facts_last_success_and_dedup(self):
        store = self.o.ObserverStore(self.root / 'state')
        store.ingest(self.facts(), NOW); store.enqueue('CI_FAILURE', 'unified-system', 'FAIL', HEAD, NOW)
        store.close(); reopened = self.o.ObserverStore(self.root / 'state'); self.addCleanup(reopened.close)
        self.assertEqual(reopened.snapshot(NOW)['computers']['PC3']['SSH_AUTHENTICATED']['status'], 'PASS')
        self.assertFalse(reopened.enqueue('CI_FAILURE', 'unified-system', 'FAIL', HEAD, NOW))
        self.assertEqual(reopened.queue_counts()['PENDING'], 1)

    def test_rate_limit_survives_restart_and_does_not_drop_queue(self):
        store = self.o.ObserverStore(self.root / 'state')
        for name in ('PC1', 'PC2'): store.enqueue('NEW_BLOCKER', name, 'BLOCKED', HEAD, NOW)
        transport = self.o.MockNotificationTransport()
        self.assertEqual(store.deliver_one(transport, NOW, minimum_interval=60), 'SENT')
        store.close(); reopened = self.o.ObserverStore(self.root / 'state'); self.addCleanup(reopened.close)
        self.assertEqual(reopened.deliver_one(transport, NOW + dt.timedelta(seconds=1), minimum_interval=60), 'RATE_LIMITED')
        self.assertEqual(reopened.queue_counts()['PENDING'], 1)
        self.assertEqual(reopened.deliver_one(transport, NOW + dt.timedelta(seconds=60), minimum_interval=60), 'SENT')

    def test_offline_notification_remains_queued_with_backoff(self):
        store = self.store(); store.enqueue('CI_FAILURE', 'unified-system', 'FAIL', HEAD, NOW)
        self.assertEqual(store.deliver_one(self.o.MockNotificationTransport('NOT_SENT'), NOW), 'NOT_SENT')
        self.assertEqual(store.queue_counts()['PENDING'], 1)
        self.assertEqual(store.deliver_one(self.o.MockNotificationTransport(), NOW), 'BACKOFF')

    def test_ambiguous_delivery_is_not_retried_after_restart(self):
        store = self.o.ObserverStore(self.root / 'state'); store.enqueue('CI_FAILURE', 'unified-system', 'FAIL', HEAD, NOW)
        self.assertEqual(store.deliver_one(self.o.MockNotificationTransport('UNKNOWN'), NOW), 'UNKNOWN')
        store.close(); reopened = self.o.ObserverStore(self.root / 'state'); self.addCleanup(reopened.close)
        self.assertEqual(reopened.deliver_one(self.o.MockNotificationTransport(), NOW + dt.timedelta(days=1)), 'EMPTY')
        self.assertEqual(reopened.queue_counts()['UNKNOWN'], 1)

    def test_inflight_crash_is_unknown_on_reopen(self):
        store = self.o.ObserverStore(self.root / 'state'); store.enqueue('CI_FAILURE', 'unified-system', 'FAIL', HEAD, NOW)
        store.claim_for_delivery(NOW, minimum_interval=60); store.close()
        reopened = self.o.ObserverStore(self.root / 'state'); self.addCleanup(reopened.close)
        self.assertEqual(reopened.queue_counts()['UNKNOWN'], 1)

    def test_private_subject_or_notification_data_is_rejected(self):
        store = self.store()
        for subject in ('192.168.2.104', 'C:/Users/private', 'token=SECRET', 'https://private.invalid'):
            with self.subTest(subject=subject):
                with self.assertRaises(self.o.ObserverError): store.enqueue('CI_FAILURE', subject, 'FAIL', HEAD, NOW)

    def test_dashboard_get_only_no_mutation_and_no_raw_source_disclosure(self):
        store = self.store(); store.ingest(self.facts(), NOW)
        app = self.o.ObserverApp(lambda: store.snapshot(NOW)); response = []
        body = b''.join(app({'REQUEST_METHOD':'GET', 'PATH_INFO':'/', 'QUERY_STRING':''}, lambda s,h:response.append((s,h))))
        self.assertTrue(response[0][0].startswith('200'))
        self.assertIn(b'Unified Observer Dashboard', body)
        for section in (b'Overview', b'Computers', b'Services', b'Market Data', b'Development', b'CI', b'Acceptance', b'Events'): self.assertIn(section, body)
        response.clear(); b''.join(app({'REQUEST_METHOD':'POST', 'PATH_INFO':'/api/status', 'QUERY_STRING':''}, lambda s,h:response.append((s,h))))
        self.assertTrue(response[0][0].startswith('405'))

    def test_source_file_offline_retains_stale_facts_not_new_online(self):
        path = self.root / 'source.json'; path.write_bytes(self.raw()); store = self.store()
        source = self.o.SnapshotSource(self.policy(), path)
        engine = self.o.ObserverEngine(store, [source]); engine.poll_once(NOW)
        path.unlink(); engine.poll_once(NOW + dt.timedelta(seconds=61))
        status = store.snapshot(NOW + dt.timedelta(seconds=61))
        self.assertEqual(status['computers']['PC3']['SSH_AUTHENTICATED']['status'], 'STALE')
        self.assertEqual(status['sources']['fixture']['status'], 'FAIL')

    def test_agent2_block_is_explicit_and_stale_never_means_resumed(self):
        store = self.store(); facts = self.facts(field='AGENT_STATE', status='BLOCKED', value='BLOCKED_COMMUNICATION', section='development', subject='Agent 2')
        store.ingest(facts, NOW); view = store.snapshot(NOW + dt.timedelta(seconds=61))
        value = view['development'][0]
        self.assertEqual(value['value'], 'BLOCKED_COMMUNICATION')
        self.assertEqual(value['status'], 'STALE')

    def test_duplicate_poll_does_not_duplicate_failure_notification(self):
        store = self.store(); facts = self.facts(field='RUN_STATUS', status='FAIL', value='FAILURE', section='ci', subject='unified-system')
        store.ingest(facts, NOW); store.ingest(facts, NOW)
        self.assertEqual(store.queue_counts()['PENDING'], 1)


if __name__ == '__main__': unittest.main(verbosity=2)
