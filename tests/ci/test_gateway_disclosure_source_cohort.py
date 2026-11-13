"""Pure source cohort checks; never import owner/PKI fixtures or open sockets."""
import ast
import hashlib
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT/'tests/storage/gateway_disclosure/support_owner.py'


def pin(name):
    tree = ast.parse(HELPER.read_bytes())
    values = [node.value.value for node in tree.body if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
              and isinstance(node.value, ast.Constant) and type(node.value.value) is str]
    if len(values) != 1: raise AssertionError('ambiguous source pin')
    return values[0]


def raw(path):
    if path.is_symlink() or path.stat().st_nlink != 1: raise AssertionError('not unique regular source')
    value = path.read_bytes()
    if b'\r' in value: raise AssertionError('source cohort requires exact canonical LF bytes')
    return value


class GatewayDisclosureSourceCohort(unittest.TestCase):
    def test_production_identity_matches_unchanged_primary_blob(self):
        value = raw(ROOT/'unified_system/gateway_identity.py')
        self.assertEqual(hashlib.sha256(value).hexdigest(), pin('IDENTITY_SHA'))
        self.assertEqual(pin('IDENTITY_SHA'), '84093865e8477ef6562100d41137922785446c9cb4e024c9ba7105593a2b36c1')
        self.assertEqual(hashlib.sha1(b'blob '+str(len(value)).encode()+b'\0'+value).hexdigest(),
                         'f81ede7ddd6973a544968922c1db20c7b056a286')

    def test_fixture_provisioning_pin_matches_reviewed_primary_blob(self):
        value = raw(ROOT/'tests/test_gateway_identity.py')
        self.assertEqual(hashlib.sha1(b'blob '+str(len(value)).encode()+b'\0'+value).hexdigest(),
                         '3e45a107ff924122cfdf20678b1d4a3b20afd255')
        self.assertEqual(hashlib.sha256(value).hexdigest(), pin('FIXTURE_SHA'))

    def test_disclosure_loader_guards_and_module_path_are_preserved(self):
        source = raw(HELPER).decode('utf-8')
        tree = ast.parse(source)
        function, = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'load_owner']
        # Exact function bytes, independent of Python-version ast.dump formatting.
        digest = hashlib.sha256(ast.get_source_segment(source, function).encode('utf-8')).hexdigest()
        self.assertEqual(digest, '3d9b5fd577164a8190b5e5cb81a2996a65aff34e5733f46a99e1dccb04bd1de0')
        literals = {node.value for node in ast.walk(function)
                    if isinstance(node, ast.Constant) and type(node.value) is str}
        self.assertIn('unified_system.gateway_identity', literals)
        self.assertIn('OWNER_SOURCE_NOT_PROVISIONED', literals)
        self.assertIn('OWNER_CANONICAL_MODULE_MISMATCH', literals)


if __name__ == '__main__': unittest.main(verbosity=2)
