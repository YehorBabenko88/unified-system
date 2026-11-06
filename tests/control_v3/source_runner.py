"""Primary Git/raw-byte source proof and exact offline/loopback fixture inventory.

No provider/Consul/native or physical qualification. Evidence lives outside source.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET


def git(root,*args,input=None):
    env=os.environ.copy()
    env.update(GIT_NO_REPLACE_OBJECTS='1',GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_COUNT='0')
    return subprocess.check_output(['git','--no-replace-objects','-c','core.fsmonitor=false',*args],
        cwd=root,env=env,input=input,timeout=30)


def verify(root,expected):
    root=Path(root).resolve()
    head=git(root,'rev-parse','HEAD').decode().strip()
    if head!=expected or git(root,'rev-parse','--show-object-format').strip()!=b'sha1':raise ValueError('PRIMARY_HEAD_MISMATCH')
    tracked=set();hashes={};total=0
    for item in filter(None,git(root,'ls-tree','-r','-z','HEAD').split(b'\0')):
        meta,name=item.split(b'\t',1);mode,kind,oid=meta.split();name=name.decode('utf-8')
        if mode not in (b'100644',b'100755') or kind!=b'blob':raise ValueError('NONREGULAR_SOURCE')
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('INVALID_SOURCE_PATH')
        path=root/relative
        for ancestor in (path,*path.parents):
            if ancestor==root.parent:break
            if ancestor.is_symlink():raise ValueError('SYMLINK_SOURCE')
        if not path.is_file() or path.stat().st_size>16*1024**2:raise ValueError('SOURCE_BOUND')
        data=path.read_bytes();total+=len(data)
        if total>256*1024**2 or len(tracked)>=10000:raise ValueError('SOURCE_TREE_BOUND')
        if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=oid.decode():raise ValueError('RAW_BLOB_MISMATCH:'+name)
        tracked.add(name);hashes[name]=hashlib.sha256(data).hexdigest()
    for folder,dirs,names in os.walk(root,followlinks=False):
        dirs[:]=[d for d in dirs if not (Path(folder)==root and d=='.git')]
        if any((Path(folder)/d).is_symlink() for d in dirs):raise ValueError('UNTRACKED_SYMLINK')
        for name in names:
            path=Path(folder)/name;relative=path.relative_to(root).as_posix()
            if relative=='.git':continue
            if relative not in tracked or path.is_symlink():raise ValueError('UNEXPECTED_SOURCE:'+relative)
    return dict(head=head,tree=git(root,'rev-parse','HEAD^{tree}').decode().strip(),
        raw_inputs=hashes,raw_bytes=total,git_replace='EXPLICITLY_DISABLED_ALL_CALLS',
        scope='INTERNAL_SOURCE_AND_SYNTHETIC_LOOPBACK_FIXTURE_ONLY',runtime_admission=False)


def build_junit(result,ids):
    xml=ET.Element('testsuite',tests=str(result.testsRun),failures=str(len(result.failures)),
                   errors=str(len(result.errors)),skipped=str(len(result.skipped)))
    cases={}
    for testid in ids:
        cls,method=testid.rsplit('.',1)
        cases[testid]=ET.SubElement(xml,'testcase',classname=cls,name=method)
    for tag,items in (('failure',result.failures),('error',result.errors),('skipped',result.skipped)):
        for test,detail in items:
            testid=getattr(test,'test_case',test).id()
            if testid not in cases:
                cls,method=testid.rsplit('.',1)
                cases[testid]=ET.SubElement(xml,'testcase',classname=cls,name=method)
            ET.SubElement(cases[testid],tag).text=detail
    return xml


def report_format_selftest():
    class Controlled(unittest.TestCase):
        def test_pass(self):pass
        def test_fail(self):self.fail('controlled formatter failure')
        def test_error(self):raise RuntimeError('controlled formatter error')
        @unittest.skip('controlled formatter skip')
        def test_skip(self):pass
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Controlled)
    ids=[t.id() for t in suite];result=unittest.TestResult();suite.run(result)
    xml=build_junit(result,ids)
    assert len(xml.findall('testcase'))==4
    assert not any(xml.findall(tag) for tag in ('failure','error','skipped'))
    for method,tag in (('test_fail','failure'),('test_error','error'),('test_skip','skipped')):
        case=next(c for c in xml.findall('testcase') if c.get('name')==method)
        assert len(case.findall(tag))==1
    return dict(cases=4,controlled_failures=1,controlled_errors=1,controlled_skips=1,
                scope='JUNIT_FORMATTER_SELFTEST_ONLY_NOT_PRODUCT_RESULTS')


def run(root,expected,output):
    before=verify(root,expected)
    output=Path(output).resolve()
    if output==root or root in output.parents:raise ValueError('EVIDENCE_MUST_BE_OUTSIDE_SOURCE')
    output.mkdir(parents=True,exist_ok=False)
    (output/'source-before.json').write_bytes((json.dumps(before,indent=2)+'\n').encode())
    sys.path.insert(0,str(root))
    from tests.control_v3.inventory import EXPECTED_IDS
    loader=unittest.TestLoader();suite=unittest.TestSuite(loader.loadTestsFromName(n) for n in EXPECTED_IDS)
    class RecordingResult(unittest.TextTestResult):
        def startTest(self,test):
            executed.append(test.id());super().startTest(test)
    executed=[]
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=RecordingResult).run(suite)
    text=stream.getvalue();(output/'tests.log').write_bytes(text.encode())
    after=verify(root,expected)
    assert before==after
    report=dict(after,tests=result.testsRun,expected_ids=list(EXPECTED_IDS),executed_ids=executed,
        failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        python=sys.version,log_sha256=hashlib.sha256(text.encode()).hexdigest(),
        http='OWNED_EPHEMERAL_LOOPBACK_PLAIN_HTTP_ONLY',native_identity='UNAVAILABLE',real_consul='NOT_RUN')
    (output/'source-after.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    xml=build_junit(result,executed)
    ET.ElementTree(xml).write(output/'tests.xml',encoding='utf-8',xml_declaration=True)
    print(text,end='')
    assert len(EXPECTED_IDS)==len(set(EXPECTED_IDS))==result.testsRun==46
    assert executed==list(EXPECTED_IDS)
    assert result.wasSuccessful() and not result.skipped


def probes(root,expected,scratch):
    root=Path(root).resolve();scratch=Path(scratch).resolve()
    scratch.mkdir(parents=True,exist_ok=False);clone=scratch/'independent-clone'
    git(root,'-c','core.autocrlf=false','-c','core.eol=lf','clone','--no-hardlinks','--no-checkout',str(root),str(clone))
    git(clone,'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',expected)
    assert (clone/'.git').is_dir()
    assert git(clone,'rev-parse','--git-dir').strip()==git(clone,'rev-parse','--git-common-dir').strip()==b'.git'
    baseline=verify(clone,expected);path=clone/'unified_system/control_v3_read_adapter.py'
    original=path.read_bytes();changed=original+b'\n# isolated source-proof negative\n'
    blob=git(clone,'rev-parse',expected+':unified_system/control_v3_read_adapter.py').decode().strip()
    replacement=git(clone,'hash-object','-w','--stdin',input=changed).decode().strip()
    cases=[]
    def rejects(name):
        try:verify(clone,expected)
        except ValueError as exc:
            assert 'RAW_BLOB_MISMATCH' in str(exc);cases.append(dict(case=name,result='REJECTED_BEFORE_TESTS',reason=str(exc)))
        else:raise AssertionError(name)
    try:
        path.write_bytes(changed);git(clone,'update-index','--assume-unchanged','--',str(path.relative_to(clone)))
        rejects('HIDDEN_ASSUMED_UNCHANGED');git(clone,'update-index','--no-assume-unchanged','--',str(path.relative_to(clone)))
        git(clone,'replace',blob,replacement)
        rejects('BLOB_REPLACE');git(clone,'replace','-d',blob)
        git(clone,'add','--',str(path.relative_to(clone)))
        original_tree=git(clone,'rev-parse',expected+'^{tree}').decode().strip()
        replacement_tree=git(clone,'write-tree').decode().strip();git(clone,'replace',original_tree,replacement_tree)
        rejects('TREE_REPLACE');git(clone,'replace','-d',original_tree)
        path.write_bytes(original.replace(b'\n',b'\r\n'));rejects('RAW_CRLF')
    finally:
        path.write_bytes(original);git(clone,'update-index','--no-assume-unchanged','--',str(path.relative_to(clone)))
        for ref in git(clone,'for-each-ref','--format=%(refname)','refs/replace').decode().splitlines():git(clone,'update-ref','-d',ref)
        git(clone,'reset','--mixed',expected)
    assert verify(clone,expected)==baseline and not git(clone,'for-each-ref','refs/replace').strip()
    report=dict(head=expected,scope='SOURCE_PROOF_NEGATIVE_CONTROLS_ONLY',cases=cases,
        junit_formatter_selftest=report_format_selftest(),
        restored_raw_baseline=True,replace_refs_only_in=str(clone/'.git'),source_repo_refs_changed=False)
    (scratch/'evidence.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps(dict(negative_controls=len(cases),restored=True)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--expected',required=True)
    parser.add_argument('--output');parser.add_argument('--probe-scratch')
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    if args.probe_scratch:probes(root,args.expected,args.probe_scratch)
    elif args.output:run(root,args.expected,args.output)
    else:parser.error('output or probe-scratch required')
