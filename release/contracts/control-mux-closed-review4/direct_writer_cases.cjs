/* Direct-writer ONLY model fixtures. No endpoints, domains or credentials. */
'use strict';
const fs=require('node:fs');
const path=require('node:path');
const {canonical,decode}=require('./cross_language_vectors.cjs');
let getterCalls=0,proxyTraps=0;
const partial=Array(2);partial[1]='x';
const overridden=['x'];overridden.forEach=()=>{};
const protoHole=Array(1);const proto=Object.create(Array.prototype);proto[0]='inherited';Object.setPrototypeOf(protoHole,proto);
const extra=['x'];extra.extra='must-not-disappear';
const symbol={x:'x'};symbol[Symbol('extra')]='must-not-disappear';
const hidden={x:'x'};Object.defineProperty(hidden,'hidden',{value:'must-not-disappear',enumerable:false});
const accessor={};Object.defineProperty(accessor,'x',{enumerable:true,get(){getterCalls++;return 'x';}});
const proxy=new Proxy({x:'x'},{getPrototypeOf(t){proxyTraps++;return Reflect.getPrototypeOf(t);}});
const inherited=Array(2);const inheritedProto=Object.create(Array.prototype);inheritedProto[0]='x';Object.setPrototypeOf(inherited,inheritedProto);
const tests=[
  ['overridden_instance_forEach',overridden,false],['inherited_index_cannot_fill_hole',protoHole,false],
  ['sparse_all_holes',Array(2),false],['sparse_partial_hole',partial,false],
  ['array_extra_own_property',extra,false],['symbol_own_key',symbol,false],['nonenumerable_own_field',hidden,false],
  ['accessor_must_not_execute',accessor,false],['proxy_must_not_execute_traps',proxy,false],
  ['custom_array_prototype',inherited,false],['undefined_value',{x:undefined},false],['function_value',{x:()=>{}},false],
  ['bigint_value',{x:1n},false],['symbol_value',{x:Symbol('x')},false],['nan_value',{x:NaN},false],
  ['date_object',new Date(0),false],['map_object',new Map(),false],['typed_array',new Uint8Array([1]),false],
  ['dense_empty',[],true,'[]'],['dense_null',[null],true,'[null]'],['dense_string',['x'],true,'["x"]'],
  ['dense_null_string',[null,'x'],true,'[null,"x"]'],['frozen_dense_array',Object.freeze(['x']),true,'["x"]'],
  ['frozen_plain_object',Object.freeze({x:'x'}),true,'{"x":"x"}']
];
const observed=[];
for(const [name,value,expected,expectedRaw] of tests){
  let accepted=false,raw=null,reason=null,roundtrip=false;
  try{raw=canonical(value);accepted=true;roundtrip=decode(raw)===raw;}catch(e){reason=e.message;}
  observed.push({name,accepted,expected,raw,reason,roundtrip,expected_raw:expectedRaw||null});
}
const report={scope:'DIRECT_WRITER_NON_JSON_INPUT_MODELS_ONLY',node:process.version,cases:observed,getter_calls:getterCalls,proxy_traps:proxyTraps,runtime_ack:false};
fs.writeFileSync(path.join(__dirname,'direct-writer-node-validation.json'),Buffer.from(JSON.stringify(report)+'\n','ascii'));
const bad=observed.filter(v=>v.accepted!==v.expected || (v.accepted&&(!v.roundtrip||v.raw!==v.expected_raw)));
if(bad.length||getterCalls||proxyTraps)throw Error('DIRECT_WRITER_MISMATCH:'+JSON.stringify({bad,getterCalls,proxyTraps}));
console.log(JSON.stringify({direct_writer_cases:observed.length,result:'MATCH_ROUNDTRIP',runtime_ack:false}));
