"""Download only pinned disposable test binary; no installation/service changes."""
import argparse,hashlib,io,json,os,sys,urllib.request,zipfile
from pathlib import Path
PINS={
 'win32':('windows','consul.exe','7b8a3bb723017d1be87decf3a7bb12661c36e43eba8283b8c04eca60501493ec','41762ef5b98c8dd9b6852df6cfbceed37e7f0acc5760856be33100f1092475e1'),
 'linux':('linux','consul','e9ad339128e396238f053269bf8f76aeba1b5fada6f6cb60ab19fe70e133acde','acb0a1b5b2a22a5fadb5d725f03610335e499e193eeade9df458c6c6017a77f4')}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 platform,name,zipsha,binsha=PINS[sys.platform];a.output.mkdir(parents=True,exist_ok=False)
 url='https://releases.hashicorp.com/consul/1.22.2/consul_1.22.2_'+platform+'_amd64.zip'
 with urllib.request.urlopen(url,timeout=60) as r:raw=r.read(128*1024*1024+1)
 if len(raw)>128*1024*1024 or hashlib.sha256(raw).hexdigest()!=zipsha:raise RuntimeError('ZIP_PIN')
 with zipfile.ZipFile(io.BytesIO(raw)) as z:binary=z.read(name)
 if hashlib.sha256(binary).hexdigest()!=binsha:raise RuntimeError('BINARY_PIN')
 path=a.output/name;path.write_bytes(binary)
 if sys.platform=='linux':path.chmod(0o700)
 (a.output/'provenance.json').write_bytes((json.dumps(dict(url=url,zip_sha256=zipsha,binary_sha256=binsha))+'\n').encode())
 print(str(path.resolve()))
