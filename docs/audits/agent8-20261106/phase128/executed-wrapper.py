import sys,runpy,subprocess,json,socket,hashlib
from unittest.mock import patch
import httpx
out=sys.argv[1];driver=sys.argv[2];args=sys.argv[3:];children=[];original=subprocess.run
def record(*a,**kw):
 result=original(*a,**kw)
 command=a[0] if a else kw.get('args',[])
 if isinstance(command,list) and '-c' in command and any('RootRegistrationCustody' in str(v) for v in command):
  children.append(dict(returncode=result.returncode,stdout=result.stdout.decode(),stderr=result.stderr.decode(),scope='OWN_SUBPROCESS_CALL_NOT_NATIVE_PID_IDENTITY_PROOF'))
 return result
sys.argv=[driver,*args]
with patch.object(subprocess,'run',side_effect=record),patch.object(socket.socket,'connect',side_effect=AssertionError('NETWORK_FORBIDDEN')) as c,patch.object(socket,'getaddrinfo',side_effect=AssertionError('DNS_FORBIDDEN')) as d,patch.object(httpx.AsyncClient,'request',side_effect=AssertionError('HTTP_FORBIDDEN')) as ah,patch.object(httpx.Client,'request',side_effect=AssertionError('HTTP_FORBIDDEN')) as sh:
 runpy.run_path(driver,run_name='__main__')
 assert len(children)==2 and all(x['returncode']==0 for x in children)
 assert json.loads(children[0]['stdout'])['status']=='DENIED' and json.loads(children[1]['stdout'])['status']=='ACQUIRED'
 assert c.call_count==d.call_count==ah.call_count==sh.call_count==0
 from pathlib import Path
 Path(out).write_text(json.dumps(dict(children=children,parent_connect_calls=c.call_count,parent_dns_calls=d.call_count,parent_http_calls=ah.call_count+sh.call_count,child_network_scope='reviewed exact child source imports local Journal/adapter only; parent guards do not propagate to child'),indent=2))
