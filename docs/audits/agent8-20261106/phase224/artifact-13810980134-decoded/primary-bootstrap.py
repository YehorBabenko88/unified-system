import hashlib, json, os, pathlib, re, stat, subprocess, sys
root = pathlib.Path(os.environ['GITHUB_WORKSPACE'])
out = pathlib.Path(os.environ['PREVIEW_EVIDENCE'])
facts = {'scope':'REVIEWED_WORKFLOW_BOOTSTRAP_NOT_TARGET_CODE_OR_OS_ATTESTATION','qualifier_load_attempted':False,'result':'FAIL'}
def ordinary(p, directory=False):
    p = pathlib.Path(p)
    if not p.is_absolute() or '..' in p.parts: raise RuntimeError('ABSOLUTE_PATH_REQUIRED')
    for item in [*reversed(p.parents), p]:
        s = item.lstat()
        if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400: raise RuntimeError('LINK_REPARSE_DENIED')
        if item!=p or directory:
            if not stat.S_ISDIR(s.st_mode): raise RuntimeError('DIRECTORY_REQUIRED')
        elif not stat.S_ISREG(s.st_mode) or s.st_nlink!=1: raise RuntimeError('SINGLE_LINK_FILE_REQUIRED')
    return p
def tree(p):
    ordinary(p,True)
    for directory, dirs, files in os.walk(p,followlinks=False):
        for name in dirs: ordinary(pathlib.Path(directory)/name,True)
        for name in files: ordinary(pathlib.Path(directory)/name)
ordinary(root,True)
ordinary(out,True)
try:
    names=[os.environ.get(k) for k in ('PREVIEW_EVENT_REPOSITORY','PREVIEW_HEAD_REPOSITORY','PREVIEW_BASE_REPOSITORY')]
    repo_ids=[os.environ.get(k) for k in ('PREVIEW_EVENT_REPOSITORY_ID','PREVIEW_HEAD_REPOSITORY_ID','PREVIEW_BASE_REPOSITORY_ID')]
    facts['repository_cohort']={'names':names,'ids':repo_ids,'expected_name':'YehorBabenko88/Terminan','expected_id':'1413341784'}
    if names!=['YehorBabenko88/Terminan']*3 or repo_ids!=['1413341784']*3: raise RuntimeError('EXACT_SAME_REPOSITORY_REQUIRED')
    # Root-first ALL path metadata, before primary Git/source/tool bytes.
    tree(root)
    python=ordinary(sys.executable)
    git=ordinary(os.environ['PREVIEW_FIXED_GIT'])
    node=ordinary(os.environ['PREVIEW_FIXED_NODE'])
    if sys.version_info[:3]!=(3,12,10) or not(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode): raise RuntimeError('PYTHON_VERSION_FLAGS')
    for k in ('NODE_OPTIONS','NODE_PATH','NODE_COMPILE_CACHE','NODE_V8_COVERAGE','GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES','GIT_NAMESPACE','GIT_REPLACE_REF_BASE'):
        if os.environ.get(k): raise RuntimeError('AMBIENT_SOURCE_CONFIG')
    if os.environ.get('GITHUB_HEAD_REF')!='feature/preview-benchmark-disposal-20261110' or os.environ.get('GITHUB_BASE_REF')!='feature/scientific-read-recovery-20261110' or os.environ.get('PREVIEW_REVIEW_BASE_SHA')!='dc810b03c3accf0e6f28fca1d5068f4171bb909d': raise RuntimeError('EXACT_OWN_STACK_REQUIRED')
    head=os.environ['PREVIEW_EXPECTED_HEAD']
    if not re.fullmatch('[a-f0-9]{40}',head): raise RuntimeError('EXPECTED_HEAD')
    facts['tools']={name:{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'role':role} for name,p,role in [('python',python,'ISOLATED_BOOTSTRAP_QUALIFIER'),('git',git,'FIXED_PRIMARY_GIT_NO_CMD_FALLBACK'),('node',node,'SETUP_NODE_TEST_BINARY_OBSERVED_NOT_SIGNED_PROVENANCE')]}
    def g(*args):
        ordinary(root,True);ordinary(git)
        p=subprocess.run([str(git),'--no-replace-objects','--no-optional-locks','-c','core.fsmonitor=false',*args],cwd=root,capture_output=True,timeout=10)
        if p.returncode or len(p.stdout)>1048576: raise RuntimeError('PRIMARY_GIT_DENIED')
        return p.stdout
    if g('rev-parse','HEAD').decode().strip()!=head: raise RuntimeError('HEAD_MISMATCH')
    filename='tests/preview_benchmark_qualification.py'
    source=ordinary(root/filename)
    raw=g('show',head+':'+filename)
    if raw!=source.read_bytes(): raise RuntimeError('QUALIFIER_PRIMARY_BYTES_MISMATCH')
    pin=hashlib.sha256(raw).hexdigest()
    facts.update(head=head,qualifier_sha256=pin,result='PRIMARY_QUALIFIER_VERIFIED')
    with (out/'bootstrap-facts.json').open('x') as f: json.dump(facts,f,indent=2)
    sys.argv=[str(source),str(root),head,str(out/'unit'),str(node),str(git),pin]
    facts['qualifier_load_attempted']=True
    exec(compile(raw,str(source),'exec'),{'__name__':'__main__','__file__':str(source)})
except BaseException as error:
    facts['result']='BOOTSTRAP_OR_QUALIFIER_DENIED'
    facts['error_type']=type(error).__name__
    if isinstance(error,SystemExit) and error.code==0:
        facts['result']='QUALIFIER_RETURNED_SUCCESS'
    with (out/'bootstrap-final.json').open('x') as f: json.dump(facts,f,indent=2)
    raise