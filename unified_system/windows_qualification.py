"""Edition qualification plan review, not a runtime or installation admission API.

Until an independent evidence verifier is implemented, PASS claims are rejected
rather than trusting JSON flags, Pro receipts or another node's results.
"""


class QualificationError(ValueError):
    pass


CHECKS=frozenset({'SSH','SERVICES','NONADMIN','MTLS_KEYS','PIPE_IPC','FIREWALL_ESET',
    'RUNTIMES','RESEARCH_WORKER','SCHEDULER','STORAGE','TERMINAN','RESTART_LOGOFF',
    'DIRECT_LAN','NO_PRO_ONLY'})
_GROUPS={
    'WINDOWS_PRO_QUALIFICATION':('Windows 11 Pro',frozenset({'LS5','PC4','PC3','PC2'})),
    'WINDOWS_HOME_QUALIFICATION':('Windows 11 Home',frozenset({'PC1','LS7'})),
}
_PENDING=frozenset({'NOT_RUN','PENDING','PARTIAL','BLOCKED','EVIDENCE_REVIEW_PENDING'})


def _need(value,reason):
    if value is not True:raise QualificationError(reason)


def review_matrix(value):
    _need(type(value) is dict and value.get('schema')=='unified.windows-edition-qualification.v1','SCHEMA')
    tracks=value.get('tracks')
    _need(type(tracks) is dict and set(tracks)==set(_GROUPS),'TRACK_INVENTORY')
    for name,(edition,nodes) in _GROUPS.items():
        track=tracks[name]
        _need(type(track) is dict and track.get('status') in _PENDING,'TRACK_UNVERIFIED_CLAIM')
        _need(track.get('pass_inheritance')=='FORBIDDEN_BETWEEN_EDITIONS_OR_NODES','PASS_INHERITANCE')
        rows=track.get('nodes');_need(type(rows) is dict and set(rows)==nodes,'NODE_INVENTORY')
        for node,row in rows.items():
            _need(type(row) is dict and row.get('edition')==edition,'EDITION_MISMATCH')
            expected='WORKER_TERMINAN' if node in {'PC1','LS7'} else 'WORKER' if node=='PC2' else 'COORDINATOR'
            _need(row.get('role')==expected,'ROLE_NOT_APPROVED')
            _need(row.get('physical_deployment')=='BLOCKED','PHYSICAL_NOT_AUTHORIZED')
            checks=row.get('checks');_need(type(checks) is list and len(checks)==14,'CHECK_COUNT')
            _need(all(type(x) is dict and type(x.get('id')) is str for x in checks),'CHECK_TYPE')
            _need({x['id'] for x in checks}==CHECKS,'CHECK_INVENTORY')
            for check in checks:
                _need(type(check.get('status')) is str and check['status'] in _PENDING,'EVIDENCE_ISSUER_NOT_VERIFIED')
                _need(type(check.get('evidence')) is list,'EVIDENCE_TYPE')
    return {'status':'CONFIGURATION_VALID_QUALIFICATION_PENDING',
        'home_nodes':['LS7','PC1'],'pending_home_checks':28,
        'independent_evidence_verifier':'NOT_IMPLEMENTED',
        'runtime_qualified':False,'physical_deployment_authorized':False}
