"""Design-only structural checks, not authority/storage fault acceptance.

Requires jsonschema 4.26.0; installed outside this repository for review.
"""
import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker


class AssignmentSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[2] / 'docs/scheduler/assignment-v1.schema.json'
        cls.schema = json.loads(path.read_text(encoding='utf-8'))
        cls.validator = Draft202012Validator(cls.schema, format_checker=FormatChecker())

    def setUp(self):
        scope = dict(job_id='job1', dataset_id='dataset1', source_id='source1', partition_id='partition1')
        self.grant = dict(schema_version='assignment.v1', assignment_id='assignment1', scope=scope,
                          assignment_revision='1', lease_epoch='9', authority_term='2', grant_revision='1',
                          worker_id='pc1', worker_incarnation_id='550e8400-e29b-41d4-a716-446655440000',
                          state='ACTIVE', issued_at_ms=1000, expires_at_ms=2000, fencing_token='opaque',
                          storage=dict(storage_reservation_id='reservation1', storage_budget_revision='3',
                                       scope=copy.deepcopy(scope), expires_at_ms=1900, byte_limit='4096'),
                          capacity=dict(node_id='pc1', observation_revision='1', observed_at_ms=900,
                                        fresh_until_ms=1500), checkpoint=None, drain=None)

    def test_schema_and_active_grant(self):
        Draft202012Validator.check_schema(self.schema)
        self.validator.validate(self.grant)

    def test_every_top_level_field_required(self):
        for key in self.grant:
            with self.subTest(key=key):
                value = copy.deepcopy(self.grant)
                del value[key]
                self.assertFalse(self.validator.is_valid(value))

    def test_unknown_properties_rejected_at_each_object(self):
        for key in (None, 'scope', 'storage', 'capacity'):
            with self.subTest(key=key):
                value = copy.deepcopy(self.grant)
                target = value if key is None else value[key]
                target['unknown'] = 'x'
                self.assertFalse(self.validator.is_valid(value))

    def test_counter_wire_types(self):
        for invalid in (0, 1, True, '0', '-1', '01', '1.0', ''):
            with self.subTest(value=invalid):
                self.grant['assignment_revision'] = invalid
                self.assertFalse(self.validator.is_valid(self.grant))
        self.grant['assignment_revision'] = '900719925474099312345'
        self.validator.validate(self.grant)

    def test_drain_binding_and_unique_batches(self):
        self.grant['state'] = 'DRAINING'
        self.assertFalse(self.validator.is_valid(self.grant))
        self.grant['drain'] = dict(deadline_ms=1800, permitted_batch_ids=['batch1'], max_remaining_bytes='512')
        self.validator.validate(self.grant)
        self.grant['drain']['permitted_batch_ids'].append('batch1')
        self.assertFalse(self.validator.is_valid(self.grant))

    def test_incarnation_and_checkpoint_digest(self):
        self.grant['worker_incarnation_id'] = 'not-a-uuid'
        self.assertFalse(self.validator.is_valid(self.grant))
        self.grant['worker_incarnation_id'] = '550e8400-e29b-41d4-a716-446655440000'
        self.grant['checkpoint'] = dict(ref='cp1', revision='1', sha256='a' * 64)
        self.validator.validate(self.grant)
        self.grant['checkpoint']['sha256'] = 'bad'
        self.assertFalse(self.validator.is_valid(self.grant))

    def test_schema_does_not_claim_semantic_authorization(self):
        # Structurally valid but forbidden semantically: the real ordered adapter
        # MUST reject mismatched scopes and reversed lifetimes.
        self.grant['storage']['scope']['job_id'] = 'other-job'
        self.grant['expires_at_ms'] = 0
        self.validator.validate(self.grant)


if __name__ == '__main__':
    unittest.main()
