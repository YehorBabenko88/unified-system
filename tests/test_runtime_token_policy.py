"""Synthetic token policy assertions; these do not create Windows accounts."""
import copy
import importlib.util
import os
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
ACCOUNT='S-1-5-21-11-22-33-1001'
SERVICE='S-1-5-80-1-2-3-4-5'


def observation():
    return dict(schema='unified.windows-runtime-token-observation.v1',user_sid=ACCOUNT,
                token_type=1,elevation_type=1,elevated=False,thread_token_present=False,
                session_id=0,ui_access=False,integrity_sid='S-1-16-16384',
                groups=[dict(sid='S-1-5-6',attributes=7),dict(sid=SERVICE,attributes=7)],
                privileges=[dict(name='SeChangeNotifyPrivilege',attributes=3)])


class TokenPolicyTests(unittest.TestCase):
    def module(self):
        path=ROOT/'unified_system/runtime_token_policy.py'
        self.assertTrue(path.is_file(),'strict runtime token audit is missing')
        spec=importlib.util.spec_from_file_location('_runtime_token_policy',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

    def admit(self,module,value):
        return module.evaluate_token(value,expected_account_sid=ACCOUNT,expected_service_sid=SERVICE)

    def test_nonadmin_dedicated_service_facts_only_satisfy_token_policy(self):
        m=self.module();result=self.admit(m,observation())
        self.assertEqual(result['status'],'TOKEN_POLICY_SATISFIED')
        self.assertIs(result['execution_authority'],False)
        self.assertEqual(result['network_configuration_access'],'NOT_PROVEN')
        self.assertEqual(result['account_provisioning'],'NOT_EVALUATED')
        value=observation();value['user_sid']=SERVICE
        m.evaluate_token(value,expected_account_sid=SERVICE,expected_service_sid=SERVICE)

    def test_admin_or_network_operator_presence_even_disabled_or_deny_only_is_rejected(self):
        m=self.module()
        for sid in ('S-1-5-32-544','S-1-5-32-556','S-1-5-32-547','S-1-5-21-11-22-33-512'):
            for attributes in (0,4,16):
                value=observation();value['groups'].append(dict(sid=sid,attributes=attributes))
                with self.subTest(sid=sid,attributes=attributes),self.assertRaises(m.TokenPolicyBlocked):self.admit(m,value)

    def test_any_nonallowlisted_privilege_held_even_disabled_is_rejected(self):
        m=self.module()
        for name in ('SeImpersonatePrivilege','SeDelegateSessionUserImpersonatePrivilege','SeDebugPrivilege',
                     'SeLoadDriverPrivilege','SeRestorePrivilege','SeTakeOwnershipPrivilege',
                     'SeBackupPrivilege','SeTcbPrivilege','SeCreateGlobalPrivilege','SeUnknownPrivilege'):
            for attributes in (0,2):
                value=observation();value['privileges'].append(dict(name=name,attributes=attributes))
                with self.subTest(name=name,attributes=attributes),self.assertRaises(m.TokenPolicyBlocked):self.admit(m,value)

    def test_elevation_linked_admin_impersonation_session_and_ui_access_rejected(self):
        m=self.module()
        for key,value in (('elevated',True),('elevation_type',2),('elevation_type',3),
                          ('token_type',2),('thread_token_present',True),('session_id',1),('ui_access',True)):
            current=observation();current[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(m.TokenPolicyBlocked):self.admit(m,current)

    def test_shared_builtin_account_wrong_account_and_wrong_service_rejected(self):
        m=self.module()
        for sid in ('S-1-5-18','S-1-5-19','S-1-5-20','S-1-5-21-11-22-33-1002'):
            value=observation();value['user_sid']=sid
            with self.subTest(sid=sid),self.assertRaises(m.TokenPolicyBlocked):self.admit(m,value)
        for attributes in (0,16):
            value=observation();value['groups'][1]['attributes']=attributes
            with self.assertRaises(m.TokenPolicyBlocked):self.admit(m,value)

    def test_closed_schema_types_duplicate_and_unknown_group_flags_rejected(self):
        m=self.module()
        for mutate in (lambda v:v.update(extra=True),lambda v:v.update(token_type=True),
                       lambda v:v.update(elevated=0),lambda v:v['groups'].append(v['groups'][0]),
                       lambda v:v['privileges'].append(v['privileges'][0]),
                       lambda v:v['groups'][0].update(attributes=128),lambda v:v['groups'][0].update(attributes=True),
                       lambda v:v.update(groups=[{}]),lambda v:v.update(privileges=[{}])):
            value=observation();mutate(value)
            with self.assertRaises(m.TokenPolicyBlocked):self.admit(m,value)

    def test_six_component_account_assignments_must_be_distinct(self):
        m=self.module();mapping={name:'S-1-5-21-11-22-33-'+str(1001+i) for i,name in enumerate(m.COMPONENTS)}
        m.validate_component_accounts(mapping)
        shared=copy.deepcopy(mapping);names=list(shared);shared[names[1]]=shared[names[0]]
        with self.assertRaises(m.TokenPolicyBlocked):m.validate_component_accounts(shared)
        with self.assertRaises(m.TokenPolicyBlocked):m.validate_component_accounts({})
        with self.assertRaises(m.TokenPolicyBlocked):m.validate_component_accounts({**mapping,'extra':ACCOUNT})

    def test_bounded_inline_sid_decoder_rejects_outside_or_truncated_memory(self):
        m=self.module();raw=b'\1\2'+(5).to_bytes(6,'big')+(32).to_bytes(4,'little')+(544).to_bytes(4,'little')
        self.assertEqual(m.sid_from_buffer(raw,1000,1000),'S-1-5-32-544')
        for pointer in (0,999,1001,1016):
            with self.assertRaises(m.TokenPolicyBlocked):m.sid_from_buffer(raw,1000,pointer)
        with self.assertRaises(m.TokenPolicyBlocked):m.sid_from_buffer(raw[:-1],1000,1000)

    def test_group_pointer_count_and_privilege_array_bounds(self):
        m=self.module();sid=b'\1\1'+(5).to_bytes(6,'big')+(6).to_bytes(4,'little')
        raw=(1).to_bytes(4,'little')+b'\0'*4+(1024).to_bytes(8,'little')+(7).to_bytes(4,'little')+b'\0'*4+sid
        self.assertEqual(m.groups_from_buffer(raw,1000,8),[dict(sid='S-1-5-6',attributes=7)])
        for malformed in (raw[:-1],(257).to_bytes(4,'little')+raw[4:],raw[:8]+(1000).to_bytes(8,'little')+raw[16:]):
            with self.assertRaises(m.TokenPolicyBlocked):m.groups_from_buffer(malformed,1000,8)
        self.assertEqual(m.privileges_from_buffer(b'\0'*4,lambda _:None),[])
        with self.assertRaises(m.TokenPolicyBlocked):m.privileges_from_buffer((257).to_bytes(4,'little'),lambda _:None)

    def test_collector_detects_changed_token_or_thread_impersonation_and_closes_handle(self):
        m=self.module()
        class Api:
            pointer_size=8
            def __init__(self,changed=False,thread=False,swapped=False,late_thread=False):
                self.changed=changed;self.thread=thread;self.swapped=swapped;self.late_thread=late_thread
                self.reads=0;self.thread_reads=0;self.closed=[];self.opened=122
            def open_process(self):self.opened+=1;return self.opened
            def close(self,handle):self.closed.append(handle)
            def thread_token_present(self):self.thread_reads+=1;return self.thread or(self.late_thread and self.thread_reads>1)
            def privilege_name(self,raw):return 'SeChangeNotifyPrivilege'
            def query(self,token,kind):
                if kind==10:
                    self.reads+=1;ident=(2 if self.swapped and token==124 else self.reads if self.changed else 1)
                    return (bytes([ident])+b'\0'*39+(2).to_bytes(4,'little')+(1).to_bytes(4,'little')+b'\0'*8,1000)
                if kind in (8,18):return ((1).to_bytes(4,'little'),1000)
                if kind in (12,20,26):return (b'\0'*4,1000)
                if kind in (1,25):
                    value=ACCOUNT if kind==1 else 'S-1-16-16384';parts=value.split('-')[2:]
                    sid=bytes([1,len(parts)-1])+int(parts[0]).to_bytes(6,'big')+b''.join(int(p).to_bytes(4,'little')for p in parts[1:])
                    return ((1016).to_bytes(8,'little')+b'\0'*8+sid,1000)
                if kind==2:
                    values=[]
                    for value in ('S-1-5-6',SERVICE):
                        parts=value.split('-')[2:];values.append(bytes([1,len(parts)-1])+int(parts[0]).to_bytes(6,'big')+b''.join(int(p).to_bytes(4,'little')for p in parts[1:]))
                    offset=40;rows=[]
                    for value in values:rows.append((1000+offset).to_bytes(8,'little')+(7).to_bytes(4,'little')+b'\0'*4);offset+=len(value)
                    return ((2).to_bytes(4,'little')+b'\0'*4+b''.join(rows)+b''.join(values),1000)
                if kind==3:return ((1).to_bytes(4,'little')+b'\0'*8+(3).to_bytes(4,'little'),1000)
                raise AssertionError(kind)
        api=Api();facts=m._collect(api);self.admit(m,facts);self.assertEqual(api.closed,[124,123])
        for api in (Api(changed=True),Api(thread=True)):
            with self.assertRaises(m.TokenPolicyBlocked):m._collect(api)
            if not api.thread:self.assertEqual(api.closed,[123])
        for api in (Api(swapped=True),Api(late_thread=True)):
            with self.assertRaises(m.TokenPolicyBlocked):m._collect(api)
            self.assertEqual(api.closed,[124,123])

    @unittest.skipUnless(os.name=='nt','native read-only Windows token query unavailable')
    def test_real_current_token_can_be_observed_without_granting_service_authority(self):
        m=self.module();facts=m.collect_current_process_token()
        self.assertEqual(set(facts),m.FIELDS)
        self.assertEqual(facts['schema'],m.SCHEMA)
        with self.assertRaises(m.TokenPolicyBlocked):
            m.require_current_runtime_token(expected_account_sid=ACCOUNT,expected_service_sid=SERVICE)

if __name__=='__main__':unittest.main()
