"""Independent pure WSGI route/framing/auth/HEAD probes at exact PR25 source."""
import ast,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1];source=ROOT/'work/review2-api';sha='320b5d0894019d72aa8927dc5c4246d28c6e5f3c';base='2df6f5c2f77f4d883bad1a8623dd8375db529be0'
def git(*args):return subprocess.check_output(['git','-C',str(source),*args])
assert git('rev-parse','HEAD').decode().strip()==sha
assert git('rev-parse','HEAD^{tree}').decode().strip()=='7c69196e55afd314e4547d327cf5e1d45eb43d94'
expected={'unified_system/control_api_readonly.py','tests/test_control_api_readonly.py','docs/architecture/control-api-readonly.md','.github/workflows/agent2-control-api.yml'}
assert set(git('diff','--name-only',base,sha).decode().splitlines())==expected
assert all(row.startswith('A\t') for row in git('diff','--name-status',base,sha).decode().splitlines())
name='unified_system/control_api_readonly.py';raw=git('show',sha+':'+name);assert raw==(source/name).read_bytes()
tree=ast.parse(raw);assert [n.names[0].name for n in tree.body if isinstance(n,ast.Import)]==['json','re']
ns={'__name__':'auditor_exact_p0'};exec(compile(raw,'exact-git-p0-boundary','exec'),ns);app=ns['ControlAPIReadOnlyApp']()
class Body:
    def read(self,*a):raise AssertionError('BODY_READ')
    def readline(self,*a):raise AssertionError('BODY_READ')
    def __iter__(self):raise AssertionError('BODY_READ')
sentinel='AUDITOR_FORGED_CREDENTIAL'
routes={'/control/v1/capabilities':('GET',200),'/control/v1/snapshot':('GET',503),'/control/v1/events':('GET',503),'/control/v1/datasets/x/snapshot':('GET',503),'/control/v1/datasets/x/events':('GET',503),'/control/v1/commands/00000000-0000-4000-8000-000000000001':('GET',503),'/control/v1/commands':('POST',503),'/control/v1/sessions':('POST',503),'/control/v1/reauth':('POST',503),'/control/v1/confirmations':('POST',503),'/control/v1/sessions/current':('DELETE',503)}
results=[]
def call(method,path,**extra):
    env={'REQUEST_METHOD':method,'PATH_INFO':path,'QUERY_STRING':'','CONTENT_LENGTH':'','wsgi.input':Body(),'HTTP_AUTHORIZATION':'Bearer '+sentinel,'REMOTE_USER':sentinel,'HTTP_COOKIE':'session='+sentinel,'HTTP_X_ROLE':'SystemOwner'};env.update(extra);seen=[]
    chunks=app(env,lambda status,headers:seen.append((int(status[:3]),dict(headers))));body=b''.join(chunks);assert len(seen)==1
    status,headers=seen[0];assert headers['Cache-Control']=='no-store' and headers['X-Content-Type-Options']=='nosniff'
    assert int(headers['Content-Length'])<4096 and sentinel.encode() not in body
    if method=='HEAD':assert body==b''
    else:
        assert len(body)==int(headers['Content-Length']);value=json.loads(body)
        if status==200:assert value['profile']=='DENY_ONLY' and all(v is False for k,v in value.items() if k.endswith('_available'))
        else:assert set(value)=={'schema','code','request_id','retryable'} and value['request_id'] is None and value['retryable'] is False
    return status
for path,(expected_method,status) in routes.items():
    assert call(expected_method,path)==status
    for method in ['GET','POST','PUT','PATCH','DELETE','OPTIONS','HEAD','TRACE','CONNECT']:
        actual=call(method,path);assert actual==(status if method==expected_method else 405)
        results.append({'path':path,'method':method,'status':actual})
for extra in [{'CONTENT_LENGTH':'1'},{'CONTENT_LENGTH':'00'},{'CONTENT_LENGTH':'0,0'}, {'HTTP_TRANSFER_ENCODING':''},{'HTTP_TRANSFER_ENCODING':'chunked'},{'QUERY_STRING':'cursor='+sentinel},{'CONTENT_LENGTH':True},{'PATH_INFO':None},{'REQUEST_METHOD':'get'}]:
    assert call('GET','/control/v1/capabilities',**extra)==400
for path in ['/control/v1/../capabilities','/control/v1/%2f','/control/v1/я','/control/v1/\x00','/'+'x'*2048]:assert call('GET',path)==400
for method in ['HEAD','GET','POST']:assert call(method,'/control/v1/not-implemented')==404
report={'head':sha,'tree':'7c69196e55afd314e4547d327cf5e1d45eb43d94','base':base,'only_four_new_allocated_paths':True,'source_sha256':hashlib.sha256(raw).hexdigest(),'route_method_cases':results,'framing_auth_head_negatives':'PASS','body_read':'NEVER','profile':'DENY_ONLY','actual_authentication':'UNAVAILABLE','runtime_API':'NOT_QUALIFIED','physical':'BLOCKED','result':'PASS_PURE_WSGI_COMPONENT_ONLY'}
(ROOT/'outputs/phase8/independent-boundary-review.json').write_text(json.dumps(report,indent=2));print(json.dumps({'route_method_cases':len(results),'result':report['result']}))
