"""Pure inventory regressions; no project or fixture imports, no discovery cases."""
import unittest


def make_suite(validator, groups):
    """Exercise the actual qualifier validator supplied by its owner."""
    expected = tuple(item for group in groups for item in group)

    class InventoryControls(unittest.TestCase):
        def test_exact_groups_preserve_17_plus_5(self):
            self.assertEqual(tuple(map(len, groups)), (17, 5))
            self.assertEqual(len(set(expected)), 22)
            self.assertEqual(validator(list(reversed(expected))), tuple(sorted(expected)))

        def test_missing_original_case_denied(self):
            for case in groups[0]:
                with self.subTest(case=case), self.assertRaisesRegex(RuntimeError, 'EXACT_CASES'):
                    validator([item for item in expected if item != case])

        def test_missing_fixed_case_denied(self):
            for case in groups[1]:
                with self.subTest(case=case), self.assertRaisesRegex(RuntimeError, 'EXACT_CASES'):
                    validator([item for item in expected if item != case])

        def test_extra_case_denied(self):
            with self.assertRaisesRegex(RuntimeError, 'EXACT_CASES'):
                validator(list(expected) + ['unexpected.Test.test_extra'])

        def test_duplicate_case_denied(self):
            for case in (groups[0][0], groups[1][0]):
                with self.subTest(case=case), self.assertRaisesRegex(RuntimeError, 'DUPLICATE_CASES'):
                    validator(list(expected) + [case])

        def test_same_count_substitution_denied(self):
            for index in (0, 17):
                changed = list(expected)
                changed[index] = 'unexpected.Test.test_substitution'
                with self.subTest(index=index), self.assertRaisesRegex(RuntimeError, 'EXACT_CASES'):
                    validator(changed)

    return unittest.defaultTestLoader.loadTestsFromTestCase(InventoryControls)
