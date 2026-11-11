import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unified_system.observer.store import ObserverStore
from unified_system.observer.model import ObserverError
from unified_system.observer.sources import ReadOnlyHTTPS

NOW = dt.datetime(2026, 11, 11, 20, tzinfo=dt.timezone.utc)

class GitHubBudgetTests(unittest.TestCase):
    def test_native_client_requires_persistent_budget_and_parses_provider_cooldown(self):
        urls = frozenset(('https://api.github.com/repos/YehorBabenko88/unified-system/actions/runs?per_page=10',))
        with self.assertRaises(ObserverError): ReadOnlyHTTPS(urls, network_admitted=True)
        with tempfile.TemporaryDirectory() as root:
            store = ObserverStore(Path(root)/'state')
            try:
                client = ReadOnlyHTTPS(urls, network_admitted=True, budget_store=store, clock=lambda: NOW)
                client._cooldown({'Retry-After':'7200', 'X-RateLimit-Reset':'invalid'})
                with self.assertRaises(ObserverError): store.reserve_github('other', NOW+dt.timedelta(seconds=7199))
                store.reserve_github('other', NOW+dt.timedelta(seconds=7200))
            finally: store.close()
    def test_global_fifty_reservations_persist_across_restart(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'state'
            store = ObserverStore(path)
            for index in range(50):
                store.reserve_github('source-'+str(index), NOW)
            with self.assertRaises(ObserverError): store.reserve_github('source-next', NOW)
            store.close(); store = ObserverStore(path)
            try:
                with self.assertRaises(ObserverError): store.reserve_github('source-next', NOW)
                store.reserve_github('source-next', NOW+dt.timedelta(seconds=3601))
            finally: store.close()

    def test_same_source_waits_fifteen_minutes_even_after_restart(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'state'; store = ObserverStore(path)
            store.reserve_github('same', NOW); store.close(); store = ObserverStore(path)
            try:
                with self.assertRaises(ObserverError): store.reserve_github('same', NOW+dt.timedelta(seconds=899))
                store.reserve_github('same', NOW+dt.timedelta(seconds=900))
            finally: store.close()

    def test_cooldown_and_clock_rollback_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            store = ObserverStore(Path(root)/'state')
            try:
                store.reserve_github('a', NOW)
                store.cooldown_github(NOW, 7200)
                with self.assertRaises(ObserverError): store.reserve_github('b', NOW+dt.timedelta(seconds=3601))
                with self.assertRaises(ObserverError): store.reserve_github('b', NOW-dt.timedelta(days=1))
                store.reserve_github('b', NOW+dt.timedelta(seconds=7200))
            finally: store.close()
