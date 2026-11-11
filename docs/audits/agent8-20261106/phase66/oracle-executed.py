import sys,pathlib,json,pytest,random,math,types,subprocess,copy
from fractions import Fraction
repo=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);sys.path.insert(0,str(repo))
sys.path.insert(0,str(repo/'python'));import history_statistics as current
calls=[];skips=[]
old=types.ModuleType('a8_old');raw=subprocess.check_output(['git','--no-replace-objects','show','917d99672e37db59835a8ab23b03c99826b12d78:python/history_statistics.py'],cwd=repo);exec(compile(raw,'<primary-base-in-memory>','exec'),old.__dict__)
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
