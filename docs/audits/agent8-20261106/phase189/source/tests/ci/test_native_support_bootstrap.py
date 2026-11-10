"""MODEL/DATA_ONLY source graphs; no fixture imports or native programs."""
import copy
import hashlib
import io
import json
import os
import signal
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

from tools.ci import verify_native_test_support as verifier


def oid(kind, data):
    return hashlib.sha1(kind + b' ' + str(len(data)).encode() + b'\0' + data).hexdigest()


class FakeGit:
    """Read-only synthetic object protocol, never invokes a process."""
    repositories = {}

    def __init__(self, root, budget):
        self.data = self.repositories[str(root)]
        self.budget = budget

    def call(self, args, *, data=None, cap=None):
        self.budget.check()
        if args == ('rev-parse', 'HEAD'):
            return (self.data['head'] + '\n').encode()
        if args == ('rev-parse', 'HEAD^{tree}'):
            return (self.data['tree'] + '\n').encode()
        if args[0] == 'ls-tree':
            return self.data['listing']
        if args == ('cat-file', '--batch'):
            result = bytearray()
            for item in data.splitlines():
                key = item.decode()
                if key not in self.data['objects']:
                    result.extend(item + b' missing\n')
                else:
                    kind, raw = self.data['objects'][key]
                    result.extend(item + b' ' + kind + b' ' + str(len(raw)).encode() + b'\n' + raw + b'\n')
            return bytes(result)
        raise AssertionError('unexpected command')


class NativeSupportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()
        self.graph_path = self.folder / 'graph.json'
        self.roots = {}
        self.inventories = {}
        self.graph = {
            'schema': 'grid.native-test-support-source-graph.v1-proposed',
            'scope': 'ELIGIBLE_FOR_PURE_SOURCE_VERIFICATION_ONLY_NOT_HA_RUNTIME_OR_FIXTURE_IMPORT',
            'actual_native_positive_api': 'NONE', 'fixture_import_allowed': False,
            'native_fixture_authorization': False, 'source_runtime_adoption': False,
            'strict_time': 'OPTION1_LOGICAL_MUTATIONS_DISABLED',
            'legacy_unified_source': 'e0c2ea20aa4f1bd9476d1046e7e4b41f1b12d8e9_RETAINED_FOR_EXISTING_GROUP_PENDING_ROOT_OWNED_COMPATIBILITY_NO_GLOBAL_REPLACEMENT',
            'whole336file_generic_suite_compatibility': 'NOT_PROVEN',
            'complete_platform_python_dependency_wheel_closure': 'PENDING_OWNER_LOCK_INCLUDES_EXISTING_RUNTIME_PLUS_PYTEST_SUPPORT_NO_UNPINNED_FALLBACK',
            'consul_artifact_provenance': 'PENDING_APPROVED_ARCHIVE_URL_MEMBER_ARCHIVE_SHA_SIZE_PLATFORM_AND_LEAF_CHAIN; NO_DOWNLOAD',
            'artifact_closure': {'status': 'INCOMPLETE_SOURCE_DATA_ONLY', 'fixture_import_allowed': False,
                                 'binary_archive_publisher_closure': 'NONE_APPROVED_IN_THIS_GRAPH',
                                 'dependency_archive_and_install_closure': 'NONE_APPROVED_FOR_BROAD_MATRIX'},
            'known_consul_leaf_sha256_reference_only': {'linux': 'a'*64, 'windows': 'b'*64},
            'existing_support_locks_reference_only': {}, 'historical_objects': [],
            'sources': {}, 'module_origins_for_named_native_group_only': {},
        }
        FakeGit.repositories = {}
        for role, repo in [('grid', 'YehorBabenko88/bybit-cluster-grid'), ('unified_native_support', 'YehorBabenko88/unified-system')]:
            root = self.folder / role
            root.mkdir()
            (root / '.git/objects/info').mkdir(parents=True)
            (root / '.git/refs').mkdir()
            (root / '.git/config').write_bytes(b'[core]\nrepositoryformatversion = 0\nbare = false\n')
            raw = b"raise RuntimeError('INERT_FIXTURE_MUST_NOT_EXECUTE')\n"
            (root / 'fixture.py').write_bytes(raw)
            blob = oid(b'blob', raw)
            tree_raw = b'100644 fixture.py\0' + bytes.fromhex(blob)
            tree = oid(b'tree', tree_raw)
            commit_raw = b'tree ' + tree.encode() + b'\nauthor Model <model@example.invalid> 0 +0000\ncommitter Model <model@example.invalid> 0 +0000\n\nMODEL DATA ONLY\n'
            head = oid(b'commit', commit_raw)
            entry = {'bytes': len(raw), 'git_blob': blob, 'mode': '100644', 'sha256': hashlib.sha256(raw).hexdigest()}
            inv = {'files': {'fixture.py': entry}, 'head': head, 'tree': tree, 'tracked_blobs': 1}
            self.inventories[role] = inv
            self.roots[role] = root
            filename = role + '.json'
            inventory_raw = (json.dumps(inv) + '\n').encode()
            (self.folder / filename).write_bytes(inventory_raw)
            self.graph['sources'][role] = dict(repository=repo, head=head, tree=tree, tracked_blobs=1,
                                               inventory=filename, inventory_sha256=hashlib.sha256(inventory_raw).hexdigest())
            module = 'grid.fixture' if role == 'grid' else 'fixture'
            self.graph['module_origins_for_named_native_group_only'][module] = dict(entry, role=role, path='fixture.py')
            self.graph['historical_objects'].append(dict(entry, role='DYNAMIC_TLS_FIXTURE_BYTES_NOT_EXECUTED',
                head=head, tree=tree, path='fixture.py', object_repository_role=role))
            self.graph['historical_objects'][-1].pop('mode')
            FakeGit.repositories[str(root)] = dict(head=head, tree=tree,
                listing=b'100644 blob ' + blob.encode() + b'\tfixture.py\0',
                objects={head: (b'commit', commit_raw), tree: (b'tree', tree_raw), blob: (b'blob', raw)})
        self.patch = patch.object(verifier, '_Git', FakeGit)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def save(self):
        raw = (json.dumps(self.graph) + '\n').encode()
        self.graph_path.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def verify(self):
        return verifier.verify_native_test_support(self.graph_path, expected_graph_sha256=self.save(), source_roots=self.roots)

    def denied(self, code, action=None):
        with self.assertRaises(verifier.NativeSupportVerificationError) as caught:
            (action or self.verify)()
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(str(caught.exception), code)

    def test_matching_data_keeps_all_execution_flags_false_and_no_global_mutation(self):
        before = (list(sys.path), dict(os.environ), set(sys.modules))
        result = self.verify()
        self.assertEqual(result['status'], 'SOURCE_MATCH_DATA_ONLY')
        self.assertEqual(result['unresolved_codes'], [])
        self.assertIs(result['fixture_import_allowed'], False)
        self.assertIs(result['native_execution_allowed'], False)
        self.assertEqual(set(result), {'schema','graph_sha256','status','sources','historical_objects','module_origins','artifact_closure','unresolved_codes','fixture_import_allowed','native_execution_allowed'})
        self.assertEqual(before, (list(sys.path), dict(os.environ), set(sys.modules)))

    def test_wrong_graph_digest_precedes_descriptor_trust(self):
        self.save()
        self.denied('GRAPH_SHA_MISMATCH', lambda: verifier.verify_native_test_support(self.graph_path, expected_graph_sha256='0'*64, source_roots=self.roots))

    def test_duplicate_json_and_unknown_fields_rejected(self):
        self.graph_path.write_bytes(b'{"schema":"a","schema":"b"}')
        sha = hashlib.sha256(self.graph_path.read_bytes()).hexdigest()
        self.denied('INVALID_DESCRIPTOR', lambda: verifier.verify_native_test_support(self.graph_path, expected_graph_sha256=sha, source_roots=self.roots))
        self.graph['private'] = 'PRIVATE_TOKEN'
        self.denied('INVALID_DESCRIPTOR')

    def test_unknown_schema_and_no_future_authorization(self):
        self.graph['schema'] = 'future'
        self.denied('UNKNOWN_SCHEMA')
        self.graph['schema'] = 'grid.native-test-support-source-graph.v1-proposed'
        self.graph['fixture_import_allowed'] = True
        self.denied('INVALID_DESCRIPTOR')

    def test_inventory_tamper_rejected_before_parse(self):
        (self.folder / 'grid.json').write_bytes(b'PRIVATE')
        self.denied('INVENTORY_SHA_MISMATCH')

    def test_duplicate_inventory_keys_and_missing_source(self):
        raw = b'{"files":{},"files":{}}'
        (self.folder/'grid.json').write_bytes(raw)
        self.graph['sources']['grid']['inventory_sha256'] = hashlib.sha256(raw).hexdigest()
        self.denied('INVALID_DESCRIPTOR')

    def test_missing_source_is_not_adopted_from_objects(self):
        (self.roots['grid']/'fixture.py').unlink()
        self.denied('RAW_MISMATCH')

    def test_path_escape_and_casefold_ambiguity_rejected(self):
        self.graph['sources']['grid']['inventory'] = '../outside.json'
        self.denied('INVALID_PATH')
        self.graph['sources']['grid']['inventory'] = 'grid.json'
        self.graph['module_origins_for_named_native_group_only']['GRID.fixture'] = copy.deepcopy(self.graph['module_origins_for_named_native_group_only']['grid.fixture'])
        self.denied('ORIGIN_CONFLICT')

    def test_wrong_head_and_tree_rejected(self):
        for field, code in [('head', 'WRONG_HEAD'), ('tree', 'WRONG_TREE')]:
            original = FakeGit.repositories[str(self.roots['grid'])][field]
            FakeGit.repositories[str(self.roots['grid'])][field] = '0'*40
            self.denied(code)
            FakeGit.repositories[str(self.roots['grid'])][field] = original

    def test_changed_raw_and_extra_cache_source_rejected(self):
        file = self.roots['grid'] / 'fixture.py'
        raw = file.read_bytes()
        file.write_bytes(b'PRIVATE_CHANGED')
        self.denied('RAW_MISMATCH')
        file.write_bytes(raw)
        (self.roots['grid'] / '__pycache__').mkdir()
        self.denied('EXTRA_SOURCE_FILE')

    def test_missing_historical_object_rejected_without_fallback(self):
        self.graph['historical_objects'][0]['head'] = 'f'*40
        self.denied('MISSING_HISTORICAL_OBJECT')

    def test_origin_conflict_and_source_order_independence(self):
        result = self.verify()
        self.roots = dict(reversed(list(self.roots.items())))
        self.assertEqual(result, self.verify())
        self.graph['module_origins_for_named_native_group_only']['grid.fixture']['role'] = 'unified_native_support'
        self.denied('ORIGIN_CONFLICT')

    def test_private_ambient_fallback_never_used(self):
        with patch.dict(os.environ, {'UNIFIED_SOURCE_ROOT':'PRIVATE','PATH':'PRIVATE','GIT_OBJECT_DIRECTORY':'PRIVATE'}):
            self.roots.pop('unified_native_support')
            self.denied('INVALID_PATH')

    def test_hardlink_source_and_alternates_rejected(self):
        link = self.folder / 'alias.py'
        os.link(self.roots['grid'] / 'fixture.py', link)
        self.denied('UNSAFE_FILE')
        link.unlink()
        (self.roots['grid'] / '.git/objects/info/alternates').write_bytes(b'PRIVATE')
        self.denied('GIT_VERIFICATION_FAILED')

    def test_declared_primary_and_blob_limits_rejected_before_git(self):
        self.graph['sources']['grid']['tracked_blobs'] = True
        self.denied('INVALID_DESCRIPTOR')

    def rewrite_inventory(self, role, inventory):
        raw = json.dumps(inventory).encode()
        (self.folder / (role+'.json')).write_bytes(raw)
        self.graph['sources'][role]['inventory_sha256'] = hashlib.sha256(raw).hexdigest()
        self.graph['sources'][role]['tracked_blobs'] = inventory['tracked_blobs']
        self.graph['sources'][role]['tree'] = inventory['tree']

    def test_large_changed_source_is_raw_mismatch(self):
        (self.roots['grid']/'fixture.py').write_bytes(b'x'*1000)
        self.denied('RAW_MISMATCH')

    def test_blob_and_primary_budgets_checked_before_git(self):
        inv = copy.deepcopy(self.inventories['grid'])
        inv['files']['fixture.py']['bytes'] = 20*1024*1024+1
        self.rewrite_inventory('grid',inv)
        with patch.object(verifier,'_Git') as child:
            self.denied('INVALID_DESCRIPTOR')
            child.assert_not_called()
        for role in self.roots:
            inv = copy.deepcopy(self.inventories[role])
            inv['files']['fixture.py']['bytes'] = 20*1024*1024
            inv['files']['other.py'] = copy.deepcopy(inv['files']['fixture.py'])
            inv['tracked_blobs'] = 2
            inv['tree'] = verifier._tree_id(inv['files'])
            self.rewrite_inventory(role,inv)
        with patch.object(verifier,'_Git') as child:
            self.denied('INVALID_DESCRIPTOR')
            child.assert_not_called()

    def test_casefold_inventory_and_windows_alias_paths(self):
        for value in ('../outside','C:/outside','NUL','x.','x\\y','a//b'):
            self.graph['sources']['grid']['inventory'] = value
            self.denied('INVALID_PATH')
        self.graph['sources']['grid']['inventory'] = 'grid.json'
        inv = copy.deepcopy(self.inventories['grid'])
        inv['files']['Fixture.py'] = copy.deepcopy(inv['files']['fixture.py'])
        inv['tracked_blobs'] = 2
        self.rewrite_inventory('grid',inv)
        self.denied('ORIGIN_CONFLICT')

    def test_primary_object_framing_and_hash_corruption(self):
        model = FakeGit.repositories[str(self.roots['grid'])]
        key = self.inventories['grid']['files']['fixture.py']['git_blob']
        kind, raw = model['objects'][key]
        model['objects'][key] = (kind,b'x'*len(raw))
        self.denied('GIT_VERIFICATION_FAILED')

    def test_reparse_metadata_is_unsafe(self):
        info = types.SimpleNamespace(st_mode=0o100644,st_nlink=1,st_file_attributes=1024)
        with patch.object(Path,'lstat',return_value=info):
            with self.assertRaises(verifier.NativeSupportVerificationError) as caught:
                verifier._ordinary(self.graph_path,directory=False)
        self.assertEqual(caught.exception.code,'UNSAFE_FILE')


class BudgetTests(unittest.TestCase):
    def linked_worktree(self, folder, relative):
        root = folder/'linked'
        root.mkdir()
        gitdir = folder/'admin/worktrees/linked'
        gitdir.mkdir(parents=True)
        (root/'.git').write_bytes(('gitdir: '+str(gitdir)+'\n').encode())
        (gitdir/'commondir').write_bytes((relative+'\n').encode())
        return root,gitdir

    def test_ordinary_parent_commondir_remains_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp).resolve()
            root,gitdir = self.linked_worktree(folder,'../..')
            (folder/'admin/objects/info').mkdir(parents=True)
            self.assertEqual(verifier._metadata(root,verifier._Budget()),gitdir)

    def test_commondir_alias_ancestor_rejected_before_resolve_or_spawn(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp).resolve()
            root,gitdir = self.linked_worktree(folder,'../alias/target')
            alias = folder/'admin/worktrees/alias'
            (alias/'target/objects/info').mkdir(parents=True)
            original_lstat = Path.lstat
            original_resolve = Path.resolve
            resolution = []
            def lstat(path,*args,**kwargs):
                # Model lstat's lexical ../ handling without resolving links.
                if os.path.normpath(str(path)) == os.path.normpath(str(alias)):
                    return types.SimpleNamespace(st_mode=0o120777,st_file_attributes=1024)
                return original_lstat(path,*args,**kwargs)
            def resolve(path,*args,**kwargs):
                if '..' in path.parts and 'alias' in path.parts:
                    resolution.append(str(path))
                return original_resolve(path,*args,**kwargs)
            with patch.object(Path,'lstat',lstat),patch.object(Path,'resolve',resolve),patch.object(verifier.subprocess,'Popen') as spawn:
                with self.assertRaises(verifier.NativeSupportVerificationError) as caught:
                    verifier._metadata(root,verifier._Budget())
                self.assertEqual(caught.exception.code,'UNSAFE_FILE')
                self.assertEqual(resolution,[],'commondir alias must be rejected before resolve')
                self.assertFalse(spawn.called)

    def test_windows_gate_zero_spawn_and_no_global_mutation(self):
        before = (list(sys.path),dict(os.environ))
        adapter = object.__new__(verifier._Git)
        adapter.root = Path.cwd()
        adapter.gitdir = adapter.root/'.git'
        adapter.budget = verifier._Budget()
        with patch.object(verifier,'_PLATFORM','nt',create=True),patch.object(verifier.subprocess,'Popen') as spawn:
            with self.assertRaises(verifier.NativeSupportVerificationError) as caught:
                adapter.call(('rev-parse','HEAD'),cap=64)
            self.assertEqual(caught.exception.code,'GIT_VERIFICATION_FAILED')
            self.assertFalse(spawn.called,'Windows must not start a Git process')
        self.assertEqual(before,(list(sys.path),dict(os.environ)))

    def test_windows_constructor_rejects_before_source_or_git_probe(self):
        with patch.object(verifier,'_PLATFORM','nt',create=True),patch.object(verifier,'_metadata') as source,patch.object(verifier.subprocess,'Popen') as spawn:
            with self.assertRaises(verifier.NativeSupportVerificationError):
                verifier._Git(Path.cwd(),verifier._Budget())
            self.assertFalse(source.called,'Windows constructor must fail before source probing')
            self.assertFalse(spawn.called,'Windows must not start a Git process')

    def test_unc_namespace_rejected_before_any_filesystem_probe(self):
        with patch.object(verifier,'_ordinary',side_effect=AssertionError('NETWORK_PATH_TOUCHED')) as probe:
            with self.assertRaises(verifier.NativeSupportVerificationError):
                verifier._canonical(Path('//PRIVATE/share/source'),directory=True)
            probe.assert_not_called()

    def test_whole_watchdog_and_aggregate_before_retention(self):
        with patch.object(verifier.time, 'monotonic', return_value=0):
            budget = verifier._Budget()
        with patch.object(verifier.time, 'monotonic', return_value=91):
            with self.assertRaises(verifier.NativeSupportVerificationError):
                budget.check()
        with patch.object(verifier.time, 'monotonic', return_value=0):
            budget = verifier._Budget()
            budget.take('stdout', 72*1024*1024)
            with self.assertRaises(verifier.NativeSupportVerificationError):
                budget.take('stdout', 1)

    def test_git_environment_is_closed_not_parent_derived(self):
        with patch.dict(os.environ, {'GIT_CONFIG_PARAMETERS':'PRIVATE','GIT_ALTERNATE_OBJECT_DIRECTORIES':'PRIVATE','PATH':'PRIVATE'}):
            env = verifier._git_environment()
        self.assertNotIn('PATH', env)
        self.assertNotIn('GIT_CONFIG_PARAMETERS', env)
        self.assertNotIn('GIT_ALTERNATE_OBJECT_DIRECTORIES', env)
        self.assertEqual(env['GIT_NO_REPLACE_OBJECTS'], '1')


class ProcessDouble:
    def __init__(self, stdout=b'', stderr=b'', hanging=False):
        self.stdout = io.BytesIO(stdout)
        self.stderr = io.BytesIO(stderr)
        self.stdin = None
        self.hanging = hanging
        self.killed = False
        self.reaped = False
        self.pid = 700001
        self.poll_calls = 0
        self.order = []
        ProcessDouble.current = self

    def poll(self):
        self.poll_calls += 1
        return None if self.hanging and not self.killed else 0

    def wait(self, timeout):
        if self.hanging and not self.killed:
            raise AssertionError('wait without prior owned kill')
        self.order.append('REAP')
        self.reaped = True
        return 0

    def kill(self):
        self.killed = True


class StreamingControls(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        patch.object(verifier,'_PLATFORM','posix').start()
        patch.object(verifier,'_SYSTEM','linux',create=True).start()
        def group_kill(pid, sig):
            p = ProcessDouble.current
            self.assertFalse(p.reaped)
            self.assertEqual(pid,p.pid)
            p.order.append('GROUP_KILL')
            p.kill()
        self.group_kill = patch.object(verifier.os,'killpg',side_effect=group_kill,create=True).start()
        patch.object(verifier.os,'getpgid',side_effect=lambda pid:pid,create=True).start()
        patch.object(verifier.os,'getsid',side_effect=lambda pid:pid,create=True).start()
        def peek(*args):
            p = ProcessDouble.current
            return None if p.hanging and not p.killed else types.SimpleNamespace(si_pid=p.pid)
        patch.object(verifier.os,'waitid',side_effect=peek,create=True).start()
        for name,value in [('P_PID',1),('WEXITED',4),('WNOHANG',1),('WNOWAIT',0x1000000)]:
            patch.object(verifier.os,name,value,create=True).start()
        patch.object(signal,'SIGCHLD',17,create=True).start()
        patch.object(signal,'SIGKILL',9,create=True).start()
        patch.object(signal,'getsignal',return_value=signal.SIG_DFL).start()

    def adapter(self):
        git = object.__new__(verifier._Git)
        git.root = Path.cwd()
        git.gitdir = git.root/'.git'
        git.budget = verifier._Budget()
        return git

    def test_stream_success_closed_environment_and_owned_streams(self):
        git = self.adapter()
        process = ProcessDouble(b'abc',b'PRIVATE_STDERR')
        with patch.object(verifier.subprocess,'Popen',return_value=process) as spawn:
            self.assertEqual(git.call(('rev-parse','HEAD'),cap=3),b'abc')
        self.assertTrue(process.reaped and process.stdout.closed and process.stderr.closed)
        self.assertEqual(spawn.call_args.args[0][0],str(verifier._GIT_EXE))
        self.assertNotIn('PATH',spawn.call_args.kwargs['env'])
        self.assertFalse(spawn.call_args.kwargs['shell'])

    def test_new_session_and_group_retirement_before_reap(self):
        process = ProcessDouble(b'abc')
        with patch.object(verifier.subprocess,'Popen',return_value=process) as spawn:
            self.assertEqual(self.adapter().call(('rev-parse','HEAD'),cap=3),b'abc')
        self.assertIs(spawn.call_args.kwargs.get('start_new_session'),True)
        self.assertEqual(process.poll_calls,0)
        self.assertEqual(process.order,['GROUP_KILL','REAP'])

    def test_unqualified_posix_context_rejects_before_spawn(self):
        for field,value in [('_SYSTEM','darwin')]:
            with patch.object(verifier,field,value),patch.object(verifier.subprocess,'Popen') as spawn:
                with self.assertRaises(verifier.NativeSupportVerificationError):
                    self.adapter().call(('rev-parse','HEAD'),cap=1)
                self.assertFalse(spawn.called)
        with patch.object(signal,'getsignal',return_value=signal.SIG_IGN),patch.object(verifier.subprocess,'Popen') as spawn:
            with self.assertRaises(verifier.NativeSupportVerificationError):
                self.adapter().call(('rev-parse','HEAD'),cap=1)
            self.assertFalse(spawn.called)

    def test_preexisting_python_worker_rejects_before_spawn(self):
        with patch.object(verifier.threading,'enumerate',return_value=[threading.main_thread(),object()]),patch.object(verifier.subprocess,'Popen') as spawn:
            with self.assertRaises(verifier.NativeSupportVerificationError):
                self.adapter().call(('rev-parse','HEAD'),cap=1)
            self.assertFalse(spawn.called)

    def test_missing_nonreaping_api_rejects_before_spawn(self):
        with patch.object(verifier.os,'waitid',None),patch.object(verifier.subprocess,'Popen') as spawn:
            with self.assertRaises(verifier.NativeSupportVerificationError):
                self.adapter().call(('rev-parse','HEAD'),cap=1)
            self.assertFalse(spawn.called)

    def test_group_custody_uncertainty_never_signals_unknown_group(self):
        process = ProcessDouble()
        with patch.object(verifier.os,'waitid',side_effect=ChildProcessError),patch.object(verifier.subprocess,'Popen',return_value=process):
            with self.assertRaises(verifier.NativeSupportVerificationError) as caught:
                self.adapter().call(('rev-parse','HEAD'),cap=1)
        self.assertEqual(caught.exception.code,'GIT_VERIFICATION_FAILED')
        self.assertFalse(self.group_kill.called)
        self.assertFalse(process.reaped)

    def test_stdout_overflow_sanitizes_and_reaps_all_threads(self):
        process = ProcessDouble(b'PRIVATE_OVERSIZE')
        threads = []
        original = threading.Thread
        def capture(*args,**kwargs):
            thread = original(*args,**kwargs)
            threads.append(thread)
            return thread
        with patch.object(verifier.subprocess,'Popen',return_value=process), patch.object(verifier.threading,'Thread',side_effect=capture):
            with self.assertRaises(verifier.NativeSupportVerificationError) as caught:
                self.adapter().call(('rev-parse','HEAD'),cap=2)
        self.assertEqual(str(caught.exception),'GIT_VERIFICATION_FAILED')
        self.assertTrue(process.reaped and all(not t.is_alive() for t in threads))

    def test_stderr_overflow_is_aggregate_and_private(self):
        process = ProcessDouble(b'',b'PRIVATE')
        with patch.object(verifier,'_STDERR_LIMIT',4),patch.object(verifier.subprocess,'Popen',return_value=process):
            with self.assertRaises(verifier.NativeSupportVerificationError) as caught:
                self.adapter().call(('rev-parse','HEAD'),cap=1)
        self.assertEqual(str(caught.exception),'GIT_VERIFICATION_FAILED')
        self.assertTrue(process.reaped)

    def test_child_watchdog_kills_only_owned_child_and_reaps(self):
        process = ProcessDouble(hanging=True)
        ticks = [0]
        def clock():
            ticks[0] += 1
            return ticks[0] / 10
        with patch.object(verifier.time,'monotonic',side_effect=clock),patch.object(verifier.subprocess,'Popen',return_value=process):
            with self.assertRaises(verifier.NativeSupportVerificationError):
                self.adapter().call(('rev-parse','HEAD'),cap=1)
        self.assertTrue(process.killed and process.reaped)

    def test_no_version_or_arbitrary_git_arguments(self):
        with patch.object(verifier.subprocess,'Popen') as spawn:
            with self.assertRaises(verifier.NativeSupportVerificationError):
                self.adapter().call(('--version',))
            spawn.assert_not_called()

    def test_blocked_reader_retires_when_owned_child_killed(self):
        event = threading.Event()
        class Blocked(io.BytesIO):
            def readinto(self,buffer):
                event.wait(10)
                return 0
        process = ProcessDouble(hanging=True)
        process.stdout = Blocked()
        kill = process.kill
        def retire():
            kill()
            event.set()
        process.kill = retire
        ticks = [0]
        def clock():
            ticks[0] += 1
            return ticks[0] / 10
        with patch.object(verifier.time,'monotonic',side_effect=clock),patch.object(verifier.subprocess,'Popen',return_value=process):
            with self.assertRaises(verifier.NativeSupportVerificationError):
                self.adapter().call(('rev-parse','HEAD'),cap=1)
        self.assertTrue(process.killed and process.reaped and event.is_set() and process.stdout.closed)

    def test_exited_shim_with_inherited_pipe_retired_before_leader_reap(self):
        event = threading.Event()
        class InheritedPipe(io.BytesIO):
            def readinto(self,buffer):
                event.wait(10)
                return 0
        process = ProcessDouble()  # leader has exited, but has not been reaped
        process.stdout = InheritedPipe()
        kill = process.kill
        def release_family():
            self.assertFalse(process.reaped)
            kill()
            event.set()
        process.kill = release_family
        ticks = [0]
        def clock():
            ticks[0] += 1
            return ticks[0]/10
        with patch.object(verifier.time,'monotonic',side_effect=clock),patch.object(verifier.subprocess,'Popen',return_value=process):
            with self.assertRaises(verifier.NativeSupportVerificationError):
                self.adapter().call(('rev-parse','HEAD'),cap=1)
        self.assertEqual(process.order,['GROUP_KILL','REAP'])
        self.assertTrue(event.is_set() and process.stdout.closed)


if __name__ == '__main__':
    unittest.main()
