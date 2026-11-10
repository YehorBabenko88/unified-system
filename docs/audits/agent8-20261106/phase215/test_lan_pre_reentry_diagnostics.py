"""SOURCE-ONLY proposed API regressions; implementation held, NEVER RUN yet.

Imports target the eventual actual helper, not a local mirror. Root must review V2 alias/retention contract and approve API before
implementation/test execution.
"""
import copy
import json
import unittest
from unittest.mock import patch


def maximal_legacy_state():
    code='BUDGET_STORE_UNAVAILABLE'
    connection=dict(slot=2,closed=False,why=code,age_ms=9999999,q=64,qb=1048576,
        streams=[[16,False,2**63-1,2**63-1] for _ in range(2)],
        jobs=[['MUX_FRAGMENT','control',False,code,-9999999] for _ in range(2)],
        alive=[False]*5)
    store=dict(phase='TX_ERROR_EXIT',waiters=16,held=False,entry_ms=9999999,
        hold_ms=9999999,max_ms=9999999,n=9999999,budget_waiters=16,budget_ms=9999999)
    io=dict(slot=2,channel='control',read='TX_ERROR_EXIT',write='MUX_FRAGMENT',
        n=65536,remaining_ms=-9999999,elapsed_ms=9999999,active=False,error=code)
    return dict(v=1,stage='TX_ERROR_EXIT',code=code,observer='UNAVAILABLE',
        connections=[copy.deepcopy(connection) for _ in range(2)],
        stores=[copy.deepcopy(store) for _ in range(2)],
        io=[copy.deepcopy(io) for _ in range(4)],truncated=False)


class PreReentryProposalTests(unittest.TestCase):
    def setUp(self):
        # Deliberately deferred: proposed actual API does not exist at base.
        from tests import lan_failure_diagnostics as helper
        self.helper=helper
        self.state=helper._PreReentryState()

    def test_two_fixed_slots_and_unknown_slot_cannot_expand_wire(self):
        self.state.readiness(1,'READY')
        self.state.readiness(2,'CONTROL_RETURN')
        self.state.readiness(3,'CONTROL_REENTRY')
        rows=self.state.packed()
        self.assertEqual(len(rows),2)
        self.assertEqual([r[0] for r in rows],[1,2])
        self.assertTrue(all(len(r)==10 for r in rows))

    def test_readiness_bits_and_false_idle_value_are_not_truthy_coerced(self):
        for event in ('READY','CONTROL_RETURN','CONTROL_REENTRY','DATA_WAIT_EXPIRED','IDLE_CALLED'):
            self.state.readiness(1,event)
        self.state.idle_result(1,False)
        self.assertEqual(self.state.packed()[0][1:3],[31,2])

    def test_first_current_failure_site_code_family_and_order_are_sticky(self):
        self.state.current_failure(1,'PONG','POLICY_REVOKED','TRANSPORT')
        first=self.state.packed()[0][3:7]
        self.state.current_failure(1,'READER','DISCONNECTED','OS')
        self.assertEqual(self.state.packed()[0][3:7],first)
        self.assertEqual(first[:3],[2,9,1])
        self.assertGreater(first[3],0)

    def test_first_close_entry_is_sticky_not_claimed_as_actual_transition(self):
        self.state.close_entry(1,'DISCONNECTED','TRANSPORT')
        first=self.state.packed()[0][7:10]
        self.state.close_entry(1,'CLOSED','OTHER')
        self.assertEqual(self.state.packed()[0][7:10],first)

    def test_ordinals_saturate_without_rollover(self):
        for _ in range(300):self.state.readiness(1,'READY')
        self.state.close_entry(2,'CLOSED','OTHER')
        self.assertEqual(self.state.packed()[1][9],255)

    def test_private_values_never_call_str_or_repr_or_enter_wire(self):
        class Private:
            def __str__(self):raise AssertionError('private str called')
            def __repr__(self):raise AssertionError('private repr called')
        self.state.current_failure(1,Private(),Private(),Private())
        text=json.dumps(self.state.packed(),ensure_ascii=True)
        self.assertTrue(text.isascii())
        self.assertEqual(self.state.packed()[0][3:6],[3,1,6])

    def test_delegating_current_calls_original_exactly_once(self):
        calls=[];sentinel=object()
        def original():calls.append(1);return sentinel
        result=self.state.call_current(1,'READER',original)
        self.assertIs(result,sentinel)
        self.assertEqual(calls,[1])

    def test_original_exception_identity_survives_observer_failure(self):
        calls=[];error=ValueError('POLICY_REVOKED')
        def original():calls.append(1);raise error
        with patch.object(self.state,'current_failure',side_effect=RuntimeError('observer unavailable')):
            with self.assertRaises(type(error)) as raised:
                self.state.call_current(1,'PONG',original)
        self.assertIs(raised.exception,error)
        self.assertEqual(calls,[1])

    def test_actual_formatter_rejects_unknown_packed_data_without_private_leak(self):
        state=dict(pre=[['private-key-body']*20]*3)
        line=self.helper.format_failure_v2({},pre=state['pre'])
        self.assertNotIn('private-key-body',line)
        self.assertLessEqual(len(line.encode('ascii')),1960)

    def test_no_earlier_truncation_of_legacy_fields_is_release_gate(self):
        # V1 chooses retention BEFORE V2 aliasing and the packed addition.
        state=maximal_legacy_state()
        for row in state['stores']:
            for key in ('entry_ms','hold_ms','max_ms','n','budget_ms'):row[key]=0
        baseline=self.helper.format_failure(state,'BUDGET_STORE_UNAVAILABLE')
        pre=[[slot,31,3,3,31,7,255,31,7,255] for slot in (1,2)]
        candidate=self.helper.format_failure_v2(state,'BUDGET_STORE_UNAVAILABLE',pre=pre)
        self.assertLessEqual(len(candidate.encode('ascii')),1960)
        old=json.loads(baseline.split(' ',1)[1]);new,decoded_pre=self.helper.decode_failure(candidate)
        self.assertEqual(new,old)
        self.assertEqual(decoded_pre,pre)
        self.assertFalse(old['truncated'])
        self.assertEqual(len(old['io']),4)


class PreReentryV2CodecProposalTests(unittest.TestCase):
    def setUp(self):
        from tests import lan_failure_diagnostics as helper
        self.helper=helper
        self.pre=[[slot,31,3,3,16,7,255,16,7,255] for slot in (1,2)]

    def test_alias_registry_is_closed_injective_and_versioned(self):
        aliases=self.helper.V2_KEY_ALIASES
        self.assertEqual(len(aliases),34)
        self.assertEqual(len(set(aliases.values())),34)
        self.assertNotIn('P',aliases.values())
        self.assertTrue(all(type(v) is str and len(v)==1 and v.isascii() for v in aliases.values()))
        self.assertEqual(aliases['remaining_ms'],'u')
        self.assertEqual(aliases['connections'],'c')
        with self.assertRaises(TypeError):aliases['v']='private'

    def test_original_v1_wire_and_historical_decode_remain_v1(self):
        state=maximal_legacy_state()
        line=self.helper.format_failure(state,'BUDGET_STORE_UNAVAILABLE')
        self.assertTrue(line.startswith('LAN_FAIL_DIAG_V1 '))
        decoded,pre=self.helper.decode_failure(line)
        self.assertEqual(decoded,json.loads(line.split(' ',1)[1]))
        self.assertIsNone(pre)

    def test_full_old_fallback_is_selected_before_new_encoding(self):
        state=maximal_legacy_state()
        old=json.loads(self.helper.format_failure(state,'BUDGET_STORE_UNAVAILABLE').split(' ',1)[1])
        line=self.helper.format_failure_v2(state,'BUDGET_STORE_UNAVAILABLE',pre=self.pre)
        decoded,pre=self.helper.decode_failure(line)
        self.assertEqual(decoded,old)
        self.assertTrue(decoded['truncated'])
        self.assertEqual(len(decoded['io']),2)
        self.assertEqual(pre,self.pre)
        self.assertLessEqual(len(line.encode('ascii')),1960)

    def test_all_bounded_collection_shapes_keep_old_decoded_retention(self):
        import itertools
        for nc,ns,ni,nstream,njob,nalive in itertools.product(range(3),range(3),range(5),range(3),range(3),range(6)):
            state=maximal_legacy_state()
            state['connections']=state['connections'][:nc]
            state['stores']=state['stores'][:ns];state['io']=state['io'][:ni]
            for row in state['connections']:
                row['streams']=row['streams'][:nstream];row['jobs']=row['jobs'][:njob]
                row['alive']=row['alive'][:nalive]
            old=json.loads(self.helper.format_failure(state,'BUDGET_STORE_UNAVAILABLE').split(' ',1)[1])
            line=self.helper.format_failure_v2(state,'BUDGET_STORE_UNAVAILABLE',pre=self.pre)
            decoded,pre=self.helper.decode_failure(line)
            self.assertEqual(decoded,old)
            self.assertEqual(pre,self.pre)
            self.assertLessEqual(len(line.encode('ascii')),1960)

    def test_busy_unavailable_connection_shapes_are_not_reinterpreted(self):
        for row in ({'busy':True},{'unavailable':True}):
            state=maximal_legacy_state();state['connections']=[row,row]
            old=json.loads(self.helper.format_failure(state).split(' ',1)[1])
            decoded,pre=self.helper.decode_failure(self.helper.format_failure_v2(state,pre=self.pre))
            self.assertEqual(decoded,old)
            self.assertEqual(pre,self.pre)

    def test_decoder_rejects_duplicate_unknown_alias_and_wrong_version(self):
        for line in ('LAN_FAIL_DIAG_V2 {"v":2,"v":2}\n',
                     'LAN_FAIL_DIAG_V2 {"v":2,"secret":"private"}\n',
                     'LAN_FAIL_DIAG_V2 {"v":1}\n',
                     'LAN_FAIL_DIAG_V1 {"v":2}\n'):
            with self.assertRaises(ValueError):self.helper.decode_failure(line)

    def test_codec_rejects_oversized_or_non_ascii_input_before_parse(self):
        for line in ('LAN_FAIL_DIAG_V2 '+' '*1960,'LAN_FAIL_DIAG_V2 {"v":2,"secret":"\u2603"}'):
            with self.assertRaises(ValueError):self.helper.decode_failure(line)
