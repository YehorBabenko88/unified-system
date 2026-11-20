"""Emit only bounded canonical SDK commit values from the admitted Root cohort."""
import argparse,json,os,pathlib,re
REPOSITORIES={'market_data':'YehorBabenko88/strattester','math':'YehorBabenko88/math','terminan':'YehorBabenko88/Terminan'}
def checkout_pins(cohort):
 if type(cohort) is not dict or cohort.get('schema')!='unified.four-owner.source-cohort.v1':raise ValueError('canonical cohort required')
 sources=cohort.get('sources')
 if type(sources) is not dict or set(sources)!={'unified_system',*REPOSITORIES}:raise ValueError('four source owners required')
 result={}
 for owner,repository in REPOSITORIES.items():
  item=sources[owner]
  if type(item) is not dict or item.get('repository')!=repository or type(item.get('commit')) is not str or re.fullmatch('[a-f0-9]{40}',item['commit']) is None:raise ValueError('literal canonical source commit required')
  result[owner]=item['commit']
 return result

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--cohort',required=True);args=p.parse_args(argv)
 raw=pathlib.Path(args.cohort).read_bytes()
 if len(raw)>65536:raise ValueError('bounded cohort required')
 pins=checkout_pins(json.loads(raw))
 with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf8') as output:
  for owner,commit in pins.items():output.write(owner+'='+commit+'\n')
if __name__=='__main__':main()
