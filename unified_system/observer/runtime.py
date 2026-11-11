"""Serial observation loop. No task execution or repair operations."""
from datetime import datetime, timedelta, timezone
import json
import signal
import threading

from .model import ObserverError, SourcePolicy, label, need, stamp, utc


class ObserverEngine:
    def __init__(self, store, sources, *, transport=None):
        need(type(sources) is list and len(sources) <= 16 and
             all(type(s.policy) is SourcePolicy for s in sources), 'SOURCE_COUNT_BOUND')
        need(len({s.policy.source_id for s in sources}) == len(sources), 'DUPLICATE_SOURCE')
        self.store, self.sources, self.transport = store, sources, transport
        self.stop_event = threading.Event()

    def poll_once(self, now):
        now = utc(now); previous = self.store.snapshot(now)['sources']; outcomes = {}
        for source in self.sources:
            if self.stop_event.is_set(): break
            policy = source.policy; prior = previous.get(policy.source_id)
            if prior and now < utc(prior['observed_at']) + timedelta(seconds=policy.interval_seconds):
                outcomes[policy.source_id] = 'NOT_DUE'; continue
            try:
                facts = source.read(now)
                self.store.ingest(facts, now)
                self.store.record_source(policy.source_id, 'PASS', now, policy.source_version)
                outcomes[policy.source_id] = 'OBSERVED'
            except Exception:
                # Never persist source exception text, URLs, body or credentials.
                self.store.record_source(policy.source_id, 'FAIL', now, policy.source_version)
                self.store.enqueue('SOURCE_UNAVAILABLE', policy.source_id, 'FAIL', policy.source_version, now)
                outcomes[policy.source_id] = 'UNAVAILABLE'
        if self.transport is not None:
            self.store.deliver_one(self.transport, now)
        return outcomes

    def daily_summary(self, now, source_version):
        return self.store.enqueue('DAILY_SUMMARY', 'Progress ' + utc(now).date().isoformat(),
                                  'UNKNOWN', source_version, now)

    def run_forever(self, *, clock=None, interval=15):
        need(type(interval) is int and 15 <= interval <= 3600, 'POLL_INTERVAL_BOUND')
        clock = clock or (lambda: datetime.now(timezone.utc))
        while not self.stop_event.is_set():
            self.poll_once(clock())
            self.stop_event.wait(interval)

    def stop(self):
        self.stop_event.set()


def sources_from_config(config):
    """Offline configuration only; live clients need explicit programmatic admission."""
    from pathlib import Path
    from .sources import MissionProjectionSource, SnapshotSource
    need(type(config) is dict and set(config) == {'schema', 'sources'} and
         config['schema'] == 'unified.observer.config.v1' and type(config['sources']) is list and
         len(config['sources']) <= 16, 'OBSERVER_CONFIG')
    sources = []
    for row in config['sources']:
        need(type(row) is dict and set(row) <= {'id', 'kind', 'path', 'source_version', 'admitted_axes',
             'ttl_seconds', 'interval_seconds', 'mode'} and {'id', 'kind', 'path', 'source_version'} <= set(row), 'SOURCE_CONFIG')
        need(row['kind'] in ('snapshot', 'mission_projection', 'storage_status', 'node_health', 'a8_acceptance'),
             'CONFIG_NETWORK_SOURCES_NOT_ADMITTED')
        policy = SourcePolicy(row['id'], row['kind'], row['source_version'],
            admitted_axes=frozenset(row.get('admitted_axes', [])),
            ttl_seconds=row.get('ttl_seconds', 300), interval_seconds=row.get('interval_seconds', 60),
            mode=row.get('mode', 'UNQUALIFIED'))
        source = MissionProjectionSource if policy.kind == 'mission_projection' else SnapshotSource
        sources.append(source(policy, Path(row['path'])))
    return sources
