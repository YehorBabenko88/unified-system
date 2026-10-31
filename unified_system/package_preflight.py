"""Raw isolated, externally pinned package preflight; never an admission gate.

The caller MUST verify the absolute Python executable and this raw script against
external hashes before launch. No package code is imported until the externally
pinned source guard has verified the exact complete Root source and Git runtime.
"""
import sys


def main():
    if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
        raise ValueError('PACKAGE_PREFLIGHT_REJECTED')
    import argparse
    import hashlib
    import json
    import os
    from pathlib import Path
    import re
    import stat
    import tempfile

    def need(ok):
        if not ok:raise ValueError('PACKAGE_PREFLIGHT_REJECTED')
    def local(raw):
        need(type(raw) is str and not raw.startswith(('//',chr(92))))
        if os.name=='nt':
            import ctypes
            need(re.match(r'^[A-Za-z]:[\\/]',raw) is not None)
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.GetDriveTypeW.argtypes=[ctypes.c_wchar_p];kernel.GetDriveTypeW.restype=ctypes.c_uint
            need(kernel.GetDriveTypeW(raw[:3])==3)
        path=Path(raw);need(path.is_absolute() and '..' not in path.parts)
        for part in (*reversed(path.parents),path):
            facts=part.lstat();need(not stat.S_ISLNK(facts.st_mode) and not getattr(facts,'st_file_attributes',0)&1024)
        return path.resolve(strict=True)
    def read_file(path,limit,*,expected_size=None):
        path=local(str(path));fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
        with os.fdopen(fd,'rb') as stream:
            before=os.fstat(stream.fileno());need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=limit)
            if expected_size is not None:need(before.st_size==expected_size)
            raw=stream.read(limit+1);need(len(raw)==before.st_size)
            after=os.fstat(stream.fileno());need((before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino))
            return raw
    parser=argparse.ArgumentParser()
    for name in ('source-root','source-head','source-tree','source-guard-sha256','git-executable','git-sha256','package-root','publisher-sha256'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--cache-root')
    args=parser.parse_args()
    for value,size in ((args.source_head,40),(args.source_tree,40),(args.source_guard_sha256,64),(args.git_sha256,64),(args.publisher_sha256,64)):
        need(re.fullmatch('[a-f0-9]{'+str(size)+'}',value) is not None)
    root=local(args.source_root);package=local(args.package_root);git=local(args.git_executable)
    need(root.is_dir() and package.is_dir() and git.is_file())
    need(local(__file__)==root/'unified_system/package_preflight.py')
    guard=root/'integration/source_guard.py'
    guard_raw=read_file(guard,1048576)
    need(hashlib.sha256(guard_raw).hexdigest()==args.source_guard_sha256)
    cache_parent=args.cache_root or next((os.environ[k] for k in ('TMPDIR','TEMP','TMP') if os.environ.get(k)),None) or ('C:\\Windows\\Temp' if os.name=='nt' else '/tmp')
    cache_parent=local(cache_parent);need(cache_parent.is_dir())
    # Explicit safe dir avoids tempfile probing an untrusted network TMP path.
    with tempfile.TemporaryDirectory(prefix='unified-package-preflight-',dir=cache_parent) as cache:
        os.chmod(cache,0o700);sys.pycache_prefix=cache;sys.dont_write_bytecode=True
        namespace={'__file__':str(guard),'__name__':'__preflight_source_guard__'}
        exec(compile(guard_raw,str(guard),'exec'),namespace)
        fence=namespace['SourceFence'](root,args.source_head,isolated_cache=cache,git_executable=str(git),git_sha256=args.git_sha256)
        before=fence.check();need(before['tree']==args.source_tree)
        fence.file(__file__,python=True);fence.file(guard,python=True)
        sys.path.insert(0,str(root))
        import unified_system
        from unified_system import release_manifest,module_catalog
        for module in (unified_system,release_manifest,module_catalog):fence.module(module)
        manifest_raw=read_file(package/'release.json',release_manifest.MAX_BYTES)
        manifest=release_manifest.parse_manifest(manifest_raw,expected_publisher=args.publisher_sha256)
        for descriptor in manifest['modules'].values():
            artifact=descriptor['artifact'];path=local(str(package/artifact['path']))
            path.relative_to(package)
            fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
            with os.fdopen(fd,'rb') as stream:
                before_file=os.fstat(stream.fileno());need(stat.S_ISREG(before_file.st_mode) and before_file.st_nlink==1 and before_file.st_size==artifact['bytes'])
                digest=hashlib.sha256();count=0
                while True:
                    part=stream.read(min(1048576,artifact['bytes']+1-count))
                    if not part:break
                    count+=len(part);need(count<=artifact['bytes']);digest.update(part)
                after=os.fstat(stream.fileno());need(count==artifact['bytes'] and digest.hexdigest()==artifact['sha256'])
                need((before_file.st_size,before_file.st_mtime_ns,before_file.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino))
        fence.finish()
        result=dict(schema='unified.package-preflight.v1',mode='PREPARE_ONLY',signature='EXTERNAL_CMS_REQUIRED',modules=len(manifest['modules']),manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),release_id=manifest['release_id'],source_head=before['head'],source_tree=before['tree'],services='NOT_INSTALLED',physical='NOT_AUTHORIZED',execution_authority=False,trading_authorized=False,physical_deployment_allowed=False)
    print(json.dumps(result,sort_keys=True,separators=(',',':')))
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        print('PACKAGE_PREFLIGHT_REJECTED',file=sys.stderr);raise SystemExit(1)
