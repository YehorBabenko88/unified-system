"""Pinned source/JUnit evidence gate; modeled contracts only, no native auth proof."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import xml.etree.ElementTree as ET

GRID_SHA='55e74863c3c28bf4cbcb4ded4d3359f98bf93f71'
REQUIRED_CASES=[('tests.test_operator_control_plane.OperatorTests', 'test_missing_provider_fails_closed'),
 ('tests.test_operator_control_plane.OperatorTests', 'test_untrusted_actor_role_and_machine_denied'),
 ('tests.test_operator_control_plane.OperatorTests', 'test_current_grants_checked_on_every_retry'),
 ('tests.test_operator_control_plane.OperatorTests', 'test_role_backend_enforced_and_unknown_action_denied'),
 ('tests.test_operator_control_plane.OperatorTests', 'test_two_windows_retry_and_conflicting_revision'),
 ('tests.test_operator_control_plane.OperatorTests', 'test_strict_boundaries'),
 ('tests.test_operator_control_plane.OperatorTests', 'test_backend_absent_never_returns_fake_receipt'),
 ('tests.test_operator_control_plane.OperatorTests', 'test_receipt_rechecks_current_actor_scope'),
 ('tests.test_operator_control_plane.OperatorTests',
  'test_revocation_during_receipt_query_prevents_disclosure'),
 ('tests.test_operator_control_plane.OperatorTests',
  'test_serialized_or_unknown_capability_principal_denied'),
 ('tests.test_operator_control_plane.OperatorTests', 'test_malformed_private_receipt_never_disclosed'),
 ('tests.test_operator_control_plane.OperatorTests', 'test_zero_grant_denied_before_backend_io'),
 ('tests.test_operator_control_plane.OperatorTests', 'test_submit_receipt_must_match_entire_intent'),
 ('tests.test_operator_control_plane.StreamTests', 'test_snapshot_gap_generation_and_staleness'),
 ('tests.test_operator_control_plane.StreamTests', 'test_invalid_snapshot_cannot_mark_live'),
 ('tests.test_operator_grid_composition.GridCompositionTests',
  'test_commit_retry_read_and_unknown_reconcile_actual_bridge'),
 ('tests.test_operator_grid_composition.GridCompositionTests',
  'test_lost_response_reconciles_same_command_and_two_windows'),
 ('tests.test_operator_grid_composition.GridCompositionTests',
  'test_no_quorum_unknown_has_no_invented_owner'),
 ('tests.test_lifecycle.LifecycleTests', 'test_sequence_and_no_authority'),
 ('tests.test_lifecycle.LifecycleTests', 'test_monitoring_barrier_and_math_independence'),
 ('tests.test_lifecycle.LifecycleTests', 'test_idempotency_collision_and_sequence'),
 ('tests.test_lifecycle.LifecycleTests', 'test_default_verifier_denies_self_assertion'),
 ('tests.test_lifecycle.LifecycleTests', 'test_recovery_revalidates_and_invalidates_downstream'),
 ('tests.test_lifecycle.LifecycleTests', 'test_missing_modules_zero_to_five'),
 ('tests.test_lifecycle.LifecycleTests', 'test_cancel_retry_cannot_retain_handoff'),
 ('tests.test_lifecycle.LifecycleTests', 'test_tampered_state_rejected'),
 ('tests.test_lifecycle.LifecycleTests', 'test_failed_commit_does_not_advance'),
 ('tests.test_lifecycle.LifecycleTests', 'test_concurrent_writer_fenced'),
 ('tests.test_lifecycle.LifecycleTests', 'test_cached_response_tamper_rejected'),
 ('tests.test_lifecycle.LifecycleTests', 'test_completed_initial_state_cannot_be_injected'),
 ('tests.test_lifecycle.LifecycleTests', 'test_old_epoch_operation_cannot_replay_after_recovery'),
 ('tests.test_lifecycle.LifecycleTests', 'test_restart_cannot_replay_cached_completion_before_revalidation'),
 ('tests.test_lifecycle.LifecycleTests', 'test_verifier_cannot_bless_different_status'),
 ('tests.test_lifecycle.LifecycleTests', 'test_read_only_api_and_safe_provider_failure')]


def require_pin(value):
    if value!=GRID_SHA: raise ValueError('GRID_PIN_MISMATCH')


def validate_junit(path):
    root=ET.parse(path).getroot()
    cases=root.findall('.//testcase')
    observed=[(c.get('classname'),c.get('name')) for c in cases]
    if (len(observed)!=34 or len(set(observed))!=34 or set(observed)!=set(REQUIRED_CASES)
            or root.findall('.//skipped') or root.findall('.//failure') or root.findall('.//error')):
        raise ValueError('REQUIRED_TEST_INVENTORY_FAILED')
    return len(cases)


def receipt(unified,grid,expected_unified,junit=None):
    unified=Path(unified).resolve();grid=Path(grid).resolve()
    # The checkout pin is a literal, not a dispatch-controlled dependency.
    previous=Path.cwd()
    try:
        os.chdir(grid)
        verifier=runpy.run_path(str(grid/'lab/consul/source_receipt.py'))['verify']
        grid_source=verifier(GRID_SHA)
        os.chdir(unified)
        unified_source=verifier(expected_unified)
    finally:
        os.chdir(previous)
    result=dict(schema='unified.operator-contract-ci.v1',unified=unified_source,grid=grid_source,
        fixture_lock_sha256=hashlib.sha256((grid/'lab/consul/requirements-three-linux.lock').read_bytes()).hexdigest(),
        dependency_integrity='INSTALL_HASH_ONLY',installed_wheel_tree_verification='NOT_RUN',
        authentication='SYNTHETIC_AUTH',consensus='MODELED_CONSUL',native_sspi='NOT_RUN',physical='NOT_RUN',production='NO_GO')
    if junit:
        result['required_tests']=validate_junit(junit)
        result['junit_sha256']=hashlib.sha256(Path(junit).read_bytes()).hexdigest()
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('unified','grid','expected-unified','report'):parser.add_argument('--'+name,required=True)
    parser.add_argument('--junit')
    args=parser.parse_args()
    output=Path(args.report).resolve()
    for source in (Path(args.unified).resolve(),Path(args.grid).resolve()):
        if output==source or source in output.parents:raise ValueError('EVIDENCE_MUST_BE_OUTSIDE_CHECKOUTS')
    output.write_text(json.dumps(receipt(args.unified,args.grid,args.expected_unified,args.junit),indent=2))
