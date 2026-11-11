"""Fetch one pinned disposable test binary; never installs a service."""
raise RuntimeError('NATIVE_QUALIFICATION_PREREQUISITES_LOCKED')
import argparse
import hashlib
import io
from pathlib import Path
import sys
import urllib.request
import zipfile

PINS={
    'win32':('windows','consul.exe','41762ef5b98c8dd9b6852df6cfbceed37e7f0acc5760856be33100f1092475e1'),
    'linux':('linux','consul','acb0a1b5b2a22a5fadb5d725f03610335e499e193eeade9df458c6c6017a77f4'),
}
parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True);args=parser.parse_args()
platform,name,pin=PINS[sys.platform]
destination=Path(args.directory).absolute();destination.mkdir(parents=True,exist_ok=False)
url='https://releases.hashicorp.com/consul/1.22.2/consul_1.22.2_'+platform+'_amd64.zip'
with urllib.request.urlopen(url,timeout=60) as response:
    raw=response.read(128*1024*1024+1)
assert len(raw)<=128*1024*1024
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
    member=archive.getinfo(name);assert member.file_size<=256*1024*1024
    binary=archive.read(member)
assert hashlib.sha256(binary).hexdigest()==pin
target=destination/name
with target.open('xb') as stream:stream.write(binary)
if sys.platform=='linux':target.chmod(0o700)
print(str(target))
