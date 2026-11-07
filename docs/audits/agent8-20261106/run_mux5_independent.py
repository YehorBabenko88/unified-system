"""Owned loopback stand invocation; retain original output, never host faults."""
import hashlib,json,os,pathlib,subprocess
r=pathlib.Path(__file__).resolve().parents[1];out=r/'outputs/phase48';out.mkdir(exist_ok=True);source=r/'work/review-mux-5fd0ccb';report=r/'work/mux5-a8-original-report';binary=r/'work/consul-bin/extracted/consul.exe';grid=r/'work/review-grid58cfe'
assert hashlib.sha256(binary.read_bytes()).hexdigest()=='41762ef5b98c8dd9b6852df6cfbceed37e7f0acc5760856be33100f1092475e1'
env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};env.update(PYTHONDONTWRITEBYTECODE='1',GIT_NO_REPLACE_OBJECTS='1',GIT_CONFIG_COUNT='2',GIT_CONFIG_KEY_0='core.autocrlf',GIT_CONFIG_VALUE_0='false',GIT_CONFIG_KEY_1='core.eol',GIT_CONFIG_VALUE_1='lf')
command=[str(r/'work/mux-independent-env/Scripts/python.exe'),'-I','-B',str(source/'tests/control_mux/source_runner.py'),'--expected-head','5fd0ccbd28c79fb5ff040ecb1030462ac4baef35','--grid-source',str(grid),'--binary',str(binary),'--scratch',str(r/'work/mux5-a8-consul-data'),'--output',str(report)]
p=subprocess.run(command,cwd=source,env=env,capture_output=True,timeout=380,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));(out/'invocation.stdout.log').write_bytes(p.stdout);(out/'invocation.stderr.log').write_bytes(p.stderr)
for f in report.iterdir():
 if f.is_file() and f.suffix in ('.json','.log'):(out/f.name).write_bytes(f.read_bytes())
(out/'invocation.json').write_text(json.dumps(dict(command=command,returncode=p.returncode,consul_binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest()),indent=2),encoding='utf-8')
assert p.returncode==0,p.stderr.decode(errors='replace')[-4000:];a=json.loads((out/'source-bound.json').read_bytes());assert len(a['executed_unit_ids'])==18 and len(a['executed_real_case_ids'])==28 and len(a['executed_source_guard_case_ids'])==8 and not a['skips'];print(p.stdout.decode())
