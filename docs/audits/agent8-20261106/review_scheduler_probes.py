"""Independent advisory scheduler invariants; never activates a worker or authority."""
import ast,dataclasses,hashlib,itertools,json,pathlib,random,subprocess,sys
from datetime import datetime
ROOT=pathlib.Path(__file__).resolve().parents[1];source=ROOT/'work/review5-scheduler';sha='787c862568eb47177c21393338e743ec01b5f45f';base='2df6f5c2f77f4d883bad1a8623dd8375db529be0'
def git(*args):return subprocess.check_output(['git','-C',str(source),*args])
assert git('rev-parse','HEAD').decode().strip()==sha
assert git('rev-parse','HEAD^{tree}').decode().strip()=='bc815723d7961a5a956565f14c53c3ed5fe73c8a'
changed=git('diff','--name-only',base,sha).decode().splitlines()
assert len(changed)==8 and all(p.startswith(('scheduler_components/','docs/scheduler/')) or p in ('tests/test_agent5_scheduler_components.py','.github/workflows/agent5-components.yml') for p in changed)
hashes={}
for row in filter(None,git('ls-tree','-r','-z',sha).split(b'\0')):
    meta,name=row.split(b'\t',1);mode,kind,oid=meta.split();name=name.decode();data=(source/name).read_bytes()
    assert kind==b'blob' and mode in (b'100644',b'100755')
    assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==oid.decode(),name
    hashes[name]=hashlib.sha256(data).hexdigest()
sys.path.insert(0,str(source));sys.dont_write_bytecode=True
from scheduler_components.placement import Resources,Candidate,Policy,place
from scheduler_components.schedules import active_at,worker_mode
from scheduler_components.authority_boundary import ClosedAuthorityBoundary,MUTATIONS
policy=Policy(10,800000,1,1);request=Resources(10,10,10,10,10)
node=Candidate('n-a','i','i',90,'bench',Resources(100,100,100,100,100),Resources(0,0,0,0,0))
def choose(nodes,req=request):return place(req,'bench',frozenset(),nodes,100,policy)
probes={}
for field in ('cpu','ram','scratch','disk_bps','network_bps'):
    exact=dataclasses.replace(node,reserved=dataclasses.replace(node.reserved,**{field:90}))
    overflow=dataclasses.replace(node,reserved=dataclasses.replace(node.reserved,**{field:91}))
    assert choose([exact]).candidate=='n-a' and choose([overflow]).candidate is None
probes['independent_resource_boundaries']='PASS'
nodes=[dataclasses.replace(node,node_id=name) for name in ('n-c','n-b','n-a')]
assert {choose(order).candidate for order in itertools.permutations(nodes)}=={'n-a'}
probes['all_six_permutations_same_advisory_candidate']='PASS'
rng=random.Random(20261106)
for _ in range(100):
    values=[rng.randrange(0,100) for _ in range(5)]
    scarce=dataclasses.replace(node,reserved=Resources(*values))
    more=dataclasses.replace(node,reserved=Resources(*(v+rng.randrange(0,30) for v in values)))
    if choose([scarce]).candidate is None:assert choose([more]).candidate is None
probes['reservation_monotonicity_100_cases']='PASS'
for patch in ({'observed_ms':89},{'observed_ms':101},{'observation_incarnation':'old'},
              {'worker_role':False},{'mode':'DRAINING'},{'mode':'MAINTENANCE'},{'healthy':False}):
    assert choose([dataclasses.replace(node,**patch)]).candidate is None
probes['bad_snapshot_never_selected']='PASS'
for stamp in ('2026-10-25T00:30:00+00:00','2026-10-25T01:30:00+00:00'):
    assert active_at(datetime.fromisoformat(stamp),120,180,iter([6]))
assert not active_at(datetime.fromisoformat('2026-03-29T01:30:00+00:00'),120,180,{6})
assert worker_mode(False,1)=='DRAINING' and worker_mode(False,0)=='STANDBY'
probes['dst_iterator_and_draining']='PASS'
expected={'GrantAssignment','RenewAssignment','DrainAssignment','SupersedeAssignment','CancelAssignment','CompleteAssignment','PublishSegment','AdoptCommittedSegment','ReleaseReservation'}
assert MUTATIONS==expected
class ExplosivePayload:
    def __getattribute__(self,name):raise AssertionError('payload inspected or invoked')
for operation in expected:assert ClosedAuthorityBoundary().execute(operation,ExplosivePayload())=='SAFETY_GATE_CLOSED'
probes['nine_mutations_ignore_caller_payload_and_deny']='PASS'
imports={}
for path in (source/'scheduler_components').glob('*.py'):
    tree=ast.parse(path.read_text());names=[]
    for node_ast in ast.walk(tree):
        if isinstance(node_ast,ast.Import):names.extend(x.name for x in node_ast.names)
        if isinstance(node_ast,ast.ImportFrom):names.append(node_ast.module)
    assert set(names)<={'dataclasses','fractions','datetime','zoneinfo'}
    imports[path.name]=names
result={'head':sha,'tree':'bc815723d7961a5a956565f14c53c3ed5fe73c8a','base':base,'changed_files':changed,'claimed_additive_scope_matches':True,'raw_tree_sha256':hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest(),'probes':probes,'component_imports':imports,'result':'PASS_COMPONENT_ONLY','runtime_authority':'SAFETY_GATE_CLOSED','physical':'BLOCKED','full_api_ACK':'NOT_GRANTED','Windows_CI':'PENDING_ORIGINAL_RECEIPTS'}
(ROOT/'outputs/phase5/scheduler-independent-probes.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
