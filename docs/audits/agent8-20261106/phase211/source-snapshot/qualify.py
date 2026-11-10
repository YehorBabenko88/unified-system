"""Ordinary hosted SQLite unit qualification; no authority or native admission.

SOURCE PREPARATION ONLY until Root/A8 review. No hard wall-clock Timer: hosted
job cancellation is distinct from normal held-handle child retirement.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import threading
import time
import traceback
import xml.etree.ElementTree as ET

HERE = Path(__file__).absolute().parent
FILES = (
    'tests/persistence/test_result_store.py',
    'tests/persistence/test_result_store_recovery.py',
    'tests/research/gateway_artifact_persistence/test_local_stage.py',
    'tests/research/gateway_artifact_persistence/test_projection_recovery_without_issuer.py',
)
PHASES = ('setup', 'call', 'teardown')
CHILD_PHASES = ('BEFORE_COMMIT', 'AFTER_COMMIT', 'AFTER_COMMIT')


def need(value, message):
    if not value:
        raise RuntimeError(message)


def ordinary(path, kind='directory'):
    """Check from anchor down; never inspect a descendant of unsafe ancestry."""
    need(path.is_absolute() and '..' not in path.parts, 'Absolute lexical path required')
    chain = [*reversed(path.parents), path]
    for index, part in enumerate(chain):
        info = part.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not (getattr(info, 'st_file_attributes', 0) & 1024), 'Link/reparse ancestry')
        final = index == len(chain) - 1
        if final and kind == 'file':
            need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'Ordinary single-link file required')
        elif final and kind == 'either':
            need(stat.S_ISDIR(info.st_mode) or (stat.S_ISREG(info.st_mode) and info.st_nlink == 1), 'Ordinary directory/file required')
        else:
            need(stat.S_ISDIR(info.st_mode), 'Ordinary directory ancestry required')
    return info


def checked_files(root):
    ordinary(root)
    pending = [root]
    while pending:
        directory = pending.pop()
        ordinary(directory)
        for path in sorted(directory.iterdir(), key=str):
            rel = path.relative_to(root)
            if rel.parts[0] == '.git':
                continue
            info = ordinary(path, 'either')
            if stat.S_ISDIR(info.st_mode):
                pending.append(path)
            else:
                yield path


def digest(path):
    ordinary(path, 'file')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def absent(path):
    ordinary(path.parent)
    try:
        path.lstat()
    except FileNotFoundError:
        return True
    return False


def read_json(path):
    info = ordinary(path, 'file')
    need(info.st_size <= 16 * 1024 * 1024, 'JSON oversized')
    return json.loads(path.read_bytes())


def write_new(path, value):
    # A candidate contains facts, not proof of its own persisted finalization.
    ordinary(path.parent)
    with path.open('x', encoding='utf-8', newline='\n') as out:
        json.dump(value, out, sort_keys=True, indent=2)
        out.write('\n')


def physical(root):
    result = {}
    for p in checked_files(root):
        rel = p.relative_to(root)
        st = ordinary(p, 'file')
        need(p.suffix not in ('.pyc', '.pyo'), 'Cache in source')
        result[rel.as_posix()] = {'sha256': digest(p), 'bytes': st.st_size}
    return result


def installed_files(root):
    ordinary(root)
    return physical(root)


def layout(args):
    target, deps, evidence = (Path(x).absolute() for x in (args.target, args.deps, args.evidence))
    namespace = evidence.parent
    runner_temp = Path(os.environ['RUNNER_TEMP']).absolute()
    for root in (runner_temp, namespace, evidence, deps, target):
        ordinary(root)
    need(namespace.is_relative_to(runner_temp) and namespace != runner_temp, 'Not owned runner.temp namespace')
    need(evidence == namespace / 'evidence' and deps == namespace / 'deps', 'Fixed namespace layout required')
    need(not target.is_relative_to(namespace) and not namespace.is_relative_to(target), 'Source/state overlap')
    need(os.environ.get('GITHUB_ACTIONS') == 'true' and os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted'
         and os.environ.get('RUNNER_OS') == 'Windows' and sys.platform == 'win32', 'Hosted Windows lane only')
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, 'Use real python -I -S -B')
    need(sys.version_info[:3] == (3, 12, 10), 'Exact Python3.12.10 required')
    return target, deps, evidence, namespace


def preflight(target, deps, evidence):
    expected = read_json(HERE / 'expected47.json')
    bootstrap = read_json(evidence / 'bootstrap.json')
    need(bootstrap.get('bootstrap_ok') is True and bootstrap.get('source_verified') is True, 'Bootstrap source not verified')
    need(bootstrap['test_head'] == expected['test_head'] and bootstrap['test_tree'] == expected['test_tree'], 'Test pin mismatch')
    need(bootstrap['tool_head'] == os.environ['TOOL_HEAD'], 'Tool event pin mismatch')
    need(bootstrap['test_files'] == {
        k: {'sha256': v['sha256'], 'bytes': v['bytes']} for k, v in expected['source_files'].items()
    } and len(bootstrap['test_files']) == 809, '809-file frozen raw ledger mismatch')
    tools = Path(bootstrap['tool_root']).absolute()
    ordinary(tools)
    need(HERE == tools / 'docs/gateway/research/persistence/qualification47', 'Wrong tool origin')
    need(physical(target) == bootstrap['test_files'], 'Raw test source changed/extras')
    need(physical(tools) == bootstrap['tool_files'], 'Raw tool source changed/extras')
    need(len(expected['node_ids']) == len(set(expected['node_ids'])) == 47, 'Frozen inventory invalid')
    report = read_json(evidence / 'pip-install.json')
    locked = {w['name'].lower(): w for w in expected['wheels']}
    acquired = {}
    for item in report['install']:
        name = item['metadata']['name'].lower()
        need(name in locked and name not in acquired, 'Unexpected/duplicate acquisition')
        pin = locked[name]
        info = item['download_info']
        need(item['metadata']['version'] == pin['version'] and info['url'] == pin['url'], 'Wheel origin/version mismatch')
        need(info['archive_info']['hashes']['sha256'] == pin['sha256'], 'Acquisition wheel hash mismatch')
        acquired[name] = {'version': pin['version'], 'filename': pin['filename'], 'sha256': pin['sha256']}
    need(set(acquired) == set(locked), 'Six-wheel acquisition closure incomplete')
    state = {
        'schema': 'agent7.hosted.sqlite47.candidate.v1', 'classification': 'UNIT_FACTS_NOT_RUNTIME_ADMISSION',
        'test_head': expected['test_head'], 'test_tree': expected['test_tree'],
        'tool_head': bootstrap['tool_head'], 'tool_tree': bootstrap['tool_tree'],
        'bootstrap_sha256': digest(evidence / 'bootstrap.json'), 'expected_sha256': digest(HERE / 'expected47.json'),
        'requirements_sha256': digest(HERE / 'requirements.lock'), 'pip_report_sha256': digest(evidence / 'pip-install.json'),
        'wheel_acquisition': acquired, 'release_wheel_qualification': 'NOT_CLAIMED',
        'source_pre': {'test_files': 809, 'tool_files': len(bootstrap['tool_files']), 'raw_git_match': True},
        'python': {'executable': sys.executable, 'sha256': digest(Path(sys.executable)), 'version': sys.version},
        'runner': {k: os.environ.get(k) for k in ('RUNNER_OS', 'RUNNER_ARCH', 'ImageOS', 'ImageVersion', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT')},
        'phase_reports': [], 'creation_intents': [], 'held_children': [], 'errors': [],
        'cleanup_uncertain': False, 'network_guard': 'AUDIT_GUARD_NOT_SECURITY_CONTAINMENT',
        'deadline_claim': 'NO_STRICT_GLOBAL180; hosted job timeout is separate cancellation policy',
        'native_admission': False, 'physical_admission': False, 'publication': 'NONE',
    }
    return expected, bootstrap, tools, state


def junit_facts(path, ids):
    doc = ET.parse(path).getroot()
    suites = doc.findall('testsuite') if doc.tag == 'testsuites' else [doc]
    need(suites and all(s.tag == 'testsuite' for s in suites), 'Invalid JUnit root')
    cases = [c for s in suites for c in s.findall('testcase')]
    actual = [(c.attrib.get('classname'), c.attrib.get('name')) for c in cases]
    wanted = [(node.split('::')[0][:-3].replace('/', '.'), node.split('::')[1]) for node in ids]
    counts = {key: sum(int(s.attrib[key]) for s in suites) for key in ('tests', 'failures', 'errors', 'skipped')}
    need(counts == {'tests': 47, 'failures': 0, 'errors': 0, 'skipped': 0}, 'JUnit failure/skip/count')
    need(len(actual) == len(set(actual)) == 47 and set(actual) == set(wanted), 'JUnit identities differ')
    need(not any(c.find(k) is not None for c in cases for k in ('failure', 'error', 'skipped')), 'JUnit error elements')
    return {'counts': counts, 'unique': 47, 'sha256': digest(path)}


def run(args):
    target, deps, evidence, namespace = layout(args)
    need(all(absent(evidence / x) for x in ('run-claim.json', 'candidate.json', 'pytest.xml', 'pytest.log')), 'Lane already used')
    need(absent(namespace / 'test-temp'), 'Test temp already exists')
    write_new(evidence / 'run-claim.json', {'run': os.environ['GITHUB_RUN_ID'], 'attempt': os.environ['GITHUB_RUN_ATTEMPT']})
    state = {'schema': 'agent7.hosted.sqlite47.precondition-failure.v1', 'errors': []}
    held = []
    pending = None
    stopped = False
    original_popen = subprocess.Popen
    initial_threads = {t.ident for t in threading.enumerate()}
    started = time.monotonic()
    try:
        expected, bootstrap, tools, state = preflight(target, deps, evidence)
        need(os.environ.get('PYTEST_DISABLE_PLUGIN_AUTOLOAD') == '1' and not os.environ.get('PYTEST_ADDOPTS')
             and not os.environ.get('PYTEST_PLUGINS'), 'External pytest configuration prohibited')
        deps_pre = installed_files(deps)
        state['installed_file_hashes_pre'] = deps_pre
        sys.path[:0] = [str(deps), str(target)]
        distributions = list(importlib.metadata.distributions(path=[str(deps)]))
        versions = {d.metadata['Name'].lower(): d.version for d in distributions}
        need(len(distributions) == len(versions) == 6 and versions == {w['name']: w['version'] for w in expected['wheels']}, 'Installed closure mismatch')
        # These imports are solely from the hash-recorded acquired dependency root.
        from packaging.requirements import Requirement
        from packaging.specifiers import SpecifierSet
        for dist in distributions:
            need(SpecifierSet(dist.metadata.get('Requires-Python', '')).contains('3.12.10'), 'Requires-Python mismatch')
            for text in dist.requires or ():
                req = Requirement(text)
                if req.marker is None or req.marker.evaluate({'extra': ''}):
                    need(req.name.lower() in versions and req.specifier.contains(versions[req.name.lower()]), 'Unsatisfied dependency')
        import pytest
        for name in ('pytest', '_pytest', 'packaging', 'pluggy', 'iniconfig', 'pygments', 'colorama'):
            module = __import__(name)
            need(Path(module.__file__).absolute().is_relative_to(deps), 'Dependency import escaped acquired root')
        temp = namespace / 'test-temp'
        helper = target / 'tests/research/gateway_artifact_persistence/crash_projection_stage_child.py'
        real = Path(sys.executable).absolute()

        class OwnedPopen(original_popen):
            def __init__(self, command, *positional, **kwargs):
                nonlocal pending, stopped
                need(not stopped and threading.current_thread() is threading.main_thread(), 'Creation stopfence/thread')
                index = len(state['creation_intents'])
                need(index < 3 and type(command) is list and len(command) == 8
                     and all(type(x) is str for x in command), 'Only three fixed Python child commands')
                need(not positional and set(kwargs) == {'stdout', 'stderr', 'creationflags'}, 'No cwd/env/shell override')
                need(kwargs['stdout'] == subprocess.PIPE and kwargs['stderr'] == subprocess.PIPE
                     and kwargs['creationflags'] == subprocess.CREATE_NO_WINDOW, 'Child pipe/window restrictions')
                need(Path.cwd() == target and Path(command[0]) == real
                     and command[1:4] == ['-I', '-S', '-B'] and Path(command[4]) == helper, 'Exact child origin required')
                need(command[5] == CHILD_PHASES[index], 'Child phase/order mismatch')
                db, marker = map(Path, command[6:])
                need(all(p.is_absolute() and '..' not in p.parts and p.is_relative_to(temp) for p in (db, marker))
                     and db.parent == marker.parent and db.name == 'own.sqlite' and marker.name == 'phase.marker', 'Own fixed child paths required')
                intent = {'index': index, 'phase': command[5], 'status': 'CREATION_PENDING', 'started_seconds': time.monotonic() - started}
                state['creation_intents'].append(intent)
                need(pending is None, 'Pending creation already exists')
                pending = (threading.get_ident(), index, subprocess.list2cmdline(command))
                try:
                    super().__init__(command, **kwargs)
                    # Returned handle enters the cleanup registry immediately,
                    # before any post-constructor invariant can refuse it.
                    held.append(self)
                    intent['status'] = 'HELD'
                    state['held_children'].append({'pid': self.pid, 'intent_index': index, 'identity': 'OWNED_POPEN_HANDLE', 'creation_returned_seconds': time.monotonic() - started})
                    need(pending is None, 'Audit allowance not consumed')
                except BaseException:
                    stopped = True
                    intent.update(status='UNKNOWN', error=traceback.format_exc())
                    state['cleanup_uncertain'] = True
                    raise
                finally:
                    pending = None

        def audit(event, values):
            nonlocal pending
            if event.startswith('socket.'):
                need(event == 'socket.gethostname' and values == (), 'Socket/network/DNS event prohibited')
                state['hostname_metadata_events'] = state.get('hostname_metadata_events', 0) + 1
            if event == 'subprocess.Popen':
                allowance, pending = pending, None
                need(allowance is not None and len(values) == 4, 'No pending exact Popen allowance')
                executable, command, cwd, env = values
                thread, index, expected_command = allowance
                need(thread == threading.get_ident() and index == len(state['creation_intents']) - 1
                     and type(command) is str and command == expected_command and cwd is None and env is None, 'Windows Popen exact allowance mismatch')
                need(executable is None or (type(executable) is str and Path(executable) == real), 'Wrong explicit executable')
                state.setdefault('consumed_allowances', []).append(index)

        subprocess.Popen = OwnedPopen
        sys.addaudithook(audit)

        class Reports:
            def pytest_collection_modifyitems(self, session, config, items):
                ids = [item.nodeid for item in items]
                state['collected_ids'] = ids
                if len(ids) != len(set(ids)) or sorted(ids) != sorted(expected['node_ids']):
                    raise pytest.UsageError('Exact 47-case inventory mismatch')

            def pytest_runtest_logreport(self, report):
                record = {'id': report.nodeid, 'phase': report.when, 'outcome': report.outcome, 'duration_seconds': report.duration}
                if report.longrepr is not None:
                    record['longrepr'] = str(report.longrepr)
                state['phase_reports'].append(record)

        argv = [*FILES, '-q', '-rs', '-p', 'no:cacheprovider', '-c', str(target / 'pyproject.toml'),
                '--confcutdir=' + str(target), '--basetemp=' + str(temp), '--junitxml=' + str(evidence / 'pytest.xml')]
        state['pytest_args'] = argv
        os.chdir(target)
        with (evidence / 'pytest.log').open('x', encoding='utf-8') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            state['pytest_exit_code'] = int(pytest.main(argv, plugins=[Reports()]))
    except BaseException:
        state['errors'].append(traceback.format_exc())
    finally:
        stopped = True
        subprocess.Popen = original_popen
        state['stopfence'] = True
        for child in held:
            try:
                if child.poll() is None:
                    state['cleanup_required'] = True
                    child.kill()
                    child.wait(timeout=2)
            except BaseException:
                state['cleanup_uncertain'] = True
                state['errors'].append(traceback.format_exc())
        for child, record in zip(held, state.get('held_children', [])):
            try:
                record.update(returncode=child.poll(), retired=child.poll() is not None)
            except BaseException:
                state['cleanup_uncertain'] = True
                state['errors'].append(traceback.format_exc())
        remaining, unknown = 0, 0
        for child in held:
            try:
                remaining += child.poll() is None
            except BaseException:
                unknown += 1
                state['cleanup_uncertain'] = True
                state['errors'].append(traceback.format_exc())
        state['remaining_held_children'] = remaining
        state['unknown_held_children'] = unknown
        state['pending_or_unknown_creation'] = any(x['status'] != 'HELD' for x in state.get('creation_intents', []))
        state['remaining_new_threads'] = [{'name': t.name, 'ident': t.ident} for t in threading.enumerate() if t.ident not in initial_threads and t.is_alive()]
        for key, action in (
            ('source_post', lambda: {'test': physical(target), 'tool': physical(tools)}),
            ('installed_file_hashes_post', lambda: installed_files(deps)),
            ('junit', lambda: junit_facts(evidence / 'pytest.xml', expected['node_ids'])),
        ):
            try:
                state[key] = action()
            except BaseException:
                state['errors'].append(key + ': ' + traceback.format_exc())
        try:
            origins = {}
            for name, module in tuple(sys.modules.items()):
                filename = getattr(module, '__file__', None)
                if filename and Path(filename).absolute().is_relative_to(target):
                    origins[name] = Path(filename).absolute().relative_to(target).as_posix()
            state['source_import_origins'] = origins
            need(set(origins.values()).issubset(set(expected['allowed_source_imports'])), 'Unexpected test/source import')
            for name in ('strattester.persistence.result_store', 'strattester.research.result_persistence'):
                need(origins.get(name) == name.replace('.', '/') + '.py', 'Research module origin mismatch')
        except BaseException:
            state['errors'].append('source_import_origins: ' + traceback.format_exc())
        state['measured_before_candidate_write_seconds'] = time.monotonic() - started
        state['candidate_persistence_proven'] = False
        # No PASS decision here: a separate process must read back closed evidence.
        write_new(evidence / 'candidate.json', state)
    return 0 if state.get('pytest_exit_code') == 0 and not state['errors'] else 1


def verify(args):
    target, deps, evidence, namespace = layout(args)
    need(absent(evidence / 'terminal.json'), 'Terminal observation already exists')
    terminal = {'classification': 'FAIL_OR_UNKNOWN', 'native_admission': False, 'physical_admission': False}
    try:
        expected, bootstrap, tools, _ = preflight(target, deps, evidence)
        candidate = read_json(evidence / 'candidate.json')
        need(candidate['schema'] == 'agent7.hosted.sqlite47.candidate.v1', 'Precondition failure candidate')
        need(candidate['test_head'] == expected['test_head'] and candidate['test_tree'] == expected['test_tree']
             and candidate['tool_head'] == bootstrap['tool_head'] and candidate['tool_tree'] == bootstrap['tool_tree'], 'Candidate source pins differ')
        need(candidate['bootstrap_sha256'] == digest(evidence / 'bootstrap.json')
             and candidate['expected_sha256'] == digest(HERE / 'expected47.json')
             and candidate['requirements_sha256'] == digest(HERE / 'requirements.lock')
             and candidate['pip_report_sha256'] == digest(evidence / 'pip-install.json'), 'Candidate provenance files changed')
        need(candidate['pytest_exit_code'] == 0 and not candidate['errors'] and candidate['stopfence'], 'Test/controller errors')
        need(candidate['python']['sha256'] == digest(Path(sys.executable)), 'Interpreter changed between steps')
        need(set(candidate['source_import_origins'].values()).issubset(set(expected['allowed_source_imports'])), 'Unexpected source import origin')
        need(not candidate['cleanup_uncertain'] and not candidate.get('cleanup_required')
             and not candidate['pending_or_unknown_creation'] and not candidate['remaining_held_children']
             and not candidate['unknown_held_children'] and not candidate['remaining_new_threads'], 'Retirement/cleanup not established')
        need(sorted(candidate['collected_ids']) == sorted(expected['node_ids']), 'Collection differs')
        records = candidate['phase_reports']
        need(len(records) == 141 and {(r['id'], r['phase']) for r in records} == {
            (node, phase) for node in expected['node_ids'] for phase in PHASES
        } and all(r['outcome'] == 'passed' for r in records), '141-phase outcome mismatch')
        need([x['phase'] for x in candidate['creation_intents']] == list(CHILD_PHASES)
             and all(x['status'] == 'HELD' for x in candidate['creation_intents'])
             and candidate['consumed_allowances'] == [0, 1, 2], 'Creation identities incomplete')
        children = candidate['held_children']
        need(len(children) == 3 and [x['intent_index'] for x in children] == [0, 1, 2]
             and [x['returncode'] for x in children] == [73, 74, 74] and all(x['retired'] for x in children), 'Child outcomes differ')
        need(candidate['source_post']['test'] == bootstrap['test_files']
             and candidate['source_post']['tool'] == bootstrap['tool_files'], 'Candidate source changed/extras')
        need(candidate['installed_file_hashes_pre'] == candidate['installed_file_hashes_post'] == installed_files(deps), 'Installed dependencies changed')
        need(junit_facts(evidence / 'pytest.xml', expected['node_ids']) == candidate['junit'], 'JUnit changed')
        terminal.update(classification='HOSTED_UNIT_QUALIFIED', test_head=expected['test_head'], test_tree=expected['test_tree'],
                        tool_head=bootstrap['tool_head'], tool_tree=bootstrap['tool_tree'], tests=47, phases=141, skips=0,
                        candidate_sha256=digest(evidence / 'candidate.json'), junit_sha256=digest(evidence / 'pytest.xml'),
                        finalization='SEPARATE_READBACK_OF_CLOSED_CANDIDATE', job_completion='NOT_OBSERVED_BY_THIS_PROCESS',
                        artifact_upload='NOT_OBSERVED_BY_THIS_PROCESS', vm_teardown='NOT_INDEPENDENTLY_OBSERVED')
    except BaseException:
        terminal['error'] = traceback.format_exc()
    write_new(evidence / 'terminal.json', terminal)
    print(json.dumps(terminal, sort_keys=True))
    return 0 if terminal['classification'] == 'HOSTED_UNIT_QUALIFIED' else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('run', 'verify'))
    parser.add_argument('--target', required=True)
    parser.add_argument('--deps', required=True)
    parser.add_argument('--evidence', required=True)
    args = parser.parse_args()
    return run(args) if args.command == 'run' else verify(args)


if __name__ == '__main__':
    sys.exit(main())
