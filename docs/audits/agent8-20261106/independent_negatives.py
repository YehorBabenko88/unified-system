"""Auditor-owned offline negatives. Does not qualify physical auth or HA.

Run: python -I -S -B independent_negatives.py --source PATH --expected-head SHA
Only imports source modules; no listeners, orders, account or network changes.
"""
import argparse, copy, json, pathlib, subprocess, sys, unittest

parser=argparse.ArgumentParser()
parser.add_argument('--source',required=True,type=pathlib.Path)
parser.add_argument('--expected-head',required=True)
args=parser.parse_args()
source=args.source.resolve()
head=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
if head!=args.expected_head or len(head)!=40:
    raise SystemExit('BLOCKED: exact HEAD mismatch')
dirty=subprocess.check_output(['git','-C',str(source),'status','--porcelain=v1','--untracked-files=all'],text=True)
if dirty.strip(): raise SystemExit('BLOCKED: source not clean')
sys.path.insert(0,str(source))
from unified_system import operator_control_plane as op, physical_acceptance as physical

def envelope():
    return dict(schema='unified.command.v1',command_id='ba219f7b-1111-4111-8111-000000000001',
        actor_id='audit-human',idempotency_key='audit-intent',generation='ba219f7b-1111-4111-8111-000000000002',
        aggregate_type='research',aggregate_id='audit-research',expected_revision=0,
        action='SetResearchControl',payload={'mode':'LAB_SIMULATION','state':'PAUSED'})

class NeverBackend:
    def __init__(self): self.calls=0
    async def submit(self,*args):
        self.calls+=1
        raise AssertionError('Unauthorized input reached backend')

class FakeProvider:
    """A seam double, never evidence of real session expiry or identity."""
    def __init__(self,principal=None,denied=False): self.principal=principal; self.denied=denied
    async def require_current(self,*args):
        if self.denied: raise op.AuthorizationDenied('expired-or-revoked-double')
        return self.principal

class IndependentNegatives(unittest.IsolatedAsyncioTestCase):
    async def test_no_provider_denies_before_backend(self):
        backend=NeverBackend()
        with self.assertRaises(op.AuthenticationUnavailable):
            await op.OperatorGateway(backend).submit(None,envelope(),object())
        self.assertEqual(backend.calls,0)

    async def test_denied_session_seam_has_no_effect(self):
        backend=NeverBackend()
        with self.assertRaises(op.AuthorizationDenied):
            await op.OperatorGateway(backend,FakeProvider(denied=True)).submit(None,envelope(),object())
        self.assertEqual(backend.calls,0)

    async def test_rbac_actor_and_machine_negatives(self):
        for actor,kind,caps in [('other-human','HUMAN',{'research.control'}),
                ('audit-human','NODE',{'research.control'}),('audit-human','SERVICE',{'research.control'}),
                ('audit-human','HUMAN',{'cluster.snapshot.read'}),
                ('audit-human','HUMAN',{'research.control','owner.override'})]:
            with self.subTest(actor=actor,kind=kind,caps=caps):
                backend=NeverBackend()
                p=op.CurrentPrincipal(actor,1,kind,frozenset(caps))
                with self.assertRaises(op.AuthorizationDenied):
                    await op.OperatorGateway(backend,FakeProvider(p)).submit(None,envelope(),object())
                self.assertEqual(backend.calls,0)

    async def test_order_live_and_destructive_intents_rejected(self):
        for patch in [{'action':'PlaceOrder'},{'action':'FullPurge'},
                      {'payload':{'mode':'LIVE','state':'RUNNING'}}, {'expected_revision':True}]:
            value=envelope();value.update(patch)
            backend=NeverBackend()
            with self.assertRaises(op.ContractError):
                await op.OperatorGateway(backend).submit(None,value,object())
            self.assertEqual(backend.calls,0)

    def test_parser_duplicate_nonfinite_and_overload(self):
        for raw in [b'{"schema":1,"schema":2}',b'{"x":NaN}',b' '*32769,
                    b'{"x":'+b'['*2000+b'0'+b']'*2000+b'}']:
            with self.subTest(length=len(raw)),self.assertRaises(op.ContractError): op.parse_envelope(raw)

    def test_complete_self_claimed_physical_pass_never_authorizes(self):
        nodes=['audit-'+str(i) for i in range(6)]
        records=[dict(node_id=n,scenario=s,release_sha=head,run_id='independent-negative',result='PASS',
            environment='PHYSICAL_WINDOWS',evidence_sha256='0'*64) for n in nodes for s in physical.SCENARIOS]
        report=physical.assess(nodes,records,release_sha=head,run_id='independent-negative')
        self.assertEqual(report['status'],'RECORDED_UNVERIFIED')
        self.assertFalse(report['physical_acceptance_confirmed'])
        self.assertFalse(report['deployment_authorized'])
        bad=copy.deepcopy(records);bad[1]=copy.deepcopy(bad[0])
        with self.assertRaises(ValueError): physical.assess(nodes,bad,release_sha=head,run_id='independent-negative')

    def test_missing_and_cloud_evidence_never_passes(self):
        nodes=['audit-'+str(i) for i in range(6)]
        report=physical.assess(nodes,[],release_sha=head,run_id='independent-negative')
        self.assertEqual(report['status'],'NOT_RUN');self.assertEqual(len(report['missing']),90)
        record=dict(node_id=nodes[0],scenario=physical.SCENARIOS[0],release_sha=head,
                    run_id='independent-negative',result='PASS',environment='CLOUD',evidence_sha256='0'*64)
        with self.assertRaises(ValueError): physical.assess(nodes,[record],release_sha=head,run_id='independent-negative')

if __name__=='__main__':
    print(json.dumps({'head':head,'scope':'OFFLINE_SEAM_NEGATIVES_ONLY','physical':'NOT_RUN','real_authentication':'NOT_RUN'}),flush=True)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentNegatives))
    raise SystemExit(not result.wasSuccessful())
