"""Actual Gateway->Grid bridge; modeled HTTP Consul only, no native/HA PASS.

Run with GRID_TEST_ROOT pointing to the reviewed Grid checkout. Absence skips
explicitly; the fixture is never admitted as a runtime identity provider.
"""
import importlib.util
import asyncio
import os
from pathlib import Path
import sys
import unittest
from unified_system.operator_control_plane import OperatorGateway, CurrentPrincipal, AuthorizationDenied

GRID_ROOT=os.environ.get('GRID_TEST_ROOT')


@unittest.skipUnless(GRID_ROOT,'GRID_TEST_ROOT required for actual cross-repository composition')
class GridCompositionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        root=Path(GRID_ROOT).resolve()
        if not (root/'grid/coordination_commands.py').is_file():
            self.fail('GRID_TEST_ROOT does not contain actual Grid bridge')
        sys.path.insert(0,str(root))
        self.addCleanup(lambda: sys.path.remove(str(root)))
        from grid.coordination_commands import CoordinationCommands
        spec=importlib.util.spec_from_file_location('modeled_grid_commands_fixture',
            root/'tests/coordination/test_coordination_commands.py')
        fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
        self.fixtures=fixtures
        self.authority,self.client,self.store,self.state=fixtures.fixture()
        await self.client.__aenter__()
        self.addAsyncCleanup(self.client.__aexit__,None,None,None)
        self.lease=await self.authority.acquire('LS5')
        class ModeledProvider:
            active=True
            async def require_current(provider,context,action,aggregate_id):
                if not provider.active or context!='MODELED_HUMAN': raise AuthorizationDenied('revoked')
                return CurrentPrincipal('human-test',3,'HUMAN',frozenset({'research.control','control.commands.read'}))
        self.provider=ModeledProvider()
        self.bridge=CoordinationCommands(self.authority,fixtures.GEN,principal_provider=self.provider)
        self.gateway=OperatorGateway(self.bridge,self.provider)
    def envelope(self):
        value=self.fixtures.command()
        value.update(schema='unified.command.v1',aggregate_type='research',actor_id='human-test')
        return value
    async def test_commit_retry_read_and_unknown_reconcile_actual_bridge(self):
        value=self.envelope()
        first=await self.gateway.submit(self.lease,value,'MODELED_HUMAN')
        self.assertEqual(first['commit_status'],'COMMITTED')
        self.assertEqual(first['effect_status'],'PENDING_UNWIRED')
        self.assertEqual(await self.gateway.submit(self.lease,value,'MODELED_HUMAN'),first)
        self.assertEqual(await self.gateway.get_command(value['command_id'],'MODELED_HUMAN'),first)
        self.assertEqual(self.state['transactions'],1)
        unknown_id='33333333-3333-4333-8333-333333333333'
        unknown=await self.gateway.get_command(unknown_id,'MODELED_HUMAN')
        self.assertEqual(set(unknown),{'schema','command_id','generation','commit_status','effect_status'})
        self.assertEqual(unknown['commit_status'],'UNKNOWN')
        self.provider.active=False
        with self.assertRaises(AuthorizationDenied):
            await self.gateway.get_command(value['command_id'],'MODELED_HUMAN')
    async def test_lost_response_reconciles_same_command_and_two_windows(self):
        value=self.envelope();self.state['lost_response']=True
        result=await self.gateway.submit(self.lease,value,'MODELED_HUMAN')
        self.assertIn(result['commit_status'],('UNKNOWN','COMMITTED'))
        first,second=await asyncio.gather(
            self.gateway.submit(self.lease,value,'MODELED_HUMAN'),
            self.gateway.submit(self.lease,value,'MODELED_HUMAN'))
        self.assertEqual(first,second)
        self.assertEqual(first['commit_status'],'COMMITTED')
        self.assertEqual(self.state['transactions'],1)
    async def test_no_quorum_unknown_has_no_invented_owner(self):
        self.state['offline']=True
        result=await self.gateway.submit(self.lease,self.envelope(),'MODELED_HUMAN')
        self.assertEqual(result['commit_status'],'UNKNOWN')
        self.assertNotIn('actor_id',result)
        self.assertEqual(self.state['transactions'],0)
