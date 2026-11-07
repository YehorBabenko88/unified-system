import copy,hashlib,json,unittest
from pathlib import Path
from unified_system.control_mux.codec import encode,decode
from unified_system.control_mux.reconciliation import encode_document,require_fit,build_document
ROOT=Path(__file__).resolve().parents[2]
class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.cases=json.loads((ROOT/'docs/control-mux/contracts/reconciliation-v3-review2.vectors.json').read_bytes())['cases']
    def test_all24_exact_review2_semantics(self):
        self.assertEqual(len(self.cases),24)
        for case in self.cases:
            with self.subTest(case=case['name']):
                if case['accepted']:self.assertEqual(decode(encode_document(case['value'])),case['value'])
                else:
                    with self.assertRaises(ValueError):encode_document(case['value'])
    def test_original201_202_204_bytes_and_inputs_unchanged(self):
        for case in self.cases:
            if not case['accepted']:continue
            value=copy.deepcopy(case['value']);before=encode(value);raw=encode_document(value)
            self.assertEqual(encode(value),before)
            self.assertEqual(decode(raw)['original_result_ascii'].encode(),value['original_result_ascii'].encode())
            self.assertLessEqual(len(raw),16384)
    def test_max_index_preflight_is_size_only_no_result_or_mutation(self):
        for case in self.cases:
            if not case['accepted']:continue
            v=copy.deepcopy(case['value']);before=encode(v)
            self.assertIsNone(require_fit(v['cluster_id'],v['original_preimage'],v['original_body_ascii'].encode(),v['receipt'],v['original_result_ascii'].encode()))
            self.assertEqual(encode(v),before)
    def test_full_wrapper_cap_is_checked_without_truncation(self):
        v=copy.deepcopy(self.cases[0]['value']);v['original_result_ascii']='x'*16384
        with self.assertRaisesRegex(ValueError,'WRAPPER_CAP'):encode_document(v)
        self.assertEqual(len(v['original_result_ascii']),16384)
    def test_observed_index_type_and_positive_u63_required(self):
        v=self.cases[0]['value']
        for index in (True,False,None,'7',0,-1,2**63):
            with self.assertRaises(ValueError):build_document(v['cluster_id'],v['query_request_id'],v['original_preimage'],v['original_body_ascii'].encode(),v['receipt'],v['original_result_ascii'].encode(),index)
if __name__=='__main__':unittest.main()
