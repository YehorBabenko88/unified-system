import datetime as dt
import contextlib
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

from unified_system import observer as o

NOW = dt.datetime(2026, 11, 11, 19, tzinfo=dt.timezone.utc)
HEAD = 'bfa3b24d8f209d5e91acfa64819d3ebed4967af7'
ROOT = Path(__file__).resolve().parents[2]


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_real_foreground_once_restart_and_static_dashboard_without_listener(self):
        source = self.root / 'source.json'; config = self.root / 'config.json'; state = self.root / 'state'
        raw = json.dumps({'schema':'unified.observer.source.v1','source_version':HEAD,
            'observed_at':NOW.isoformat(),'facts':[{'section':'development','subject':'Agent 2',
            'field':'AGENT_STATE','scope':'AGENT_STATE','status':'BLOCKED','value':'BLOCKED_COMMUNICATION'}]}).encode()
        source.write_bytes(raw)
        config.write_text(json.dumps({'schema':'unified.observer.config.v1','sources':[{
            'id':'root-export','kind':'snapshot','path':str(source),'source_version':HEAD}]}), encoding='utf-8')
        code = "import sys,socket;sys.path.insert(0,sys.argv[1]);from unified_system.observer.__main__ import main;socket.socket=lambda *a,**k:(_ for _ in ()).throw(AssertionError('LISTENER_OR_NETWORK_FORBIDDEN'));raise SystemExit(main(sys.argv[2:]))"
        command = [sys.executable,'-I','-S','-B','-c',code,str(ROOT),'--config',str(config),
                   '--state-dir',str(state),'--once','--export-dashboard']
        for attempt in range(2):
            result = subprocess.run(command, capture_output=True, timeout=10, check=False)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            receipt = json.loads(result.stdout)
            self.assertFalse(receipt['physical_admission']); self.assertEqual(receipt['notification_transport'], 'DISABLED')
        self.assertEqual(source.read_bytes(), raw)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['config.json','source.json','state'])
        page = (state/'dashboard.html').read_text(encoding='utf-8')
        self.assertIn('Unified Observer Dashboard', page); self.assertIn('BLOCKED_COMMUNICATION', page)
        self.assertNotIn('<script', page); self.assertNotIn('href="/app.css"', page)

    def test_no_unified_owner_module_is_imported_by_observer(self):
        code = "import sys;sys.path.insert(0,sys.argv[1]);import unified_system.observer;bad={'unified_system.mission_controller','unified_system.installer','unified_system.service_postgres','unified_system.node_supervisor_v2','unified_system.lan_transport','unified_system.runtime_process'};assert not bad.intersection(sys.modules)"
        result = subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(ROOT)],capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr.decode())

    def test_foreign_sqlite_header_is_rejected_before_connect_or_write(self):
        state = self.root/'state';state.mkdir();path=state/'observer.sqlite3'
        connection=sqlite3.connect(path)
        try:
            connection.execute('CREATE TABLE user_data(value TEXT)');connection.commit()
        finally:connection.close()
        (state/'owner.json').write_text(json.dumps({'schema':'unified.observer.owned-state.v1',
            'state_id':str(uuid.uuid4())}),encoding='utf-8')
        original=path.read_bytes();real=sqlite3.connect;calls=[]
        def spy(*args,**kwargs):calls.append(args);return real(*args,**kwargs)
        with patch('unified_system.observer.store._connect',spy):
            with self.assertRaises(o.ObserverError):o.ObserverStore(state)
        self.assertEqual(calls,[])
        self.assertEqual(path.read_bytes(),original)

    def test_notification_after_recovery_is_new_but_same_state_poll_is_not(self):
        store=o.ObserverStore(self.root/'state');self.addCleanup(store.close)
        policy=o.SourcePolicy('health','snapshot',HEAD,admitted_axes=frozenset(('LAN_REACHABLE',)))
        for seconds,status in ((0,'FAIL'),(1,'FAIL'),(2,'PASS'),(3,'FAIL')):
            now=NOW+dt.timedelta(seconds=seconds)
            raw=json.dumps({'schema':'unified.observer.source.v1','source_version':HEAD,
                'observed_at':now.isoformat(),'facts':[{'section':'computers','subject':'PC3',
                'field':'LAN_REACHABLE','scope':'LAN_REACHABLE','status':status,'value':None}]}).encode()
            store.ingest(o.parse_snapshot(raw,policy,now),now)
        self.assertEqual(store.queue_counts()['PENDING'],2)

    def test_sent_event_compaction_does_not_erase_deduplication(self):
        store=o.ObserverStore(self.root/'state');self.addCleanup(store.close)
        transport=o.MockNotificationTransport()
        for i in range(514):
            when=NOW+dt.timedelta(days=i);head=format(i,'040x')
            store.enqueue('CI_FAILURE','unified-system','FAIL',head,when)
            self.assertEqual(store.deliver_one(transport,when),'SENT')
        self.assertFalse(store.enqueue('CI_FAILURE','unified-system','FAIL',format(0,'040x'),NOW+dt.timedelta(days=515)))

    def test_mock_delivery_is_labelled_mock_in_persisted_events(self):
        store=o.ObserverStore(self.root/'state');self.addCleanup(store.close)
        store.enqueue('CI_FAILURE','unified-system','FAIL',HEAD,NOW)
        store.deliver_one(o.MockNotificationTransport(),NOW)
        self.assertEqual(store.snapshot(NOW)['events'][0].get('transport'),'MOCK')

    def test_server_thread_start_failure_does_not_wait_for_never_started_server(self):
        from unified_system.observer.__main__ import main
        config=self.root/'config.json';config.write_text(json.dumps({'schema':'unified.observer.config.v1','sources':[]}))
        calls=[]
        class Server:
            def serve_forever(self,**kwargs):pass
            def shutdown(self):calls.append('shutdown')
            def server_close(self):calls.append('close')
        class Thread:
            def __init__(self,*args,**kwargs):pass
            def start(self):raise RuntimeError('THREAD_START_DENIED')
            def is_alive(self):return False
            def join(self,*args):calls.append('join')
        with patch('unified_system.observer.__main__._make_loopback_server',return_value=Server()),patch('unified_system.observer.__main__._ObserverThread',Thread):
            with self.assertRaisesRegex(RuntimeError,'THREAD_START_DENIED'):
                main(['--config',str(config),'--state-dir',str(self.root/'state'),'--serve-loopback'])
        self.assertNotIn('shutdown',calls);self.assertIn('close',calls)

    def test_unknown_cli_argument_does_not_echo_a_secret(self):
        from unified_system.observer.__main__ import main
        error=io.StringIO()
        with contextlib.redirect_stderr(error):
            with self.assertRaises((o.ObserverError,SystemExit)):
                main(['--config','unused','--state-dir','unused','--token=PRIVATE_SENTINEL'])
        self.assertNotIn('PRIVATE_SENTINEL',error.getvalue())


if __name__=='__main__':unittest.main(verbosity=2)
