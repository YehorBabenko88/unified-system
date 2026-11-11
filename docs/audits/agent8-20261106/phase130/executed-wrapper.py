import sys,subprocess,json,runpy
from pathlib import Path
from unittest.mock import patch
out=sys.argv[1];driver=sys.argv[2];args=sys.argv[3:];children=[];original=subprocess.run
def record(*a,**kw):
 result=original(*a,**kw);cmd=a[0] if a else kw.get('args',[])
 if isinstance(cmd,list) and any(str(v).endswith('proxy_probe_child.py') for v in cmd):
  children.append(dict(returncode=result.returncode,stdout=result.stdout.decode(),stderr=result.stderr.decode(),scope='OWN_CHILD_NOT_NATIVE_PID_IDENTITY_QUALIFICATION'))
 return result
sys.argv=[driver,*args]
with patch.object(subprocess,'run',side_effect=record):runpy.run_path(driver,run_name='__main__')
module=sys.modules['test_proxy'];processes=module.ProxyIsolationTests.lab.all_processes
retired=[dict(pid=p.pid,returncode=p.poll()) for p in processes]
assert len(retired)==3 and all(x['returncode'] is not None for x in retired)
assert len(children)==2 and all(x['returncode']==0 for x in children)
Path(out).write_text(json.dumps(dict(owned_children=children,owned_Consul_retained_handles_retired=retired,trap_thread_cleanup='committed tests assert joined own thread per case',scope='ACTUAL_OWNED_CONSUL_READ_ONLY_NO_JOB_OR_REGISTRATION'),indent=2))
