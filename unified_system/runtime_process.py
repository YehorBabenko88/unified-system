"""Owned local subprocess driver; no remote shell or physical authorization.

The deployment boundary must authenticate configuration/artifacts and provide an
authorization callback. Default execution is denied. PID reuse, stale release
health and ambiguous interrupted starts fail closed. Health is loopback only.
"""
import ctypes
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import re
import secrets
import select
import signal
import socket
import threading
import tempfile
import ssl
import stat
import subprocess
import time
from urllib.parse import urlsplit


def _sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
    return h.hexdigest()


def _safe_path(path):
    raw=str(path)
    if raw.startswith(('\\\\','//')) or '..' in Path(path).parts:raise ValueError('nonlocal runtime path')
    p=Path(path).absolute()
    # Inspect ancestors first: looking at a descendant through a junction can
    # already perform an unintended network or out-of-namespace filesystem read.
    for part in reversed((p,*p.parents)):
        try:facts=part.lstat()
        except FileNotFoundError:continue
        if stat.S_ISLNK(facts.st_mode) or getattr(facts,'st_file_attributes',0)&1024:
            raise ValueError('linked runtime path')
    return p


def _win_api():
    from ctypes import wintypes as w
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
    k.CloseHandle.argtypes=[w.HANDLE];k.CloseHandle.restype=w.BOOL
    k.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)];k.GetProcessTimes.restype=w.BOOL
    k.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)];k.QueryFullProcessImageNameW.restype=w.BOOL
    k.TerminateProcess.argtypes=[w.HANDLE,w.UINT];k.TerminateProcess.restype=w.BOOL
    k.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];k.WaitForSingleObject.restype=w.DWORD
    return k,w


def _win_identity(k,w,handle):
    a,b,c,d=(w.FILETIME() for _ in range(4));buf=ctypes.create_unicode_buffer(32768);size=w.DWORD(len(buf))
    if not k.GetProcessTimes(handle,ctypes.byref(a),ctypes.byref(b),ctypes.byref(c),ctypes.byref(d)):raise ValueError('process identity unavailable')
    if not k.QueryFullProcessImageNameW(handle,0,buf,ctypes.byref(size)):raise ValueError('process executable unavailable')
    return [str((a.dwHighDateTime<<32)|a.dwLowDateTime),str(Path(buf.value).resolve()).casefold()]


def _identity(pid):
    if type(pid) is not int or pid<=0:raise ValueError('invalid process identity')
    if os.name=='nt':
        k,w=_win_api();handle=k.OpenProcess(0x1000|0x100000,False,pid)
        if not handle:
            if ctypes.get_last_error()==87:return None
            raise ValueError('process identity unavailable')
        try:
            if k.WaitForSingleObject(handle,0)==0:return None
            return _win_identity(k,w,handle)
        finally:k.CloseHandle(handle)
    try:
        raw=Path(f'/proc/{pid}/stat').read_text();parts=raw[raw.rfind(')')+2:].split()
        if parts[0]=='Z':return None
        return [Path('/proc/sys/kernel/random/boot_id').read_text().strip()+':'+parts[19],str(Path(f'/proc/{pid}/exe').resolve(strict=True))]
    except (FileNotFoundError,ProcessLookupError):return None




class RetainedOsProcessWait:
    """Read-only, incarnation-bound Win HANDLE / Linux pidfd wait primitive.

    The caller must independently verify its OWNERSHIP of the process, e.g.
    C's dedicated LAB PostgreSQL marker, executable, data root and PID file.
    This never signals/kills a process, infers SQL completion, or issues a
    RootProcessExtinction/RootBackendExtinction grant. Failure is UNKNOWN.
    """

    def __init__(self, pid, created):
        if (type(pid) is not int or pid <= 1 or type(created) is not list
                or len(created) != 2 or not all(type(v) is str and v for v in created)):
            raise ValueError('owned OS incarnation invalid')
        self.pid = pid
        self.created = tuple(created)
        self._handle = None
        self._kernel = None
        self._windows = os.name == 'nt'
        if _identity(pid) != created:
            raise ValueError('owned OS incarnation changed')
        if self._windows:
            kernel, wintypes = _win_api()
            handle = kernel.OpenProcess(0x1000 | 0x100000, False, pid)
            if not handle:
                raise ValueError('owned OS handle unavailable')
            try:
                # Opened handle pins a kernel process object, not a PID
                # which may later be reused by a different application.
                if (kernel.WaitForSingleObject(handle, 0) != 0x102
                        or _win_identity(kernel, wintypes, handle) != created):
                    raise ValueError('owned OS incarnation changed')
            except BaseException:
                kernel.CloseHandle(handle)
                raise
            self._kernel, self._handle = kernel, handle
        else:
            if not hasattr(os, 'pidfd_open'):
                raise ValueError('owned OS pidfd unavailable')
            fd = os.pidfd_open(pid)
            try:
                if (_identity(pid) != created
                        or bool(select.select([fd], [], [], 0)[0])):
                    raise ValueError('owned OS incarnation changed')
            except BaseException:
                os.close(fd)
                raise
            self._handle = fd

    def wait_exited(self, timeout):
        """True only if the retained kernel object has signalled exit."""
        if (type(timeout) not in (int, float) or not math.isfinite(timeout)
                or not 0 <= timeout <= 60):
            raise ValueError('owned OS wait timeout invalid')
        if self._handle is None:
            raise ValueError('owned OS wait handle closed')
        if self._windows:
            status = self._kernel.WaitForSingleObject(self._handle, int(timeout * 1000))
            if status == 0:
                return True
            if status == 0x102:
                return False
            raise ValueError('owned OS wait unavailable')
        return bool(select.select([self._handle], [], [], timeout)[0])

    def close(self):
        if self._handle is None:
            return
        if self._windows:
            self._kernel.CloseHandle(self._handle)
        else:
            os.close(self._handle)
        self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()



def _windows_tcp_listener_owner_pids(port):
    """Read ALL IPv4/IPv6 Windows TCP LISTEN owners; never an admission grant.

    Return a bounded snapshot of kernel owning PIDs for the exact local TCP
    port, including wildcard binds. This is read-only: an empty snapshot is
    not durable proof of a departed child, descendants or a future bind.
    Any API error, buffer race or unsupported platform is UNKNOWN via error.
    """
    if os.name != 'nt' or type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('kernel TCP ownership unavailable')
    import struct
    from ctypes import wintypes as w
    api = ctypes.WinDLL('iphlpapi', use_last_error=True)
    api.GetExtendedTcpTable.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(w.DWORD), w.BOOL,
        w.ULONG, w.ULONG, w.ULONG]
    api.GetExtendedTcpTable.restype = w.ULONG
    owners = set()
    # TABLE_OWNER_PID_LISTENER = 3, MIB_TCP_STATE_LISTEN = 2.
    for family, row_size, state_offset, port_offset, pid_offset in (
            (2, 24, 0, 8, 20), (23, 56, 48, 20, 52)):
        size = w.DWORD(0)
        result = api.GetExtendedTcpTable(None, ctypes.byref(size),
                                         False, family, 3, 0)
        if result not in (0, 122):  # ERROR_INSUFFICIENT_BUFFER
            raise ValueError('kernel TCP owner census unavailable')
        for _ in range(4):
            if not 4 <= size.value <= 2 * 1024 * 1024:
                raise ValueError('kernel TCP owner census unbounded')
            buffer = ctypes.create_string_buffer(size.value)
            result = api.GetExtendedTcpTable(buffer, ctypes.byref(size),
                                             False, family, 3, 0)
            if result == 0:
                raw = buffer.raw
                count = struct.unpack_from('<I', raw, 0)[0]
                if count > 32768 or 4 + count * row_size > len(raw):
                    raise ValueError('kernel TCP owner census malformed')
                for index in range(count):
                    offset = 4 + index * row_size
                    state = struct.unpack_from('<I', raw, offset + state_offset)[0]
                    local_port = struct.unpack_from('<I', raw, offset + port_offset)[0]
                    owning_pid = struct.unpack_from('<I', raw, offset + pid_offset)[0]
                    if (state == 2 and socket.ntohs(local_port & 65535) == port
                            and owning_pid > 0):
                        owners.add(owning_pid)
                break
            if result != 122:
                raise ValueError('kernel TCP owner census failed')
        else:
            raise ValueError('kernel TCP owner census raced')
    return tuple(sorted(owners))



def _windows_service_process_roster():
    """Read-only bounded native SCM service→PID roster; UNKNOWN raises.

    Includes stopped transitions that still retain a PID. No service is
    started, stopped, reconfigured or treated as Root-owned by this census.
    PID alone is not an OS incarnation; compare with a retained process
    handle and executable/creation identity before any lifecycle decision.
    """
    if os.name != 'nt':
        raise ValueError('Windows SCM ownership unavailable')
    from ctypes import wintypes as w

    class ServiceStatusProcess(ctypes.Structure):
        _fields_ = [(name, w.DWORD) for name in (
            'service_type', 'state', 'controls', 'win32_exit',
            'service_exit', 'checkpoint', 'wait_hint', 'pid', 'flags')]

    class ServiceEntry(ctypes.Structure):
        _fields_ = [('name', ctypes.c_wchar_p),
                    ('display_name', ctypes.c_wchar_p),
                    ('status', ServiceStatusProcess)]

    adv = ctypes.WinDLL('advapi32', use_last_error=True)
    adv.OpenSCManagerW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, w.DWORD]
    adv.OpenSCManagerW.restype = w.HANDLE
    adv.CloseServiceHandle.argtypes = [w.HANDLE]
    adv.CloseServiceHandle.restype = w.BOOL
    adv.EnumServicesStatusExW.argtypes = [
        w.HANDLE, w.DWORD, w.DWORD, w.DWORD, ctypes.c_void_p,
        w.DWORD, ctypes.POINTER(w.DWORD), ctypes.POINTER(w.DWORD),
        ctypes.POINTER(w.DWORD), ctypes.c_wchar_p]
    adv.EnumServicesStatusExW.restype = w.BOOL

    # SC_MANAGER_ENUMERATE_SERVICE only; never request control/stop rights.
    scm = adv.OpenSCManagerW(None, None, 0x0004)
    if not scm:
        raise ValueError('Windows SCM access unavailable')
    try:
        roster = set()
        resume = w.DWORD(0)
        allocation = 65536
        for _ in range(64):
            if allocation > 2 * 1024 * 1024:
                raise ValueError('Windows SCM census unbounded')
            buf = ctypes.create_string_buffer(allocation)
            need = w.DWORD(0)
            got = w.DWORD(0)
            completed = adv.EnumServicesStatusExW(
                scm, 0, 0x30, 0x3, buf, allocation,
                ctypes.byref(need), ctypes.byref(got),
                ctypes.byref(resume), None)
            err = ctypes.get_last_error() if not completed else 0
            if not completed and err != 234:  # ERROR_MORE_DATA
                raise ValueError('Windows SCM census unavailable')
            if got.value > 4096 or len(roster) + got.value > 4096:
                raise ValueError('Windows SCM census unbounded')
            if got.value:
                entries = (ServiceEntry * got.value).from_buffer(buf)
                for entry in entries:
                    if not entry.name or not 0 < entry.status.pid < 2**32:
                        continue
                    roster.add((entry.name, int(entry.status.pid)))
            if completed:
                return tuple(sorted(roster))
            if got.value == 0:
                # No forward progress means the receiving buffer must grow.
                allocation = max(allocation * 2, int(need.value))
            elif resume.value == 0:
                raise ValueError('Windows SCM census pagination uncertain')
        raise ValueError('Windows SCM census incomplete')
    finally:
        adv.CloseServiceHandle(scm)



def _windows_process_descendant_snapshot(root_pid, expected_root_created):
    """Read-only Toolhelp descendants with exact OS identities; not a receipt.

    The root PID must still represent its expected creation/executable at
    BOTH ends of the enumeration. Every detected descendant has its own
    identity checked. Parent-PID relations can race with process creation:
    callers must retain kernel wait handles for the inspected descendants
    and still exclude new spawns / foreign services before any Root grant.
    """
    if (os.name != 'nt' or type(root_pid) is not int or root_pid <= 1
            or type(expected_root_created) is not list
            or len(expected_root_created) != 2):
        raise ValueError('Windows descendant census unavailable')
    if _identity(root_pid) != expected_root_created:
        raise ValueError('Windows descendant root identity changed')
    from ctypes import wintypes as w

    class ProcessEntry(ctypes.Structure):
        _fields_ = [
            ('size', w.DWORD), ('usage', w.DWORD),
            ('pid', w.DWORD), ('heap', ctypes.c_size_t),
            ('module', w.DWORD), ('threads', w.DWORD),
            ('parent_pid', w.DWORD), ('priority', w.LONG),
            ('flags', w.DWORD), ('exe', ctypes.c_wchar * 260),
        ]

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [w.DWORD, w.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = w.HANDLE
    kernel.Process32FirstW.argtypes = [w.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.Process32FirstW.restype = w.BOOL
    kernel.Process32NextW.argtypes = [w.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.Process32NextW.restype = w.BOOL
    kernel.CloseHandle.argtypes = [w.HANDLE]
    kernel.CloseHandle.restype = w.BOOL

    snapshot = kernel.CreateToolhelp32Snapshot(0x00000002, 0)
    if not snapshot or snapshot == ctypes.c_void_p(-1).value:
        raise ValueError('Windows descendant census unavailable')
    try:
        entry = ProcessEntry()
        entry.size = ctypes.sizeof(ProcessEntry)
        if not kernel.Process32FirstW(snapshot, ctypes.byref(entry)):
            raise ValueError('Windows descendant census unavailable')
        parent_by_pid = {}
        while True:
            pid = int(entry.pid)
            if pid > 0:
                if pid in parent_by_pid or len(parent_by_pid) >= 16384:
                    raise ValueError('Windows descendant census ambiguous')
                parent_by_pid[pid] = int(entry.parent_pid)
            entry.size = ctypes.sizeof(ProcessEntry)
            if not kernel.Process32NextW(snapshot, ctypes.byref(entry)):
                if ctypes.get_last_error() != 18:  # ERROR_NO_MORE_FILES
                    raise ValueError('Windows descendant census incomplete')
                break
    finally:
        kernel.CloseHandle(snapshot)
    if _identity(root_pid) != expected_root_created:
        raise ValueError('Windows descendant root identity changed')

    discovered = set()
    frontier = {root_pid}
    for _ in range(16384):
        children = {pid for pid, parent in parent_by_pid.items()
                    if parent in frontier and pid != root_pid and pid not in discovered}
        if not children:
            break
        discovered.update(children)
        if len(discovered) > 4096:
            raise ValueError('Windows descendant census unbounded')
        frontier = children
    else:
        raise ValueError('Windows descendant census unbounded')

    observations = []
    for pid in sorted(discovered):
        identity = _identity(pid)
        if identity is None:
            raise ValueError('Windows descendant identity raced')
        observations.append((pid, tuple(identity)))
    if _identity(root_pid) != expected_root_created:
        raise ValueError('Windows descendant root identity changed')
    return tuple(observations)



class OwnedWindowsJob:
    """Kernel-backed containment for a NEW, isolated, Root-created child.

    Must be created before CreateProcess and the child must be assigned before
    it is allowed to execute. Attaching an already running old process cannot
    close the historical child-spawn race and is deliberately unsupported.
    The job can keep members contained while Root observes shutdown, but does
    not independently authorize a new owner, SQL fence or writer epoch.
    """

    def __init__(self):
        if os.name != 'nt':
            raise ValueError('Windows Job Object unavailable')
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        from ctypes import wintypes as w
        k.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
        k.CreateJobObjectW.restype = w.HANDLE
        k.CloseHandle.argtypes = [w.HANDLE]
        k.CloseHandle.restype = w.BOOL
        k.IsProcessInJob.argtypes = [w.HANDLE, w.HANDLE, ctypes.POINTER(w.BOOL)]
        k.IsProcessInJob.restype = w.BOOL
        k.QueryInformationJobObject.argtypes = [
            w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD,
            ctypes.POINTER(w.DWORD)]
        k.QueryInformationJobObject.restype = w.BOOL
        self._k = k
        self._handle = k.CreateJobObjectW(None, None)
        if not self._handle:
            raise ValueError('Windows Job Object creation denied')
        # Prevent children from escaping into a breakaway job and ensure
        # cleanup if the protected owner closes its final Job handle.
        class BasicLimits(ctypes.Structure):
            _fields_ = [('user_time', ctypes.c_int64),
                        ('job_time', ctypes.c_int64),
                        ('limit_flags', w.DWORD),
                        ('minimum_ws', ctypes.c_size_t),
                        ('maximum_ws', ctypes.c_size_t),
                        ('active_limit', w.DWORD),
                        ('affinity', ctypes.c_size_t),
                        ('priority', w.DWORD),
                        ('scheduling', w.DWORD)]
        class IoCounters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in
                        ('read_ops', 'write_ops', 'other_ops',
                         'read_bytes', 'write_bytes', 'other_bytes')]
        class ExtendedLimits(ctypes.Structure):
            _fields_ = [('basic', BasicLimits), ('io', IoCounters),
                        ('process_memory_limit', ctypes.c_size_t),
                        ('job_memory_limit', ctypes.c_size_t),
                        ('peak_process_memory', ctypes.c_size_t),
                        ('peak_job_memory', ctypes.c_size_t)]
        k.SetInformationJobObject.argtypes = [
            w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
        k.SetInformationJobObject.restype = w.BOOL
        config = ExtendedLimits()
        config.basic.limit_flags = 0x00002000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not k.SetInformationJobObject(
                self._handle, 9, ctypes.byref(config), ctypes.sizeof(config)):
            k.CloseHandle(self._handle)
            self._handle = None
            raise ValueError('Windows Job containment configuration denied')
        # The Windows launcher must create the child suspended and assign
        # before ResumeThread; never adopt a running process by numeric PID.
        self._created_prelaunch = True
        self._assigned = False

    def assign_suspended_child(self, process_handle, *, created_suspended=False):
        # Caller acknowledgement alone is never a security proof. This is
        # an internal launch primitive; production caller must retain both
        # original PROCESS_INFORMATION handles from CreateProcessW and must
        # NEVER allow any thread to resume before assignment completes.
        if self._handle is None or self._assigned or created_suspended is not True:
            raise ValueError('Windows Job suspended launch required')
        from ctypes import wintypes as w
        self._k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self._k.AssignProcessToJobObject.restype = w.BOOL
        if not self._k.AssignProcessToJobObject(self._handle, process_handle):
            raise ValueError('Windows Job suspended assignment denied')
        self._assigned = True

    def verify_member(self, process_handle):
        if self._handle is None:
            raise ValueError('Windows Job Object closed')
        from ctypes import wintypes as w
        in_job = w.BOOL()
        if not self._k.IsProcessInJob(process_handle, self._handle,
                                      ctypes.byref(in_job)):
            raise ValueError('Windows Job membership inaccessible')
        return bool(in_job.value)

    def resume_suspended_child(self, thread_handle):
        if self._handle is None or not self._assigned:
            raise ValueError('Windows Job suspended child not assigned')
        from ctypes import wintypes as w
        self._k.ResumeThread.argtypes = [w.HANDLE]
        self._k.ResumeThread.restype = w.DWORD
        count = self._k.ResumeThread(thread_handle)
        if count == 0xffffffff:
            raise ValueError('Windows Job suspended resume denied')
        return count

    def active_process_count(self):
        if self._handle is None:
            raise ValueError('Windows Job Object closed')
        from ctypes import wintypes as w
        # JOBOBJECT_BASIC_ACCOUNTING_INFORMATION (JobObjectBasicAccounting=1)
        class Accounting(ctypes.Structure):
            _fields_ = [('total_user', ctypes.c_int64),
                        ('total_kernel', ctypes.c_int64),
                        ('total_page_fault', w.DWORD),
                        ('total_processes', w.DWORD),
                        ('active_processes', w.DWORD),
                        ('total_terminated', w.DWORD)]
        info = Accounting()
        n = w.DWORD()
        if not self._k.QueryInformationJobObject(
                self._handle, 1, ctypes.byref(info), ctypes.sizeof(info),
                ctypes.byref(n)):
            raise ValueError('Windows Job membership inaccessible')
        return int(info.active_processes)

    def close(self):
        if self._handle is not None:
            self._k.CloseHandle(self._handle)
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


class RetainedWindowsDescendantCensus:
    """Hold exact kernel process handles for observed Windows descendants.

    A Toolhelp PPID census is NOT a no-new-child barrier. This object binds
    observed descendants to exact Windows process incarnations, retaining
    their wait handles, and refuses any claim of complete subtree extinction
    unless a separate Root-owned creation barrier has been established.
    No foreign process is signalled or terminated by this class.
    """

    def __init__(self, root_pid, root_created):
        if os.name != 'nt':
            raise ValueError('Windows descendant retention unavailable')
        self._root = RetainedOsProcessWait(root_pid, root_created)
        self._children = []
        self._root_pid = root_pid
        self._root_created = list(root_created)
        try:
            for pid, created in _windows_process_descendant_snapshot(
                    root_pid, self._root_created):
                self._children.append(RetainedOsProcessWait(pid, list(created)))
            # Recheck while handles are retained: a new descendant after the
            # census is a race, not an invitation to claim no old processes.
            after = _windows_process_descendant_snapshot(
                root_pid, self._root_created)
            if after != tuple((c.pid, c.created) for c in self._children):
                raise ValueError('Windows descendant census changed')
        except BaseException:
            self.close()
            raise

    def wait_observed_exited(self, timeout):
        if (type(timeout) not in (int, float) or not math.isfinite(timeout)
                or not 0 <= timeout <= 60):
            raise ValueError('Windows descendant deadline invalid')
        deadline = time.monotonic() + timeout
        result = []
        for child in self._children:
            result.append(child.wait_exited(max(0.0, deadline - time.monotonic())))
        result.append(self._root.wait_exited(max(0.0, deadline - time.monotonic())))
        return all(result)

    def verify_complete_extinction(self, *, creation_barrier=False):
        # Critical: a caller boolean cannot establish a kernel creation
        # barrier. Until the Root-owned Job Object or another kernel-backed
        # containment proof exists, never claim complete process extinction.
        raise ValueError('Windows process creation containment not proven')

    def close(self):
        for child in self._children:
            child.close()
        self._children = []
        self._root.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


PRIVATE_DATA_CAPABILITY_ENV='UNIFIED_MARKET_DATA_READ_CAPABILITY'

def _public_environment(program):
    value=program.get('env',{})
    if type(value) is not dict or any(type(key) is not str or key.upper() in (PRIVATE_DATA_CAPABILITY_ENV,'PGPASSWORD','PGPASSFILE') for key in value):
        raise ValueError('private capability cannot be configured')
    return value


class ProcessDriver:
    def __init__(self,root,programs,*,authorize=None,child_environment=None):
        self.root=_safe_path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.programs=programs;self.authorize=authorize or (lambda action,module:False);self.children={}
        self.prestart_rejections={}
        self.child_environment=child_environment
        if type(programs) is not dict or not 1<=len(programs)<=64:raise ValueError('bounded programs required')
        extra_health_budget=0.
        for name,p in programs.items():
            _public_environment(p)
            timeout=p.get('health_timeout_seconds',.5)
            if type(timeout) not in (int,float) or not math.isfinite(timeout) or not .05<=timeout<=1.:
                raise ValueError('invalid health deadline')
            extra_health_budget+=max(0.,timeout-.5)
            argv=p.get('argv');url=urlsplit(p.get('health_url',''))
            if (not isinstance(argv,list) or not 1<=len(argv)<=32
                    or any(type(x) is not str or not x or len(x)>4096 or '\0' in x for x in argv)
                    or any(x.casefold() in ('-c','-command','-encodedcommand','/c','-e') for x in argv[1:])
                    or not Path(argv[0]).is_absolute() or not Path(p.get('cwd','')).is_absolute()
                    or not re.fullmatch('[a-f0-9]{64}',p.get('executable_sha256',''))
                    or not isinstance(p.get('file_pins'),dict) or not p['file_pins']
                    or url.scheme not in ('http','https') or url.hostname not in ('127.0.0.1','::1')
                    or url.username or url.password or url.query or url.fragment or url.port is None):
                raise ValueError('invalid local program policy')
            for file,pin in p['file_pins'].items():
                relative=Path(file)
                if relative.is_absolute() or '..' in relative.parts or not re.fullmatch('[a-f0-9]{64}',pin):raise ValueError('invalid file pin')
            external=p.get('external_file_pins',{})
            if type(external) is not dict or len(external)>64:raise ValueError('invalid external file pins')
            for file,pin in external.items():
                if (type(file) is not str or not Path(file).is_absolute() or len(file)>4096
                        or type(pin) is not str or not re.fullmatch('[a-f0-9]{64}',pin)):
                    raise ValueError('invalid external file pin')
                _safe_path(file)
        # Preserve the builtin profile's four-second baseline publication budget
        # and its existing .5-second allowance per extension. At most .5s of
        # additional probe time may be explicitly allocated across this driver.
        if extra_health_budget>.5:raise ValueError('aggregate health deadline budget')
    def _file(self,op):
        if type(op) is not str or not re.fullmatch('[a-f0-9-]{32,36}',op):raise ValueError('invalid operation identity')
        return _safe_path(self.root/(op+'.json'))
    def _load(self,op):
        path=self._file(op)
        if path.stat().st_nlink!=1 or path.stat().st_size>8192:raise ValueError('invalid private process record')
        data=json.loads(path.read_text())
        if not isinstance(data,dict) or not {'pid','created','module_id','version','release_id','token','state'}<=set(data):raise ValueError('invalid private process record')
        return data
    def _save(self,op,data,*,new=False):
        path=self._file(op)
        if new:
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as f:json.dump(data,f);f.flush();os.fsync(f.fileno())
        else:
            temp=path.with_name(path.name+'.'+secrets.token_hex(8)+'.tmp')
            fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as f:json.dump(data,f);f.flush();os.fsync(f.fileno())
            os.replace(temp,path)
    def _verify(self,module):
        _public_environment(self.programs[module])
        p=self.programs[module];exe=_safe_path(p['argv'][0]);cwd=_safe_path(p['cwd'])
        if _sha(exe)!=p['executable_sha256']:raise ValueError('runtime executable integrity')
        for file,pin in p['file_pins'].items():
            target=_safe_path(cwd/file)
            if not target.is_file() or _sha(target)!=pin:raise ValueError('runtime file integrity')
        for file,pin in p.get('external_file_pins',{}).items():
            target=_safe_path(file)
            if not target.is_file() or _sha(target)!=pin:raise ValueError('runtime external file integrity')
    def _market_data_read_capability(self,release_id):
        """Transient private child handoff, never program configuration or status."""
        from types import SimpleNamespace
        candidates=[]
        for handle in tuple(self.children):
            record=self._load(handle)
            if record['module_id']=='market_data' and self.alive(handle):candidates.append((handle,record))
        if len(candidates)!=1:raise ValueError('owned market data source unavailable')
        handle,record=candidates[0]
        if (record['release_id']!=release_id or record['state']!='RUNNING'
                or record['created'] is None or not re.fullmatch('[a-f0-9]{64}',record['token'])):
            raise ValueError('market data source identity unavailable')
        program=self.programs['market_data'];url=urlsplit(program['health_url'])
        if program['health_url']!=f'http://127.0.0.1:{url.port}/health':raise ValueError('market data source endpoint rejected')
        commit=_public_environment(program).get('UNIFIED_SOURCE_COMMIT','')
        if type(commit) is not str or not re.fullmatch('[a-f0-9]{40}',commit) or record.get('source_commit')!=commit:raise ValueError('market data source revision unavailable')
        spec=SimpleNamespace(module_id='market_data',version=record['version'])
        ready=self.ready(spec,handle,release_id)
        if (type(ready) is not dict or ready.get('ready') is not True
                or ready.get('module_id')!='market_data' or ready.get('version')!=record['version']
                or ready.get('release_id')!=release_id):
            raise ValueError('market data source not ready')
        return dict(port=url.port,token=record['token'],source_commit=commit,release_id=release_id,epoch=handle)

    def start(self,spec,release_id,operation_id):
        path=self._file(operation_id)
        phase='AUTHORIZATION_REJECTED'
        try:
            if self.authorize('start',spec.module_id) is not True:raise ValueError('runtime execution not authorized')
            phase='INTEGRITY_REJECTED';self._verify(spec.module_id)
            capability=self._market_data_read_capability(release_id) if spec.module_id=='terminan' else None
        except Exception:
            # This live driver witnessed rejection before the durable STARTING
            # intent or Popen. An absent file alone is never that evidence.
            if not path.exists() and operation_id not in self.children:
                if len(self.prestart_rejections)>=1024:self.prestart_rejections.pop(next(iter(self.prestart_rejections)))
                self.prestart_rejections[operation_id]=(spec.module_id,spec.version,release_id,phase)
            raise
        self.prestart_rejections.pop(operation_id,None)
        if path.exists():
            d=self._load(operation_id)
            if (d['module_id'],d['version'],d['release_id'])!=(spec.module_id,spec.version,release_id):raise ValueError('operation identity mismatch')
            if capability is not None and d.get('market_data_epoch')!=capability['epoch']:raise ValueError('dependency epoch changed')
            # Re-attaching by operation ID requires positive same-incarnation OS
            # evidence; alive() maps access-denied/invalid records to False and
            # cannot be a process-ownership or recovery proof.
            if d['state'] != 'RUNNING' or self.owned_process_state(operation_id) != 'STILL_ALIVE':
                raise ValueError('ambiguous prior process start')
            return operation_id
        d=dict(pid=None,created=None,module_id=spec.module_id,version=spec.version,release_id=release_id,
               token=secrets.token_hex(32),state='STARTING')
        if spec.module_id=='market_data':d['source_commit']=_public_environment(self.programs[spec.module_id]).get('UNIFIED_SOURCE_COMMIT')
        if capability is not None:d['market_data_epoch']=capability['epoch']
        self._save(operation_id,d,new=True)
        p=self.programs[spec.module_id]
        env=os.environ.copy() if self.child_environment is None else self.child_environment(spec.module_id)
        env=dict(env)  # Providers may return a cached/public mapping; never mutate it.
        env.update(_public_environment(p))
        for key in tuple(env):
            if key.upper()==PRIVATE_DATA_CAPABILITY_ENV or (key.upper() in ('PGPASSWORD','PGPASSFILE') and (spec.module_id!='market_data' or self.child_environment is None)):del env[key]
        if capability is not None:
            env[PRIVATE_DATA_CAPABILITY_ENV]=json.dumps(capability,separators=(',',':'),allow_nan=False)
        cache=tempfile.mkdtemp(prefix=operation_id+'-cache-',dir=self.root)
        os.chmod(cache,0o700)
        env.update(PYTHONPYCACHEPREFIX=cache,PYTHONDONTWRITEBYTECODE='1',UNIFIED_PRIVATE_CACHE_ROOT=cache)
        env.update(UNIFIED_MODULE_ID=spec.module_id,UNIFIED_MODULE_VERSION=spec.version,
                   UNIFIED_RELEASE_ID=release_id,UNIFIED_INSTANCE_TOKEN=d['token'])
        proc=subprocess.Popen(p['argv'],cwd=p['cwd'],env=env,stdin=subprocess.PIPE,
                              stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,shell=False)
        self.children[operation_id]=proc
        d.update(pid=proc.pid,created=_identity(proc.pid),state='RUNNING');self._save(operation_id,d)
        return operation_id
    def owned_process_state(self, handle):
        """Read-only Root OS witness: EXTINCT, STILL_ALIVE, or UNKNOWN.

        An absent PID lookup by itself is not a historical proof of an exit:
        only the original retained Popen handle with completed poll, or a
        trusted durable stop receipt backed by that original handle, can
        establish EXTINCT here. This does NOT inspect TCP listener ownership,
        descendants, foreign SCM services, or a PostgreSQL backend and cannot
        independently authorize a new writer epoch.
        """
        try:
            d = self._load(handle)
            pid, created = d.get('pid'), d.get('created')
            if type(pid) is not int or pid <= 1 or not isinstance(created, list) or len(created) != 2:
                return 'UNKNOWN'
            child = self.children.get(handle)
            if child is None or child.pid != pid:
                # A persisted record with no original process handle is not
                # sufficient to distinguish PID reuse, access denied and
                # exited process. Never infer EXTINCT from state='STOPPED'.
                return 'UNKNOWN'
            try:
                exit_code = child.poll()
                if exit_code is not None:
                    # The retained Popen handle has observed its own exit.
                    # An unrelated PID may already have replaced it.
                    return 'EXTINCT'
                identity = _identity(pid)
            except (OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired):
                return 'UNKNOWN'
            if identity == created:
                return 'STILL_ALIVE'
            # Identity mismatch with no recorded exit may be a PID race or
            # an unavailable observation. Neither grants owner replacement.
            return 'UNKNOWN'
        except (OSError, ValueError, TypeError, KeyError):
            return 'UNKNOWN'

    def alive(self,handle):
        if handle in self.children and self.children[handle].poll() is not None:
            if self.children[handle].stdin:self.children[handle].stdin.close()
            return False
        try:
            d=self._load(handle)
            if d['state']=='STOPPED' and handle in self.children:
                self.children[handle].wait(timeout=1)
                if self.children[handle].stdin:self.children[handle].stdin.close()
            return d['state']=='RUNNING' and d['created'] is not None and _identity(d['pid'])==d['created']
        except (OSError,ValueError,TypeError,KeyError,subprocess.TimeoutExpired):return False
    def ready(self,spec,handle,release_id):
        result={'ready':False}
        if not self.alive(handle):return result
        try:
            self._verify(spec.module_id);d=self._load(handle)
            if (d['module_id'],d['version'],d['release_id'])!=(spec.module_id,spec.version,release_id):return result
            url=urlsplit(self.programs[spec.module_id]['health_url'])
            cls=http.client.HTTPSConnection if url.scheme=='https' else http.client.HTTPConnection
            timeout=self.programs[spec.module_id].get('health_timeout_seconds',.5)
            kwargs={'timeout':timeout}
            if url.scheme=='https':kwargs['context']=ssl.create_default_context(cafile=self.programs[spec.module_id].get('ca_file'))
            connection=cls(url.hostname,url.port,**kwargs)
            # Socket inactivity timeouts do not bound trickled headers/body.
            # Retain the transport even if HTTPConnection detaches its socket.
            transport=None
            expired=threading.Event()
            def expire():
                expired.set()
                sock=transport if transport is not None else connection.sock
                if sock is not None:
                    try:sock.shutdown(socket.SHUT_RDWR)
                    except OSError:pass
            deadline=threading.Timer(timeout,expire);deadline.daemon=True;deadline.start()
            try:
                connection.connect();transport=connection.sock
                if expired.is_set():return result
                connection.request('GET',url.path or '/',headers={'Authorization':'Bearer '+d['token']})
                response=connection.getresponse();raw=response.read(16385)
                if expired.is_set() or response.status!=200 or len(raw)>16384:return result
                body=json.loads(raw)
                if (not isinstance(body,dict) or body.get('instance_token')!=d['token']
                        or body.get('module_id')!=spec.module_id or body.get('version')!=spec.version
                        or body.get('release_id')!=release_id or body.get('ready') is not True):return result
                return dict(module_id=spec.module_id,version=spec.version,release_id=release_id,ready=True)
            finally:
                deadline.cancel();connection.close();deadline.join()
        except (OSError,ValueError,TypeError,KeyError,http.client.HTTPException):return result
    def stop(self,handle):
        path=self._file(handle)
        if handle in self.prestart_rejections and not path.exists() and handle not in self.children:
            module,version,release,phase=self.prestart_rejections[handle]
            self._save(handle,dict(pid=None,created=None,module_id=module,version=version,release_id=release,
                                   token=secrets.token_hex(32),state='STOPPED',failure_phase=phase),new=True)
            del self.prestart_rejections[handle]
            return
        d=self._load(handle)
        if d['state']=='STOPPED':
            # Historical STOPPED JSON is not OS extinction; a retained exact
            # process exit is the only local process-level confirmation.
            # STARTING/prestart authorization rejection has no child to kill,
            # but must not be converted to an OS-exit receipt.
            if d['pid'] is not None:
                if self.owned_process_state(handle) != 'EXTINCT':
                    raise ValueError('stopped record OS extinction unverified')
            if handle in self.children and self.children[handle].stdin:
                self.children[handle].stdin.close()
            return
        if d['pid'] is None:
            child=self.children.get(handle)
            if child is None or child.poll() is None:raise ValueError('ambiguous prior process start')
        identity=_identity(d['pid'])
        if identity is None:
            # PID disappearance or failed lookup by itself proves nothing.
            # Only the retained original Popen wait confirms child exit.
            if self.owned_process_state(handle) != 'EXTINCT':
                raise ValueError('owned process extinction unverified')
            if handle in self.children and self.children[handle].stdin:
                self.children[handle].stdin.close()
            d['state']='STOPPED';self._save(handle,d);return
        if identity!=d['created']:raise ValueError('refuse unrelated process stop')
        # OS exit evidence belongs to the exact handle opened and identity-
        # checked before any signal. A second ProcessDriver may legitimately
        # stop an owned child without holding the original subprocess.Popen.
        # Never mistake an arbitrary missing numeric PID for this evidence.
        exit_witness=False
        if os.name=='nt':
            k,w=_win_api();h=k.OpenProcess(0x1000|0x100000|1,False,d['pid'])
            if not h:raise ValueError('owned process unavailable')
            try:
                if _win_identity(k,w,h)!=d['created']:raise ValueError('refuse reused process')
                if not k.TerminateProcess(h,0) or k.WaitForSingleObject(h,5000)!=0:
                    raise ValueError('owned process stop failed')
                exit_witness=True  # wait on the SAME verified Windows HANDLE
            finally:k.CloseHandle(h)
        else:
            if not hasattr(os,'pidfd_open') or not hasattr(signal,'pidfd_send_signal'):
                raise ValueError('safe owned process signalling unavailable')
            fd=os.pidfd_open(d['pid'])
            try:
                if _identity(d['pid'])!=d['created']:raise ValueError('refuse reused process')
                signal.pidfd_send_signal(fd,signal.SIGTERM)
                # pidfd readability observes the same kernel process object,
                # not a potentially reused PID or a deleted pidfile.
                exit_witness=bool(select.select([fd],[],[],3)[0])
                if not exit_witness:
                    signal.pidfd_send_signal(fd,signal.SIGKILL)
                    exit_witness=bool(select.select([fd],[],[],2)[0])
                if not exit_witness:raise ValueError('owned process stop unverified')
            finally:os.close(fd)
        if handle in self.children:
            self.children[handle].wait(timeout=5)
            if self.owned_process_state(handle) != 'EXTINCT':
                raise ValueError('owned process extinction unverified')
        if not exit_witness:raise ValueError('owned process extinction unverified')
        if handle in self.children and self.children[handle].stdin:
            self.children[handle].stdin.close()
        d['state']='STOPPED';self._save(handle,d)
