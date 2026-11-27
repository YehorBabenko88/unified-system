"""Closing the transport must quiesce real SQLite accounting workers."""
import tempfile
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from unified_system.lan_transport import Connection, LanTransport, _Memory
from unified_system.network_budget import BandwidthPolicy, NodeBudget, NODES


class ShutdownTests(unittest.TestCase):
    def test_close_interrupts_exhausted_budget_and_releases_sqlite_before_return(self):
        # Without close cancellation a sender keeps reopening SQLite until its
        # caller deadline, racing Windows temporary-directory removal.
        with tempfile.TemporaryDirectory() as directory:
            policy=BandwidthPolicy({n:{'rate':100,'burst':100} for n in NODES},
                cluster_rate=600,cluster_burst=600,classes={'control':80,'live':10,'bulk':10})
            budget=NodeBudget.isolated(Path(directory)/'node.sqlite','PC1',policy)
            fixed=budget.clock();budget.clock=lambda:fixed
            while budget.try_take('tx','LS5','control',1):pass
            registry=SimpleNamespace(peer=lambda _: 'admitted')
            owner=SimpleNamespace(registry=registry,node_id='PC1',memory=_Memory(),budget=budget)
            class InertSocket:
                def shutdown(self,*_):pass
                def close(self):pass
                def send(self,_):raise AssertionError('exhausted budget must never write')
            with patch.object(Connection,'_reader'),patch.object(Connection,'_sender'),patch.object(Connection,'_heartbeat'):
                connection=Connection(owner,'LS5','unused',{'control':InertSocket(),'data':InertSocket()})
            entered=threading.Event();finished=threading.Event();errors=[]
            original=budget.try_take
            def observed(*args,**kwargs):
                entered.set();return original(*args,**kwargs)
            budget.try_take=observed
            def emit():
                try:connection._emit('PING',0,'control')
                except ValueError as error:errors.append(str(error))
                finally:finished.set()
            worker=threading.Thread(target=emit);connection.threads.append(worker);worker.start()
            transport=LanTransport.__new__(LanTransport);transport.listener=None;transport.connections={'LS5':connection}
            try:
                self.assertTrue(entered.wait(1))
                transport.close()
                self.assertTrue(finished.is_set(),'close returned while accounting worker was active')
                self.assertEqual(errors,['CANCELLED'])
                budget.path.unlink()  # Windows refuses this while SQLite owns the file.
            finally:
                connection.closed_event.set();worker.join(6)

    def test_concurrent_mux_construction_and_close_never_observe_unstarted_worker(self):
        import uuid
        from unified_system import lan_mux_channel as mux
        owner=SimpleNamespace(registry=SimpleNamespace(peer=lambda _: 'admitted'),
            node_id='PC1',memory=_Memory(),application_protocol='unified-lan-mux-v1')
        with patch.object(Connection,'_reader'),patch.object(Connection,'_sender'),patch.object(Connection,'_heartbeat'):
            connection=Connection(owner,'LS5',str(uuid.uuid4()),{})
        binding=mux.MuxBinding(str(uuid.uuid4()),1,str(uuid.uuid4()),'a'*64)
        transport=LanTransport.__new__(LanTransport);transport.listener=None;transport.connections={'LS5':connection}
        constructor_entered=threading.Event();release_constructor=threading.Event();errors=[];channels=[]
        thread_type=threading.Thread
        def delayed_thread(*args,**kwargs):
            constructor_entered.set()
            if not release_constructor.wait(2):raise AssertionError('constructor release missing')
            return thread_type(*args,**kwargs)
        def build():
            try:channels.append(mux.LanMuxChannel.isolated(connection,binding,allowed_send_kinds={3},expected_receive_kinds={3}))
            except BaseException as error:errors.append(error)
        def close():
            try:transport.close()
            except BaseException as error:errors.append(error)
        with patch.object(mux.LanMuxChannel,'_reader'),patch.object(mux.threading,'Thread',side_effect=delayed_thread):
            builder=thread_type(target=build);builder.start()
            self.assertTrue(constructor_entered.wait(1))
            closer=thread_type(target=close);closer.start()
            # The constructor is deliberately paused before thread assignment.
            # close must either see no published wrapper or await safe publication.
            closer.join(.05)
            release_constructor.set();builder.join(2);closer.join(2)
        self.assertFalse(builder.is_alive());self.assertFalse(closer.is_alive())
        self.assertEqual(errors,[])
        self.assertEqual(len(channels),1)
        self.assertFalse(channels[0].thread.is_alive())
