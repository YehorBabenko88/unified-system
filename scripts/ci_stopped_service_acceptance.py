"""Disposable GitHub Windows stopped-service test; never an office installer.

The capsule is explicitly synthetic and grants no runtime/source authenticity.
No service start, activation, force cleanup or policy change exists in this lane.
Failures retain interrupted resources for the disposable VM's eventual removal.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import ssl
import subprocess
import sys
import time
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from unified_system import installation_service as service, lab_release, windows_toolchain
from unified_system.installation_uninstall import Uninstaller, WindowsRemovalBoundary
from unified_system.lab_capsule_acl import FreshCodeRoot, _safe
from scripts import prepare_lab_capsule as builder
from tests.test_lab_release import fixture

ERROR = 'CI_STOPPED_SERVICE_REJECTED'
ENTRY_BYTES = 2477
BOOTSTRAP_BYTES = 25043


def need(value):
    if not value:
        raise ValueError(ERROR)


def admit_context(root, env, system, computer_name):
    """Pure predicate; main supplies GetComputerNameW, never COMPUTERNAME env."""
    need(system == 'win32' and env.get('GITHUB_ACTIONS') == 'true'
         and env.get('RUNNER_ENVIRONMENT') == 'github-hosted' and env.get('RUNNER_OS') == 'Windows')
    need(type(computer_name) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,255}', computer_name))
    normalized = re.sub('[^A-Za-z0-9]', '', computer_name).upper()
    need(not any(label in normalized for label in ('ADMINIT', 'LS5', 'LS7', 'PC1', 'PC2', 'PC3', 'PC4')))
    need(bool(env.get('RUNNER_TEMP')))
    temporary = _safe(env['RUNNER_TEMP'])
    root = _safe(root)
    need(temporary.is_dir() and temporary in root.parents and root.parent == temporary)
    need(not root.exists())
    return dict(root=root, temporary=temporary, computer_name=computer_name)


def safe_url(url, host):
    need(type(url) is str and len(url) <= 2048 and not re.search(r'[\x00-\x20\x7f\\]', url))
    parsed = urlsplit(url)
    need(parsed.scheme == 'https' and parsed.hostname == host and parsed.port is None
         and parsed.username is None and parsed.password is None and not parsed.query and not parsed.fragment)


class SameHostRedirect(HTTPRedirectHandler):
    def __init__(self, host):
        self.host, self.count = host, 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.count += 1
        need(self.count <= 3)
        safe_url(newurl, self.host)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_archive(artifact, target, *, opener=None):
    """TLS plus fixed same-host redirects, byte cap and exact archive digest."""
    safe_url(artifact['url'], 'www.nssm.cc')
    need(type(artifact['max_bytes']) is int and 0 < artifact['max_bytes'] <= 16 * 1024 * 1024)
    need(re.fullmatch('[a-f0-9]{64}', artifact['sha256']) is not None)
    target = _safe(target)
    need(target.parent.is_dir() and not target.exists())
    if opener is None:
        opener = build_opener(SameHostRedirect('www.nssm.cc'), HTTPSHandler(context=ssl.create_default_context()))
    started, total, digest = time.monotonic(), 0, hashlib.sha256()
    with opener.open(Request(artifact['url'], headers={'User-Agent': 'UnifiedStoppedServiceCI/1'}), timeout=15) as response:
        safe_url(response.geturl(), 'www.nssm.cc')
        length = response.headers.get('Content-Length')
        if length is not None:
            need(re.fullmatch('[0-9]{1,10}', length) is not None and 0 < int(length) <= artifact['max_bytes'])
        with target.open('xb') as output:
            while True:
                need(time.monotonic() - started < 75)
                block = response.read(min(65536, artifact['max_bytes'] - total + 1))
                if not block:
                    break
                total += len(block)
                need(total <= artifact['max_bytes'])
                output.write(block)
                digest.update(block)
            output.flush()
            os.fsync(output.fileno())
    need(total > 0 and (length is None or total == int(length)))
    need(artifact['expected_bytes'] is None or total == artifact['expected_bytes'])
    need(digest.hexdigest() == artifact['sha256'])
    return dict(url=artifact['url'], bytes=total, sha256=digest.hexdigest(), transport='HTTPS_SAME_HOST_FIXED_PIN')


def staged_archive(artifact, target, source, temporary):
    """A separately pinned CI transport may supply identical bytes, never trust."""
    source = lab_release.regular(source)
    need(source.parent == _safe(temporary))
    target = _safe(target)
    need(target.parent.is_dir() and not target.exists())
    need(type(artifact['max_bytes']) is int and 0 < artifact['max_bytes'] <= 16*1024*1024)
    with source.open('rb') as stream:
        raw = stream.read(artifact['max_bytes']+1)
    need(0 < len(raw) <= artifact['max_bytes'])
    need(artifact['expected_bytes'] is None or len(raw) == artifact['expected_bytes'])
    need(hashlib.sha256(raw).hexdigest() == artifact['sha256'])
    # Validate before any destination write; package scripts are never run.
    with target.open('xb') as output:
        output.write(raw); output.flush(); os.fsync(output.fileno())
    return dict(bytes=len(raw), sha256=artifact['sha256'],
                transport='PRESTAGED_EXACT_BYTES_NOT_PUBLISHER_TRUST')


class PhaseGuard:
    def __init__(self):
        self.plans, self.calls = {}, []

    def admit(self, digest, actions):
        need(re.fullmatch('[a-f0-9]{64}', digest) is not None)
        self.plans[digest] = frozenset(actions)

    def __call__(self, action, digest):
        permitted = action in self.plans.get(digest, ())
        self.calls.append(dict(action=action, plan_sha256=digest, permitted=permitted))
        return permitted


def source_identity(expected):
    need(re.fullmatch('[a-f0-9]{40}', expected) is not None)
    git = shutil.which('git')
    need(git is not None)
    def read(*arguments):
        result = subprocess.run([git, '-C', str(REPO), *arguments], capture_output=True, timeout=15)
        need(result.returncode == 0 and len(result.stdout) <= 65536 and len(result.stderr) <= 65536)
        return result.stdout.decode('ascii').strip()
    head, tree = read('rev-parse', 'HEAD'), read('rev-parse', 'HEAD^{tree}')
    need(head == expected and re.fullmatch('[a-f0-9]{40}', tree) and read('status', '--porcelain', '--untracked-files=normal') == '')
    version = read('--version')
    need(re.fullmatch(r'git version [A-Za-z0-9.+-]{1,80}', version) is not None)
    return dict(head=head, tree=tree, checkout='EXACT_HEAD_CLEAN', git_version=version,
                script_sha256=lab_release.hash_file(Path(__file__))['sha256'])


def source_blob(expected,member_name):
    allowed={'service_entry.py':(ENTRY_BYTES,service.SERVICE_ENTRY_SHA256),'service_bootstrap.py':(BOOTSTRAP_BYTES,service.SERVICE_BOOTSTRAP_SHA256)}
    need(member_name in allowed);size_bound,pin=allowed[member_name]
    need(source_identity(expected)['head'] == expected)
    git = shutil.which('git');need(git is not None)
    path='unified_system/'+member_name;member=expected+':'+path
    arguments=[git,'-C',str(REPO),'cat-file']
    size=subprocess.check_output([*arguments,'-s',member],stderr=subprocess.DEVNULL,timeout=15)
    need(size.strip()==str(size_bound).encode('ascii'))
    raw=subprocess.check_output([*arguments,'blob',member],stderr=subprocess.DEVNULL,timeout=15)
    need(len(raw)==size_bound and hashlib.sha256(raw).hexdigest()==pin)
    return raw,dict(origin='EXACT_HEAD_GIT_BLOB',head=expected,path=path,bytes=len(raw),sha256=pin)


def entry_blob(expected):return source_blob(expected,'service_entry.py')
def bootstrap_blob(expected):return source_blob(expected,'service_bootstrap.py')


def make_capsule(root, payload, expected):
    need(hashlib.sha256(payload).hexdigest() == builder.NSSM_MEMBER_SHA256 == service.NSSM_PIN)
    entry, origin = entry_blob(expected)
    bootstrap,bootstrap_origin=bootstrap_blob(expected);origin={**origin,'bootstrap':bootstrap_origin}
    root.mkdir()
    manifest = fixture(root)
    manifest['dependencies'][0]['version'] = platform.python_version()
    additions = {'runtime/nssm/nssm.exe': payload,
                 'runtime/python/python.exe': lab_release.regular(sys.executable).read_bytes(),
                 'sources/unified-system/unified_system/owned_python.py': (REPO/'unified_system/owned_python.py').read_bytes(),
                 'sources/unified-system/unified_system/service_entry.py': entry,
                 'sources/unified-system/unified_system/service_bootstrap.py': bootstrap}
    for relative, raw in additions.items():
        path = root/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    manifest['files'], manifest['directories'] = builder.inventory(root)
    raw = lab_release.canonical(manifest)
    with (root/'lab-release.json').open('xb') as stream:
        stream.write(raw)
    pin = hashlib.sha256(raw).hexdigest()
    lab_release.verify_capsule(root, pin)
    return pin, {name: lab_release.hash_file(root/name) for name in additions}, origin


def publish_owned_reports(context):
    """Only an admitted fresh namespace may enable the failure artifact step."""
    output = _safe(os.environ['GITHUB_OUTPUT'])
    need(context['temporary'] in output.parents and output.is_file())
    facts = output.stat()
    need(facts.st_nlink == 1 and facts.st_size <= 65536)
    with output.open('a', encoding='utf8') as stream:
        stream.write('report_root_owned=true\n')


def read_tool_versions(plan):
    tool = plan['native_tools']['powershell']
    need(service._native_hash(tool['path']) == tool['sha256'])
    output, status = service._run([tool['path'], '-NoProfile', '-NonInteractive', '-Command',
                                  '$PSVersionTable.PSVersion.ToString()'],
                                 env=service._environment(), timeout=10, limit=8192)
    need(status == 0 and re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,3}', output.strip()) is not None)
    return dict(python=platform.python_version(), powershell=output.strip(), windows=platform.version(),
                nssm_catalog_archive=builder.NSSM_FILENAME, python_leaf_executed=False)


def execute_lane(context, expected):
    # Re-admit OS identity immediately before the first fresh-directory effect.
    context = admit_context(context['root'], os.environ, sys.platform, service.current_computer_name())
    report = dict(schema='unified.ci-stopped-service.v1', result='FAIL', scope='DISPOSABLE_HOSTED_STOPPED_SERVICE_ONLY',
                  input='SYNTHETIC_TEST_INPUT', source_proof='NOT_EVALUATED', activation='BLOCKED', service_start='NOT_RUN',
                  physical='NOT_RUN', installation_closure=False, publisher_authenticated=False, execution_authority=False,
                  computer_name=context['computer_name'], python_version=platform.python_version(), stages=[], error_code=None)
    stage, reports, guard = 'source', None, PhaseGuard()
    try:
        report['test_source'] = source_identity(expected)
        stage = 'private_parent'
        owned = FreshCodeRoot.create(context['root'])
        need(owned._owned() == context['root'])
        reports = context['root']/'reports'
        reports.mkdir()
        publish_owned_reports(context)
        stage = 'download'
        catalog = windows_toolchain.read_catalog()
        artifact = next(item for item in catalog['artifacts'] if item['component'] == 'nssm')
        archive = context['root']/artifact['filename']
        staged = os.environ.get('CI_PINNED_NSSM_ARCHIVE')
        report['archive'] = (staged_archive(artifact, archive, staged, context['temporary'])
                             if staged else download_archive(artifact, archive))
        payload, report['nssm'] = builder.nssm_payload(archive)
        stage = 'synthetic_capsule'
        capsule = context['root']/'synthetic-capsule'
        pin, report['capsule_leaves'], report['entry_origin'] = make_capsule(capsule, payload, expected)
        report['capsule_manifest_sha256'] = pin
        boundary = service.WindowsServiceBoundary()
        install_id = 'ci-' + hashlib.sha256(str(context['root']).encode()).hexdigest()[:24]
        plan = service.service_plan(capsule, pin, context['root']/'stopped-resource', install_id, 'hosted-ci', 'CONTROL', boundary)
        report['service_plan_sha256'], report['native_tools'] = plan['plan_sha256'], plan['native_tools']
        report['tool_versions'] = read_tool_versions(plan)
        report['service_name'], report['service_sid'] = plan['service_name'], plan['service_sid']
        guard.admit(plan['plan_sha256'], {'BEGIN','WRITE_RECEIPT','STAGE','SEAL','REGISTER','INSPECT'})
        stage = 'create_stopped'
        report['nssm']['native_execution'] = 'ATTEMPTED_CONFIGURATION_ONLY'
        resource = service.ServiceResource.create(plan, boundary, guard)
        stage = 'inspect_stopped'
        inspected = resource.inspect(guard)
        need(inspected['activation'] == 'BLOCKED' and inspected['status'] == 'STOPPED_RESOURCE_RECORDED')
        record = resource.recorded()
        need(record['proof']['state'] == 1 and record['proof']['start_type'] == 3 and record['proof']['sid_type'] == 1)
        need(record['proof']['account'] == 'NT AUTHORITY\\LocalService')
        report['stopped_proof'] = record['proof']
        report['nssm']['native_execution'] = 'CONFIGURATION_GET_SET_ONLY_NO_SERVICE_START'
        report['stages'].append(dict(stage='native_create_inspect', result='PASS'))
        state = Path(plan['state'])/'preserved-fixture.bin'
        state.write_bytes(b'SYNTHETIC_TEST_INPUT_PRESERVE_STATE')
        state_hash = lab_release.hash_file(state)
        ownership = Path(plan['root'])/'ownership/service.sqlite'
        ownership_hash = lab_release.hash_file(ownership)
        uninstaller = Uninstaller(resource, WindowsRemovalBoundary())
        preview = uninstaller.preview()
        need(preview['mode'] == 'APP_ONLY' and preview['service_plan_sha256'] == plan['plan_sha256'])
        report['uninstall_plan_sha256'] = preview['plan_sha256']
        guard.admit(preview['plan_sha256'], {'WRITE_RECEIPT','INSPECT_SERVICE','REMOVE_SERVICE','OBSERVE_SERVICE','REMOVE_CODE','ADMIT_REMOVAL'})
        stage = 'blocked_modes'
        for mode in ('REMOVE_CONFIG','FULL'):
            calls = len(guard.calls)
            try:
                uninstaller.run(mode=mode, guard=guard)
            except ValueError:
                pass
            else:
                need(False)
            need(len(guard.calls) == calls)
        stage = 'app_only_removal'
        removed = uninstaller.run(guard=guard)
        need(removed['status'] == 'APP_ONLY_REMOVED' and removed['state'] == 'PRESERVED_NO_CONTENT_ASSERTION')
        need(not _safe(plan['code']).exists())
        need(lab_release.hash_file(state) == state_hash and lab_release.hash_file(ownership) == ownership_hash)
        need(uninstaller.audit.path.is_file() and resource.recorded() == record)
        # A complete rerun freshly observes SCM absence; it never deletes again.
        need(uninstaller.run(guard=guard)['status'] == 'APP_ONLY_REMOVED')
        report['stages'].append(dict(stage='native_app_only_remove', result='PASS', scm='ABSENT', code='ABSENT', state='RETAINED', ownership='RETAINED', uninstall_journal='RETAINED'))
        report['preserved_state_sha256'] = state_hash['sha256']
        report['test_source_after'] = source_identity(expected)
        need(report['test_source_after'] == report['test_source'])
        report['result'], stage = 'PASS_COMPONENT_STOPPED_SERVICE_ONLY', None
    except (Exception, KeyboardInterrupt) as exc:
        report['error_code'] = 'INTERRUPTED' if isinstance(exc, KeyboardInterrupt) else 'CLOSED_STAGE_FAILURE'
        if isinstance(exc,service.OwnedServiceRejected):
            report['native_stage']=exc.native_stage
            report['native_exit_code']=exc.native_exit_code
    report['failure_stage'], report['phase_calls'] = stage, guard.calls
    if reports is not None:
        try:
            raw = lab_release.canonical(report)
            with (reports/'report.json').open('xb') as stream:
                stream.write(raw)
            manifest = dict(files=[dict(path='report.json', sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))])
            with (reports/'manifest.json').open('xb') as stream:
                stream.write(lab_release.canonical(manifest))
        except (OSError, ValueError):
            report['result'], report['error_code'] = 'FAIL', 'EVIDENCE_WRITE_FAILED'
    else:
        report['result'] = 'FAIL'
    print(json.dumps({key: report[key] for key in ('result','failure_stage','error_code','source_proof','activation','physical')}))
    return 0 if report['result'] == 'PASS_COMPONENT_STOPPED_SERVICE_ONLY' else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--expected-sha', required=True)
    args = parser.parse_args(argv)
    try:
        need(sys.platform == 'win32' and os.environ.get('GITHUB_ACTIONS') == 'true'
             and os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted' and os.environ.get('RUNNER_OS') == 'Windows')
        context = admit_context(args.root, os.environ, sys.platform, service.current_computer_name())
        return execute_lane(context, args.expected_sha)
    except (Exception, KeyboardInterrupt):
        print(json.dumps(dict(result='FAIL', error_code='CI_GUARD_REJECTED', physical='NOT_RUN', activation='BLOCKED')))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
