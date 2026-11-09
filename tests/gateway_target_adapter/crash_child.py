"""Owned disposable PROCESS fault only. Never an office/service fault injector."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,sys.argv[1])
from unified_system.gateway_target_adapter import DisposableTargetStand,prepare_target,template_request
stand=DisposableTargetStand(Path(sys.argv[2]),stratt_source_root=sys.argv[3],meta_source_root=sys.argv[4])
original=stand._invoke
def fault(check):
    if sys.argv[5]=='AFTER':original(check)
    os._exit(73)
stand._invoke=fault
stand.execute(prepare_target(json.dumps(template_request(),sort_keys=True,separators=(',',':')).encode()),context=stand.local_test_context())
