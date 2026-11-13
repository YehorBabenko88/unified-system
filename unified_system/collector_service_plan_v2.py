"""Distinct Collector V2 pure policies; no V1 pin mutation or host admission."""
import copy
from .collector_service_plan import _keys, _need

SCHEMA='unified.owned-collector-stopped-service.v2'


def validate_collector_stop_policy(value):
 """Pure shape/arithmetic only, not vendor or timing qualification."""
 fields={'transport','console','skip_methods','kill_process_tree',
         'console_grace_ms','owner_retire_seconds','actuation_timeout_seconds'}
 _keys(value,fields)
 _need(type(value['transport']) is str and value['transport']=='NSSM_CONSOLE_CTRL_C_V1')
 _need(all(type(value[k]) is int for k in fields if k!='transport'))
 _need(value['console']==0 and value['skip_methods']==6 and value['kill_process_tree']==0)
 _need(value['owner_retire_seconds']==5 and 1<=value['actuation_timeout_seconds']<=60)
 _need(value['console_grace_ms']>0 and
       value['console_grace_ms']+5000<value['actuation_timeout_seconds']*1000)
 return copy.deepcopy(value)
