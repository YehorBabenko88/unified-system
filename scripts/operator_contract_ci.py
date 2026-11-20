"""Root-only Git-byte/JUnit evidence gate; modeled contracts, never native auth proof."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

FIXTURE_LOCK_SHA256 = "6654ea74257c1141553c34cef2e9de5355b9b7ddb3ab4a834ae382ae0fd47b12"
REQUIRED_CASES = [
    ("tests.test_operator_control_plane.OperatorTests", "test_backend_absent_never_returns_fake_receipt"),
    ("tests.test_operator_control_plane.OperatorTests", "test_current_grants_checked_on_every_retry"),
    ("tests.test_operator_control_plane.OperatorTests", "test_malformed_private_receipt_never_disclosed"),
    ("tests.test_operator_control_plane.OperatorTests", "test_missing_provider_fails_closed"),
    ("tests.test_operator_control_plane.OperatorTests", "test_receipt_rechecks_current_actor_scope"),
    ("tests.test_operator_control_plane.OperatorTests", "test_revocation_during_receipt_query_prevents_disclosure"),
    ("tests.test_operator_control_plane.OperatorTests", "test_role_backend_enforced_and_unknown_action_denied"),
    ("tests.test_operator_control_plane.OperatorTests", "test_serialized_or_unknown_capability_principal_denied"),
    ("tests.test_operator_control_plane.OperatorTests", "test_strict_boundaries"),
    ("tests.test_operator_control_plane.OperatorTests", "test_submit_receipt_must_match_entire_intent"),
    ("tests.test_operator_control_plane.OperatorTests", "test_two_windows_retry_and_conflicting_revision"),
    ("tests.test_operator_control_plane.OperatorTests", "test_untrusted_actor_role_and_machine_denied"),
    ("tests.test_operator_control_plane.OperatorTests", "test_zero_grant_denied_before_backend_io"),
    ("tests.test_operator_control_plane.StreamTests", "test_invalid_snapshot_cannot_mark_live"),
    ("tests.test_operator_control_plane.StreamTests", "test_snapshot_gap_generation_and_staleness"),
    ("tests.test_operator_command_composition.CommandCompositionTests", "test_commit_retry_read_and_unknown_reconcile_actual_bridge"),
    ("tests.test_operator_command_composition.CommandCompositionTests", "test_lost_response_reconciles_same_command_and_two_windows"),
    ("tests.test_operator_command_composition.CommandCompositionTests", "test_no_quorum_unknown_has_no_invented_owner"),
    ("tests.test_lifecycle.LifecycleTests", "test_cached_response_tamper_rejected"),
    ("tests.test_lifecycle.LifecycleTests", "test_cancel_retry_cannot_retain_handoff"),
    ("tests.test_lifecycle.LifecycleTests", "test_completed_initial_state_cannot_be_injected"),
    ("tests.test_lifecycle.LifecycleTests", "test_concurrent_writer_fenced"),
    ("tests.test_lifecycle.LifecycleTests", "test_default_verifier_denies_self_assertion"),
    ("tests.test_lifecycle.LifecycleTests", "test_failed_commit_does_not_advance"),
    ("tests.test_lifecycle.LifecycleTests", "test_idempotency_collision_and_sequence"),
    ("tests.test_lifecycle.LifecycleTests", "test_missing_modules_zero_to_four"),
    ("tests.test_lifecycle.LifecycleTests", "test_monitoring_barrier_and_math_independence"),
    ("tests.test_lifecycle.LifecycleTests", "test_old_epoch_operation_cannot_replay_after_recovery"),
    ("tests.test_lifecycle.LifecycleTests", "test_read_only_api_and_safe_provider_failure"),
    ("tests.test_lifecycle.LifecycleTests", "test_recovery_revalidates_and_invalidates_downstream"),
    ("tests.test_lifecycle.LifecycleTests", "test_restart_cannot_replay_cached_completion_before_revalidation"),
    ("tests.test_lifecycle.LifecycleTests", "test_sequence_and_no_authority"),
    ("tests.test_lifecycle.LifecycleTests", "test_tampered_state_rejected"),
    ("tests.test_lifecycle.LifecycleTests", "test_verifier_cannot_bless_different_status"),
    ("tests.test_lifecycle.LifecycleTests", "test_version_and_retired_owners_are_rejected"),
    ("tests.test_consul_command_store", "test_committed_research_state_retry_and_conflicts"),
    ("tests.test_consul_command_store", "test_unknown_committed_response_reconciles_without_reexecution"),
    ("tests.test_consul_command_store", "test_untrusted_envelope_denied_without_mutation[change0]"),
    ("tests.test_consul_command_store", "test_untrusted_envelope_denied_without_mutation[change1]"),
    ("tests.test_consul_command_store", "test_untrusted_envelope_denied_without_mutation[change2]"),
    ("tests.test_consul_command_store", "test_untrusted_envelope_denied_without_mutation[change3]"),
    ("tests.test_consul_command_store", "test_untrusted_envelope_denied_without_mutation[change4]"),
    ("tests.test_consul_command_store", "test_untrusted_envelope_denied_without_mutation[change5]"),
    ("tests.test_consul_command_store", "test_untrusted_envelope_denied_without_mutation[change6]"),
    ("tests.test_consul_command_store", "test_untrusted_envelope_denied_without_mutation[change7]"),
    ("tests.test_consul_command_store", "test_untrusted_envelope_denied_without_mutation[change8]"),
    ("tests.test_consul_command_store", "test_untrusted_envelope_denied_without_mutation[change9]"),
    ("tests.test_consul_command_store", "test_untrusted_envelope_denied_without_mutation[change10]"),
    ("tests.test_consul_command_store", "test_untrusted_envelope_denied_without_mutation[change11]"),
    ("tests.test_consul_command_store", "test_no_auth_revocation_and_no_quorum_deny"),
    ("tests.test_consul_command_store", "test_structural_principal_rejects_forgery_and_machine_authority[True]"),
    ("tests.test_consul_command_store", "test_structural_principal_rejects_forgery_and_machine_authority[principal1]"),
    ("tests.test_consul_command_store", "test_structural_principal_rejects_forgery_and_machine_authority[principal2]"),
    ("tests.test_consul_command_store", "test_structural_principal_rejects_forgery_and_machine_authority[principal3]"),
    ("tests.test_consul_command_store", "test_structural_principal_rejects_forgery_and_machine_authority[principal4]"),
    ("tests.test_consul_command_store", "test_current_authentication_rechecked_before_commit_and_replay"),
    ("tests.test_consul_command_store", "test_raw_public_decoder_rejects_ambiguity_depth_and_bounds[duplicate]"),
    ("tests.test_consul_command_store", "test_raw_public_decoder_rejects_ambiguity_depth_and_bounds[nonfinite]"),
    ("tests.test_consul_command_store", "test_raw_public_decoder_rejects_ambiguity_depth_and_bounds[overflow]"),
    ("tests.test_consul_command_store", "test_raw_public_decoder_rejects_ambiguity_depth_and_bounds[depth]"),
    ("tests.test_consul_command_store", "test_raw_public_decoder_rejects_ambiguity_depth_and_bounds[bytes]"),
    ("tests.test_consul_command_store", "test_raw_public_decoder_rejects_ambiguity_depth_and_bounds[utf8]"),
    ("tests.test_consul_command_store", "test_raw_public_decoder_rejects_ambiguity_depth_and_bounds[array]"),
    ("tests.test_consul_command_store", "test_raw_public_decoder_roundtrip"),
    ("tests.test_consul_command_store", "test_receipt_decoder_rejects_private_unknown_fields"),
    ("tests.test_consul_command_store", "test_stored_kv_corruption_never_discloses_arbitrary_receipt[corrupt0]"),
    ("tests.test_consul_command_store", "test_stored_kv_corruption_never_discloses_arbitrary_receipt[corrupt1]"),
    ("tests.test_consul_command_store", "test_stored_kv_corruption_never_discloses_arbitrary_receipt[corrupt2]"),
    ("tests.test_consul_command_store", "test_stored_kv_corruption_never_discloses_arbitrary_receipt[corrupt3]"),
    ("tests.test_consul_command_store", "test_own_receipt_read_needs_read_capability_not_mutation_capability"),
    ("tests.test_consul_command_store", "test_postcommit_revocation_blocks_disclosure_without_undoing_committed_intent"),
    ("tests.test_consul_command_store", "test_cross_actor_receipt_requires_explicit_audit_capability[False]"),
    ("tests.test_consul_command_store", "test_cross_actor_receipt_requires_explicit_audit_capability[True]"),
    ("tests.test_consul_command_store", "test_existing_aggregate_corruption_denies_cas[change0]"),
    ("tests.test_consul_command_store", "test_existing_aggregate_corruption_denies_cas[change1]"),
    ("tests.test_consul_command_store", "test_existing_aggregate_corruption_denies_cas[change2]"),
    ("tests.test_consul_command_store", "test_existing_aggregate_corruption_denies_cas[change3]"),
    ("tests.test_consul_command_store", "test_existing_aggregate_corruption_denies_cas[change4]"),
    ("tests.test_consul_command_store", "test_existing_aggregate_corruption_denies_cas[change5]"),
    ("tests.test_consul_command_store", "test_untrusted_storage_json_uses_strict_decoder[duplicate]"),
    ("tests.test_consul_command_store", "test_untrusted_storage_json_uses_strict_decoder[nonfinite]"),
    ("tests.test_consul_command_store", "test_untrusted_storage_json_uses_strict_decoder[overflow]"),
    ("tests.test_consul_command_store", "test_untrusted_storage_json_uses_strict_decoder[bytes]"),
    ("tests.test_consul_command_store", "test_untrusted_storage_json_uses_strict_decoder[depth]"),
    ("tests.test_consul_command_store", "test_zero_grant_principal_cannot_submit_or_query_private_receipt"),
    ("tests.test_consul_command_store", "test_principal_dto_is_shared_and_no_retired_backend_alias"),
]


def require_pin(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{40}', value) is None:
        raise ValueError('ROOT_PIN_REQUIRED')


def require_fixture_lock(raw):
    if type(raw) is not bytes or hashlib.sha256(raw).hexdigest() != FIXTURE_LOCK_SHA256:
        raise ValueError('ROOT_FIXTURE_LOCK_MISMATCH')
    return FIXTURE_LOCK_SHA256


def validate_junit(path):
    root = ET.parse(path).getroot()
    cases = root.findall('.//testcase')
    observed = [(case.get('classname'), case.get('name')) for case in cases]
    if (len(observed) != len(REQUIRED_CASES) or len(set(observed)) != len(REQUIRED_CASES)
            or set(observed) != set(REQUIRED_CASES)
            or root.findall('.//skipped') or root.findall('.//failure') or root.findall('.//error')):
        raise ValueError('REQUIRED_TEST_INVENTORY_FAILED')
    return len(cases)


def receipt(unified, expected_unified, junit=None):
    require_pin(expected_unified)
    unified = Path(unified).resolve()
    # Use the existing Root fence unchanged. This bootstrap is source-qualified,
    # not an identity provider; no external Grid verifier or runtime is imported.
    sys.path.insert(0, str(unified))
    try:
        from integration.source_guard import SourceFence
        import integration.source_guard as guard_module
        if sys.pycache_prefix is None:
            raise ValueError('ISOLATED_CACHE_REQUIRED')
        fence = SourceFence(unified, expected_unified, isolated_cache=sys.pycache_prefix)
        source = fence.check()
        fence.module(guard_module)
        fence.file(__file__, python=True)
        lock = unified / 'docs/ci/operator-command/requirements-linux.lock'
        fence.file(lock)
        lock_hash = require_fixture_lock(lock.read_bytes())
        result = dict(schema='unified.operator-contract-ci.v2', unified=source,
            fixture_lock_sha256=lock_hash, dependency_integrity='INSTALL_HASH_ONLY',
            installed_wheel_tree_verification='NOT_RUN', authentication='SYNTHETIC_AUTH',
            consensus='MODELED_CONSUL', native_sspi='NOT_RUN', physical='NOT_RUN', production='NO_GO')
        if junit:
            result['required_tests'] = validate_junit(junit)
            result['junit_sha256'] = hashlib.sha256(Path(junit).read_bytes()).hexdigest()
        fence.finish()
        return result
    finally:
        sys.path.pop(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('unified', 'expected-unified', 'report'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--junit')
    args = parser.parse_args()
    output = Path(args.report).resolve()
    source = Path(args.unified).resolve()
    if output == source or source in output.parents:
        raise ValueError('EVIDENCE_MUST_BE_OUTSIDE_CHECKOUTS')
    output.write_text(json.dumps(receipt(args.unified, args.expected_unified, args.junit), indent=2))
