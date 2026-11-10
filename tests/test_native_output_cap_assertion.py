"""SOURCE PREPARATION: explicit pure-PowerShell classifier controls, never fixtures.

No TestCase exists at import/discovery time. Root must separately allocate the
explicit __main__ suite below. No skip, workflow filter or old inventory changes.
The shared .ps1 helper is deliberately absent until controlled missing-helper RED.
"""
import base64
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'tests/native_output_cap_assertion.ps1'
POWERSHELL = Path('C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe')
CASE_IDS = (
    'accept_leaf', 'accept_aggregate_single', 'accept_aggregate_all_cap',
    'accept_method_aggregate', 'accept_target_method_aggregate',
    'accept_max_depth', 'accept_max_nodes', 'reject_null',
    'reject_truthy_nonexception', 'reject_deadline', 'reject_drain_deadline',
    'reject_launch_failure', 'reject_unrelated', 'reject_wrong_case',
    'reject_cap_prefix', 'reject_unknown_wrapper', 'reject_nonleaf_cap',
    'reject_empty_aggregate', 'reject_mixed_aggregate', 'reject_nested_mixed',
    'reject_cycle', 'reject_depth', 'reject_nodes', 'reject_oversized_message',
)
ACCEPT_IDS = frozenset(CASE_IDS[:7])

# Stock managed exceptions only. Reflection rewires ONE owned exception's private
# inner link solely to supply a genuine cycle; it calls no native/project API.
# No Add-Type, C# compiler, subprocess, service, ACL, registry or socket fixture.
PS_MATRIX = r"""
$ErrorActionPreference='Stop'
try {
  $load=@(. $env:UNIFIED_OUTPUT_CAP_HELPER)
  if($load.Count -ne 0){throw 'HELPER_LOAD_OUTPUT'}
  function Cap { return [InvalidOperationException]::new('CHILD_OUTPUT_LIMIT') }
  function Agg([Exception[]]$items) { return [AggregateException]::new('unit aggregate',$items) }
  function Wrap([Exception]$inner) { return [Reflection.TargetInvocationException]::new('unit wrapper',$inner) }
  $single=Agg @((Cap))
  $method=[Management.Automation.MethodInvocationException]::new('unit method',$single)
  $depth8=Cap;for($i=0;$i -lt 7;$i++){$depth8=Wrap $depth8}
  $depth9=Wrap $depth8
  $fifteen=[Exception[]]@();for($i=0;$i -lt 15;$i++){$fifteen+=,(Cap)}
  $sixteen=[Exception[]]@();for($i=0;$i -lt 16;$i++){$sixteen+=,(Cap)}
  $cycle=Wrap (Cap)
  $field=[Exception].GetField('_innerException',[Reflection.BindingFlags]'Instance,NonPublic')
  if($null -eq $field){throw 'CYCLE_SEAM_UNAVAILABLE'}
  $field.SetValue($cycle,$cycle)
  $cases=@(
    @{id='accept_leaf';value=(Cap)},
    @{id='accept_aggregate_single';value=$single},
    @{id='accept_aggregate_all_cap';value=(Agg @((Cap),(Cap)))},
    @{id='accept_method_aggregate';value=$method},
    @{id='accept_target_method_aggregate';value=(Wrap $method)},
    @{id='accept_max_depth';value=$depth8},
    @{id='accept_max_nodes';value=(Agg $fifteen)},
    @{id='reject_null';value=$null},
    @{id='reject_truthy_nonexception';value=[pscustomobject]@{Message='CHILD_OUTPUT_LIMIT';InnerException=$null}},
    @{id='reject_deadline';value=[InvalidOperationException]::new('CHILD_DEADLINE')},
    @{id='reject_drain_deadline';value=[InvalidOperationException]::new('CHILD_DRAIN_DEADLINE')},
    @{id='reject_launch_failure';value=[ComponentModel.Win32Exception]::new(2)},
    @{id='reject_unrelated';value=[InvalidOperationException]::new('UNRELATED')},
    @{id='reject_wrong_case';value=[InvalidOperationException]::new('child_output_limit')},
    @{id='reject_cap_prefix';value=[InvalidOperationException]::new('CHILD_OUTPUT_LIMIT_PRIVATE')},
    @{id='reject_unknown_wrapper';value=[Exception]::new('unit unknown',(Cap))},
    @{id='reject_nonleaf_cap';value=[InvalidOperationException]::new('CHILD_OUTPUT_LIMIT',(Cap))},
    @{id='reject_empty_aggregate';value=[AggregateException]::new()},
    @{id='reject_mixed_aggregate';value=(Agg @((Cap),[InvalidOperationException]::new('CHILD_DEADLINE')))},
    @{id='reject_nested_mixed';value=(Wrap (Agg @((Cap),[Exception]::new('UNRELATED'))))},
    @{id='reject_cycle';value=$cycle},
    @{id='reject_depth';value=$depth9},
    @{id='reject_nodes';value=(Agg $sixteen)},
    @{id='reject_oversized_message';value=[Reflection.TargetInvocationException]::new(('x'*1025),(Cap))}
  )
  [Console]::Out.WriteLine('UNIT_CAP_V1')
  foreach($case in $cases){
    # Calls the actual shared classifier, not a Python mirror or copied algorithm.
    $answer=@(Test-NativeOutputCapException -ExceptionObject $case.value)
    $status='NOT_BOOL'
    if($answer.Count -eq 1 -and $answer[0] -is [bool]){
      if($answer[0]){$status='TRUE'}else{$status='FALSE'}
    }
    [Console]::Out.WriteLine($case.id+'|'+$status)
  }
} catch {
  [Console]::Error.WriteLine('UNIT_CAP_SETUP_OR_CLASSIFIER_ERROR')
  exit 2
}
"""


def _ordinary_tool():
    """OS tool leaves may have servicing links; no alias/ancestor redirection."""
    for path in reversed(POWERSHELL.parents):
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 1024:
            raise AssertionError('PURE_PS_TOOL_PARENT_UNSAFE')
    info = POWERSHELL.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink < 1 or getattr(info, 'st_file_attributes', 0) & 1024 or not 0 < info.st_size <= 64 * 1024 * 1024:
        raise AssertionError('PURE_PS_TOOL_UNSAFE')
    return hashlib.sha256(POWERSHELL.read_bytes()).hexdigest()


def _run_matrix():
    if os.name != 'nt':
        raise AssertionError('EXPLICIT_WINDOWS_CONTROL_ALLOCATION_REQUIRED')
    _ordinary_tool()  # Root's external source/tool receipt must pin this tool.
    environment = {key: value for key, value in os.environ.items()
                   if key.upper() in {'SYSTEMDRIVE', 'PROGRAMDATA', 'TEMP', 'TMP', 'USERPROFILE', 'LOCALAPPDATA', 'APPDATA'}}
    environment.update(SYSTEMROOT='C:\\Windows', WINDIR='C:\\Windows',
                       PSModulePath='C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\Modules',
                       UNIFIED_OUTPUT_CAP_HELPER=str(HELPER))
    encoded = base64.b64encode(PS_MATRIX.encode('utf-16le')).decode('ascii')
    command = [str(POWERSHELL), '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded]
    # External temp files keep pipes from extending timeout retirement. Finite
    # file polling precedes every retained output read; no raw stderr is relayed.
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as error:
        child = subprocess.Popen(command, cwd=ROOT, env=environment,
                                 stdin=subprocess.DEVNULL, stdout=output, stderr=error,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline = time.monotonic() + 8
            while child.poll() is None:
                if time.monotonic() >= deadline or os.fstat(output.fileno()).st_size > 32768 or os.fstat(error.fileno()).st_size > 8192:
                    raise AssertionError('PURE_PS_BOUND_EXCEEDED')
                time.sleep(.01)
        finally:
            cleanup_uncertain = False
            try:
                status = child.poll()
            except BaseException:
                cleanup_uncertain = True
                status = None
            if status is None:
                try:
                    child.kill()
                except BaseException:
                    cleanup_uncertain = True
            # Even an observation/kill failure cannot bypass the held-child wait.
            try:
                retired = child.wait(timeout=2)
                if type(retired) is not int:
                    cleanup_uncertain = True
            except BaseException:
                cleanup_uncertain = True
            if cleanup_uncertain:
                raise AssertionError('PURE_PS_CLEANUP_UNCERTAIN') from None
        if child.returncode != 0 or os.fstat(output.fileno()).st_size > 32768 or os.fstat(error.fileno()).st_size != 0:
            raise AssertionError('PURE_PS_CHILD_FAILED_OR_OUTPUT_REJECTED')
        output.seek(0)
        raw = output.read(32769)
    lines = raw.decode('ascii').splitlines()
    if not lines or lines[0] != 'UNIT_CAP_V1' or len(lines) != len(CASE_IDS) + 1:
        raise AssertionError('PURE_PS_CASE_FRAMING')
    records = {}
    for line in lines[1:]:
        case, separator, outcome = line.partition('|')
        if not separator or case not in CASE_IDS or case in records or outcome not in ('TRUE', 'FALSE', 'NOT_BOOL'):
            raise AssertionError('PURE_PS_CASE_FRAMING')
        records[case] = outcome
    if tuple(records) != CASE_IDS:
        raise AssertionError('PURE_PS_CASE_INVENTORY')
    return records


def make_suite():
    """Explicit allocation seam; ordinary project discovery runs no new cases."""
    class NativeOutputCapAssertionControls(unittest.TestCase):
        def test_actual_shared_classifier_stock_exception_matrix(self):
            # Deliberate first-stage assertion: absent helper => one feature RED,
            # zero PowerShell children, not an old-catch behavior demonstration.
            self.assertTrue(HELPER.is_file(), 'NATIVE_OUTPUT_CAP_HELPER_MISSING')
            records = _run_matrix()
            for case in CASE_IDS:
                with self.subTest(case=case):
                    self.assertEqual(records[case], 'TRUE' if case in ACCEPT_IDS else 'FALSE')
    NativeOutputCapAssertionControls.__module__ = 'native_output_cap_assertion_controls'
    NativeOutputCapAssertionControls.__qualname__ = 'NativeOutputCapAssertionControls'
    return unittest.defaultTestLoader.loadTestsFromTestCase(NativeOutputCapAssertionControls)


if __name__ == '__main__':
    if sys.argv[1:] != ['--allocated-pure-powershell'] or not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise SystemExit('EXPLICIT_ISOLATED_ALLOCATION_REQUIRED')
    result = unittest.TextTestRunner(verbosity=2).run(make_suite())
    raise SystemExit(0 if result.wasSuccessful() and result.testsRun == 1 and not result.skipped else 1)
