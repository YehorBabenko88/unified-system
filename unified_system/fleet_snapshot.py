"""Validate unqualified fleet display envelopes at both read boundaries."""
import json
import math
from .contracts import ContractError


def validate_fleet(value):
    if not isinstance(value, dict):
        raise ContractError('invalid fleet snapshot')
    if value == {'status': 'UNAVAILABLE', 'nodes': [], 'links': []}:
        return value
    if set(value) != {'mode','status','execution_authorized','nodes','links','databases','alerts','source_provenance','physical','production'}:
        raise ContractError('invalid fleet schema')
    if (value.get('mode') != 'PLAN_ONLY' or value.get('status') != 'PLAN_ONLY'
            or value.get('execution_authorized') is not False
            or value.get('source_provenance') != 'NOT_EVALUATED'
            or value.get('physical') != 'NOT_RUN' or value.get('production') != 'NO_GO'):
        raise ContractError('invalid fleet authority')
    if not isinstance(value.get('nodes'), list) or len(value['nodes']) > 256:
        raise ContractError('invalid fleet nodes')
    if value.get('links') != [] or value.get('databases') != []:
        raise ContractError('unqualified fleet links or databases')
    if value.get('alerts') != []:
        raise ContractError('unqualified fleet alerts')
    ids = set()
    for node in value['nodes']:
        if not isinstance(node, dict) or set(node) != {'id','epoch','sequence','state','zone','modules','last_heartbeat_ms','cpu','memory','disk','available_resources','db_sizes','identity_verified'}:
            raise ContractError('invalid fleet node schema')
        ident = node['id']
        if not isinstance(ident,str) or not 1 <= len(ident) <= 128 or ident in ids:
            raise ContractError('invalid fleet node identity')
        ids.add(ident)
        if (type(node['epoch']) is not int or node['epoch'] < 1 or type(node['sequence']) is not int or node['sequence'] < 0
                or not isinstance(node['zone'],str) or not 1 <= len(node['zone']) <= 1024
                or node['state'] not in ('APPROVED','ACTIVE','DRAINING','RETIRED','OFFLINE','SUSPECT','QUARANTINED')):
            raise ContractError('invalid fleet node state')
        heartbeat = node['last_heartbeat_ms']
        if heartbeat is not None and (type(heartbeat) is not int or heartbeat < 0):
            raise ContractError('invalid fleet heartbeat')
        if node['identity_verified'] is not False or node['modules'] != [] or any(node[k] is not None for k in ('cpu','memory','disk','db_sizes')):
            raise ContractError('unqualified fleet telemetry')
        available = node['available_resources']
        if available is not None and (not isinstance(available,dict) or set(available) != {'cpu','memory','disk'} or any(type(x) not in (int,float) or not math.isfinite(x) or not 0 <= x <= 2**53-1 for x in available.values())):
            raise ContractError('invalid fleet resource observation')
    encoded = json.dumps(value, allow_nan=False)
    if len(encoded.encode('utf-8')) > 524288:
        raise ContractError('fleet response bounds')
    return value
