"""In-process source scope after raw kernel/capsule admission, not a JSON grant.

Only the protected raw dispatcher constructs this adapter after full admission.
It delegates revocation to the live grant and grants no execution or network
capability. Imported library code/test doubles are not kernel qualification.
"""
import copy,hashlib
from pathlib import Path
from .service_bootstrap import local,need

MODULES=frozenset(('unified-system','grid','strattester','meta_analyse','terminan','math'))

class StartupSourceAdmission:
 def __init__(self,grant,config,manifest):
  need(grant is not None and not isinstance(grant,dict) and callable(getattr(grant,'require_current',None)))
  self._grant=grant;self._config=copy.deepcopy(config);self._manifest=copy.deepcopy(manifest)
  self._roots={};self._identities={}
  need(grant.require_current() is True)
  for module in MODULES:
   root=local(grant.code_root/manifest['sources'][module]['root']);info=root.stat()
   need(root.is_dir() and grant.code_root in root.parents)
   self._roots[module]=root;self._identities[module]=(info.st_dev,info.st_ino)
  self._git=local(grant.code_root/manifest['git']);self._git_sha=manifest['files'][manifest['git']]['sha256']
  self.require_current()
 def require_current(self):
  need(self._grant.require_current() is True)
  for module,root in self._roots.items():
   info=local(root).stat();need((info.st_dev,info.st_ino)==self._identities[module])
  return True
 @property
 def git_executable(self):self.require_current();return str(self._git)
 @property
 def git_sha256(self):self.require_current();return self._git_sha
 def source_scope(self,module_id,actual_root,expected_commit):
  self.require_current();need(module_id in MODULES)
  root=local(actual_root);need(root==self._roots[module_id])
  need(expected_commit==self._manifest['sources'][module_id]['commit'])
  return root
 def source_identity(self,module_id):
  self.require_current();need(module_id in MODULES)
  return copy.deepcopy(self._manifest['sources'][module_id])
 def verification_launch(self,module_id):
  self.require_current();need(module_id=='strattester')
  root=self._grant.code_root;python=local(self._config['programs'][module_id]['argv'][0])
  entry=local(self._roots['unified-system']/'unified_system/service_entry.py')
  for path in (python,entry):
   relative=path.relative_to(root).as_posix();info=path.stat();need(path.is_file() and info.st_nlink==1 and info.st_size<=64*1024*1024)
   need(hashlib.sha256(path.read_bytes()).hexdigest()==self._manifest['files'][relative]['sha256'])
  self.require_current();return [str(python),'-I','-S','-B',str(entry),'--verify-module-source',module_id]
