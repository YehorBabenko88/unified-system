"""ADMINIT preparation only; no host discovery, execution, or admission authority.

Reuse the physical ledger's NOT_RUN/BLOCKED/RECORDED_UNVERIFIED semantics.
A separate owner grant and independent signature/evidence verifier are required
before any future execution. This module never grants either.
"""
import re
from .physical_acceptance import _matches, _SHA, _DIGEST

PHASES = {
    'A': 'owner_grant_inventory_release_preflight',
    'B': 'isolated_install_health_and_uninstall',
    'C': 'ten_instrument_historical_heldout_research',
    'D': 'public_feed_diagnostics_backpressure_paper_only',
    'E': 'bounded_isolated_faults_and_recovery',
    'F': 'verified_update_rollback_and_reproducibility',
    'G': 'defect_retest_evidence_and_owner_review',
}
PUBLIC_NETWORK = {
    'api.bybit.com': {'transport': 'HTTPS', 'port': 443, 'purpose': 'public market REST'},
    'stream.bybit.com': {'transport': 'WSS', 'port': 443, 'purpose': 'v5/public/linear'},
    'public.bybit.com': {'transport': 'HTTPS', 'port': 443, 'purpose': 'optional public trade archive'},
}
ROOT = r'C:\UnifiedAdminitTest'


def need(ok):
    if not ok:
        raise ValueError('ADMINIT_PREPARATION_REJECTED')


def prepare(*, release_sha, publisher_sha256, run_id):
    need(_matches(_SHA, release_sha) and _matches(_DIGEST, publisher_sha256))
    need(type(run_id) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,63}',run_id))
    return dict(schema='unified.adminit.preparation.v1', node='ADMINIT',
                release_sha=release_sha, publisher_sha256=publisher_sha256,run_id=run_id,
                owner_grant=None, physical_execution=False, inventory_status='NOT_RUN',
                instruments_status='NOT_RUN', isolated_root=ROOT,
                postgres_data=ROOT+r'\postgres-data',
                service_prefix='UnifiedAdminitTest-',
                rollback_policy='RESTORE_ONLY_TEST_NAMESPACE',
                uninstall_policy='REMOVE_ONLY_RECEIPTED_TEST_FILES_PRESERVE_DATA',
                phases={p: 'NOT_RUN' for p in PHASES},
                native_powershell_validation='NOT_RUN')


def assess(plan, records):
    """Count claimed phase evidence; signatures/hashes never authenticate themselves."""
    need(type(plan) is dict)
    expected=prepare(release_sha=plan.get('release_sha'),publisher_sha256=plan.get('publisher_sha256'),run_id=plan.get('run_id'))
    need(plan==expected and plan['physical_execution'] is False and plan['owner_grant'] is None)
    need(type(records) is list and len(records)<=len(PHASES))
    seen={}
    for record in records:
        need(type(record) is dict and set(record)=={'phase','result','release_sha','node','run_id','observed_at_ms','evidence_sha256','signature_sha256'})
        phase=record['phase']
        need(type(phase) is str and phase in PHASES and phase not in seen)
        need(record['result'] in ('PASS','FAIL') and record['release_sha']==plan['release_sha'])
        need(_matches(_DIGEST,record['evidence_sha256']) and _matches(_DIGEST,record['signature_sha256']))
        need(record['node']=='ADMINIT' and record['run_id']==plan['run_id'])
        need(type(record['observed_at_ms']) is int and 0<=record['observed_at_ms']<=2**53-1)
        seen[phase]=record['result']
    missing=[p for p in PHASES if p not in seen]
    failed=[p for p in PHASES if seen.get(p)=='FAIL']
    return dict(schema='unified.adminit.ledger.v1',node='ADMINIT',
                release_sha=plan['release_sha'],run_id=plan['run_id'],status='NOT_RUN' if not seen else 'BLOCKED' if missing or failed else 'RECORDED_UNVERIFIED',
                missing=missing,failed=failed,evidence_authenticity='UNVERIFIED',
                physical_acceptance_confirmed=False,physical_execution=False,
                deployment_authorized=False,multi_node_ha_confirmed=False,
                fleet_qualification='REQUIRES_SEPARATE_FIVE_OR_SIX_NODE_PHYSICAL_LEDGER')


def validate_instruments(evidence, *, start_ms, end_ms):
    """Validate claimed public API observations; never fetch or authenticate them.

    AUTHENTICATED describes the required producer origin, distinct from synthetic
    fixtures. It is a claim until externally verified against captured responses.
    Historical coverage must be assessed separately from current Trading status.
    """
    need(type(start_ms) is int and type(end_ms) is int and 0<=start_ms<end_ms<=2**53-1)
    need(type(evidence) is list and len(evidence)==10)
    seen=set()
    fields={'symbol','category','quote_coin','contract_type','status','origin','source',
            'observed_at_ms','response_sha256','historical_source',
            'historical_response_sha256','start_ms','end_ms','first_available_ms',
            'last_available_ms','coverage'}
    for row in evidence:
        need(type(row) is dict and set(row)==fields)
        symbol=row['symbol']
        need(type(symbol) is str and re.fullmatch('[A-Z0-9]{1,32}USDT',symbol) and symbol not in seen)
        seen.add(symbol)
        need((row['category'],row['quote_coin'],row['contract_type'],row['status'],row['origin'])==('linear','USDT','LinearPerpetual','Trading','AUTHENTICATED'))
        need(row['source']=='https://api.bybit.com/v5/market/instruments-info'
             and row['historical_source']=='https://api.bybit.com/v5/market/kline')
        need(type(row['observed_at_ms']) is int and 0<=row['observed_at_ms']<=2**53-1)
        need(all(_matches(_DIGEST,row[k]) for k in ('response_sha256','historical_response_sha256')))
        need(all(type(row[k]) is int for k in ('start_ms','end_ms','first_available_ms','last_available_ms')))
        need((row['start_ms'],row['end_ms'])==(start_ms,end_ms)
             and 0<=row['first_available_ms']<=start_ms<end_ms<=row['last_available_ms']<=2**53-1
             and row['coverage']=='OBSERVED_COMPLETE')
    return dict(count=10,symbols=sorted(seen),origin='AUTHENTICATED',
                authenticity='UNVERIFIED',availability='CLAIMED_REQUIRES_RESPONSE_VERIFICATION',
                physical_execution=False,execution_authority=False,trading_authorized=False)


def check_inventory(inventory):
    """Apply proposed isolated-test minimums to local claims, without host admission."""
    fields={'node','logical_processors','memory_bytes','free_bytes','service_names',
            'root_exists','postgres_data_exists','linked_namespace','dependencies','os'}
    need(type(inventory) is dict and set(inventory)==fields)
    issues=[]
    if inventory['node']!='ADMINIT':issues.append('WRONG_LOCAL_HOST')
    for key,minimum in (('logical_processors',4),('memory_bytes',8*1024**3),('free_bytes',20*1024**3)):
        value=inventory[key]
        if type(value) is not int or not minimum<=value<=2**63-1:issues.append(key.upper()+'_INSUFFICIENT_OR_UNKNOWN')
    services=inventory['service_names']
    need(type(services) is list and len(services)<=10000 and all(type(x) is str and len(x)<=256 for x in services))
    if any(x.casefold().startswith('unifiedadminittest-') for x in services):issues.append('SERVICE_NAMESPACE_CONFLICT')
    for key in ('root_exists','postgres_data_exists','linked_namespace'):
        if inventory[key] is not False:issues.append(key.upper()+'_CONFLICT_OR_UNKNOWN')
    os_info=inventory['os']
    if (type(os_info) is not dict or set(os_info)!={'caption','edition','build','version','architecture'}
            or any(type(v) is not str or not v.strip() or len(v)>256 for v in os_info.values())):
        issues.append('OS_IDENTITY_UNAVAILABLE')
    deps=inventory['dependencies']
    if type(deps) is not dict or set(deps)!={'python','node','postgres','git'} or any(type(x) is not dict or set(x)!={'path','file_version'}
            or type(x['path']) is not str or not re.fullmatch(r'C:\\[A-Za-z0-9 _.-]+(?:\\[A-Za-z0-9 _.-]+)*',x['path'])
            or any(part in ('.','..') for part in x['path'].split('\\'))
            or type(x['file_version']) is not str or not x['file_version'].strip() or len(x['file_version'])>256
            for x in deps.values()):issues.append('DEPENDENCIES_UNAVAILABLE')
    return dict(status='BLOCKED' if issues else 'RECORDED_UNVERIFIED',issues=issues,
                evidence_authenticity='UNVERIFIED',deployment_authorized=False,
                physical_execution=False,resource_policy='PROPOSED_TEST_MINIMUM_NOT_CAPACITY_QUALIFICATION')
