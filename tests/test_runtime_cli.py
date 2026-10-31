import copy,hashlib,http.client,json,os,pathlib,socket,tempfile,threading,unittest
from unittest.mock import patch
from unified_system import runtime_cli as cli
from unified_system.module_catalog import MODULE_IDS


def fixture(root):
    exe=root/'runtime.exe';exe.write_bytes(b'fixture executable only')
    code=root/'code';code.mkdir();(code/'worker.py').write_text('fixture')
    pin=hashlib.sha256(exe.read_bytes()).hexdigest()
    specs=[dict(module_id=n,version='1.0.0',api_major=1,dependencies=[],start_timeout=5) for n in sorted(MODULE_IDS)]
    programs={n:dict(argv=[str(exe),str(code/'worker.py')],cwd=str(code),health_url='http://127.0.0.1:19000/ready',executable_sha256=pin,file_pins={'worker.py':'a'*64}) for n in MODULE_IDS}
    return dict(schema='unified.runtime.config.v1',node_id='lab-node',release_id='r1',release_sha256='b'*64,state_root=str(root/'state'),snapshot_path=str(root/'public/runtime.json'),http_port=0,tick_seconds=.1,specs=specs,programs=programs)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='mission3-cli-');self.addCleanup(self.temp.cleanup)
        self.root=pathlib.Path(self.temp.name);self.config=fixture(self.root)
        self.path=self.root/'trusted-runtime.json';self.path.write_text(json.dumps(self.config))
    def test_prepare_default_never_constructs_driver_supervisor_or_spawns(self):
        with patch.object(cli,'make_runtime',side_effect=AssertionError('MUST_NOT_RUN')),patch('subprocess.Popen',side_effect=AssertionError('MUST_NOT_SPAWN')):
            self.assertEqual(cli.main(['--config',str(self.path)]),0)
        self.assertFalse((self.root/'state').exists());self.assertFalse((self.root/'public').exists())
    def test_execute_without_actual_hosted_scope_and_external_pin_is_denied(self):
        for args in (['--execute'],['--scope','ephemeral-ci','--execute'],['--scope','prepare','--execute']):
            with patch.object(cli,'make_runtime',side_effect=AssertionError('MUST_NOT_RUN')):
                self.assertEqual(cli.main(['--config',str(self.path),*args]),1)
        self.assertFalse((self.root/'state').exists())
    def test_strict_config_rejects_missing_extra_alias_and_self_authorization(self):
        for fault in ('missing','extra','alias','authorize','shell','relative','nonfinite'):
            c=copy.deepcopy(self.config)
            if fault=='missing':c['programs'].pop('math')
            if fault=='extra':c['programs']['other']=c['programs']['math']
            if fault=='alias':c['specs'][0]['module_id']='UNIFIED'
            if fault=='authorize':c['authorized']=True
            if fault=='shell':c['programs']['math']['argv']=['/bin/sh','-c','echo unsafe']
            if fault=='relative':c['state_root']='relative'
            if fault=='nonfinite':c['tick_seconds']=float('nan')
            with self.assertRaises(ValueError):cli.validate_config(c)
    def test_office_target_or_external_root_cannot_be_authorized_by_config(self):
        env=dict(GITHUB_ACTIONS='true',RUNNER_ENVIRONMENT='github-hosted',RUNNER_OS='Windows',RUNNER_TEMP=str(self.root))
        for host in ('ADMINIT','LS5','PC4'):
            with self.assertRaises(ValueError):cli.assert_ephemeral(self.config,self.path,env=env,platform='win32',hostname=host)
        c=copy.deepcopy(self.config);c['state_root']=str(self.root.parent/'outside')
        with self.assertRaises(ValueError):cli.assert_ephemeral(c,self.path,env=env,platform='win32',hostname='ci-host')
    def test_cached_loopback_http_never_ticks_and_rejects_mutating_methods(self):
        view=cli.SnapshotView();view.set({'schema':'fixture','ready':False})
        server=cli.status_server(view,port=0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            connection=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=2)
            for method,path,code in [('GET','/internal/v2/runtime',200),('POST','/internal/v2/runtime',405),('GET','/internal/v2/runtime?tick=1',404),('GET','/health',404)]:
                connection.request(method,path);response=connection.getresponse();body=response.read();self.assertEqual(response.status,code)
                if code==200:self.assertEqual(json.loads(body),{'schema':'fixture','ready':False})
            connection.close()
        finally:server.shutdown();server.server_close();thread.join(2)
    def test_finally_stops_owned_runtime_even_when_tick_fails(self):
        class Runtime:
            stopped=False
            def start(self):pass
            def tick(self):raise RuntimeError('PRIVATE_ERROR')
            def stop(self,administrative=True):self.stopped=administrative
            def snapshot(self):return {'schema':'fixture','ready':False}
        r=Runtime()
        with self.assertRaises(RuntimeError):cli.run_runtime(self.config,r,stop_event=threading.Event())
        self.assertTrue(r.stopped)
    def test_stop_failure_still_publishes_unready_final_snapshot(self):
        class Runtime:
            stopped=False
            def start(self):pass
            def stop(self,administrative=True):
                self.stopped=True
                raise ValueError('owned process cleanup required')
            def snapshot(self):return {'schema':'fixture','ready':not self.stopped}
        stop=threading.Event();stop.set()
        cli.write_snapshot(self.config['snapshot_path'],{'schema':'fixture','ready':True})
        with self.assertRaises(ValueError):cli.run_runtime(self.config,Runtime(),stop_event=stop)
        self.assertFalse(json.loads(pathlib.Path(self.config['snapshot_path']).read_text())['ready'])

    def test_atomic_snapshot_has_no_partial_overwrite_and_refuses_links(self):
        path=self.root/'public.json';cli.write_snapshot(path,{'ready':False});cli.write_snapshot(path,{'ready':True})
        self.assertEqual(json.loads(path.read_text()),{'ready':True})
        link=self.root/'link.json'
        try:link.symlink_to(path)
        except OSError:return
        with self.assertRaises(ValueError):cli.write_snapshot(link,{'ready':False})

    def test_initial_http_cache_contains_complete_actual_producer_snapshot(self):
        r=cli.make_runtime(self.config,lambda *_:False)
        entered=threading.Event();release=threading.Event();stop=threading.Event();created=[]
        original_start=r.start
        def wait_start():
            entered.set();release.wait(3);original_start()
        r.start=wait_start
        original_server=cli.status_server
        def capture(*a,**kw):
            server=original_server(*a,**kw);created.append(server);return server
        with patch.object(cli,'status_server',side_effect=capture):
            worker=threading.Thread(target=cli.run_runtime,args=(self.config,r),kwargs={'stop_event':stop});worker.start()
            try:
                self.assertTrue(entered.wait(2))
                connection=http.client.HTTPConnection('127.0.0.1',created[0].server_address[1],timeout=2)
                connection.request('GET','/internal/v2/runtime');response=connection.getresponse();body=json.loads(response.read());connection.close()
                self.assertEqual(body,r.snapshot())
                self.assertEqual(set(body['modules']),MODULE_IDS)
                self.assertTrue(all(m['state']=='STOPPED' for m in body['modules'].values()))
            finally:stop.set();release.set();worker.join(4)
            self.assertFalse(worker.is_alive())

    def test_status_connections_have_absolute_deadline_and_bounded_workers(self):
        import time
        view=cli.SnapshotView();view.set(cli.make_runtime(self.config,lambda *_:False).snapshot())
        server=cli.status_server(view,port=0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();clients=[]
        try:
            for _ in range(12):
                c=socket.create_connection(server.server_address,timeout=2);c.settimeout(.1);clients.append(c)
            time.sleep(.05)
            with server.worker_lock:self.assertGreater(len(server.workers),0);self.assertLessEqual(len(server.workers),4)
            started=time.monotonic()
            while time.monotonic()-started<1.6:
                try:clients[0].sendall(b'G')
                except OSError:break
                time.sleep(.05)
            else:self.fail('slow header kept connection alive beyond absolute deadline')
            self.assertLessEqual(server.max_active_requests,4)
        finally:
            for c in clients:c.close()
            began=time.monotonic();server.shutdown();server.server_close();thread.join(2)
            self.assertLess(time.monotonic()-began,2)
            self.assertFalse(thread.is_alive())
