import datetime as dt
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from unified_system.observer import ObserverStore,SourcePolicy,ObserverEngine,ObserverError
from unified_system.observer.notifications import MockNotificationTransport

NOW=dt.datetime(2026,11,11,21,tzinfo=dt.timezone.utc)
HEAD='8d7c3c321b8b0bd7704a92721c9549b778d053f6'

class ToggleSource:
    policy=SourcePolicy('source','snapshot',HEAD)
    fail=True
    def read(self,now):
        if self.fail:raise ObserverError('OFFLINE')
        return []

class SourceEpisodeTests(unittest.TestCase):
    def test_existing_fail_without_episode_migrates_without_duplicate_alert(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'state';store=ObserverStore(path)
            try:
                store.db.execute('DROP TABLE source_episodes')
                store.db.execute('INSERT INTO sources VALUES(?,?,?,?)',('source','FAIL',NOW.isoformat(),HEAD))
                store.enqueue('SOURCE_UNAVAILABLE','source','FAIL',HEAD,NOW)
                store.close();store=ObserverStore(path)
                source=ToggleSource();engine=ObserverEngine(store,[source])
                engine.poll_once(NOW+dt.timedelta(seconds=60))
                self.assertEqual(store.queue_counts()['PENDING'],1)
                source.fail=False;engine.poll_once(NOW+dt.timedelta(seconds=120))
                source.fail=True;engine.poll_once(NOW+dt.timedelta(seconds=180))
                self.assertEqual(store.queue_counts()['PENDING'],2)
            finally:store.close()

    def test_repeated_failure_same_episode_but_recovery_opens_new_alert(self):
        with tempfile.TemporaryDirectory() as root:
            store=ObserverStore(Path(root)/'state')
            source=ToggleSource();engine=ObserverEngine(store,[source])
            try:
                engine.poll_once(NOW);engine.poll_once(NOW+dt.timedelta(seconds=60))
                self.assertEqual(store.queue_counts()['PENDING'],1)
                source.fail=False;engine.poll_once(NOW+dt.timedelta(seconds=120))
                source.fail=True;engine.poll_once(NOW+dt.timedelta(seconds=180))
                self.assertEqual(store.queue_counts()['PENDING'],2)
            finally:store.close()

    def test_sent_compaction_and_restart_preserve_new_failure_episode(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'state';store=ObserverStore(path)
            source=ToggleSource();engine=ObserverEngine(store,[source])
            try:
                engine.poll_once(NOW)
                self.assertEqual(store.deliver_one(MockNotificationTransport(),NOW),'SENT')
                source.fail=False;engine.poll_once(NOW+dt.timedelta(seconds=60))
                with patch('unified_system.observer.store.MAX_EVENTS',2):
                    for index in range(2):
                        t=NOW+dt.timedelta(seconds=120+index*60)
                        store.enqueue('DAILY_SUMMARY','Summary '+str(index),'UNKNOWN',HEAD,t)
                        store.deliver_one(MockNotificationTransport(),t)
                store.close();store=ObserverStore(path)
                source.fail=True;ObserverEngine(store,[source]).poll_once(NOW+dt.timedelta(seconds=300))
                self.assertEqual(store.queue_counts()['PENDING'],1)
                events=store.snapshot(NOW+dt.timedelta(seconds=300))['events']
                self.assertEqual(len([e for e in events if e['kind']=='SOURCE_UNAVAILABLE' and e['delivery']=='PENDING']),1)
            finally:store.close()
