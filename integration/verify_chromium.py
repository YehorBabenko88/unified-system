"""Fence the actual browser/server processes with the same five tracked trees."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
cache=tempfile.TemporaryDirectory(prefix='five-browser-bytecode-')
sys.pycache_prefix=cache.name
from integration.source_guard import SourceFence, SourceQualificationError
parser=argparse.ArgumentParser()
for name in ('terminan','math','grid','strattester'):parser.add_argument('--'+name,required=True,type=Path)
parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args();args.output=args.output.resolve()
pins=json.loads((ROOT/'integration/source-pins.json').read_text())
evidence_path=args.output/'evidence.json'
proof=json.loads(evidence_path.read_text())
proof['browser']={'qualification':'NOT_RUN'}
evidence_path.write_text(json.dumps(proof,sort_keys=True,indent=2),encoding='utf-8')
fences={'unified-system':SourceFence(ROOT,proof.get('head'),isolated_cache=cache.name),**{name:SourceFence(getattr(args,name),pins[name],isolated_cache=cache.name) for name in ('terminan','math','grid','strattester')}}
try:
    if proof.get('qualification')!='EXACT_SOURCE_CONSISTENT':raise SourceQualificationError('SOURCE_RUN_UNQUALIFIED')
    if (proof.get('python_tests')!=11 or any(proof.get(key)!=0 for key in ('python_failures','python_errors','python_skips','math_exit','network_attempts'))
            or proof.get('math_counts')!={'tests':6,'pass':6,'fail':0,'cancelled':0,'skipped':0,'todo':0}):
        raise SourceQualificationError('SOURCE_TESTS_NOT_SUCCESSFUL')
    pre={name:fence.check() for name,fence in fences.items()}
    if pre!=proof['source_post']:raise SourceQualificationError('SOURCE_CHANGED_BEFORE_BROWSER')
    origins={name:fences['unified-system'].file(ROOT/'integration'/name) for name in ('verify_chromium.py','serve_terminan.py','actual-ui.spec.cjs','playwright.config.cjs')}
    env=os.environ.copy();env.update(FIVE_TERMINAN=str(args.terminan.resolve()),FIVE_EVIDENCE=str(args.output),PYTHONPYCACHEPREFIX=cache.name)
    result=subprocess.run(['node',str(ROOT/'integration/node_modules/@playwright/test/cli.js'),'test','--config',str(ROOT/'integration/playwright.config.cjs')],cwd=ROOT,env=env,capture_output=True,text=True,timeout=180)
    (args.output/'chromium.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    print(result.stdout)
    post={name:fence.finish() for name,fence in fences.items()}
    report=json.loads((args.output/'chromium-results.json').read_text())
    stats=report['stats']
    if result.returncode or stats['expected']!=4 or any(stats[k] for k in ('unexpected','flaky','skipped')):
        raise SourceQualificationError('BROWSER_INVENTORY_OR_RESULT_FAILED')
    proof['browser']={'qualification':'EXACT_SOURCE_CONSISTENT','pre':pre,'post':post,'origins':origins,'exit':result.returncode,'stats':stats}
except (SourceQualificationError,OSError,ValueError,KeyError,subprocess.TimeoutExpired) as exc:
    proof['browser']={'qualification':'UNQUALIFIED','reason':str(exc)}
    evidence_path.write_text(json.dumps(proof,sort_keys=True,indent=2),encoding='utf-8')
    raise SystemExit('BROWSER_UNQUALIFIED:'+str(exc))
evidence_path.write_text(json.dumps(proof,sort_keys=True,indent=2),encoding='utf-8')
