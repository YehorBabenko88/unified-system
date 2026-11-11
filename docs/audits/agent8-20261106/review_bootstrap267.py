"""Numerical component audit: stdlib workflow, original21 and exact rational oracle."""
import hashlib,io,json,os,pathlib,subprocess,textwrap
r=pathlib.Path(__file__).resolve().parents[1];repo=r/'work/review-bootstrap7a83';out=r/'outputs/phase63';out.mkdir(exist_ok=True);head='7a83e6e1aa74001c4797e9bf7af9368d3192bfbe';base='7a19ab40c30efef431bb16f0ddc91960608bf597';temp=r/'work/bootstrap-a8-temp';temp.mkdir(exist_ok=False);py=r/'work/audit-venv/Scripts/python.exe'
def git(*a):return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*a])
changes=git('diff','--name-only',base,head).decode().splitlines();assert len(changes)==4 and git('rev-parse',head+'^{tree}').decode().strip()=='246a30296803de4c0f2e41a35f2cf6e3faf88a9d'
raw=git('show',head+':.github/workflows/mission-bootstrap-overflow.yml');(out/'workflow.original.yml').write_bytes(raw);part=raw.decode().split('        run: |\n',1)[1].split('      - uses:',1)[0];block=textwrap.dedent(part)
env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};env.update(EXPECTED_HEAD=head,RUNNER_TEMP=str(temp),TEMP=str(temp),TMP=str(temp),PYTHONDONTWRITEBYTECODE='1',GIT_NO_REPLACE_OBJECTS='1',GIT_CONFIG_COUNT='2',GIT_CONFIG_KEY_0='core.autocrlf',GIT_CONFIG_VALUE_0='false',GIT_CONFIG_KEY_1='core.eol',GIT_CONFIG_VALUE_1='lf')
p=subprocess.run([str(py),'-I','-B','-c',block],cwd=repo,env=env,capture_output=True,timeout=60);(out/'workflow10.stdout.log').write_bytes(p.stdout);(out/'workflow10.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr.decode(errors='replace')[-2000:];receipt=(temp/'bootstrap-finite-evidence.json').read_bytes();a=json.loads(receipt);assert len(a['tests'])==10 and a['skips']==0 and len(a['source_sha256'])==692;(out/'workflow10.original.json').write_bytes(receipt)
script='''import sys,pathlib,json,pytest,random,math,types,subprocess,copy
from fractions import Fraction
repo=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);sys.path.insert(0,str(repo))
calls=[];skips=[]
class Reports:
 def pytest_runtest_logreport(self,report):
  if report.skipped:skips.append(report.nodeid)
  if report.when=='call':calls.append(dict(id=report.nodeid,status=report.outcome))
rc=pytest.main(['-q','-o','addopts=','-p','no:cacheprovider','tests/test_strategy_statistics.py','tests/test_strategy_statistics_integrity.py','tests/test_strategy_statistics_overflow.py','--junitxml='+str(out/'exact21.junit.xml')],plugins=[Reports()]);assert rc==0 and len(calls)==21 and not skips and all(c['status']=='passed' for c in calls)
from grid import strategy_statistics as current
old=types.ModuleType('a8_old');raw=subprocess.check_output(['git','--no-replace-objects','show','7a19ab40c30efef431bb16f0ddc91960608bf597:grid/strategy_statistics.py'],cwd=repo);exec(compile(raw,'<primary-base-in-memory>','exec'),old.__dict__)
trade=lambda k,p:dict(signal_id=k,pnl=p,fees=0,slippage=0)
b=[trade('a',-1e308),trade('b',-1e308)];v=[trade('a',1e308),trade('b',1e308)];original=copy.deepcopy((b,v));prior=old.paired_expectancy_bootstrap(b,v,runs=4);assert math.isinf(prior['delta_mean']) and prior['positive_supported'] and all(math.isinf(x) for x in prior['ci95'])
refused=False
try:current.paired_expectancy_bootstrap(b,v,runs=4)
except ValueError:refused=True
assert refused and (b,v)==original
block_old=old.block_bootstrap_expectancy([trade('a',1e308),trade('b',1e308)],block_size=1,runs=4);assert all(math.isinf(x) for x in block_old['ci95']);fixed=current.block_bootstrap_expectancy([trade('a',1e308),trade('b',1e308)],block_size=1,runs=4);assert fixed['ci95']==[1e308,1e308]
pool=[0.,5e-324,-5e-324,1e-323,-1e-323,sys.float_info.min,-sys.float_info.min,1.,-1.,1e16,-1e16,1e308,-1e308,sys.float_info.max,-sys.float_info.max]
vectors=[[5e-324,5e-324],[1e16,1.,-1e16],[1e308,1e308,-1e308,-1e308]+[5e-324]*100,[sys.float_info.max]*4]
rng=random.Random(267)
vectors += [[rng.choice(pool) for _ in range(rng.randint(1,24))] for _ in range(512)]
nonidentical=0;max_ulps=0
for values in vectors:
 expected=float(sum((Fraction.from_float(x) for x in values),Fraction())/len(values));actual=current._finite_mean(values);assert math.isfinite(actual)
 if actual!=expected:
  nonidentical+=1;ulps=abs(actual-expected)/max(math.ulp(actual),math.ulp(expected));max_ulps=max(max_ulps,ulps);assert ulps<=1,(values,actual,expected)
 if expected==0:assert actual==0
 else:assert (actual>0)==(expected>0)
# Independently replay paired RNG samples and order-statistic indices using exact rational means.
values=[1e308,-1e308,5e-324,1.,-1.,sys.float_info.min];keys=[str(i) for i in range(len(values))];diffs=[values[int(k)] for k in sorted(keys,key=str)];rng=random.Random(31);means=[]
for _ in range(64):means.append(float(sum((Fraction.from_float(diffs[rng.randrange(len(diffs))]) for _ in diffs),Fraction())/len(diffs)))
means.sort();observed=current.paired_expectancy_bootstrap([trade(k,0) for k in keys],[trade(k,values[int(k)]) for k in keys],runs=64,seed=31);oracle=[means[int(.025*63)],means[int(.975*63)]]
for x,y in zip(observed['ci95'],oracle):assert abs(x-y)<=max(math.ulp(x),math.ulp(y))
(out/'numerical-oracle.json').write_text(json.dumps(dict(exact21_calls=calls,skips=skips,base_paired_infinite_positive_support_reproduced=True,base_block_infinite_bounds_reproduced=True,current_unrepresentable_diff_refused=True,current_large_block_finite=True,exact_fraction_vectors=len(vectors),normal_path_nonidentical_exact_means=nonidentical,max_observed_error_ULPs=max_ulps,paired_seeded_exact_oracle_samples=64,original_inputs_unchanged=True,scope='FINITE_ARITHMETIC_ONLY_NOT_PROFITABILITY'),indent=2),encoding='utf-8')
'''
e=dict(env,PYTEST_DISABLE_PLUGIN_AUTOLOAD='1');p=subprocess.run([str(py),'-I','-B','-c',script,str(repo),str(out)],cwd=repo,env=e,capture_output=True,timeout=60);(out/'numerical.stdout.log').write_bytes(p.stdout);(out/'numerical.stderr.log').write_bytes(p.stderr);assert p.returncode==0,p.stderr.decode(errors='replace')[-2200:]
for name,digest in a['source_sha256'].items():assert hashlib.sha256((repo/name).read_bytes()).hexdigest()==digest
report=dict(head=head,tree='246a30296803de4c0f2e41a35f2cf6e3faf88a9d',changed_paths=changes,workflow_actual_stdlib_tests=10,old_new_regressions=21,skips=0,raw_source_files_before_after=692,scope='LOCAL_NUMERICAL_COMPONENT_ONLY',hosted='PENDING_SEPARATE_REVIEW',profitability_native_provider_admission=False)
(out/'local-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
