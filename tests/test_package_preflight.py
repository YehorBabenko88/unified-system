"""Actual raw isolated package preflight; disposable Git/artifact fixtures only."""
import hashlib,json,os,py_compile,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from tests.test_release_manifest import fixture
from unified_system.release_manifest import canonical

ROOT=Path(__file__).resolve().parents[1]
class PackagePreflightTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.home=Path(self.temp.name).resolve();self.repo=self.home/'trusted';self.repo.mkdir();self.package=self.home/'package';(self.package/'modules').mkdir(parents=True)
  self.cache_parent=self.home/'cache';self.cache_parent.mkdir()
  self.git=Path(shutil.which('git')).resolve();self.gitpin=hashlib.sha256(self.git.read_bytes()).hexdigest()
  for name in ('integration/source_guard.py','unified_system/__init__.py','unified_system/module_catalog.py','unified_system/release_manifest.py','unified_system/package_preflight.py'):
   source=ROOT/name
   if source.exists():
    target=self.repo/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
  def git(*args):return subprocess.check_output([str(self.git),'-C',str(self.repo),*args],stderr=subprocess.PIPE).decode().strip()
  self.command_git=git;git('init');git('add','.');git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','trusted fixture')
  self.head=git('rev-parse','HEAD');self.tree=git('rev-parse','HEAD^{tree}');self.guardpin=hashlib.sha256((self.repo/'integration/source_guard.py').read_bytes()).hexdigest()
  manifest=fixture()
  for name,descriptor in manifest['modules'].items():
   raw=('inert '+name).encode();(self.package/descriptor['artifact']['path']).write_bytes(raw);descriptor['artifact'].update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
  (self.package/'release.json').write_bytes(canonical(manifest))
 def command(self):
  return [sys.executable,'-I','-S','-B',str(self.repo/'unified_system/package_preflight.py'),'--source-root',str(self.repo),'--source-head',self.head,'--source-tree',self.tree,'--source-guard-sha256',self.guardpin,'--git-executable',str(self.git),'--git-sha256',self.gitpin,'--package-root',str(self.package),'--publisher-sha256','d'*64,'--cache-root',str(self.cache_parent)]
 def run_preflight(self,command=None,env=None):
  return subprocess.run(command or self.command(),env=env,capture_output=True,text=True,timeout=20)
 def test_real_raw_preflight_all_six_artifacts_and_no_authority(self):
  before={str(p):p.read_bytes() for p in self.package.rglob('*') if p.is_file()}
  result=self.run_preflight();self.assertEqual(result.returncode,0,result.stderr);out=json.loads(result.stdout)
  self.assertEqual(out['manifest_sha256'],hashlib.sha256((self.package/'release.json').read_bytes()).hexdigest())
  self.assertEqual(out['signature'],'EXTERNAL_CMS_REQUIRED');self.assertEqual(out['modules'],6);self.assertEqual(out['mode'],'PREPARE_ONLY')
  self.assertFalse(out['execution_authority']);self.assertFalse(out['trading_authorized']);self.assertFalse(out['physical_deployment_allowed'])
  self.assertEqual(before,{str(p):p.read_bytes() for p in self.package.rglob('*') if p.is_file()})
  self.assertEqual(self.command_git('status','--porcelain'),'');self.assertEqual(list(self.cache_parent.iterdir()),[])
 def test_poisoned_import_and_timestamp_cache_cannot_override_raw_pins(self):
  source=self.repo/'unified_system/__init__.py';honest=source.read_bytes();poison=self.home/'poison.py';malicious=b"raise RuntimeError('POISON')\n";poison.write_bytes(malicious+b' '*(len(honest)-len(malicious)));os.utime(poison,ns=(source.stat().st_atime_ns,source.stat().st_mtime_ns))
  cache=self.home/'poisoned';cache.mkdir()
  code='import importlib.util,sys;sys.pycache_prefix=sys.argv[1];print(importlib.util.cache_from_source(sys.argv[2]))'
  cached=Path(subprocess.check_output([sys.executable,'-c',code,str(cache),str(source)],text=True).strip());cached.parent.mkdir(parents=True);py_compile.compile(str(poison),cfile=str(cached),doraise=True)
  ambient=self.home/'ambient';ambient.mkdir();(ambient/'unified_system.py').write_text("raise RuntimeError('AMBIENT_IMPORT')")
  env=dict(os.environ,PYTHONPYCACHEPREFIX=str(cache),PYTHONPATH=str(ambient))
  attack=subprocess.run([sys.executable,'-B','-c','import sys;sys.path.insert(0,sys.argv[1]);import unified_system',str(self.repo)],env=env,capture_output=True,text=True)
  self.assertNotEqual(attack.returncode,0);self.assertIn('POISON',attack.stderr)
  result=self.run_preflight(env=env);self.assertEqual(result.returncode,0,result.stderr)
 def test_tampered_source_git_guard_and_artifact_are_rejected(self):
  for option in ('--git-sha256','--source-head','--source-tree','--source-guard-sha256'):
   command=self.command();command[command.index(option)+1]='0'*(64 if 'sha256' in option else 40)
   with self.subTest(option=option):self.assertNotEqual(self.run_preflight(command).returncode,0)
  fake_git=self.home/'tampered-git';fake_git.write_bytes(b'not executable');fake_git.chmod(0o700)
  command=self.command();command[command.index('--git-executable')+1]=str(fake_git)
  self.assertNotEqual(self.run_preflight(command).returncode,0)
  source=self.repo/'unified_system/__init__.py';marker=self.home/'BAD_IMPORT';source.write_text('from pathlib import Path;Path('+repr(str(marker))+').touch()')
  self.command_git('update-index','--assume-unchanged','unified_system/__init__.py')
  self.assertNotEqual(self.run_preflight().returncode,0);self.assertFalse(marker.exists());self.assertEqual(list(self.cache_parent.iterdir()),[])
 def test_required_flags_relative_namespace_and_bad_artifact_fail_closed(self):
  command=self.command()
  for flag in ('-I','-S','-B'):
   bad=command.copy();bad.remove(flag)
   with self.subTest(flag=flag):self.assertNotEqual(self.run_preflight(bad).returncode,0)
  bad=command.copy();bad[bad.index('--package-root')+1]='relative';self.assertNotEqual(self.run_preflight(bad).returncode,0)
  (self.package/'modules/grid.zip').write_bytes(b'tamper');self.assertNotEqual(self.run_preflight().returncode,0)
