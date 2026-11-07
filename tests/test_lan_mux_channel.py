"""Bounded fragment contracts; real TLS cases follow negotiated record integration."""
import hashlib
import struct
import unittest
import uuid

from unified_system import lan_mux_channel as mux
from unified_system.lan_transport import TransportError


class FragmentContractTests(unittest.TestCase):
    def setUp(self):
        self.nonce=str(uuid.uuid4())
        self.binding=mux.MuxBinding(str(uuid.uuid4()),1,str(uuid.uuid4()),'a'*64)
        self.transfer=str(uuid.uuid4())

    def fragment(self,total,index,chunk,kind=3,digest=None):
        return mux.encode_fragment(self.binding,self.nonce,self.transfer,kind,total,index,
                                   digest or hashlib.sha256(chunk).digest(),chunk)

    def test_exact_header_and_derived_chunk_count_residual(self):
        self.assertEqual(mux.HEADER.size,160)
        self.assertEqual(mux.CHUNK_SIZE,65536-mux.HEADER.size)
        for total in (1,mux.CHUNK_SIZE,mux.CHUNK_SIZE+1,133120,133128,2097152):
            kind=4 if total>133128 else 3
            count=(total+mux.CHUNK_SIZE-1)//mux.CHUNK_SIZE
            for index in range(count):
                size=min(mux.CHUNK_SIZE,total-index*mux.CHUNK_SIZE)
                raw=self.fragment(total,index,b'x'*size,kind)
                self.assertLessEqual(len(raw),65536)
                part=mux.decode_fragment(raw,self.binding,self.nonce,{kind})
                self.assertEqual((part.total,part.index,part.count,len(part.chunk)),(total,index,count,size))

    def test_wrong_session_stream_attempt_profile_and_kind_rejected(self):
        raw=self.fragment(1,0,b'x')
        with self.assertRaises(mux.MuxError):mux.decode_fragment(raw,self.binding,str(uuid.uuid4()),{3})
        for binding in (mux.MuxBinding(self.binding.connection_id,1,str(uuid.uuid4()),'a'*64),
                        mux.MuxBinding(self.binding.connection_id,2,self.binding.stream_attempt_id,'a'*64),
                        mux.MuxBinding(self.binding.connection_id,1,self.binding.stream_attempt_id,'b'*64)):
            with self.assertRaises(mux.MuxError):mux.decode_fragment(raw,binding,self.nonce,{3})
        with self.assertRaises(mux.MuxError):mux.decode_fragment(raw,self.binding,self.nonce,{2})

    def test_malformed_length_count_index_flags_magic_and_kind_rejected(self):
        raw=self.fragment(1,0,b'x');fields=list(mux.HEADER.unpack(raw[:mux.HEADER.size]))
        for position,value in ((0,b'NOPE'),(1,2),(2,9),(3,1),(10,0),(11,1),(12,2),(13,2)):
            bad=list(fields);bad[position]=value
            with self.subTest(position=position),self.assertRaises(mux.MuxError):
                mux.decode_fragment(mux.HEADER.pack(*bad)+b'x',self.binding,self.nonce,{3})
        for bad in (b'',raw[:-1],raw+b'x'):
            with self.assertRaises(mux.MuxError):mux.decode_fragment(bad,self.binding,self.nonce,{3})

    def test_nonfinal_short_chunk_and_kind_oversize_rejected(self):
        with self.assertRaises(mux.MuxError):self.fragment(mux.CHUNK_SIZE+1,0,b'x')
        with self.assertRaises(mux.MuxError):self.fragment(133129,0,b'x'*mux.CHUNK_SIZE,3)
        with self.assertRaises(mux.MuxError):self.fragment(2097153,0,b'x'*mux.CHUNK_SIZE,4)

    def test_binding_rejects_noncanonical_ids_bool_epoch_and_invalid_hash(self):
        for epoch in (0,True,2**63):
            with self.assertRaises(mux.MuxError):mux.MuxBinding(str(uuid.uuid4()),epoch,str(uuid.uuid4()),'a'*64)
        with self.assertRaises(mux.MuxError):mux.MuxBinding('provisional',1,str(uuid.uuid4()),'a'*64)



class ReassemblyContractTests(unittest.TestCase):
    def setUp(self):
        from unified_system.lan_transport import _Memory
        self.memory=_Memory();self.now=[100.0];self.nonce=str(uuid.uuid4())
        self.binding=mux.MuxBinding(str(uuid.uuid4()),1,str(uuid.uuid4()),'a'*64)
        self.rx=mux.Reassembler(self.binding,self.nonce,self.memory,{3,4},clock=lambda:self.now[0])
        self.addCleanup(self.rx.close)

    def frames(self,payload,kind=3,*,digest=None,transfer=None):
        digest=digest or hashlib.sha256(payload).digest();transfer=transfer or str(uuid.uuid4())
        return [mux.encode_fragment(self.binding,self.nonce,transfer,kind,len(payload),i,digest,payload[i*mux.CHUNK_SIZE:(i+1)*mux.CHUNK_SIZE])
                for i in range((len(payload)+mux.CHUNK_SIZE-1)//mux.CHUNK_SIZE)]

    def test_complete_hash_verified_and_memory_retained_until_handoff(self):
        payload=b'x'*133128;frames=self.frames(payload)
        for frame in frames[:-1]:
            self.rx.push(frame);self.assertIsNone(self.rx.pop())
        self.assertEqual(self.memory.used,2*len(payload))
        self.rx.push(frames[-1]);self.assertEqual(self.memory.used,2*len(payload))
        message=self.rx.pop();self.assertEqual((message.kind,message.payload),(3,payload));self.assertEqual(self.memory.used,0)

    def test_wrong_whole_hash_rejects_no_partial_and_releases(self):
        frames=self.frames(b'x'*133128,digest=b'0'*32)
        for frame in frames[:-1]:self.rx.push(frame)
        with self.assertRaisesRegex(mux.MuxError,'HASH'):self.rx.push(frames[-1])
        self.assertEqual(self.memory.used,0)
        with self.assertRaises(mux.MuxError):self.rx.push(frames[0])

    def test_absolute_assembly_deadline_not_refreshed_and_close_releases(self):
        frames=self.frames(b'x'*133128);self.rx.push(frames[0]);self.now[0]+=9
        self.rx.push(frames[1]);self.now[0]+=1.01
        with self.assertRaisesRegex(mux.MuxError,'DEADLINE'):self.rx.check_deadline()
        self.assertEqual(self.memory.used,0)

    def test_gap_duplicate_interleaving_reject_and_release(self):
        for mode in ('gap','duplicate','interleave'):
            from unified_system.lan_transport import _Memory
            memory=_Memory();rx=mux.Reassembler(self.binding,self.nonce,memory,{3})
            frames=self.frames(b'x'*133128);rx.push(frames[0])
            bad=frames[2] if mode=='gap' else frames[0] if mode=='duplicate' else self.frames(b'x'*133128)[1]
            with self.assertRaises(mux.MuxError):rx.push(bad)
            self.assertEqual(memory.used,0)

    def test_shared_node_pool_denies_before_allocation_and_queue_bound(self):
        self.assertTrue(self.memory.take(8388608))
        with self.assertRaisesRegex(mux.MuxError,'MEMORY'):self.rx.push(self.frames(b'x')[0])
        self.assertEqual(self.memory.used,8388608);self.memory.release(8388608)

class MuxTlsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_lan_transport as fixtures
        cls.fixtures=fixtures;fixtures.TLSIsolationTests.setUpClass()

    @classmethod
    def tearDownClass(cls):cls.fixtures.TLSIsolationTests.tearDownClass()

    def setUp(self):
        self.fixture=self.fixtures.TLSIsolationTests();self.fixture.setUp()

    def tearDown(self):self.fixture.tearDown()

    def pair(self,server_protocol='unified-lan-mux-v1',client_protocol='unified-lan-mux-v1'):
        from pathlib import Path
        import queue,threading,time
        from unified_system.lan_transport import LanTransport,PeerRegistry,tls_context
        from unified_system.network_budget import BandwidthPolicy,NodeBudget
        f=self.fixture;doc=f.document()
        for row in doc['nodes']:row['roles']=['control']
        def transport(node,protocol):
            policy=BandwidthPolicy({n:{'rate':64000000,'burst':8000000} for n in self.fixtures.NODES},cluster_rate=384000000,cluster_burst=48000000,classes={'control':80,'live':10,'bulk':10})
            budget=NodeBudget.isolated(Path(f.store.name)/(node+'.sqlite'),node,policy)
            t=LanTransport.isolated(node,PeerRegistry.from_document(doc),budget=budget,application_protocol=protocol,
                client_context=tls_context(f.root/'ca.pem',f.root/(node+'.pem'),f.root/(node+'.key'),application_protocol=protocol),
                server_context=tls_context(f.root/'ca.pem',f.root/(node+'.pem'),f.root/(node+'.key'),server=True,application_protocol=protocol))
            f.transports.append(t);return t
        server=transport('LS5',server_protocol);port=server.listen();doc['nodes'][0]['endpoints'][0]['port']=port
        client=transport('PC1',client_protocol);q=queue.Queue()
        def accept():
            try:q.put(server.accept(deadline=time.monotonic()+3))
            except Exception as exc:q.put(exc)
        thread=threading.Thread(target=accept);thread.start()
        try:c=client.connect('LS5',deadline=time.monotonic()+3)
        finally:thread.join(4)
        s=q.get(timeout=1)
        if isinstance(s,Exception):raise s
        return client,server,c,s

    def test_negotiated_control_only_data_record_and_app_demux(self):
        import time
        client,server,c,s=self.pair();raw=b'x'*65536
        before=client.budget.counters()['tx'];c.send_mux_fragment(raw,deadline=time.monotonic()+3)
        with self.assertRaises(TransportError):s.receive(deadline=time.monotonic()+.03)
        self.assertEqual(s.receive_mux_fragment(deadline=time.monotonic()+2).payload,raw)
        self.assertGreater(client.budget.counters()['tx']-before,len(raw))
        c.send(b'legacy-control','control');self.assertEqual(s.receive().payload,b'legacy-control')
        with self.assertRaises(TransportError):c.send(b'x'*4097,'control')
        with self.assertRaises(TransportError):c.send(b'x','live')

    def test_legacy_session_rejects_new_record_without_fallback(self):
        client,server,c,s=self.pair('unified-lan-v1','unified-lan-v1')
        with self.assertRaisesRegex(TransportError,'MUX_NOT_NEGOTIATED'):c.send_mux_fragment(b'x')

    def test_mismatched_alpn_rejected(self):
        with self.assertRaises(TransportError):self.pair('unified-lan-mux-v1','unified-lan-v1')

    def channels(self):
        import time
        client,server,c,s=self.pair()
        binding=mux.MuxBinding(str(uuid.uuid4()),1,str(uuid.uuid4()),'a'*64)
        left=mux.LanMuxChannel.isolated(c,binding,allowed_send_kinds={1,2,3,4},expected_receive_kinds={1,2,3,4})
        right=mux.LanMuxChannel.isolated(s,binding,allowed_send_kinds={1,2,3,4},expected_receive_kinds={1,2,3,4})
        self.addCleanup(left.close);self.addCleanup(right.close)
        return client,server,c,s,left,right,binding

    def test_complete_large_messages_real_mtls_and_budget_overhead(self):
        import queue,threading,time
        client,server,c,s,left,right,binding=self.channels()
        for kind,size in ((3,133128),(4,2097152)):
            payload=b'Z'*size;outcome=queue.Queue();beforetx=client.budget.counters()['tx'];beforerx=server.budget.counters()['rx']
            def send():
                try:outcome.put(left.send(kind,payload,deadline=time.monotonic()+5))
                except Exception as exc:outcome.put(exc)
            t=threading.Thread(target=send);t.start();got=right.receive(deadline=time.monotonic()+5);t.join(5)
            self.assertFalse(t.is_alive());result=outcome.get(timeout=1)
            if isinstance(result,Exception):raise result
            self.assertEqual((got.kind,got.transfer_id,got.payload),(kind,result,payload))
            minimum=size+mux.HEADER.size*((size+mux.CHUNK_SIZE-1)//mux.CHUNK_SIZE)
            self.assertGreater(client.budget.counters()['tx']-beforetx,minimum)
            self.assertGreater(server.budget.counters()['rx']-beforerx,minimum)
        left.close();right.close();self.assertEqual((client.memory.used,server.memory.used),(0,0))

    def test_real_hash_failure_no_complete_payload_and_memory_cleanup(self):
        import time
        client,server,c,s,left,right,binding=self.channels();payload=b'x'*133128;transfer=str(uuid.uuid4())
        for i in range((len(payload)+mux.CHUNK_SIZE-1)//mux.CHUNK_SIZE):
            chunk=payload[i*mux.CHUNK_SIZE:(i+1)*mux.CHUNK_SIZE]
            c.send_mux_fragment(mux.encode_fragment(binding,c.nonce,transfer,3,len(payload),i,b'0'*32,chunk),deadline=time.monotonic()+3)
        with self.assertRaisesRegex(mux.MuxError,'HASH'):right.receive(deadline=time.monotonic()+3)
        self.assertEqual(server.memory.used,0)

    def test_real_partial_disconnect_discards_incomplete_transfer(self):
        import time
        client,server,c,s,left,right,binding=self.channels();payload=b'x'*133128
        raw=mux.encode_fragment(binding,c.nonce,str(uuid.uuid4()),3,len(payload),0,hashlib.sha256(payload).digest(),payload[:mux.CHUNK_SIZE])
        c.send_mux_fragment(raw,deadline=time.monotonic()+3);c.close('FAULT_TEST')
        with self.assertRaises(mux.MuxError):right.receive(deadline=time.monotonic()+3)
        self.assertEqual(server.memory.used,0)

    def test_cancel_after_first_actual_fragment_is_unknown_no_retry(self):
        import threading,time
        from unittest.mock import patch
        client,server,c,s,left,right,binding=self.channels();cancel=threading.Event();original=c.send_mux_fragment;calls=[]
        def send(*args,**kwargs):
            result=original(*args,**kwargs);calls.append(result);cancel.set();return result
        with patch.object(c,'send_mux_fragment',side_effect=send):
            with self.assertRaisesRegex(mux.MuxError,'UNKNOWN'):left.send(3,b'x'*133128,deadline=time.monotonic()+3,cancel=cancel)
        self.assertEqual(len(calls),1)
        with self.assertRaises(mux.MuxError):right.receive(deadline=time.monotonic()+3)
        self.assertEqual(server.memory.used,0)

    def test_completed_queue_backpressure_keeps_control_app_progress(self):
        import queue,threading,time
        client,server,c,s,left,right,binding=self.channels();one=b'A'*133128;two=b'B'*133128
        left.send(3,one,deadline=time.monotonic()+3)
        done=threading.Event();errors=[]
        def send():
            try:left.send(3,two,deadline=time.monotonic()+4)
            except Exception as exc:errors.append(exc)
            finally:done.set()
        t=threading.Thread(target=send);t.start()
        self.assertFalse(done.wait(.05),'second transfer must stop behind unconsumed complete message')
        c.send(b'control-progress','control');self.assertEqual(s.receive().payload,b'control-progress')
        self.assertEqual(right.receive().payload,one);self.assertEqual(right.receive().payload,two)
        t.join(4);self.assertFalse(t.is_alive());self.assertEqual(errors,[])

    def test_actual_node_budget_blocks_fragment_writes(self):
        import time
        client,server,c,s,left,right,binding=self.channels()
        left.send(3,b'warm');self.assertEqual(right.receive().payload,b'warm')
        with client.budget.transaction() as con:fixed=con.execute('SELECT last_ms FROM meta WHERE id=1').fetchone()[0]/1000
        client.budget.clock=lambda:fixed  # Explicit isolated-clock seam; actual debit/store/socket are real.
        for size in (1048576,65536,4096,256,16,1):
            while client.budget.try_take('tx','LS5','control',size):pass
        before=client.budget.counters()['tx']
        with self.assertRaisesRegex(mux.MuxError,'UNKNOWN'):left.send(3,b'no allowance',deadline=time.monotonic()+.1)
        self.assertEqual(client.budget.counters()['tx'],before)
        with self.assertRaises(mux.MuxError):right.receive(deadline=time.monotonic()+1)

    def test_new_transport_and_stream_attempt_reject_old_fragments(self):
        import time
        client,server,c,s,left,right,old_binding=self.channels();old_nonce=c.nonce
        left.close();right.close()
        for mode in ('old_session','old_attempt'):
            client,server,c,s,left,right,binding=self.channels()
            bad_binding=binding if mode=='old_session' else mux.MuxBinding(binding.connection_id,binding.epoch,old_binding.stream_attempt_id,binding.profile_sha256)
            nonce=old_nonce if mode=='old_session' else c.nonce
            raw=mux.encode_fragment(bad_binding,nonce,str(uuid.uuid4()),3,1,0,hashlib.sha256(b'x').digest(),b'x')
            c.send_mux_fragment(raw,deadline=time.monotonic()+2)
            with self.assertRaisesRegex(mux.MuxError,'BINDING'):right.receive(deadline=time.monotonic()+2)
            self.assertEqual(server.memory.used,0)


    def test_explicit_completed_transfer_replay_charged_without_transport_exactly_once(self):
        import time
        client,server,c,s,left,right,binding=self.channels()
        payload=b'explicit-replay';transfer=str(uuid.uuid4())
        raw=mux.encode_fragment(binding,c.nonce,transfer,3,len(payload),0,hashlib.sha256(payload).digest(),payload)
        for _ in range(2):
            beforetx=client.budget.counters()['tx'];beforerx=server.budget.counters()['rx']
            c.send_mux_fragment(raw,deadline=time.monotonic()+2)
            message=right.receive(deadline=time.monotonic()+2)
            self.assertEqual((message.transfer_id,message.payload),(transfer,payload))
            self.assertGreater(client.budget.counters()['tx']-beforetx,len(raw))
            self.assertGreater(server.budget.counters()['rx']-beforerx,len(raw))


    def test_hash_terminal_cause_survives_reader_receive_interleaving(self):
        import threading,time
        from unittest.mock import patch
        client,server,c,s,left,right,binding=self.channels()
        failed=threading.Event();resume=threading.Event();original=right._abort
        def pause_reader_abort(reason):
            if reason=='MUX_MESSAGE_HASH_REJECTED' and threading.current_thread() is right.thread:
                failed.set()
                if not resume.wait(3):raise AssertionError('test synchronization release missing')
            return original(reason)
        try:
            with patch.object(right,'_abort',side_effect=pause_reader_abort):
                payload=b'x'*133128;transfer=str(uuid.uuid4())
                for i in range((len(payload)+mux.CHUNK_SIZE-1)//mux.CHUNK_SIZE):
                    chunk=payload[i*mux.CHUNK_SIZE:(i+1)*mux.CHUNK_SIZE]
                    c.send_mux_fragment(mux.encode_fragment(binding,c.nonce,transfer,3,len(payload),i,b'0'*32,chunk),deadline=time.monotonic()+2)
                self.assertTrue(failed.wait(2),'reader must reach the actual hash failure')
                try:
                    with self.assertRaisesRegex(mux.MuxError,'MUX_MESSAGE_HASH_REJECTED'):
                        right.receive(deadline=time.monotonic()+1)
                finally:
                    resume.set();right.thread.join(2)
                self.assertEqual(right.error,'MUX_MESSAGE_HASH_REJECTED')
                self.assertEqual(server.memory.used,0)
        finally:resume.set()


if __name__=='__main__':unittest.main()
