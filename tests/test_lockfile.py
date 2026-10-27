import json
import unittest
from unified_system.lockfile import validate_lock,parse_lock
from unified_system.installer import plan
from unified_system.contracts import ContractError

def fixture():
    return {"lock_version":1,"modules":[{"descriptor":{"module_id":"grid","api_major":1,"api_minor":0,"source_sha":"a"*64,"capabilities":["read_only_health"]},"artifact_sha256":"b"*64}]}

class LockTests(unittest.TestCase):
    def test_valid(self):self.assertEqual(validate_lock(fixture()),("grid",))
    def test_dry_run(self):
        result=plan(fixture())
        self.assertEqual(result["would_install"],["grid"])
        self.assertFalse(result["mutations_performed"])
    def test_duplicate(self):
        x=fixture();x["modules"].append(x["modules"][0])
        with self.assertRaises(ContractError):validate_lock(x)
    def test_bad_hash(self):
        x=fixture();x["modules"][0]["artifact_sha256"]="invalid"
        with self.assertRaises(ContractError):validate_lock(x)
    def test_nan(self):
        with self.assertRaises(ContractError):parse_lock('{"lock_version":1,"modules":[],"extra":NaN}')
    def test_size(self):
        with self.assertRaises(ContractError):parse_lock(" "*65537)
    def test_unknown_installed(self):
        with self.assertRaises(ValueError):plan(fixture(),("mystery",))
    def test_roundtrip(self):self.assertEqual(parse_lock(json.dumps(fixture())),fixture())

if __name__=="__main__":unittest.main()
