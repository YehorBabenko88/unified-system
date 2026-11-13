"""Finite synthetic composition of existing Worker/raw/Storage components.

No scheduler, provider transport, authority or alternate storage is defined here.
This developer path cannot activate a protected service or public submission.
Synchronous local I/O in awaited owners is not a cooperative cancellation bound.
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import stat
import time
from .collector_profile import CollectorProfile,CollectorProfileRejected,decode_collector_profile
from .runtime_process import _safe_path

class CollectorOfflineBlocked(ValueError):
 def __init__(self):super().__init__('COLLECTOR_OFFLINE_BLOCKED')

class CollectorBudgetExhausted(CollectorOfflineBlocked):
 def __init__(self):ValueError.__init__(self,'COLLECTOR_BUDGET_EXHAUSTED')

def _need(ok):
 if not ok:raise CollectorOfflineBlocked()

def synthetic_frames():
 """One fixed SYNTHETIC fixture, never verified market history."""
 return (json.dumps({'topic':'publicTrade.BTCUSDT','data':[{'T':1794441600000,
  's':'BTCUSDT','p':'100','v':'2','S':'Buy','i':'synthetic-1'}]},separators=(',',':')).encode('ascii'),)

def _grid_revision(raw):
 _need(type(raw) is bytes and 0<len(raw)<=262144)
 def unique(pairs):
  out={}
  for key,value in pairs:
   _need(key not in out);out[key]=value
  return out
 def nonfinite(_):raise CollectorOfflineBlocked()
 try:value=json.loads(raw.decode('utf-8'),object_pairs_hook=unique,parse_constant=nonfinite)
 except (ValueError,UnicodeError,RecursionError):raise CollectorOfflineBlocked() from None
 _need(type(value) is dict and value.get('schema')=='unified.collector.integration-manifest.v1'
       and value.get('execution_scope')=='SYNTHETIC_OFFLINE')
 permissions=value.get('permissions')
 _need(type(permissions) is dict and set(permissions)=={'real_provider_sends','service_creation','acl_changes',
  'production_sql','training','trading','public_submit','authority_mutation'} and all(v is False for v in permissions.values()))
 components=value.get('new_components');_need(type(components) is list and len(components)<=16)
 owners=[item for item in components if type(item) is dict and item.get('owner')=='A3']
 _need(len(owners)==1)
 revision=owners[0].get('head');_need(type(revision) is str and re.fullmatch('[a-f0-9]{40}',revision) is not None)
 return revision

async def collect_synthetic(profile,*,manifest_bytes,frames,state_root,code_root,observed_at_ms,resume=False):
 """One explicitly bounded developer capture; clean resume requires same binding.

Root's external source custodian must admit exact code/dependencies. Configuration
and this function's local custody receipts are not that admission or authority.
"""
 started=time.monotonic()
 _need(type(profile) is CollectorProfile and type(resume) is bool)
 _need(type(manifest_bytes) is bytes and 0<len(manifest_bytes)<=262144)
 try:checked=decode_collector_profile(profile.encoded,manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest())
 except CollectorProfileRejected as error:raise CollectorOfflineBlocked() from error
 config=checked.document;revision=_grid_revision(manifest_bytes);limits=config['limits']
 _need(type(observed_at_ms) is int and 0<observed_at_ms<2**63)
 _need(type(frames) is tuple and 1<=len(frames)<=limits['frames'])
 sizes=[]
 for frame in frames:
  _need(type(frame) in (str,bytes) and len(frame)<=limits['frame_bytes'])
  size=len(frame.encode('utf-8')) if type(frame) is str else len(frame)
  _need(size<=limits['frame_bytes']);sizes.append(size)
 _need(sum(sizes)<=limits['raw_bytes'])
 state_root=Path(state_root);code_root=Path(code_root)
 _need(state_root.is_absolute() and code_root.is_absolute())
 state_root=_safe_path(state_root);code_root=_safe_path(code_root)
 _need(stat.S_ISDIR(code_root.lstat().st_mode) and stat.S_ISDIR(state_root.parent.lstat().st_mode))
 _need(state_root!=code_root and code_root not in state_root.parents and state_root not in code_root.parents)
 # These are actual existing components, imported only after finite input checks.
 from grid.worker import Worker,COLLECTOR_PROFILE
 from grid.raw_capture import RawCaptureRecorder,RawCaptureProfile as GridRawProfile,decode_observation
 from .storage.collector_context import CollectorContext,CollectorContextProfile
 from .storage.raw_capture import RawCaptureProfile as StoreRawProfile
 from .collector_logging import CollectorLog,LogLimits
 if not resume:state_root.mkdir(exist_ok=False)
 else:_need(stat.S_ISDIR(state_root.lstat().st_mode))
 log=None;context=None;result=None;errors=[]
 try:
  log_limits=LogLimits(file_bytes=config['logging']['max_file_bytes'],file_count=config['logging']['file_count'])
  logging_open=CollectorLog.open if resume else CollectorLog.create
  log=logging_open(state_root/'logs',state_root=state_root,code_root=code_root,context_id=config['context_id'],limits=log_limits)
  log.emit(event='RECOVERY' if resume else 'STARTUP',state='STARTING',digest=checked.sha256)
  context_profile=CollectorContextProfile(raw_profile=StoreRawProfile(sqlite_headroom_bytes=262144,inventory_file_limit=128),lifecycle_headroom_bytes=65536)
  context_open=CollectorContext.open if resume else CollectorContext.create
  context=context_open(state_root/'context',context_id=config['context_id'],store_id=config['store_id'],
   binding_sha256=config['source_manifest_sha256'],profile=context_profile)
  context.require_ready()
  def inspect_history(history):
   values=[]
   for fact in history:
    _need(hashlib.sha256(fact.observation_bytes).hexdigest()==fact.observation_sha256)
    if fact.payload_bytes is not None:_need(hashlib.sha256(fact.payload_bytes).hexdigest()==fact.payload_sha256)
    value=decode_observation(fact.observation_bytes)
    _need(value['source_kind']=='SYNTHETIC' and value['producer_source_revision']==revision
     and value['endpoint']=='synthetic://bybit/linear'
     and value['instrument']==dict(exchange='bybit',category='linear',symbol='BTCUSDT',instrument_version='1'))
    _need(value['payload_sha256']==fact.payload_sha256 and int(value['payload_bytes'])==fact.payload_byte_count)
    values.append(value)
   return values
  initial=await context.read_history()
  inspect_history(initial) # Invalid/unreadable history cannot become zero gaps.
  previous=None if not initial else asdict(await context.checkpoint())
  # The pinned finite Worker v1 emits frame + validated/gap per input and
  # reserves two TOTAL-context slots for disconnect/error control. A fresh
  # recorder after restart must not turn persisted usage into a fresh pool.
  if (len(initial)+2*len(frames)>16-2
      or sum(f.payload_byte_count for f in initial)+sum(sizes)>4194304):
   raise CollectorBudgetExhausted()
  log.emit(event='READY',state='RUNNING',count=len(initial))
  factory_calls=[]
  def factory(symbol,endpoint):
   _need(not factory_calls);factory_calls.append((symbol,endpoint));context.require_ready()
   return RawCaptureRecorder(context,instrument=dict(exchange='bybit',category='linear',symbol='BTCUSDT',instrument_version='1'),
    producer_source_revision=revision,source_kind='SYNTHETIC',endpoint=endpoint,
    profile=GridRawProfile(16,4194304,1048576,16384,2))
  worker=Worker(launch_profile=COLLECTOR_PROFILE,raw_capture_factory=factory)
  received=await worker.receive_offline(frames,symbol='BTCUSDT',endpoint='synthetic://bybit/linear',observed_at_ms=observed_at_ms)
  _need(len(factory_calls)==1 and time.monotonic()-started<=limits['duration_seconds'])
  facts=await context.read_history();checkpoint=await context.checkpoint()
  history_values=inspect_history(facts)
  unique_payloads={};payload_occurrences=0
  for fact in facts:
   _need(hashlib.sha256(fact.observation_bytes).hexdigest()==fact.observation_sha256)
   if fact.payload_bytes is not None:
    _need(hashlib.sha256(fact.payload_bytes).hexdigest()==fact.payload_sha256)
    payload_occurrences+=len(fact.payload_bytes);unique_payloads[fact.payload_sha256]=len(fact.payload_bytes)
  gap_count=sum(value['kind']=='gap_observation' for value in history_values)
  invocation_gap=received['metrics']['gap_open'];gap=invocation_gap or gap_count>0
  log.emit(event='QUALITY' if gap else 'CAPTURE',state='RUNNING',error_code='QUALITY_GAP' if gap else 'NONE',
   count=len(facts),bytes_count=payload_occurrences,digest=checkpoint.observation_sha256)
  log.emit(event='CHECKPOINT',state='RUNNING',digest=checkpoint.raw_journal_digest)
  stopped=await context.stop();_need(stopped.state=='STOPPED')
  log.emit(event='SHUTDOWN',state='STOPPED',count=len(facts))
  result=dict(schema='unified.collector.offline-result.v1',phase='STOPPED',scope='SYNTHETIC_OFFLINE',
   classification='LOCAL_UNATTESTED',counter_epoch=config['context_id'],profile_sha256=checked.sha256,
   source_manifest_sha256=config['source_manifest_sha256'],raw_frames_received=len(frames),
   raw_received_bytes=sum(sizes),raw_observations_stored=len(facts),raw_payload_occurrence_bytes=payload_occurrences,
   raw_payload_unique_bytes=sum(unique_payloads.values()),payload_sha256s=sorted(unique_payloads),
   parsed_trade_occurrences=sum(len(batch) for batch in received['batches']),all_digests_verified=True,
   gap_open=gap,invocation_gap_open=invocation_gap,gap_count=gap_count,gap_scope='CONTEXT_HISTORY_RECORDED_GAP_EVENTS',
   continuity='UNKNOWN',raw_durability='UNKNOWN',
   quality='GAP_DETECTED' if gap else 'SYNTHETIC_INPUT_VALIDATED',checkpoint=asdict(checkpoint),
   previous_checkpoint=previous,native_outcome='UNKNOWN',publication_confirmed=False,
   database_rows_sqlite_raw_links=len(facts),postgresql='NOT_RUN',provider_sends=0,
   service_running=False,physical_accepted=False,process_restart_verified=False,
   counter_scopes=dict(raw_frames_received='INVOCATION',raw_received_bytes='INVOCATION',
    parsed_trade_occurrences='INVOCATION',raw_observations_stored='CONTEXT_HISTORY',
    raw_payload_occurrence_bytes='CONTEXT_HISTORY',raw_payload_unique_bytes='CONTEXT_ARCHIVE'))
 except BaseException as error:
  errors.append(error)
  if context is not None:
   try:
    if context.status().state=='ACTIVE':
     await context.mark_terminal('collector_budget_exhausted' if isinstance(error,CollectorBudgetExhausted) else 'collector_failed')
   except BaseException as cleanup:errors.append(cleanup)
  if log is not None:
   try:
    if isinstance(error,CollectorBudgetExhausted):log.emit(event='RESOURCE',state='BLOCKED',error_code='RESOURCE_LIMIT')
    else:log.emit(event='ERROR',state='UNKNOWN',error_code='CAPTURE_STOPPED')
   except BaseException as cleanup:errors.append(cleanup)
 finally:
  # Awaited receive is finished/raised; close is never treated as async I/O retirement.
  for owner in (context,log):
   if owner is not None:
    try:owner.close()
    except BaseException as cleanup:errors.append(cleanup)
 if errors:
  if len(errors)==1:raise errors[0]
  raise BaseExceptionGroup('Collector primary/cleanup outcomes',errors)
 _need(result is not None and time.monotonic()-started<=limits['duration_seconds'])
 result['writer_closed']=True;result['elapsed_seconds']=time.monotonic()-started
 return result
