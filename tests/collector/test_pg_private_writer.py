"""Inert controls for actual private writer, no native/PG/real-secret fixture."""
import unittest
from types import SimpleNamespace
from tools.collector import pg_private_writer as w
from tools.collector import pg_protocol as p

def packet():
    return p.Protocol(tuple((n,('SELECT '+n+';\n').encode()) for n in ('bootstrap','migrate','verify','readback')),(('secrets/bootstrap-password',b'INERT_ADMIN\n',True),('secrets/pgpass.conf',b'INERT_PASSFILE\n',True)),'a'*32,'b'*64)
class IO:
    def __init__(self):self.data={};self.opened={};self.identity=(1,2);self.context=('INERT',);self.fault=None;self.events=[];self.bad=None
    def snapshot(self):
        rows=[dict(name=n,kind='directory',nlink=1,reparse=False,private=True) for n in w.DIRECTORIES]
        rows += [dict(name=n,kind='file',nlink=1,reparse=False,private=True,bytes=len(raw),sha256=w.digest(raw)) for n,raw in self.data.items()]
        if self.bad:
            field,value=self.bad;rows[0][field]=value
        return dict(identity=self.identity,context=self.context,rows=rows)
    def create(self,name):
        if name in self.data:raise FileExistsError()
        self.data[name]=b'';self.opened[name]=name;self.events.append('create');return name
    def write(self,fd,raw):
        self.events.append('write')
        if self.fault=='write':self.data[fd]=raw[:1];raise OSError('INERT')
        self.data[fd]=raw
    def flush(self,fd):
        self.events.append('flush')
        if self.fault=='flush':raise OSError('INERT')
    def check(self,fd,raw):
        self.events.append('check')
        if self.data[fd]!=raw or self.fault=='check':raise ValueError('INERT')
    def close(self,fd):
        self.events.append('close')
        if self.fault=='close':raise OSError('INERT')
        del self.opened[fd]
class PrivateWriterTests(unittest.TestCase):
    def test_native_io_uses_exact_shared_attempt2_root_gate_before_io(self):
        from pathlib import Path
        from tools.collector import pg_qualification as q
        profile=Path('C:/Users/INERT');plan=object();backend=SimpleNamespace(plan=plan,root=profile/'AppData/Local/UnifiedCollectorTest/pg-attempt2',context_identity=('INERT',profile))
        c=SimpleNamespace(backend=backend,plan=plan)
        self.assertEqual(w._NativeIO(c).root,backend.root)
        backend.root=backend.root.parent/'pg-attempt1'
        with self.assertRaises(ValueError):w._NativeIO(c)
    def setup_writer(self):
        v=packet();io=IO();c=SimpleNamespace(plan=SimpleNamespace(native=False,sql_pins=v.sql_pins()),backend=None);return v,io,w.PrivateWriter(c,v,io=io)
    def stage(self,v,writer):
        for row in v.private_files():writer(*row)
    def test_six_exact_files_seal_and_redact_secret_hashes(self):
        v,io,writer=self.setup_writer();self.stage(v,writer);r=writer.finish();self.assertTrue(r['sealed']);self.assertEqual(len(io.data),6)
        for name,raw,secret in v.private_files():
            if secret:self.assertNotIn(w.digest(raw),str(r));self.assertNotIn(raw.decode().strip(),repr(writer))
    def test_unknown_name_denied_before_create(self):
        v,io,writer=self.setup_writer()
        with self.assertRaises(ValueError):writer('../escape',b'x',True)
        self.assertEqual(io.events,[])
    def test_wrong_bytes_denied_before_create(self):
        v,io,writer=self.setup_writer();n,r,s=v.private_files()[0]
        with self.assertRaises(ValueError):writer(n,r+b'x',s)
        self.assertEqual(io.events,[])
    def test_privacy_flag_mismatch_denied(self):
        v,io,writer=self.setup_writer();n,r,s=v.private_files()[0]
        with self.assertRaises(ValueError):writer(n,r,not s)
        self.assertEqual(io.events,[])
    def test_nonbytes_denied(self):
        v,io,writer=self.setup_writer();n,r,s=v.private_files()[0]
        with self.assertRaises(ValueError):writer(n,r.decode(),s)
    def test_duplicate_never_overwrites(self):
        v,io,writer=self.setup_writer();row=v.private_files()[0];writer(*row)
        with self.assertRaises(ValueError):writer(*row)
        self.assertEqual(io.events.count('create'),1)
    def test_unknown_existing_file_denies(self):
        v,io,writer=self.setup_writer();io.data['sql/foreign.sql']=b'x'
        with self.assertRaises(ValueError):writer(*v.private_files()[0])
        self.assertNotIn('create',io.events)
    def test_reparse_denies(self):
        v,io,writer=self.setup_writer();io.bad=('reparse',True)
        with self.assertRaises(ValueError):writer(*v.private_files()[0])
    def test_multilink_denies(self):
        v,io,writer=self.setup_writer();row=v.private_files()[0];writer(*row)
        original=io.snapshot
        def snapshot():
            r=original();r['rows'][-1]['nlink']=2;return r
        io.snapshot=snapshot
        with self.assertRaises(ValueError):writer(*v.private_files()[1])
    def test_nonprivate_acl_fact_denies(self):
        v,io,writer=self.setup_writer();io.bad=('private',False)
        with self.assertRaises(ValueError):writer(*v.private_files()[0])
    def test_root_identity_change_denies(self):
        v,io,writer=self.setup_writer();io.identity=(1,3)
        with self.assertRaises(ValueError):writer(*v.private_files()[0])
    def test_context_change_denies(self):
        v,io,writer=self.setup_writer();io.context=('OTHER',)
        with self.assertRaises(ValueError):writer(*v.private_files()[0])
    def test_partial_write_sticky_and_close_attempted(self):
        v,io,writer=self.setup_writer();io.fault='write'
        with self.assertRaises(ValueError):writer(*v.private_files()[0])
        self.assertIn('close',io.events);self.assertEqual(len(io.data),1)
        with self.assertRaises(ValueError):writer(*v.private_files()[1])
        self.assertEqual(io.events.count('create'),1)
    def test_flush_failure_sticky(self):
        v,io,writer=self.setup_writer();io.fault='flush'
        with self.assertRaises(ValueError):writer(*v.private_files()[0])
        self.assertIn('close',io.events)
    def test_close_uncertainty_not_sealed(self):
        v,io,writer=self.setup_writer();io.fault='close'
        with self.assertRaises(ValueError):writer(*v.private_files()[0])
        with self.assertRaises(ValueError):writer.finish()
        self.assertEqual(io.events.count('close'),1)
    def test_incomplete_finish_denies_and_latches(self):
        v,io,writer=self.setup_writer()
        with self.assertRaises(ValueError):writer.finish()
        with self.assertRaises(ValueError):writer(*v.private_files()[0])
    def test_native_plan_rejects_injected_io_before_actions(self):
        v=packet();io=IO();c=SimpleNamespace(plan=SimpleNamespace(native=True,sql_pins=v.sql_pins()),backend=None)
        with self.assertRaises(ValueError):w.PrivateWriter(c,v,io=io)
        self.assertEqual(io.events,[])
