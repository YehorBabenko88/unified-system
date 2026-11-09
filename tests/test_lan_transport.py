"""Ephemeral certificate tests and real isolated loopback TLS, never office hosts."""
import hashlib
import json
from pathlib import Path
import queue
import shutil
import ssl
import subprocess
import tempfile
import struct
import threading
import time
import unittest
import uuid
from unittest.mock import patch
from unified_system.lan_transport import PeerRegistry, TransportError, ReconnectPolicy, LanTransport, tls_context
from unified_system.network_budget import BandwidthPolicy, NodeBudget

NODES=('LS5','PC1','PC2','PC3','PC4','LS7')


class TLSIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='unified-tls-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        cls.openssl=shutil.which('openssl')
        if cls.openssl is None:
            candidate=Path('C:/Program Files/Git/usr/bin/openssl.exe')
            if candidate.exists():cls.openssl=str(candidate)
        if not cls.openssl:raise RuntimeError('Mandatory isolated TLS tests require OpenSSL executable')
        cls.cluster=str(uuid.uuid4())
        cls.command('req','-x509','-newkey','ec','-pkeyopt','ec_paramgen_curve:P-256','-nodes','-subj','/CN=Isolated CA','-keyout','ca.key','-out','ca.pem','-days','2',
                    '-addext','basicConstraints=critical,CA:TRUE','-addext','keyUsage=critical,keyCertSign,cRLSign')
        cls.pins={}
        for node in (*NODES,'wronguri','wrongeku','expired'):
            cls.command('req','-new','-newkey','ec','-pkeyopt','ec_paramgen_curve:P-256','-nodes','-subj','/CN='+node,'-keyout',node+'.key','-out',node+'.csr')
            uri_node='PC2' if node=='wronguri' else ('PC1' if node in ('wrongeku','expired') else node)
            eku='codeSigning' if node=='wrongeku' else 'serverAuth,clientAuth'
            (cls.root/(node+'.ext')).write_text('basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage='+eku+'\nsubjectAltName=URI:urn:unified:'+cls.cluster+':'+uri_node+'\n')
            if node=='expired':
                (cls.root/'index.txt').write_text('');(cls.root/'serial').write_text('1000\n')
                (cls.root/'ca.conf').write_text('[ca]\ndefault_ca=local\n[local]\ndatabase=index.txt\nserial=serial\nnew_certs_dir=.\ncertificate=ca.pem\nprivate_key=ca.key\ndefault_md=sha256\npolicy=policy\n[policy]\ncommonName=supplied\n')
                cls.command('ca','-batch','-notext','-config','ca.conf','-in',node+'.csr','-out',node+'.pem','-startdate','200101000000Z','-enddate','200102000000Z','-extfile',node+'.ext')
            else:
                cls.command('x509','-req','-in',node+'.csr','-CA','ca.pem','-CAkey','ca.key','-CAcreateserial','-out',node+'.pem','-days','2','-extfile',node+'.ext')
            pem=(cls.root/(node+'.pem')).read_text()
            cls.pins[node]=hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest()

    @classmethod
    def command(cls,*args):
        p=subprocess.run([cls.openssl,*args],cwd=cls.root,capture_output=True,timeout=15)
        if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace'))

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def setUp(self):
        self.transports=[];self.store=tempfile.TemporaryDirectory(prefix='unified-node-budgets-')
        self.enrollments={n:str(uuid.uuid4()) for n in NODES}
    def tearDown(self):
        for t in self.transports:t.close()
        for t in self.transports:
            for c in t.connections.values():
                for thread in c.threads:thread.join(2)
        self.store.cleanup()

    def document(self,port=1):
        return {'schema':'unified.lan-peer-registry.v1','cluster_id':self.cluster,'generation':1,
                'nodes':[{'node_id':n,'enrollment_id':self.enrollments[n],'fingerprints':[self.pins[n]],
                          'roles':['control','ingestion','storage'],'enabled':True,
                          'endpoints':[{'address':'127.0.0.1','port':port,'priority':0,'transport':'lan'}]} for n in NODES]}

    def transport(self,node,registry,cert=None):
        cert=cert or node
        policy=BandwidthPolicy({n:{'rate':64000000,'burst':8000000} for n in NODES},
                               cluster_rate=384000000,cluster_burst=48000000,
                               classes={'control':20,'live':50,'bulk':30})
        budget=NodeBudget.isolated(Path(self.store.name)/(node+str(len(self.transports))+'.sqlite'),node,policy)
        t=LanTransport.isolated(node,registry,
             client_context=tls_context(self.root/'ca.pem',self.root/(cert+'.pem'),self.root/(cert+'.key')),
             server_context=tls_context(self.root/'ca.pem',self.root/(cert+'.pem'),self.root/(cert+'.key'),server=True),budget=budget)
        self.transports.append(t);return t

    def pair(self,*,cert=None,change_registry=None,change_context=None):
        doc=self.document()
        if change_registry:change_registry(doc)
        server=self.transport('LS5',PeerRegistry.from_document(doc));port=server.listen()
        doc['nodes'][0]['endpoints'][0]['port']=port
        client=self.transport('PC1',PeerRegistry.from_document(doc),cert)
        if change_context:client.client_context=change_context(client.client_context)
        outcome=queue.Queue()
        def accept():
            try:outcome.put(server.accept(deadline=time.monotonic()+2))
            except Exception as exc:outcome.put(exc)
        thread=threading.Thread(target=accept);thread.start()
        try:
            c=client.connect('LS5',deadline=time.monotonic()+2)
        finally:thread.join(3)
        s=outcome.get(timeout=1)
        if isinstance(s,Exception):raise s
        return client,server,c,s

    def test_real_mtls_payload_credit_classes_and_actual_byte_accounting(self):
        client,server,c,s=self.pair()
        for cls,size in (('control',100),('live',65536),('bulk',10000),('live',65536)):
            payload=bytes([size%251])*size
            c.send(payload,cls,deadline=time.monotonic()+3)
            received=s.receive(deadline=time.monotonic()+3)
            self.assertEqual((received.peer_id,received.traffic_class,received.payload),('PC1',cls,payload))
        self.assertGreater(client.budget.counters()['tx'],141000)
        self.assertGreaterEqual(server.budget.counters()['rx'],141000)
        self.assertLessEqual(client.memory.used,8388608)

    def test_fingerprint_and_wrong_uri_cert_rejected(self):
        with self.assertRaises(TransportError):
            self.pair(change_registry=lambda d:d['nodes'][0].update(fingerprints=['0'*64]))
        with self.assertRaises(TransportError):
            self.pair(cert='wronguri',change_registry=lambda d:d['nodes'][1].update(fingerprints=[self.pins['wronguri']]))

    def test_wrong_eku_and_expired_cert_rejected(self):
        for cert in ('wrongeku','expired'):
            with self.subTest(cert=cert),self.assertRaises(TransportError):
                self.pair(cert=cert,change_registry=lambda d:d['nodes'][1].update(fingerprints=[self.pins[cert]]))

    def test_missing_client_certificate_rejected(self):
        def no_cert(_):
            ctx=ssl.create_default_context(cafile=str(self.root/'ca.pem'))
            ctx.check_hostname=False;ctx.set_alpn_protocols(['unified-lan-v1']);return ctx
        with self.assertRaises(TransportError):self.pair(change_context=no_cert)

    def test_peer_cannot_spoof_control_role(self):
        client,server,c,s=self.pair(change_registry=lambda d:d['nodes'][1].update(roles=['ingestion']))
        with self.assertRaisesRegex(TransportError,'CLASS_NOT_ADMITTED'):c.send(b'x','control')
        c._emit('APP',0,'control',b'forged')
        end=time.monotonic()+2
        while not s.closed and time.monotonic()<end:time.sleep(.01)
        self.assertTrue(s.closed)
        self.assertIn('CLASS_NOT_ADMITTED',s.error)

    def test_untrusted_ca_rejected_even_with_correct_leaf_pin(self):
        self.command('req','-x509','-newkey','ec','-pkeyopt','ec_paramgen_curve:P-256','-nodes','-subj','/CN=Other CA',
                     '-keyout','other.key','-out','other.pem','-days','2',
                     '-addext','basicConstraints=critical,CA:TRUE','-addext','keyUsage=critical,keyCertSign,cRLSign')
        def other_ca(_):return tls_context(self.root/'other.pem',self.root/'PC1.pem',self.root/'PC1.key')
        with self.assertRaises(TransportError):self.pair(change_context=other_ca)

    def test_close_releases_credit_reservations_and_queue_memory(self):
        client,server,c,s=self.pair()
        c.send(b'data')
        self.assertEqual(s.receive().payload,b'data')
        client.close();server.close()
        for connection in (c,s):
            for thread in connection.threads:thread.join(2)
        self.assertEqual(client.memory.used,0)
        self.assertEqual(server.memory.used,0)

    def test_active_control_heartbeats_keep_idle_data_channel_healthy(self):
        # Exercise expiry of the OLD data-read deadline directly. A compressed
        # .4s peer idle limit tested host scheduling rather than renewal semantics.
        import unified_system.lan_transport as lan
        original=lan._read_frame;ready=threading.Event();control={};data={}
        renewed=queue.Queue();forced=set();seen_control=set();lock=threading.Lock()
        def read(sock,budget,peer,deadline,on_idle=None):
            if on_idle is None:return original(sock,budget,peer,deadline)
            if not ready.wait(3):raise RuntimeError('fixture connection readiness')
            key=id(sock)
            # Reentry proves Connection._reader processed the prior heartbeat
            # and updated last_rx, not merely that bytes reached the wrapper.
            if key in control and key in seen_control:control[key].set()
            if key in data:
                with lock:
                    first=key not in forced;forced.add(key)
                if first:
                    if not data[key].wait(3):raise RuntimeError('fixture control heartbeat readiness')
                    def idle():
                        healthy=on_idle();renewed.put(healthy);return healthy
                    return original(sock,budget,peer,time.monotonic()-1,on_idle=idle)
            result=original(sock,budget,peer,deadline,on_idle=on_idle)
            if key in control and result[0]['kind'] in ('PING','PONG'):seen_control.add(key)
            return result
        with patch('unified_system.lan_transport.HEARTBEAT_INTERVAL',.05),patch.object(lan,'_read_frame',side_effect=read):
            client,server,c,s=self.pair()
            for connection in (c,s):
                heartbeat=threading.Event()
                control[id(connection.channels['control'])]=heartbeat
                data[id(connection.channels['data'])]=heartbeat
            ready.set()
            try:
                self.assertIs(renewed.get(timeout=3),True)
                self.assertIs(renewed.get(timeout=3),True)
                self.assertFalse(c.closed,c.error);self.assertFalse(s.closed,s.error)
                c.send(b'after idle');self.assertEqual(s.receive().payload,b'after idle')
                s.send(b'reply');self.assertEqual(c.receive().payload,b'reply')
            finally:client.close();server.close()

    def test_expired_idle_peer_without_activity_still_closes_real_tls(self):
        import unified_system.lan_transport as lan
        original=lan._read_frame;ready=threading.Event();data=set()
        def read(sock,budget,peer,deadline,on_idle=None):
            if on_idle is None:return original(sock,budget,peer,deadline)
            if not ready.wait(3):raise RuntimeError('fixture connection readiness')
            if id(sock) in data:
                return original(sock,budget,peer,time.monotonic()-1,on_idle=lambda:False)
            return original(sock,budget,peer,deadline,on_idle=on_idle)
        with patch.object(lan,'_read_frame',side_effect=read):
            client,server,c,s=self.pair();data.update((id(c.channels['data']),id(s.channels['data'])))
            ready.set()
            try:
                self.assertTrue(c.closed_event.wait(3));self.assertTrue(s.closed_event.wait(3))
                self.assertIn('DEADLINE',(c.error,s.error))
            finally:client.close();server.close()

    def test_revoked_pin_during_final_hello_cannot_install_connection(self):
        doc=self.document();server=self.transport('LS5',PeerRegistry.from_document(doc));port=server.listen()
        doc['nodes'][0]['endpoints'][0]['port']=port
        client=self.transport('PC1',PeerRegistry.from_document(doc));original=client._hello
        def hello(*args,**kwargs):
            result=original(*args,**kwargs)
            if args[2]=='data':
                revised=json.loads(json.dumps(doc));revised['generation']=2
                revised['nodes'][0]['fingerprints']=['0'*64]
                client.update_registry(PeerRegistry.from_document(revised))
            return result
        out=queue.Queue()
        def accept():
            try:out.put(server.accept(deadline=time.monotonic()+3))
            except Exception as exc:out.put(exc)
        t=threading.Thread(target=accept);t.start()
        try:
            with patch.object(client,'_hello',side_effect=hello),self.assertRaises(TransportError):
                client.connect('LS5',deadline=time.monotonic()+3)
        finally:t.join(4)

    def test_sender_waiting_for_memory_does_not_reset_stream_created_while_waiting(self):
        client,server,c,s=self.pair();waiting=threading.Event();result=queue.Queue()
        held=8388608-1;self.assertTrue(client.memory.take(held));original=client.memory.take
        def take(size):
            if size==64:waiting.set()
            return original(size)
        def send():
            try:result.put(c.send(b'w'*64,stream_id=3,deadline=time.monotonic()+3))
            except Exception as exc:result.put(exc)
        with patch.object(client.memory,'take',side_effect=take):
            t=threading.Thread(target=send);t.start()
            try:
                self.assertTrue(waiting.wait(1))
                c.send(b'x',stream_id=3,deadline=time.monotonic()+2)
                self.assertEqual(s.receive().payload,b'x')
            finally:client.memory.release(held)
            t.join(4)
        out=result.get(timeout=1)
        if isinstance(out,Exception):raise out
        self.assertEqual(s.receive().payload,b'w'*64)

    def test_concurrent_registry_updates_cannot_restore_older_revoked_pin(self):
        doc=self.document();client=self.transport('PC1',PeerRegistry.from_document(doc))
        high=json.loads(json.dumps(doc));high['generation']=3;high['nodes'][0]['fingerprints']=['0'*64]
        low=json.loads(json.dumps(doc));low['generation']=2
        real=client.lock;entered={n:threading.Event() for n in ('high','low')};high_done=threading.Event();out=queue.Queue()
        class OrderedLock:
            def __enter__(self):
                name=threading.current_thread().name;entered[name].set()
                if name=='low':high_done.wait(2)
                real.acquire()
            def __exit__(self,*args):real.release()
        def update(name,document):
            try:client.update_registry(PeerRegistry.from_document(document));out.put((name,None))
            except Exception as exc:out.put((name,exc))
            finally:
                if name=='high':high_done.set()
        with real,patch.object(client,'lock',OrderedLock()):
            a=threading.Thread(target=update,name='high',args=('high',high));a.start();self.assertTrue(entered['high'].wait(1))
            b=threading.Thread(target=update,name='low',args=('low',low));b.start();self.assertTrue(entered['low'].wait(1))
        a.join(3);b.join(3)
        self.assertEqual(client.registry.generation,3)
        result=dict(out.get(timeout=1) for _ in range(2))
        self.assertIsNone(result['high']);self.assertIsInstance(result['low'],TransportError)

    def test_credit_backpressure_and_control_lane_while_data_waits(self):
        client,server,c,s=self.pair()
        c.send(b'x'*65536,deadline=time.monotonic()+2)
        with self.assertRaises(TransportError):c.send(b'y'*65536,deadline=time.monotonic()+.1)
        c.send(b'control','control',deadline=time.monotonic()+2)
        with s.cv:
            end=time.monotonic()+2
            while not any(d.traffic_class=='control' for d in s.incoming) and not s.closed and time.monotonic()<end:s.cv.wait(.01)
        self.assertEqual(s.receive().payload,b'control')
        self.assertEqual(s.receive().payload,b'x'*65536)
        c.send(b'z'*65536,deadline=time.monotonic()+2)
        self.assertEqual(s.receive().payload,b'z'*65536)

    def test_malformed_frame_rejected_before_payload_allocation(self):
        client,server,c,s=self.pair()
        with c.locks['data']:c.channels['data'].sendall(struct.pack('!HI',4097,10000000))
        end=time.monotonic()+2
        while not s.closed and time.monotonic()<end:time.sleep(.01)
        self.assertTrue(s.closed)
        self.assertIn('FRAME_BOUNDS',s.error)

    def test_control_writer_progresses_while_data_budget_waits(self):
        client,server,c,s=self.pair();entered=threading.Event();release=threading.Event();out=queue.Queue()
        original=client.budget.wait_take
        def wait(direction,peer,cls,size,**kwargs):
            if direction=='tx' and cls=='live':entered.set();release.wait(2)
            return original(direction,peer,cls,size,**kwargs)
        def send_data():
            try:out.put(c.send(b'data',deadline=time.monotonic()+3))
            except Exception as exc:out.put(exc)
        with patch.object(client.budget,'wait_take',side_effect=wait):
            thread=threading.Thread(target=send_data);thread.start()
            try:
                self.assertTrue(entered.wait(1))
                c.send(b'priority','control',deadline=time.monotonic()+.5)
                self.assertEqual(s.receive().payload,b'priority')
            finally:release.set();thread.join(4)
        result=out.get(timeout=1)
        if isinstance(result,Exception):raise result

    def test_changed_endpoint_reconnect_keeps_certificate_identity_no_replay(self):
        client,server,c,s=self.pair()
        c.send(b'old');self.assertEqual(s.receive().payload,b'old')
        old_nonce=c.nonce;server.close()
        replacement=self.transport('LS5',server.registry);port=replacement.listen()
        doc=self.document(port);doc['generation']=2;client.update_registry(PeerRegistry.from_document(doc))
        out=queue.Queue()
        def accept():
            try:out.put(replacement.accept(deadline=time.monotonic()+3))
            except Exception as exc:out.put(exc)
        t=threading.Thread(target=accept);t.start()
        new=client.connect('LS5',deadline=time.monotonic()+3);t.join(4);remote=out.get(timeout=1)
        if isinstance(remote,Exception):raise remote
        self.assertNotEqual(new.nonce,old_nonce)
        with self.assertRaisesRegex(TransportError,'DEADLINE'):remote.receive(deadline=time.monotonic()+.05)
        new.send(b'new');self.assertEqual(remote.receive().peer_id,'PC1')

    def test_registry_revocation_and_cancellation(self):
        client,server,c,s=self.pair()
        stop=threading.Event();stop.set()
        with self.assertRaises(TransportError):c.send(b'x',cancel=stop)
        doc=self.document();doc['generation']=2;doc['nodes'][0]['enabled']=False
        client.update_registry(PeerRegistry.from_document(doc))
        self.assertTrue(c.closed)
        with self.assertRaises(TransportError):c.send(b'x')

    def test_isolation_rejects_nonloopback_even_if_registry_admits_it(self):
        doc=self.document();doc['nodes'][0]['endpoints'][0]['address']='192.168.2.173'
        client=self.transport('PC1',PeerRegistry.from_document(doc))
        with self.assertRaisesRegex(TransportError,'ISOLATION_BOUNDARY'):client.connect('LS5')
        with self.assertRaisesRegex(TransportError,'NATIVE_RUNTIME'):LanTransport.runtime()

    def test_six_real_isolated_nodes_independent_of_tailscale(self):
        doc=self.document();server=self.transport('LS5',PeerRegistry.from_document(doc));port=server.listen()
        doc['nodes'][0]['endpoints'][0]['port']=port
        for node in NODES[1:]:
            client=self.transport(node,PeerRegistry.from_document(doc));outcome=queue.Queue()
            def accept():
                try:outcome.put(server.accept(deadline=time.monotonic()+3))
                except Exception as exc:outcome.put(exc)
            thread=threading.Thread(target=accept);thread.start()
            c=client.connect('LS5',deadline=time.monotonic()+3);thread.join(4)
            s=outcome.get(timeout=1)
            if isinstance(s,Exception):raise s
            c.send(node.encode(),deadline=time.monotonic()+3)
            self.assertEqual(s.receive().payload,node.encode())
        self.assertEqual(len(server.connections),5)


class RegistryTests(unittest.TestCase):
    def test_duplicate_or_ip_claim_cannot_be_node_identity(self):
        with self.assertRaises(TransportError):
            PeerRegistry.from_document({'schema':'unified.lan-peer-registry.v1','nodes':[]})

    def test_backoff_is_bounded_auth_failure_not_retryable(self):
        p=ReconnectPolicy(seed=1)
        self.assertTrue(0 <= p.delay(10) <= 30)
        self.assertFalse(p.retryable('AUTH_REJECTED'))
        self.assertTrue(p.retryable('DISCONNECTED'))


if __name__=='__main__': unittest.main()
