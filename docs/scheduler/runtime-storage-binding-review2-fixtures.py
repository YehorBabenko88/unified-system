"""NEW semantic vectors only; no backend, authority or publication side effects."""
import copy
import json
from pathlib import Path


def fixture_relation(x):
    return (x['resolution'] == 'VERIFIED_FIXTURE'
            and x['assignment_issuance_budget_revision'] == x['reservation_issuance_budget_revision']
            and x['issued_policy_reference'] == x['current_policy_reference']
            and x['issued_policy_revision'] == x['current_policy_revision']
            and x['issued_grant_digest'] == x['current_grant_digest']
            and x['lifecycle_state'] == 'RESERVED'
            and x['resolved_lifecycle_revision'] == x['current_lifecycle_revision']
            and x['read_native_index'] == x['current_native_index']
            and x['lifecycle_current_fencing_token'] == x['current_fencing_token']
            and all(x['issuance_fencing_token'][k] == x['current_fencing_token'][k]
                    for k in x['issuance_fencing_token'] if k != 'grant_revision')
            and int(x['current_fencing_token']['grant_revision']) >= int(x['issuance_fencing_token']['grant_revision']))


base = dict(resolution='VERIFIED_FIXTURE', assignment_issuance_budget_revision='17',
            reservation_issuance_budget_revision='17', issued_policy_reference='policy-alpha',
            current_policy_reference='policy-alpha', issued_policy_revision='23', current_policy_revision='23',
            issued_grant_digest='fixture-grant-A', current_grant_digest='fixture-grant-A', lifecycle_state='RESERVED',
            resolved_lifecycle_revision='3', current_lifecycle_revision='3', read_native_index=101,
            current_native_index=101, usage_revision='9')
token = json.loads((Path(__file__).parent/'runtime-authority-review2/records.json').read_bytes())['assignment']['fencing_token']
base.update(issuance_fencing_token=copy.deepcopy(token), current_fencing_token=copy.deepcopy(token), lifecycle_current_fencing_token=copy.deepcopy(token))
assert fixture_relation(base)  # Budget17/policy23 are valid distinct domains.
b = copy.deepcopy(base); b['usage_revision'] = '10'; assert fixture_relation(b)
faults = [('current_policy_revision', '24'), ('lifecycle_state', 'REVOKED'),
          ('current_grant_digest', 'different-issuance'), ('current_lifecycle_revision', '4'),
          ('current_native_index', 102), ('resolution', 'UNKNOWN'),
          ('assignment_issuance_budget_revision', '23'), ('current_policy_reference', 'different-policy')]
for field, value in faults:
    changed = copy.deepcopy(base); changed[field] = value
    assert not fixture_relation(changed), field
renewed = copy.deepcopy(base); renewed['current_fencing_token']['grant_revision'] = '6'
renewed['lifecycle_current_fencing_token'] = copy.deepcopy(renewed['current_fencing_token'])
renewed.update(resolved_lifecycle_revision='4', current_lifecycle_revision='4', read_native_index=102, current_native_index=102)
assert fixture_relation(renewed)
assert renewed['issuance_fencing_token'] == base['issuance_fencing_token']
uncoupled = copy.deepcopy(renewed); uncoupled['lifecycle_current_fencing_token'] = copy.deepcopy(token)
assert not fixture_relation(uncoupled)
print(json.dumps(dict(status='PASS_SYNTHETIC_RELATION_ONLY_NOT_NATIVE_AUTHORITY', vectors=3+len(faults),
                      distinct_budget_policy_control=True, full_api_ack=False, production_admission=False)))
