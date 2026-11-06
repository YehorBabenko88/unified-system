"""TEST_ONLY envelope sweep; not a production throughput/TTL qualification.

Run from repository root: python -m tests.scheduler_design.envelope_probe OUTPUT
"""
import copy
import json
import platform
from pathlib import Path
import statistics
import sys
import time
import tracemalloc

from tests.scheduler_design.test_assignment_schema import AssignmentSchemaTests


def main(output):
    AssignmentSchemaTests.setUpClass()
    case = AssignmentSchemaTests()
    case.setUp()
    rows = []
    for count in (1, 16, 256, 4096):
        grant = copy.deepcopy(case.grant)
        grant['state'] = 'DRAINING'
        grant['drain'] = dict(deadline_ms=1800, max_remaining_bytes='4096',
                              permitted_batch_ids=[f'batch-{i:08d}' for i in range(count)])
        wire = json.dumps(grant, separators=(',', ':'), sort_keys=True).encode('utf-8')
        timings = []
        for _ in range(30):
            start = time.perf_counter_ns()
            parsed = json.loads(wire)
            case.validator.validate(parsed)
            timings.append((time.perf_counter_ns() - start) / 1e6)
        rows.append(dict(TEST_ONLY_batch_ids=count, canonical_bytes=len(wire),
                         samples=30, median_decode_validate_ms=statistics.median(timings),
                         max_decode_validate_ms=max(timings)))
    memory = []
    for count in (1, 16, 256, 4096):
        tracemalloc.start()
        snapshots = [copy.deepcopy(case.grant) for _ in range(count)]
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        memory.append(dict(TEST_ONLY_retained_snapshots=count, allocated_bytes=current, peak_bytes=peak))
        del snapshots
    report = dict(status='TEST_ONLY_NOT_PRODUCTION_LIMITS', platform=platform.platform(),
                  python=sys.version, envelope=rows, retained_snapshots=memory,
                  limits_promoted=[], limitation='No transport, authority, physical I/O or running job load measured.')
    Path(output).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main(sys.argv[1])
