"""Semantic review vectors only; NOT an authority or publication implementation."""
import copy
import json


def fixture_relation(value):
    # All inputs are synthetic. In production every 'current' input and issuer
    # proof must come from actual A2/A4 admitted records, never caller claims.
    return (value['resolution'] == 'VERIFIED_FIXTURE'
            and value['issued_policy'] == value['current_policy']
            and value['issued_grant_digest'] == value['current_grant_digest']
            and value['lifecycle_state'] == 'RESERVED'
            and value['resolved_lifecycle_revision'] == value['current_lifecycle_revision']
            and value['read_native_index'] == value['current_native_index'])


base = dict(resolution='VERIFIED_FIXTURE', issued_policy='7', current_policy='7',
            issued_grant_digest='fixture-grant-A', current_grant_digest='fixture-grant-A',
            lifecycle_state='RESERVED', resolved_lifecycle_revision='3', current_lifecycle_revision='3',
            read_native_index=101, current_native_index=101, usage_revision='8')
assert fixture_relation(base)
b_usage = copy.deepcopy(base); b_usage['usage_revision'] = '9'
assert fixture_relation(b_usage)  # B changing usage does not change A's policy.
for field, value in [('current_policy', '8'), ('lifecycle_state', 'REVOKED'),
                     ('current_grant_digest', 'different-grant-under-same-id'),
                     ('current_native_index', 102), ('resolution', 'UNKNOWN')]:
    changed = copy.deepcopy(base); changed[field] = value
    assert not fixture_relation(changed), field
print(json.dumps(dict(status='PASS_SYNTHETIC_RELATION_ONLY_NOT_NATIVE_AUTHORITY', vectors=6,
                      full_api_ack=False, production_admission=False)))
