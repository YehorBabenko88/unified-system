"""Native capture is observation only; unsafe host inputs must fail closed."""
import unittest
from unified_system import native_peer_identity as n
NATIVE_RESULTS=[]

class BoundaryTests(unittest.TestCase):
    def test_raw_request_values_rejected_before_native_use(self):
        for value in (None,True,1,{'handle':1},object(),lambda:True):
            with self.subTest(type=type(value).__name__),self.assertRaises(n.NativeCaptureError):
                n.capture_owned_pipe_peer(value,value,deadline_ns=1)

    def test_capture_cannot_run_in_controller_host(self):
        with self.assertRaisesRegex(n.NativeCaptureError,'STERILE_HOST_REQUIRED'):
            n._require_sterile_host()

    def test_private_resource_constructors_and_runtime_fail_closed(self):
        for cls in (n.OwnedProcessInstance,n.OwnedPipeReadLease,n.NativePeerCapture):
            with self.assertRaises(n.NativeCaptureError):cls()
        with self.assertRaisesRegex(n.NativeCaptureError,'ROOT_PRODUCTION_HOST_ADMISSION_REQUIRED'):
            n.capture_runtime_peer(native_admitted=True)

    def test_no_authority_or_grant_surface(self):
        for name in ('issue_identity','permit','authenticate','resolve','mint_token','adjust_privileges'):
            self.assertFalse(hasattr(n,name))




def _fixture_client(name,level):
    import ctypes as c,sys
    api=n._Win32();H=c.c_void_p;U=c.c_uint32;B=c.c_int32;P=c.POINTER
    k=api.k
    k.CreateFileW.restype=H;k.CreateFileW.argtypes=[c.c_wchar_p,U,U,H,U,U,H]
    k.ReadFile.restype=B;k.ReadFile.argtypes=[H,H,U,P(U),H]
    k.WriteFile.restype=B;k.WriteFile.argtypes=[H,H,U,P(U),H]
    k.WaitNamedPipeW.restype=B;k.WaitNamedPipeW.argtypes=[c.c_wchar_p,U]
    path='\\\\.\\pipe\\'+name
    if not k.WaitNamedPipeW(path,5000):raise RuntimeError('CLIENT_WAIT')
    h=k.CreateFileW(path,0xc0000000,0,None,3,0x100000|(int(level)<<16),None)
    if not h or h==c.c_void_p(-1).value:raise RuntimeError('CLIENT_OPEN')
    try:
        received=U();buf=c.create_string_buffer(4)
        if not k.ReadFile(h,buf,1,c.byref(received),None) or buf.raw[:1]!=b'G':raise RuntimeError('CLIENT_GO')
        msg=c.create_string_buffer(b'USI1')
        if not k.WriteFile(h,msg,4,c.byref(received),None):raise RuntimeError('CLIENT_WRITE')
        # Server keeps the process alive through capture/check_current.
        if not k.ReadFile(h,buf,1,c.byref(received),None):return
    finally:api.CloseHandle(h)


def _host_case(case,result,release=None):
    import ctypes as c,hashlib,subprocess,sys,time,threading,uuid
    from pathlib import Path
    api=None;pipe=None;descriptor=c.c_void_p();client=None;other=None;owned=None;wrong=None;lease=None;capture=None
    context={}
    try:
        api=n._register_isolated_sterile_host();H=c.c_void_p;U=c.c_uint32;B=c.c_int32;P=c.POINTER
        class SA(c.Structure):_fields_=[('length',U),('descriptor',H),('inherit',B)]
        k=api.k;a=api.a
        k.CreateNamedPipeW.restype=H;k.CreateNamedPipeW.argtypes=[c.c_wchar_p,U,U,U,U,U,U,P(SA)]
        k.ConnectNamedPipe.restype=B;k.ConnectNamedPipe.argtypes=[H,H]
        k.ReadFile.restype=B;k.ReadFile.argtypes=[H,H,U,P(U),H]
        k.WriteFile.restype=B;k.WriteFile.argtypes=[H,H,U,P(U),H]
        a.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype=B
        a.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes=[c.c_wchar_p,U,P(H),P(U)]
        own_token=H();buf=c.create_string_buffer(65536);raw=n._RawToken()
        if not api.OpenProcessToken(api.GetCurrentProcess(),8,c.byref(own_token)):raise RuntimeError('OBSERVER_TOKEN')
        try:
            n._read_raw_token(own_token.value,buf,raw);sid,_,_=n._materialize(raw)
            needed=U()
            if not api.GetTokenInformation(own_token.value,20,buf,4,c.byref(needed)) or needed.value!=4:raise RuntimeError('TOKEN_ELEVATION_QUERY')
            context['token_elevation_raw']=int(c.cast(buf,P(U))[0])
            size=n._query(own_token.value,3,buf);count=int(c.cast(buf,P(U))[0]);context['privilege_count']=count
            if count>1024 or 4+count*12>size:raise RuntimeError('PRIVILEGE_BOUNDS')
            # Record raw LUID/attributes, not an inferred nonadmin/Home PASS.
            context['token_privileges']=[{'luid_raw':bytes(buf[4+i*12:12+i*12]).hex(),'attributes':int.from_bytes(bytes(buf[12+i*12:16+i*12]),'little')} for i in range(count)]
        finally:api.CloseHandle(own_token.value)
        size=U();sddl='D:P(A;;GA;;;'+sid+')'
        if not a.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl,1,c.byref(descriptor),c.byref(size)):raise RuntimeError('FIXTURE_DACL')
        name='UnifiedCaptureFixture-'+uuid.uuid4().hex;sa=SA(c.sizeof(SA),descriptor,0)
        pipe=k.CreateNamedPipeW('\\\\.\\pipe\\'+name,3|0x80000,2|4|8,1,4096,4096,0,c.byref(sa))
        if not pipe or pipe==H(-1).value:raise RuntimeError('FIXTURE_PIPE')
        repo=Path(__file__).resolve().parents[1]
        script="import sys;sys.path[:0]=[sys.argv[1],sys.argv[1]+'/tests'];from test_native_peer_identity import _fixture_client;_fixture_client(sys.argv[2],sys.argv[3])"
        level=0 if case=='anonymous' else 2 if case=='strong_level' else 1
        client=subprocess.Popen([sys.executable,'-I','-S','-B','-c',script,str(repo),name,str(level)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        # Actual retained launch handle exists BEFORE server permits request write.
        owned=n.OwnedProcessInstance._from_created_process_handle(int(client._handle))
        if case=='wrong_process':
            other=subprocess.Popen([sys.executable,'-I','-S','-B','-c','import time;time.sleep(10)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            wrong=n.OwnedProcessInstance._from_created_process_handle(int(other._handle))
        if not k.ConnectNamedPipe(pipe,None) and c.get_last_error()!=535:raise RuntimeError('FIXTURE_CONNECT')
        transferred=U();go=c.create_string_buffer(b'G')
        if not k.WriteFile(pipe,go,1,c.byref(transferred),None):raise RuntimeError('FIXTURE_GO')
        request=c.create_string_buffer(4)
        if not k.ReadFile(pipe,request,4,c.byref(transferred),None) or request.raw!=b'USI1':raise RuntimeError('FIXTURE_READ')
        lease=n.OwnedPipeReadLease._after_completed_read(int(pipe),generation=1,read_lock=threading.Lock())
        if case=='exit_before_capture':
            ack=c.create_string_buffer(b'Q');k.WriteFile(pipe,ack,1,c.byref(transferred),None);client.wait(3)
        if case=='closed_lease':lease.close()
        if case=='closed_process':owned.close()
        cancelled=threading.Event()
        if case=='cancelled':cancelled.set()
        k.GetProcessHandleCount.restype=B;k.GetProcessHandleCount.argtypes=[H,P(U)]
        before_handles=U();after_handles=U()
        if not k.GetProcessHandleCount(api.GetCurrentProcess(),c.byref(before_handles)):raise RuntimeError('HANDLE_COUNT_UNAVAILABLE')
        if case=='revert_failure':
            from functools import partial
            from multiprocessing.reduction import DupHandle
            import multiprocessing as mp
            # Transfer an actual OWN launched-client handle before the fault so
            # controller cleanup never targets a reused PID or unrelated process.
            resource=DupHandle(int(client._handle),access=0x100000|0x1000|1,pid=mp.parent_process().pid)
            result.put({'status':'OWN_FAILFAST_READY','client_resource':resource,'context':context})
            if release is None or not release.wait(5):raise RuntimeError('FAILFAST_FIXTURE_HANDSHAKE')
            # Inject an actual failing Win32 call, not an admission boolean.
            # This branch is OWN disposable helper only and is labeled injected.
            api.RevertToSelf=partial(api.CloseHandle,None)
        preexisting=case=='preexisting'
        if preexisting and not api.ImpersonateNamedPipeClient(pipe):raise RuntimeError('PREEXISTING_SETUP')
        try:
            if case=='lease_busy':
                n.OwnedPipeReadLease._after_completed_read(int(pipe),generation=1,read_lock=lease._lock)
                raise RuntimeError('CONCURRENT_LEASE_ACCEPTED')
            try:
                reserved=[]
                try:
                    if case=='resource_limit':
                        for _ in range(16):
                            if not n._SLOTS.acquire(False):raise RuntimeError('FIXTURE_SLOT_STATE')
                            reserved.append(True)
                    capture=n.capture_owned_pipe_peer(lease,wrong or owned,deadline_ns=time.monotonic_ns()+(0 if case=='deadline' else 3_000_000_000),cancel=cancelled)
                finally:
                    for _ in reserved:n._SLOTS.release()
            finally:
                if preexisting:
                    # Fixture owns this preexisting token, not the capture API.
                    if not n._thread_has_token():raise RuntimeError('PREEXISTING_TOKEN_WAS_OVERWRITTEN')
                    if not api.RevertToSelf():api.TerminateProcess(api.GetCurrentProcess(),74)
            observation=capture.check_current()
            import pickle
            try:pickle.dumps(capture)
            except TypeError:pass
            else:raise RuntimeError('CAPTURE_SERIALIZED')
            if observation.sid in repr(observation):raise RuntimeError('SID_REPR_LEAK')
            if case=='exit_after_capture':
                ack=c.create_string_buffer(b'Q');k.WriteFile(pipe,ack,1,c.byref(transferred),None);client.wait(3)
                capture.check_current()
                raise RuntimeError('DEAD_PROCESS_CAPTURE_STILL_CURRENT')
            if case=='reuse':
                try:n.capture_owned_pipe_peer(lease,owned,deadline_ns=time.monotonic_ns()+1_000_000_000)
                except n.NativeCaptureError as e:
                    if e.code!='PIPE_READ_LEASE_CONSUMED':raise
                else:raise RuntimeError('REUSED_READ_LEASE_ACCEPTED')
            capture.close();capture.close()
            try:capture.check_current()
            except n.NativeCaptureError as e:
                if e.code!='CAPTURE_CLOSED':raise
            else:raise RuntimeError('CLOSED_CAPTURE_ACCEPTED')
            if case not in ('positive','reuse'):raise RuntimeError('NEGATIVE_ACCEPTED')
            verdict={'status':'OBSERVED_NOT_AUTHENTICATED','sid_sha256':hashlib.sha256(observation.sid.encode()).hexdigest(),'level':observation.impersonation_level}
        except n.NativeCaptureError as e:
            if capture:capture.close()
            if case in ('positive','reuse'):raise
            verdict={'status':'REJECTED','code':e.code}
        if n._thread_has_token():raise RuntimeError('SERVER_TOKEN_NOT_RESTORED')
        if not k.GetProcessHandleCount(api.GetCurrentProcess(),c.byref(after_handles)):raise RuntimeError('HANDLE_COUNT_UNAVAILABLE')
        if before_handles.value!=after_handles.value:raise RuntimeError('NATIVE_HANDLE_LEAK')
        context['capture_handles_before']=before_handles.value;context['capture_handles_after']=after_handles.value
        verdict.update(case=case,server_identity_restored=True,context=context,runtime_admission=False)
        result.put(verdict)
    except BaseException as exc:result.put({'case':case,'status':'FIXTURE_ERROR','error':type(exc).__name__+':'+str(exc)[:100],'context':context})
    finally:
        if capture:capture.close()
        if lease:lease.close()
        if wrong:wrong.close()
        if owned:owned.close()
        if pipe and api:api.CloseHandle(pipe)
        if descriptor.value and api:api.LocalFree(descriptor)
        for process in (client,other):
            if process:
                try:process.wait(1)
                except subprocess.TimeoutExpired:process.terminate();process.wait(3)


@unittest.skipUnless(n.SUPPORTED,'Windows native fixture NOT_RUN on other platforms')
class NativeOwnedChildTests(unittest.TestCase):
    def run_case(self,case):
        import multiprocessing as mp,queue
        ctx=mp.get_context('spawn');q=ctx.Queue();p=ctx.Process(target=_host_case,name='UnifiedNativePeerCaptureHost',args=(case,q));p.start()
        try:
            try:value=q.get(timeout=15)
            except queue.Empty:self.fail('owned sterile fixture deadline')
            p.join(4)
            if p.is_alive():p.terminate();p.join(3);self.fail('owned sterile host did not stop')
            self.assertEqual(p.exitcode,0);self.assertNotEqual(value['status'],'FIXTURE_ERROR',value)
            self.assertTrue(value['server_identity_restored']);self.assertFalse(value['runtime_admission']);NATIVE_RESULTS.append(value);return value
        finally:
            if p.is_alive():p.terminate();p.join(3)
            q.close();q.join_thread()

    def test_injected_revert_failure_terminates_only_owned_sterile_host(self):
        import multiprocessing as mp,ctypes as c
        ctx=mp.get_context('spawn');q=ctx.Queue();go=ctx.Event()
        p=ctx.Process(target=_host_case,name='UnifiedNativePeerCaptureHost',args=('revert_failure',q,go));p.start();client_handle=None
        api=n._Win32()  # Controller performs only own-handle query/cleanup, never impersonates.
        try:
            ready=q.get(timeout=10);self.assertEqual(ready['status'],'OWN_FAILFAST_READY',ready)
            client_handle=ready['client_resource'].detach();go.set();p.join(6)
            self.assertFalse(p.is_alive(),'injected unsafe helper must failfast')
            self.assertEqual(p.exitcode & 0xffffffff,0xE0420001)
            stopped=api.WaitForSingleObject(client_handle,5000)==0
            if not stopped:api.TerminateProcess(client_handle,75);api.WaitForSingleObject(client_handle,3000)
            self.assertTrue(stopped,'owned client must observe broken pipe and exit')
            NATIVE_RESULTS.append({'case':'INJECTED_REVERT_FAILURE','own_helper_failfast_exit':p.exitcode,
                                   'owned_client_stopped':stopped,'context':ready['context'],'runtime_admission':False})
        finally:
            go.set()
            if p.is_alive():p.terminate();p.join(3)
            if client_handle:api.CloseHandle(client_handle)
            q.close();q.join_thread()

    def test_actual_identification_child(self):self.assertEqual(self.run_case('positive')['status'],'OBSERVED_NOT_AUTHENTICATED')
    def test_actual_wrong_owned_process(self):self.assertEqual(self.run_case('wrong_process')['code'],'CLIENT_PROCESS_INSTANCE_MISMATCH')
    def test_actual_anonymous_token(self):self.assertEqual(self.run_case('anonymous')['status'],'REJECTED')
    def test_actual_stronger_token(self):self.assertEqual(self.run_case('strong_level')['code'],'IDENTIFICATION_LEVEL_REQUIRED')
    def test_resource_binding_expires_on_own_client_exit(self):self.assertEqual(self.run_case('exit_after_capture')['code'],'PROCESS_NOT_LIVE')
    def test_injected_slot_saturation_denies_before_native_capture(self):self.assertEqual(self.run_case('resource_limit')['code'],'CAPTURE_RESOURCE_LIMIT')
    def test_actual_own_child_exit(self):self.assertEqual(self.run_case('exit_before_capture')['status'],'REJECTED')
    def test_closed_lease(self):self.assertEqual(self.run_case('closed_lease')['code'],'NATIVE_RESOURCE_CLOSED')
    def test_closed_process(self):self.assertEqual(self.run_case('closed_process')['code'],'NATIVE_RESOURCE_CLOSED')
    def test_cancelled_capture(self):self.assertEqual(self.run_case('cancelled')['code'],'CAPTURE_CANCELLED')
    def test_expired_deadline(self):self.assertEqual(self.run_case('deadline')['code'],'CAPTURE_DEADLINE')
    def test_preexisting_token_not_overwritten(self):self.assertEqual(self.run_case('preexisting')['code'],'SERVER_ALREADY_IMPERSONATING')
    def test_concurrent_read_lease_denied(self):self.assertEqual(self.run_case('lease_busy')['code'],'PIPE_READ_LEASE_BUSY')
    def test_read_lease_single_capture(self):self.assertEqual(self.run_case('reuse')['status'],'OBSERVED_NOT_AUTHENTICATED')

if __name__=='__main__':unittest.main()
