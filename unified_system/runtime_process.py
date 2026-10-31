"""Owned local subprocess driver; no remote shell or physical authorization.

The deployment boundary must authenticate configuration/artifacts and provide an
authorization callback. Default execution is denied. PID reuse, stale release
health and ambiguous interrupted starts fail closed. Health is loopback only.
"""
import ctypes
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import secrets
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


class ProcessDriver:
    def __init__(self,root,programs,*,authorize=None):
        self.root=_safe_path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.programs=programs;self.authorize=authorize or (lambda action,module:False);self.children={}
        if type(programs) is not dict or not 1<=len(programs)<=64:raise ValueError('bounded programs required')
        for name,p in programs.items():
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
        p=self.programs[module];exe=_safe_path(p['argv'][0]);cwd=_safe_path(p['cwd'])
        if _sha(exe)!=p['executable_sha256']:raise ValueError('runtime executable integrity')
        for file,pin in p['file_pins'].items():
            target=_safe_path(cwd/file)
            if not target.is_file() or _sha(target)!=pin:raise ValueError('runtime file integrity')
        for file,pin in p.get('external_file_pins',{}).items():
            target=_safe_path(file)
            if not target.is_file() or _sha(target)!=pin:raise ValueError('runtime external file integrity')
    def start(self,spec,release_id,operation_id):
        if self.authorize('start',spec.module_id) is not True:raise ValueError('runtime execution not authorized')
        self._verify(spec.module_id)
        path=self._file(operation_id)
        if path.exists():
            d=self._load(operation_id)
            if (d['module_id'],d['version'],d['release_id'])!=(spec.module_id,spec.version,release_id):raise ValueError('operation identity mismatch')
            if not self.alive(operation_id):raise ValueError('ambiguous prior process start')
            return operation_id
        d=dict(pid=None,created=None,module_id=spec.module_id,version=spec.version,release_id=release_id,
               token=secrets.token_hex(32),state='STARTING')
        self._save(operation_id,d,new=True)
        p=self.programs[spec.module_id];env=os.environ.copy();env.update(p.get('env',{}))
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
            kwargs={'timeout':.5}
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
            deadline=threading.Timer(.5,expire);deadline.daemon=True;deadline.start()
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
        d=self._load(handle)
        if d['state']=='STOPPED':
            if handle in self.children:self.children[handle].wait(timeout=5)
            if handle in self.children and self.children[handle].stdin:self.children[handle].stdin.close()
            return
        identity=_identity(d['pid'])
        if identity is None:
            d['state']='STOPPED';self._save(handle,d);return
        if identity!=d['created']:raise ValueError('refuse unrelated process stop')
        if os.name=='nt':
            k,w=_win_api();h=k.OpenProcess(0x1000|0x100000|1,False,d['pid'])
            if not h:raise ValueError('owned process unavailable')
            try:
                if _win_identity(k,w,h)!=d['created']:raise ValueError('refuse reused process')
                if not k.TerminateProcess(h,0) or k.WaitForSingleObject(h,5000)!=0:raise ValueError('owned process stop failed')
            finally:k.CloseHandle(h)
        else:
            if not hasattr(os,'pidfd_open') or not hasattr(signal,'pidfd_send_signal'):raise ValueError('safe owned process signalling unavailable')
            fd=os.pidfd_open(d['pid'])
            try:
                if _identity(d['pid'])!=d['created']:raise ValueError('refuse reused process')
                signal.pidfd_send_signal(fd,signal.SIGTERM)
                deadline=time.monotonic()+3
                while time.monotonic()<deadline and _identity(d['pid']) is not None:time.sleep(.02)
                if _identity(d['pid']) is not None:signal.pidfd_send_signal(fd,signal.SIGKILL)
            finally:os.close(fd)
        if handle in self.children:
            self.children[handle].wait(timeout=5)
            if self.children[handle].stdin:self.children[handle].stdin.close()
        d['state']='STOPPED';self._save(handle,d)
