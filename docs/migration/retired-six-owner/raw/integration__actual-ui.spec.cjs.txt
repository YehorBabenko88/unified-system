const {test,expect}=require('@playwright/test');
const fs=require('node:fs'),path=require('node:path');
const evidence=path.resolve(process.env.FIVE_EVIDENCE);
function select(n){fs.copyFileSync(path.join(evidence,`lifecycle-${n}.json`),path.join(evidence,'current.json'))}
test('actual lifecycle file -> actual Terminan HTTP -> Chromium controls',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',route=>new URL(route.request().url()).hostname==='127.0.0.1'?route.continue():route.abort());
 await page.goto('/infrastructure');
 for(const n of [0,1,5,6,7,10]){select(n);await page.getByRole('button',{name:'Refresh',exact:true}).click();await expect(page.locator('#status')).toContainText(`${n} observed`);await expect(page.locator('#nodes article')).toHaveCount(Math.max(n,6))}
 const controls=await page.locator('button,input,select,textarea,a,[role="button"],[contenteditable="true"]').evaluateAll(nodes=>nodes.map(n=>({tag:n.tagName,id:n.id,text:n.textContent.trim(),disabled:n.disabled===true})));
 const expectedIds=new Set(['refresh','search','filter','timeframe']);
 expect(controls.filter(c=>c.id)).toHaveLength(4);
 for(const control of controls){if(control.id)expect(expectedIds.has(control.id)).toBe(true);else expect(control.tag==='BUTTON'&&/^node-[0-9]$/.test(control.text)&&!control.disabled).toBe(true)}
 expect(controls).toHaveLength(14);
 fs.writeFileSync(path.join(evidence,'chromium-control-inventory.json'),JSON.stringify(controls,null,2));
 for(let i=0;i<10;i++){await page.getByRole('button',{name:`node-${i}`,exact:true}).click();await expect(page.locator('#selected')).toContainText(`node-${i}`)}
 await page.locator('#search').fill('node-1');await expect(page.locator('#nodes article')).toHaveCount(1);
 await page.getByRole('button',{name:'node-1',exact:true}).click();await expect(page.locator('#selected')).toContainText('node-1');
 await page.locator('#search').fill('');await page.locator('#filter').selectOption('ACTIVE');await expect(page.locator('#nodes article')).toHaveCount(10);
 await page.locator('#filter').selectOption('OFFLINE');await expect(page.locator('#nodes article')).toHaveCount(0);await expect(page.locator('#selected')).toHaveText('UNAVAILABLE');
 await page.locator('#filter').selectOption('');await page.locator('#timeframe').selectOption('300000');await expect(page.locator('#nodes article')).toHaveCount(0);
 await page.locator('#timeframe').selectOption('3600000');await expect(page.locator('#nodes article')).toHaveCount(0);
 await page.locator('#timeframe').selectOption('0');await expect(page.locator('#nodes article')).toHaveCount(10);
 await expect(page.locator('#links')).toContainText('no verified links');await expect(page.locator('#nodes')).toContainText('DB sizes UNAVAILABLE');await expect(page.locator('#nodes')).toContainText('CPU UNAVAILABLE');
 await expect(page.locator('#stages p')).toHaveCount(7);await expect(page.locator('#stages')).toContainText('INFRA_PREFLIGHT');await expect(page.locator('#stages')).toContainText('NOT_STARTED');await expect(page.locator('#stages')).toContainText('STEADY_STATE');await expect(page.locator('#modules')).toContainText('NOT_AUTHORIZED');
 await page.screenshot({path:path.join(evidence,'actual-chromium.png'),fullPage:true});expect(errors).toEqual([]);
});
test('cancelled stale HTTP response cannot replace latest actual source',async({page})=>{
 select(1);let first=true,capturedResolve,releaseResolve,lateResolve;
 const captured=new Promise(resolve=>{capturedResolve=resolve}),release=new Promise(resolve=>{releaseResolve=resolve}),late=new Promise(resolve=>{lateResolve=resolve});
 const observed={old_count:null,new_count:null,late_attempt:false};
 await page.route('**/api/infrastructure',async route=>{
  const isOld=first;first=false;const response=await route.fetch(),body=await response.json();
  if(isOld){observed.old_count=body.nodes.length;capturedResolve();await release;observed.late_attempt=true}else observed.new_count=body.nodes.length;
  try{await route.fulfill({response})}catch{}finally{if(isOld)lateResolve()}
 });
 try{
  await page.goto('/infrastructure');await captured;expect(observed.old_count).toBe(1);
  select(10);await page.getByRole('button',{name:'Refresh',exact:true}).click();await expect(page.locator('#status')).toContainText('10 observed');expect(observed.new_count).toBe(10);
  releaseResolve();await late;await page.waitForTimeout(500);await expect(page.locator('#status')).toContainText('10 observed');expect(observed.late_attempt).toBe(true);
  observed.final_status=await page.locator('#status').textContent();fs.writeFileSync(path.join(evidence,'stale-actual-http-proof.json'),JSON.stringify(observed,null,2));
 }finally{releaseResolve()}
});
test('real missing snapshot renders explicit error and recovers',async({page})=>{
 fs.unlinkSync(path.join(evidence,'current.json'));await page.goto('/infrastructure');await expect(page.locator('#status')).toContainText('SOURCE_INVALID_OR_UNAVAILABLE');select(6);await page.getByRole('button',{name:'Refresh',exact:true}).click();await expect(page.locator('#status')).toContainText('6 observed');
});
test('actual socket disconnect becomes unavailable then recovers',async({page})=>{
 select(6);await page.goto('/infrastructure');await expect(page.locator('#status')).toContainText('6 observed');
 const flag=path.join(evidence,'disconnect.flag');fs.writeFileSync(flag,'TEST_TRANSPORT_CLOSE');
 try{await page.getByRole('button',{name:'Refresh',exact:true}).click();await expect(page.locator('#status')).toContainText('UNAVAILABLE')}finally{fs.unlinkSync(flag)}
 await page.getByRole('button',{name:'Refresh',exact:true}).click();await expect(page.locator('#status')).toContainText('6 observed');
});
