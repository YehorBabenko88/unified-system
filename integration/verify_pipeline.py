"""Run the source-owned historical/scientific/UI contract on fenced sources.

This uses synthetic market observations, real numerical subprocesses and actual
source-owned backtesting/display adapters. It never qualifies physical hosts,
source authenticity, trained models or a deployment release.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
cache = tempfile.TemporaryDirectory(prefix='six-pipeline-bytecode-')
sys.pycache_prefix = cache.name
from integration.source_guard import SourceFence, SourceQualificationError

parser = argparse.ArgumentParser(description=__doc__)
for name in ('terminan', 'math', 'grid', 'strattester', 'meta-analyse'):
    parser.add_argument('--' + name, required=True, type=Path)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
pins = json.loads((ROOT / 'integration/source-pins.json').read_text())
sources = {name: getattr(args, name).resolve() for name in
           ('terminan', 'math', 'grid', 'strattester', 'meta_analyse')}
output = args.output.resolve()
evidence_path = output / 'evidence.json'
proof = json.loads(evidence_path.read_text())
proof['pipeline'] = {'qualification': 'NOT_RUN', 'physical': 'NOT_RUN'}
evidence_path.write_text(json.dumps(proof, sort_keys=True, indent=2), encoding='utf-8')

try:
    if (proof.get('qualification') != 'EXACT_SOURCE_CONSISTENT'
            or proof.get('schema') != 'unified.six-source.v1'
            or proof.get('python_tests') != 13
            or any(proof.get(k) != 0 for k in
                   ('python_failures', 'python_errors', 'python_skips', 'math_exit', 'network_attempts'))):
        raise SourceQualificationError('SOURCE_TESTS_NOT_QUALIFIED')
    fences = {'unified-system': SourceFence(ROOT, proof['head'], isolated_cache=cache.name),
              **{name: SourceFence(path, pins[name], isolated_cache=cache.name)
                 for name, path in sources.items()}}
    before = {name: fence.check() for name, fence in fences.items()}
    if before != proof['source_post']:
        raise SourceQualificationError('SOURCE_CHANGED_BEFORE_PIPELINE')
    test = sources['strattester'] / 'tests/research/test_composed_history_runtime.py'
    test_origin = fences['strattester'].file(test, python=True)
    fences['unified-system'].file(__file__, python=True)
    junit = output / 'pipeline-junit.xml'
    packet = output / 'composed-runtime-display.json'
    if junit.exists() or packet.exists():
        raise SourceQualificationError('FRESH_PIPELINE_OUTPUT_REQUIRED')
    env = os.environ.copy()
    env.update(GRID_REFERENCE=str(sources['grid']), MATH_REFERENCE=str(sources['math']),
               TERMINAN_REFERENCE=str(sources['terminan']), HISTORY_REQUIRE_CROSSREPO='1',
               HISTORY_EVIDENCE_ROOT=str(output), OMP_NUM_THREADS='2', MKL_NUM_THREADS='2',
               PYTHONPYCACHEPREFIX=cache.name,
               PYTHONPATH=os.pathsep.join(str(sources[n]) for n in ('grid', 'strattester')))
    run = subprocess.run([sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                          str(test), '--junitxml=' + str(junit)],
                         cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
    (output / 'pipeline.log').write_text(run.stdout + run.stderr, encoding='utf-8')
    post = {name: fence.finish() for name, fence in fences.items()}
    if run.returncode != 0:
        raise SourceQualificationError('PIPELINE_TEST_FAILED')
    cases = list(ET.parse(junit).getroot().iter('testcase'))
    if len(cases) != 1 or any(list(case) for case in cases):
        raise SourceQualificationError('PIPELINE_INVENTORY_OR_RESULT_FAILED')
    raw = packet.read_bytes()
    if not 2 <= len(raw) <= 8 * 1024 * 1024:
        raise SourceQualificationError('PIPELINE_PACKET_BOUNDS')
    display = json.loads(raw)
    if (display.get('schema') != 'terminan.unified-display.v1'
            or display.get('qualification') != 'NOT_QUALIFIED'
            or display.get('contract_only') is not True
            or any(display.get(k) is not False for k in
                   ('training_authorized', 'execution_authority', 'trading_authorized'))):
        raise SourceQualificationError('PIPELINE_AUTHORITY_MISMATCH')
    import hashlib
    proof['pipeline'] = {'qualification': 'EXACT_SOURCE_CONTRACT_PASS', 'tests': 1,
                         'test_origin': test_origin, 'exit': run.returncode,
                         'packet_sha256': hashlib.sha256(raw).hexdigest(),
                         'source_pre': before, 'source_post': post,
                         'source_authenticity': 'UNVERIFIED', 'physical': 'NOT_RUN',
                         'production': 'NO_GO'}
except (SourceQualificationError, OSError, ValueError, KeyError, ET.ParseError,
        subprocess.TimeoutExpired) as exc:
    proof['pipeline'] = {'qualification': 'UNQUALIFIED', 'reason': str(exc), 'physical': 'NOT_RUN'}
    evidence_path.write_text(json.dumps(proof, sort_keys=True, indent=2), encoding='utf-8')
    raise SystemExit('PIPELINE_UNQUALIFIED:' + str(exc))
evidence_path.write_text(json.dumps(proof, sort_keys=True, indent=2), encoding='utf-8')
print('Actual historical/scientific/display contract: PASS; physical NOT_RUN')
