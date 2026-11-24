import copy
import unittest

from unified_system.contracts import ContractError
from unified_system.installer import plan
from unified_system.lockfile import validate_lock
from unified_system.registry import negotiate


IDS = ('unified_system', 'market_data', 'math', 'terminan')


def release_lock():
    return {'lock_version': 2, 'modules': [
        {'descriptor': {'module_id': name, 'api_major': 1, 'api_minor': 0,
                        'source_sha': 'a' * 64, 'capabilities': ['read_only_health']},
         'artifact_sha256': 'b' * 64}
        for name in IDS]}


class FourModuleReleaseTests(unittest.TestCase):
    def test_every_module_can_negotiate(self):
        for item in release_lock()['modules']:
            d = item['descriptor']
            with self.subTest(module=d['module_id']):
                self.assertEqual(negotiate(d, expected_id=d['module_id'])['module_id'], d['module_id'])

    def test_complete_release_is_installable_without_removing_independent_modules(self):
        lock = release_lock()
        self.assertEqual(validate_lock(lock), tuple(sorted(IDS)))
        result = plan(lock, installed=('math', 'terminan'))
        self.assertEqual(result['would_install'], sorted(set(IDS) - {'math', 'terminan'}))
        self.assertEqual(result['already_present'], ['math', 'terminan'])
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
        self.assertIn('backtesting', OWNER_CAPABILITIES['terminan'])
        self.assertIn('release_orchestration', OWNER_CAPABILITIES['unified_system'])
        self.assertIn('microstructure_analytics', OWNER_CAPABILITIES['terminan'])
        self.assertIn('market_capture', OWNER_CAPABILITIES['market_data'])

    def test_retired_identities_never_negotiate_or_install(self):
        for retired in ('grid', 'strattester', 'meta_analyse', 'unified-system'):
            descriptor = dict(release_lock()['modules'][0]['descriptor'], module_id=retired)
            with self.subTest(retired=retired), self.assertRaises(ContractError):
                negotiate(descriptor, expected_id=retired)

    def test_retired_identities_cannot_return_as_runtime_extensions(self):
        from unified_system.runtime import ModuleSpec, _valid
        for retired in ('grid', 'strattester', 'meta_analyse', 'unified-system'):
            with self.subTest(retired=retired), self.assertRaises(ValueError):
                _valid(ModuleSpec(retired, '1.0.0'))


if __name__ == '__main__':
    unittest.main()
