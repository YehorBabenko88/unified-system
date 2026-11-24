"""Pinned raw-script release preparation; no signing, network or installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import types

FILES=('unified_system/__init__.py','unified_system/module_catalog.py','unified_system/release_manifest.py')

def need(value):
    if not value:raise ValueError('RELEASE_PREPARATION_REJECTED')

def local(path,*,file=False):
    path=Path(path);raw=str(path)
    need(path.is_absolute() and not raw.startswith(('\\','//')) and '..' not in path.parts)
    if os.name=='nt':
        import ctypes
        need(re.match(r'^[A-Za-z]:[\\/]',raw) is not None)
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetDriveTypeW.argtypes=[ctypes.c_wchar_p];kernel.GetDriveTypeW.restype=ctypes.c_uint
        need(kernel.GetDriveTypeW(raw[:3])==3)
    for part in (*reversed(path.parents),path):
        facts=part.lstat();need(not stat.S_ISLNK(facts.st_mode) and not getattr(facts,'st_file_attributes',0)&1024)
    facts=path.stat()
    need(stat.S_ISREG(facts.st_mode) and facts.st_nlink==1 if file else stat.S_ISDIR(facts.st_mode))
    return path

def bounded(path,maximum):
    path=local(path,file=True)
    with path.open('rb') as stream:
        before=os.fstat(stream.fileno());need(before.st_size<=maximum)
        raw=stream.read(maximum+1);after=os.fstat(stream.fileno())
    need(len(raw)<=maximum and (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns))
    return raw

def strict(raw):
    def pairs(items):
        out={}
        for key,value in items:need(key not in out);out[key]=value
        return out
    return json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=lambda _:need(False))

def main():
    need(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode)
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--source-pins',type=Path,required=True)
    p.add_argument('--source-pins-sha256',required=True);p.add_argument('--template',type=Path,required=True)
    p.add_argument('--artifact-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--publisher',required=True)
    a=p.parse_args();root=local(a.source_root);output=local(a.output);artifacts=local(a.artifact_root)
    need(not any(output.iterdir()) and re.fullmatch('[0-9a-f]{64}',a.source_pins_sha256))
    pins_raw=bounded(a.source_pins,16384);need(hashlib.sha256(pins_raw).hexdigest()==a.source_pins_sha256)
    pins=strict(pins_raw);need(type(pins) is dict and set(pins)==set(FILES))
    source={}
    for name in FILES:
        need(type(pins[name]) is str and re.fullmatch('[0-9a-f]{64}',pins[name]))
        raw=bounded(root/name,1048576);need(hashlib.sha256(raw).hexdigest()==pins[name]);source[name]=raw
    # Execute only retained verified bytes. No .pth, untracked package, bytecode
    # cache or subsequent pathname replacement can select project imports.
    need(not any(name=='unified_system' or name.startswith('unified_system.') for name in sys.modules))
    for filename,name in zip(FILES,('unified_system','unified_system.module_catalog','unified_system.release_manifest')):
        module=types.ModuleType(name);module.__file__=str(root/filename);module.__package__='unified_system'
        if name=='unified_system':module.__path__=[]
        sys.modules[name]=module;exec(compile(source[filename],module.__file__,'exec'),module.__dict__)
    api=sys.modules['unified_system.release_manifest'];manifest=strict(bounded(a.template,1048576))
    api.validate_manifest(manifest,expected_publisher=a.publisher)
    modules=output/'modules';modules.mkdir()
    for value in manifest['modules'].values():
        descriptor=value['artifact'];path=local(artifacts/descriptor['path'],file=True)
        with path.open('rb') as src,(output/descriptor['path']).open('xb') as dst:
            before=os.fstat(src.fileno());need(before.st_size==descriptor['bytes'])
            h=hashlib.sha256();count=0
            for chunk in iter(lambda:src.read(1048576),b''):
                count+=len(chunk);need(count<=descriptor['bytes']);h.update(chunk);dst.write(chunk)
            dst.flush();os.fsync(dst.fileno());after=os.fstat(src.fileno())
        need(count==descriptor['bytes'] and h.hexdigest()==descriptor['sha256'])
        need((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns))
    raw=api.canonical(manifest)
    with (output/'release.json').open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    print(json.dumps({'schema':'unified.release.preparation.v1','release_sha256':hashlib.sha256(raw).hexdigest(),'signed':False,'modules':len(manifest['modules'])}))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,TypeError,UnicodeError,RecursionError):raise SystemExit('RELEASE_PREPARATION_REJECTED')
