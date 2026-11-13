"""Static V2 authorization/source DATA only; no workflow CLI or native body.

Caller context is untrusted data. Valid bytes/source are not review, software
qualification, artifact admission or permission to run A5.
"""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path,PurePosixPath
import re
import stat
from unified_system import collector_operational_review as codec

CONTEXT_FIELDS=frozenset('event repository sha source_sha attempt run_id actor authorization_commit authorization_sha256 job_name runner_name'.split())
SOURCE_MANIFEST='integration/collector/v1/source-inputs.json'
HELPER_SHA256='b4fdd6cc2dea47a4fe8da0ce400004a20e36d4f401fb9bb37d20c0a597857df5'
MISSING_GATES=('QUALIFIED_WORKFLOW_BRIDGE_MISSING','QUALIFIED_FACTORY_MISSING',
 'QUALIFIED_ARTIFACT_SOURCE_CLOSURE_MISSING','ACTUAL_PROTECTED_REVIEW_NOT_ACQUIRED',
 'ACTUAL_SOURCE_CAPACITY_OWNER_ADMISSION_MISSING')
CODES=frozenset(('STATIC_CONTEXT_REJECTED','STATIC_AUTHORIZATION_REJECTED','STATIC_SOURCE_VERIFICATION_FAILED','STATIC_PREFLIGHT_BLOCKED','CONFIG_CONTEXT_REJECTED','CONFIG_AUTHORIZATION_REJECTED','CONFIG_ACQUISITION_REJECTED','CONFIG_PROTECTION_REJECTED'))

class StaticPreflightBlocked(ValueError):
    def __init__(self,code):
        self.code=code if type(code) is str and code in CODES else 'STATIC_PREFLIGHT_BLOCKED'
        super().__init__(self.code)

def _need(value):
    if not value:raise ValueError('STATIC_DATA_REJECTED')

def _keys(value,expected):
    _need(type(value) is dict and all(type(key) is str for key in value))
    _need(set(value)==expected)

def _context(context):
    _keys(context,CONTEXT_FIELDS)
    _need(all(type(v) is str for v in context.values()))
    _need(context['event']=='workflow_dispatch' and context['repository']==codec.REPOSITORY and context['attempt']=='1')
    _need(re.fullmatch('[1-9][0-9]{0,18}',context['run_id']) is not None and int(context['run_id'])<=2**63-1)
    _need(re.fullmatch('[a-f0-9]{40}',context['sha']) is not None and context['source_sha']==context['sha'])
    _need(re.fullmatch('[a-f0-9]{40}',context['authorization_commit']) is not None and re.fullmatch('[a-f0-9]{64}',context['authorization_sha256']) is not None)
    _need(context['job_name']=='collector-preflight' and re.fullmatch('[A-Za-z0-9-]{1,39}',context['actor']) is not None)
    _need(re.fullmatch('[A-Za-z0-9 _.-]{1,128}',context['runner_name']) is not None)

def _ordinary(path,*,file=False):
    _need(isinstance(path,Path) and path.is_absolute() and '..' not in path.parts and not str(path).startswith(('\\\\','//')))
    current=Path(path.anchor)
    for index,part in enumerate((None,*path.parts[1:])):
        if part is not None:current/=part
        info=current.lstat();leaf=index==len(path.parts)-1
        _need(not(stat.S_ISLNK(info.st_mode) or getattr(info,'st_reparse_tag',0) or getattr(info,'st_file_attributes',0)&1024))
        _need(stat.S_ISREG(info.st_mode) if leaf and file else stat.S_ISDIR(info.st_mode))
        if leaf and file:_need(info.st_nlink==1)
    return path

def _read_ordinary(path,limit):
    path=_ordinary(path,file=True);before=path.lstat();_need(0<before.st_size<=limit)
    fields=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)
    with path.open('rb') as stream:
        held=os.fstat(stream.fileno());_need(fields(before)==fields(held))
        raw=stream.read(limit+1);after=os.fstat(stream.fileno())
    current=_ordinary(path,file=True).lstat()
    _need(fields(before)==fields(after)==fields(current) and held.st_ctime_ns==after.st_ctime_ns and len(raw)==before.st_size)
    return raw

def _read_source_manifest(root):
    _ordinary(root)
    return _read_ordinary(root/SOURCE_MANIFEST,262144)

def _primary_source(root,head,tree):
    """Actual bounded primary Git acquisition; replaced only in inert tests."""
    path=root/'tools/raw_capture/qualify.py';raw=_read_ordinary(path,131072)
    _need(hashlib.sha256(raw).hexdigest()==HELPER_SHA256)
    spec=importlib.util.spec_from_file_location('_collector_static_primary',path)
    module=importlib.util.module_from_spec(spec)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    return module.primary(root,head,tree)

def _relative(value):
    _need(type(value) is str and 0<len(value)<=1024 and not value.startswith('/') and '\\' not in value and ':' not in value)
    _need(all(part not in ('','.','..') for part in value.split('/')))
    return PurePosixPath(value)

def _snapshot(snapshot,source,raw):
    _keys(snapshot,{'head','tree','files','directories'})
    _need(type(snapshot['head']) is str and type(snapshot['tree']) is str)
    _need(snapshot['head']==source['head'] and snapshot['tree']==source['tree'])
    files=snapshot['files'];directories=snapshot['directories']
    _need(type(files) is dict and 1<=len(files)<=10000 and type(directories) is list)
    _need(all(type(name) is str for name in files))
    total=0;derived=set();folded=set()
    for name,pin in files.items():
        relative=_relative(name);_need(name.casefold() not in folded);folded.add(name.casefold())
        derived.update(p.as_posix() for p in relative.parents if p.as_posix()!='.')
        _keys(pin,{'oid','bytes','sha256'})
        _need(type(pin['bytes']) is int and 0<=pin['bytes']<=20*1024*1024)
        _need(type(pin['oid']) is str and re.fullmatch('[a-f0-9]{40}',pin['oid']) is not None and type(pin['sha256']) is str and re.fullmatch('[a-f0-9]{64}',pin['sha256']) is not None)
        total+=pin['bytes'];_need(total<=64*1024*1024)
    _need(all(type(name) is str for name in directories) and directories==sorted(derived))
    _need(len({name.casefold() for name in (*files,*directories)})==len(files)+len(directories))
    pin=files[SOURCE_MANIFEST]
    _need(pin['bytes']==len(raw) and pin['sha256']==source['source_manifest_sha256']==hashlib.sha256(raw).hexdigest())
    _need(pin['oid']==hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest())
    digest=hashlib.sha256((json.dumps(snapshot,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()).hexdigest()
    return dict(files=len(files),bytes=total,primary_snapshot_sha256=digest,source_manifest_path=SOURCE_MANIFEST,
                source_manifest_sha256=pin['sha256'],source_manifest_bytes=len(raw),kind='STATIC_PRIMARY_BYTES_NOT_OWNER_ADMISSION')

def select_static_authorization(authorization_raw:bytes,*,context:dict,source_root:Path,now=None)->dict:
    """Detached STATIC_VALID_NOT_ADMITTED evidence, never a phase grant.

    No provider/kernel/factory/callback/readiness parameter is accepted. This
    fixed V1 SourceManifest is byte-bound only; genuine A5 source admission
    must validate its semantics and software/capsule combination.
    """
    try:_context(context)
    except Exception:raise StaticPreflightBlocked('STATIC_CONTEXT_REJECTED') from None
    try:
        _need(type(authorization_raw) is bytes and 0<len(authorization_raw)<=codec.LIMIT)
        _need(hashlib.sha256(authorization_raw).hexdigest()==context['authorization_sha256'])
        _need(now is None or type(now) in (int,float) and math.isfinite(now))
        authorization=codec.parse_authorization(authorization_raw,now=now)
        _need(authorization['source']['head']==context['sha'])
    except Exception:raise StaticPreflightBlocked('STATIC_AUTHORIZATION_REJECTED') from None
    try:
        root=_ordinary(source_root);raw=_read_source_manifest(root)
        _need(hashlib.sha256(raw).hexdigest()==authorization['source']['source_manifest_sha256'])
        snapshot=_primary_source(root,context['sha'],authorization['source']['tree'])
        evidence=_snapshot(snapshot,authorization['source'],raw)
        _need(_read_source_manifest(root)==raw)
    except Exception:raise StaticPreflightBlocked('STATIC_SOURCE_VERIFICATION_FAILED') from None
    result=dict(status='STATIC_VALID_NOT_ADMITTED',selected=False,scope='STATIC_DATA_NOT_ADMISSION',
      authorization_id=authorization['authorization_id'],cohort_id=authorization['cohort_id'],
      authorization_commit=context['authorization_commit'],authorization_sha256=context['authorization_sha256'],
      source=authorization['source'],source_evidence=evidence,target=authorization['target'],
      capsule=authorization['capsule'],missing_gates=list(MISSING_GATES))
    return json.loads(json.dumps(result,allow_nan=False))


ENVIRONMENT_NAME='collector-c3-operational-v2'
ENVIRONMENT_ENDPOINT='https://api.github.com/repos/'+codec.REPOSITORY+'/environments/'+ENVIRONMENT_NAME


def _environment_config_raw():
    """Fixed broker-only readonly acquisition; never a review or permission."""
    from scripts import ci_service_operational_admission as legacy
    token=os.environ.get('GITHUB_TOKEN')
    _need(type(token) is str and 0<len(token)<=4096 and '\r' not in token and '\n' not in token)
    return legacy.get(ENVIRONMENT_ENDPOINT,token)


def _config_projection(environment,approved_by,context):
    from scripts import ci_service_operational_admission as legacy
    _need(type(environment) is dict)
    codec.integer(environment.get('id'));_need(type(environment.get('name')) is str and environment['name']==ENVIRONMENT_NAME)
    for key in ('can_admins_bypass',):
        if key in environment:_need(type(environment[key]) is bool)
    if environment.get('deployment_branch_policy') is not None:
        policy=environment['deployment_branch_policy'];_keys(policy,{'protected_branches','custom_branch_policies'})
        _need(all(type(value) is bool for value in policy.values()))
    rules=environment.get('protection_rules');_need(type(rules) is list and 1<=len(rules)<=16)
    seen_ids=set();seen_types=set();required=None
    for rule in rules:
        _need(type(rule) is dict);codec.integer(rule.get('id'))
        kind=rule.get('type');_need(type(kind) is str and kind in ('required_reviewers','wait_timer'))
        _need(rule['id'] not in seen_ids and kind not in seen_types);seen_ids.add(rule['id']);seen_types.add(kind)
        if 'can_admins_bypass' in rule:_need(type(rule['can_admins_bypass']) is bool)
        if kind=='wait_timer':codec.integer(rule.get('wait_timer'),0,43200);continue
        required=rule;_need(type(rule.get('prevent_self_review')) is bool)
        reviewers=rule.get('reviewers');_need(type(reviewers) is list and 1<=len(reviewers)<=100)
        ids=set();logins=set()
        for item in reviewers:
            _need(type(item) is dict and type(item.get('type')) is str and item['type']=='User')
            user=item.get('reviewer');_need(type(user) is dict)
            codec.integer(user.get('id'));codec.text(user.get('login'),r'[A-Za-z0-9-]{1,39}')
            _need(type(user.get('type')) is str and user['type']=='User')
            _need(user['id'] not in ids and user['login'].lower() not in logins)
            ids.add(user['id']);logins.add(user['login'].lower())
    _need(required is not None)
    # None means CONFIG ONLY, preserving the original legacy preflight semantics.
    # It MUST NOT stand in for V2's later non-None actual review history.
    legacy.verify_protected_review(context,environment,None,environment_name=ENVIRONMENT_NAME,approved_by=approved_by)
    matches=[item['reviewer'] for item in required['reviewers'] if item['reviewer']['login']==approved_by]
    _need(len(matches)==1)
    return dict(id=environment['id'],name=ENVIRONMENT_NAME,
        required_reviewer=dict(id=matches[0]['id'],login=matches[0]['login']),
        prevent_self_review=required['prevent_self_review'])


def observe_protected_environment_config(authorization_raw:bytes,*,context:dict,now=None)->dict:
    """CONFIG_OBSERVED_NOT_ADMITTED; cannot select/schedule a job or call A5.

    Invoke in a job with NO environment declaration before any environment job
    can be scheduled. Missing/403/redirect/unconfigured protection always deny.
    This API does not implement workflow routing or attest future scheduling.
    """
    try:_context(context)
    except Exception:raise StaticPreflightBlocked('CONFIG_CONTEXT_REJECTED') from None
    try:
        _need(type(authorization_raw) is bytes and 0<len(authorization_raw)<=codec.LIMIT)
        _need(hashlib.sha256(authorization_raw).hexdigest()==context['authorization_sha256'])
        _need(now is None or type(now) in (int,float) and math.isfinite(now))
        authorization=codec.parse_authorization(authorization_raw,now=now)
        _need(authorization['source']['head']==context['sha'])
    except Exception:raise StaticPreflightBlocked('CONFIG_AUTHORIZATION_REJECTED') from None
    try:
        raw=_environment_config_raw()
        _need(type(raw) is bytes and 0<len(raw)<=codec.LIMIT)
    except Exception:raise StaticPreflightBlocked('CONFIG_ACQUISITION_REJECTED') from None
    try:
        from scripts import ci_service_operational_admission as legacy
        environment=legacy.decode_json(raw)
        projection=_config_projection(environment,authorization['approved_by'],context)
        result=dict(status='CONFIG_OBSERVED_NOT_ADMITTED',selected=False,execution_authority=False,
            environment=projection,response_body=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)),
            missing_gates=list(MISSING_GATES))
        return json.loads(json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False))
    except Exception:raise StaticPreflightBlocked('CONFIG_PROTECTION_REJECTED') from None
