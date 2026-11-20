"""Retired source routes cannot reach the protected service entry."""
import unittest
from unified_system import service_entry
from unified_system import service_bootstrap

class RetiredServiceRouteTests(unittest.TestCase):
    def test_retired_routes_are_rejected_before_platform_or_application_imports(self):
        for args in (['--data-first-worker'], ['--data-first-research'], ['--module-source','grid'], ['--module-source','strattester']):
            with self.subTest(args=args):
                self.assertFalse(service_entry._valid_arguments(args))
    def test_only_canonical_closed_module_routes_are_valid(self):
        for args in ([], ['--module-source','market_data'], ['--module-source','terminan']):
            self.assertTrue(service_entry._valid_arguments(args))
        self.assertFalse(service_entry._valid_arguments(['--module-source','math']))
    def test_retired_bootstrap_dispatchers_are_absent(self):
        self.assertFalse(hasattr(service_bootstrap,'run_protected_data_first'))
        self.assertFalse(hasattr(service_bootstrap,'run_protected_data_first_worker'))
