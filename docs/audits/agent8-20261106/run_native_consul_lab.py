"""Auditor-owned disposable Windows loopback Consul/Grid qualification.

Starts and terminates ONLY its own consul.exe Popen handles. No services, network
configuration, production data, real accounts or order endpoints are touched.
Consul ACL/TLS disabled in loopback lab: this is NOT peer/human authentication.
"""
import argparse,asyncio,base64,hashlib,json,os,pathlib,socket,subprocess,sys,time,uuid

parser=argparse.ArgumentParser();parser.add_argument('--source',type=pathlib.Path,required=True);parser.add_argument('--binary',type=pathlib.Path,required=True);parser.add_argument('--scratch',type=pathlib.Path,required=True);parser.add_argument('--output',type=pathlib.Path,required=True);parser.add_argument('--raft-backend',choices=['wal','boltdb'],default='wal')
args=parser.parse_args();source=args.source.resolve();binary=args.binary.resolve();scratch=args.scratch.resolve();out=args.output.resolve()
scratch.mkdir(parents=True,exist_ok=False);out.mkdir(parents=True,exist_ok=True)
expected='71084a336520187d6e260531a2f5d15555ba0e0c'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==expected
assert hashlib.sha256(binary.read_bytes()).hexdigest()=='41762ef5b98c8dd9b6852df6cfbceed37e7f0acc5760856be33100f1092475e1'
sys.path.insert(0,str(source));sys.dont_write_bytecode=True
import httpx
from grid.coordination import ConsulConfig,ConsulSessionAuthority,canonical
from grid.coordination_commands import CoordinationCommands,CurrentPrincipal,CommandDenied

report={'schema':'agent8.native-loopback.v1','head':expected,'scope':'ISOLATED_WINDOWS_LOOPBACK_COMPONENTS',
 'consul_version':'1.22.2','raft_backend':args.raft_backend,'consul_binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
 'consul_zip_sha256':'7b8a3bb723017d1be87decf3a7bb12661c36e43eba8283b8c04eca60501493ec',
 'download_source':'https://releases.hashicorp.com/consul/1.22.2/',
 'physical':'BLOCKED','tailscale_removal':'BLOCKED','production_deployment':'NOT_AUTHORIZED',
 'human_authentication':'SYNTHETIC_PROVIDER_ONLY','peer_tls_acl':'NOT_RUN','network_partition':'NOT_RUN',
 'events':[],'result':'RUNNING'}
def record(scenario,**detail):
    report['events'].append({'scenario':scenario,**detail});(out/'native-consul-receipt.json').write_text(json.dumps(report,indent=2));print(scenario,flush=True)

def reserve_ports(count):
    socks=[];ports=[]
    try:
        for _ in range(count):
            sock=socket.socket();sock.bind(('127.0.0.1',0));socks.append(sock);ports.append(sock.getsockname()[1])
        return ports
    finally:
        for sock in socks:sock.close()

ports=reserve_ports(20);nodes=[];handles=[]
for i in range(4):
    rpc,lan,wan,http,dns=ports[i*5:i*5+5]
    folder=scratch/f'node-{i}';folder.mkdir()
    config={'server':True,'bootstrap_expect':3 if i<3 else 1,'datacenter':'a8-three' if i<3 else 'a8-restore',
      'node_name':f'a8-disposable-{i}','data_dir':str(folder/'data'),'bind_addr':'127.0.0.1','advertise_addr':'127.0.0.1',
      'client_addr':'127.0.0.1','ports':{'server':rpc,'serf_lan':lan,'serf_wan':wan,'http':http,'https':-1,'dns':-1,'grpc':-1,'grpc_tls':-1},
      'disable_update_check':True,'disable_remote_exec':True,'leave_on_terminate':False,
      'skip_leave_on_interrupt':True,'log_level':'warn','performance':{'raft_multiplier':1},
      'connect':{'enabled':False},'raft_logstore':{'backend':args.raft_backend}}
    if i<3:config['retry_join']=[f'127.0.0.1:{ports[j*5+1]}' for j in range(3) if j!=i]
    configpath=folder/'agent.json';configpath.write_text(json.dumps(config))
    nodes.append({'config':configpath,'endpoint':f'http://127.0.0.1:{http}','rpc':f'127.0.0.1:{rpc}','name':config['node_name'],'folder':folder,'process':None})

def start(node):
    logfile=(out/f'{node["name"]}.log').open('ab');handles.append(logfile)
    env=os.environ.copy();env['CHECKPOINT_DISABLE']='1'
    node['process']=subprocess.Popen([str(binary),'agent','-config-file',str(node['config'])],stdout=logfile,stderr=subprocess.STDOUT,env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    record('owned_process_started',node=node['name'],pid=node['process'].pid,endpoint=node['endpoint'])
def stop(node):
    p=node['process']
    if p is not None and p.poll() is None:p.kill();p.wait(timeout=10);record('owned_process_stopped',node=node['name'],pid=p.pid)
async def healthy(client,live,expected_voters=3,timeout=60):
    deadline=time.monotonic()+timeout;last=''
    while time.monotonic()<deadline:
        try:
            for n in live:
                assert n['process'].poll() is None,'owned test process exited'
                r=await client.get(n['endpoint']+'/v1/operator/raft/configuration',params={'consistent':''});r.raise_for_status();servers=r.json()['Servers']
                assert len(servers)==expected_voters and sum(s['Leader'] for s in servers)==1
                assert all(s['Voter'] is True for s in servers) and len({s['ID'] for s in servers})==expected_voters
                r=await client.get(n['endpoint']+'/v1/kv/a8-health',params={'consistent':''});assert r.status_code==404
            return servers
        except Exception as exc:last=repr(exc);await asyncio.sleep(.3)
    raise AssertionError('LAB_QUORUM_TIMEOUT '+last)
async def kv(client,node,key):
    r=await client.get(node['endpoint']+'/v1/kv/'+key,params={'consistent':''});r.raise_for_status()
    return base64.b64decode(r.json()[0]['Value'])

class Provider:
    allowed=True
    async def require_current(self,*args):
        if not self.allowed:raise CommandDenied('AUDIT_EXPIRED_SESSION_DOUBLE')
        return CurrentPrincipal('audit-human',1,'HUMAN',frozenset({'research.control','control.commands.read'}))

async def run():
    gen=str(uuid.uuid4());namespace='lab-a8/'+uuid.uuid4().hex;provider=Provider()
    def command(revision=0):return dict(schema='unified.command.v1',command_id=str(uuid.uuid4()),actor_id='audit-human',idempotency_key=uuid.uuid4().hex,generation=gen,aggregate_type='research',aggregate_id='test-research',expected_revision=revision,action='SetResearchControl',payload={'mode':'LAB_SIMULATION','state':'PAUSED'})
    async with httpx.AsyncClient(timeout=2,trust_env=False) as client:
        for n in nodes[:3]:start(n)
        voters=await healthy(client,nodes[:3]);record('three_actual_persistent_voters_one_leader',servers=voters)
        endpoints=tuple(n['endpoint'] for n in nodes[:3])
        authority=ConsulSessionAuthority(ConsulConfig(endpoints=endpoints,namespace=namespace,isolated_lab=True,ttl_seconds=15,request_timeout=2),client=client)
        commands=CoordinationCommands(authority,gen,principal_provider=provider)
        r=await client.put(nodes[0]['endpoint']+'/v1/kv/'+namespace+'/commands/generation',content=canonical({'generation':gen}));r.raise_for_status()
        lease=await authority.acquire('audit-owner-a');assert lease is not None
        intent=command();receipt=await commands.submit(lease,intent,object());assert receipt['commit_status']=='COMMITTED'
        assert await commands.submit(lease,intent,object())==receipt
        record('actual_grid_commit_and_idempotent_retry',command_id=intent['command_id'],revision=receipt['revision'])
        provider.allowed=False
        try:await commands.submit(lease,command(1),object())
        except CommandDenied:pass
        else:raise AssertionError('expired provider accepted')
        provider.allowed=True;record('expired_provider_denied_no_submit')
        r=await client.get(nodes[0]['endpoint']+'/v1/snapshot');r.raise_for_status();snapshot=r.content
        (out/'native-test-backup.snap').write_bytes(snapshot);record('actual_consul_snapshot_backup',sha256=hashlib.sha256(snapshot).hexdigest(),bytes=len(snapshot))
        raft_leader=next(s for s in voters if s['Leader']);crashed=next(n for n in nodes[:3] if n['name']==raft_leader['Node']);stop(crashed)
        live=[n for n in nodes[:3] if n is not crashed]
        successor=await healthy(client,live);assert next(s for s in successor if s['Leader'])['Node']!=raft_leader['Node']
        assert (await commands.get_command(intent['command_id'],object()))['digest']==receipt['digest']
        record('actual_raft_leader_crash_successor_and_receipt_recovery')
        await authority.release(lease)
        authority2=ConsulSessionAuthority(ConsulConfig(endpoints=tuple(n['endpoint'] for n in live),namespace=namespace,isolated_lab=True,ttl_seconds=15,request_timeout=2),client=client)
        nextlease=await authority2.acquire('audit-owner-b');assert nextlease is not None
        nextcommands=CoordinationCommands(authority2,gen,principal_provider=provider)
        stale=command(1);stale_result=await commands.submit(lease,stale,object());assert stale_result['commit_status']=='UNKNOWN'
        assert (await nextcommands.get_command(stale['command_id'],object()))['commit_status']=='UNKNOWN'
        next_intent=command(1);next_receipt=await nextcommands.submit(nextlease,next_intent,object())
        assert next_receipt['commit_status']=='COMMITTED' and next_receipt['revision']==2
        record('stale_owner_fenced_successor_commits',old_fence=lease.token,new_fence=nextlease.token)
        stop(live[1]);isolated_intent=command(2)
        assert (await nextcommands.submit(nextlease,isolated_intent,object()))['commit_status']=='UNKNOWN'
        record('actual_two_voter_process_loss_noquorum_command_unknown')
        for n in nodes[:3]:stop(n)
        for n in nodes[:3]:start(n)
        restarted=await healthy(client,nodes[:3])
        assert {s['ID'] for s in restarted}=={s['ID'] for s in voters}
        assert (await commands.get_command(intent['command_id'],object()))['digest']==receipt['digest']
        assert (await commands.get_command(next_intent['command_id'],object()))['digest']==next_receipt['digest']
        assert (await commands.get_command(isolated_intent['command_id'],object()))['commit_status']=='UNKNOWN'
        record('all_process_restart_persistent_receipts_recovered_noquorum_intent_absent')
        start(nodes[3]);await healthy(client,[nodes[3]],expected_voters=1)
        restore=await client.put(nodes[3]['endpoint']+'/v1/snapshot',content=snapshot,timeout=10);restore.raise_for_status()
        recovered=json.loads(await kv(client,nodes[3],namespace+'/commands/ids/'+intent['command_id']))
        assert recovered['digest']==receipt['digest'] and recovered['revision']==1
        generation=json.loads(await kv(client,nodes[3],namespace+'/commands/generation'));assert generation=={'generation':gen}
        record('backup_restore_to_independent_test_cluster_digest_verified',restored_revision=recovered['revision'])
        report['result']='PASS';record('isolated_native_component_scenarios_complete')

try:
    asyncio.run(run());report['result']='PASS'
except BaseException as exc:
    report['result']='FAIL';report['error']=repr(exc);record('failure',error=repr(exc));raise
finally:
    for n in nodes:stop(n)
    for h in handles:h.close()
    report['all_owned_processes_stopped']=all(n['process'] is None or n['process'].poll() is not None for n in nodes)
    (out/'native-consul-receipt.json').write_text(json.dumps(report,indent=2))
