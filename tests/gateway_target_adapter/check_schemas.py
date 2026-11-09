"""Separate optional jsonschema qualification, never folded into direct20 count."""
import copy,json,sys
from pathlib import Path
from jsonschema import Draft202012Validator
root=Path(sys.argv[1]);docs=root/'docs/intelligence/target-adapter'
schemas={key:json.loads((docs/(key+'.schema.json')).read_bytes()) for key in ('request','success-result','refusal-result')}
for value in schemas.values():Draft202012Validator.check_schema(value)
validators={key:Draft202012Validator(value) for key,value in schemas.items()}
sample=json.loads((docs/'sample-result.WIP.json').read_bytes())
checks=[]
def check(name,kind,value,valid):
    actual=validators[kind].is_valid(value);checks.append({'name':name,'expected':valid,'actual':actual})
check('actual_success','success-result',sample,True)
for kind in ('success-result','refusal-result'):
    value=copy.deepcopy(sample)
    if kind=='refusal-result':
        value.update(status='FAILED',error='TARGET_RESULT_UNAVAILABLE',result=None,research_descriptor=None,result_artifact_ref=None)
    for key,bad in [('request_id',''),('request_id','not-an-issued-request'),('request_id',sample['request_id']+'\n'),('request_sha256',sample['request_sha256']+'\n')]:
        malformed=copy.deepcopy(value);malformed[key]=bad;check(kind+':'+key+':'+repr(bad),kind,malformed,False)
for status,error,valid in [('CANCELLED','LOCAL_CANCELLED',True),('FAILED','TARGET_RESULT_UNAVAILABLE',True),
 ('UNKNOWN','TARGET_RESULT_UNAVAILABLE',True),('UNKNOWN','ORIGINAL_INTENT_OUTCOME_UNKNOWN_NO_REEXECUTION',True),
 ('UNKNOWN','LOCAL_CANCELLED',False),('CANCELLED','ORIGINAL_INTENT_OUTCOME_UNKNOWN_NO_REEXECUTION',False),('FAILED','LOCAL_CANCELLED',False)]:
    value=copy.deepcopy(sample);value.update(status=status,error=error,result=None,research_descriptor=None,result_artifact_ref=None)
    check(status+':'+error,'refusal-result',value,valid)
print(json.dumps({'checks':checks,'passed':sum(x['expected']==x['actual'] for x in checks),'total':len(checks)},indent=2))
assert all(x['expected']==x['actual'] for x in checks)
