import tempfile
import unittest
from pathlib import Path
from scripts.operator_contract_ci import REQUIRED_CASES, validate_junit, require_pin


class EvidenceTests(unittest.TestCase):
    def test_only_exact_grid_pin_admitted(self):
        require_pin('55e74863c3c28bf4cbcb4ded4d3359f98bf93f71')
        with self.assertRaises(ValueError): require_pin('0'*40)
    def test_inventory_requires_every_unique_case_no_skip_or_failure(self):
        def xml(cases,extra=''):
            return '<testsuites><testsuite>'+''.join(
                '<testcase classname="'+c+'" name="'+n+'">'+extra+'</testcase>' for c,n in cases)+'</testsuite></testsuites>'
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'results.xml'
            path.write_text(xml(REQUIRED_CASES));self.assertEqual(validate_junit(path),32)
            for content in (xml(REQUIRED_CASES[:-1]),xml(REQUIRED_CASES+[REQUIRED_CASES[0]]),
                            xml(REQUIRED_CASES,'<skipped/>'),xml(REQUIRED_CASES,'<failure/>')):
                path.write_text(content)
                with self.assertRaises(ValueError):validate_junit(path)
