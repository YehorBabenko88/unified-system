"""Optional offline raw-capture UNIT qualification, not mandatory/native admission.

ONE58: immutable owner factories, one isolated child, retained NEW owned state.
The guards constrain cooperative reviewed code; they are not an OS sandbox or a
hostile process-family containment proof. Git/source checks are outside the
30-second observed child phase. Cleanup wait/join requests share five seconds
of clock-derived requested time, not a measured/enforced cleanup deadline:
kill/close and other calls may overrun. No kernel, family or whole-lane bound.
"""
import hashlib
import importlib.machinery
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import threading
import time
import unittest

GRID = ('53b842df817d37b006809d73f9b6195348d32cc2', '19a12a6b76f89ee6c170051bc34f50290295f406')
STORAGE = ('01d7cf17f47a6bfa930a36808a4b0065c5f0f053', '599f39e91ea83fb1233b3bd5fb407755626b9468')
GRID_PINS = {'docs/market-data/raw-capture-observation-v1.schema.json': (4250,
                                                             '3fd5fd8a9d845d73f9b16f53d838386af01982b026d13b7ada67e09c0b1d7936'),
 'grid/__init__.py': (22, '91447944015cec709e8aa7655f7e9d64e1e4508e7023a57fe3746911c0fc6fed'),
 'grid/book_velocity.py': (1714,
                           'e97d331b6bdccb2604be8001a35252bb7a07d7606008bdd1a148f0eaefc65b5f'),
 'grid/cluster.py': (4091, '6fbceffdd1a8dc68aa2aabedd41970b76cf904710325104f27deba52cb041fbb'),
 'grid/continuity.py': (3830, 'cbbe420279537de6c7e23556bdbfbc5b125294a3dd83c6a5acf54cf323de0a2c'),
 'grid/data_quality.py': (1977, '382975f68ed4fab75655ca720f6a18cede65db6fadd53c0b5be1fe831689e435'),
 'grid/microstructure.py': (28909,
                            '7b3b70832991edb816005f092d4201f56819da60e73214b6d46d4b0404c79831'),
 'grid/models.py': (711, 'b869a4e9dbc0a58e2d1dda9ddef1090c4ec30f2b02b6e1e7cc27307d6f569f8a'),
 'grid/orderbook.py': (2271, 'fcdbc9513b38035cca898228df20d713484c273ce56cb514d804996f5039f64d'),
 'grid/public_trade_validation.py': (8260,
                                     '83ea624ceabb65ec502ea3489c97d1ae2fd7fa760176cad520262b633687bbd6'),
 'grid/raw_capture.py': (16748, '089131b3ca3e01ee5ea3127ed56fdfc05dc0c17fa15e3557160b3f7a8da5fb87'),
 'grid/resilience.py': (832, '6c4f947f954d21cecf657d01ff013e04cdfe524d634c9347d100b4d87141056a'),
 'grid/topic_watchdog.py': (585,
                            '2ab206cea8a68013472fe12c8ed554d6c6f01a2611590bd8cf64d3c1f0f5b211'),
 'grid/wall_tracker.py': (2700, 'a6533ef2052a5b745c8a024b882c29a096a0024bd8ad8ff53a3b21c2b15f74e0'),
 'grid/worker.py': (43079, '7124bc3dc8c70c4dd13fdeb1b18cda58a50a5e5cf69d63b00f05f8aa7342c290'),
 'tests/raw_capture/storage_bridge_cases.py': (4817,
                                               '94f7207fb968da7a068be9678acff4b132d192590279ff1611696d43ac8a4eb2'),
 'tests/raw_capture/test_receive_hooks.py': (20182,
                                             '5b37007210436e2da5767c4970f6ce0737cdfd7fb72f5113fc1cd823a4220476'),
 'tests/raw_capture/test_recorder.py': (11069,
                                        '1632b08b6a9ddcac8e46c2e79b281c0f83cb7649c08dd696c45120be3fb3f24c')}
STORAGE_PINS = {'tests/storage/raw_capture/test_adapter.py': (10372,
                                               '16d79ff4aca7de50f9379f115f7a12dfe4c6dc3f0c65ec4750e3c54d72381f21'),
 'unified_system/__init__.py': (81,
                                '68113e881a6bce0a682d3ebe1a3a1086c176c35b889d8c852b14e75645409610'),
 'unified_system/contracts.py': (2352,
                                 '935f946bcf9cf64f9c4b98a9cd6f391e92e03f6db5120ad910bb11f3e1dbc9fc'),
 'unified_system/journal.py': (3459,
                               '9f170cf33f8cdd79baef6fa633d03bebf9eb4b594c54c9cf8dd6c7cb9810bbc3'),
 'unified_system/storage/__init__.py': (84,
                                        'b1e9fb9689b449be9532be0393a6ea52fc5c70f9b3ef6aa598937b313b9bddee'),
 'unified_system/storage/contracts.py': (5978,
                                         '1c9225b15a59b5f6c706de30664ea00094d3b293034e594e4113db9a76cb0e38'),
 'unified_system/storage/object_store.py': (9211,
                                            '193c4e68e48dcdda212412ed7bd00d23afa04fe36bffb84c074948602bb8f739'),
 'unified_system/storage/raw_capture.py': (13372,
                                           '8af7b96a57f0b84329e8914fe40b41f3804c12722d87f906cb4d25c70e6e2174')}
EXPECTED_IDS = ['test_receive_hooks.HookTests.test_accumulated_level_overflow_persists_gap_before_snapshot',
 'test_receive_hooks.HookTests.test_actual_sequence_rejection_and_snapshot_emit_persistent_gap_then_resync',
 'test_receive_hooks.HookTests.test_actual_worker_captures_individual_trade_frames_including_duplicates',
 'test_receive_hooks.HookTests.test_actual_worker_raw_failure_does_not_reconnect',
 'test_receive_hooks.HookTests.test_cancel_cleanup_sink_failure_does_not_mask_original_cancellation',
 'test_receive_hooks.HookTests.test_cancelled_uncertain_task_is_not_restarted_by_supervisor',
 'test_receive_hooks.HookTests.test_crossed_book_persists_gap_before_fresh_snapshot',
 'test_receive_hooks.HookTests.test_duplicate_payload_occurrences_are_not_collapsed_by_receive_hook',
 'test_receive_hooks.HookTests.test_fake_module_is_not_published_to_shared_grid_package',
 'test_receive_hooks.HookTests.test_micro_assignment_cancel_outcome_blocks_replacement_profiles',
 'test_receive_hooks.HookTests.test_missing_exchange_timestamp_is_not_filled_from_local_wall',
 'test_receive_hooks.HookTests.test_multi_symbol_raw_profile_rejects_before_connect',
 'test_receive_hooks.HookTests.test_original_raw_and_malformed_frame_are_stored_before_derived_event',
 'test_receive_hooks.HookTests.test_raw_transport_failure_stops_without_legacy_backoff',
 'test_receive_hooks.HookTests.test_storage_failure_is_terminal_not_automatic_reconnect',
 'test_receive_hooks.HookTests.test_supervisor_does_not_restart_a_raw_capture_failure',
 'test_receive_hooks.HookTests.test_trade_removal_cancel_outcome_blocks_later_reassignment',
 'test_receive_hooks.HookTests.test_unknown_raw_task_exception_is_terminal_not_profile_reset',
 'test_receive_hooks.HookTests.test_worker_micro_reconciliation_passes_raw_profile_and_single_symbol_batches',
 'test_receive_hooks.HookTests.test_worker_opted_in_factory_cannot_silently_disable_capture',
 'test_recorder.RecorderTests.test_budget_and_busy_reentry_are_fail_closed',
 'test_recorder.RecorderTests.test_codec_rejects_calendar_upper_bound_newline_alias_and_null_violation',
 'test_recorder.RecorderTests.test_codec_rejects_noncanonical_duplicate_numeric_and_trailing_bytes',
 'test_recorder.RecorderTests.test_codec_roundtrip_and_independent_instrument_copy',
 'test_recorder.RecorderTests.test_exact_text_binary_empty_and_distinct_occurrences',
 'test_recorder.RecorderTests.test_false_publication_readback_is_not_accepted',
 'test_recorder.RecorderTests.test_foreign_frame_reference_stops_without_control_write',
 'test_recorder.RecorderTests.test_gap_remains_in_history_after_resync',
 'test_recorder.RecorderTests.test_mutated_returned_metrics_do_not_change_recorder',
 'test_recorder.RecorderTests.test_nonboolean_resync_mode_is_rejected_before_write',
 'test_recorder.RecorderTests.test_oversized_frame_stops_without_forwarding_payload',
 'test_recorder.RecorderTests.test_profile_refuses_expansion_bool_and_missing_limits',
 'test_recorder.RecorderTests.test_readback_clock_is_separate_from_receive_clock',
 'test_recorder.RecorderTests.test_readback_hash_mismatch_stops_before_durable_advance',
 'test_recorder.RecorderTests.test_reconnect_does_not_reset_count_and_preserves_disconnect',
 'test_recorder.RecorderTests.test_regressing_monotonic_receive_clock_stops',
 'test_recorder.RecorderTests.test_reserved_control_slots_are_inside_total_sixteen',
 'test_recorder.RecorderTests.test_sink_cancellation_propagates_original_and_keeps_unknown',
 'test_recorder.RecorderTests.test_sink_failure_keeps_received_not_durable_and_is_terminal',
 'test_recorder.RecorderTests.test_validation_capacity_uses_reserved_gap_slot_before_stopping',
 'test_recorder.RecorderTests.test_validation_preserves_original_receive_clock_and_real_exchange_fields',
 'storage_bridge_cases.make_suite.<locals>.StorageBridgeCases.test_exact_raw_empty_occurrences_reopen_and_original_link_idempotence',
 'storage_bridge_cases.make_suite.<locals>.StorageBridgeCases.test_gap_resync_and_disconnect_are_real_metadata_objects_not_raw_payloads',
 'qualified_a4_raw.RawCaptureTests.test_busy_does_not_queue',
 'qualified_a4_raw.RawCaptureTests.test_bytes_roundtrip_reopen_false_authority',
 'qualified_a4_raw.RawCaptureTests.test_count_persists_across_adapter_reopen',
 'qualified_a4_raw.RawCaptureTests.test_empty_frame_is_distinct_from_absent_payload',
 'qualified_a4_raw.RawCaptureTests.test_headroom_and_inventory_required',
 'qualified_a4_raw.RawCaptureTests.test_idempotence_and_different_occurrence',
 'qualified_a4_raw.RawCaptureTests.test_input_limits_reject_before_mutation',
 'qualified_a4_raw.RawCaptureTests.test_link_codec_lexical_and_null_pair_rules',
 'qualified_a4_raw.RawCaptureTests.test_logical_state_and_inventory_limits',
 'qualified_a4_raw.RawCaptureTests.test_namespace_scan_stops_at_admitted_inventory_bound',
 'qualified_a4_raw.RawCaptureTests.test_occurrence_budget_charges_deduplicated_payload',
 'qualified_a4_raw.RawCaptureTests.test_orphan_denies_write_but_not_linked_read',
 'qualified_a4_raw.RawCaptureTests.test_prospective_object_count_refuses_before_mutation',
 'qualified_a4_raw.RawCaptureTests.test_same_payload_observation_hash_uses_one_object_slot',
 'qualified_a4_raw.RawCaptureTests.test_unknown_append_retained_and_read_reconciled']


MAX_BLOB = 20 * 1024 * 1024
MAX_SOURCE = 64 * 1024 * 1024
MAX_CAPTURE = 128 * 1024 * 1024
LOG_CAP = 256 * 1024
OWNER_ACKS = {
    'A3': 'e31914981898e61963c0d8ae39c51b08cac7f3ed26f9ac29321984acaa64afbd',
    'A3_sqlite_intrinsic_effects': 'aafddbbdf34fb5df5d345cb3fc1e97fd28475982cb14b2a91e6f84233731e393',
    'A4': 'f50a79bf6cb0a68f15d470f613791d06cfe206d5740b7d68003707e4fde47df6',
}
DATA_ONLY = {'grid/worker.py', 'docs/market-data/raw-capture-observation-v1.schema.json'}


class Denied(RuntimeError): pass
class Prerequisite(Denied): pass


def need(value, code):
    if not value: raise Denied(code)


def require_api(module, name):
    value = getattr(module, name, None)
    if not callable(value): raise Prerequisite('MISSING_FACTORY_API')
    return value


def require_ids(ids):
    need(len(ids) == 58 and len(set(ids)) == 58 and sorted(ids) == sorted(EXPECTED_IDS), 'CASE_INVENTORY')


def require_fresh_modules(modules):
    need(not any(n == 'grid' or n.startswith('grid.') or n == 'unified_system' or n.startswith('unified_system.') or n in ('test_recorder', 'test_receive_hooks', 'storage_bridge_cases', 'qualified_a4_raw') for n in modules), 'FOREIGN_MODULE_CACHE')


def require_code_role(role, name):
    need(role in ('grid', 'storage'), 'FOREIGN_PROJECT_ROLE')
    pins = GRID_PINS if role == 'grid' else STORAGE_PINS
    need(name in pins and name.endswith('.py') and name not in DATA_ONLY, 'SOURCE_CODE_ROLE')


def ordinary(path, file=False, single=True):
    path = Path(path)
    need(path.is_absolute() and '..' not in path.parts, 'ABSOLUTE_ORDINARY_PATH')
    current = Path(path.anchor)
    for index, part in enumerate(path.parts[1:]):
        current /= part
        s = current.lstat()
        need(not (stat.S_ISLNK(s.st_mode) or getattr(s, 'st_reparse_tag', 0) or getattr(s, 'st_file_attributes', 0) & 1024), 'PATH_ALIAS')
        leaf = index == len(path.parts) - 2
        need(stat.S_ISREG(s.st_mode) if leaf and file else stat.S_ISDIR(s.st_mode), 'PATH_KIND')
        if leaf and file and single: need(s.st_nlink == 1, 'PATH_LINK_COUNT')
    return path


def raw_file(path, limit):
    ordinary(path, True)
    a = path.stat()
    need(a.st_size <= limit, 'FILE_BOUND')
    with path.open('rb') as f: raw = f.read(limit + 1)
    ordinary(path, True)
    b = path.stat()
    need(len(raw) == a.st_size and (a.st_ino, a.st_size, a.st_mtime_ns) == (b.st_ino, b.st_size, b.st_mtime_ns), 'FILE_CHANGED')
    return raw


def save(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    need(len(raw) <= 2 * 1024 * 1024, 'RECEIPT_BOUND')
    with path.open('xb') as f: f.write(raw)


def capture(argv, cwd, env, seconds, cap, input_bytes=None):
    """Held direct process; sticky overflow and independent bounded retirement.

    No process scan/Job/descendant guarantee. Approved Git is helper-disabled;
    the test child denies process creation. Unknown reader retirement is FAIL.
    The five-second SHARED_REQUESTED wait/join budget is not an enforced cleanup
    deadline; kill/close can overrun, and the observed child phase is not an OS
    kernel, process-family or whole-lane timing guarantee.
    """
    child = None; readers = []; chunks = [bytearray(), bytearray()]
    errors = []; total = 0; lock = threading.Lock(); overflow = threading.Event(); failed = threading.Event()
    started = time.monotonic(); reason = None; retired = False
    def drain(pipe, which):
        nonlocal total
        try:
            while True:
                block = pipe.read(8192)
                if not block: break
                with lock:
                    room = max(0, cap - total); total += len(block)
                    chunks[which].extend(block[:room])
                    if total > cap: overflow.set()
        except BaseException: errors.append('READER'); failed.set()
    def feed(pipe):
        try: pipe.write(input_bytes); pipe.close()
        except BaseException: errors.append('INPUT_WRITER'); failed.set()
    try:
        child = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tasks = [(drain, (child.stdout, 0)), (drain, (child.stderr, 1))]
        if input_bytes is not None: tasks.append((feed, (child.stdin,)))
        for target, args in tasks:
            thread = threading.Thread(target=target, args=args, daemon=True)
            entry = [thread, 'UNKNOWN']; readers.append(entry)
            try: thread.start(); entry[1] = 'STARTED'
            except BaseException:
                try:
                    if thread.ident is not None or thread.is_alive(): entry[1] = 'STARTED'
                except BaseException: pass
                raise
        while child.poll() is None:
            if overflow.is_set(): reason = 'OUTPUT_BOUND'; break
            if failed.is_set(): reason = 'STREAM_UNKNOWN'; break
            if time.monotonic() - started >= seconds: reason = 'CHILD_DEADLINE'; break
            time.sleep(.01)
        if time.monotonic() - started > seconds: reason = reason or 'OBSERVED_DEADLINE'
    except BaseException: reason = reason or 'LIFECYCLE_UNKNOWN'
    finally:
        cleanup_start = None; cleanup_end = None
        def fault(code):
            if code not in errors: errors.append(code)
        try:
            cleanup_start = time.monotonic()
            need(isinstance(cleanup_start, (int, float)) and math.isfinite(cleanup_start), 'CLOCK_VALUE')
            cleanup_end = cleanup_start + 5
        except BaseException: fault('CLEANUP_CLOCK_UNKNOWN')
        def remaining():
            # An unknown shared requested-time budget cannot grant fresh time.
            # This requests wait/join time; it cannot enforce kill/close timing.
            # Still
            # attempt wait/join nonblocking; retain UNKNOWN and every held item.
            if cleanup_end is None: return 0
            try:
                now = time.monotonic()
                need(isinstance(now, (int, float)) and math.isfinite(now) and now >= cleanup_start, 'CLOCK_VALUE')
                return max(0, min(5, cleanup_end-now))
            except BaseException:
                fault('CLEANUP_CLOCK_UNKNOWN'); return 0
        if child is not None:
            running_or_unknown = True
            try:
                running_or_unknown = child.poll() is None
            except BaseException: fault('POLL_UNKNOWN')
            if running_or_unknown:
                try: child.kill()
                except BaseException: errors.append('KILL')
            try: child.wait(timeout=remaining()); retired = True
            except BaseException: errors.append('WAIT')
        for thread, state in readers:
            if state != 'STARTED': errors.append('START_UNKNOWN'); continue
            try: thread.join(remaining())
            except BaseException: errors.append('JOIN')
            try:
                if thread.is_alive(): errors.append('READER_ALIVE')
            except BaseException: errors.append('READER_STATE_UNKNOWN')
        if child is not None and retired and not errors:
            for pipe in (child.stdin, child.stdout, child.stderr):
                if pipe is not None:
                    try: pipe.close()
                    except BaseException: errors.append('CLOSE')
        if overflow.is_set() or total > cap: reason = reason or 'OUTPUT_BOUND'
        observed = None
        try:
            observed = time.monotonic()-started
            need(isinstance(observed, (int, float)) and math.isfinite(observed) and observed >= 0, 'CLOCK_VALUE')
        except BaseException:
            observed = None; fault('OBSERVED_CLOCK_UNKNOWN')
        if errors or not retired: reason = reason or 'RETIREMENT_UNKNOWN'
    return {'returncode': None if child is None else child.returncode, 'reason': reason, 'retired': retired, 'errors': errors, 'total_bytes': total, 'stdout': bytes(chunks[0]), 'stderr': bytes(chunks[1]), 'observed_seconds': observed}


def safe_component(name):
    need(bool(name) and name not in ('.', '..', '.git') and not any(c in name for c in '/\\:\0') and not name.endswith((' ', '.')), 'TREE_PATH')
    return name


def check_object(oid, kind, raw):
    need(kind in ('blob', 'tree', 'commit') and re.fullmatch('[0-9a-f]{40}', oid) is not None, 'OBJECT_HEADER')
    need(hashlib.sha1(kind.encode() + b' ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == oid, 'OBJECT_HASH')
    return raw


def parse_batch(raw, expected):
    objects = {}; offset = 0
    for oid in expected:
        end = raw.find(b'\n', offset)
        need(end >= offset and end-offset < 96, 'BATCH_HEADER')
        fields = raw[offset:end].split(b' ')
        need(len(fields) == 3 and fields[0] == oid.encode() and fields[1] in (b'blob', b'tree', b'commit') and fields[2].isdigit(), 'BATCH_IDENTITY')
        size = int(fields[2]); need(size <= MAX_BLOB, 'OBJECT_BOUND')
        start = end+1; offset = start+size+1
        need(offset <= len(raw) and raw[offset-1:offset] == b'\n', 'BATCH_SIZE_LF')
        kind = fields[1].decode(); content = raw[start:start+size]
        check_object(oid, kind, content); need(oid not in objects, 'OBJECT_DUPLICATE')
        objects[oid] = (kind, content)
    need(offset == len(raw), 'BATCH_TRAILING')
    return objects


def parse_tree(raw):
    entries = []; offset = 0; folded = set()
    while offset < len(raw):
        end = raw.find(b'\0', offset); need(end > offset and end+21 <= len(raw), 'TREE_ENCODING')
        header = raw[offset:end].split(b' ', 1); need(len(header) == 2, 'TREE_HEADER')
        mode = header[0].decode(); name = header[1].decode('utf-8', 'strict'); safe_component(name)
        need(mode in ('40000', '100644', '100755') and name.casefold() not in folded, 'TREE_MODE_OR_COLLISION')
        folded.add(name.casefold()); entries.append((mode, name, raw[end+1:end+21].hex())); offset = end+21
    return entries


def git_env():
    env = {k:v for k,v in os.environ.items() if k.upper() in ('SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')
    return env


def primary(root, head, tree=None):
    """Recompute all commit/tree/blob OIDs, compare EVERY working raw file."""
    ordinary(root); need(re.fullmatch('[0-9a-f]{40}', head) is not None, 'HEAD_PIN')
    gitdir = ordinary(root/'.git')  # hosted standalone checkouts only
    need(not any(os.path.lexists(gitdir/p) for p in ('objects/info/alternates', 'refs/replace', 'shallow', 'info/grafts')), 'FOREIGN_OBJECT_SOURCE')
    executable = Path('C:/Program Files/Git/mingw64/bin/git.exe') if os.name == 'nt' else Path('/usr/bin/git')
    ordinary(executable, True, single=False)
    def run(args, limit, data=None):
        result = capture([str(executable), '--no-replace-objects', '-c', 'core.fsmonitor=false', '-c', 'core.untrackedCache=false', '-c', 'core.hooksPath='+os.devnull, '-C', str(root), *args], root, git_env(), 60, limit, data)
        need(result['reason'] is None and result['returncode'] == 0 and not result['stderr'], 'PRIMARY_GIT')
        return result['stdout']
    need(run(['rev-parse', 'HEAD'], 128).strip().decode() == head, 'WORKTREE_HEAD')
    listing = run(['ls-tree', '-r', '-t', '-z', head], 2*1024*1024)
    requested = {head}; listing_files = {}; listing_trees = set()
    for line in listing.split(b'\0'):
        if not line: continue
        meta, name = line.split(b'\t', 1); mode, kind, oid = meta.decode().split(' ')
        path = name.decode(); need(not path.startswith('/') and all(safe_component(p) for p in path.split('/')), 'LISTING_PATH')
        need(kind in ('blob', 'tree') and re.fullmatch('[0-9a-f]{40}', oid), 'LISTING_OBJECT')
        requested.add(oid)
        if kind == 'blob': need(path not in listing_files, 'LISTING_DUPLICATE'); listing_files[path] = oid
        else: listing_trees.add(path)
    commit = run(['cat-file', 'commit', head], MAX_BLOB)
    check_object(head, 'commit', commit)
    root_tree = commit.split(b'\n', 1)[0].removeprefix(b'tree ').decode()
    need(re.fullmatch('[0-9a-f]{40}', root_tree) and (tree is None or root_tree == tree), 'COMMIT_TREE')
    requested.add(root_tree); ordered = sorted(requested)
    objects = parse_batch(run(['cat-file', '--batch'], MAX_SOURCE, ('\n'.join(ordered)+'\n').encode()), ordered)
    need(objects[head] == ('commit', commit), 'COMMIT_BATCH')
    files = {}; dirs = set(); visited = {head}
    def descend(oid, prefix='', depth=0):
        need(depth < 32 and oid in objects and objects[oid][0] == 'tree', 'TREE_CLOSURE')
        visited.add(oid)
        for mode, name, child in parse_tree(objects[oid][1]):
            path = prefix+name
            if mode == '40000': dirs.add(path); descend(child, path+'/', depth+1)
            else:
                need(child in objects and objects[child][0] == 'blob', 'BLOB_CLOSURE'); visited.add(child)
                content = objects[child][1]; need(len(files) < 4096, 'SOURCE_COUNT')
                files[path] = {'oid': child, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
    descend(root_tree)
    need(visited == requested and {p:v['oid'] for p,v in files.items()} == listing_files and dirs == listing_trees, 'PRIMARY_TREE_INVENTORY')
    need(sum(v['bytes'] for v in files.values()) <= MAX_SOURCE, 'SOURCE_TOTAL')
    seen = set(); seen_dirs = set()
    def walk(directory, prefix=''):
        ordinary(directory)
        for child in directory.iterdir():
            if not prefix and child.name == '.git': continue
            rel = prefix+child.name; s = child.lstat()
            if stat.S_ISDIR(s.st_mode):
                need(rel in dirs, 'EXTRA_DIRECTORY'); ordinary(child); seen_dirs.add(rel); walk(child, rel+'/')
            else:
                need(rel in files, 'EXTRA_FILE'); content = raw_file(child, MAX_BLOB)
                need(len(content) == files[rel]['bytes'] and hashlib.sha256(content).hexdigest() == files[rel]['sha256'], 'RAW_SOURCE_MISMATCH'); seen.add(rel)
    walk(root); need(seen == set(files) and seen_dirs == dirs, 'RAW_INVENTORY')
    return {'head': head, 'tree': root_tree, 'files': files, 'directories': sorted(dirs)}


def verify_roles(root, pins, ledger):
    for path, (size, digest) in pins.items():
        need(path in ledger['files'] and ledger['files'][path]['bytes'] == size and ledger['files'][path]['sha256'] == digest, 'OWNER_SOURCE_PIN')
        content = raw_file(root/path, MAX_BLOB)
        need(len(content) == size and hashlib.sha256(content).hexdigest() == digest, 'OWNER_RAW_PIN')


def effect_event(event, args):
    if event.startswith('socket.') or event.startswith('ctypes.') or event in ('subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.fork', 'os.forkpty', 'os.exec', 'pty.spawn', 'os.chdir') or event.startswith('os.spawn'):
        raise Denied('FORBIDDEN_EFFECT')


def owned_effect_guard(scratch, result_path):
    """Reviewed Python audit boundary; SQLite's own journal I/O is intrinsic.

    This does not intercept arbitrary native APIs. It confines the selected
    cooperative sources' explicit writes, not hostile in-process mutation.
    """
    def writable(value, result=False):
        need(isinstance(value, (str, bytes, os.PathLike)), 'WRITE_PATH_TYPE')
        path = Path(os.fsdecode(value))
        need(path.is_absolute() and '..' not in path.parts, 'WRITE_PATH_FORM')
        need(path.is_relative_to(scratch) or (result and path == result_path), 'WRITE_OUTSIDE_OWNED_STATE')
    def hook(event, args):
        effect_event(event, args)
        if event == 'sqlite3.connect': writable(args[0])
        elif event == 'open':
            mode, flags = args[1:3]
            if (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)) or (isinstance(mode, str) and any(c in mode for c in 'wax+')):
                writable(args[0], True)
        elif event in ('os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.truncate'):
            writable(args[0])
        elif event in ('os.rename', 'os.link', 'os.symlink'):
            # Symlink creation has no approved fixture use.
            need(event != 'os.symlink', 'SYMLINK_EFFECT')
            writable(args[0]); writable(args[1])
    return hook


def loaded_origins(roots):
    import typing
    facts = {}
    base = Path(sys.base_prefix).absolute()
    for name, module in list(sys.modules.items()):
        if module is None: continue
        spec = getattr(module, '__spec__', None)
        origin = getattr(spec, 'origin', None)
        if name in ('typing.io', 'typing.re'):
            need(module is getattr(typing, name.split('.')[1], None), 'PSEUDOMODULE_IDENTITY')
            facts[name] = {'role': 'stdlib_exact_typing_pseudo'}; continue
        if origin in ('built-in', 'frozen'):
            facts[name] = {'role': origin}; continue
        filename = getattr(module, '__file__', None)
        # The entry module is THIS primary-qualified source; no unknown fileless
        # namespaces or ambient site packages are accepted.
        need(filename is not None, 'UNKNOWN_FILELESS_MODULE')
        path = Path(filename).absolute()
        matched = False
        for role, source in roots.items():
            if path.is_relative_to(source):
                rel = path.relative_to(source).as_posix()
                if role == 'root': need(name == '__main__' and rel == 'tools/raw_capture/qualify.py', 'ROOT_MODULE_ORIGIN')
                else: require_code_role(role, rel)
                raw = raw_file(path, MAX_BLOB)
                facts[name] = {'role': role, 'path': rel, 'sha256': hashlib.sha256(raw).hexdigest()}
                matched = True; break
        if not matched:
            need(path.is_relative_to(base) and 'site-packages' not in path.parts, 'LOADED_FOREIGN_ORIGIN')
            ordinary(path, True, single=False)
            facts[name] = {'role': 'hosted_stdlib_observed', 'relative': path.relative_to(base).as_posix()}
    return facts


def evidence_index(out):
    entries = {}
    def walk(directory, prefix=''):
        ordinary(directory)
        for path in directory.iterdir():
            rel = prefix+path.name
            need(len(entries) < 2048, 'EVIDENCE_COUNT')
            if stat.S_ISDIR(path.lstat().st_mode):
                ordinary(path); walk(path, rel+'/')
            else:
                raw = raw_file(path, 16*1024*1024)
                entries[rel] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    walk(out)
    return {'schema': 'raw-capture.pre-final-evidence-index.v1', 'files': entries,
            'exclusions': ['artifact-inputs.json', 'qualification.json'],
            'provider_zip_sha256': 'AVAILABLE_FROM_GITHUB_ARTIFACT_API_ONLY_AFTER_UPLOAD'}


def worker(root, grid, storage, out):
    """Only this entry activates the 58 approved local unit methods."""
    require_fresh_modules(sys.modules)
    manifest = json.loads(raw_file(out/'source-before.json', 2*1024*1024))
    roots = {'root': root, 'grid': grid, 'storage': storage}
    for role, source in roots.items():
        # Parent's immutable primary map is rechecked before fixture imports.
        for path, item in manifest[role]['files'].items():
            raw = raw_file(source/path, MAX_BLOB)
            need(len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'], 'CHILD_SOURCE_RAW')
    verify_roles(grid, GRID_PINS, manifest['grid']); verify_roles(storage, STORAGE_PINS, manifest['storage'])
    need(manifest['grid']['head'] == GRID[0] and manifest['grid']['tree'] == GRID[1] and manifest['storage']['head'] == STORAGE[0] and manifest['storage']['tree'] == STORAGE[1], 'CHILD_OWNER_IDENTITY')
    original_code = importlib.machinery.SourceFileLoader.get_code
    origins = {}
    def guarded_code(loader, fullname):
        path = Path(loader.path).absolute()
        for role, source in roots.items():
            if path.is_relative_to(source):
                rel = path.relative_to(source).as_posix(); require_code_role(role, rel)
                pins = GRID_PINS if role == 'grid' else STORAGE_PINS
                size, digest = pins[rel]; raw = raw_file(path, size)
                need(len(raw) == size and hashlib.sha256(raw).hexdigest() == digest, 'LOADER_SOURCE_PIN')
                origins[fullname] = {'role': role, 'path': rel, 'sha256': digest}
                return compile(raw, str(path), 'exec', dont_inherit=True)
        # Only the isolated interpreter stdlib is an external import root.
        base = Path(sys.base_prefix).absolute()
        need(path.is_relative_to(base) and 'site-packages' not in path.parts, 'FOREIGN_IMPORT')
        return original_code(loader, fullname)
    importlib.machinery.SourceFileLoader.get_code = guarded_code
    import asyncio
    from unittest import mock  # stdlib only; does not create a loop
    old_start = threading.Thread.start
    old_loop = asyncio.BaseEventLoop.__init__
    def forbidden(*args, **kwargs): raise Denied('THREAD_OR_LOOP_DENIED')
    threading.Thread.start = forbidden; asyncio.BaseEventLoop.__init__ = forbidden
    # All supplied state roots are NEW; bridge factory creates its absent parent.
    scratch = out/'owned-state'; scratch.mkdir()
    a4 = scratch/'a4'; a4.mkdir()
    bridge = scratch/'bridge'
    sys.addaudithook(owned_effect_guard(scratch, out/'actual-result.json'))
    os.environ['A4_RAW_TEST_SCRATCH'] = str(a4)
    sys.path[:0] = [str(grid), str(grid/'tests/raw_capture'), str(storage)]
    records = []; result = None; boundary = None; loaded = {}; cleanup_errors = []
    class Result(unittest.TextTestResult):
        def startTest(self, test): records.append({'id': test.id(), 'outcome': 'RUNNING'}); super().startTest(test)
        def addSuccess(self, test): records[-1]['outcome'] = 'PASS'; super().addSuccess(test)
        def addFailure(self, test, err): records[-1]['outcome'] = 'FAIL'; super().addFailure(test, err)
        def addError(self, test, err): records[-1]['outcome'] = 'ERROR'; super().addError(test, err)
        def addSkip(self, test, reason): records[-1]['outcome'] = 'SKIP'; super().addSkip(test, reason)
    try:
        suite = unittest.defaultTestLoader.discover(str(grid/'tests/raw_capture'), pattern='test_*.py')
        hooks = sys.modules['test_receive_hooks'].HookTests
        need(hooks.microstructure_source_override is None and hooks.worker_source_override is None, 'OWNER_OVERRIDE')
        import storage_bridge_cases
        suite.addTests(require_api(storage_bridge_cases, 'make_suite')(str(storage), str(bridge)))
        spec = importlib.util.spec_from_file_location('qualified_a4_raw', storage/'tests/storage/raw_capture/test_adapter.py')
        module = importlib.util.module_from_spec(spec); sys.modules['qualified_a4_raw'] = module; spec.loader.exec_module(module)
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(module.RawCaptureTests))
        def ids(s):
            return [i for t in s for i in (ids(t) if isinstance(t, unittest.TestSuite) else [t.id()])]
        require_ids(ids(suite))
        result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(suite)
        require_ids([r['id'] for r in records])
        need(result.testsRun == 58 and result.wasSuccessful() and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses and all(r['outcome'] == 'PASS' for r in records), 'ACTUAL_CASE_FAILURE')
        loaded = loaded_origins(roots)
    except BaseException as exc:
        boundary = 'NEWFEATURE_PREREQUISITE' if isinstance(exc, Prerequisite) else 'CASE_OR_BOUNDARY_FAILURE'
        raise
    finally:
        try:
            need(importlib.machinery.SourceFileLoader.get_code is guarded_code and threading.Thread.start is forbidden and asyncio.BaseEventLoop.__init__ is forbidden, 'GUARD_RESTORATION')
            need(not any(n == 'grid.worker' or n == 'websockets' or n == 'grid.config' for n in sys.modules), 'OWNER_FAKE_BINDING_RESTORATION')
        except BaseException: cleanup_errors.append('GUARD_OR_OWNER_BINDING_UNKNOWN')
        importlib.machinery.SourceFileLoader.get_code = original_code
        threading.Thread.start = old_start; asyncio.BaseEventLoop.__init__ = old_loop
        save(out/'actual-result.json', {'schema': 'raw-capture.scoped-unit.v1', 'status': 'PASS' if boundary is None and not cleanup_errors and result is not None and result.wasSuccessful() else 'FAILURE_OR_UNKNOWN', 'boundary': boundary, 'cleanup_errors': cleanup_errors, 'records': records, 'testsRun': 0 if result is None else result.testsRun, 'origins': origins, 'loaded_origins': loaded, 'flags': {'provider': False, 'native_admission': False, 'physical': False, 'authority': False, 'full_matrix': False}, 'scope': 'ONE58_LOCAL_OFFLINE_UNIT_ONLY'})
        need(not cleanup_errors, 'CLEANUP_ORIGIN_UNKNOWN')


def main():
    need(sys.version_info[:3] == (3, 12, 10) and sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode, 'INTERPRETER_PROFILE')
    need(len(sys.argv) == 6 and sys.argv[1] in ('--parent', '--worker'), 'CLOSED_ENTRY')
    mode = sys.argv[1]; root, grid, storage, out = [Path(p) for p in sys.argv[2:]]
    for path in (root, grid, storage): ordinary(path)
    ordinary(out.parent)
    need(len({str(p).casefold() for p in (root, grid, storage, out)}) == 4 and not any(out.is_relative_to(p) or p.is_relative_to(out) for p in (root, grid, storage)), 'ROOT_SEPARATION')
    prefix = out/('worker-cache' if mode == '--worker' else 'parent-cache')
    need(sys.pycache_prefix is not None and Path(sys.pycache_prefix) == prefix and not prefix.exists(), 'FRESH_CACHE_PREFIX')
    if mode == '--worker':
        ordinary(out); worker(root, grid, storage, out); return 0
    out.mkdir()  # exclusive: never overwrite or clean a previous attempt
    source_before = {}; source_after = {}; process = None; faults = []; phase = 'SOURCE_PREFLIGHT'
    expected = os.environ.get('EXPECTED_HEAD', '')
    try:
        source_before = {'root': primary(root, expected), 'grid': primary(grid, *GRID), 'storage': primary(storage, *STORAGE)}
        need(sum(item['bytes'] for repo in source_before.values() for item in repo['files'].values()) <= MAX_CAPTURE, 'ALL_SOURCE_TOTAL')
        verify_roles(grid, GRID_PINS, source_before['grid']); verify_roles(storage, STORAGE_PINS, source_before['storage'])
        save(out/'source-before.json', source_before)
        phase = 'ONE58_CHILD'
        argv = [sys.executable, '-I', '-S', '-B', '-X', 'pycache_prefix='+str(out/'worker-cache'), str(root/'tools/raw_capture/qualify.py'), '--worker', str(root), str(grid), str(storage), str(out)]
        env = {k:v for k,v in os.environ.items() if k.upper() in ('SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP')}
        process = capture(argv, out, env, 30, LOG_CAP)
        for key in ('stdout', 'stderr'):
            with (out/(key+'.original.log')).open('xb') as f: f.write(process.pop(key))
        need(process['reason'] is None and process['returncode'] == 0, 'CHILD_FAILURE_OR_UNKNOWN')
        phase = 'ACTUAL_RESULT'
        actual = json.loads(raw_file(out/'actual-result.json', 2*1024*1024))
        require_ids([record['id'] for record in actual['records']])
        need(actual['status'] == 'PASS' and actual['testsRun'] == 58 and all(record['outcome'] == 'PASS' for record in actual['records']) and all(value is False for value in actual['flags'].values()), 'ACTUAL_RESULT')
    except BaseException as exc:
        faults.append(str(exc) if isinstance(exc, Denied) and re.fullmatch('[A-Z_]+', str(exc)) else 'BOUNDARY_UNKNOWN')
    finally:
        for role, source, head, tree in (('root', root, expected, None), ('grid', grid, *GRID), ('storage', storage, *STORAGE)):
            try: source_after[role] = primary(source, head, tree)
            except BaseException: faults.append('SOURCE_POST_'+role.upper())
        try: save(out/'source-after.json', source_after)
        except BaseException: faults.append('POST_EVIDENCE')
        if source_before != source_after: faults.append('SOURCE_CHANGED_OR_UNKNOWN')
        try:
            logical = 0
            if (out/'owned-state').exists():
                ordinary(out/'owned-state')
                for directory, dirs, files in os.walk(out/'owned-state', followlinks=False):
                    ordinary(Path(directory))
                    for name in dirs: ordinary(Path(directory)/name)
                    for name in files: logical += len(raw_file(Path(directory)/name, 16*1024*1024))
            need(logical <= 16*1024*1024, 'LOGICAL_STATE_BOUND')
        except BaseException: faults.append('STATE_BOUND_UNKNOWN')
        try:
            need(not (out/'parent-cache').exists() and not (out/'worker-cache').exists(), 'CACHE_CREATED')
            save(out/'artifact-inputs.json', evidence_index(out))
        except BaseException: faults.append('EVIDENCE_INDEX_UNKNOWN')
        save(out/'qualification.json', {'schema': 'raw-capture.optional-qualification.v1', 'status': 'PASS' if not faults else 'FAILURE_OR_UNKNOWN', 'last_stage': phase, 'faults': faults, 'process': process, 'source': {r:{k:v[k] for k in ('head', 'tree')} for r,v in source_before.items()}, 'owner_source_effects_ACKs': OWNER_ACKS, 'authority': 'NONE', 'mandatory_grid_collection': 'OPEN_UNCHANGED', 'A2': 'BLOCKED_NO_WAIVER', 'physical_quota': 'NOT_CLAIMED', 'runtime': 'HOSTED_LAB_OBSERVED_NOT_ROOT_RELEASE_ADMITTED'})
    return 1 if faults else 0


if __name__ == '__main__': sys.exit(main())
