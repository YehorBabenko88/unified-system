"""Privilege reduction probes always run in fresh child processes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


@unittest.skipUnless(os.name=='nt','Windows primary token API')
class LabPrivilegeTests(unittest.TestCase):
    def test_child_removal_is_idempotent_and_parent_is_unchanged(self):
        from unified_system.lab_privileges import current_privilege_state
        before=current_privilege_state()
        child='''import json,sys
sys.path.insert(0,sys.argv[1])
from unified_system.lab_privileges import current_privilege_state,remove_lab_write_bypass_privileges
before=current_privilege_state()
first=remove_lab_write_bypass_privileges()
second=remove_lab_write_bypass_privileges()
print(json.dumps(dict(before=before,after=current_privilege_state(),first=first,second=second)))
'''
        result=subprocess.run([sys.executable,'-I','-S','-B','-c',child,str(Path(__file__).resolve().parents[1])],
                              capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads(result.stdout)
        self.assertEqual(set(report['after'].values()),{'ABSENT'})
        self.assertEqual(report['first'],'LAB_WRITE_BYPASS_PRIVILEGES_ABSENT')
        self.assertEqual(report['second'],report['first'])
        self.assertEqual(current_privilege_state(),before)


class LabPrivilegeEntrypointTests(unittest.TestCase):
    def test_failure_blocks_before_capsule_preparation(self):
        from unittest.mock import patch
        from unified_system import lab_runtime
        with (patch('unified_system.lab_privileges.remove_lab_write_bypass_privileges',side_effect=ValueError('LAB_PRIVILEGE_REMOVAL_FAILED')),
              patch.object(lab_runtime,'prepare') as prepare):
            self.assertEqual(lab_runtime.main(['--mode','LAB_SIMULATION','--root',str(Path.cwd()),'--manifest-sha256','a'*64,'--execute']),1)
            prepare.assert_not_called()

    def test_unsupported_platform_fails_closed(self):
        from unittest.mock import patch
        from unified_system import lab_privileges
        with patch.object(lab_privileges.os,'name','posix'):
            with self.assertRaisesRegex(ValueError,'LAB_PRIVILEGE_WINDOWS_REQUIRED'):
                lab_privileges.remove_lab_write_bypass_privileges()

    @unittest.skipUnless(os.name=='nt','Windows token API bindings')
    def test_thread_token_is_rejected_without_adjusting_process_token(self):
        from unittest.mock import Mock,patch
        from unified_system import lab_privileges
        c,w,k,a,LUID,ENTRY=lab_privileges._api()
        fake=Mock();fake.OpenThreadToken.return_value=True
        kernel=Mock()
        with patch.object(lab_privileges,'_api',return_value=(c,w,kernel,fake,LUID,ENTRY)):
            with self.assertRaisesRegex(ValueError,'LAB_PRIVILEGE_THREAD_TOKEN_REJECTED'):
                lab_privileges.remove_lab_write_bypass_privileges()
        fake.OpenProcessToken.assert_not_called();fake.AdjustTokenPrivileges.assert_not_called()
        kernel.CloseHandle.assert_called_once()

    @unittest.skipUnless(os.name=='nt','Windows token API bindings')
    def test_token_information_rejects_oversize_count_and_truncated_records(self):
        import struct
        from unittest.mock import Mock
        from unified_system import lab_privileges
        c,w,k,a,LUID,ENTRY=lab_privileges._api()
        for length,count in ((65537,0),(4,257),(4,1)):
            fake=Mock()
            def query(token,kind,buffer,capacity,returned):
                self.assertEqual(capacity,65536)
                c.memmove(buffer,struct.pack('<I',count),4);returned._obj.value=length
                return True
            fake.GetTokenInformation.side_effect=query
            with self.assertRaisesRegex(ValueError,'LAB_PRIVILEGE_QUERY_BOUNDS'):
                lab_privileges._snapshot(c,w,fake,None,ENTRY)

    def test_execute_reduces_before_prepare_but_verification_and_trusted_do_not(self):
        from unittest.mock import patch
        from unified_system import lab_runtime
        events=[]
        def reject_prepare(*args):events.append('prepare');raise ValueError('inert')
        with (patch('unified_system.lab_privileges.remove_lab_write_bypass_privileges',side_effect=lambda:events.append('reduce')),
              patch.object(lab_runtime,'prepare',side_effect=reject_prepare)):
            lab_runtime.main(['--mode','LAB_SIMULATION','--root',str(Path.cwd()),'--manifest-sha256','a'*64,'--execute'])
            self.assertEqual(events,['reduce','prepare']);events.clear()
            lab_runtime.main(['--mode','LAB_SIMULATION','--root',str(Path.cwd()),'--manifest-sha256','a'*64])
            self.assertEqual(events,['prepare']);events.clear()
            lab_runtime.main(['--mode','TRUSTED_RELEASE','--root',str(Path.cwd()),'--manifest-sha256','a'*64,'--execute'])
            self.assertEqual(events,[])
