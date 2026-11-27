// One Root-owned bounded HTTP byte reader; no admission or policy callbacks.
const failures=new WeakMap();
function failure(kind){const error=Error('HTTP_BODY_REFUSED');failures.set(error,kind);return error;}
const need=value=>{if(!value)throw failure('RESPONSE');};
/** Classify only errors created by this reader; never inspect foreign properties. */
export function httpBodyFailure(error){return error!==null&&(typeof error==='object'||typeof error==='function')?failures.get(error):undefined;}
/** Literal data-only {maxBytes:1..1MiB,timeoutMs:5000|10000}; byte progress only. */
export async function readHttpBody(response,options){
 let iterator,timer,pendingReject=null,finished=false;
 try{
  need(options!==null&&typeof options==='object'&&!Array.isArray(options)&&Object.getPrototypeOf(options)===Object.prototype);const d=Object.getOwnPropertyDescriptors(options),keys=Object.keys(d);
  need(keys.length===2&&keys.includes('maxBytes')&&keys.includes('timeoutMs')&&keys.every(k=>Object.hasOwn(d[k],'value')));const limit=d.maxBytes.value,timeout=d.timeoutMs.value;
  need(Number.isSafeInteger(limit)&&limit>0&&limit<=1048576&&typeof timeout==='number'&&[5000,10000].includes(timeout));
  need(response!==null&&typeof response==='object');const stream=response.body;need(stream!==null&&typeof stream==='object');const iterate=stream[Symbol.asyncIterator];need(typeof iterate==='function');
  const storage=Buffer.alloc(limit),deadline=performance.now()+timeout;let size=0,count=0,timedOut=false;
  timer=setTimeout(()=>{timedOut=true;if(pendingReject)pendingReject(failure('DEADLINE'));},timeout);iterator=iterate.call(stream);need(iterator!==null&&typeof iterator==='object'&&typeof iterator.next==='function');
  function progress(){if(timedOut||performance.now()>deadline)throw failure('DEADLINE');}
  function next(){return new Promise((resolve,reject)=>{pendingReject=reject;try{Promise.resolve(iterator.next()).then(step=>{if(pendingReject===reject)pendingReject=null;resolve(step);},error=>{if(pendingReject===reject)pendingReject=null;reject(error);});}catch(error){pendingReject=null;reject(error);}});}
  for(;;){
   progress();const step=await next();progress();need(step!==null&&typeof step==='object'&&typeof step.done==='boolean');
   if(step.done){finished=true;need(size>0);return storage.subarray(0,size);}
   if(++count>4096)throw failure('BOUND');const chunk=step.value;need((Buffer.isBuffer(chunk)||chunk instanceof Uint8Array)&&[Buffer.prototype,Uint8Array.prototype].includes(Object.getPrototypeOf(chunk))&&Object.getOwnPropertyDescriptor(chunk,'byteLength')===undefined&&Object.getOwnPropertyDescriptor(chunk,'length')===undefined);
   const bytes=chunk.byteLength;if(bytes===0||size+bytes>limit)throw failure('BOUND');storage.set(chunk,size);size+=bytes;
  }
 }catch(error){if(httpBodyFailure(error))throw error;throw failure('RESPONSE');}
 finally{if(timer!==undefined)clearTimeout(timer);pendingReject=null;if(!finished&&iterator){try{const close=iterator.return;if(typeof close==='function')Promise.resolve(close.call(iterator)).catch(()=>{});}catch{}}}
}
