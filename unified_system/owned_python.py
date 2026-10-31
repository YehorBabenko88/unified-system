"""Raw-script owned Python bootstrap. External launch policy must pin this file.

Usage: python -I -S -B owned_python.py --source-root /repo --module pkg.module
       [--dependency-root /explicit/root ...] [-- application arguments ...]
No site initialization, .pth processing, source self-authorization or new process.
"""
import sys



def reject_external_namespace(path,*,platform=None,drive_type=None):
    """Lexical rejection before ANY metadata access; fixed Windows drives only."""
    import os
    import re
    if type(path) is not str or path.startswith(('//',chr(92))):
        raise ValueError('OWNED_PYTHON_REJECTED')
    if (os.name if platform is None else platform)=='nt':
        if re.match(r'^[A-Za-z]:[\\/]',path) is None:raise ValueError('OWNED_PYTHON_REJECTED')
        if drive_type is None:
            import ctypes
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.GetDriveTypeW.argtypes=[ctypes.c_wchar_p];kernel.GetDriveTypeW.restype=ctypes.c_uint
            drive_type=kernel.GetDriveTypeW
        if drive_type(path[:3])!=3:raise ValueError('OWNED_PYTHON_REJECTED')


def main():
    # These interpreter flags must be effective before any application imports.
    if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
        raise ValueError('OWNED_PYTHON_REQUIRED_FLAGS')
    import argparse
    import importlib.util
    import os
    from pathlib import Path
    import re
    import runpy
    import stat
    import tempfile

    def need(ok):
        if not ok:raise ValueError('OWNED_PYTHON_REJECTED')
    def local(path):
        reject_external_namespace(path)
        need(type(path) is str and Path(path).is_absolute() and '..' not in Path(path).parts)
        p=Path(path)
        for part in (*reversed(p.parents),p):
            info=part.lstat()
            need(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&1024)
        need(str(p.resolve(strict=True))==path)
        return p
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-root',required=True)
    parser.add_argument('--module',required=True)
    parser.add_argument('--dependency-root',action='append',default=[])
    parser.add_argument('application_args',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    identity=os.environ
    need(re.fullmatch('[a-z][a-z0-9_-]{0,63}',identity.get('UNIFIED_MODULE_ID','')) is not None)
    need(re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]{1,40})?',identity.get('UNIFIED_MODULE_VERSION','')) is not None)
    need(re.fullmatch('[A-Za-z0-9_.:-]{1,128}',identity.get('UNIFIED_RELEASE_ID','')) is not None)
    need(re.fullmatch('[a-f0-9]{64}',identity.get('UNIFIED_INSTANCE_TOKEN','')) is not None)
    cache=local(identity.get('UNIFIED_PRIVATE_CACHE_ROOT',''));need(cache.is_dir())
    info=cache.stat()
    if os.name!='nt':need(info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)&0o077==0)
    fresh=tempfile.mkdtemp(prefix='owned-python-',dir=cache);os.chmod(fresh,0o700)
    sys.pycache_prefix=fresh;sys.dont_write_bytecode=True
    os.environ.update(PYTHONPYCACHEPREFIX=fresh,PYTHONDONTWRITEBYTECODE='1')
    root=local(args.source_root);need(root.is_dir())
    need(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*',args.module) is not None)
    need(len(args.module)<=256 and len(args.dependency_root)<=32)
    relative=Path(*args.module.split('.'))
    base=None;expected_entry=None
    for candidate in (root/'src',root):
        # Check ancestors first even during module discovery.
        try:
            local(str(candidate))
            for entry in (candidate/relative.with_suffix('.py'),candidate/relative/'__main__.py'):
                try:checked=local(str(entry))
                except FileNotFoundError:continue
                if checked.is_file():base=candidate;expected_entry=checked;break
        except FileNotFoundError:continue
        if base is not None:break
    need(base is not None)
    dependencies=[local(p) for p in args.dependency_root];need(all(p.is_dir() for p in dependencies))
    # Keep interpreter stdlib roots; -I/-S supplied no application/site paths.
    sys.path[:0]=[str(base),*(str(p) for p in dependencies)]
    parts=args.module.split('.')
    package_count=len(parts) if expected_entry.name=='__main__.py' else len(parts)-1
    for count in range(1,package_count+1):
        initializer=local(str(base.joinpath(*parts[:count])/'__init__.py'))
        need(initializer.is_file())
    spec_name=args.module+'.__main__' if expected_entry.name=='__main__.py' else args.module
    module_spec=importlib.util.find_spec(spec_name)
    need(module_spec is not None and module_spec.origin is not None
         and module_spec.origin not in ('frozen','built-in')
         and local(module_spec.origin)==expected_entry)
    application=args.application_args
    if application[:1]==['--']:application=application[1:]
    sys.argv=[args.module,*application]
    runpy.run_module(args.module,run_name='__main__',alter_sys=True)
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError):
        print('OWNED_PYTHON_REJECTED',file=sys.stderr);raise SystemExit(1)
