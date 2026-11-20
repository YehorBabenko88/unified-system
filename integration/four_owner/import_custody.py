"""Fresh external import-cache custody; source consistency, not code attestation.
Loaded from verified raw Root bytes before app/SDK imports, never via a pyc.
"""
import importlib.util,os,pathlib,stat,sys
SDK_TOP=frozenset(('market_data','terminan','market_math','market_compute_api','history_statistics'))
ROOT_TOP=frozenset(('unified_system','integration','scripts','tests'))
def application(name):return name.split('.')[0] in SDK_TOP|ROOT_TOP or name.startswith('test_')
def plain_directory(path):
 info=path.lstat()
 if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&1024:raise ValueError('IMPORT_CACHE_DIRECTORY_ALIAS')
 return info.st_dev,info.st_ino

def begin(cache,forbidden_roots):
 if not(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):raise ValueError('ISOLATED_NO_SITE_IMPORTS_REQUIRED')
 path=pathlib.Path(cache).absolute()
 if not pathlib.Path(cache).is_absolute() or '..' in path.parts or str(path).startswith(('//',chr(92))) or ':' in str(path)[len(path.drive):]:raise ValueError('ORDINARY_ABSOLUTE_IMPORT_CACHE_REQUIRED')
 if sys.pycache_prefix is None or pathlib.Path(sys.pycache_prefix).absolute()!=path:raise ValueError('MATCHING_CLI_IMPORT_CACHE_PREFIX_REQUIRED')
 if any(application(name) for name in sys.modules):raise ValueError('PRELOADED_APPLICATION_MODULE_REJECTED')
 if any(path.resolve().is_relative_to(root.resolve()) for root in forbidden_roots):raise ValueError('IMPORT_CACHE_INSIDE_SOURCE_OR_SDK')
 for parent in reversed(path.parents):plain_directory(parent)
 if path.exists() or path.is_symlink():raise ValueError('FRESH_IMPORT_CACHE_REQUIRED')
 path.mkdir();state=(path,plain_directory(path));empty(state);return state

def empty(state):
 path,identity=state
 if plain_directory(path)!=identity or any(path.iterdir()):raise ValueError('IMPORT_CACHE_NOT_EMPTY_OR_CHANGED')
 if sys.pycache_prefix is None or pathlib.Path(sys.pycache_prefix).absolute()!=path:raise ValueError('IMPORT_CACHE_PREFIX_CHANGED')

def verify_loaded(state,root,site):
 cache,_=state;records={}
 for name,module in tuple(sys.modules.items()):
  if not application(name):continue
  raw=getattr(module,'__file__',None)
  if raw is None:
   if name.split('.')[0] in SDK_TOP or not hasattr(module,'__path__') or any(not pathlib.Path(p).resolve().is_relative_to(root) for p in module.__path__):raise ValueError('APPLICATION_NAMESPACE_ORIGIN_REJECTED')
   continue
  source=pathlib.Path(raw).resolve()
  if source.suffix!='.py' or not any(source.is_relative_to(p) for p in (root,site)):raise ValueError('APPLICATION_SOURCE_ORIGIN_REJECTED')
  actual=getattr(module,'__cached__',None);expected=pathlib.Path(importlib.util.cache_from_source(str(source))).absolute()
  if actual is None or pathlib.Path(actual).absolute()!=expected or not expected.is_relative_to(cache):raise ValueError('APPLICATION_CACHED_PATH_REJECTED')
  records[name]=dict(source=str(source),cached=str(expected))
 empty(state);return records


def controlled_probe(root,state):
    """Harmless constant-only PEP552 control, not an application import."""
    prefix=sys.pycache_prefix;before=dict(sys.modules)
    try:
        import importlib.machinery,marshal,hashlib
        root=pathlib.Path(root);root.mkdir(exist_ok=False)
        source=root/'probe.py';approved=b'VALUE="APPROVED_SOURCE"\n';source.write_bytes(approved)
        def load():
            loader=importlib.machinery.SourceFileLoader('cache_custody_control',str(source))
            spec=importlib.util.spec_from_loader(loader.name,loader);module=importlib.util.module_from_spec(spec);loader.exec_module(module);return module.VALUE
        sys.pycache_prefix=None
        pyc=pathlib.Path(importlib.util.cache_from_source(str(source)));pyc.parent.mkdir()
        code=compile(b'VALUE="UNAPPROVED_CONTROL"\n',str(source),'exec',dont_inherit=True)
        pyc.write_bytes(importlib.util.MAGIC_NUMBER+(1).to_bytes(4,'little')+importlib.util.source_hash(approved)+marshal.dumps(code))
        negative=load();sys.pycache_prefix=prefix;positive=load()
        if negative!='UNAPPROVED_CONTROL' or positive!='APPROVED_SOURCE' or source.read_bytes()!=approved:raise ValueError('UNCHECKED_HASH_CACHE_CONTROL_FAILED')
        result=dict(scope='CONTROLLED_CONSTANT_ONLY_NO_APP_OR_AUTHENTICATION',without_prefix=negative,with_fresh_prefix=positive,source_sha256=hashlib.sha256(approved).hexdigest(),source_unchanged=True)
    finally:
        sys.pycache_prefix=prefix
        for name in tuple(sys.modules):
            if name not in before:del sys.modules[name]
        for name,module in before.items():sys.modules[name]=module
        empty(state)
    return result
