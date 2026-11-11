"""Exact primary old15+new7 native profile-v2 source qualification; no job grants."""
raise RuntimeError('NATIVE_QUALIFICATION_PREREQUISITES_LOCKED')
import argparse,hashlib,json,os
from pathlib import Path
import re,subprocess,sys,types,unittest

def git(root,*args):return subprocess.check_output(['git','--no-replace-objects','-C',str(root),*args])
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--expected-head',required=True)
    parser.add_argument('--grid-source',required=True)
    parser.add_argument('--expected-grid-head',required=True)
    args=parser.parse_args()
    assert sys.flags.isolated and sys.dont_write_bytecode and sys.pycache_prefix is None
    script=Path(__file__).absolute();root=script.parents[4];grid=Path(args.grid_source).absolute()
    assert all(re.fullmatch('[0-9a-f]{40}',v) for v in (args.expected_head,args.expected_grid_head))
    raw=git(root,'show','f155126a95e80139b1b9679c1870ffd66c29360e:docs/intelligence/identity/run_qualification.py')
    assert hashlib.sha256(raw).hexdigest()=='e3733379da5e0cde84573f3279d265c91e16eceb8c94aeeda8983b51031216fe'
    guard=types.ModuleType('pinned_primary_guard');exec(compile(raw,'<pinned-primary-guard>','exec'),guard.__dict__)
    for ancestor in (script,*script.parents):guard.ordinary(ancestor)
    assert git(root,'rev-parse','HEAD').decode().strip()==args.expected_head
    assert git(grid,'rev-parse','HEAD').decode().strip()==args.expected_grid_head
    before=guard.inventory(root);grid_before=guard.inventory(grid)
    os.environ['A2_RESEARCH_GRID_SOURCE']=str(grid)
    sys.path[:0]=[str(root),str(root/'tests/gateway_research_identity')]
    suite=unittest.defaultTestLoader.discover(str(root/'tests/gateway_research_identity'),pattern='test_*.py')
    def ids(value):
        for item in value:
            if isinstance(item,unittest.TestSuite):yield from ids(item)
            else:yield item.id()
    actual=list(ids(suite));expected=json.loads((script.parent/'EXPECTED-TESTS.json').read_bytes())
    assert len(actual)==len(set(actual))==len(expected)==len(set(expected))==22
    assert sorted(actual)==sorted(expected)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert guard.inventory(root)==before and guard.inventory(grid)==grid_before
    assert result.wasSuccessful() and result.testsRun==22 and not result.skipped
    print(json.dumps(dict(result='PASS',scope='ACTUAL_DISPOSABLE_PROFILE_V2_PRINCIPAL_NOT_JOB_RESOURCE_DISPATCH_OR_STORAGE_GRANT',head=args.expected_head,tree=git(root,'rev-parse','HEAD^{tree}').decode().strip(),grid_head=args.expected_grid_head,raw_files=len(before),grid_raw_files=len(grid_before),tests=22,skips=0,exact_unique_ids=True,module_sha256=before['unified_system/gateway_research_identity.py'],read840_unchanged=before['unified_system/gateway_identity.py']=='84093865e8477ef6562100d41137922785446c9cb4e024c9ba7105593a2b36c1')))
if __name__=='__main__':main()
