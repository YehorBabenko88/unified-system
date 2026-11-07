import copy,hashlib,json,unittest
from unified_system.control_mux.codec import encode,decode
from unified_system.control_mux.commands import AdmittedContext,prepare_subscribe,prepare_ack,prepare_close,validate_original
C='22222222-2222-4222-8222-222222222222'
S='33333333-3333-4333-8333-333333333333'
SN='44444444-4444-4444-8444-444444444444'
R='11111111-1111-4111-8111-111111111111'
class OtherCommandTests(unittest.TestCase):
 def setUp(self):
  self.ctx=AdmittedContext(C,'operator','session','owner','OPERATOR_CONTROL','policy','1',frozenset({'OPEN_SUBSCRIPTION','ACK_SNAPSHOT','CLOSE_SUBSCRIPTION','CLOSE_CONNECTION'}),object())
  self.sub=dict(schema='unified.control.subscription-open.v3',request_id=R,kind='CONTROL',selector=dict(kind='CONTROL',dataset_id=None,source_id=None,partition_id=None),expected_connection_epoch='2')
  self.ack=dict(schema='unified.control.snapshot-ack.v3',request_id=R,snapshot_id=SN,snapshot_body_sha256='a'*64,cursor='cursor',expected_subscription_epoch='3')
 def test_positive_subscribe_and_ack_originals(self):
  sub=prepare_subscribe(self.ctx,encode(self.sub),R,'key',C,'2')
  ack=prepare_ack(self.ctx,encode(self.ack),R,'key2',C,S,'2','3')
  self.assertEqual(validate_original(decode(sub.preimage),sub.body),self.sub)
  self.assertEqual(validate_original(decode(ack.preimage),ack.body),self.ack)
 def test_subscribe_epoch_header_mismatch(self):
  with self.assertRaises(ValueError):prepare_subscribe(self.ctx,encode(self.sub),R,'key',C,'9')
 def test_selector_kind_mismatch(self):
  with self.assertRaises(ValueError):prepare_subscribe(self.ctx,encode(dict(self.sub,kind='DATASET')),R,'key',C,'2')
 def test_hash_consistent_subscribe_body_epoch_mismatch(self):
  cmd=prepare_subscribe(self.ctx,encode(self.sub),R,'key',C,'2');pre=decode(cmd.preimage)
  body=encode(dict(self.sub,expected_connection_epoch='9'));pre['canonical_body_sha256']=hashlib.sha256(body).hexdigest()
  with self.assertRaises(ValueError):validate_original(pre,body)
 def test_hash_consistent_ack_snapshot_mismatch(self):
  cmd=prepare_ack(self.ctx,encode(self.ack),R,'key',C,S,'2','3');pre=decode(cmd.preimage)
  body=encode(dict(self.ack,snapshot_id=C));pre['canonical_body_sha256']=hashlib.sha256(body).hexdigest()
  with self.assertRaises(ValueError):validate_original(pre,body)
 def test_hash_consistent_ack_epoch_mismatch(self):
  cmd=prepare_ack(self.ctx,encode(self.ack),R,'key',C,S,'2','3');pre=decode(cmd.preimage)
  body=encode(dict(self.ack,expected_subscription_epoch='9'));pre['canonical_body_sha256']=hashlib.sha256(body).hexdigest()
  with self.assertRaises(ValueError):validate_original(pre,body)
 def test_empty_close_targets_and_epochs_bind_digest(self):
  a=prepare_close(self.ctx,b'',R,'key',C,'2');b=prepare_close(self.ctx,b'',R,'key',C,'3');c=prepare_close(self.ctx,b'',R,'key',C,'2',S,'3')
  self.assertIsNone(validate_original(decode(a.preimage),a.body));self.assertNotEqual(a.digest,b.digest);self.assertNotEqual(a.digest,c.digest);self.assertEqual(a.key_sha256,c.key_sha256)
 def test_nonempty_delete_rejected(self):
  with self.assertRaises(ValueError):prepare_close(self.ctx,b'{}',R,'key',C,'2')
if __name__=='__main__':unittest.main()
