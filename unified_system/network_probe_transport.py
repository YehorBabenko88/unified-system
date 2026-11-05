"""Owned read-only monitor operations, never network repair or job scheduling.

Callers admit a protected exclusive state leaf and the source before use. These
checks do not contain hostile code running as the same Windows user or Admin.
An unfinished operation is sticky across restarts; there is no elapsed expiry,
automatic state reset, unknown database adoption or process-tree termination.
"""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
import time
import base64
from dataclasses import dataclass
import gzip
import subprocess
import threading
from .lan_probe_inventory import LanProbeInventory,LanInventoryBlocked


NODES = frozenset(('LS5','PC1','PC2','PC3','PC4','LS7'))
REMOTE_NODES = NODES - {'LS5'}
MAX_EVENTS = 512
MAX_RECEIPT = 16384
MAX_DB_BYTES = 8*1024*1024
APP_ID = 0x554E5052
_SLOTS = "CREATE TABLE slots(node TEXT PRIMARY KEY,generation INTEGER NOT NULL,status TEXT NOT NULL,nonce TEXT NOT NULL,recipe_sha TEXT NOT NULL,receipt TEXT NOT NULL)"
_EVENTS = "CREATE TABLE events(sequence INTEGER PRIMARY KEY,node TEXT NOT NULL,generation INTEGER NOT NULL,status TEXT NOT NULL,nonce TEXT NOT NULL,recipe_sha TEXT NOT NULL,receipt TEXT NOT NULL)"


class ProbeTransportBlocked(ValueError):
    pass


class _NoSpawn(ProbeTransportBlocked):
    """Internal control-flow proof: this invocation never reached the runner."""


def _need(value, reason='PROBE_STATE_UNAVAILABLE'):
    if value is not True:
        raise ProbeTransportBlocked(reason)


def _canonical(value):
    try:
        raw = json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
    except (ValueError,TypeError,RecursionError):
        raise ProbeTransportBlocked('PROBE_RECEIPT_REJECTED') from None
    _need(type(value) is dict and len(raw)<=MAX_RECEIPT,'PROBE_RECEIPT_REJECTED')
    return raw


def _object(pairs):
    result = {}
    for key,value in pairs:
        _need(key not in result)
        result[key] = value
    return result


def _parse(raw):
    try:
        value = json.loads(raw,object_pairs_hook=_object,parse_constant=lambda x: (_ for _ in ()).throw(ValueError()))
        _need(_canonical(value)==raw)
        return value
    except (ValueError,TypeError,RecursionError):
        raise ProbeTransportBlocked('PROBE_STATE_UNAVAILABLE') from None


def _path(raw):
    path = Path(raw)
    _need(path.is_absolute() and not str(path).startswith(('\\\\','//')) and '..' not in path.parts)
    for item in (*reversed(path.parents),path):
        info = item.lstat()
        _need(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&1024)
    return path


def _identity(path, *, directory=False):
    _path(path)
    info = path.lstat()
    _need(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode) and info.st_nlink==1)
    return [info.st_dev,info.st_ino]


def _regular(path, limit):
    before = _identity(path)
    with path.open('rb') as stream:
        held = os.fstat(stream.fileno())
        _need([held.st_dev,held.st_ino]==before and held.st_nlink==1 and held.st_size<=limit)
        raw = stream.read(limit+1)
        _need(len(raw)<=limit and _identity(path)==before)
    return raw,before


def _node(node):
    _need(type(node) is str and node in NODES,'PROBE_HOST_REJECTED')


def _hex(value, length):
    return type(value) is str and re.fullmatch('[a-f0-9]{'+str(length)+'}',value) is not None


class ProbeJournal:
    """Crash latch for monitor helpers, independent of Grid job authority.

    The caller's admission callback must verify the real protected leaf/ACLs.
    A marker is a namespace identity, never a substitute for that admission.
    """
    def __init__(self, root, installation_id, *, admit):
        self.root = Path(root)
        self.installation_id = installation_id
        self.admit = admit
        self.marker = self.root/'probe-owner.json'
        self.db = self.root/'probe-latch.sqlite'
        self._admitted()
        self._marker_raw,self._marker_identity = _regular(self.marker,4096)
        self._metadata = _parse(self._marker_raw)
        _need(set(self._metadata)=={'schema','installation_id','nonce','root_identity','db_identity'})
        _need(self._metadata['schema']=='unified.network-probe-state.v1' and self._metadata['installation_id']==installation_id)
        _need(_hex(self._metadata['nonce'],32))
        _need(all(type(self._metadata[key]) is list and len(self._metadata[key])==2 and all(type(item) is int and item>=0 for item in self._metadata[key]) for key in ('root_identity','db_identity')))
        self._guard()
        with self._connection() as con:
            self._validate(con)

    def _admitted(self):
        _need(callable(self.admit) and type(self.installation_id) is str and re.fullmatch('[A-Za-z0-9_-]{1,80}',self.installation_id) is not None)
        try:
            _need(self.admit(self.root) is True,'PROBE_STATE_ADMISSION_REVOKED')
        except ProbeTransportBlocked:
            raise
        except Exception:
            raise ProbeTransportBlocked('PROBE_STATE_ADMISSION_REVOKED') from None
        _identity(self.root,directory=True)

    @classmethod
    def create(cls, root, installation_id, *, admit):
        leaf = Path(root)
        _need(callable(admit) and admit(leaf) is True,'PROBE_STATE_ADMISSION_REVOKED')
        root_identity = _identity(leaf,directory=True)
        _need(not list(leaf.iterdir()),'PROBE_FOREIGN_STATE_NOT_ADOPTED')
        _need(type(installation_id) is str and re.fullmatch('[A-Za-z0-9_-]{1,80}',installation_id) is not None)
        marker = leaf/'probe-owner.json'
        db = leaf/'probe-latch.sqlite'
        # Exclusive first claim. Failed creation remains visibly incomplete;
        # never delete or silently reconstruct a possibly interrupted latch.
        with marker.open('xb') as owner:
            owner.write(b'{"creating":true}');owner.flush();os.fsync(owner.fileno())
            with db.open('xb') as stream:
                stream.flush();os.fsync(stream.fileno())
            with contextlib.closing(sqlite3.connect(db,timeout=.2,isolation_level=None)) as con:
                con.execute('PRAGMA synchronous=FULL')
                con.execute('PRAGMA page_size=4096')
                con.execute('PRAGMA application_id='+str(APP_ID))
                con.execute('PRAGMA user_version=1')
                con.execute('BEGIN IMMEDIATE')
                con.execute(_SLOTS);con.execute(_EVENTS)
                con.executemany('INSERT INTO slots VALUES(?,0,?,?,?,?)',[(node,'COMPLETE','','','{}') for node in sorted(NODES)])
                _need(admit(leaf) is True and _identity(leaf,directory=True)==root_identity)
                con.execute('COMMIT')
            data = dict(schema='unified.network-probe-state.v1',installation_id=installation_id,
                        nonce=secrets.token_hex(16),root_identity=root_identity,db_identity=_identity(db))
            owner.seek(0);owner.write(_canonical(data));owner.truncate();owner.flush();os.fsync(owner.fileno())
        return cls.open(leaf,installation_id,admit=admit)

    @classmethod
    def open(cls, root, installation_id, *, admit):
        try:
            return cls(root,installation_id,admit=admit)
        except ProbeTransportBlocked:
            raise
        except (OSError,sqlite3.Error):
            raise ProbeTransportBlocked('PROBE_STATE_UNAVAILABLE') from None

    def _guard(self, *, writing=False):
        self._admitted()
        raw,identity = _regular(self.marker,4096)
        _need(raw==self._marker_raw and identity==self._marker_identity)
        _need(_identity(self.root,directory=True)==self._metadata['root_identity'])
        _need(_identity(self.db)==self._metadata['db_identity'] and self.db.stat().st_size<=MAX_DB_BYTES)
        for suffix in ('-wal','-shm','-journal'):
            sidecar = self.db.with_name(self.db.name+suffix)
            try:
                _identity(sidecar)
            except FileNotFoundError:
                continue
            _need(writing and suffix=='-journal','PROBE_FOREIGN_SIDECAR_NOT_ADOPTED')

    @contextlib.contextmanager
    def _connection(self):
        con = None
        try:
            self._guard()
            con = sqlite3.connect(self.db.as_uri()+'?mode=rw',uri=True,timeout=.2,isolation_level=None)
            con.execute('PRAGMA synchronous=FULL')
            con.execute('PRAGMA trusted_schema=OFF')
            deadline = time.monotonic()+.5
            con.set_progress_handler(lambda:int(time.monotonic()>=deadline),1000)
            self._guard()
            yield con
        except ProbeTransportBlocked:
            raise
        except (OSError,sqlite3.Error):
            raise ProbeTransportBlocked('PROBE_STATE_UNAVAILABLE') from None
        finally:
            if con is not None:
                try:
                    if con.in_transaction:con.execute('ROLLBACK')
                finally:
                    con.close()

    def _validate(self, con):
        _need(con.execute('PRAGMA application_id').fetchone()==(APP_ID,))
        _need(con.execute('PRAGMA user_version').fetchone()==(1,))
        _need(con.execute('PRAGMA page_count').fetchone()[0]<=2048)
        schema=con.execute("SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name LIMIT 4").fetchall()
        _need(schema==[('table','events',_EVENTS),('table','slots',_SLOTS)])
        rows=con.execute('SELECT node,generation,status,nonce,recipe_sha,receipt FROM slots LIMIT 7').fetchall()
        _need(len(rows)==6 and {row[0] for row in rows}==NODES)
        slots={row[0]:dict(zip(('node','generation','status','nonce','recipe_sha','receipt'),row)) for row in rows}
        events=con.execute('SELECT sequence,node,generation,status,nonce,recipe_sha,receipt FROM events ORDER BY sequence LIMIT 513').fetchall()
        _need(len(events)<=MAX_EVENTS,'PROBE_EVIDENCE_CAPACITY')
        states={node:(0,'COMPLETE','','','{}') for node in NODES}
        used=set()
        for expected,event in enumerate(events,1):
            seq,node,generation,status,nonce,recipe,receipt=event
            _need(seq==expected and node in NODES and type(generation) is int and 1<=generation<=1000000000)
            _need(status in ('IN_FLIGHT','COMPLETE','UNCERTAIN') and _hex(nonce,32) and _hex(recipe,64))
            _need(type(receipt) is str)
            try:_parse(receipt.encode('ascii'))
            except UnicodeError:raise ProbeTransportBlocked('PROBE_STATE_UNAVAILABLE') from None
            prior=states[node]
            if status=='IN_FLIGHT':
                _need(prior[1]=='COMPLETE' and generation==prior[0]+1 and nonce not in used and receipt=='{}')
                used.add(nonce)
            else:
                _need(prior[:4]==(generation,'IN_FLIGHT',nonce,recipe))
            states[node]=(generation,status,nonce,recipe,receipt)
        for node,row in slots.items():
            _need(tuple(row[key] for key in ('generation','status','nonce','recipe_sha','receipt'))==states[node])
        return slots,events

    def state(self, node):
        _node(node)
        with self._connection() as con:
            states,_ = self._validate(con)
            return dict(states[node])

    def _change(self, node, nonce, recipe, receipt, *, terminal=None):
        _node(node);_need(_hex(nonce,32),'PROBE_NONCE_REJECTED')
        raw = _canonical(receipt).decode('ascii')
        with self._connection() as con:
            con.execute('BEGIN IMMEDIATE')
            states,events=self._validate(con)
            before=states[node]
            _need(len(events)<MAX_EVENTS,'PROBE_EVIDENCE_CAPACITY')
            if terminal is None:
                _need(len(events)+sum(row['status']=='IN_FLIGHT' for row in states.values())+2<=MAX_EVENTS,'PROBE_EVIDENCE_CAPACITY')
                _need(before['status']=='COMPLETE','PROBE_OPERATION_UNRESOLVED')
                _need(_hex(recipe,64),'PROBE_RECIPE_REJECTED')
                _need(not any(event[4]==nonce for event in events),'PROBE_NONCE_REJECTED')
                generation=before['generation']+1;status='IN_FLIGHT'
            else:
                _need(before['status']=='IN_FLIGHT' and before['nonce']==nonce,'PROBE_OPERATION_MISMATCH')
                generation=before['generation'];recipe=before['recipe_sha'];status=terminal
            changed=con.execute('UPDATE slots SET generation=?,status=?,nonce=?,recipe_sha=?,receipt=? WHERE node=? AND generation=? AND status=? AND nonce=?',
                (generation,status,nonce,recipe,raw,node,before['generation'],before['status'],before['nonce'])).rowcount
            _need(changed==1,'PROBE_OPERATION_MISMATCH')
            con.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?)',(len(events)+1,node,generation,status,nonce,recipe,raw))
            self._guard(writing=True)
            con.execute('COMMIT')
            self._guard()
        return self.state(node)

    def begin(self, node, nonce, recipe_sha):
        return self._change(node,nonce,recipe_sha,{})

    def finish(self, node, nonce, receipt, *, exit_confirmed):
        return self._change(node,nonce,None,receipt,terminal='COMPLETE' if exit_confirmed is True else 'UNCERTAIN')


@dataclass(frozen=True)
class RunResult:
    returncode: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool
    output_limit: bool
    local_process_exit_confirmed: bool
    stdout_eof: bool
    stderr_eof: bool
    readers_joined: bool

    @property
    def local_exit_confirmed(self):
        # A reader returning on overflow/error is not EOF. These independent
        # facts must all be literal True before a monitor operation can clear.
        return all(value is True for value in (self.local_process_exit_confirmed,
            self.stdout_eof,self.stderr_eof,self.readers_joined))


@dataclass(frozen=True)
class _Recipe:
    node: str
    nonce: str
    source_sha256: str
    command: str
    encoded: str
    encoded_sha256: str
    command_sha256: str
    payload_sha256: str
    source_offset: int
    source_length: int


_OWNER_PREFIX = r'''$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false);$n='__NONCE__';$s=Get-CimInstance Win32_Process -Filter ('ProcessId='+$PID);$p=Get-CimInstance Win32_Process -Filter ('ProcessId='+$s.ParentProcessId);if(-not $s -or -not $p -or [Environment]::MachineName -ne '__NODE__'){exit 73};$h=@{schema='unified.network-probe-owner.v1';computer=[Environment]::MachineName;nonce=$n;pid=$PID;ppid=$s.ParentProcessId;parent_ppid=$p.ParentProcessId;created_utc=$s.CreationDate.ToUniversalTime().ToString('o');parent_created_utc=$p.CreationDate.ToUniversalTime().ToString('o')};[Console]::Out.WriteLine('UNIFIED_PROBE_OWNER '+($h|Microsoft.PowerShell.Utility\ConvertTo-Json -Compress));[Console]::Out.Flush();$r=& {
'''
_RESULT_SUFFIX = r'''
};if($r -isnot [string] -or $r.Length -gt 1048576){exit 75};[Console]::Out.WriteLine('UNIFIED_PROBE_RESULT '+$n+' '+$r);[Console]::Out.Flush();exit 0'''
_BOOTSTRAP = r'''$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';$n='__NONCE__';try{$k='UNIFIED_NP_'+$n;$b=[Convert]::FromBase64String([Environment]::GetEnvironmentVariable($k,'Process'));[Environment]::SetEnvironmentVariable($k,$null,'Process');$z=New-Object IO.Compression.GZipStream((New-Object IO.MemoryStream(,$b)),[IO.Compression.CompressionMode]::Decompress);$b=New-Object byte[] (__PAYLOAD_LENGTH__+1);$i=0;while($i -lt $b.Length){$c=$z.Read($b,$i,$b.Length-$i);if($c -eq 0){break};$i+=$c};$z.Dispose();if($i -ne __PAYLOAD_LENGTH__){exit 74};$s=[Security.Cryptography.SHA256]::Create();function D($v){([BitConverter]::ToString($v)).Replace('-','')};$d=D ($s.ComputeHash($b,0,$i));$q=D ($s.ComputeHash($b,__OFFSET__,__LENGTH__));$s.Dispose();if($d -ne '__PAYLOAD_SHA__' -or $q -ne '__SOURCE_SHA__'){exit 74};&([scriptblock]::Create([Text.Encoding]::UTF8.GetString($b,0,$i)));exit 0}catch{exit 76}'''


def _encoded(script):
    return base64.b64encode(script.encode('utf-16le')).decode('ascii')


def _make_recipe(node, nonce, source):
    _need(type(node) is str and node in REMOTE_NODES,'PROBE_HOST_REJECTED')
    _need(_hex(nonce,32),'PROBE_NONCE_REJECTED')
    _need(type(source) is bytes and 1<=len(source)<=65536,'PROBE_SOURCE_REJECTED')
    try:source.decode('utf-8-sig')
    except UnicodeError:raise ProbeTransportBlocked('PROBE_SOURCE_REJECTED') from None
    digest=hashlib.sha256(source).hexdigest()
    prefix=_OWNER_PREFIX.replace('__NONCE__',nonce).replace('__NODE__',node).encode('utf-8')
    payload=prefix+source+_RESULT_SUFFIX.encode('utf-8')
    payload_sha=hashlib.sha256(payload).hexdigest()
    bootstrap=_BOOTSTRAP.replace('__NONCE__',nonce).replace('__SOURCE_SHA__',digest).replace('__PAYLOAD_SHA__',payload_sha).replace('__OFFSET__',str(len(prefix))).replace('__LENGTH__',str(len(source))).replace('__PAYLOAD_LENGTH__',str(len(payload)))
    encoded=_encoded(bootstrap)
    packed=base64.b64encode(gzip.compress(payload,mtime=0)).decode('ascii')
    _need(re.fullmatch('[A-Za-z0-9+/=]+',packed) is not None)
    # Only the transient cmd child owns this variable; no setx, user/system
    # environment or stdin. Both strings are closed ASCII, no caller shell text.
    # No nested quotes around set: name/value contain only closed safe ASCII.
    # A single quoted /c argument survives both cmd and PowerShell default
    # shells; nested set quotes are changed by PowerShell's native binding.
    command=r'C:\Windows\System32\cmd.exe /d /v:off /s /c "set UNIFIED_NP_'+nonce+'='+packed+r'&C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoLogo -NoProfile -NonInteractive -EncodedCommand '+encoded+'"'
    _need(len(command)<=7000 and len(encoded)<=7000,'PROBE_COMMAND_BOUNDS')
    return _Recipe(node,nonce,digest,command,encoded,hashlib.sha256(encoded.encode('ascii')).hexdigest(),hashlib.sha256(command.encode('ascii')).hexdigest(),payload_sha,len(prefix),len(source))


def _remote_json(raw, limit=1048576):
    _need(type(raw) is bytes and len(raw)<=limit,'PROBE_FRAME_REJECTED')
    try:
        value=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=_object,
            parse_constant=lambda x: (_ for _ in ()).throw(ValueError()))
        _need(type(value) is dict,'PROBE_FRAME_REJECTED')
        return value
    except (ValueError,TypeError,UnicodeError,RecursionError):
        raise ProbeTransportBlocked('PROBE_FRAME_REJECTED') from None


def _header(stdout, recipe):
    first=stdout.split(b'\n',1)[0].rstrip(b'\r')
    _need(first.startswith(b'UNIFIED_PROBE_OWNER '),'PROBE_OWNER_UNAVAILABLE')
    owner=_remote_json(first[len(b'UNIFIED_PROBE_OWNER '):],2048)
    _need(set(owner)=={'schema','computer','nonce','pid','ppid','parent_ppid','created_utc','parent_created_utc'},'PROBE_OWNER_UNAVAILABLE')
    _need(owner['schema']=='unified.network-probe-owner.v1' and owner['computer']==recipe.node and owner['nonce']==recipe.nonce,'PROBE_OWNER_UNAVAILABLE')
    _need(all(type(owner[key]) is int and 1<=owner[key]<=0xFFFFFFFF for key in ('pid','ppid','parent_ppid')) and len({owner[key] for key in ('pid','ppid','parent_ppid')})==3,'PROBE_OWNER_UNAVAILABLE')
    for key in ('created_utc','parent_created_utc'):
        _need(type(owner[key]) is str and re.fullmatch(r'20[0-9]{2}-[01][0-9]-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]:[0-5][0-9]\.[0-9]{7}Z',owner[key]) is not None,'PROBE_OWNER_UNAVAILABLE')
    return owner


# Kept as a pure function inside the actual cleanup script so hosted model
# tests can invoke the same guards with inert Process/CIM-shaped objects.
_MATCH_PS = r'''function M($a,$b,$v){if(-not $a -or -not $b){return $false};$m=[regex]::Matches([string]$a.CommandLine,'(?i)-EncodedCommand\s+([A-Za-z0-9+/=]+)');$c=$a.CreationDate.ToUniversalTime();$h=$b.StartTime.ToUniversalTime();return ($a.ProcessId -eq $v[0] -and $a.ParentProcessId -eq $v[1] -and $a.Name -ieq $v[2] -and $c.ToString('o') -eq $v[3] -and $a.ExecutablePath -ieq $v[4] -and $c.Ticks -eq ($h.Ticks-($h.Ticks%10)) -and $m.Count -eq 1 -and (D $m[0].Groups[1].Value) -eq $e -and -not $b.HasExited)}'''


def _cleanup_command(recipe, owner):
    # All inserted values were closed-type checked by _header; never accept a
    # caller command, process selector, arbitrary executable or wildcard.
    script=r'''$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';$n='__NONCE__';$e='__ENCODED_SHA__';$s=[Security.Cryptography.SHA256]::Create();function D([string]$v){([BitConverter]::ToString($s.ComputeHash([Text.Encoding]::UTF8.GetBytes($v)))).Replace('-','').ToLowerInvariant()};__MATCH__;$r=@{schema='unified.network-probe-cleanup.v1';computer=[Environment]::MachineName;nonce=$n;pid=__PID__;created_utc='__CREATED__';owner_exit_confirmed=$false;parent_exit_confirmed=$false;stop_attempted=$false};$t=$null;$p=$null;try{if($r.computer -ne '__NODE__'){throw 'HOST'};$a=Get-CimInstance Win32_Process -Filter 'ProcessId=__PID__';$b=Get-CimInstance Win32_Process -Filter 'ProcessId=__PPID__';$v=@(__PPID__,__PARENT_PPID__,'cmd.exe','__PARENT_CREATED__','C:\Windows\system32\cmd.exe');if(-not $a){$r.owner_exit_confirmed=$true;if(-not $b){$r.parent_exit_confirmed=$true}else{$p=[Diagnostics.Process]::GetProcessById(__PPID__);$ph=$p.Handle;if(M $b $p $v){$r.parent_exit_confirmed=$p.WaitForExit(2000)}}}elseif($b){$t=[Diagnostics.Process]::GetProcessById(__PID__);$p=[Diagnostics.Process]::GetProcessById(__PPID__);$th=$t.Handle;$ph=$p.Handle;$a=Get-CimInstance Win32_Process -Filter 'ProcessId=__PID__';$b=Get-CimInstance Win32_Process -Filter 'ProcessId=__PPID__';$w=@(__PID__,__PPID__,'powershell.exe','__CREATED__','C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe');if((M $a $t $w) -and (M $b $p $v) -and -not $t.HasExited -and -not $p.HasExited){$r.stop_attempted=$true;Stop-Process -InputObject $t -Confirm:$false;$r.owner_exit_confirmed=$t.WaitForExit(5000);$r.parent_exit_confirmed=$p.WaitForExit(2000)}}}catch{}finally{if($t){$t.Dispose()};if($p){$p.Dispose()};$s.Dispose()};$r|Microsoft.PowerShell.Utility\ConvertTo-Json -Compress'''
    replacements={'__MATCH__':_MATCH_PS,'__NONCE__':recipe.nonce,'__ENCODED_SHA__':recipe.encoded_sha256,
        '__PID__':str(owner['pid']),'__PPID__':str(owner['ppid']),'__PARENT_PPID__':str(owner['parent_ppid']),
        '__CREATED__':owner['created_utc'],'__PARENT_CREATED__':owner['parent_created_utc'],'__NODE__':recipe.node}
    for key,value in replacements.items():script=script.replace(key,value)
    command=r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoLogo -NoProfile -NonInteractive -EncodedCommand '+_encoded(script)
    _need(len(command)<=7000,'PROBE_COMMAND_BOUNDS')
    return command


class _BoundedRunner:
    """Own one local SSH Process handle; bounded pipes, no stdin or child kill.

    Local deadlines cannot guarantee remote termination. A missing owner frame
    or timeout of the cleanup SSH itself remains sticky UNCERTAIN, with no
    retry or claim of a hard remote deadline. Deployment must stay blocked.
    """
    def run(self, argv, *, timeout, stdout_limit, stderr_limit, stdin_mode):
        _need(os.name=='nt' and stdin_mode=='DEVNULL','WINDOWS_MONITOR_REQUIRED')
        from .worker_transport import windows_ssh_environment
        buffers=[bytearray(),bytearray()];limits=[stdout_limit,stderr_limit]
        overflow=threading.Event();eof=[threading.Event(),threading.Event()];threads=[];proc=None;timed_out=False;exited=False
        def drain(index,stream):
            try:
                while True:
                    data=stream.read(4096)
                    if not data:eof[index].set();return
                    room=limits[index]+1-len(buffers[index])
                    buffers[index].extend(data[:max(0,room)])
                    if len(buffers[index])>limits[index]:overflow.set();return
            except (OSError,ValueError):overflow.set()
        try:
            proc=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                bufsize=0,shell=False,env=windows_ssh_environment(),creationflags=subprocess.CREATE_NO_WINDOW)
            for index,stream in enumerate((proc.stdout,proc.stderr)):
                thread=threading.Thread(target=drain,args=(index,stream),daemon=True);threads.append(thread);thread.start()
            deadline=time.monotonic()+timeout
            while proc.poll() is None:
                if overflow.is_set() or time.monotonic()>=deadline:
                    timed_out=not overflow.is_set();break
                time.sleep(.01)
            if proc.poll() is None:proc.kill()  # Popen retains the actual handle.
            proc.wait(timeout=2);exited=True
        except BaseException:
            if proc is not None:
                try:
                    if proc.poll() is None:proc.kill()
                    proc.wait(timeout=2);exited=True
                except (OSError,subprocess.SubprocessError):pass
        finally:
            for thread in threads:thread.join(2)
            drained=not any(thread.is_alive() for thread in threads)
            if proc is not None:
                for stream in (proc.stdout,proc.stderr):
                    if stream is not None:stream.close()
        return RunResult(proc.returncode if proc is not None else None,bytes(buffers[0][:stdout_limit]),bytes(buffers[1][:stderr_limit]),
                         timed_out,overflow.is_set(),exited,eof[0].is_set(),eof[1].is_set(),drained)


class NetworkProbeTransport:
    """Closed five-host observer for an already admitted LS5 controller.

    No ambient SSH aliases/configuration or automatic Tailscale fallback. No
    arbitrary source/command/host or cleanup API is exposed. Tests inject a
    modeled runner; such results never qualify SSH, SCM or a real office host.
    """
    def __init__(self, journal, *, inventory, require_current, runner=None):
        _need(isinstance(journal,ProbeJournal) and isinstance(inventory,LanProbeInventory) and callable(require_current))
        self.journal=journal;self.require_current=require_current
        self.inventory=inventory
        self.runner=runner if runner is not None else _BoundedRunner()
        _need(callable(getattr(self.runner,'run',None)))

    def _current(self):
        try:_need(self.require_current() is True,'PROBE_SOURCE_ADMISSION_REVOKED')
        except ProbeTransportBlocked:raise
        except Exception:raise ProbeTransportBlocked('PROBE_SOURCE_ADMISSION_REVOKED') from None

    def _run(self,endpoint,command,seconds,limit,*,cleanup=False):
        try:argv=endpoint._argv(command,cleanup=cleanup)
        except (ProbeTransportBlocked,LanInventoryBlocked) as exc:
            if not cleanup:raise _NoSpawn(str(exc)) from None
            raise
        endpoint._channel_started();result=None;attempted=False
        try:
            if not cleanup:
                try:self._current()
                except ProbeTransportBlocked as exc:raise _NoSpawn(str(exc)) from None
            attempted=True
            result=self.runner.run(argv,timeout=seconds,stdout_limit=limit,stderr_limit=65536,stdin_mode='DEVNULL')
            return result
        finally:
            endpoint._channel_finished(not attempted or (isinstance(result,RunResult) and result.local_process_exit_confirmed is True))

    def observe(self, node):
        _need(type(node) is str and node in REMOTE_NODES,'PROBE_HOST_REJECTED')
        _need(not isinstance(self.runner,_BoundedRunner) or os.name=='nt','WINDOWS_MONITOR_REQUIRED')
        self._current()  # Source admission precedes private asset access too.
        try:
            with self.inventory.lease(node) as endpoint:
                _need(endpoint.installation_id==self.journal.installation_id,'PROBE_INSTALLATION_MISMATCH')
                return self._observe_endpoint(node,endpoint)
        except LanInventoryBlocked as exc:raise ProbeTransportBlocked(str(exc)) from None

    def _observe_endpoint(self,node,endpoint):
        self._current()
        source_path=Path(__file__).absolute().parents[1]/'scripts/network_readonly_probe.ps1'
        source,_=_regular(source_path,65536)
        self._current()
        recipe=_make_recipe(node,secrets.token_hex(16),source)
        # Both commands must fit before the first effect; cleanup shape has
        # maximum-width PID/UTC placeholders, not a permissive fallback path.
        max_owner=dict(pid=4294967295,ppid=4294967294,parent_ppid=4294967293,
            created_utc='2099-12-31T23:59:59.9999999Z',parent_created_utc='2099-12-31T23:59:59.9999999Z')
        _cleanup_command(recipe,max_owner)
        self.journal.begin(node,recipe.nonce,recipe.command_sha256)
        try:self._current();endpoint._current()
        except (ProbeTransportBlocked,LanInventoryBlocked):
            self.journal.finish(node,recipe.nonce,{'reason':'ADMISSION_REVOKED_BEFORE_SPAWN'},exit_confirmed=True)
            raise
        receipt=dict(source_sha256=recipe.source_sha256,command_sha256=recipe.command_sha256,
                     nonce=recipe.nonce,inventory_sha256=endpoint.scope['sha256'],reason='PROBE_TRANSPORT_UNCERTAIN')
        result=None;observation=None;confirmed=False
        try:
            result=self._run(endpoint,recipe.command,65,1048576+4096)
            _need(isinstance(result,RunResult),'PROBE_TRANSPORT_UNCERTAIN')
            _need(type(result.stdout) is bytes and len(result.stdout)<=1048576+4096 and type(result.stderr) is bytes and len(result.stderr)<=65536,'PROBE_OUTPUT_BOUNDS')
            receipt.update(stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),stderr_sha256=hashlib.sha256(result.stderr).hexdigest(),
                stderr_bytes=len(result.stderr),local_ssh_exit_and_drain_confirmed=result.local_exit_confirmed,
                local_ssh_os_exit_confirmed=result.local_process_exit_confirmed,stdout_eof=result.stdout_eof,
                stderr_eof=result.stderr_eof,readers_joined=result.readers_joined,
                timed_out=result.timed_out,output_limit=result.output_limit)
            owner=_header(result.stdout,recipe);receipt['owner']=owner
            cleanup=self._run(endpoint,_cleanup_command(recipe,owner),12,8192,cleanup=True)
            _need(isinstance(cleanup,RunResult) and cleanup.returncode==0 and cleanup.local_exit_confirmed is True and not cleanup.timed_out and not cleanup.output_limit,'PROBE_CLEANUP_UNCERTAIN')
            proof=_remote_json(cleanup.stdout,8192)
            _need(set(proof)=={'schema','computer','nonce','pid','created_utc','owner_exit_confirmed','parent_exit_confirmed','stop_attempted'},'PROBE_CLEANUP_UNCERTAIN')
            _need(proof['schema']=='unified.network-probe-cleanup.v1' and proof['computer']==node and proof['nonce']==recipe.nonce and type(proof['pid']) is int and proof['pid']==owner['pid'] and proof['created_utc']==owner['created_utc'],'PROBE_CLEANUP_UNCERTAIN')
            _need(proof['owner_exit_confirmed'] is True and proof['parent_exit_confirmed'] is True and type(proof['stop_attempted']) is bool,'PROBE_CLEANUP_UNCERTAIN')
            confirmed=result.local_exit_confirmed is True
            receipt.update(cleanup=proof,cleanup_stdout_sha256=hashlib.sha256(cleanup.stdout).hexdigest(),
                cleanup_stderr_sha256=hashlib.sha256(cleanup.stderr).hexdigest(),cleanup_stderr_bytes=len(cleanup.stderr))
            _need(confirmed,'PROBE_LOCAL_DRAIN_UNCERTAIN')
            self._current()  # Revocation never skips cleanup of our old owner.
            endpoint._current()
            _need(not result.timed_out,'PROBE_DEADLINE')
            _need(not result.output_limit and result.returncode==0,'PROBE_EXECUTION_FAILED')
            lines=result.stdout.splitlines()
            prefix=b'UNIFIED_PROBE_RESULT '+recipe.nonce.encode('ascii')+b' '
            _need(len(lines)==2 and lines[1].startswith(prefix),'PROBE_FRAME_REJECTED')
            candidate=_remote_json(lines[1][len(prefix):])
            _need(candidate.get('computer')==node and candidate.get('schema')=='unified.network-readonly-observation.v1' and candidate.get('mutations') is False,'PROBE_FRAME_REJECTED')
            observation=candidate
            receipt['reason']='OWNED_HELPER_EXIT_CONFIRMED_READY_FOR_PUBLICATION_CHECK'
        except BaseException as exc:
            if isinstance(exc,_NoSpawn):confirmed=True
            receipt['reason']=str(exc) if isinstance(exc,(ProbeTransportBlocked,LanInventoryBlocked)) else 'PROBE_TRANSPORT_UNCERTAIN'
        self.journal.finish(node,recipe.nonce,receipt,exit_confirmed=confirmed)
        if observation is None:raise ProbeTransportBlocked(receipt['reason'])
        self._current()  # Fresh after persistence, immediately before handoff.
        endpoint._current()
        return observation
