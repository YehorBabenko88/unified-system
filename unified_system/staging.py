"""Pure bounded staging review model. No host discovery, execution or admission."""
import hashlib
import json
import re

MODULES = frozenset(('unified','grid','strattester','terminan','math'))
CHECKS = (
    'WINDOWS_10_11_BUILD_ARCHITECTURE', 'POWERSHELL_5_1_7', 'PYTHON_APPLICATION_COMPATIBILITY',
    'NODE_22_24_EXACT_RUNTIME', 'POSTGRESQL_18_POLICY_SCHEMA_ROLES', 'APPLICATION_TRANSITIVE_CLOSURE_SBOM',
    'SOURCE_ARTIFACT_PUBLISHER_TRUST', 'MANAGED_SSH_NODE_IDENTITY', 'TAILSCALE_TAG_OWNERS_ACL',
    'WINDOWS_PATH_REPARSE_ACL_FIREWALL', 'DEDICATED_NON_ADMIN_SERVICE_RIGHTS',
    'CPU_RAM_DISK_GROWTH_HEADROOM', 'FAILURE_DOMAIN_QUORUM_WITNESS', 'LEASE_EPOCH_FENCING',
    'BACKUP_ENCRYPTION_RETENTION_RESTORE_RPO_RTO', 'PREDECESSOR_ROLLBACK_COMPATIBILITY',
    'STRATTESTER_GRID_SEALED_HANDOFF', 'SEPARATE_PER_NODE_PHYSICAL_APPROVAL',
)
BLOCKERS = (
    'AUTHENTIC_RELEASE_ARTIFACTS_SIGNERS_SBOM_UNQUALIFIED', 'REAL_NODE_AND_OWNERSHIP_UNVERIFIED',
    'LEAST_PRIVILEGE_NETWORK_SERVICE_DB_RIGHTS_UNVERIFIED', 'RESTORE_HA_CAPACITY_UNVERIFIED',
    'MATH_RUNTIME_PG_PACKAGING_UNRESOLVED', 'OPTIONAL_RESEARCH_NATIVE_DEPENDENCIES_UNQUALIFIED',
    'SEALED_HANDOFF_ADMISSION_EXTERNAL', 'NO_PHYSICAL_EXECUTION_AUTHORIZATION',
)
ADD_REVIEW = ('REVIEW_SOURCE_AND_PACKAGE_CLOSURE','REVIEW_IDENTITY_AND_LEAST_PRIVILEGE',
              'REVIEW_CAPACITY_QUORUM_FENCING','REVIEW_BACKUP_RESTORE_AND_ROLLBACK',
              'REQUEST_SEPARATE_PHYSICAL_APPROVAL')
REMOVE_REVIEW = ('REVIEW_DRAIN','REVIEW_LEASE_EXPIRY_FENCING_CHECKPOINT',
                 'REVIEW_BACKUP_RESTORE_AND_ROLLBACK','REVIEW_IDENTITY_REVOCATION_AND_RETENTION',
                 'REQUEST_SEPARATE_PHYSICAL_APPROVAL')


def _exact(value, keys):
    if not isinstance(value,dict) or set(value)!=set(keys):
        raise ValueError('exact declarative schema required')


def _hex(value, length):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{'+str(length)+'}',value):
        raise ValueError('immutable digest or source pin required')


def source_lock_digest(source_lock):
    """Digest identifies untrusted declared source pins, never artifacts or admission."""
    _exact(source_lock, ('schema','sources'))
    if source_lock['schema']!='unified.staging-sources.v1':
        raise ValueError('source version')
    _exact(source_lock['sources'], MODULES)
    for pin in source_lock['sources'].values():
        _exact(pin, ('commit','tree'))
        for v in pin.values():
            _hex(v,40)
    return hashlib.sha256(json.dumps(source_lock,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def _roster(rows, previous=False):
    if not isinstance(rows,(list,tuple)) or len(rows)>64:
        raise ValueError('fleet limit 64 per roster')
    output={}
    for row in rows:
        _exact(row, ('id','modules','source_lock_sha256') if previous else ('id','modules','intent'))
        ident=row['id']
        if not isinstance(ident,str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',ident) or ident.casefold() in output:
            raise ValueError('unique bounded logical node id required')
        modules=row['modules']
        if not isinstance(modules,list) or len(modules)>5 or any(not isinstance(m,str) or m not in MODULES for m in modules) or len(set(modules))!=len(modules):
            raise ValueError('known unique module declarations required')
        if previous:
            _hex(row['source_lock_sha256'],64)
        elif not isinstance(row['intent'],str) or row['intent'] not in ('PRESENT','DRAIN','RETIRE'):
            raise ValueError('declarative intent required')
        output[ident.casefold()] = dict(row,modules=sorted(modules))
    return output


def build_staging_plan(source_lock, desired, previous=()):
    """Return review proposals from declarations; no accepted observed host facts."""
    digest=source_lock_digest(source_lock)
    wanted=_roster(desired);old=_roster(previous,previous=True)
    plans=[]
    for ident in sorted(set(wanted)|set(old)):
        target=wanted.get(ident);before=old.get(ident)
        if target is None:
            action='RETIRE'
        elif target['intent']!='PRESENT':
            if before is None:
                raise ValueError('drain or retire requires predecessor declaration')
            action=target['intent']
        elif before is None:
            action='ADD'
        elif before['source_lock_sha256']==digest and before['modules']==target['modules']:
            action='KEEP'
        else:
            action='UPDATE'
        row=target if target is not None else before
        ops=() if action=='KEEP' else REMOVE_REVIEW if action in ('DRAIN','RETIRE') else ADD_REVIEW
        removed=set(before['modules'])-set(target['modules']) if before and target else set()
        if action=='UPDATE':
            # Replacement requires a drain/fencing review even without module removal.
            removal=REMOVE_REVIEW[:-1] if removed else REMOVE_REVIEW[:2]
            ops=tuple(dict.fromkeys((*removal,*ADD_REVIEW)))
        plans.append(dict(logical_id=row['id'],action=action,status='BLOCKED',
                          host_identity='UNVERIFIED',source_lock_sha256=digest,
                          previous_source_lock_sha256=before['source_lock_sha256'] if before else None,
                          previous_modules=list(before['modules']) if before else [],
                          desired_modules=list(target['modules']) if target else [],
                          checks=[dict(check=c,status='UNVERIFIED',probe='NOT_RUN') for c in CHECKS],
                          operations=list(ops),actual_rpo='UNVERIFIED',actual_rto='UNVERIFIED',
                          execution_authorized=False))
    return dict(schema='unified.windows-staging.v1',mode='PLAN_ONLY',source_lock_sha256=digest,
                nodes=plans,blockers=list(BLOCKERS),source_provenance='NOT_EVALUATED',
                admission='BLOCKED',physical='NOT_RUN',production='NO_GO',
                mutations_performed=False,execution_authorized=False,trading_authorized=False,
                secrets_collected=False)
