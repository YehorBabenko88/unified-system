"""Preparation must finish under pinned isolated Python before signer access."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from tests.test_release_manifest import fixture

ROOT=Path(__file__).resolve().parents[1]
FILES=('unified_system/__init__.py','unified_system/module_catalog.py','unified_system/release_manifest.py')
SHELL=os.environ.get('UNIFIED_PREPARATION_TEST_SHELL','powershell')
if SHELL not in ('powershell','pwsh'):raise ValueError('explicit supported test shell required')


class ReleasePreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.source=self.root/'source';self.artifacts=self.root/'artifacts';(self.artifacts/'modules').mkdir(parents=True)
        pins={}
        for name in FILES:
            path=self.source/name;path.parent.mkdir(parents=True,exist_ok=True);raw=(ROOT/name).read_bytes();path.write_bytes(raw);pins[name]=hashlib.sha256(raw).hexdigest()
        self.pinfile=self.root/'pins.json';self.pinfile.write_text(json.dumps(pins))
        self.manifest=fixture()
        for name,module in self.manifest['modules'].items():
            raw=('fixture only '+name).encode();(self.artifacts/module['artifact']['path']).write_bytes(raw)
            module['artifact'].update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        self.template=self.root/'template.json';self.template.write_text(json.dumps(self.manifest))
    def command(self,output):
        return [sys.executable,'-I','-S','-B',str(ROOT/'scripts/prepare_unified_release.py'),
                '--source-root',str(self.source),'--source-pins',str(self.pinfile),'--source-pins-sha256',hashlib.sha256(self.pinfile.read_bytes()).hexdigest(),
                '--template',str(self.template),'--artifact-root',str(self.artifacts),'--output',str(output),'--publisher','d'*64]
    def test_actual_isolated_unsigned_preparation_and_source_pin_rejection(self):
        output=self.root/'stage';output.mkdir()
        r=subprocess.run(self.command(output),capture_output=True,text=True,timeout=15)
        self.assertEqual(r.returncode,0,r.stderr)
        evidence=json.loads(r.stdout);raw=(output/'release.json').read_bytes()
        self.assertEqual(evidence['release_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertFalse((output/'release.p7s').exists())
        marker=self.root/'untrusted-executed'
        (self.source/'unified_system/__init__.py').write_text('from pathlib import Path\nPath('+repr(str(marker))+').touch()\n')
        second=self.root/'second';second.mkdir()
        r=subprocess.run(self.command(second),capture_output=True,text=True,timeout=15)
        self.assertNotEqual(r.returncode,0);self.assertFalse(marker.exists());self.assertFalse((second/'release.json').exists())
    def test_incomplete_artifacts_and_nonisolated_invocation_fail_closed(self):
        (self.artifacts/'modules/math.zip').write_bytes(b'tampered')
        output=self.root/'stage';output.mkdir()
        r=subprocess.run(self.command(output),capture_output=True,text=True,timeout=15)
        self.assertNotEqual(r.returncode,0);self.assertFalse((output/'release.json').exists())
        command=self.command(output);command=[v for v in command if v not in ('-I','-S','-B')]
        r=subprocess.run(command,capture_output=True,text=True,timeout=15)
        self.assertNotEqual(r.returncode,0)
    @unittest.skipUnless(sys.platform=='win32','Windows certificate provider contract')
    def test_invalid_artifact_never_reaches_certificate_provider(self):
        (self.artifacts/'modules/math.zip').write_bytes(b'tampered')
        prep=ROOT/'scripts/prepare_unified_release.py'
        # Older builders have no isolated preparation entrypoint and fail this test.
        self.assertTrue(prep.is_file(),'pinned preparation entrypoint missing')
        args=['-Template',str(self.template),'-ArtifactRoot',str(self.artifacts),'-OutputDirectory',str(self.root/'signed'),
              '-CertificateThumbprint','0'*40,'-ExpectedPublisherSha256','d'*64,'-Python',sys.executable,
              '-PythonSha256',hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),'-PreparationSha256',hashlib.sha256(prep.read_bytes()).hexdigest(),
              '-SourcePinsPath',str(self.pinfile),'-SourcePinsSha256',hashlib.sha256(self.pinfile.read_bytes()).hexdigest(),'-SourceRoot',str(self.source),
              '-SecurityModuleSha256',hashlib.sha256((ROOT/'scripts/SecurityPackage.psm1').read_bytes()).hexdigest()]
        quote=lambda value:"'"+value.replace("'","''")+"'"
        code="Import-Module Microsoft.PowerShell.Utility; function Get-Item { param([string]$LiteralPath,[switch]$Force) if($LiteralPath.StartsWith('Cert:')){throw 'SIGNER_TOUCHED_BEFORE_PREPARATION'}; Microsoft.PowerShell.Management\\Get-Item -LiteralPath $LiteralPath -Force }; & "+quote(str(ROOT/'scripts/Build-UnifiedRelease.ps1'))+' '+ ' '.join(quote(x) if not x.startswith('-') else x for x in args)
        r=subprocess.run([SHELL,'-NoProfile','-NonInteractive','-Command',code],env={k:v for k,v in os.environ.items() if k.upper()!='PSMODULEPATH'},capture_output=True,text=True,timeout=20)
        self.assertNotEqual(r.returncode,0)
        self.assertNotIn('SIGNER_TOUCHED_BEFORE_PREPARATION',r.stderr)
        self.assertIn('RELEASE_PREPARATION_REJECTED',r.stderr)
    @unittest.skipUnless(sys.platform=='win32','Windows native signature verification')
    def test_unsigned_artifact_is_never_admitted_by_authenticode(self):
        artifact=self.root/'unsigned.ps1';artifact.write_text("Write-Output 'fixture'\n")
        quote=lambda value:"'"+str(value).replace("'","''")+"'"
        code="Import-Module "+quote(ROOT/'scripts/SecurityPackage.psm1')+" -Force; try { Test-UnifiedAuthenticodeArtifact -Path "+quote(artifact)+" -ExpectedPublisherSha256 ('a'*64); exit 3 } catch { if($_.Exception.Message -ne 'Authenticode signature is not valid'){throw}; 'UNSIGNED_REJECTED' }"
        r=subprocess.run([SHELL,'-NoProfile','-NonInteractive','-Command',code],env={k:v for k,v in os.environ.items() if k.upper()!='PSMODULEPATH'},capture_output=True,text=True,timeout=20)
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout.strip(),'UNSIGNED_REJECTED')
    @unittest.skipUnless(sys.platform=='win32','Windows file sharing prevents preparer replacement')
    def test_prepare_only_holds_verified_script_and_never_queries_signer(self):
        tools=self.root/'tools';tools.mkdir();prep=tools/'prepare_unified_release.py'
        wrapper=tools/'Build-UnifiedRelease.ps1';shutil.copyfile(ROOT/'scripts/Build-UnifiedRelease.ps1',wrapper)
        security=tools/'SecurityPackage.psm1';shutil.copyfile(ROOT/'scripts/SecurityPackage.psm1',security)
        prefix="import os\ntry:\n    with open(__file__,'ab') as f: f.write(b'UNVERIFIED_REPLACEMENT')\nexcept PermissionError:\n    pass\nelse:\n    raise RuntimeError('PREPARER_WAS_NOT_LOCKED')\n"
        prep.write_text(prefix+(ROOT/'scripts/prepare_unified_release.py').read_text())
        args=['-PrepareOnly','-Template',str(self.template),'-ArtifactRoot',str(self.artifacts),'-OutputDirectory',str(self.root/'unsigned-stage'),
              '-ExpectedPublisherSha256','d'*64,'-Python',sys.executable,'-PythonSha256',hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
              '-PreparationSha256',hashlib.sha256(prep.read_bytes()).hexdigest(),'-SourcePinsPath',str(self.pinfile),'-SourcePinsSha256',hashlib.sha256(self.pinfile.read_bytes()).hexdigest(),
              '-SourceRoot',str(self.source),'-SecurityModuleSha256',hashlib.sha256(security.read_bytes()).hexdigest()]
        quote=lambda value:"'"+value.replace("'","''")+"'"
        code="& "+quote(str(wrapper))+' '+' '.join(quote(x) if not x.startswith('-') else x for x in args)
        r=subprocess.run([SHELL,'-NoProfile','-NonInteractive','-Command',code],env={k:v for k,v in os.environ.items() if k.upper()!='PSMODULEPATH'},capture_output=True,text=True,timeout=20)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('PREPARED_UNSIGNED_RELEASE',r.stdout);self.assertFalse((self.root/'unsigned-stage/release.p7s').exists())


if __name__=='__main__':unittest.main()
