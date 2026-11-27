import json
from pathlib import Path
import unittest
from unified_system.control_mux.commands import AdmittedContext, prepare_open
from unified_system.control_mux.codec import encode
ROOT=Path(__file__).resolve().parents[2]/'release/contracts/control-mux-closed-review4'
class CommandTests(unittest.TestCase):
    def test_frozen_preimages(self):
        v=json.loads((ROOT/'hash-preimages.json').read_bytes())
        context=AdmittedContext('22222222-2222-4222-8222-222222222222','operator1','session1','owner1','OPERATOR_CONTROL','policy1','1',frozenset({'OPEN_CONNECTION'}),object())
        command=prepare_open(context,v['canonical_body_ascii'].encode(),'11111111-1111-4111-8111-111111111111','command1')
        self.assertEqual(command.digest,v['command_digest'])
        self.assertEqual(command.key_sha256,v['command_key_sha256'])
        self.assertEqual(command.body,v['canonical_body_ascii'].encode())
    def test_request_id_and_rbac_rejected(self):
        body=json.loads((ROOT/'vectors.json').read_bytes())['valid']['open_body']
        context=AdmittedContext('22222222-2222-4222-8222-222222222222','operator1','session1','owner1','OPERATOR_CONTROL','policy1','1',frozenset(),object())
        with self.assertRaises(ValueError):prepare_open(context,encode(body),body['request_id'],'command1')
if __name__=='__main__':unittest.main()
