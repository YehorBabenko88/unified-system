import io,json,sqlite3,tempfile,unittest,subprocess,shutil
from contextlib import closing
from unittest.mock import patch
from pathlib import Path
from unified_system.installation_progress import InstallationProgress
from unified_system.installation_ui import InstallationBootstrapApp, MAX_JSON_RESPONSE_BYTES
from unified_system.journal import Journal

class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'progress.db'
        self.progress=InstallationProgress.create(self.path,'installation','node','a'*64)
        self.app=InstallationBootstrapApp(self.progress,'127.0.0.1:18765')
    def call(self,path='/api/v1/installation',**changes):
        env={'REQUEST_METHOD':'GET','HTTP_HOST':'127.0.0.1:18765','PATH_INFO':path,'QUERY_STRING':'','wsgi.input':io.BytesIO(b'')};env.update(changes)
        seen={}
        def start(status,headers):seen.update(code=int(status.split()[0]),headers=dict(headers))
        body=b''.join(self.app(env,start));return seen['code'],body,seen['headers']
    def append(self,**changes):
        value=dict(receipt_id='r1',operation_id='o1',correlation_id='c1',timestamp_ms=1000,phase='VERIFY',outcome='PASS');value.update(changes);self.progress.append(**value)
    def test_real_source_counts_and_read_only_identity(self):
        self.append(done=2,total=8)
        code,body,_=self.call();data=json.loads(body)
        self.assertEqual(code,200);self.assertEqual(data['snapshot'],self.progress.snapshot());self.assertEqual(data['snapshot']['events'][0]['percentage'],25)
        self.assertFalse(data['snapshot']['authority']);self.assertEqual(data['snapshot']['readiness'],'NOT_PROVEN')
    def test_oversized_snapshot_fixed_bounded_unavailable(self):
        self.append()
        snapshot=self.progress.snapshot()
        event=snapshot['events'][0]
        snapshot['events']=[dict(event,receipt_id='PUBLIC_OVERSIZED_EVENT_'+str(index)) for index in range(5000)]
        self.assertGreater(len(json.dumps(snapshot).encode('utf-8')),MAX_JSON_RESPONSE_BYTES)
        with patch.object(InstallationProgress,'snapshot',return_value=snapshot):
            code,body,headers=self.call()
        self.assertEqual(code,503);self.assertLess(len(body),512)
        self.assertEqual(json.loads(body),{'status':'UNAVAILABLE','error_code':'SOURCE_UNAVAILABLE','authority':False})
        self.assertNotIn(b'PUBLIC_OVERSIZED_EVENT',body);self.assertEqual(int(headers['Content-Length']),len(body));self.assert_security(headers)

    def test_actual_append_after_app_creation_is_seen(self):
        self.assertEqual(json.loads(self.call()[1])['snapshot']['events'],[])
        self.append();self.assertEqual(len(json.loads(self.call()[1])['snapshot']['events']),1)
    def test_request_boundaries_no_body_read(self):
        class NeverRead:
            def read(self,*args):raise AssertionError('must not read body')
        cases=[({'HTTP_HOST':'evil.invalid'},400),({'HTTP_HOST':'localhost:18765'},400),({'HTTP_HOST':'127.0.0.1:18766'},400),({'QUERY_STRING':'token=secret'},400),({'HTTP_ORIGIN':'http://127.0.0.1:18765'},400),({'HTTP_TRANSFER_ENCODING':'chunked'},400),({'CONTENT_LENGTH':'1'},400),({'CONTENT_LENGTH':'999999999999999999999'},400),({'CONTENT_LENGTH':'-1'},400),({'CONTENT_LENGTH':'bad'},400),({'wsgi.input_terminated':True},400),({'REQUEST_METHOD':'POST'},405),({'REQUEST_METHOD':'OPTIONS'},405)]
        for changes,expected in cases:
            with self.subTest(changes=changes):
                code,body,headers=self.call(**(changes|{'wsgi.input':NeverRead()}));self.assertEqual(code,expected);self.assertNotIn(b'secret',body);self.assert_security(headers)
    def assert_security(self,headers):
        self.assertEqual(headers['Cache-Control'],'no-store');self.assertEqual(headers['X-Content-Type-Options'],'nosniff');self.assertEqual(headers['Referrer-Policy'],'no-referrer')
        self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy']);self.assertNotIn('unsafe-inline',headers['Content-Security-Policy'])
    def test_static_ui_assets_honest_disabled_controls_and_safe_dom(self):
        for path,mime in [('/','text/html'),('/bootstrap.js','application/javascript'),('/bootstrap.css','text/css')]:
            code,body,headers=self.call(path);self.assertEqual(code,200);self.assertIn(mime,headers['Content-Type']);self.assert_security(headers)
        html=self.call('/')[1].decode();script=self.call('/bootstrap.js')[1].decode()
        for word in ('Continue','Retry','Stop','NOT_PROVEN','Export diagnostics','View error'):self.assertIn(word,html)
        self.assertEqual(html.count(' disabled'),3);self.assertIn('authenticated installer controller',html)
        self.assertIn('textContent',script);self.assertNotIn('innerHTML',script);self.assertIn('createObjectURL',script);self.assertIn('addEventListener',script)
        self.assertNotIn('window.open',script);self.assertNotIn('location.href',script)
    def test_missing_and_tampered_source_503_no_false_progress(self):
        self.path.unlink();code,body,_=self.call();self.assertEqual(code,503);self.assertEqual(json.loads(body)['status'],'UNAVAILABLE');self.assertNotIn(b'percentage',body)
    def test_secret_or_xss_receipt_rejected_not_echoed(self):
        Journal(self.path).append('OBSERVING',{'message':'<img src=x onerror=alert(1)> PRIVATE'})
        code,body,_=self.call();self.assertEqual(code,503);self.assertNotIn(b'PRIVATE',body);self.assertNotIn(b'<img',body)
    def test_tamper_and_unknown_route(self):
        with closing(sqlite3.connect(self.path)) as db:db.execute("UPDATE transitions SET digest='bad'");db.commit()
        self.assertEqual(self.call()[0],503);self.assertEqual(self.call('/execute')[0],404)
    @unittest.skipUnless(shutil.which('node'),'Node required for isolated DOM harness')
    def test_browser_script_counts_diagnostics_and_error_controls(self):
        self.append(done=2,total=8)
        payload=json.loads(self.call()[1]);script=self.call('/bootstrap.js')[1].decode()
        harness=r"""
process.stderr.write('UNIFIED_NODE:ENTRY\n');
const vm=require('node:vm'),assert=require('node:assert/strict');
let input='';process.stdin.on('data',chunk=>input+=chunk);process.stdin.on('end',async()=>{
 process.stderr.write('UNIFIED_NODE:STDIN_END\n');
 const {script,payload}=JSON.parse(input),nodes={},timers=[];let exported='',clicked=false,unavailable=false;
 process.stderr.write('UNIFIED_NODE:PARSED\n');
 function node(id){return nodes[id]??=( {textContent:'',hidden:false,removeAttribute(){delete this.value;},addEventListener(name,fn){this[name]=fn;}});}
 const document={getElementById:node,body:{appendChild(){}},createElement(){return {click(){clicked=true;},remove(){}};}};
 const context={document,window:{setTimeout(fn){timers.push(fn);}},URL:{createObjectURL(blob){exported=blob.parts.join('');return 'blob:test';},revokeObjectURL(){}},Blob:class{constructor(parts){this.parts=parts;}},
 fetch:async()=>({ok:!unavailable,json:async()=>unavailable?{status:'UNAVAILABLE'}:payload})};
 vm.runInNewContext(script,context);process.stderr.write('UNIFIED_NODE:VM_RETURN\n');await new Promise(setImmediate);
 process.stderr.write('UNIFIED_NODE:FIRST_SETTLED\n');
 assert.equal(node('counts').textContent,'2 / 8 (25%)');assert.equal(node('progress').value,25);assert.equal(node('progress').hidden,false);
 node('error').textContent='overwritten';node('view-error').click();assert.equal(node('error').textContent,'NONE');
 node('export').click();assert(clicked);assert.deepEqual(JSON.parse(exported).snapshot,payload.snapshot);
 unavailable=true;const refresh=timers.shift();refresh();await new Promise(setImmediate);
 process.stderr.write('UNIFIED_NODE:SECOND_SETTLED\n');
 assert.equal(node('status').textContent,'UNAVAILABLE');assert.equal(node('progress').hidden,true);assert.equal(node('progress').value,undefined);
 node('view-error').click();assert.equal(node('error').textContent,'SOURCE_UNAVAILABLE');
 node('export').click();assert.equal(JSON.parse(exported).status,'UNAVAILABLE');assert(!exported.includes('percentage'));
 process.stderr.write('UNIFIED_NODE:DONE\n');
});
"""
        from tests.native_phase_diagnostics import run_node_phased
        result=run_node_phased([shutil.which('node'),'-e',harness],input=json.dumps({'script':script,'payload':payload}))
        self.assertEqual(result.returncode,0,result.stderr)

    def test_reject_provider_and_nonloopback_construction(self):
        for source,host in [(lambda:{},'127.0.0.1:18765'),(self.progress,'0.0.0.0:18765'),(self.progress,'127.0.0.1:0'),(self.progress,'127.0.0.1:65536'),(self.progress,'127.0.0.1:018765')]:
            with self.subTest(host=host),self.assertRaises(ValueError):InstallationBootstrapApp(source,host)

if __name__=='__main__':unittest.main()
