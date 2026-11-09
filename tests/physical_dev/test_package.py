"""Pure owned fixture integrity; never native or physical admission evidence."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools.physical_dev import package


def metadata():
    return dict(description="Synthetic local package",sources=[dict(name="unified",repository="YehorBabenko88/unified-system",commit="a"*40,tree="b"*40)],dependencies=[dict(name="python",version="3.12.10")])


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()/"package";self.root.mkdir()
        (self.root/"source.py").write_bytes(b"inert\n")
        (self.root/".hidden").write_bytes(b"hidden")

    def manifest(self):
        raw=package.manifest_bytes(package.snapshot_files(self.root),metadata())
        return raw,hashlib.sha256(raw).hexdigest()

    def test_snapshot_includes_hidden_nested_and_empty_files(self):
        (self.root/"nested").mkdir();(self.root/"nested/empty").write_bytes(b"")
        files=package.snapshot_files(self.root)
        self.assertEqual(set(files),{"source.py",".hidden","nested/empty"})
        self.assertEqual(files["source.py"],dict(bytes=6,sha256=hashlib.sha256(b"inert\n").hexdigest()))
        self.assertEqual(files["nested/empty"]["bytes"],0)

    def test_snapshot_rejects_invalid_and_exhausted_limits(self):
        for limits in (dict(max_files=True),dict(max_files=0),dict(max_files=20001),dict(max_bytes=True),dict(max_bytes=-1),dict(max_bytes=1073741825),dict(max_files=1),dict(max_bytes=5)):
            with self.subTest(limits=limits),self.assertRaises(package.PackageError): package.snapshot_files(self.root,**limits)

    def test_relative_noncanonical_and_file_roots_refused(self):
        (self.root/"walk").mkdir()
        for root in (Path("relative"),self.root/"walk"/"..",self.root/"source.py"):
            with self.subTest(root=root),self.assertRaises(package.PackageError):package.snapshot_files(root)

    def test_hardlinks_rejected(self):
        os.link(self.root/"source.py",self.root/"alias")
        with self.assertRaises(package.PackageError): package.snapshot_files(self.root)

    def test_casefold_alias_in_manifest_rejected_portably(self):
        files=package.snapshot_files(self.root);files["SOURCE.py"]=files["source.py"]
        with self.assertRaises(package.PackageError):package.manifest_bytes(files,metadata())

    def test_unsafe_relative_manifest_paths_rejected(self):
        item=dict(bytes=0,sha256=hashlib.sha256(b"").hexdigest())
        for name in ("../escape","/absolute","C:/drive",r"back\slash","nul\0name","a//b","a/./b","a/../b","name.","name ","NUL.txt","NUL .txt","file:stream","bad\nname","bad\ud800name"):
            with self.subTest(name=name),self.assertRaises(package.PackageError):package.manifest_bytes({name:item},metadata())

    def test_manifest_is_canonical_and_never_authority(self):
        raw,pin=self.manifest();value=json.loads(raw)
        self.assertFalse(raw.endswith(b"\n"));self.assertEqual(raw,json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii"))
        result=package.verify_package(self.root,raw,pin)
        self.assertEqual(result["status"],"VERIFIED_FILE_BYTES_ONLY")
        self.assertEqual(result["source_provenance"],"DESCRIPTIVE_NOT_VERIFIED")
        self.assertEqual(result["public_submit"],"DENY")
        self.assertIs(result["runtime_admission"],False);self.assertIs(result["physical_execution_authorization"],False)
        self.assertEqual(result["file_count"],2)

    def test_external_pin_required_and_canonical(self):
        raw,pin=self.manifest()
        for value in (None,"",pin+"\n",pin.upper(),"0"*64):
            with self.subTest(pin=value),self.assertRaises(package.PackageError):package.verify_package(self.root,raw,value)

    def test_changed_extra_and_missing_files_rejected(self):
        raw,pin=self.manifest();source=self.root/"source.py"
        source.write_bytes(b"drift\n")
        with self.assertRaises(package.PackageError):package.verify_package(self.root,raw,pin)
        source.write_bytes(b"inert\n");extra=self.root/".extra";extra.write_bytes(b"extra")
        with self.assertRaises(package.PackageError):package.verify_package(self.root,raw,pin)
        extra.unlink();source.unlink()
        with self.assertRaises(package.PackageError):package.verify_package(self.root,raw,pin)

    def test_noncanonical_duplicate_and_open_json_rejected(self):
        raw,_=self.manifest();value=json.loads(raw)
        variants=[raw+b"\n",json.dumps(value,indent=2).encode(),b'{"schema":"duplicate",'+raw[1:]]
        value["unknown"]=True;variants.append(json.dumps(value,sort_keys=True,separators=(",",":")).encode())
        for data in variants:
            with self.subTest(data=data[:40]),self.assertRaises(package.PackageError):package.verify_package(self.root,data,hashlib.sha256(data).hexdigest())

    def test_bool_sizes_and_open_member_fields_rejected(self):
        for entry in (dict(bytes=True,sha256="a"*64),dict(bytes=-1,sha256="a"*64),dict(bytes=1,sha256="a"*64+"\n"),dict(bytes=1,sha256="a"*64,extra=True)):
            with self.subTest(entry=entry),self.assertRaises(package.PackageError):package.manifest_bytes({"file":entry},metadata())

    def test_metadata_closed_and_descriptive_fields_only(self):
        for change in (dict(metadata(),verified=True),dict(metadata(),sources=[dict(name="unified",repository="owner/repo",commit="a"*40+"\n",tree="b"*40)]),dict(metadata(),dependencies=[dict(name="python",version="3.12",approved=True)])):
            with self.subTest(value=change),self.assertRaises(package.PackageError):package.manifest_bytes(package.snapshot_files(self.root),change)

    def test_claimed_runtime_or_physical_authorization_rejected(self):
        raw,_=self.manifest()
        for key,value in (("runtime_admission",True),("physical_execution_authorization",True),("public_submit","ALLOW"),("source_provenance","VERIFIED_GIT"),("file_count",True),("total_bytes",True)):
            changed=json.loads(raw);changed[key]=value;data=json.dumps(changed,sort_keys=True,separators=(",",":")).encode()
            with self.subTest(key=key),self.assertRaises(package.PackageError):package.verify_package(self.root,data,hashlib.sha256(data).hexdigest())

    def test_growth_during_actual_read_rejected(self):
        real_read=os.read;changed=False
        def mutate(fd,count):
            nonlocal changed
            data=real_read(fd,count)
            if not changed and os.fstat(fd).st_ino==(self.root/"source.py").stat().st_ino:
                changed=True
                with (self.root/"source.py").open("ab") as stream:stream.write(b"concurrent")
            return data
        with patch.object(package.os,"read",side_effect=mutate):
            with self.assertRaises(package.PackageError):package.snapshot_files(self.root)

    def test_oversized_manifest_refused_before_json_decode(self):
        raw=b" "*(8*1024*1024+1)
        with patch.object(package.json,"loads",side_effect=AssertionError("oversized parse")):
            with self.assertRaises(package.PackageError):package.verify_package(self.root,raw,hashlib.sha256(raw).hexdigest())

    def test_directory_case_alias_and_file_ancestor_rejected(self):
        item=dict(bytes=0,sha256=hashlib.sha256(b"").hexdigest())
        for files in ({"Folder/a":item,"folder/b":item},{"parent":item,"parent/child":item}):
            with self.subTest(files=files),self.assertRaises(package.PackageError):package.manifest_bytes(files,metadata())

    def test_same_size_mutation_during_hash_rejected(self):
        original_read=os.read;changed=False;source=self.root/"source.py"
        def mutate(fd,count):
            nonlocal changed
            result=original_read(fd,count)
            if not changed and os.fstat(fd).st_ino==source.stat().st_ino:
                changed=True;before=source.stat();source.write_bytes(b"other\n")
                os.utime(source,ns=(before.st_atime_ns,before.st_mtime_ns+1000000000))
            return result
        with patch.object(package.os,"read",side_effect=mutate):
            with self.assertRaises(package.PackageError):package.snapshot_files(self.root)

    def test_file_added_during_hash_is_not_omitted(self):
        original_read=os.read;changed=False
        def mutate(fd,count):
            nonlocal changed
            result=original_read(fd,count)
            if not changed:changed=True;(self.root/"new-hidden").write_bytes(b"extra")
            return result
        with patch.object(package.os,"read",side_effect=mutate):
            with self.assertRaises(package.PackageError):package.snapshot_files(self.root)

    def test_reparse_and_symlink_controls(self):
        target=self.root.parent/"target";target.mkdir();link=self.root/"link"
        try:link.symlink_to(target,target_is_directory=True)
        except OSError:
            # A Windows metadata control is not native reparse qualification.
            self.assertEqual(os.name,"nt")
            original=Path.lstat
            def reparse(path,*args,**kwargs):
                result=original(path,*args,**kwargs)
                if path==self.root:return SimpleNamespace(st_file_attributes=1024)
                return result
            with patch.object(Path,"lstat",reparse):
                with self.assertRaises(package.PackageError):package.snapshot_files(self.root)
        else:
            with self.assertRaises(package.PackageError):package.snapshot_files(self.root)

    def test_empty_directory_enumeration_is_bounded(self):
        for name in ("one","two","three"):(self.root/name).mkdir()
        with patch.object(package,"MAX_FILES",2):
            with self.assertRaises(package.PackageError):package.snapshot_files(self.root,max_files=2)

    def test_identity_replacement_after_inventory_refused(self):
        original_read=os.read;changed=False
        def replace(fd,count):
            nonlocal changed
            result=original_read(fd,count)
            if not changed:
                changed=True
                replacement=self.root/"replacement";replacement.write_bytes(b"inert\n")
                replacement.replace(self.root/"source.py")
            return result
        with patch.object(package.os,"read",side_effect=replace):
            with self.assertRaises(package.PackageError):package.snapshot_files(self.root)

    def test_manifest_table_and_metadata_capacities(self):
        item=dict(bytes=0,sha256=hashlib.sha256(b"").hexdigest())
        for files in ({str(n):item for n in range(20001)},{"large":dict(item,bytes=1073741824),"extra":dict(item,bytes=1)}):
            with self.subTest(count=len(files)),self.assertRaises(package.PackageError):package.manifest_bytes(files,metadata())
        for key,limit in (("sources",32),("dependencies",128)):
            value=metadata();value[key]=value[key]*(limit+1)
            with self.subTest(key=key),self.assertRaises(package.PackageError):package.manifest_bytes({},value)

    def test_ctime_is_checked_within_api_not_across_windows_stat_apis(self):
        if os.name!="nt":
            self.assertEqual(package.snapshot_files(self.root)["source.py"]["bytes"],6)
            return
        original=os.fstat
        def descriptor_ctime(fd):
            result=original(fd)
            # Explicit API-semantics control, not a native timestamp assertion.
            fields={name:getattr(result,name) for name in ("st_dev","st_ino","st_mode","st_nlink","st_size","st_mtime_ns","st_ctime_ns","st_file_attributes")}
            fields["st_ctime_ns"]+=1
            return SimpleNamespace(**fields)
        with patch.object(package.os,"fstat",side_effect=descriptor_ctime):
            self.assertEqual(package.snapshot_files(self.root)["source.py"]["bytes"],6)


if __name__=="__main__":unittest.main()
