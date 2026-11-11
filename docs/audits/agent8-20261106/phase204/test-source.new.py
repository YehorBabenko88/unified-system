"""Proposed pure regression seam; SOURCE ONLY until Root allocates execution.

Future execution reads actual workflow/qualifier source, extracts actual AST
definitions, and compiles those definitions against inert fakes. It never imports
qualify.py, executes workflow top-level code, uses a real Popen/backend, creates
filesystem fixtures, or changes production/tests. Source extraction is the seam,
not a copied implementation. No results are claimed before an allocated RED.
"""
import ast
import hashlib
import io
from pathlib import Path, PurePosixPath
import stat
from types import SimpleNamespace
import traceback
import unittest

HERE = Path(__file__).absolute().parent
WORKFLOW = HERE.parents[4] / '.github/workflows/projection-recovery-47.yml'
QUALIFIER = HERE / 'qualify.py'


def workflow_definitions():
    lines = WORKFLOW.read_text(encoding='utf-8').splitlines()
    start = lines.index('        run: |') + 1
    body = []
    for line in lines[start:]:
        if line and not line.startswith('          '):
            break
        body.append(line[10:])
    parsed = ast.parse('\n'.join(body), filename=str(WORKFLOW))
    definitions = [node for node in parsed.body if isinstance(node, ast.FunctionDef)]
    if len([n for n in definitions if n.name == 'ledger']) != 1:
        raise AssertionError('Actual inline ledger definition required')
    return definitions


class InertTree:
    """Path metadata/content model. Every filesystem operation is an observation."""
    ROOT = '/sandbox/root'
    LEAF = '/sandbox/root/folder/item.txt'

    def __init__(self, blocked=None, kind=None):
        self.blocked = blocked
        self.kind = kind
        self.events = []
        self.payload_sha256 = None
        scenario = self

        class ModelPath(PurePosixPath):
            def resolve(self, *args, **kwargs):
                scenario.record('resolve', self)
                return self

            def is_symlink(self):
                scenario.record('is_symlink', self)
                return scenario.kind_for(self) == 'symlink'

            def is_dir(self):
                scenario.record('is_dir', self)
                return scenario.kind_for(self) in ('directory', 'reparse')

            def is_file(self):
                scenario.record('is_file', self)
                return scenario.kind_for(self) == 'file'

            def exists(self):
                scenario.record('exists', self)
                return scenario.kind_for(self) != 'missing'

            def lstat(self):
                scenario.record('lstat', self)
                kind = scenario.kind_for(self)
                if kind == 'missing':
                    raise FileNotFoundError(str(self))
                mode = stat.S_IFREG if kind == 'file' else stat.S_IFDIR
                if kind == 'symlink':
                    mode = stat.S_IFLNK
                return SimpleNamespace(st_mode=mode | 0o755, st_file_attributes=1024 if kind == 'reparse' else 0, st_nlink=1)

            def read_bytes(self):
                scenario.record('read_bytes', self)
                if str(self) != scenario.LEAF:
                    raise AssertionError('Only inert selected leaf may be read')
                return b'fixture bytes\n'

            def rglob(self, pattern):
                scenario.record('rglob', self)
                return iter([ModelPath('/sandbox/root/folder'), ModelPath(scenario.LEAF)])

        self.Path = ModelPath
        self.root = ModelPath(self.ROOT)

    def kind_for(self, path):
        if str(path) == self.blocked:
            return self.kind
        return 'file' if str(path) == self.LEAF else 'directory'

    def record(self, operation, path):
        self.events.append((operation, str(path)))

    def git(self, root, *args, data=None):
        self.record('git', root)
        payload = b'fixture bytes\n'
        oid = hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest().encode()
        if args == ('rev-parse', 'HEAD'):
            return b'1' * 40 + b'\n'
        if args == ('for-each-ref', 'refs/replace', '--format=%(refname)'):
            return b''
        if args == ('rev-parse', 'HEAD^{tree}'):
            return b'2' * 40 + b'\n'
        if args == ('ls-tree', '-rz', '--full-tree', 'HEAD'):
            return b'100644 blob ' + oid + b'\tfolder/item.txt\0'
        if args == ('cat-file', '--batch'):
            return oid + b' blob ' + str(len(payload)).encode() + b'\n' + payload + b'\n'
        raise AssertionError('Unexpected Git request in inert backend')

    def sha256(self, raw):
        self.events.append(('sha256', '<payload>'))
        result = hashlib.sha256(raw)
        self.payload_sha256 = result.hexdigest()
        return result

    def ledger(self):
        env = {'pathlib': SimpleNamespace(PurePosixPath=PurePosixPath, Path=self.Path),
               'Path': self.Path, 'stat': stat, 'io': io,
               'os': SimpleNamespace(), 'hashlib': SimpleNamespace(sha1=hashlib.sha1, sha256=self.sha256)}
        # Actual definitions only; imports, checkout, subprocess and writes from
        # the workflow are excluded. The actual g name is replaced with inert g.
        module = ast.Module(body=workflow_definitions(), type_ignores=[])
        exec(compile(ast.fix_missing_locations(module), str(WORKFLOW), 'exec'), env)
        env['g'] = self.git
        return env['ledger'](self.root, '1' * 40, 1)


class RootFirstControls(unittest.TestCase):
    def assert_unsafe_parent_refuses_before_descendants(self, kind):
        tree = InertTree('/sandbox', kind)
        result = None
        caught = None
        try:
            result = tree.ledger()
        except (AssertionError, RuntimeError, OSError) as error:
            caught = error
        descendant_events = [(op, path) for op, path in tree.events
                             if path.startswith('/sandbox/') or op in ('git', 'sha256')]
        self.assertEqual(descendant_events, [], 'Unsafe parent must stop before root/descendant/Git/hash access')
        self.assertIsNotNone(caught, 'Unsafe ancestry must be refused')
        self.assertIsNone(result, 'Unsafe ancestry cannot yield a ledger')
        self.assertIsNone(tree.payload_sha256, 'Failure observation hash must remain null')

    def test_reparse_parent_stops_before_descendant_or_git(self):
        self.assert_unsafe_parent_refuses_before_descendants('reparse')

    def test_file_parent_stops_before_descendant_or_git(self):
        self.assert_unsafe_parent_refuses_before_descendants('file')

    def test_missing_parent_stops_before_descendant_or_git(self):
        self.assert_unsafe_parent_refuses_before_descendants('missing')

    def test_file_root_stops_before_leaf_git_or_hash(self):
        tree = InertTree(InertTree.ROOT, 'file')
        result = None
        caught = None
        try:
            result = tree.ledger()
        except (AssertionError, RuntimeError, OSError) as error:
            caught = error
        self.assertFalse(any(op in ('git', 'sha256') or path.startswith(tree.ROOT + '/') for op, path in tree.events))
        self.assertIsNotNone(caught)
        self.assertIsNone(result)
        self.assertIsNone(tree.payload_sha256)

    def test_selected_reparse_parent_stops_before_leaf_inspection(self):
        tree = InertTree('/sandbox/root/folder', 'reparse')
        result = None
        caught = None
        try:
            result = tree.ledger()
        except (AssertionError, RuntimeError, OSError) as error:
            caught = error
        self.assertFalse(any(path == tree.LEAF for _, path in tree.events), 'Selected leaf cannot be inspected through unsafe parent')
        self.assertIsNotNone(caught)
        self.assertIsNone(result)
        self.assertIsNone(tree.payload_sha256)

    def test_ordinary_tree_retains_exact_blob_and_ledger(self):
        tree = InertTree()
        actual_tree, ledger = tree.ledger()
        self.assertEqual(actual_tree, '2' * 40)
        self.assertEqual(ledger, {'folder/item.txt': {'bytes': 14, 'sha256': hashlib.sha256(b'fixture bytes\n').hexdigest()}})


def actual_class_seam():
    parsed = ast.parse(QUALIFIER.read_text(encoding='utf-8'), filename=str(QUALIFIER))
    run = next(n for n in parsed.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
    cls = [n for n in ast.walk(run) if isinstance(n, ast.ClassDef) and n.name == 'OwnedPopen']
    need = [n for n in parsed.body if isinstance(n, ast.FunctionDef) and n.name == 'need']
    outer_try = next(n for n in run.body if isinstance(n, ast.Try))
    held_loops = [n for n in outer_try.finalbody if isinstance(n, ast.For)
                  and isinstance(n.target, ast.Name) and n.target.id == 'child'
                  and isinstance(n.iter, ast.Name) and n.iter.id == 'held']
    cleanup = [loop for loop in held_loops
               if not any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda))
                          for n in ast.walk(loop))
               and {'kill', 'wait'}.issubset({
                   n.func.attr for n in ast.walk(loop)
                   if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                   and isinstance(n.func.value, ast.Name) and n.func.value.id == 'child'
               })]
    if len(cls) != 1 or len(need) != 1 or len(cleanup) != 1:
        raise AssertionError('One actual OwnedPopen/need/held-handle cleanup loop required')
    # Synthetic binding wrapper only; actual class and cleanup loop AST unchanged.
    wrapper = ast.parse('def seam():\n pending=None\n stopped=False\n def cleanup():\n  nonlocal stopped\n  stopped=True\n return None\n').body[0]
    cleanup_wrapper = wrapper.body[-2]
    cleanup_wrapper.body.extend(cleanup)
    wrapper.body.insert(2, cls[0])
    wrapper.body[-1] = ast.Return(value=ast.Tuple(elts=[ast.Name(id='OwnedPopen', ctx=ast.Load()), ast.Name(id='cleanup', ctx=ast.Load())], ctx=ast.Load()))
    return ast.Module(body=[need[0], wrapper], type_ignores=[])


class ReturnedHandleControls(unittest.TestCase):
    def make_seam(self):
        state = {'creation_intents': [], 'held_children': [], 'errors': [], 'cleanup_uncertain': False}
        held, effects = [], []

        class ModelPath(PurePosixPath):
            def resolve(self, *args, **kwargs):
                return self

            @classmethod
            def cwd(cls):
                return cls('/source')

        class InertSuccessfulPopen:
            def __init__(self, command, **kwargs):
                effects.append('constructor_returned')
                self.pid = 7001
                self.returncode = None
                # Deliberately leave the allowance pending. Actual class must
                # refuse this invariant, but still retain the returned handle.

            def poll(self):
                return self.returncode

            def kill(self):
                effects.append('kill_held_handle')

            def wait(self, timeout):
                effects.append(('wait_held_handle', timeout))
                if 'kill_held_handle' not in effects:
                    raise AssertionError('wait must follow kill')
                self.returncode = -1
                return self.returncode

        main = object()
        env = {'original_popen': InertSuccessfulPopen, 'state': state, 'held': held,
               'Path': ModelPath, 'target': ModelPath('/source'), 'real': ModelPath('/python'),
               'helper': ModelPath('/source/helper.py'), 'temp': ModelPath('/owned/temp'),
               'CHILD_PHASES': ('BEFORE_COMMIT', 'AFTER_COMMIT', 'AFTER_COMMIT'),
               'started': 0, 'time': SimpleNamespace(monotonic=lambda: 1), 'traceback': traceback,
               'threading': SimpleNamespace(current_thread=lambda: main, main_thread=lambda: main, get_ident=lambda: 1),
               'subprocess': SimpleNamespace(PIPE=-1, CREATE_NO_WINDOW=0x08000000, list2cmdline=lambda args: ' '.join(args))}
        exec(compile(ast.fix_missing_locations(actual_class_seam()), str(QUALIFIER), 'exec'), env)
        creator, cleanup = env['seam']()
        command = ['/python', '-I', '-S', '-B', '/source/helper.py', 'BEFORE_COMMIT', '/owned/temp/case/own.sqlite', '/owned/temp/case/phase.marker']
        kwargs = {'stdout': -1, 'stderr': -1, 'creationflags': 0x08000000}
        return creator, cleanup, command, kwargs, held, effects, state

    def test_returned_handle_registered_before_invariant_refusal(self):
        creator, _, command, kwargs, held, effects, state = self.make_seam()
        with self.assertRaisesRegex(RuntimeError, 'Audit allowance not consumed'):
            creator(command, **kwargs)
        self.assertEqual(effects, ['constructor_returned'])
        self.assertEqual(len(held), 1, 'Returned backend handle must already be in cleanup registry')
        self.assertTrue(state['cleanup_uncertain'], 'Invariant refusal must not become success')

    def test_invariant_refusal_cleanup_kills_and_waits_known_handle(self):
        creator, cleanup, command, kwargs, held, effects, state = self.make_seam()
        with self.assertRaisesRegex(RuntimeError, 'Audit allowance not consumed'):
            creator(command, **kwargs)
        cleanup()  # Actual finally-loop AST, inert handles only.
        self.assertEqual(effects, ['constructor_returned', 'kill_held_handle', ('wait_held_handle', 2)])
        self.assertEqual(len(held), 1)
        self.assertIsNotNone(held[0].poll())
        self.assertTrue(state['cleanup_required'])

    def test_preconstructor_refusal_creates_no_handle(self):
        creator, _, command, kwargs, held, effects, _ = self.make_seam()
        kwargs['shell'] = True
        with self.assertRaisesRegex(RuntimeError, 'No cwd/env/shell override'):
            creator(command, **kwargs)
        self.assertEqual(held, [])
        self.assertEqual(effects, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
