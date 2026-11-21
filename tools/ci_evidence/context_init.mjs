import {INIT_PHASES,initFailure} from './diagnostics.mjs';
/** Only production worker supplies real owned effects. Inert tests exercise refusals, never authentication. */
export async function initializeContext(expected,deps){
 let phase='CONTEXT_INPUT',journal;
 const stage=value=>{if(!INIT_PHASES.includes(value))throw initFailure(phase);phase=value;};
 try{
  const discovered=await deps.discover(expected,stage);stage('RECEIVER_INIT');journal=deps.openJournal();
  stage('CHALLENGE_ISSUE');const session=deps.createSession(journal,discovered,stage);
  stage('DESCRIPTOR');const descriptor=session.describe();return {journal,session,descriptor};
 }catch(error){try{journal?.close();}catch{}throw initFailure(phase,error);}
}
