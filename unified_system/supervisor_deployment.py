"""Reuse existing immutable capsule/installation plans; no physical actuator.

Supplied inventory and rollback references are metadata, never admission. The
actual native issuer, scheduler backend, service gate and rollback verification
must be qualified separately. This module never creates an install directory,
starts a service, sends market data, elects a leader or invokes a command.
"""
import copy
import re
from pathlib import Path
from . import lab_release
from .installation_transaction import source_plan
from .installation_service import _check_plan as check_service_plan

ORDER=('LS5','PC4','PC3','PC2','PC1','LS7')
COORDINATORS=frozenset(('LS5','PC4','PC3'))
HOME=frozenset(('PC1','LS7'))
NODE_FIELDS={'node_id','incarnation_id','os_edition','role','inventory_sha256'}
UUID=re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}')
LABEL=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}')
SHA=re.compile(r'[0-9a-f]{64}')

class DeploymentBlocked(ValueError):
    pass

def need(value):
    if not value:raise DeploymentBlocked('SUPERVISOR_DEPLOYMENT_NOT_ADMITTED')

def node(value):
    need(type(value) is dict and set(value)==NODE_FIELDS)
    need(type(value['node_id']) is str and value['node_id'] in ORDER)
    need(type(value['incarnation_id']) is str and UUID.fullmatch(value['incarnation_id']) is not None)
    need(type(value['inventory_sha256']) is str and SHA.fullmatch(value['inventory_sha256']) is not None)
    need(type(value['os_edition']) is str and value['os_edition'] in ('HOME','PRO'))
    need(value['role']==('COORDINATOR' if value['node_id'] in COORDINATORS else 'WORKER'))
    return copy.deepcopy(value)

class DeploymentControllerAdapter:
    def __init__(self,capsule_root,manifest_sha256):
        self._capsule=Path(capsule_root)
        need(self._capsule.is_absolute())
        lab_release.digest(manifest_sha256)
        self._pin=manifest_sha256
        self._report()
    def _report(self):
        # Existing verifier reads every closed file and detects changed bytes;
        # its source_provenance limitation must never be silently upgraded.
        return lab_release.verify_capsule(self._capsule,self._pin)
    def rollout(self,nodes,*,previous_release=None):
        report=self._report();manifest=report['manifest']
        need(type(nodes) is list and 1<=len(nodes)<=len(ORDER))
        chosen=[node(item) for item in nodes]
        need(len({item['node_id'] for item in chosen})==len(chosen))
        previous=copy.deepcopy(previous_release)
        if previous is not None:
            need(type(previous) is dict and set(previous)=={'release_id','manifest_sha256','backup_sha256'})
            need(type(previous['release_id']) is str and LABEL.fullmatch(previous['release_id']) is not None)
            for key in ('manifest_sha256','backup_sha256'):
                need(type(previous[key]) is str and SHA.fullmatch(previous[key]) is not None)
        steps=[]
        for item in sorted(chosen,key=lambda item:ORDER.index(item['node_id'])):
            expected='HOME' if item['node_id'] in HOME else 'PRO'
            drift=item['os_edition']!=expected
            requirements=['ACTUAL_SOURCE_ADMISSION','NATIVE_NODE_IDENTITY','CURRENT_AUTHORITY_AND_FENCING',
                'PROTECTED_INSTALLATION_ROOT','INSTALLER_SECURITY_GATE','VERIFIED_BACKUP_AND_ROLLBACK']
            requirements.append('CURRENT_QUORUM_AND_SPARE_VOTER' if item['node_id'] in COORDINATORS else 'DRAIN_AND_CHECKPOINT')
            if drift:requirements.append('EDITION_DRIFT')
            steps.append(dict(node=item,mode='PLAN_ONLY',blockers=requirements,local_health='UNKNOWN',
                authority_freshness='UNKNOWN',data_integrity='CAPSULE_BYTES_VERIFIED_ONLY',replication='UNKNOWN',
                release_compatibility='NOT_EVALUATED',windows_qualification='NOT_RUN_EDITION_DRIFT' if drift else expected+'_NOT_RUN',
                approval_status='NOT_EVALUATED',effects_authorized=False))
        return dict(schema='unified.supervisor-rollout-plan.v1',mode='PLAN_ONLY',release_id=manifest['release_id'],
            manifest_sha256=self._pin,source_pins={key:{field:value[field] for field in ('commit','tree')} for key,value in manifest['sources'].items()},
            source_provenance=report['source_provenance'],inventory_origin='SUPPLIED_METADATA_NOT_NATIVE_PROOF',
            steps=steps,max_concurrent_nodes=1,previous_release=previous,
            rollback_readiness='REFERENCE_ONLY_NOT_VERIFIED' if previous else 'UNAVAILABLE',rollback_authorized=False,
            installed_release='NOT_OBSERVED',effects_authorized=False,development_task_conversion=False,
            physical_acceptance='NOT_RUN',trading_authorized=False)
    def prepare_install(self,observed_node,*,install_root,state_root,installation_id,operation_id):
        selected=node(observed_node)
        # Existing source_plan verifies byte closure again and returns a
        # non-activating plan. It performs no stage/create/register operation.
        transaction=source_plan(capsule_root=self._capsule,install_root=install_root,state_root=state_root,
            installation_id=installation_id,node_id=selected['node_id'],operation_id=operation_id,
            role='CONTROL' if selected['role']=='COORDINATOR' else 'WORKER',manifest_sha256=self._pin)
        return dict(schema='unified.supervisor-install-preparation.v1',mode='PLAN_ONLY',node=selected,
            transaction_plan=transaction,effects_authorized=False,physical_acceptance='NOT_RUN',
            authority_freshness='UNKNOWN',installation_root_acl='NOT_EVALUATED')
    def service_prototype(self,service_plan,expected_plan_sha256):
        """Bind an existing stopped-service PLAN without register/start/stop.

        Native service identity/source qualification is not inferred from the
        supplied plan or its external digest. Existing service validation and
        capsule closure checks are reused, not reimplemented.
        """
        need(type(service_plan) is dict and type(expected_plan_sha256) is str and SHA.fullmatch(expected_plan_sha256) is not None)
        need(service_plan.get('plan_sha256')==expected_plan_sha256)
        try:checked=check_service_plan(copy.deepcopy(service_plan))
        except (ValueError,OSError,TypeError,KeyError):raise DeploymentBlocked('SUPERVISOR_DEPLOYMENT_NOT_ADMITTED') from None
        need(Path(checked['capsule_root'])==self._capsule and checked['manifest_sha256']==self._pin)
        need(checked['node_id'] in ORDER)
        need(checked['role']==('CONTROL' if checked['node_id'] in COORDINATORS else 'WORKER'))
        return dict(schema='unified.supervisor-service-prototype.v1',mode='PLAN_ONLY',service_plan=checked,
            service_state='NOT_OBSERVED',service_identity='NOT_NATIVE_QUALIFIED',user_logoff_independence='NOT_RUN',
            startup_qualification='NOT_RUN',effects_authorized=False,physical_acceptance='NOT_RUN')
    def execute(self,plan):
        raise DeploymentBlocked('SUPERVISOR_DEPLOYMENT_NOT_ADMITTED')
