import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

from unified_system.windows_wheels import parse_compiled_lock, validate_windows_wheels


class WindowsWheelTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.wheels=self.root/'wheels';self.wheels.mkdir();self.lock=self.root/'candidate.lock'
    def wheel(self,*,filename='demo-1.0-py3-none-any.whl',metadata=None,tags=('py3-none-any',),extras=()):
        path=self.wheels/filename
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
                z.writestr('demo/__init__.py','')
                z.writestr('demo-1.0.dist-info/METADATA',metadata or 'Metadata-Version: 2.1\nName: demo\nVersion: 1.0\n\nInert fixture\n')
                z.writestr('demo-1.0.dist-info/WHEEL','Wheel-Version: 1.0\nRoot-Is-Purelib: true\n'+''.join('Tag: '+t+'\n' for t in tags)+'\n')
                for name,data in extras:z.writestr(name,data)
        return path
    def pin(self,path):
        self.lock.write_text('# compiled candidate only\ndemo==1.0 \\\n    --hash=sha256:'+hashlib.sha256(path.read_bytes()).hexdigest()+'\n')
    def report(self):return validate_windows_wheels(self.lock,self.wheels)
    def blocked(self):self.assertEqual(self.report()['result'],'BLOCKED')
    def test_normal_candidate_matches_without_any_install_or_dependency_authority(self):
        p=self.wheel();self.pin(p);before={x:x.read_bytes() for x in (p,self.lock)}
        with patch('socket.socket',side_effect=AssertionError('network')),patch('subprocess.Popen',side_effect=AssertionError('exec')):
            report=self.report()
        self.assertEqual(report['result'],'CANDIDATE_BYTES_MATCH')
        for key in ('dependency_closure_verified','installation_closure','publisher_authenticated','execution_authority'):self.assertFalse(report[key])
        self.assertEqual(report['native_execution'],'NOT_RUN');self.assertEqual(before,{x:x.read_bytes() for x in before})
    def test_strict_compiled_lock_rejects_unpinned_options_urls_markers_and_duplicates(self):
        h=' --hash=sha256:'+'a'*64
        for raw in ('demo>=1'+h,'--index-url https://example.invalid','demo @ https://example.invalid/a.whl',
                    'demo==1.0','demo[extra]==1.0'+h,'demo==1.0; python_version>"3"'+h,
                    'demo==1.0'+h+'\ndemo==1.0'+h,'demo==1.0 --hash=md5:'+'a'*32,'demo==1.0'+h+' \\'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):parse_compiled_lock(raw.encode())
        self.assertIn('demo',parse_compiled_lock(('# comment\ndemo==1.0 \\\n  '+h.strip()+'\n # via dependency\n').encode()))
    def test_missing_unknown_duplicate_and_nonwheel_files_block(self):
        p=self.wheel();self.pin(p)
        p.unlink();self.blocked();p=self.wheel()
        extra=self.wheels/'unknown-1.0-py3-none-any.whl';extra.write_bytes(p.read_bytes());self.blocked();extra.unlink()
        extra=self.wheels/'demo-1.0-1-py3-none-any.whl';extra.write_bytes(p.read_bytes());self.blocked();extra.unlink()
        (self.wheels/'source.tar.gz').write_bytes(b'not a wheel');self.blocked()
    def test_wrong_hash_and_ambiguous_or_mismatched_metadata_block(self):
        p=self.wheel();self.pin(p);self.lock.write_text('demo==1.0 --hash=sha256:'+'0'*64);self.blocked()
        for metadata in ('Metadata-Version: 2.1\nName: demo\nName: other\nVersion: 1.0\n',
                         'Metadata-Version: 2.1\nName: demo\nVersion: 2.0\n'):
            p=self.wheel(metadata=metadata);self.pin(p);self.blocked()
        p=self.wheel(extras=[('other-1.0.dist-info/METADATA','Name: other\nVersion: 1.0')]);self.pin(p);self.blocked()
    def test_unsafe_zip_alias_and_duplicate_metadata_block(self):
        for name in ('../escape.py','x/../escape.py','C:/escape.py','pkg/NUL.txt','pkg/trailing.','demo-1.0.dist-info/METADATA'):
            with self.subTest(name=name):
                p=self.wheel(extras=[(name,'untrusted')]);self.pin(p);self.blocked()
        info=zipfile.ZipInfo('linked');info.create_system=3;info.external_attr=0o120777<<16
        p=self.wheel(extras=[(info,'target')]);self.pin(p);self.blocked()
    def test_tag_filename_agreement_and_actual_windows_compatibility(self):
        cases=[('py3-none-any',True),('cp312-cp312-win_amd64',True),('cp310-abi3-win_amd64',True),
               ('py3-none-win_amd64',True),('cp313-abi3-win_amd64',False),('cp311-cp311-win_amd64',False),
               ('cp312-cp312-manylinux_2_17_x86_64',False),('py3-none-win32',False)]
        for tag,accepted in cases:
            with self.subTest(tag=tag):
                for old in self.wheels.iterdir():old.unlink()
                p=self.wheel(filename='demo-1.0-'+tag+'.whl',tags=(tag,));self.pin(p)
                self.assertEqual(self.report()['result']=='CANDIDATE_BYTES_MATCH',accepted)
        for old in self.wheels.iterdir():old.unlink()
        p=self.wheel(tags=('cp312-cp312-win_amd64',));self.pin(p);self.blocked()
    def test_zip_metadata_uses_same_open_descriptor_as_streamed_hash(self):
        p=self.wheel();self.pin(p);real_open=os.open;real_zip=zipfile.ZipFile;opened=[];seen=[]
        def opening(path,*a,**kw):
            fd=real_open(path,*a,**kw)
            if Path(path)==p:opened.append(fd)
            return fd
        def archive(file,*a,**kw):
            self.assertFalse(isinstance(file,(str,Path)));seen.append(file.fileno());return real_zip(file,*a,**kw)
        with patch('unified_system.windows_wheels.os.open',side_effect=opening),patch('unified_system.windows_wheels.zipfile.ZipFile',side_effect=archive):
            self.assertEqual(self.report()['result'],'CANDIDATE_BYTES_MATCH')
        self.assertEqual(len(opened),1);self.assertEqual(seen,opened)
    def test_external_paths_and_multiply_linked_wheels_block(self):
        with patch('pathlib.Path.lstat',side_effect=AssertionError('metadata before namespace check')):
            self.assertEqual(validate_windows_wheels('//office.invalid/lock','//office.invalid/wheels')['result'],'BLOCKED')
        p=self.wheel();self.pin(p);os.link(p,self.root/'linked.whl');self.blocked()


    def test_replaced_path_after_hash_cannot_borrow_other_file_metadata(self):
        p=self.wheel();self.pin(p);original_zip=zipfile.ZipFile
        def swapping(file,*args,**kwargs):
            p.rename(self.root/'original.whl');p.write_bytes(b'replacement')
            return original_zip(file,*args,**kwargs)
        with patch('unified_system.windows_wheels.zipfile.ZipFile',side_effect=swapping):self.blocked()

    def test_central_directory_and_metadata_bounds_fail_before_large_parsing(self):
        import struct
        p=self.wheel();data=bytearray(p.read_bytes());offset=data.rfind(b'PK\x05\x06')
        struct.pack_into('<HH',data,offset+8,65535,65535);p.write_bytes(data);self.pin(p)
        with patch('unified_system.windows_wheels.zipfile.ZipFile',side_effect=AssertionError('unbounded ZIP parse')):self.blocked()
        metadata='Metadata-Version: 2.1\nName: demo\nVersion: 1.0\n\n'+'x'*(1024*1024)
        p=self.wheel(metadata=metadata);self.pin(p);self.blocked()


    def test_vendored_metadata_is_data_not_an_alternate_wheel_identity(self):
        p=self.wheel(extras=[
            ('demo/_vendor/dependency-2.0.dist-info/METADATA','Metadata-Version: 2.1\nName: dependency\nVersion: 2.0\n'),
            ('demo/_vendor/dependency-2.0.dist-info/WHEEL','not an authoritative wheel header'),
        ]);self.pin(p)
        self.assertEqual(self.report()['result'],'CANDIDATE_BYTES_MATCH')
        p=self.wheel(extras=[('dependency-2.0.dist-info/METADATA','Metadata-Version: 2.1\nName: dependency\nVersion: 2.0\n')]);self.pin(p)
        self.blocked()

        for scheme in ('purelib','platlib'):
            p=self.wheel(extras=[('demo-1.0.data/'+scheme+'/dependency-2.0.dist-info/METADATA','Name: dependency\nVersion: 2.0\n')]);self.pin(p)
            self.blocked()
