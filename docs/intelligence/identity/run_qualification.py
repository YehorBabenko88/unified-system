"""Exact raw tracked source pre/post and mandatory isolated identity tests."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

EXPECTED_TEST_NAMES = (
    'test_actual_tls_read_capability_two_checks_then_replay_denied',
    'test_claims_and_public_constructor_cannot_authenticate',
    'test_wrong_request_tool_store_and_view_deny',
    'test_revocation_and_closed_actual_connection',
    'test_closed_socket_denies',
    'test_copy_and_foreign_authority_reject',
    'test_profile_is_copied_and_cannot_change_grant',
    'test_missing_audit_blocks',
    'test_real_elapsed_registry_expiry_denies',
    'test_clock_rollback_is_permanent_and_monotonic_deadline_independent',
    'test_cumulative_slow_wall_clock_is_not_allowed_to_drift_forever',
    'test_context_inventory_is_bounded',
    'test_audit_full_cannot_issue_or_check',
    'test_revocation_latches_even_when_audit_full',
    'test_denial_and_revocation_target_are_audited',
    'test_nonread_commissioning_grant_unavailable',
    'test_forged_exact_type_handle_not_in_issuer_inventory',
    'test_forged_capability_cannot_delegate_to_method_shaped_none_provider',
    'test_owner_expected_issuer_rejects_legitimate_foreign_issuer_same_store',
    'test_expected_owner_method_is_one_check_and_never_fake_provider',
    'test_query_has_seven_current_checks_then_eighth_denied',
    'test_context_exact_original_peer_pin_not_other_registered_entry',
    'test_wrong_actual_san_denies',
    'test_untrusted_ca_and_missing_client_cert_real_handshake_refused',
)

def git(root, *arguments):
    return subprocess.check_output(['git','--no-replace-objects','-C',str(root),*arguments])

def ordinary(path):
    info = path.lstat()
    assert not path.is_symlink() and not getattr(info,'st_file_attributes',0) & 0x400, str(path)

def primary_objects(root):
    # Recompute actual Git object IDs, not merely cat-file's reported OID header.
    head=git(root,'rev-parse','HEAD').decode().strip()
    commit=git(root,'cat-file','commit',head)
    assert hashlib.sha1(b'commit '+str(len(commit)).encode()+b'\0'+commit).hexdigest()==head
    tree=commit.split(b'\n',1)[0]
    assert tree.startswith(b'tree ')
    root_oid=tree[5:].decode('ascii')
    assert git(root,'rev-parse','HEAD^{tree}').decode().strip()==root_oid
    visited=set()
    def verify(oid):
        if oid in visited: return
        raw=git(root,'cat-file','tree',oid)
        assert hashlib.sha1(b'tree '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid
        visited.add(oid)
        offset=0
        while offset<len(raw):
            space=raw.index(b' ',offset)
            end=raw.index(b'\0',space)
            mode,name=raw[offset:space],raw[space+1:end]
            child=raw[end+1:end+21]
            assert len(child)==20 and name not in (b'',b'.',b'..') and b'/' not in name
            if mode==b'40000': verify(child.hex())
            else: assert mode in (b'100644',b'100755')
            offset=end+21
        assert offset==len(raw)
    verify(root_oid)

def inventory(root):
    root = Path(root).absolute()
    for ancestor in (root,*root.parents): ordinary(ancestor)
    primary_objects(root)
    result = {}
    process = subprocess.Popen(['git','--no-replace-objects','-C',str(root),'cat-file','--batch'],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        for row in git(root,'ls-tree','-rz','--full-tree','HEAD').split(b'\0'):
            if not row: continue
            meta, name = row.split(b'\t',1)
            mode, kind, oid = meta.split()
            assert kind == b'blob' and mode in (b'100644',b'100755')
            path = root / name.decode('utf-8')
            assert path.resolve().is_relative_to(root)
            for ancestor in (path,*path.parents):
                ordinary(ancestor)
                if ancestor==root: break
            process.stdin.write(oid+b'\n'); process.stdin.flush()
            header = process.stdout.readline().split()
            assert header[0] == oid and header[1] == b'blob'
            raw = process.stdout.read(int(header[2])); assert process.stdout.read(1)==b'\n'
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest().encode()==oid
            assert path.read_bytes() == raw, name
            result[name.decode()] = hashlib.sha256(raw).hexdigest()
    finally:
        process.stdin.close(); process.wait(timeout=15); process.stdout.close()
    assert process.returncode == 0
    allowed_dirs = {'.'}
    for name in result:
        for parent in Path(name).parents: allowed_dirs.add(parent.as_posix())
    seen = set()
    for directory, dirs, files in os.walk(root,followlinks=False):
        location = Path(directory)
        for name in tuple(dirs)+tuple(files):
            path = location/name
            ordinary(path)
            relative = path.relative_to(root).as_posix()
            if relative=='.git':
                if name in dirs: dirs.remove(name)
                continue
            assert name not in ('__pycache__','.pytest_cache') and not name.endswith(('.pyc','.pyo')), relative
            if name in dirs:
                assert relative in allowed_dirs, relative
            else:
                assert relative in result, relative
                seen.add(relative)
    assert seen==set(result)
    return result

def validate_test_ids(suite):
    def ids(value):
        for test in value:
            if isinstance(test,unittest.TestSuite): yield from ids(test)
            else: yield test.id()
    actual = list(ids(suite))
    expected = ['test_gateway_identity.GatewayIdentityTests.'+name for name in EXPECTED_TEST_NAMES]
    assert len(actual)==len(set(actual))==24 and sorted(actual)==sorted(expected)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected-head', required=True)
    args = parser.parse_args()
    assert sys.flags.isolated and sys.dont_write_bytecode and sys.pycache_prefix is None
    assert re.fullmatch('[0-9a-f]{40}',args.expected_head)
    # Check unresolved script ancestors BEFORE resolve, so aliases cannot disappear.
    script = Path(__file__).absolute()
    for ancestor in (script,*script.parents): ordinary(ancestor)
    root = script.parents[3]
    assert git(root,'rev-parse','HEAD').decode().strip() == args.expected_head
    before = inventory(root)
    sys.path.insert(0,str(root))
    suite = unittest.defaultTestLoader.discover(str(root/'tests'),pattern='test_gateway_identity.py')
    validate_test_ids(suite)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = inventory(root)
    assert before==after and result.testsRun==24 and not result.skipped
    assert result.wasSuccessful()
    print(json.dumps(dict(result='PASS',head=args.expected_head,tests=24,skips=0,
                          raw_files_before_after=len(before),exact_unique_test_ids=True,
                          scope='DISPOSABLE_MTLS_AND_LOCAL_READ_CAPABILITY_ONLY',
                          cross_owner_read='NOT_RUN',nativeauthentication=False)))

if __name__=='__main__': main()
