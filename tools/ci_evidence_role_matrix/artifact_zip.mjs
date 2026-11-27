import {createHash} from 'node:crypto';
import {inflateRawSync} from 'node:zlib';
import {validateCell} from './contract.mjs';
const MAX_ARCHIVE=1048576,MAX_MEMBER=65536;
const need=x=>{if(!x)throw Error('ROOT_ARTIFACT_ZIP_REFUSED');};
const plainBuffer=x=>Buffer.isBuffer(x)&&Object.getPrototypeOf(x)===Buffer.prototype&&['length','byteLength','buffer','byteOffset','valueOf',Symbol.iterator,Symbol.toPrimitive].every(k=>Object.getOwnPropertyDescriptor(x,k)===undefined);
function crc32(bytes){let x=0xffffffff;for(const b of bytes){x^=b;for(let k=0;k<8;k++)x=(x>>>1)^((x&1)?0xedb88320:0);}return (x^0xffffffff)>>>0;}
/** Read one explicitly allowlisted basename; never extract any filesystem path. */
export function readArtifactMember(raw,member,expectedSha256){
 need(plainBuffer(raw)&&raw.length>=22&&raw.length<=MAX_ARCHIVE);
 raw=Buffer.from(raw);
 need(typeof member==='string'&&/^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/.test(member)&&!member.includes('..'));
 need(typeof expectedSha256==='string'&&/^[a-f0-9]{64}$/.test(expectedSha256)&&createHash('sha256').update(raw).digest('hex')===expectedSha256);
 const u16=o=>raw.readUInt16LE(o),u32=o=>raw.readUInt32LE(o),end=raw.length-22;
 need(u32(end)===0x06054b50&&u16(end+4)===0&&u16(end+6)===0&&u16(end+8)===1&&u16(end+10)===1&&u16(end+20)===0);
 const center=u32(end+16),centerSize=u32(end+12);need(center>=30&&center+centerSize===end&&center+46<=end&&u32(center)===0x02014b50);
 const made=u16(center+4),version=u16(center+6),flags=u16(center+8),method=u16(center+10);
 need([0,3].includes(made>>>8)&&[20,45].includes(made&255)&&[10,20].includes(version)&&(flags&~0x0808)===0&&[0,8].includes(method));
 const crc=u32(center+16),packed=u32(center+20),size=u32(center+24),nameSize=u16(center+28);
 need(size>0&&size<=MAX_MEMBER&&packed>0&&packed<=MAX_ARCHIVE&&nameSize===Buffer.byteLength(member,'ascii')&&u16(center+30)===0&&u16(center+32)===0&&u16(center+34)===0&&u16(center+36)===0&&u32(center+42)===0&&center+46+nameSize===end);
 const attributes=u32(center+38),mode=attributes>>>16;need((attributes&0xffff&~0x20)===0&&(mode===0||(mode&0xf000)===0x8000));
 const name=Buffer.from(member,'ascii');need(raw.subarray(center+46,end).equals(name));
 need(u32(0)===0x04034b50&&u16(4)===version&&u16(6)===flags&&u16(8)===method&&u16(10)===u16(center+12)&&u16(12)===u16(center+14)&&u16(26)===nameSize&&u16(28)===0);
 const start=30+nameSize,finish=start+packed;need(start<=center&&finish<=center&&raw.subarray(30,start).equals(name));
 if(flags&8){
  need(finish+16===center&&u32(finish)===0x08074b50&&u32(finish+4)===crc&&u32(finish+8)===packed&&u32(finish+12)===size);
  need((u32(14)===0&&u32(18)===0&&u32(22)===0)||(u32(14)===crc&&u32(18)===packed&&u32(22)===size));
 }else need(finish===center&&u32(14)===crc&&u32(18)===packed&&u32(22)===size);
 let data;
 if(method===0){need(packed===size);data=Buffer.from(raw.subarray(start,finish));}
 else{const inflated=inflateRawSync(raw.subarray(start,finish),{maxOutputLength:size,info:true});need(inflated.engine.bytesWritten===packed);data=inflated.buffer;}
 need(data.length===size&&crc32(data)===crc);return Buffer.from(data);
}
/** Fixed Root cell member plus the actual GitHub ZIP digest/size, not JSON hash. */
export function readCellArtifact(raw,cell,expectedSize,digest){
 validateCell(cell);need(Number.isSafeInteger(expectedSize)&&expectedSize>0&&expectedSize<=MAX_ARCHIVE&&plainBuffer(raw)&&raw.length===expectedSize);
 need(typeof digest==='string'&&/^sha256:[a-f0-9]{64}$/.test(digest));
 return readArtifactMember(raw,'roles-'+cell+'.json',digest.slice(7));
}
