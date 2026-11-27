"""Closed four-owner source contracts; no process, network or grant factory."""
import re
SCHEMA='unified.four-owner.source-cohort.v1'
OWNERS=('unified_system','market_data','math','terminan')
BROWSER_CASES=(
 'actual lifecycle file -> actual Terminan HTTP -> Chromium controls',
 'cancelled stale HTTP response cannot replace latest actual source',
 'real missing snapshot renders explicit error and recovers',
 'actual socket disconnect becomes unavailable then recovers')

def bind_heads(manifest,root_head):
 if type(manifest) is not dict or manifest.get('schema')!=SCHEMA or manifest.get('release_status')!='NO_GO' or manifest.get('execution_authority') is not False or manifest.get('trading_authorized') is not False:raise ValueError('COHORT_SCOPE_REQUIRED')
 sources=manifest.get('sources')
 if type(sources) is not dict or len(sources)!=4 or set(sources)!=set(OWNERS):raise ValueError('CANONICAL_FOUR_OWNER_ROSTER_REQUIRED')
 if type(root_head) is not str or re.fullmatch('[a-f0-9]{40}',root_head) is None:raise ValueError('EXACT_ROOT_HEAD_REQUIRED')
 heads={}
 for name in OWNERS:
  value=sources[name]['commit']
  if name=='unified_system':
   if value!='ENCLOSING_HEAD':raise ValueError('ROOT_COMMIT_MUST_BIND_ENCLOSING_HEAD')
   value=root_head
  if type(value) is not str or re.fullmatch('[a-f0-9]{40}',value) is None:raise ValueError('EXACT_SOURCE_HEAD_REQUIRED')
  heads[name]=value
 return heads

def require_cases(actual,expected):
 if not expected or len(actual)!=len(set(actual)) or len(expected)!=len(set(expected)) or sorted(actual)!=sorted(expected):raise ValueError('EXACT_UNIQUE_CASE_IDS_REQUIRED')
 return sorted(actual)

def result_complete(result,count):
 return result.wasSuccessful() and result.testsRun==count and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses

STATUS_CONSUMER_HELD_ROLES=("PARTIAL_TO_TERMINAL_GAP_DISPLAY","UNAVAILABLE_TERMINAL_DISPLAY","WRONG_PRODUCER_HTTP_REFUSAL","WRONG_PRODUCER_HTTP_RETIREMENT","WRONG_PRODUCER_ENV_PATH_RESTORATION","ROOT_BLOCKED_TO_TERMINAL_MONITOR_HTTP","MONITOR_UNVERIFIED_NO_TRADE","MONITOR_HTTP_RETIREMENT","MONITOR_ENV_PATH_RESTORATION",)

def runtime_gate(kind,source_proof):
 return dict(schema='unified.four-owner.mandatory-runtime-gate.v1',kind=kind,status='BLOCKED',passed=False,release_status='NO_GO',source_qualification=source_proof.get('qualification','NOT_RUN'),
  missing_proofs=['LEGACY_STATUS_CONSUMER_COMPOSITION_NOT_QUALIFIED','CANONICAL_STARTUP_ADMISSION_REQUIRED','PROTECTED_FOUR_OWNER_LIVE_SOURCE_AND_DATABASE_CAPABILITY_NOT_QUALIFIED','CANONICAL_MONITOR_SOURCE_ADAPTER_NOT_CONNECTED','CANONICAL_BROWSER_ROUTE_AND_CONTROL_PORT_NOT_QUALIFIED','TERMINAN_CANONICAL_PRODUCER_RESULT_LEDGER_GRAPH_DISPLAY_HANDOFF_NOT_QUALIFIED'],
  preserved_browser_cases=list(BROWSER_CASES),preserved_runtime_obligations=['OWNED_START_AND_AUTHENTICATED_READINESS','ACTUAL_RUNTIME_DISPLAY','UNAUTHENTICATED_HEALTH_DENIAL','OWNED_STOP','SOURCE_POSTCHECK','PRIVATE_CLEANUP'],
  preserved_legacy_obligation_inventory='docs/migration/retired-six-owner/role-inventory.json',
  additional_legacy_obligation_inventory='docs/migration/retired-status-consumers-20261120/role-inventory.json',held_status_consumer_roles=list(STATUS_CONSUMER_HELD_ROLES),
  native_installation='NOT_RUN',physical='NOT_RUN',production='NO_GO',execution_authority=False,trading_authorized=False)
