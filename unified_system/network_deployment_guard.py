"""Read-only deployment interlock, not a privileged network repair service.

The controller supplies its independent, source-pinned observer and durable
evidence sink. JSON observations are evidence, never runtime authorization.
This gate cannot constrain an administrator bypassing the controller.
"""
import copy,datetime,hashlib,json,math,re,time

NODES=frozenset(('LS5','PC1','PC2','PC3','PC4','LS7'))
HOSTS=frozenset(('www.microsoft.com','api.bybit.com'))
ROW_KEYS={
 'adapters':{'InterfaceIndex','InterfaceGuid','Name','Status','MacAddress'},
 'interfaces':{'InterfaceIndex','AddressFamily','Dhcp','ConnectionState','InterfaceMetric'},
 'addresses':{'InterfaceIndex','IPAddress','PrefixLength','PrefixOrigin','SuffixOrigin','AddressState'},
 'dns':{'InterfaceIndex','AddressFamily','ServerAddresses'},
 'routes':{'InterfaceIndex','DestinationPrefix','NextHop','RouteMetric','Protocol','PolicyStore'},
 'firewall':{'Name','Enabled','DefaultInboundAction','DefaultOutboundAction'},
 'services':{'Name','status'}}
class NetworkBlocked(ValueError):pass
def need(ok,code='NETWORK_OBSERVATION_REJECTED'):
 if not ok:raise NetworkBlocked(code)
def canonical(data):return json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
def timestamp(value):
 need(type(value)is str and len(value)<=40)
 try:
  parsed=datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
  need(parsed.utcoffset()==datetime.timedelta(0));return parsed.timestamp()
 except (ValueError,OverflowError,TypeError):raise NetworkBlocked('NETWORK_OBSERVATION_REJECTED')from None
def validate(data,node,now):
 need(type(data)is dict and set(data)=={'schema','computer','started_utc','finished_utc','mutations','configuration','checks'})
 need(data['schema']=='unified.network-readonly-observation.v1'and data['mutations']is False)
 need(data['computer'].upper()in ({'LS5','LS-5'}if node=='LS5'else{node}))
 start=timestamp(data['started_utc']);end=timestamp(data['finished_utc'])
 need(type(now)in(int,float)and math.isfinite(now)and 0<=now-end<=90 and 0<=end-start<=75)
 config=data['configuration'];need(type(config)is dict and set(config)==set(ROW_KEYS))
 for key,fields in ROW_KEYS.items():
  need(type(config[key])is list and 1<=len(config[key])<=4096)
  need(all(type(row)is dict and set(row)==fields for row in config[key]))
  for row in config[key]:
   for value in row.values():
    need(value is None or type(value)in(str,int,bool,list))
    if type(value)is str:need(len(value)<=2048)
    if type(value)is list:need(len(value)<=64 and all(type(item)is str and len(item)<=256 for item in value))
 need(len(config['firewall'])==3 and {row['Name']for row in config['firewall']}=={'Domain','Private','Public'})
 need(len({row['Name']for row in config['services']})==len(config['services']))
 need(type(data['checks'])is list and len(data['checks'])==2)
 need(all(type(item)is dict for item in data['checks']))
 need({item.get('host')for item in data['checks']}==HOSTS)
 for item in data['checks']:
  need(all(item.get(key)=='PASS'for key in('dns','tcp443','https')),'NETWORK_CONNECTIVITY_DEGRADED')
  need(item.get('api')==('PASS'if item['host']=='api.bybit.com'else'NOT_RUN'),'NETWORK_CONNECTIVITY_DEGRADED')
 raw=canonical(data);need(len(raw)<=1048576)
 return copy.deepcopy(data),hashlib.sha256(canonical(data['configuration'])).hexdigest(),hashlib.sha256(raw).hexdigest()

class NetworkDeploymentGuard:
 def __init__(self,node,operation_id,*,observe,record,now=time.time):
  need(node in NODES and type(operation_id)is str and re.fullmatch('[A-Za-z0-9_-]{1,80}',operation_id)is not None)
  need(callable(observe)and callable(record)and callable(now))
  self.node=node;self.operation_id=operation_id;self._observe=observe;self._record=record;self._now=now
  self._baseline=None;self.stopped=False;self._sequence=0
 def begin(self):
  need(self._baseline is None and not self.stopped,'NETWORK_OPERATION_STOPPED')
  return self._check('BEFORE')
 def checkpoint(self,phase):
  need(not self.stopped,'NETWORK_OPERATION_STOPPED')
  if self._baseline is None:self.stopped=True;raise NetworkBlocked('NETWORK_BASELINE_REQUIRED')
  need(phase in('BEFORE_EFFECT','AFTER'))
  return self._check(phase)
 def _check(self,phase):
  need(not self.stopped,'NETWORK_OPERATION_STOPPED')
  receipt=dict(schema='unified.network-deployment-evidence.v1',computer=self.node,operation_id=self.operation_id,
   sequence=self._sequence+1,phase=phase,network_mutations=False,decision='STOP_CURRENT_DEPLOYMENT')
  try:
   observation=self._observe();now=self._now()
   receipt['observed_at_utc']=datetime.datetime.fromtimestamp(now,datetime.timezone.utc).isoformat()
   data,config_digest,observation_digest=validate(observation,self.node,now)
   receipt.update(observation=data,observation_sha256=observation_digest,configuration_sha256=config_digest)
   need(self._baseline is None or self._baseline==config_digest,'NETWORK_CONFIGURATION_CHANGED')
   receipt['decision']='CONTINUE_OWNED_DEPLOYMENT_PHASE'
   self._record(copy.deepcopy(receipt))
   self._baseline=config_digest;self._sequence+=1
   return copy.deepcopy(receipt)
  except Exception as exc:
   self.stopped=True;receipt['decision']='STOP_CURRENT_DEPLOYMENT'
   receipt['reason']=str(exc)if isinstance(exc,NetworkBlocked)else'NETWORK_OBSERVER_OR_EVIDENCE_UNAVAILABLE'
   try:self._record(copy.deepcopy(receipt))
   except Exception:pass
   raise NetworkBlocked(receipt['reason'])from None
