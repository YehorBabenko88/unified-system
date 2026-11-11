import sys,pathlib,importlib.util,json,copy,random,hashlib
from decimal import Decimal,localcontext
import jsonschema
root=pathlib.Path.cwd()/'contracts/agent7-financial-boundary';spec=importlib.util.spec_from_file_location('a8_financial_tests',root/'test_adapter.py');t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t);f=t.BoundaryTests();f.setUp();schema=json.loads((root/'financial-calculation.schema.json').read_text());jsonschema.Draft202012Validator.check_schema(schema);v=jsonschema.Draft202012Validator(schema)
rng=random.Random(8069);count=0
with localcontext() as context:
 context.prec=200
 for scale in [0,2,18]:
  p=dict(f.profile,decimal_places=scale,max_digits=78);pin=t.digest(p)
  for _ in range(64):
   values=[rng.randint(-10**35,10**35),rng.randint(0,10**30),rng.randint(0,10**30),rng.randint(-10**30,10**30)]
   def fmt(n):return format(Decimal(n).scaleb(-scale),'.'+str(scale)+'f')
   for basis in ['GROSS_MINUS_SIGNED_COSTS','NET_INCLUDES_SIGNED_COSTS']:
    rec=dict(f.record,profile_sha256=pin,calculation_basis=basis,**dict(zip(['raw_pnl','fees','slippage','funding'],map(fmt,values))))
    old=copy.deepcopy((rec,p));out=f.m.convert(rec,p,{pin});cost=sum(map(Decimal,[rec['fees'],rec['slippage'],rec['funding']]))
    assert Decimal(out['net_pnl'])==(Decimal(rec['raw_pnl'])-cost if basis.startswith('GROSS') else Decimal(rec['raw_pnl']))
    assert Decimal(out['gross_pnl'])==(Decimal(rec['raw_pnl']) if basis.startswith('GROSS') else Decimal(rec['raw_pnl'])+cost)
    assert not list(v.iter_errors(out)) and (rec,p)==old;count+=1
base=f.run_record();probes=[]
for path in [('gross_pnl',),('net_pnl',),('fees',),('slippage',),('funding',),('profile_sha256',),('provenance','source_head'),('provenance','source_tree'),('provenance','input_manifest_sha256')]:
 d=copy.deepcopy(base);parent=d if len(path)==1 else d[path[0]];parent[path[-1]]+='\n';accepted=not list(v.iter_errors(d));assert not accepted;probes.append(dict(path='.'.join(path),trailing_LF_schema_accepted=accepted))
for key in ['currency','unit']:
 d=copy.deepcopy(base);d[key]+='\n';assert list(v.iter_errors(d))
rec=copy.deepcopy(f.record);rec['raw_pnl']+='\n'
try:f.run_record(rec);raise AssertionError('adapter accepted LF')
except ValueError:pass
print(json.dumps(dict(decimal_oracle_cases=count,scales=[0,2,18],input_unchanged=True,schema_trailing_LF_mismatch=probes,code_LF_correctly_refused=True,adapter_monetary_LF_correctly_refused=True,scope='PROPOSAL_SCHEMA_P2_NOT_RUNTIME_ADMISSION_BYPASS'),indent=2))
