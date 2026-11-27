import {need,oid,id,exact} from './strict.mjs';
export const COLLECTOR_REPOSITORY='YehorBabenko88/unified-system';
export const COLLECTOR_WORKFLOW='/.github/workflows/ci-evidence-collector.yml@';
export const WORKLOAD_REPOSITORY='YehorBabenko88/math';
export const AUDIENCE_PREFIX='urn:unified-system:ci-evidence:';
const fields=Object.freeze(['repository','event','runId','attempt','sourceSha','workflowRef','workflowSha','collectorSha','collectorRepository']);
export function snapshotExpected(input){
 need(input!==null&&typeof input==='object'&&!Array.isArray(input));const descriptors=Object.getOwnPropertyDescriptors(input);exact(descriptors,fields);
 const out={};for(const key of fields){const d=descriptors[key];need(Object.hasOwn(d,'value')&&typeof d.value==='string'&&d.value.length<=512);out[key]=d.value;}
 need(out.repository===WORKLOAD_REPOSITORY&&out.collectorRepository===COLLECTOR_REPOSITORY&&out.event==='pull_request'&&id(out.runId)&&id(out.attempt)&&oid(out.sourceSha)&&oid(out.workflowSha)&&oid(out.collectorSha)&&/^YehorBabenko88\/math\/\.github\/workflows\/confidential-synthetic-e2e\.yml@refs\/pull\/[1-9][0-9]*\/merge$/.test(out.workflowRef));return Object.freeze(out);
}
