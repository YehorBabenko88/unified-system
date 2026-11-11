import sys,pathlib,json,copy
sys.path[:0]=[str(pathlib.Path.cwd()),str(pathlib.Path.cwd()/'tests')]
from test_gateway_identity import GatewayIdentityTests,U
case=GatewayIdentityTests();case.setUp()
try:
 m=case.m;_,cap=case.permit();args=dict(tool_name='unified.get_dataset_manifest',request_bytes=case.request,binding=case.binding,owned_store=case.store);fixed=m.DisposableIdentityAuthority.require_issued_read;denied=0
 class Fake:
  def require_issued_read(self,*a,**k):raise AssertionError('FAKE_CALLED')
 for issuer in [None,True,{},Fake()]:
  try:fixed(issuer,cap,**args);raise AssertionError('BAD_ISSUER')
  except m.GatewayIdentityDenied:denied+=1
 forged=object.__new__(m.GatewayReadCapability);forged._issuer=case.auth
 for badcap in [forged,None,True,{}]:
  try:fixed(case.auth,badcap,**args);raise AssertionError('FORGED_CAP')
  except m.GatewayIdentityDenied:denied+=1
 for changed in [dict(args,request_bytes=case.request+b' '),dict(args,tool_name='unified.query_market_data'),dict(args,owned_store=object()),dict(args,binding=dict(case.binding,dataset_revision='2')),dict(args,binding=dict(case.binding,view_id='22222222-2222-4222-8222-222222222222'))]:
  try:fixed(case.auth,cap,**changed);raise AssertionError('READ_SCOPE_ALIAS')
  except m.GatewayIdentityDenied:denied+=1
 assert case.auth._caps[cap][5]==0
 assert fixed(case.auth,cap,**args) is None and fixed(case.auth,cap,**args) is None
 try:fixed(case.auth,cap,**args);raise AssertionError('THIRD_MANIFEST_CHECK')
 except m.GatewayIdentityDenied:denied+=1
 events=case.audit.drain();assert all('request_bytes' not in e and 'certificate' not in e for e in events)
 # Separate real TLS-issued context/cap, exact query budget7 then eighth refuse.
 prof=dict(case.profile,clients=[dict(case.profile['clients'][0],grants=[dict(tool_name='unified.query_market_data',binding=case.binding,owned_store=case.store)])]);sink=m.GatewayAuditSink(max_events=100);auth=m.DisposableIdentityAuthority(server_ssl_context=case.tls.server_context,profile=prof,audit_sink=sink);context=auth.authenticate_connection(case.tls.accepted);qargs=dict(args,tool_name='unified.query_market_data');qcap=auth.authorize_read(context,**qargs)
 for _ in range(7):assert fixed(auth,qcap,**qargs) is None
 try:fixed(auth,qcap,**qargs);raise AssertionError('EIGHTH_QUERY_CHECK')
 except m.GatewayIdentityDenied:denied+=1
 # Real issuance fills bounded audit; failed check cannot consume success count; revocation latches despite full sink.
 sink2=m.GatewayAuditSink(max_events=2);auth2=m.DisposableIdentityAuthority(server_ssl_context=case.tls.server_context,profile=case.profile,audit_sink=sink2);context2=auth2.authenticate_connection(case.tls.accepted);cap2=auth2.authorize_read(context2,**args)
 try:fixed(auth2,cap2,**args);raise AssertionError('AUDIT_FULL_BYPASS')
 except m.GatewayIdentityUnavailable:pass
 assert auth2._caps[cap2][5]==0
 try:auth2.revoke_service(U);raise AssertionError('AUDITFULL_REVOKE_NOT_REPORTED')
 except m.GatewayIdentityUnavailable:pass
 sink2.drain()
 try:fixed(auth2,cap2,**args);raise AssertionError('REVOKE_LOST')
 except m.GatewayIdentityDenied:denied+=1
 print(json.dumps(dict(scope='DISPOSABLE_REAL_MTLS_LOCAL_READ_CAPABILITY_ONLY',extra_negative_issuer_cap_request_scope_budget_revocation_refusals=denied,invalid_calls_consume_successful_checks=0,manifest_successful_check_budget=2,query_successful_check_budget=7,audit_full_blocks_before_count_increment=True,revocation_latches_despite_full_audit=True,audit_no_raw_request_or_certificate=True,cross_owner_ObjectStore_reads='NOT_RUN',Windows_native_human=False,Gateway_40row_matrix='UNCHANGED'),indent=2))
finally:case.doCleanups()
