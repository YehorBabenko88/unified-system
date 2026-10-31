import copy
import unittest

from unified_system.contracts import ContractError
from unified_system.installer import plan
from unified_system.lockfile import validate_lock
from unified_system.registry import negotiate


IDS = ('unified-system', 'grid', 'strattester', 'math', 'meta_analyse', 'terminan')


def release_lock():
    return {'lock_version': 1, 'modules': [
        {'descriptor': {'module_id': name, 'api_major': 1, 'api_minor': 0,
                        'source_sha': 'a' * 64, 'capabilities': ['read_only_health']},
         'artifact_sha256': 'b' * 64}
        for name in IDS]}


class SixModuleReleaseTests(unittest.TestCase):
    def test_every_module_can_negotiate(self):
        for item in release_lock()['modules']:
            d = item['descriptor']
            with self.subTest(module=d['module_id']):
                self.assertEqual(negotiate(d, expected_id=d['module_id'])['module_id'], d['module_id'])

    def test_complete_release_is_installable_without_removing_independent_modules(self):
        lock = release_lock()
        self.assertEqual(validate_lock(lock), tuple(sorted(IDS)))
        result = plan(lock, installed=('math', 'meta_analyse'))
        self.assertEqual(result['would_install'], sorted(set(IDS) - {'math', 'meta_analyse'}))
        self.assertEqual(result['already_present'], ['math', 'meta_analyse'])
        self.assertEqual(result['would_remove'], [])
        self.assertFalse(result['mutations_performed'])

    def test_duplicate_and_unknown_still_rejected(self):
        for name in ('math', 'unrecognized'):
            lock = release_lock()
            extra = copy.deepcopy(lock['modules'][0])
            extra['descriptor']['module_id'] = name
            # Stay inside the roster bound so this exercises identity checks.
            lock['modules'][0] = extra
            with self.subTest(name=name), self.assertRaises(ContractError):
                validate_lock(lock)

    def test_capability_has_one_owner(self):
        from unified_system.module_catalog import MODULE_IDS, OWNER_CAPABILITIES
        self.assertEqual(set(MODULE_IDS), set(IDS))
        self.assertEqual(set(OWNER_CAPABILITIES), set(IDS))
        capabilities = [c for xs in OWNER_CAPABILITIES.values() for c in xs]
        self.assertEqual(len(capabilities), len(set(capabilities)))
        self.assertIn('backtesting', OWNER_CAPABILITIES['strattester'])
        self.assertIn('release_orchestration', OWNER_CAPABILITIES['unified-system'])
        self.assertIn('microstructure_analytics', OWNER_CAPABILITIES['meta_analyse'])


if __name__ == '__main__':
    unittest.main()
