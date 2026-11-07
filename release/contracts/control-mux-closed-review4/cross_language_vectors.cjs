/* OUTPUT-ONLY canonical exact-string model, not an endpoint/domain/provider. */
'use strict';
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const {isProxy}=require('node:util').types;
const boundsRaw=fs.readFileSync(path.join(__dirname,'codec-bounds.json'));
const schemaRaw=fs.readFileSync(path.join(__dirname,'control-mux-closed.schema.json'));
const pinnedSchema=JSON.parse(schemaRaw);
const registry=JSON.parse(fs.readFileSync(path.join(__dirname,'registry.json'),'utf8'));
if(crypto.createHash('sha256').update(boundsRaw).digest('hex')!==pinnedSchema['x-c3-codec-bounds-sha256']||crypto.createHash('sha256').update(schemaRaw).digest('hex')!==registry.profile_schema_sha256)throw Error('PROFILE_BOUNDS_PIN_MISMATCH');
const bounds=JSON.parse(boundsRaw);
function canonical(value) {
  let nodes=0,bytes=0;const chunks=[];
  function count(){if(++nodes>Number(bounds.max_nodes))throw Error('NODE_CAP');}
  function emit(text){bytes+=Buffer.byteLength(text,'ascii');if(bytes>Number(bounds.max_raw_ascii_bytes))throw Error('BYTE_CAP');chunks.push(text);}
  function write(v,parentContainerDepth=0) {
    count();
    if(v===null){emit('null');return;}
    if(typeof v==='boolean'){emit(v?'true':'false');return;}
    if(typeof v==='number')throw Error('NO_NUMERIC_LITERAL');
    if(typeof v==='string'){
      if(v.length>Number(bounds.max_value_ascii_characters)||!/^[ -~]*$/.test(v))throw Error('STRING_CAP');
      emit(JSON.stringify(v));return;
    }
    if(typeof v!=='object'||isProxy(v))throw Error('NON_JSON_OBJECT');
    const depth=parentContainerDepth+1;
    if(depth>Number(bounds.max_container_depth))throw Error('DEPTH_CAP');
    if(Array.isArray(v)){
      if(v.length>Number(bounds.max_array_entries))throw Error('ARRAY_CAP');
      if(Object.getPrototypeOf(v)!==Array.prototype)throw Error('NON_JSON_ARRAY_PROTOTYPE');
      const own=Reflect.ownKeys(v);
      if(own.some(k=>typeof k!=='string')||own.length!==v.length+1||!own.includes('length'))throw Error('SPARSE_OR_EXTRA_ARRAY_KEYS');
      const elements=[];
      for(let i=0;i<v.length;i++){
        const descriptor=Object.getOwnPropertyDescriptor(v,String(i));
        if(!descriptor||!Object.hasOwn(descriptor,'value')||descriptor.enumerable!==true)throw Error('ARRAY_OWN_DATA_INDEX_REQUIRED');
        elements.push(descriptor.value);
      }
      // Validate every own index BEFORE emitting the array opener; never forEach holes.
      emit('[');for(let i=0;i<elements.length;i++){if(i)emit(',');write(elements[i],depth);}emit(']');return;
    }
    if(typeof v==='object'&&Object.getPrototypeOf(v)===Object.prototype){
      const keys=Reflect.ownKeys(v);
      if(keys.some(k=>typeof k!=='string'))throw Error('NON_JSON_SYMBOL_KEY');
      keys.sort();
      if(keys.length>Number(bounds.max_object_members))throw Error('MEMBER_CAP');
      if(keys.some(k=>k.length<Number(bounds.min_key_ascii_bytes)||k.length>Number(bounds.max_key_ascii_bytes)||!/^[ -~]*$/.test(k)))throw Error('KEY_CAP');
      const entries=keys.map(k=>{
        const descriptor=Object.getOwnPropertyDescriptor(v,k);
        if(!descriptor||!Object.hasOwn(descriptor,'value')||descriptor.enumerable!==true)throw Error('OWN_ENUMERABLE_DATA_PROPERTY_REQUIRED');
        return [k,descriptor.value];
      });
      emit('{');entries.forEach(([k,value],i)=>{count();if(i)emit(',');emit(JSON.stringify(k));emit(':');write(value,depth);});emit('}');return;
    }
    throw Error('UNSUPPORTED_TYPE');
  }
  write(value);return chunks.join('');
}
function decode(raw) {
  if(typeof raw!=='string'||raw.length===0||Buffer.byteLength(raw,'utf8')>Number(bounds.max_raw_ascii_bytes)||!/^[\x00-\x7f]*$/.test(raw))throw Error('RAW_BOUND');
  let depth=0,quoted=false,escaped=false;
  for(const c of raw) {
    if(quoted){if(escaped)escaped=false;else if(c==='\\')escaped=true;else if(c==='"')quoted=false;}
    else if(c==='"')quoted=true;
    else if(c==='['||c==='{'){if(++depth>Number(bounds.max_container_depth))throw Error('DEPTH_BOUND');}
    else if(c===']'||c==='}'){if(--depth<0)throw Error('INVALID_JSON');}
  }
  const encoded=canonical(JSON.parse(raw));
  if(encoded!==raw)throw Error('NONCANONICAL');
  return encoded;
}
function materialize(v) {
  if ('raw' in v) return v.raw;
  const kind=v.recipe.kind,n=Number(v.recipe.n);
  if (!Number.isSafeInteger(n)) throw Error('RECIPE');
  if (kind==='depth') {if(n<1||n>13)throw Error('RECIPE');return '{"k":'.repeat(n)+'"x"'+'}'.repeat(n);}
  if (kind==='array') {if(n<0||n>1001)throw Error('RECIPE');return '['+Array(n).fill('"x"').join(',')+']';}
  if (kind==='string') {if(n<0||n>16385)throw Error('RECIPE');return '{"x":"'+'a'.repeat(n)+'"}';}
  if (kind==='key_length') {if(n<1||n>129)throw Error('RECIPE');return '{"'+'k'.repeat(n)+'":"x"}';}
  const object=()=>Object.fromEntries(Array.from({length:64},(_,i)=>['k'+String(i).padStart(2,'0'),'']));
  if (kind==='members') {if(n<0||n>65)throw Error('RECIPE');return JSON.stringify(Object.fromEntries(Array.from({length:n},(_,i)=>['k'+String(i).padStart(2,'0'),'x'])));}
  if (kind==='nodes') {if(n!==1&&n!==2)throw Error('RECIPE');const a=Array.from({length:254},object);for(let i=0;i<n;i++)a[0]['k'+String(i).padStart(2,'0')]=[''];return JSON.stringify(a);}
  if (kind==='bytes') {if(n!==0&&n!==1)throw Error('RECIPE');return JSON.stringify([...Array(127).fill('a'.repeat(16384)),'a'.repeat(15999+n)]);}
  throw Error('RECIPE');
}
function runVectors() {
const input=JSON.parse(fs.readFileSync(path.join(__dirname,'canonical-cross-language-vectors.json'),'utf8'));
const results=[];
for (const v of input.vectors) {
  const raw=materialize(v);let accepted=false,hash=null;
  let writerAccepted=false,written=null;
  try{written=canonical(JSON.parse(raw));writerAccepted=true;}catch(_){}
  try {
    const encoded=decode(raw);accepted=true;
    if (accepted) hash=crypto.createHash('sha256').update(encoded,'ascii').digest('hex');
  } catch (_) { accepted=false; }
  if(writerAccepted!==v.writer_accept||(writerAccepted&&crypto.createHash('sha256').update(written,'ascii').digest('hex')!==v.writer_sha256_ascii))throw Error('WRITER_BOUND_MISMATCH');
  results.push({id:v.id||null,raw_sha256:crypto.createHash('sha256').update(raw,'ascii').digest('hex'),raw_bytes:Buffer.byteLength(raw,'ascii'),accepted,sha256_ascii:hash,expected:v.accept,writer_accepted:writerAccepted,writer_sha256_ascii:writerAccepted?crypto.createHash('sha256').update(written,'ascii').digest('hex'):null});
}
const report={scope:'NODE_CANONICAL_COUNTER_BOUNDARY_MODEL_ONLY',node:process.version,cases:results,runtime_ack:false};
fs.writeFileSync(path.join(__dirname,'cross-language-node-validation.json'),Buffer.from(JSON.stringify(report)+'\n','ascii'));
const bad=results.filter((r,i)=>r.accepted!==input.vectors[i].accept || (r.accepted && r.sha256_ascii!==input.vectors[i].sha256_ascii));
if(bad.length)throw Error('VECTOR_MISMATCH:'+JSON.stringify(bad));
process.stdout.write(JSON.stringify({cases:results.length,result:'NODE_MODEL_VECTORS_MATCH',runtime_ack:false})+'\n');

}
module.exports={canonical,decode,materialize};
if(require.main===module)runVectors();
