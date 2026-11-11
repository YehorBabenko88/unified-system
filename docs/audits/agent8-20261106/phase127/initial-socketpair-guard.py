import sys,os,json,asyncio,socket
from unittest.mock import patch
sys.path[:0]=sys.argv[1:3]
import httpx
from grid.coordination import ConsulConfig,ConsulSessionAuthority
from unified_system.gateway_native_negative import _loopback_endpoints
endpoint='http://127.0.0.1:8500';_loopback_endpoints((endpoint,),True)
async def probe():
 observations=[]
 for bypass in ('','127.0.0.1'):
  controlled={k:v for k,v in os.environ.items() if k.upper() not in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY')}
  controlled.update(HTTP_PROXY='http://127.0.0.1:9',NO_PROXY=bypass)
  with patch.dict(os.environ,controlled,clear=True):
   authority=ConsulSessionAuthority(ConsulConfig((endpoint,),'a8/proxy-source-only',isolated_lab=True,acl_token='A8_SYNTHETIC_NEVER_SENT'))
  try:
   selected=authority.client._transport_for_url(httpx.URL(endpoint))
   pool=type(selected._pool).__name__
   assert pool==('AsyncHTTPProxy' if not bypass else 'AsyncConnectionPool')
   observations.append(dict(controlled_no_proxy=bypass,loopback_gate_accepted=True,selected_pool=pool,client_trust_env=authority.client.trust_env,proxy_selection_persists_outside_env_patch=True))
  finally:await authority.close()
 return observations
with patch.object(socket.socket,'connect',side_effect=AssertionError('NETWORK_FORBIDDEN')) as c,patch.object(socket.socket,'connect_ex',side_effect=AssertionError('NETWORK_FORBIDDEN')) as e,patch.object(socket,'getaddrinfo',side_effect=AssertionError('DNS_FORBIDDEN')) as d:
 observations=asyncio.run(probe());assert c.call_count==e.call_count==d.call_count==0
 print(json.dumps(dict(httpx=httpx.__version__,observations=observations,network_connect_calls=c.call_count,network_connect_ex_calls=e.call_count,dns_calls=d.call_count,requests_issued=0,Consul_processes_started=0,scope='ACTUAL_CLIENT_TRANSPORT_SELECTION_ONLY_NO_NETWORK')))
