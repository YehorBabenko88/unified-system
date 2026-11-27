"""Structural identity guards never authenticate a Windows principal."""
import json
import unittest
from unified_system.security_identity_records import (IdentityBinding, IdentityRecordError,
    guard_keys, decode_guard_records)


def fixtures():
    ids=['00000000-0000-4000-8000-'+str(i).zfill(12) for i in range(1,7)]
    binding=IdentityBinding(*ids)
    common={'schema':'unified.security.identity-record.v1','cluster_id':ids[0],
            'principal_id':ids[1],'state':'ACTIVE','revision':'1'}
    values={
        'principal':dict(common,kind='principal',node_id=ids[5],sid='S-1-5-21-1-2-3-1001'),
        'session':dict(common,kind='session',session_id=ids[2],enrollment_id=ids[3],
                       policy_id=ids[4],native_logon_id='000000000000001a'),
        'enrollment':dict(common,kind='enrollment',enrollment_id=ids[3],node_id=ids[5]),
        'policy':dict(common,kind='policy',policy_id=ids[4],role='operator',
                      permissions=['GET_COMMAND','OPEN_CONNECTION'])}
    return binding,values


def encode(values):
    return {k:json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
            for k,v in values.items()}


class IdentityRecordTests(unittest.TestCase):
    def test_fixed_keys_cross_bound_and_no_authorization_property(self):
        binding,values=fixtures();keys=guard_keys(binding)
        self.assertEqual(len(keys),4)
        self.assertEqual(keys['session'],f'unified/{binding.cluster_id}/security/v1/sessions/{binding.session_id}')
        records=decode_guard_records(binding,encode(values))
        self.assertEqual(records['policy']['role'],'operator')
        self.assertNotIn('authenticated',records)

    def test_key_injection_and_noncanonical_uuid_denied(self):
        b,_=fixtures()
        for bad in ['../sessions/other','AAAAAAAA-0000-4000-8000-000000000001','00000000-0000-1000-8000-000000000001',True]:
            with self.subTest(bad=bad),self.assertRaises(IdentityRecordError):
                guard_keys(IdentityBinding(bad,b.principal_id,b.session_id,b.enrollment_id,b.policy_id,b.node_id))

    def test_every_binding_mismatch_denied(self):
        b,values=fixtures()
        for kind,record in values.items():
            for key in set(record)&{'cluster_id','principal_id','session_id','enrollment_id','policy_id','node_id'}:
                with self.subTest(kind=kind,key=key):
                    changed=json.loads(json.dumps(values));changed[kind][key]='00000000-0000-4000-8000-999999999999'
                    with self.assertRaises(IdentityRecordError):decode_guard_records(b,encode(changed))

    def test_revoked_unknown_missing_and_extra_denied(self):
        b,values=fixtures()
        for kind in values:
            changed=json.loads(json.dumps(values));changed[kind]['state']='REVOKED'
            with self.assertRaises(IdentityRecordError):decode_guard_records(b,encode(changed))
        raw=encode(values);raw.pop('session')
        with self.assertRaises(IdentityRecordError):decode_guard_records(b,raw)
        values['policy']['authenticated']=True
        with self.assertRaises(IdentityRecordError):decode_guard_records(b,encode(values))

    def test_duplicate_noncanonical_and_oversized_json_denied(self):
        b,values=fixtures();raw=encode(values)
        for bad in [b'{"kind":"session","kind":"session"}',b' '+raw['session'],b'x'*16385]:
            changed=dict(raw,session=bad)
            with self.assertRaises(IdentityRecordError):decode_guard_records(b,changed)

    def test_permissions_and_revision_are_strict(self):
        b,values=fixtures()
        for key,bad in [('permissions',['OPEN_CONNECTION','GET_COMMAND']),('permissions',['GET_COMMAND','GET_COMMAND']),
                        ('permissions',['REAL_ORDER']),('revision',1),('revision','01'),('revision',str(2**63))]:
            changed=json.loads(json.dumps(values));changed['policy'][key]=bad
            with self.subTest(key=key,bad=bad),self.assertRaises(IdentityRecordError):decode_guard_records(b,encode(changed))

    def test_sid_and_native_logon_id_not_free_form(self):
        b,values=fixtures()
        for kind,key,bad in [('principal','sid','Administrator'),('session','native_logon_id','0x1a')]:
            changed=json.loads(json.dumps(values));changed[kind][key]=bad
            with self.assertRaises(IdentityRecordError):decode_guard_records(b,encode(changed))

    def test_result_deeply_immutable_and_independent(self):
        b,values=fixtures();raw=encode(values);parsed=decode_guard_records(b,raw)
        raw['policy']=b'{}'
        with self.assertRaises(TypeError):parsed['policy']['role']='administrator'
        with self.assertRaises(TypeError):parsed['principal']={}
        self.assertEqual(parsed['policy']['permissions'],('GET_COMMAND','OPEN_CONNECTION'))


if __name__=='__main__':unittest.main()
