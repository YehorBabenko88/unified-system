"""Workstream A diagnostic (MASTER #111): PowerShell child-process timing.

Diagnostic only. It does not change any product deadline, test bound, policy or
protection setting. It reproduces the three phases that time out in the offline
suite (first Add-Member, Add-Type compile, command-not-found lookup) and measures
them under several child environments, cold and warm.

Each child gets a generous 180 s *observation* bound so the real duration is
recorded instead of being cut at 15 s. Product/test bounds are untouched.
Output: one JSON line per run plus a summary table; artifact diag.json.
"""
import json, os, platform, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OBS_BOUND = 180

# Each probe prints UNIFIED_T:<phase>:<ms since child start> to stderr.
PRELUDE = ("$sw=[Diagnostics.Stopwatch]::StartNew();"
           "function P($n){[Console]::Error.WriteLine('UNIFIED_T:'+$n+':'+$sw.ElapsedMilliseconds)};P 'ENTRY';")
PROBES = {
    "ADD_MEMBER": PRELUDE + "$o=[pscustomobject]@{};P 'FIRST_MEMBER_BEGIN';"
                  "$o|Add-Member -MemberType NoteProperty -Name a -Value 1;P 'FIRST_MEMBER_END';"
                  "$o|Add-Member -MemberType ScriptMethod -Name b -Value {1};P 'SECOND_MEMBER_END'",
    "ADD_TYPE": PRELUDE + "P 'COMPILE_BEGIN';"
                "Add-Type -TypeDefinition ('public static class UnifiedDiag'+[guid]::NewGuid().ToString('N')+'{public static int F(){return 1;}}');"
                "P 'COMPILE_END'",
    "CMD_LOOKUP": PRELUDE + "P 'SAFE_LOOKUP_BEGIN';"
                  "try{Get-UnifiedPoisonProbe -ErrorAction Stop}catch [System.Management.Automation.CommandNotFoundException]{P 'NOT_FOUND'};"
                  "P 'SAFE_LOOKUP_END'",
    "BASELINE": PRELUDE + "P 'DONE'",
}


def restricted_env():
    from unified_system import installation_service as s
    return s._environment()


def variants():
    full = dict(os.environ)
    base = restricted_env()
    sysdir = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    extra = {
        "PATH": {"PATH": os.environ.get("PATH", "")},
        "PATH_SYSTEM_ONLY": {"PATH": f"{sysdir};{sysdir.parent};{sysdir / 'WindowsPowerShell' / 'v1.0'}"},
        "COMSPEC": {"ComSpec": os.environ.get("ComSpec", str(sysdir / "cmd.exe"))},
        "PROGRAMFILES": {k: os.environ[k] for k in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432", "CommonProgramFiles") if k in os.environ},
        "MACHINE_IDENTITY": {k: os.environ[k] for k in ("COMPUTERNAME", "USERNAME", "USERDOMAIN", "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS", "OS", "PATHEXT") if k in os.environ},
        "DEFAULT_PSMODULEPATH": {"PSModulePath": os.environ.get("PSModulePath", "")},
    }
    # RESTRICTED first so its cold run is the machine's first PowerShell start.
    out = {"RESTRICTED": dict(base), "FULL": full}
    for name, add in extra.items():
        e = dict(base); e.update(add); out["RESTRICTED+" + name] = e
    allx = dict(base)
    for name in ("PATH", "COMSPEC", "PROGRAMFILES", "MACHINE_IDENTITY"):
        allx.update(extra[name])
    out["RESTRICTED+ALL_BUT_PSMODULEPATH"] = allx
    return out


def run(exe, script, env):
    t0 = time.monotonic()
    try:
        r = subprocess.run([exe, "-NoProfile", "-NonInteractive", "-Command", script],
                           env=env, capture_output=True, timeout=OBS_BOUND)
        code, err, timed_out = r.returncode, r.stderr, False
    except subprocess.TimeoutExpired as e:
        code, err, timed_out = None, e.stderr or b"", True
    wall = round((time.monotonic() - t0) * 1000)
    phases = {}
    for line in err.decode("utf-8", "replace").splitlines():
        if line.startswith("UNIFIED_T:"):
            _, n, ms = line.strip().split(":", 2)
            phases[n] = int(ms)
    other = [l for l in err.decode("utf-8", "replace").splitlines() if not l.startswith("UNIFIED_T:")][:5]
    return dict(wall_ms=wall, exit=code, timed_out=timed_out, phases=phases, stderr_other=other)


def defender_state(exe):
    # Read-only query; nothing is changed.
    r = subprocess.run([exe, "-NoProfile", "-NonInteractive", "-Command",
                        "try{$s=Get-MpComputerStatus;'RTP='+$s.RealTimeProtectionEnabled+' AMSI='+$s.AMServiceEnabled+' IOAV='+$s.IoavProtectionEnabled}catch{'UNAVAILABLE '+$_.Exception.GetType().Name}"],
                       capture_output=True, text=True, timeout=120)
    return (r.stdout or r.stderr).strip()


def main():
    if os.name != "nt":
        print("WINDOWS_ONLY"); return 2
    sysdir = Path(os.environ["SystemRoot"]) / "System32"
    hosts = {"powershell": str(sysdir / "WindowsPowerShell" / "v1.0" / "powershell.exe")}
    pwsh = subprocess.run(["where", "pwsh"], capture_output=True, text=True).stdout.strip().splitlines()
    if pwsh: hosts["pwsh"] = pwsh[0]
    meta = dict(platform=platform.platform(), python=sys.version.split()[0],
                image=os.environ.get("ImageOS"), image_version=os.environ.get("ImageVersion"),
                defender=defender_state(hosts["powershell"]))
    print("META", json.dumps(meta), flush=True)
    results = []
    order = list(PROBES)
    for host, exe in hosts.items():
        for vname, env in variants().items():
            for probe in order:
                for attempt in ("cold", "warm"):
                    res = run(exe, PROBES[probe], env)
                    rec = dict(host=host, variant=vname, probe=probe, attempt=attempt, **res)
                    results.append(rec)
                    print("RUN", json.dumps(rec), flush=True)
    Path("diag.json").write_text(json.dumps(dict(meta=meta, results=results), indent=1))
    print("\nSUMMARY host variant probe cold_ms warm_ms over15s")
    for host in hosts:
        for vname in variants():
            for probe in order:
                c = next(r for r in results if (r["host"], r["variant"], r["probe"], r["attempt"]) == (host, vname, probe, "cold"))
                w = next(r for r in results if (r["host"], r["variant"], r["probe"], r["attempt"]) == (host, vname, probe, "warm"))
                flag = "OVER15" if max(c["wall_ms"], w["wall_ms"]) > 15000 else ""
                print(f"{host:10} {vname:34} {probe:10} {c['wall_ms']:>7} {w['wall_ms']:>7} {flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
