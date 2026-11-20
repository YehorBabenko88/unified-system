"""Raw custody of retired v1 smoke only; runtime obligations remain HELD."""
import ast
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/"docs/migration/retired-terminan-smoke-20261121"
EXPECTED={".github/workflows/terminan-contract-smoke.yml":{"archive":"docs/migration/retired-terminan-smoke-20261121/raw/.github__workflows__terminan-contract-smoke.yml.txt","sha256":"643193327d79fdf727ba5fac8e6040e6513d3098a8a86749b0daf0c1240357dc","bytes":702},"scripts/verify_terminan_contract.py":{"archive":"docs/migration/retired-terminan-smoke-20261121/raw/scripts__verify_terminan_contract.py.txt","sha256":"d794241118a390cf21fbc504bf1359dde81bd86907c6922fd72220988aad041c","bytes":1211}}
class RetiredTerminanSmokeTests(unittest.TestCase):
 def test_original_raw_bytes_and_inventory_are_bound(self):
  inventory=json.loads((FOLDER/"inventory.json").read_bytes())
  self.assertEqual({m["source"]:{k:m[k] for k in ("archive","sha256","bytes")} for m in inventory["members"]},EXPECTED)
  for source,record in EXPECTED.items():
   raw=(ROOT/record["archive"]).read_bytes()
   self.assertEqual(len(raw),record["bytes"]);self.assertEqual(hashlib.sha256(raw).hexdigest(),record["sha256"])
 def test_three_original_assertions_remain_archived(self):
  raw=(ROOT/EXPECTED["scripts/verify_terminan_contract.py"]["archive"]).read_bytes();tree=ast.parse(raw)
  self.assertEqual(len([n for n in ast.walk(tree) if isinstance(n,ast.Assert)]),3)
  imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
  self.assertIn("terminan.consumer",imports)
 def test_removed_consumer_is_not_an_active_workflow(self):
  for source in EXPECTED:self.assertFalse((ROOT/source).exists())
  for path in (ROOT/".github/workflows").glob("*.yml"):
   self.assertNotIn("scripts.verify_terminan_contract",path.read_text(encoding="utf8"))
 def test_historical_pass_issues_no_runtime_acceptance(self):
  value=json.loads((FOLDER/"inventory.json").read_bytes())
  self.assertEqual(value["historical_assertions"],3);self.assertEqual(value["semantic_mapping"],"HELD")
  self.assertEqual(value["runtime_qualification"],"NOT_RUN");self.assertEqual(value["release_status"],"NO_GO")
  self.assertIs(value["execution_authority"],False);self.assertIs(value["trading_authorized"],False)
