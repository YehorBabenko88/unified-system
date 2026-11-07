"""Synthetic TEST-NET assets and modeled owner admission, never office trust."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

from unified_system.lan_probe_inventory import LanProbeInventory,LanInventoryBlocked


def key_blob(label):
    algorithm=b'ssh-ed25519';public=hashlib.sha256(('INERT_PUBLIC_FIXTURE_'+label).encode()).digest()
    return struct.pack('>I',len(algorithm))+algorithm+struct.pack('>I',len(public))+public


def fingerprint(blob):return 'SHA256:'+base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip('=')


class InventoryFixture:
    """No private key and no actual office IP/key is used in these fixtures."""
    def __init__(self,root):
        self.root=root;root.mkdir();self.live=True;self.identity_calls=[];self.endpoint_calls=[]
        self.path=root/'inventory.json';self.empty=root/'empty config';self.empty.write_bytes(b'')
        self.identity=root/'inert identity';self.identity.write_bytes(b'INERT_NOT_A_PRIVATE_KEY')
        self.data=dict(schema='unified.lan-probe-inventory.v1',installation_id='installation-1',empty_config=str(self.empty),nodes=[])
        for index,node in enumerate(('PC1','PC2','PC3','PC4','LS7'),11):
            blob=key_blob(node);public=base64.b64encode(blob).decode()
            known=root/(node.lower()+'.known_hosts')
            known.write_bytes(('unified-lan-'+node.lower()+' ssh-ed25519 '+public+'\n').encode())
            self.data['nodes'].append(dict(node=node,address='192.0.2.'+str(index),port=22,username='FixtureUser',host_key='ssh-ed25519 '+public,known_hosts=str(known),identity_file=str(self.identity),identity_public_fingerprint=fingerprint(key_blob('CLIENT'))))
        self.repin()
    def repin(self):
        self.path.write_text(json.dumps(self.data),encoding='utf-8')
        self.expected_sha=hashlib.sha256(self.path.read_bytes()).hexdigest()
    def require_current(self):return self.live
    def network_inventory_identity(self):
        return dict(path=self.path,sha256=self.expected_sha,installation_id='installation-1',private_root=self.root)
    def admit_lan_endpoint(self,node,descriptor):
        self.endpoint_calls.append((node,copy.deepcopy(descriptor)))
        return self.live and node in {row['node'] for row in self.data['nodes']}
    def admit_ssh_identity(self,node,facts,public_fingerprint):
        self.identity_calls.append((node,copy.deepcopy(facts),public_fingerprint))
        return self.live and facts['path']==self.identity and public_fingerprint==fingerprint(key_blob('CLIENT'))


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.fixture=InventoryFixture(Path(self.temp.name)/'private owner assets')
        self.inventory=LanProbeInventory(self.fixture)

    def test_fixed_direct_ip_user_and_exact_files_replace_all_ambient_aliases(self):
        with self.inventory.lease('PC1') as endpoint:
            argv=endpoint._argv('INERT_MODELED_COMMAND',cleanup=False)
            self.assertEqual(argv[-2:],[self.fixture.data['nodes'][0]['address'],'INERT_MODELED_COMMAND'])
            self.assertEqual(argv[argv.index('-F')+1],self.fixture.empty.as_posix())
            self.assertEqual(argv[argv.index('-l')+1],'FixtureUser')
            self.assertEqual(argv[argv.index('-i')+1],self.fixture.identity.as_posix())
            for option in ('HostKeyAlias=unified-lan-pc1','StrictHostKeyChecking=yes','KnownHostsCommand=none','IdentityAgent=none','IdentitiesOnly=yes','UpdateHostKeys=no','VerifyHostKeyDNS=no','CanonicalizeHostname=no','ProxyCommand=none','ProxyJump=none','PermitLocalCommand=no','GlobalKnownHostsFile="'+self.fixture.empty.as_posix()+'"'):
                self.assertIn(option,argv)
            self.assertNotIn('pc1',argv)
            self.assertTrue(self.fixture.identity_calls)
            self.assertEqual(endpoint.installation_id,'installation-1')

    def test_json_marker_or_truthy_callable_cannot_become_owner_admission(self):
        for admission in ({'approved':True},json.loads('{"require_current":true}')):
            with self.assertRaises(LanInventoryBlocked):LanProbeInventory(admission)
        with patch.object(self.fixture,'require_current',return_value=1):
            with self.assertRaises(LanInventoryBlocked):LanProbeInventory(self.fixture)

    def test_external_pin_not_an_inventory_claim_authorizes_bytes(self):
        self.fixture.data['sha256']='f'*64;self.fixture.path.write_text(json.dumps(self.fixture.data),encoding='utf-8')
        with self.assertRaises(LanInventoryBlocked):
            with self.inventory.lease('PC1'):pass

    def test_unknown_nodes_hostnames_ports_users_and_expansion_paths_rejected(self):
        baseline=copy.deepcopy(self.fixture.data)
        for change in ('adminit','hostname','port','user','alias','keypath','duplicate_host_key'):
            self.fixture.data=copy.deepcopy(baseline);row=self.fixture.data['nodes'][0]
            if change=='adminit':row['node']='ADMINIT'
            if change=='hostname':row['address']='pc1'
            if change=='port':row['port']=True
            if change=='user':row['username']='FixtureUser & whoami'
            if change=='alias':row['host_key_alias']='ADMINIT'
            if change=='keypath':row['identity_file']=str(self.fixture.root/'%USERPROFILE%')
            if change=='duplicate_host_key':row['host_key']=self.fixture.data['nodes'][1]['host_key']
            self.fixture.repin()
            with self.subTest(change=change),self.assertRaises(LanInventoryBlocked):
                with self.inventory.lease('PC1'):pass

    def test_unknown_extra_known_host_or_different_key_is_not_adopted(self):
        known=Path(self.fixture.data['nodes'][0]['known_hosts'])
        known.write_bytes(known.read_bytes()+b'ADMINIT ssh-ed25519 NOT_A_KEY\n')
        before=known.read_bytes()
        with self.assertRaises(LanInventoryBlocked):
            with self.inventory.lease('PC1'):pass
        self.assertEqual(known.read_bytes(),before)

    def test_downlevel_domain_user_is_one_explicit_literal_not_ambient_user(self):
        self.fixture.data['nodes'][0]['username']=r'EXAMPLE\FixtureUser'
        self.fixture.repin()
        with self.inventory.lease('PC1') as endpoint:
            argv=endpoint._argv('INERT_NOT_EXECUTED',cleanup=False)
            self.assertEqual(argv[argv.index('-l')+1],r'EXAMPLE\FixtureUser')

    @unittest.skipUnless(os.name=='nt','Windows mapped-drive classification model')
    def test_nonlocal_drive_rejected_before_any_descendant_probe(self):
        from unified_system import lan_probe_inventory as mod
        class RemoteDrive:
            def __call__(self,*args):return 4
        with patch.object(mod.ctypes,'WinDLL',return_value=SimpleNamespace(GetDriveTypeW=RemoteDrive())):
            with patch.object(Path,'lstat',side_effect=AssertionError('descendant probed')):
                with self.assertRaisesRegex(LanInventoryBlocked,'LAN_ASSET_NONLOCAL'):
                    mod._ordinary(Path('Z:/not-a-real-mapping/private-inventory'))

    def test_nonempty_config_is_rejected_before_any_identity_file_use(self):
        self.fixture.empty.write_bytes(b'Host *\n HostName ADMINIT\n KnownHostsCommand unknown-helper\n')
        with self.assertRaises(LanInventoryBlocked):
            with self.inventory.lease('PC1'):pass
        self.assertEqual(self.fixture.identity_calls,[])

    def test_private_identity_bytes_are_never_read_by_inventory_loader(self):
        from unified_system import lan_probe_inventory as mod
        original=mod._LockedRead.read
        def public_only(held,*args):
            if held.path==self.fixture.identity:self.fail('loader read private identity content')
            return original(held,*args)
        with patch.object(mod._LockedRead,'read',public_only):
            with self.inventory.lease('PC1') as endpoint:endpoint._current()

    def test_revoked_lease_can_only_finish_original_cleanup_not_start_or_publish(self):
        with self.inventory.lease('PC1') as endpoint:
            before=endpoint._argv('INERT_OWN_PROBE',cleanup=False)
            self.fixture.live=False
            with self.assertRaises(LanInventoryBlocked):endpoint._argv('INERT_NEW_PROBE',cleanup=False)
            cleanup=endpoint._argv('INERT_OWN_CLEANUP',cleanup=True)
            self.assertEqual(cleanup[:-1],before[:-1])
            with self.assertRaises(LanInventoryBlocked):endpoint._current()

    def test_identity_and_endpoint_owner_callbacks_are_literal_and_current(self):
        with patch.object(self.fixture,'admit_ssh_identity',return_value=1):
            with self.assertRaises(LanInventoryBlocked):
                with self.inventory.lease('PC1'):pass
        with patch.object(self.fixture,'admit_lan_endpoint',return_value=False):
            with self.assertRaises(LanInventoryBlocked):
                with self.inventory.lease('PC1'):pass

    @unittest.skipUnless(os.name=='nt','Local OpenSSH -G resolver model; never connects')
    def test_offline_ssh_resolver_ignores_redirect_config_and_disables_helpers(self):
        # A separate explicit fixture models what an ambient config can do;
        # this test never writes the user's real ~/.ssh/config or opens TCP.
        bad=self.fixture.root/'redirect config'
        bad.write_text('Host *\n HostName 203.0.113.99\n User WrongUser\n HostKeyAlias ADMINIT\n KnownHostsCommand INERT_NOT_EXECUTED\n',encoding='ascii')
        exe=r'C:\Windows\System32\OpenSSH\ssh.exe'
        baseline=subprocess.run([exe,'-G','-F',str(bad),'pc1'],stdin=subprocess.DEVNULL,capture_output=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(baseline.returncode,0)
        self.assertIn(b'hostname 203.0.113.99',baseline.stdout)
        self.assertIn(b'knownhostscommand INERT_NOT_EXECUTED',baseline.stdout)
        with self.inventory.lease('PC1') as endpoint:
            argv=endpoint._argv('INERT_NOT_EXECUTED',cleanup=False)
            result=subprocess.run(argv[:-2]+['-G',argv[-2]],stdin=subprocess.DEVNULL,capture_output=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode,0,(len(result.stderr),hashlib.sha256(result.stderr).hexdigest()))
        lines=dict(line.split(' ',1) for line in result.stdout.decode('utf-8').splitlines() if ' ' in line)
        self.assertEqual(lines['hostname'],'192.0.2.11')
        self.assertEqual(lines['user'],'FixtureUser')
        self.assertEqual(lines['hostkeyalias'],'unified-lan-pc1')
        # OpenSSH omits cleared pointer-valued options from -G. Require the
        # explicit disabling argv too; absence alone would not prove our policy.
        for key in ('knownhostscommand','identityagent','proxycommand'):
            self.assertIn(lines.get(key),(None,'none'))
        for option in ('KnownHostsCommand=none','IdentityAgent=none','ProxyCommand=none'):
            self.assertIn(option,argv)
        self.assertIn(lines['updatehostkeys'],('no','false'))
        self.assertNotIn('WrongUser',result.stdout.decode('utf-8'))

    @unittest.skipUnless(os.name=='nt','Native Windows file-share locks')
    def test_held_assets_deny_write_delete_and_allow_independent_read(self):
        assets=[self.fixture.path,self.fixture.empty,self.fixture.identity,Path(self.fixture.data['nodes'][0]['known_hosts'])]
        with self.inventory.lease('PC1'):
            for asset in assets:
                self.assertIsInstance(asset.read_bytes(),bytes)  # Only inert fixtures.
                with self.assertRaises(PermissionError):
                    with asset.open('r+b'):pass
                with self.assertRaises(PermissionError):asset.unlink()
        with self.fixture.empty.open('r+b'):pass


if __name__=='__main__':unittest.main()
