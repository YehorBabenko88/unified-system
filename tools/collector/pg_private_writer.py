"""Exclusive six-file staging for one already admitted disposable PG root.

No native initialization/IO at import. Partial/uncertain files are retained;
there is no overwrite, cleanup-delete, ACL change, retry or authority grant.
"""
import hashlib
import os
from pathlib import Path
from .pg_protocol import Protocol
from .pg_qualification import Plan,WindowsBackend,_ordinary,_held

DIRECTORIES=('cwd','temp','logs','secrets','sql','results')
NAMES=('sql/bootstrap.sql','sql/migrate.sql','sql/verify.sql','sql/readback.sql','secrets/bootstrap-password','secrets/pgpass.conf')
SECRET=frozenset(('sql/bootstrap.sql','secrets/bootstrap-password','secrets/pgpass.conf'))

def require(value):
    if value is not True:raise ValueError('PG_PRIVATE_WRITER_DENIED')
def digest(raw):return hashlib.sha256(raw).hexdigest()

class PrivateWriter:
    """Exact protocol bytes only; public facts redact all secret-derived hashes."""
    def __init__(self,custodian,protocol,*,io=None):
        require(type(protocol) is Protocol and tuple(custodian.plan.sql_pins)==protocol.sql_pins())
        require(type(custodian.plan.native) is bool)
        if custodian.plan.native:
            require(io is None and type(custodian.plan) is Plan and type(custodian.backend) is WindowsBackend)
            io=_NativeIO(custodian)
        else:require(io is not None and type(io) is not _NativeIO)
        rows=protocol.private_files();require(tuple(n for n,_,_ in rows)==NAMES)
        self._expected={};self._done=set();self._failed=False;self._sealed=False;self._io=io
        for n,raw,secret in rows:
            require(type(raw) is bytes and 0<len(raw)<=65536 and type(secret) is bool and secret==(n in SECRET))
            # Every supplied file is closed ASCII, a subset of valid UTF-8.
            require(all(b in (9,10,13) or 32<=b<=126 for b in raw))
            self._expected[n]=(raw,secret)
        first=io.snapshot();self._identity=first['identity'];self._context=first['context'];self._check(first,set())
    def __repr__(self):return '<PrivateWriter PRIVATE_REDACTED>'
    def _check(self,snapshot,allowed):
        require(snapshot['identity']==self._identity and snapshot['context']==self._context)
        rows=snapshot['rows'];require(type(rows) is list and len(rows)==len(DIRECTORIES)+len(allowed))
        seen=set()
        for row in rows:
            n=row['name'];require(type(n) is str and n not in seen);seen.add(n)
            require(row['reparse'] is False and row['private'] is True)
            if n in DIRECTORIES:require(row['kind']=='directory')
            else:
                require(n in allowed and row['kind']=='file' and row['nlink']==1)
                raw,_=self._expected[n];require(row['bytes']==len(raw) and row['sha256']==digest(raw))
        require(seen==set(DIRECTORIES)|allowed)
    def __call__(self,name,raw,secret):
        fd=None;primary=None;close_error=False
        try:
            require(not self._failed and not self._sealed and type(name) is str and name in self._expected and name not in self._done)
            require(type(raw) is bytes and type(secret) is bool and (raw,secret)==self._expected[name])
            self._check(self._io.snapshot(),self._done)
            fd=self._io.create(name)
            self._io.write(fd,raw);self._io.flush(fd);self._io.check(fd,raw)
        except BaseException as e:primary=e;self._failed=True
        finally:
            if fd is not None:
                try:self._io.close(fd)
                except BaseException:close_error=True;self._failed=True
        if primary is not None or close_error:raise ValueError('PG_PRIVATE_WRITER_DENIED') from None
        try:
            self._check(self._io.snapshot(),self._done|{name});self._done.add(name)
            if len(self._done)==len(NAMES):self.finish()  # seals BEFORE initdb can run
        except BaseException:
            self._failed=True;raise ValueError('PG_PRIVATE_WRITER_DENIED') from None
    def finish(self):
        try:
            require(not self._failed and self._done==set(NAMES));self._check(self._io.snapshot(),self._done);self._sealed=True
        except BaseException:
            self._failed=True;raise ValueError('PG_PRIVATE_WRITER_DENIED') from None
        return {'scope':'OWN_PRIVATE_FILES_ONLY','sealed':True,'count':len(self._done),'files':[{'name':n,'bytes':len(raw),'sha256':'PRIVATE_REDACTED' if secret else digest(raw)} for n,(raw,secret) in self._expected.items()]}

class _NativeIO:
    """Own-root filesystem adapter, construction/use only under native lease."""
    def __init__(self,custodian):
        self.backend=custodian.backend;self.root=self.backend.root;self._fds={}
        require(self.backend.plan is custodian.plan and self.backend.context_identity is not None)
        sid,profile=self.backend.context_identity
        from .pg_qualification import _require_native_root
        _require_native_root(self.root,profile)
    def _context(self):
        require(self.backend._token()==self.backend.context_identity)
        s=_ordinary(self.root);require((s.st_dev,s.st_ino)==self.backend.root_identity);self.backend._private(self.root,self.backend.context_identity[0])
        return s
    def snapshot(self):
        root=self._context();rows=[];sid=self.backend.context_identity[0]
        for p in self.root.iterdir():
            name=p.name;require(name in DIRECTORIES);_ordinary(p);self.backend._private(p,sid)
            rows.append(dict(name=name,kind='directory',nlink=1,reparse=False,private=True))
            for f in p.iterdir():
                name=p.name+'/'+f.name;require(name in NAMES);s=_ordinary(f,True);self.backend._private(f,sid);raw=_held(f,limit=65536)
                rows.append(dict(name=name,kind='file',nlink=s.st_nlink,reparse=False,private=True,bytes=len(raw),sha256=digest(raw)))
        return dict(identity=(root.st_dev,root.st_ino),context=self.backend.context_identity,rows=rows)
    def create(self,name):
        require(name in NAMES);self._context();p=self.root/name;_ordinary(p.parent)
        self.backend._private(p.parent,self.backend.context_identity[0])
        # O_EXCL never adopts a preexisting leaf, including symlinks/reparse paths.
        fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_RDWR|getattr(os,'O_BINARY',0),0o600)
        self._fds[fd]=name  # retained immediately, before metadata/ACL inspection
        return fd
    def write(self,fd,raw):
        require(fd in self._fds and type(raw) is bytes and 0<len(raw)<=65536)
        # Check inherited ACL BEFORE credential bytes are written, never change it.
        p=self.root/self._fds[fd];_ordinary(p,True);self.backend._private(p,self.backend.context_identity[0])
        offset=0
        while offset<len(raw):
            count=os.write(fd,raw[offset:]);require(type(count) is int and 0<count<=len(raw)-offset);offset+=count
    def flush(self,fd):require(fd in self._fds);os.fsync(fd)
    def check(self,fd,expected):
        import stat
        require(fd in self._fds);self._context();p=self.root/self._fds[fd];path=_ordinary(p,True);self.backend._private(p,self.backend.context_identity[0]);before=os.fstat(fd)
        def common(s):return (s.st_dev,s.st_ino,stat.S_IFMT(s.st_mode),s.st_nlink,s.st_size,s.st_mtime_ns,getattr(s,'st_birthtime_ns',None))
        def same(s):return common(s)+(s.st_mode,s.st_ctime_ns)
        require(common(path)==common(before) and stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size==len(expected))
        os.lseek(fd,0,os.SEEK_SET);actual=os.read(fd,len(expected)+1);after=os.fstat(fd);final=_ordinary(p,True)
        require(actual==expected and same(before)==same(after) and same(path)==same(final))
    def close(self,fd):
        require(fd in self._fds);os.close(fd);del self._fds[fd]

class NativeUnitDenied(RuntimeError):
    def __init__(self,facts):self.facts=facts;super().__init__('PG_NATIVE_UNIT_DENIED')

def run_native_disposable(*,migration,readback,context_id,binding_sha256,admin_password,app_password,support_modules,job_source):
    """Explicit native-lease entry, NEVER called by inert tests or automatically.

    Root must externally hold/bound this process, admit its exact source/import
    closure and supply reviewed private credentials/source buffers. No lease is
    minted by this API; no binary/provenance fallback or alternate path exists.
    """
    from .pg_qualification import PgCustodian
    from .pg_protocol import render_protocol,run_protocol
    custodian=None;stage='RENDER';failure=None;cleanup_error=False;result=None
    try:
        protocol=render_protocol(migration=migration,readback=readback,context_id=context_id,binding_sha256=binding_sha256,admin_password=admin_password,app_password=app_password)
        plan=Plan('C:/Users/LS-5/AppData/Local/UnifiedCollectorTest/pg-attempt2',native=True,sql_pins=protocol.sql_pins())
        stage='NATIVE_BINDING';backend=WindowsBackend(plan,support_modules,job_source)
        stage='ROOT_ADMISSION';custodian=PgCustodian(plan,backend)
        stage='PRIVATE_STAGING';writer=PrivateWriter(custodian,protocol)
        stage='PROTOCOL';result=run_protocol(custodian,protocol,writer)
        require(writer._sealed is True and writer._failed is False);stage='COMPLETE'
    except BaseException as error:failure={'stage':stage,'error_type':type(error).__name__[:64]}
    finally:
        if custodian is not None:
            try:custodian.close()
            except BaseException:cleanup_error=True
    if failure is not None or cleanup_error:
        custody=None
        if custodian is not None:
            try:custody=custodian.snapshot()
            except BaseException:cleanup_error=True
        raise NativeUnitDenied({'status':'DENIED_OR_UNKNOWN','primary':failure,'cleanup_error':cleanup_error,'custody':custody,'native_authority':False}) from None
    return result
