import json
from pathlib import Path
import unittest
from unified_system.control_mux.codec import encode, decode, validate

ROOT=Path(__file__).resolve().parents[2]/'release/contracts/control-mux-closed-review4'
class CodecTests(unittest.TestCase):
    def test_frozen_valid_vectors(self):
        for value in json.loads((ROOT/'vectors.json').read_bytes())['valid'].values():
            self.assertEqual(decode(encode(value)),value)
    def test_numeric_aliases_and_noncanonical_rejected(self):
        for raw in (b'{"x":1}',b'{"x":1.0}',b'{"x":-0}',b' {}',b'{"x":"a","x":"b"}',b'{"x":"\\u0061"}'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):decode(raw)
    def test_depth_and_host_types(self):
        for value in (1,1.0,("x",),{1:'x'},set()):
            with self.subTest(value=repr(value)),self.assertRaises(ValueError):encode(value)
        with self.assertRaises(ValueError):decode(b'['*13+b']'*13)
    def test_schema_specific(self):
        body=json.loads((ROOT/'vectors.json').read_bytes())['valid']['open_body']
        validate('open_request',body)
        with self.assertRaises(ValueError):validate('open_request',dict(body,extra=True))
if __name__=='__main__':unittest.main()
