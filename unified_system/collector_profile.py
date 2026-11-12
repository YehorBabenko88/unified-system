"""Versioned synthetic Collector configuration, never a provider/host grant.

Separate from the existing full-runtime/DataFirst policies. Bytes use Python's
ASCII sorted compact JSON profile with LF; this is not RFC8785 certification.
"""
from dataclasses import dataclass
import hashlib
import json
import re

SCHEMA = 'unified.data-only-collector.profile.v1'
GRID_PROFILE = 'grid.data-only-collector.v1'
LOG_SCHEMA = 'unified.collector.logging.v1'
_FIELDS = frozenset(('schema','mode','grid_launch_profile','context_id','store_id',
 'source_manifest_sha256','instrument_identity','limits','network','features','logging'))
_FEATURES = frozenset(('trading','training','math','public_submit','authority_mutation'))

class CollectorProfileRejected(ValueError):
 def __init__(self):super().__init__('COLLECTOR_PROFILE_REJECTED')

def _need(ok):
 if not ok:raise CollectorProfileRejected()

def _keys(value,keys):
 _need(type(value) is dict)
 # Check before hashing/equality: Python callers are not necessarily JSON.
 _need(all(type(key) is str for key in value))
 _need(set(value)==set(keys))
def _string(value,expected):_need(type(value) is str and value==expected)
def _integer(value,low,high):_need(type(value) is int and low<=value<=high)

@dataclass(frozen=True)
class CollectorProfile:
 encoded: bytes
 @property
 def document(self):return json.loads(self.encoded)
 @property
 def sha256(self):return hashlib.sha256(self.encoded).hexdigest()
 @property
 def execution_authority(self):return False

def validate_collector_profile(value,*,manifest_sha256):
 try:
  _keys(value,_FIELDS)
  _string(value['schema'],SCHEMA);_string(value['mode'],'SYNTHETIC_OFFLINE')
  _string(value['grid_launch_profile'],GRID_PROFILE)
  _need(type(manifest_sha256) is str and re.fullmatch(r'[a-f0-9]{64}',manifest_sha256) is not None)
  _string(value['source_manifest_sha256'],manifest_sha256)
  context=value['context_id'];_need(type(context) is str and re.fullmatch(r'[a-f0-9]{32}',context) is not None)
  store=value['store_id'];_need(type(store) is str and re.fullmatch(r'[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}',store) is not None)
  _string(value['instrument_identity'],'synthetic-btcusdt-v1')
  limits=value['limits'];_keys(limits,('frames','frame_bytes','raw_bytes','duration_seconds'))
  _integer(limits['frames'],1,4);_integer(limits['frame_bytes'],1,1048576)
  _integer(limits['raw_bytes'],1,4194304);_integer(limits['duration_seconds'],1,120)
  _need(limits['raw_bytes']>=limits['frame_bytes'])
  network=value['network'];_keys(network,('rest','websocket'))
  _need(all(x is False for x in network.values()))
  features=value['features'];_keys(features,_FEATURES)
  _need(all(x is False for x in features.values()))
  logging=value['logging'];_keys(logging,('schema','max_file_bytes','file_count'))
  _string(logging['schema'],LOG_SCHEMA)
  _integer(logging['max_file_bytes'],1024,1048576);_integer(logging['file_count'],2,4)
  raw=(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('ascii')
  _need(len(raw)<=32768)
  return CollectorProfile(raw)
 except CollectorProfileRejected:raise
 except (KeyError,TypeError,ValueError,AttributeError,OverflowError,RecursionError):
  raise CollectorProfileRejected() from None

def decode_collector_profile(raw,*,manifest_sha256):
 try:
  _need(type(raw) is bytes and 0<len(raw)<=32768)
  def unique(pairs):
   result={}
   for key,value in pairs:
    _need(key not in result);result[key]=value
   return result
  def nonfinite(_):raise CollectorProfileRejected()
  value=json.loads(raw.decode('utf-8'),object_pairs_hook=unique,parse_constant=nonfinite)
  return validate_collector_profile(value,manifest_sha256=manifest_sha256)
 except CollectorProfileRejected:raise
 except (UnicodeError,ValueError,TypeError,RecursionError):raise CollectorProfileRejected() from None

def collector_plan(profile):
 _need(type(profile) is CollectorProfile)
 # Revalidate even a directly constructed dataclass: it is not a capability.
 try:
  document=profile.document
  _need(type(document) is dict)
  checked=decode_collector_profile(profile.encoded,manifest_sha256=document.get('source_manifest_sha256'))
 except CollectorProfileRejected:raise
 except (ValueError,TypeError,AttributeError,RecursionError):raise CollectorProfileRejected() from None
 return dict(schema='unified.data-only-collector.plan.v1',status='PLAN_ONLY_NOT_EXECUTION_AUTHORITY',
  profile_sha256=checked.sha256,profile_schema=SCHEMA,grid_launch_profile=GRID_PROFILE,
  provider_sends=False,installed=False,service_admission=False,
  scope='SYNTHETIC_OFFLINE_LOCAL_UNATTESTED',limits=checked.document['limits'],logging=checked.document['logging'])
