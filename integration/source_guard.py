"""Git-byte/source-origin fence. This proves source consistency, never authenticity."""
from pathlib import Path
import configparser
import hashlib
import os
import subprocess
import sys


class SourceQualificationError(ValueError):
    pass


class SourceFence:
    def __init__(self, root, expected_head=None, *, isolated_cache=None):
        self.root=Path(root).resolve(strict=True)
        self.expected_head=expected_head
        self.before=None
        self.files={}
        self.blobs={}
        self.text={}
        self.isolated_cache=Path(isolated_cache).resolve() if isolated_cache else None
        if self.isolated_cache is not None and (sys.pycache_prefix is None or Path(sys.pycache_prefix).resolve()!=self.isolated_cache):raise SourceQualificationError('ISOLATED_CACHE_NOT_ACTIVE')
    def git(self,*args,input=None):
        env={key:value for key,value in os.environ.items() if not key.upper().startswith('GIT_')}
        env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_SYSTEM=os.devnull,GIT_ATTR_NOSYSTEM='1',GIT_NO_REPLACE_OBJECTS='1')
        result=subprocess.run(['git','--no-replace-objects','-C',str(self.root),*args],input=input,capture_output=True,env=env)
        if result.returncode:raise SourceQualificationError('GIT_CHECK_FAILED')
        return result.stdout
    def check(self):
        overrides={'GIT_DIR','GIT_WORK_TREE','GIT_COMMON_DIR','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES','GIT_CONFIG_PARAMETERS','GIT_CONFIG_COUNT','GIT_INDEX_FILE','GIT_REPLACE_REF_BASE'}
        if overrides.intersection(key.upper() for key in os.environ):raise SourceQualificationError('GIT_ENV_OVERRIDE')
        gitdir=self.root/'.git'
        if not gitdir.is_dir() or gitdir.is_symlink() or (gitdir/'commondir').exists():raise SourceQualificationError('EXTERNAL_GIT_DIRECTORY')
        if (gitdir/'objects/info/alternates').exists() or (gitdir/'info/attributes').exists():raise SourceQualificationError('EXTERNAL_OBJECTS_OR_ATTRIBUTES')
        config=configparser.RawConfigParser(strict=False)
        try:config.read_string((gitdir/'config').read_text(encoding='utf-8'))
        except (OSError,configparser.Error):raise SourceQualificationError('LOCAL_CONFIG_INVALID') from None
        for section in config.sections():
            lower=section.casefold()
            if lower.startswith(('include','filter')):raise SourceQualificationError('CONFIG_INCLUDE_OR_FILTER')
            if lower=='core' and any(key in config[section] for key in ('worktree','attributesfile')):raise SourceQualificationError('EXTERNAL_WORKTREE_OR_ATTRIBUTES')
            if lower=='extensions' and 'worktreeconfig' in config[section]:raise SourceQualificationError('EXTERNAL_WORKTREE_CONFIG')
        if self.git('for-each-ref','--format=%(refname)','refs/replace').strip():raise SourceQualificationError('REPLACE_REFS_FORBIDDEN')
        head=self.git('rev-parse','HEAD').decode().strip()
        if self.expected_head is not None and head!=self.expected_head:
            raise SourceQualificationError('SOURCE_PIN_MISMATCH')
        records=self.git('ls-tree','-rz','--full-tree','HEAD').split(b'\0')
        files={}
        for record in records:
            if not record:continue
            meta,raw=record.split(b'\t',1);mode,kind,blob=meta.split()
            relative=raw.decode('utf-8')
            if mode not in (b'100644',b'100755') or kind!=b'blob':
                raise SourceQualificationError('NON_REGULAR_SOURCE:'+relative)
            path=self.root/relative
            try:resolved=path.resolve(strict=True);resolved.relative_to(self.root)
            except (OSError,ValueError):raise SourceQualificationError('SOURCE_PATH_ESCAPE:'+relative) from None
            if path.is_symlink() or not path.is_file() or '\n' in relative or '\r' in relative:
                raise SourceQualificationError('NON_REGULAR_SOURCE:'+relative)
            files[relative]=blob.decode()
        if self.git('diff','--cached','--no-ext-diff','--no-textconv','--name-only','HEAD').strip():
            raise SourceQualificationError('INDEX_DIRTY')
        # cat-file reads immutable objects directly: NEVER hash-object/clean filters.
        unique=list(dict.fromkeys(files.values()))
        batch=self.git('cat-file','--batch',input=('\n'.join(unique)+'\n').encode())
        blobs={};offset=0
        for expected in unique:
            end=batch.index(b'\n',offset);header=batch[offset:end].split();offset=end+1
            if len(header)!=3 or header[0].decode()!=expected or header[1]!=b'blob':raise SourceQualificationError('OBJECT_IDENTITY')
            size=int(header[2]);body=batch[offset:offset+size];offset+=size+1
            if hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()!=expected:raise SourceQualificationError('OBJECT_BYTES')
            blobs[expected]=body
        attributes=self.git('check-attr','--cached','-z','--stdin','text',input=b'\0'.join(name.encode() for name in files)+b'\0').split(b'\0')
        text={attributes[i].decode():attributes[i+2].decode() for i in range(0,len(attributes)-1,3)}
        self.files=files;self.blobs=blobs;self.text=text
        runtime={}
        for relative,blob in files.items():
            raw=(self.root/relative).read_bytes()
            mode=self.compare(relative,raw)
            runtime[relative]={'blob':blob,'raw_sha256':hashlib.sha256(raw).hexdigest(),'comparison':mode}
        generated={'.git','node_modules','.source','test-results','five-source-evidence'}
        for raw in self.git('ls-files','--others','-z').split(b'\0'):
            if not raw:continue
            name=raw.decode('utf-8');path=Path(name)
            if any(part in generated for part in path.parts):continue
            if path.suffix.lower() in ('.pyc','.pyo') and self.isolated_cache is not None:continue
            if path.suffix.lower() in ('.py','.pyc','.pyo','.pyd','.so','.js','.cjs','.mjs'):
                raise SourceQualificationError('UNTRACKED_SOURCE:'+name)
        snapshot={'head':head,'tree':self.git('rev-parse','HEAD^{tree}').decode().strip(),'tracked_files':len(files),'runtime_files':runtime}
        if self.before is not None and snapshot!=self.before:
            raise SourceQualificationError('SOURCE_CHANGED_DURING_RUN')
        self.files=files
        if self.before is None:self.before=snapshot
        return snapshot
    def compare(self,relative,raw):
        blob=self.blobs[self.files[relative]]
        if raw==blob:return 'RAW_IDENTICAL'
        # Explicit guard text policy; -text in tracked attributes always wins.
        suffixes={'.py','.mjs','.cjs','.js','.json','.md','.yml','.yaml','.ps1','.psm1','.txt','.toml','.cfg','.ini','.html','.css','.sql','.sh','.bat','.cmd','.xml','.svg','.csv','.tsv','.log','.jsonl','.ndjson','.rst','.c','.h','.cpp','.hpp','.cs','.csproj','.sln','.props','.targets','.resx'}
        declared=self.text.get(relative)=='set' or Path(relative).suffix.lower() in suffixes or Path(relative).name in ('.gitattributes','.gitignore','Dockerfile','.env.example','LICENSE','Makefile','.dockerignore','.editorconfig','.npmrc')
        if self.text.get(relative)!='unset' and declared and b'\0' not in raw+blob:
            if raw.replace(b'\r\n',b'\n')==blob.replace(b'\r\n',b'\n'):return 'TEXT_EOL_ONLY'
        raise SourceQualificationError('TRACKED_BYTES_MISMATCH:'+relative)
    def module(self,module):
        raw=getattr(module,'__file__',None)
        if not raw:raise SourceQualificationError('IMPORT_ORIGIN_MISSING')
        cached=getattr(module,'__cached__',None)
        if cached:
            if self.isolated_cache is None:raise SourceQualificationError('ISOLATED_CACHE_REQUIRED')
            try:Path(cached).resolve().relative_to(self.isolated_cache)
            except ValueError:raise SourceQualificationError('BYTECODE_ORIGIN_OUTSIDE_ISOLATED_CACHE') from None
        return self.file(raw,python=True)
    def file(self,raw,*,python=False):
        try:
            lexical=Path(raw).absolute()
            # Windows DOS short names are lexical aliases, not escapes. Resolve
            # containment only after rejecting symlink/reparse ancestors.
            for component in (lexical,*lexical.parents):
                if component.is_symlink() or getattr(component.lstat(),'st_file_attributes',0)&1024:
                    raise ValueError('symlink or reparse import')
            path=Path(raw).resolve(strict=True)
            relative=path.relative_to(self.root).as_posix()
        except (OSError,ValueError):raise SourceQualificationError('IMPORT_ORIGIN_OUTSIDE_TREE') from None
        if relative not in self.files or python and path.suffix!='.py':
            raise SourceQualificationError('IMPORT_ORIGIN_UNTRACKED:'+relative)
        self.compare(relative,path.read_bytes())
        return relative
    def finish(self):
        if self.before is None:raise SourceQualificationError('PRECHECK_REQUIRED')
        return self.check()
