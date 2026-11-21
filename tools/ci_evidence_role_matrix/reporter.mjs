import {readFileSync} from 'node:fs';
import {projectTerminal} from './contract.mjs';
const plan=JSON.parse(readFileSync(new URL('./role-plan.json',import.meta.url)));
export default async function* reporter(source){
 try{
  for await(const event of source){const result=projectTerminal(event,plan,process.env.ROLE_SOURCE_ROOT);if(result)yield JSON.stringify(result)+'\n';}
 }catch{yield '{"refused":"E_TEST_EVENT"}\n';}
}
