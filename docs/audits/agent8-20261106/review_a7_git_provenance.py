"""Independent exact-source and isolated replacement regression review (A8)."""
import datetime, hashlib, json, os, pathlib, subprocess, xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/phase29'; OUT.mkdir(exist_ok=True)
PY=ROOT/'work/audit-venv/Scripts/python.exe'
def git(repo,*args):
    return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*args])
def identity(repo,sha):
    rows=[]
    for row in git(repo,'ls-tree','-rz',sha).split(b'\0'):
        if not row: continue
        metadata,name=row.split(b'\t',1);mode,kind,oid=metadata.split()
        assert kind==b'blob'
        raw=(repo/name.decode()).read_bytes()
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid.decode(), name
        rows.append([name.decode(),hashlib.sha256(raw).hexdigest()])
    return dict(files=len(rows),sha256=hashlib.sha256(json.dumps(rows).encode()).hexdigest())
cases=[('meta_analyse',78,'88b45c328bfdc8131ff0c6d139fddd8b27a4050c','f3c01a23fa5baaeeeb28eb8e9397e72b5ef4d5a1','c155c935a801fa98b7c78219c9798ce1f1be8848','tests/test_ci_source_replacements.py'),('strattester',72,'1722244f42d5d71a29b89bdec0e7211f2b723158','88a180b29afe9c85ddea26ef98cbe0bec8de24a6','572e530db6fca4beff5cbfa3efc9317964fca5ef','tests/research/test_financial_ci_source_replacements.py')]
results=[]
for name,pr,old,new,tree,test in cases:
    seed=ROOT/('work/review7-'+name)
    metadata=subprocess.check_output(['gh','pr','view',str(pr),'--repo','YehorBabenko88/'+name,'--json','headRefOid,baseRefOid,isDraft,url,files'])
    (OUT/(name+'-pr.json')).write_bytes(metadata)
    meta=json.loads(metadata); assert meta['headRefOid']==new and meta['baseRefOid']==old and meta['isDraft']
    variants={}
    for label,sha in [('fixed',new),('baseline',old)]:
        repo=ROOT/('work/a8-provenance-'+name+'-'+label)
        assert not repo.exists(),repo
        subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(seed),str(repo)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(repo),'-c','core.autocrlf=false','-c','core.eol=lf','checkout','--detach',sha],check=True,capture_output=True)
        assert (repo/'.git').is_dir() and not (repo/'.git/objects/info/alternates').exists()
        assert (repo/git(repo,'rev-parse','--git-common-dir').decode().strip()).resolve()==(repo/'.git').resolve()
        before=identity(repo,sha)
        if label=='fixed': assert git(repo,'rev-parse','HEAD^{tree}').decode().strip()==tree
        else:
            target=repo/test; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(git(seed,'show',new+':'+test))
        xml=OUT/(name+'-'+label+'.xml')
        env=dict(os.environ,PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1')
        env.pop('GIT_NO_REPLACE_OBJECTS',None)
        args=['--noconftest','-q','--import-mode=importlib','-p','no:cacheprovider','--basetemp='+str(ROOT/('work/a8-provenance-temp-'+name+'-'+label)),'--junitxml='+str(xml),test]
        boot='import sys;sys.path.insert(0,'+repr(str(repo))+');import pytest;raise SystemExit(pytest.main('+repr(args)+'))'
        p=subprocess.run([str(PY),'-I','-B','-c',boot],cwd=repo,env=env,capture_output=True,timeout=120)
        (OUT/(name+'-'+label+'.stdout.log')).write_bytes(p.stdout);(OUT/(name+'-'+label+'.stderr.log')).write_bytes(p.stderr)
        document=ET.parse(xml); count=len(document.findall('.//testcase'));fail=len(document.findall('.//failure'));error=len(document.findall('.//error'));skip=len(document.findall('.//skipped'))
        assert (count,fail,error,skip)==((10,0,0,0) if label=='fixed' else (10,4,0,0)),(name,label,p.returncode,count,fail,error,skip)
        after=identity(repo,sha);assert before==after
        variants[label]=dict(head=sha,exit_code=p.returncode,cases=count,failures=fail,errors=error,skips=skip,raw_source_before=before,raw_source_after=after,independent_common_git=True)
    results.append(dict(repository=name,pr=meta['url'],head=new,tree=tree,requirement='F16_GIT_REPLACEMENT_CONFORMANCE',status='FIX_VERIFIED_OFFLINE',variants=variants))
report=dict(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),environment='Windows isolated clones; Python 3.12 audit venv; no native invocation',results=results,scope='Git replacement provenance only; Meta wrong-tree metadata corrected; Stratt false-dirty availability corrected. No runtime/source-authenticity or hosted CI qualification.',F16_global='OPEN',physical='BLOCKED',tailscale_removal='BLOCKED',overall='NO_GO')
(OUT/'a7-git-provenance-review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
