"""Schema and bounded transition checks only; not an A6/runtime adapter."""
import copy
import json
from pathlib import Path
import jsonschema
from importlib.metadata import version

root = Path(__file__).parent
schema = json.loads((root/'control-sync-v2.schema.json').read_text())
vectors = json.loads((root/'golden-vectors.json').read_text())
jsonschema.Draft202012Validator.check_schema(schema)
validator = jsonschema.Draft202012Validator(schema)
results = []
for name, value in vectors['valid'].items():
    validator.validate(value)
    results.append({'case':name,'expected':'VALID','matched':True})
for name, value in vectors['invalid'].items():
    assert list(validator.iter_errors(value)), name
    results.append({'case':name,'expected':'REJECT','matched':True})
u63 = jsonschema.Draft202012Validator({'$defs':schema['$defs'],'$ref':'#/$defs/u63'})
for value in ('0','1','999999999999999999','9223372036854775807'):
    u63.validate(value)
for value in ('9223372036854775808','9999999999999999999','01','-1',1,True):
    assert list(u63.iter_errors(value)), value
results.append({'case':'EXACT_U63_BOUNDARIES','matched':True})

def model_transition(state, frame):
    assert frame['context'] == state['context'], 'resnapshot on view/context change'
    if frame['schema'] == 'unified.control.liveness.v2':
        return copy.deepcopy(state)
    assert frame['schema'] == 'unified.control.change.v2'
    assert int(frame['previous_sequence']) == state['sequence']
    assert int(frame['change_sequence']) == state['sequence'] + 1
    assert int(frame['metadata_revision']) >= state['metadata_revision']
    assert frame['previous_state_root'] == state['root']
    identities = [x['resource_id'] for x in frame['upserts']] + frame['deletes']
    assert 0 < len(identities) <= 100 and len(identities) == len(set(identities))
    return dict(context=state['context'],sequence=int(frame['change_sequence']),
        metadata_revision=int(frame['metadata_revision']),root=frame['state_root'],live=False)

snapshot = vectors['valid']['snapshot']
state = dict(context=snapshot['context'],sequence=10,metadata_revision=25,root='1'*64,live=False)
assert model_transition(state,vectors['valid']['liveness']) == state
changed = model_transition(state,vectors['valid']['metadata_jump_change'])
assert changed['sequence'] == 11 and changed['metadata_revision'] == 30
results.append({'case':'HIDDEN_METADATA_JUMP_WITH_CONTIGUOUS_VIEW_SEQUENCE','matched':True})
results.append({'case':'LIVENESS_CANNOT_ADVANCE_CURSOR_OR_LIVE','matched':True})
bad_seq = copy.deepcopy(vectors['valid']['metadata_jump_change']); bad_seq['change_sequence']='12'
bad_view = copy.deepcopy(vectors['valid']['metadata_jump_change']); bad_view['context']['view_id']='other-view'
bad_duplicate = copy.deepcopy(vectors['valid']['metadata_jump_change']); bad_duplicate['deletes']=['model-resource']
for name, value in [('sequence_gap',bad_seq),('view_changed',bad_view),('duplicate_resource',bad_duplicate)]:
    try:
        model_transition(state,value)
    except AssertionError:
        results.append({'case':name,'expected':'REJECT','matched':True})
    else:
        raise AssertionError('model failed to reject '+name)
# A hidden-only global update does not change this projection watermark.
hidden_observation = copy.deepcopy(vectors['valid']['authority_observation'])
hidden_observation['authority_read_ref']='MODEL_NEW_BARRIER_AFTER_HIDDEN_CHANGE'
validator.validate(hidden_observation)
assert (hidden_observation['metadata_revision'],hidden_observation['change_sequence'],hidden_observation['state_root']) == ('25','10','1'*64)
results.append({'case':'HIDDEN_ONLY_UPDATE_FRESH_BARRIER_UNCHANGED_VIEW','matched':True})
old_observation = vectors['valid']['authority_observation']
assert int(old_observation['change_sequence']) != changed['sequence'] and old_observation['state_root'] != changed['root']
results.append({'case':'OLD_BARRIER_OBSERVATION_CANNOT_REFRESH_NEW_STATE','matched':True})
report = dict(schema='unified.control-sync.v2-proposal-validation.v1',result='MODEL_CHECKS_MATCH_EXPECTED',
    cases=results, jsonschema_version=version('jsonschema'),
    qualification='OUTPUT_SCHEMA_AND_BOUNDED_TRANSITION_MODELS_ONLY',
    a6_exact_consumer_ack='PENDING',runtime_endpoint='NOT_IMPLEMENTED',physical='NOT_RUN',production_go=False)
(root/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'cases':len(results),'result':report['result'],'runtime_ack':False}))
