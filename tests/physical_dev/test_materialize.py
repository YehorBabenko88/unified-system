"""Materializer tests copy only owned inert temporary fixture bytes."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.physical_dev import assembly, materialize
from tools.physical_dev import package as integrity


def assert_owned_close_failure(testcase,copy_call,*,write_failure=False):
    """Inject on owned inert descriptors and close any retained test FDs safely."""
    real_open=os.open;real_close=os.close;opened=[];attempts=[];pending=set()
    close_error=OSError("inert target close failure");write_error=OSError("inert prior write failure")
    def open_owned(*args,**kwargs):
        descriptor=real_open(*args,**kwargs);opened.append(descriptor);pending.add(descriptor);return descriptor
    def close_owned(descriptor):
        attempts.append(descriptor)
        if len(opened)==2 and descriptor==opened[1]:raise close_error
        real_close(descriptor);pending.discard(descriptor)
    captured=None
    try:
        with patch.object(materialize.os,"open",side_effect=open_owned),patch.object(materialize.os,"close",side_effect=close_owned):
            try:
                if write_failure:
                    with patch.object(materialize.os,"write",side_effect=write_error):copy_call()
                else:copy_call()
            except OSError as exc:captured=exc
    finally:
        # The injected close never closes its target. This test's own fallback
        # closes only the still-pending owned descriptors, with no fd retry loop.
        for descriptor in pending:real_close(descriptor)
    testcase.assertEqual(len(opened),2)
    testcase.assertEqual(attempts,[opened[1],opened[0]])
    testcase.assertIs(captured,write_error if write_failure else close_error)
    testcase.assertTrue(any("OWNED_FD_CLOSE_FAILED" in note for note in getattr(captured,"__notes__",[])))


class MaterializeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.source=self.root/"source";self.source.mkdir()
        (self.source/"inert.bin").write_bytes(b"inert fixture bytes\0\xff")
        (self.source/".hidden").write_bytes(b"hidden")
        self.parent=self.root/"owned-evidence";self.parent.mkdir()
        self.destination=self.parent/"ls5-package-fixture"
        control=patch.object(materialize,"FIXED_EVIDENCE_PARENT",self.parent);control.start();self.addCleanup(control.stop)
        self.plan=assembly.plan_assembly([dict(name="fixture",source_root=str(self.source),destination_prefix="source",profile="closed-tree")],self.destination)
        self.raw=integrity._canonical(self.plan);self.pin=hashlib.sha256(self.raw).hexdigest()

    def call(self,raw=None,pin=None):return materialize.materialize(self.raw if raw is None else raw,self.pin if pin is None else pin)

    def test_normal_exact_bytes_and_no_runtime_authority(self):
        result=self.call()
        self.assertEqual((self.destination/"source/inert.bin").read_bytes(),(self.source/"inert.bin").read_bytes())
        self.assertEqual((self.destination/"source/.hidden").read_bytes(),b"hidden")
        self.assertEqual(result["status"],"COPIED_BYTES_ONLY")
        self.assertEqual(result["plan_sha256"],self.pin)
        self.assertEqual(result["selected_file_count"],2)
        self.assertEqual(result["public_submit"],"DENY")
        self.assertIs(result["runtime_admission"],False);self.assertIs(result["physical_execution_authorization"],False)

    def test_wrong_pin_noncanonical_duplicate_or_open_plan_fail_before_destination(self):
        variants=[(self.raw,"0"*64),(self.raw+b"\n",None),(b'{"schema":"duplicate",'+self.raw[1:],None)]
        changed=dict(self.plan,unknown=True);variants.append((integrity._canonical(changed),None))
        for raw,pin in variants:
            with self.subTest(raw=raw[:20]),self.assertRaises(materialize.MaterializeError):self.call(raw,pin or hashlib.sha256(raw).hexdigest())
            self.assertFalse(self.destination.exists())

    def test_changed_source_fails_before_destination(self):
        (self.source/"inert.bin").write_bytes(b"changed")
        with self.assertRaises(materialize.MaterializeError):self.call()
        self.assertFalse(self.destination.exists())

    def test_existing_destination_is_never_adopted_or_overwritten(self):
        self.destination.mkdir();foreign=self.destination/"foreign";foreign.write_bytes(b"preserve")
        with self.assertRaises(materialize.MaterializeError):self.call()
        self.assertEqual(foreign.read_bytes(),b"preserve")
        self.assertEqual(list(self.destination.iterdir()),[foreign])

    def test_outside_fixed_parent_or_wrong_name_fails_before_destination(self):
        for destination in (self.root/"ls5-package-outside",self.parent/"other-name",self.parent/"nested/ls5-package-nested"):
            # Plan generation itself requires existing destination parents.
            if destination.parent!=self.root and not destination.parent.exists():destination.parent.mkdir()
            plan=dict(self.plan,destination=str(destination));raw=integrity._canonical(plan)
            with self.subTest(destination=destination),self.assertRaises(materialize.MaterializeError):self.call(raw,hashlib.sha256(raw).hexdigest())
            self.assertFalse(destination.exists())

    def test_rehashed_file_path_injection_or_bool_limit_is_not_a_grant(self):
        for field,value in (("files",{"../escape":next(iter(self.plan["files"].values()))}),("limits",dict(self.plan["limits"],max_files=True)),("runtime_admission",True)):
            changed=dict(self.plan);changed[field]=value;raw=integrity._canonical(changed)
            with self.subTest(field=field),self.assertRaises(materialize.MaterializeError):self.call(raw,hashlib.sha256(raw).hexdigest())
            self.assertFalse(self.destination.exists())

    def test_hardlinked_source_refused_before_destination(self):
        os.link(self.source/"inert.bin",self.source/"alias")
        with self.assertRaises(materialize.MaterializeError):self.call()
        self.assertFalse(self.destination.exists())

    def test_write_failure_retains_partial_directory_and_file(self):
        with patch.object(materialize.os,"write",side_effect=OSError("owned fixture full disk")):
            with self.assertRaises(materialize.MaterializeError):self.call()
        self.assertTrue(self.destination.is_dir())
        self.assertTrue(any(path.is_file() for path in self.destination.rglob("*")))

    def test_source_mutation_during_copy_preserves_partial_evidence(self):
        original=os.read;changed=False
        def mutate(fd,count):
            nonlocal changed
            data=original(fd,count)
            if not changed and self.destination.exists() and os.fstat(fd).st_ino==(self.source/"inert.bin").stat().st_ino:
                changed=True
                with (self.source/"inert.bin").open("ab") as stream:stream.write(b"changed")
            return data
        with patch.object(materialize.os,"read",side_effect=mutate):
            with self.assertRaises(materialize.MaterializeError):self.call()
        self.assertTrue(changed);self.assertTrue(self.destination.exists())

    def test_source_and_destination_file_caps_remain_fixed(self):
        changed=dict(self.plan,limits=dict(self.plan["limits"],max_bytes=1073741825));raw=integrity._canonical(changed)
        with self.assertRaises(materialize.MaterializeError):self.call(raw,hashlib.sha256(raw).hexdigest())
        self.assertFalse(self.destination.exists())

    def test_late_target_file_is_never_overwritten(self):
        original=os.open;injected=[]
        def late_file(path,flags,*args,**kwargs):
            if flags&os.O_EXCL and self.destination in Path(path).parents and not injected:
                Path(path).write_bytes(b"foreign late bytes");injected.append(Path(path))
            return original(path,flags,*args,**kwargs)
        with patch.object(materialize.os,"open",side_effect=late_file):
            with self.assertRaises(materialize.MaterializeError):self.call()
        self.assertEqual(len(injected),1)
        self.assertEqual(injected[0].read_bytes(),b"foreign late bytes")

    def test_partial_writes_are_completed_and_reads_are_bounded(self):
        original_write=os.write;original_read=os.read;reads=[]
        def short_write(fd,chunk):return original_write(fd,chunk[:max(1,len(chunk)//2)])
        def bounded_read(fd,count):reads.append(count);return original_read(fd,count)
        with patch.object(materialize.os,"write",side_effect=short_write),patch.object(materialize.os,"read",side_effect=bounded_read):
            self.call()
        self.assertTrue(reads);self.assertLessEqual(max(reads),65536)
        self.assertEqual((self.destination/"source/inert.bin").read_bytes(),(self.source/"inert.bin").read_bytes())

    def test_zero_write_refuses_without_retry_or_deletion(self):
        with patch.object(materialize.os,"write",return_value=0) as writer:
            with self.assertRaises(materialize.MaterializeError):self.call()
        self.assertEqual(writer.call_count,1);self.assertTrue(self.destination.exists())

    def test_zero_byte_member_is_created_exclusively(self):
        (self.source/"empty").write_bytes(b"")
        self.plan=assembly.plan_assembly(self.plan["components"],self.destination)
        self.raw=integrity._canonical(self.plan);self.pin=hashlib.sha256(self.raw).hexdigest()
        self.call()
        self.assertEqual((self.destination/"source/empty").read_bytes(),b"")

    def test_oversized_plan_refuses_before_json_parser(self):
        with patch.object(materialize.assembly,"MAX_PLAN_BYTES",1),patch.object(materialize.json,"loads",side_effect=AssertionError("oversized parse")):
            with self.assertRaises(materialize.MaterializeError):self.call()
        self.assertFalse(self.destination.exists())

    def test_target_close_failure_still_attempts_source_close_and_cannot_pass(self):
        source=self.source/"inert.bin";target=self.root/"target-close.bin"
        record=dict(bytes=source.stat().st_size,sha256=hashlib.sha256(source.read_bytes()).hexdigest())
        assert_owned_close_failure(self,lambda:materialize._copy_file(source,target,record))
        self.assertTrue(target.exists())

    def test_prior_write_failure_survives_target_close_failure_with_note(self):
        source=self.source/"inert.bin";target=self.root/"write-close.bin"
        record=dict(bytes=source.stat().st_size,sha256=hashlib.sha256(source.read_bytes()).hexdigest())
        assert_owned_close_failure(self,lambda:materialize._copy_file(source,target,record),write_failure=True)
        self.assertTrue(target.exists())

    def test_caller_handled_exception_cannot_hide_new_close_failure(self):
        source=self.source/"inert.bin";target=self.root/"caller-except.bin"
        record=dict(bytes=source.stat().st_size,sha256=hashlib.sha256(source.read_bytes()).hexdigest())
        try:raise LookupError("inert caller handled error")
        except LookupError:
            assert_owned_close_failure(self,lambda:materialize._copy_file(source,target,record))


if __name__=="__main__":unittest.main()
