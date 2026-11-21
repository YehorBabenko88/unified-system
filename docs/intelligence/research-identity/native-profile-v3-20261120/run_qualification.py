"""Canonical Root-owned native source qualification; hosted execution only."""
import argparse,os,re,subprocess,sys,types
from pathlib import Path

def main():
 if not (sys.flags.isolated and sys.dont_write_bytecode and sys.pycache_prefix is None):raise ValueError('PYTHON_ISOLATION')
 forbidden=('GIT_DIR','GIT_WORK_TREE','GIT_COMMON_DIR','GIT_INDEX_FILE','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES','GIT_REPLACE_REF_BASE','GIT_CONFIG','GIT_CONFIG_GLOBAL','GIT_CONFIG_SYSTEM','GIT_CONFIG_COUNT','GIT_CONFIG_PARAMETERS','GIT_CONFIG_KEY_','GIT_CONFIG_VALUE_')
 if any(name==prefix or prefix.endswith('_') and name.startswith(prefix) for name in os.environ for prefix in forbidden):raise ValueError('GIT_ENV_OVERRIDE_REJECTED')
 parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--expected-head',required=True)
 args,_=parser.parse_known_args()
 if re.fullmatch('[a-f0-9]{40}',args.expected_head) is None:raise ValueError('EXPECTED_HEAD')
 root=Path(__file__).absolute().parents[4]
 helper=root/'docs/intelligence/native-negative/canonical-v2-20261120/source_harness.py'
 git=Path('C:/Program Files/Git/cmd/git.exe' if sys.platform=='win32' else '/usr/bin/git')
 def read(*arguments):return subprocess.check_output([str(git),'--no-replace-objects','--no-optional-locks','-c','core.fsmonitor=false','-C',str(root),*arguments],timeout=30)
 if read('rev-parse','HEAD').decode().strip()!=args.expected_head:raise ValueError('HEAD_MISMATCH')
 committed=read('show',args.expected_head+':docs/intelligence/native-negative/canonical-v2-20261120/source_harness.py')
 if helper.read_bytes()!=committed:raise ValueError('HARNESS_SOURCE_MISMATCH')
 module=types.ModuleType('root_source_harness');module.__file__=str(helper)
 exec(compile(committed,str(helper),'exec'),module.__dict__)
 module.entrypoint('research_identity',__file__)
if __name__=='__main__':main()
