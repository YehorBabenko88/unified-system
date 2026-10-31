"""Read-only offline artifact integrity; no download, extraction or execution.

The catalog must itself be independently reviewed/pinned by its consumer.
Matching these checksums grants neither publisher trust nor installation rights.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from urllib.parse import urlsplit

from .owned_python import reject_external_namespace
from .runtime_process import _safe_path

ERROR='WINDOWS_TOOLCHAIN_REJECTED'
HOSTS={'python':'api.nuget.org','node':'nodejs.org','git':'github.com',
       'postgresql':'get.enterprisedb.com','nssm':'www.nssm.cc'}
UNLOCKED={'python-wheels':'NO_REVIEWED_WINDOWS_WHEEL_CLOSURE','consul':'NO_REVIEWED_OFFICIAL_BINARY_PIN'}
BASES={'VENDOR_METADATA_REVIEWED','EXISTING_REPOSITORY_CI_PIN','THIRD_PARTY_VERIFICATION_PIN'}


def need(ok):
    if not ok:raise ValueError(ERROR)


def local(path):
    raw=str(path)
    # Lexical external/mapped-drive rejection before ANY descendant metadata.
    reject_external_namespace(raw)
    need(Path(path).is_absolute())
    return _safe_path(path)  # Existing ancestor-first symlink/reparse policy.


def validate_catalog(catalog):
    need(type(catalog) is dict and set(catalog)=={'schema','platform','scope','artifacts','required_unlocked'})
    need(catalog['schema']=='unified.windows.toolchain.catalog.v1' and catalog['platform']=='windows-x64'
         and catalog['scope']=='OFFLINE_BYTE_INTEGRITY_ONLY')
    artifacts=catalog['artifacts'];need(type(artifacts) is list and len(artifacts)==len(HOSTS))
    components=set();filenames=set()
    for item in artifacts:
        need(type(item) is dict and set(item)=={'component','version','filename','url','sha256','expected_bytes','max_bytes','provenance'})
        component=item['component'];need(type(component) is str and component in HOSTS and component not in components);components.add(component)
        filename=item['filename'];need(type(filename) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]{1,127}',filename)
            and not filename.endswith('.') and filename.split('.')[0].upper() not in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}
            and filename.casefold() not in filenames);filenames.add(filename.casefold())
        need(type(item['version']) is str and re.fullmatch('[0-9][A-Za-z0-9.-]{0,63}',item['version']))
        need(type(item['sha256']) is str and re.fullmatch('[a-f0-9]{64}',item['sha256']))
        need(type(item['max_bytes']) is int and 1<=item['max_bytes']<=1073741824)
        expected=item['expected_bytes'];need(expected is None or type(expected) is int and 1<=expected<=item['max_bytes'])
        need(type(item['url']) is str and len(item['url'])<=1024 and not re.search(r'[\x00-\x20\x7f\\]',item['url']))
        url=urlsplit(item['url'])
        need(url.scheme=='https' and url.hostname==HOSTS[component] and not url.username and not url.password
             and url.port is None and not url.query and not url.fragment and url.path.rsplit('/',1)[-1]==filename
             and '..' not in url.path.split('/') and '%' not in url.path)
        if component=='git':need(url.path.startswith('/git-for-windows/git/releases/download/'))
        provenance=item['provenance']
        need(type(provenance) is dict and set(provenance)=={'checksum_basis','reference','native_execution'})
        need(type(provenance['checksum_basis']) is str and provenance['checksum_basis'] in BASES and provenance['native_execution']=='NOT_RUN')
        need(type(provenance['reference']) is str and 1<=len(provenance['reference'])<=256 and not re.search(r'[\x00-\x1f\x7f]',provenance['reference']))
    unlocked=catalog['required_unlocked'];need(type(unlocked) is list and len(unlocked)==len(UNLOCKED))
    seen=set()
    for item in unlocked:
        need(type(item) is dict and set(item)=={'component','reason'})
        name=item['component'];need(type(name) is str and name in UNLOCKED and name not in seen and item['reason']==UNLOCKED[name]);seen.add(name)
    return catalog


def unique(pairs):
    out={}
    for k,v in pairs:need(k not in out);out[k]=v
    return out


def _read(path,maximum,expected=None):
    """Stream a fresh unique regular leaf; do not follow/open a pipe or link."""
    path=local(path);before=path.lstat()
    need(stat.S_ISREG(before.st_mode) and before.st_nlink==1)
    if before.st_size>maximum or expected is not None and before.st_size!=expected:return None,'SIZE_MISMATCH'
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NONBLOCK',0)|getattr(os,'O_NOFOLLOW',0))
    h=hashlib.sha256();total=0
    def identity(s):return (s.st_dev,s.st_ino,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    with os.fdopen(fd,'rb') as f:
        facts=os.fstat(f.fileno());need(stat.S_ISREG(facts.st_mode) and identity(facts)==identity(before))
        while True:
            chunk=f.read(min(1048576,maximum-total+1))
            if not chunk:break
            total+=len(chunk)
            if total>maximum:return None,'SIZE_MISMATCH'
            h.update(chunk)
        need(identity(os.fstat(f.fileno()))==identity(before))
    need(identity(local(path).lstat())==identity(before) and total==before.st_size)
    return h.hexdigest(),None


def read_catalog(path=None):
    path=local(Path(__file__).with_name('windows-toolchain.catalog.json') if path is None else path)
    try:
        facts=path.lstat();need(stat.S_ISREG(facts.st_mode) and facts.st_nlink==1 and 0<facts.st_size<=65536)
        # The catalog is bounded and read as data; no policy code is evaluated.
        fd=os.open(path,os.O_RDONLY|getattr(os,'O_NONBLOCK',0)|getattr(os,'O_NOFOLLOW',0))
        with os.fdopen(fd,'rb') as f:
            opened=os.fstat(f.fileno());need(stat.S_ISREG(opened.st_mode) and opened.st_nlink==1 and opened.st_size<=65536)
            raw=f.read(65537)
        need(len(raw)<=65536)
        return validate_catalog(json.loads(raw,object_pairs_hook=unique))
    except (OSError,TypeError,json.JSONDecodeError,KeyError):raise ValueError(ERROR) from None


def validate_artifact_directory(directory,*,catalog=None):
    """Read existing files only; missing/unlocked artifacts never grant closure."""
    root=local(directory);need(root.is_dir())
    catalog=validate_catalog(catalog) if catalog is not None else read_catalog()
    results=[]
    for artifact in catalog['artifacts']:
        result={k:artifact[k] for k in ('component','version','filename')}
        result['checksum_basis']=artifact['provenance']['checksum_basis']
        try:
            digest,error=_read(root/artifact['filename'],artifact['max_bytes'],artifact['expected_bytes'])
            result['status']=error or ('BYTES_MATCH' if digest==artifact['sha256'] else 'DIGEST_MISMATCH')
        except FileNotFoundError:result['status']='MISSING'
        except (OSError,ValueError):result['status']='UNVERIFIED'
        results.append(result)
    return dict(schema='unified.windows.toolchain.integrity.v1',scope='OFFLINE_BYTE_INTEGRITY_ONLY',
        result='INCOMPLETE',artifacts=results,required_unlocked=[dict(i) for i in catalog['required_unlocked']],
        all_locked_artifacts_match=all(r['status']=='BYTES_MATCH' for r in results),installation_closure=False,
        publisher_authenticated=False,execution_authority=False,native_execution='NOT_RUN',physical='NOT_RUN')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--artifact-dir',required=True);p.add_argument('--catalog')
    args=p.parse_args(argv)
    try:
        result=validate_artifact_directory(args.artifact_dir,catalog=read_catalog(args.catalog) if args.catalog else None)
        print(json.dumps(result,sort_keys=True));return 1  # Known unlocked mandatory closure.
    except (OSError,ValueError,TypeError):print(ERROR);return 2


if __name__=='__main__':raise SystemExit(main())
