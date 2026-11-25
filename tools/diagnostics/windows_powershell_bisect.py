"""Workstream A, round 2 (MASTER #111): bisect the environment variable(s) whose
absence makes Windows PowerShell 5.1 slow. Diagnostic only; no bound changes."""
import json, os, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
from windows_powershell_probe import PROBES, restricted_env, run  # noqa: E402

EXE = str(Path(os.environ['SystemRoot']) / 'System32' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe')
FAST_MS = 5000


def timed(probe, env):
    r = run(EXE, PROBES[probe], env)
    return r['wall_ms']


def main():
    full = dict(os.environ)
    base = restricted_env()
    out = dict(full_keys=sorted(full), restricted_keys=sorted(base), steps=[])
    # V1: FULL environment, but PSModulePath replaced by the restricted value.
    v1 = dict(full, PSModulePath=base['PSModulePath'])
    out['full_with_restricted_psmodulepath'] = {p: timed(p, v1) for p in ('ADD_MEMBER', 'ADD_TYPE', 'CMD_LOOKUP')}
    print('V1', out['full_with_restricted_psmodulepath'], flush=True)
    # V2: start from RESTRICTED + default PSModulePath; bisect FULL keys that make CMD_LOOKUP fast.
    start = dict(base, PSModulePath=full.get('PSModulePath', ''))
    candidates = sorted(k for k in full if k.upper() not in {x.upper() for x in start})

    def fast_with(keys):
        env = dict(start); env.update({k: full[k] for k in keys})
        ms = timed('CMD_LOOKUP', env)
        out['steps'].append(dict(n=len(keys), keys=keys if len(keys) <= 8 else keys[:8] + ['...'], ms=ms))
        print('STEP', len(keys), ms, keys[:6], flush=True)
        return ms < FAST_MS

    if not fast_with(candidates):
        out['cmd_lookup_result'] = 'NOT_EXPLAINED_BY_ENV_KEYS'
    else:
        needed = []
        while not fast_with(needed) and len(needed) < 6:
            rem = [k for k in candidates if k not in needed]
            lo, hi = 1, len(rem)          # invariant: needed + rem[:hi] is fast
            while lo < hi:
                mid = (lo + hi) // 2
                if fast_with(needed + rem[:mid]):
                    hi = mid
                else:
                    lo = mid + 1
            needed.append(rem[lo - 1])
        out['cmd_lookup_needed_keys'] = needed
        # confirm minimal set for each probe
        env = dict(start); env.update({k: full[k] for k in needed})
        out['confirm'] = {p: timed(p, env) for p in ('ADD_MEMBER', 'ADD_TYPE', 'CMD_LOOKUP')}
        env2 = dict(base); env2.update({k: full[k] for k in needed})
        out['confirm_without_default_psmodulepath'] = {p: timed(p, env2) for p in ('ADD_MEMBER', 'ADD_TYPE', 'CMD_LOOKUP')}
    Path('bisect.json').write_text(json.dumps(out, indent=1))
    print('RESULT', json.dumps({k: v for k, v in out.items() if k not in ('full_keys', 'restricted_keys', 'steps')}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
