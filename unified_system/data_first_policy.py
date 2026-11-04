"""Closed proposed DataFirst permissions, never activation or readiness proof.

Only a live kernel-validated protected revision may admit this configuration.
This pure validator neither writes a profile nor authorizes a process/request.
"""
import copy, math, re

FIELDS=frozenset(('schema','source_commit','strategy_fingerprints','categories',
 'network_scope','workspace_relative','limits'))
LIMITS={'timeout_seconds':(1,300),'ram_limit_mb':(64,65536),
 'max_pages':(1,100),'max_observations':(1,1000000)}

def _need(value):
 if not value:raise ValueError('DATA_FIRST_GRANT_REJECTED')

def validate_data_first_grant(value,manifest):
 try:
  _need(type(value) is dict and set(value)==FIELDS)
  _need(value['schema']=='unified.data-first-runtime.v1'
   and value['network_scope']=='BYBIT_PUBLIC_GET_ONLY'
   and value['workspace_relative']=='data-first')
  source=value['source_commit']
  _need(type(source) is str and re.fullmatch('[a-f0-9]{40}',source)
   and source==manifest['sources']['strattester']['commit'])
  pins=value['strategy_fingerprints'];categories=value['categories'];limits=value['limits']
  _need(type(pins) is list and 1<=len(pins)<=128)
  _need(all(type(pin) is str and re.fullmatch('[a-f0-9]{64}',pin) for pin in pins)
   and len(set(pins))==len(pins))
  _need(type(categories) is list and 1<=len(categories)<=3
   and all(type(category) is str and category in ('linear','inverse','spot') for category in categories)
   and len(set(categories))==len(categories))
  _need(type(limits) is dict and set(limits)==set(LIMITS)|{'requests_per_second'})
  for name,(minimum,maximum) in LIMITS.items():
   _need(type(limits[name]) is int and minimum<=limits[name]<=maximum)
  rate=limits['requests_per_second']
  _need(type(rate) in (int,float) and math.isfinite(rate) and .1<=rate<=10)
  return copy.deepcopy(value)
 except (KeyError,TypeError,AttributeError,OverflowError,RecursionError):
  raise ValueError('DATA_FIRST_GRANT_REJECTED') from None
