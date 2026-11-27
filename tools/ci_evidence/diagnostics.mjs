export const INIT_PHASES=Object.freeze(['CONTEXT_INPUT','CONTEXT_API_RUN','CONTEXT_API_JOBS','CONTEXT_API_COMMIT','CONTEXT_SHAPE','CONTEXT_SOURCE_BINDING','RECEIVER_INIT','CHALLENGE_ISSUE','KEY_SETUP','DESCRIPTOR']);
export const INIT_CODES=Object.freeze(INIT_PHASES.map(p=>'E_'+p));
export const API_CODES=Object.freeze(['E_API_AUTH','E_API_UNAVAILABLE','E_API_RESPONSE','E_API_BOUND']);
const failures=new WeakMap();
export function initFailure(phase,error){
 const known=error!==null&&(typeof error==='object'||typeof error==='function')?failures.get(error):undefined;
 const selected=known?.phase??phase;const safe=INIT_PHASES.includes(selected)?selected:'CONTEXT_INPUT';
 const code=known?.code??('E_'+safe);const e=Error('CI_EVIDENCE_BLOCKED');failures.set(e,Object.freeze({phase:safe,code}));return e;
}
export function apiFailure(status){
 const valid=typeof status==='number'&&Number.isSafeInteger(status)&&status>=100&&status<=599;
 const code=valid&&(status===401||status===403)?'E_API_AUTH':valid&&(status===429||status>=500)?'E_API_UNAVAILABLE':'E_API_RESPONSE';
 const e=Error('CI_EVIDENCE_BLOCKED');failures.set(e,Object.freeze({phase:null,code}));return e;
}
export function publicInitFailure(error){
 const known=error!==null&&(typeof error==='object'||typeof error==='function')?failures.get(error):undefined;
 return Object.freeze(known?.phase?{phase:known.phase,code:known.code}:{phase:'CONTEXT_INPUT',code:'E_INTERNAL'});
}
export async function atInitPhase(phase,operation){try{return await operation();}catch(error){throw initFailure(phase,error);}}

export function apiFailureFrom(error){const known=error!==null&&(typeof error==='object'||typeof error==='function')?failures.get(error):undefined;const e=Error('CI_EVIDENCE_BLOCKED');failures.set(e,Object.freeze({phase:null,code:API_CODES.includes(known?.code)?known.code:'E_API_RESPONSE'}));return e;}
export function apiBoundFailure(){const e=Error('CI_EVIDENCE_BLOCKED');failures.set(e,Object.freeze({phase:null,code:'E_API_BOUND'}));return e;}
