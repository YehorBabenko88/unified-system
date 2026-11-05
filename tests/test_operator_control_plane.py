"""Offline contract evidence only; fixtures do not qualify native human auth."""
import copy
import hashlib
import json
import unittest
from unified_system.operator_control_plane import (
    AuthenticationUnavailable, AuthorizationDenied, ContractError, CurrentPrincipal,
    OperatorGateway, StreamView, validate_envelope, parse_envelope,
)


def intent():
    return dict(schema='unified.command.v1', command_id='11111111-1111-4111-8111-111111111111',
                actor_id='operator-1', idempotency_key='intent-1', generation='00000000-0000-0000-0000-000000000007',
                aggregate_type='research', aggregate_id='research-1', expected_revision=0,
                action='SetResearchControl', payload={'mode':'LAB_SIMULATION','state':'PAUSED'})


class FixtureVerifier:
    """Explicit test-only verifier; never installed by any runtime factory."""
    def __init__(self):
        self.state='current'; self.kind='HUMAN'; self.roles=frozenset({'research.control','control.commands.read'})
    async def require_current(self, context, action, aggregate_id):
        if self.state != 'current': raise AuthorizationDenied(self.state)
        return CurrentPrincipal('operator-1', 3, self.kind, self.roles)


class FixtureBackend:
    """In-memory CAS/receipt seam; no persistent consensus claim."""
    generation='00000000-0000-0000-0000-000000000007'
    def __init__(self): self.revision=0; self.receipts={}; self.effects=0
    async def submit(self, lease, envelope, session_context):
        key=(envelope['generation'], envelope['actor_id'], envelope['idempotency_key'])
        if key in self.receipts:
            prior, receipt=self.receipts[key]
            if prior != envelope: raise ContractError('IDEMPOTENCY_CONFLICT')
            return receipt
        if envelope['expected_revision'] != self.revision: raise ContractError('REVISION_CONFLICT')
        self.revision+=1; self.effects+=1
        receipt=dict(schema='unified.command-receipt.v1',revision=self.revision,
            command_id=envelope['command_id'],generation=envelope['generation'],
            actor_id=envelope['actor_id'],aggregate_id=envelope['aggregate_id'],grant_revision=3,
            idempotency_key=envelope['idempotency_key'],
            digest=hashlib.sha256(json.dumps(envelope,sort_keys=True).encode()).hexdigest(),
            action=envelope['action'],commit_status='COMMITTED',effect_status='PENDING_UNWIRED',
            leader_lock_index=10,consensus_modify_index=11)
        self.receipts[key]=(copy.deepcopy(envelope),receipt)
        return receipt
    async def get_command(self, command_id, session_context):
        return next((r for e,r in self.receipts.values() if e['command_id']==command_id),None)


class OperatorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.verifier=FixtureVerifier(); self.backend=FixtureBackend()
        self.gateway=OperatorGateway(self.backend,self.verifier)
    async def test_missing_provider_fails_closed(self):
        with self.assertRaises(AuthenticationUnavailable): await OperatorGateway(self.backend).submit(None,intent(),object())
        self.assertEqual(self.backend.effects,0)
    async def test_untrusted_actor_role_and_machine_denied(self):
        for update in ({'actor_id':'owner'}, {'role':'SystemOwner'}):
            value=intent(); value.update(update)
            with self.assertRaises((AuthorizationDenied,ContractError)): await self.gateway.submit(None,value,object())
        for kind in ('NODE','SERVICE'):
            self.verifier.kind=kind
            with self.assertRaises(AuthorizationDenied): await self.gateway.submit(None,intent(),object())
        self.assertEqual(self.backend.effects,0)
    async def test_current_grants_checked_on_every_retry(self):
        await self.gateway.submit(None,intent(),object())
        for state in ('expired','revoked'):
            self.verifier.state=state
            with self.assertRaises(AuthorizationDenied): await self.gateway.submit(None,intent(),object())
        self.assertEqual(self.backend.effects,1)
    async def test_role_backend_enforced_and_unknown_action_denied(self):
        self.verifier.roles=frozenset({'cluster.snapshot.read','control.commands.read'})
        with self.assertRaises(AuthorizationDenied): await self.gateway.submit(None,intent(),object())
        value=intent();value['action']='FullPurge'
        with self.assertRaises(ContractError): await self.gateway.submit(None,value,object())
    async def test_two_windows_retry_and_conflicting_revision(self):
        result=await self.gateway.submit(None,intent(),object())
        self.assertEqual(result,await self.gateway.submit(None,intent(),object()))
        value=intent();value['idempotency_key']='other';value['command_id']='22222222-2222-4222-8222-222222222222'
        with self.assertRaisesRegex(ContractError,'REVISION_CONFLICT'): await self.gateway.submit(None,value,object())
        value=intent();value['payload']['state']='RUNNING'
        with self.assertRaisesRegex(ContractError,'IDEMPOTENCY_CONFLICT'): await self.gateway.submit(None,value,object())
        self.assertEqual(self.backend.effects,1)
    async def test_strict_boundaries(self):
        for patch in ({'expected_revision':True},{'expected_version':0},{'payload':{'mode':'LIVE','state':'RUNNING'}},
                      {'payload':{'mode':'LAB_SIMULATION','state':'PAUSED','extra':'x'}},{'idempotency_key':'x'*40000}):
            value=intent();value.update(patch)
            with self.assertRaises(ContractError): validate_envelope(value)
        for raw in (b'{"schema":1,"schema":2}', b'{"nested":'+b'['*10+b'0'+b']'*10+b'}',
                    b'{"x":NaN}', b' '*32769):
            with self.assertRaises(ContractError): parse_envelope(raw)
        value=intent();value['generation']='generation-1'
        with self.assertRaises(ContractError): validate_envelope(value)
    async def test_backend_absent_never_returns_fake_receipt(self):
        with self.assertRaises(AuthenticationUnavailable): await OperatorGateway(None,self.verifier).submit(None,intent(),object())
    async def test_receipt_rechecks_current_actor_scope(self):
        await self.gateway.submit(None,intent(),object())
        self.assertEqual((await self.gateway.get_command(intent()['command_id'],object()))['actor_id'],'operator-1')
        self.verifier.state='revoked'
        with self.assertRaises(AuthorizationDenied): await self.gateway.get_command(intent()['command_id'],object())
        self.verifier.state='current'
        for _,receipt in self.backend.receipts.values(): receipt['actor_id']='operator-2'
        with self.assertRaises(AuthorizationDenied): await self.gateway.get_command(intent()['command_id'],object())
    async def test_revocation_during_receipt_query_prevents_disclosure(self):
        await self.gateway.submit(None,intent(),object())
        original=self.backend.get_command
        async def revoke(command_id,context):
            self.verifier.state='revoked'
            return await original(command_id,context)
        self.backend.get_command=revoke
        with self.assertRaises(AuthorizationDenied): await self.gateway.get_command(intent()['command_id'],object())
    async def test_serialized_or_unknown_capability_principal_denied(self):
        class SerializedVerifier:
            async def require_current(self,*args): return {'actor_id':'operator-1','grant_revision':3,'principal_kind':'HUMAN'}
        with self.assertRaises(AuthorizationDenied): await OperatorGateway(self.backend,SerializedVerifier()).submit(None,intent(),object())
        self.verifier.roles=frozenset({'research.control','owner.override'})
        with self.assertRaises(AuthorizationDenied): await self.gateway.submit(None,intent(),object())
    async def test_malformed_private_receipt_never_disclosed(self):
        receipt=await self.gateway.submit(None,intent(),object())
        patches=({'secret':'private'}, {'commit_status':'SUCCESS'}, {'effect_status':'EXECUTED'},
                 {'consensus_modify_index':True},{'consensus_modify_index':0},
                 {'consensus_modify_index':10},{'consensus_modify_index':2**53},
                 {'command_id':'22222222-2222-4222-8222-222222222222'},
                 {'generation':'00000000-0000-0000-0000-000000000008'},
                 {'digest':'invalid'},{'revision':False})
        async def result(*args): return malformed
        self.backend.get_command=result
        for patch in patches:
            malformed=dict(receipt,**patch)
            with self.assertRaises(ContractError): await self.gateway.get_command(intent()['command_id'],object())
        malformed=dict(receipt,secret='private')
        self.backend.submit=result
        with self.assertRaises(ContractError): await self.gateway.submit(None,intent(),object())


class StreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_snapshot_gap_generation_and_staleness(self):
        view=StreamView();self.assertEqual(view.status(0),'OFFLINE')
        view.snapshot('g1',4,10,100,500,True)
        self.assertEqual(view.status(100),'LIVE')
        self.assertEqual(view.status(601),'STALE')
        view.event('g1',11,5,602);self.assertEqual(view.status(602),'LIVE')
        self.assertFalse(view.event('g1',11,5,603))
        with self.assertRaises(ContractError): view.event('g1',13,6,604)
        self.assertEqual(view.status(604),'RECONNECTING')
        with self.assertRaises(ContractError): view.event('g2',12,6,605)
        view.snapshot('g2',0,0,606,500,False)
        self.assertEqual(view.status(606),'NO_QUORUM')
        view.disconnect();self.assertEqual(view.status(607),'RECONNECTING')
    async def test_invalid_snapshot_cannot_mark_live(self):
        for args in [('g',True,0,0,500,True),('g',0,0,0,0,True),('g',0,0,0,500,1)]:
            with self.assertRaises(ContractError): StreamView().snapshot(*args)
