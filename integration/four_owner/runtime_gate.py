"""Mandatory current canonical runtime/browser migration gate; never starts code."""
import argparse,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]

def main(argv=None,*,kind):
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--source-proof',required=True);parser.add_argument('--output',required=True)
 args=parser.parse_args(argv);source=pathlib.Path(args.source_proof).absolute();out=pathlib.Path(args.output).absolute()
 if out.exists() or out.resolve().is_relative_to(ROOT.resolve()):raise ValueError('FRESH_EXTERNAL_GATE_EVIDENCE_REQUIRED')
 if source.stat().st_size>33554432:raise ValueError('SOURCE_PROOF_BOUNDS')
 proof=json.loads(source.read_bytes());sys.path.insert(0,str(ROOT))
 from integration.four_owner.contracts import runtime_gate
 report=runtime_gate(kind,proof)
 qualified=(type(proof) is dict and proof.get('qualification')=='PASS_SCOPED' and proof.get('release_status')=='NO_GO' and proof.get('execution_authority') is False and proof.get('trading_authorized') is False)
 if not qualified:report['missing_proofs'].insert(0,'SOURCE_RUN_UNQUALIFIED')
 out.mkdir();(out/'evidence.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n',encoding='utf8')
 prefix={'browser':'BROWSER_UNQUALIFIED','managed-runtime':'TERMINAN_RUNTIME_UNQUALIFIED','pipeline':'PIPELINE_UNQUALIFIED'}[kind]
 print(prefix+':'+('SOURCE_RUN_UNQUALIFIED' if not qualified else 'CANONICAL_STARTUP_ADMISSION_REQUIRED'),file=sys.stderr)
 return 1
