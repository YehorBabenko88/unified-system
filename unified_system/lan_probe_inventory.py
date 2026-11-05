"""Owner-admitted private LAN assets; JSON is data, never a grant.

Actual office addresses, users and keys belong in the owner's external pinned
inventory, not this repository. No enrollment, keyscan, TOFU, network repair or
Tailscale fallback is provided. The caller must use a real protected-plan/kernel
admission object. This does not contain hostile same-user/Admin code.
"""
import base64
import contextlib
import copy
import ctypes
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import struct
import subprocess


NODES=frozenset(('PC1','PC2','PC3','PC4','LS7'))
_QUARANTINED={}


class LanInventoryBlocked(ValueError):pass


def _need(value,reason='LAN_INVENTORY_REJECTED'):
    if value is not True:raise LanInventoryBlocked(reason)


def _ordinary(raw):
    path=Path(raw)
    _need(path.is_absolute() and len(str(path))<=1024 and not str(path).startswith(('\\\\','//')))
    _need(not any(char in str(path) for char in ('%','$','~','"','`','\0','\r','\n')))
    _need('..' not in path.parts)
    if os.name=='nt':
        from ctypes import wintypes as w
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetDriveTypeW.argtypes=[w.LPCWSTR];kernel.GetDriveTypeW.restype=w.UINT
        _need(kernel.GetDriveTypeW(path.anchor)==3,'LAN_ASSET_NONLOCAL')
    for part in path.parts:
        _need(part==path.anchor or (':' not in part and not part.endswith((' ','.'))))
    for item in (*reversed(path.parents),path):
        info=item.lstat()
        _need(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&1024)
    return path


def _private_path(raw,root):
    _need(type(raw) is str)
    path=_ordinary(Path(raw))
    _need(path.is_relative_to(root) and path!=root,'LAN_ASSET_OUTSIDE_PRIVATE_ROOT')
    # Only examine named ancestors, never walk unrelated repositories/archives.
    for parent in path.parents:
        try:(parent/'.git').lstat()
        except FileNotFoundError:continue
        raise LanInventoryBlocked('LAN_ASSET_IN_REPOSITORY')
    return path


def _facts(path,stream):
    _ordinary(path)
    info=path.lstat();held=os.fstat(stream.fileno())
    _need(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and stat.S_ISREG(held.st_mode) and held.st_nlink==1)
    _need((info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)==(held.st_dev,held.st_ino,held.st_size,held.st_mtime_ns))
    _need(0<=info.st_size<=65536)
    return dict(path=path,device=info.st_dev,inode=info.st_ino,size=info.st_size,mtime_ns=info.st_mtime_ns)


class _LockedRead:
    """Windows READ sharing only: SSH may read, writers/deleters cannot open.

    POSIX descriptors are for modeled CI only; real transport is Windows-only.
    The protected owner must also admit the ancestor namespace/ACLs. No claim
    is made against privileged ancestor replacement or a controller crash.
    """
    def __init__(self,path):
        self.path=_ordinary(path);self.stream=None
        try:
            if os.name=='nt':
                import msvcrt
                from ctypes import wintypes as w
                kernel=ctypes.WinDLL('kernel32',use_last_error=True)
                kernel.CreateFileW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,w.LPVOID,w.DWORD,w.DWORD,w.HANDLE]
                kernel.CreateFileW.restype=w.HANDLE
                kernel.CloseHandle.argtypes=[w.HANDLE];kernel.CloseHandle.restype=w.BOOL
                handle=kernel.CreateFileW(str(path),0x80000000,1,None,3,0x00200000,None)
                if handle==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
                try:fd=msvcrt.open_osfhandle(int(handle),os.O_RDONLY|os.O_BINARY)
                except BaseException:kernel.CloseHandle(handle);raise
                try:self.stream=os.fdopen(fd,'rb',buffering=0)
                except BaseException:os.close(fd);raise
            else:
                fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
                self.stream=os.fdopen(fd,'rb',buffering=0)
            self.original=_facts(self.path,self.stream)
        except BaseException:
            if self.stream is not None:self.stream.close()
            raise
    def check(self):
        _need(self.original==_facts(self.path,self.stream),'LAN_ASSET_IDENTITY_CHANGED')
    def facts(self):self.check();return dict(self.original)
    def read(self,limit=65536):
        self.check();self.stream.seek(0);raw=self.stream.read(limit+1)
        _need(len(raw)<=limit);self.check();return raw
    def close(self):
        if self.stream is not None:self.stream.close();self.stream=None


def _pairs(pairs):
    value={}
    for key,item in pairs:_need(key not in value);value[key]=item
    return value


def _json(raw):
    try:
        value=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=_pairs,
            parse_constant=lambda x: (_ for _ in ()).throw(ValueError()))
        _need(type(value) is dict);return value
    except (ValueError,TypeError,UnicodeError,RecursionError):raise LanInventoryBlocked('LAN_INVENTORY_REJECTED') from None


def _fingerprint(blob):return 'SHA256:'+base64.b64encode(hashlib.sha256(blob).digest()).decode('ascii').rstrip('=')


def _host_key(value):
    _need(type(value) is str and len(value)<=256 and value.startswith('ssh-ed25519 '))
    text=value[len('ssh-ed25519 '):]
    try:blob=base64.b64decode(text,validate=True)
    except ValueError:raise LanInventoryBlocked('LAN_HOST_KEY_REJECTED') from None
    _need(base64.b64encode(blob).decode('ascii')==text and len(blob)==51,'LAN_HOST_KEY_REJECTED')
    _need(blob[:4]==struct.pack('>I',11) and blob[4:15]==b'ssh-ed25519' and blob[15:19]==struct.pack('>I',32),'LAN_HOST_KEY_REJECTED')
    return _fingerprint(blob)


def _scope(admission):
    _need(not isinstance(admission,dict) and all(callable(getattr(admission,name,None)) for name in
        ('require_current','network_inventory_identity','admit_lan_endpoint','admit_ssh_identity')),'LAN_OWNER_ADMISSION_REQUIRED')
    try:_need(admission.require_current() is True,'LAN_OWNER_ADMISSION_REVOKED')
    except LanInventoryBlocked:raise
    except Exception:raise LanInventoryBlocked('LAN_OWNER_ADMISSION_REVOKED') from None
    try:scope=admission.network_inventory_identity()
    except Exception:raise LanInventoryBlocked('LAN_OWNER_SCOPE_UNAVAILABLE') from None
    _need(type(scope) is dict and set(scope)=={'path','sha256','installation_id','private_root'})
    _need(isinstance(scope['path'],Path) and isinstance(scope['private_root'],Path))
    root=_ordinary(scope['private_root']);_need(root.is_dir())
    _private_path(str(scope['path']),root)
    _need(type(scope['sha256']) is str and re.fullmatch('[a-f0-9]{64}',scope['sha256']) is not None)
    _need(type(scope['installation_id']) is str and re.fullmatch('[A-Za-z0-9_-]{1,80}',scope['installation_id']) is not None)
    return dict(scope)


def _grant(admission,name,reason,*args):
    try:_need(getattr(admission,name)(*args) is True,reason)
    except LanInventoryBlocked:raise
    except Exception:raise LanInventoryBlocked(reason) from None


def _inventory(raw,scope):
    _need(hashlib.sha256(raw).hexdigest()==scope['sha256'],'LAN_EXTERNAL_PIN_MISMATCH')
    data=_json(raw)
    _need(set(data)=={'schema','installation_id','empty_config','nodes'})
    _need(data['schema']=='unified.lan-probe-inventory.v1' and data['installation_id']==scope['installation_id'])
    config=_private_path(data['empty_config'],scope['private_root'])
    _need(type(data['nodes']) is list and len(data['nodes'])==5)
    rows={};keys=set()
    for row in data['nodes']:
        _need(type(row) is dict and set(row)=={'node','address','port','username','host_key','known_hosts','identity_file','identity_public_fingerprint'})
        node=row['node'];_need(type(node) is str and node in NODES and node not in rows,'LAN_NODE_REJECTED')
        try:ip=ipaddress.IPv4Address(row['address'])
        except (ValueError,TypeError):raise LanInventoryBlocked('LAN_LITERAL_IP_REQUIRED') from None
        # TEST-NET is non-global and supports offline fixtures. A real protected
        # owner's endpoint callback must admit the exact current office mapping.
        _need(type(row['address']) is str and str(ip)==row['address'] and ip.is_private
            and not (ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved),'LAN_LITERAL_IP_REQUIRED')
        _need(type(row['port']) is int and row['port']==22)
        _need(type(row['username']) is str and re.fullmatch(r'(?:[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\\)?[A-Za-z0-9][A-Za-z0-9_.-]{0,63}',row['username']) is not None)
        fingerprint=_host_key(row['host_key']);_need(fingerprint not in keys,'LAN_HOST_KEYS_NOT_DISTINCT');keys.add(fingerprint)
        _need(type(row['identity_public_fingerprint']) is str and re.fullmatch(r'SHA256:[A-Za-z0-9+/]{43}',row['identity_public_fingerprint']) is not None)
        entry=dict(row,known_hosts=_private_path(row['known_hosts'],scope['private_root']),
            identity_file=_private_path(row['identity_file'],scope['private_root']),host_fingerprint=fingerprint)
        rows[node]=entry
    return config,rows


class _EndpointLease:
    def __init__(self,owner,node,scope,row,config,files,stack):
        self.owner=owner;self.node=node;self.scope=scope;self.row=row;self.config=config
        self.files=files;self.stack=stack;self.pending=0;self.quarantined=False;self.closed=False
        self.installation_id=scope['installation_id']
        self.key=(self.installation_id,node)
    def _descriptor(self):
        return dict(node=self.node,address=self.row['address'],port=22,username=self.row['username'],
            host_fingerprint=self.row['host_fingerprint'],identity_public_fingerprint=self.row['identity_public_fingerprint'],
            identity_path=self.row['identity_file'],inventory_sha256=self.scope['sha256'],
            assets={name:held.facts() for name,held in self.files.items() if name!='identity'})
    def _locked(self):
        _need(not self.closed,'LAN_LEASE_CLOSED')
        for held in self.files.values():held.check()
    def _current(self):
        self._locked()
        _need(_scope(self.owner.admission)==self.scope,'LAN_OWNER_SCOPE_CHANGED')
        _grant(self.owner.admission,'admit_lan_endpoint','LAN_ENDPOINT_NOT_ADMITTED',self.node,copy.deepcopy(self._descriptor()))
        _grant(self.owner.admission,'admit_ssh_identity','LAN_IDENTITY_NOT_ADMITTED',self.node,self.files['identity'].facts(),self.row['identity_public_fingerprint'])
    def _channel_started(self):self._locked();self.pending+=1
    def _channel_finished(self,os_exit_confirmed):
        if os_exit_confirmed is True:self.pending-=1
        else:self.quarantined=True
    def _argv(self,command,*,cleanup):
        # Private assembly for the transport's fixed generated commands; no UI
        # endpoint or command selector is exposed by this inventory module.
        if cleanup:self._locked()  # Prior immutable lease survives revocation.
        else:self._current()
        _need(type(command) is str and len(command)<=7000 and '\r' not in command and '\n' not in command)
        alias='unified-lan-'+self.node.lower()
        options=('HostName='+self.row['address'],'HostKeyAlias='+alias,
            'HostKeyAlgorithms=ssh-ed25519','StrictHostKeyChecking=yes','BatchMode=yes',
            'UserKnownHostsFile="'+self.row['known_hosts'].as_posix()+'"',
            'GlobalKnownHostsFile="'+self.config.as_posix()+'"','KnownHostsCommand=none',
            'UpdateHostKeys=no','VerifyHostKeyDNS=no','CanonicalizeHostname=no','CheckHostIP=no',
            'IdentitiesOnly=yes','IdentityAgent=none','AddKeysToAgent=no','CertificateFile=none',
            # Preserve the OS client algorithm policy for the one admitted
            # identity; never fall back to other agent/default identities.
            'PubkeyAuthentication=yes','PreferredAuthentications=publickey',
            'PasswordAuthentication=no','KbdInteractiveAuthentication=no','NumberOfPasswordPrompts=0',
            'GSSAPIAuthentication=no','HostbasedAuthentication=no','PKCS11Provider=none','SecurityKeyProvider=none',
            'PermitLocalCommand=no','ProxyCommand=none','ProxyJump=none','ClearAllForwardings=yes',
            'ForwardAgent=no','ForwardX11=no','Tunnel=no','ControlMaster=no','ControlPersist=no',
            'ControlPath=none','ConnectTimeout=8')
        argv=[r'C:\Windows\System32\OpenSSH\ssh.exe','-F',self.config.as_posix(),'-T','-p','22',
            '-l',self.row['username'],'-i',self.row['identity_file'].as_posix()]
        for value in options:argv.extend(('-o',value))
        argv.extend((self.row['address'],command))
        _need(len(subprocess.list2cmdline(argv).encode('utf-16le'))//2<30000,'LAN_LOCAL_COMMAND_BOUNDS')
        return argv
    def _close(self):
        if self.pending or self.quarantined:
            # Keep exact files pinned within this controller process if a local
            # SSH owner might still read them. No automatic release/retry API.
            _QUARANTINED[self.key]=self
        else:self.closed=True;self.stack.close()


class LanProbeInventory:
    def __init__(self,admission):
        self.admission=admission
        try:_scope(admission)
        except LanInventoryBlocked:raise
        except Exception:raise LanInventoryBlocked('LAN_OWNER_ADMISSION_REQUIRED') from None
    @contextlib.contextmanager
    def lease(self,node):
        _need(type(node) is str and node in NODES,'LAN_NODE_REJECTED')
        scope=_scope(self.admission);key=(scope['installation_id'],node)
        _need(key not in _QUARANTINED and len(_QUARANTINED)<64,'LAN_LOCAL_OWNER_UNCERTAIN')
        stack=contextlib.ExitStack();endpoint=None;yielded=False
        try:
            files={}
            def hold(name,path):
                held=_LockedRead(path);stack.callback(held.close);files[name]=held;return held
            raw=hold('inventory',scope['path']).read()
            config,rows=_inventory(raw,scope);row=rows[node]
            _need(hold('config',config).read()==b'','LAN_CONFIG_NOT_EMPTY')
            known=hold('known_hosts',row['known_hosts']).read(4096)
            expected=('unified-lan-'+node.lower()+' '+row['host_key']).encode('ascii')
            _need(known in (expected+b'\n',expected+b'\r\n'),'LAN_KNOWN_HOSTS_REJECTED')
            endpoint=_EndpointLease(self,node,scope,row,config,files,stack)
            _grant(self.admission,'admit_lan_endpoint','LAN_ENDPOINT_NOT_ADMITTED',node,copy.deepcopy(endpoint._descriptor()))
            hold('identity',row['identity_file'])  # Metadata/lock only; never read.
            endpoint._current()
            yielded=True
            yield endpoint
        except LanInventoryBlocked:raise
        except (OSError,ValueError,TypeError,AttributeError):
            if yielded:raise  # Do not relabel a caller's durable transport result.
            raise LanInventoryBlocked('LAN_ASSET_UNAVAILABLE') from None
        finally:
            if endpoint is not None:endpoint._close()
            else:stack.close()
