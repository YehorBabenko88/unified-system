"""Research identity source boundaries; no synthetic job/grant fixtures."""
import importlib
import unittest

class BrokerBoundaryTests(unittest.TestCase):
    def test_missing_or_method_shaped_authority_never_authenticates(self):
        m=importlib.import_module('unified_system.gateway_research_identity')
        for source in (None,True,{},object()):
            with self.subTest(source=type(source)):
                with self.assertRaises(m.ResearchIdentityUnavailable):
                    m.ResearchIdentityBroker(authority=source,generation='00000000-0000-4000-8000-000000000001',
                        realm_id='00000000-0000-4000-8000-000000000002',profile_sha256='a'*64,
                        server_ssl_context=None,server_certificate_der=b'',audit_sink=None)
    def test_context_and_capture_have_no_public_constructor(self):
        m=importlib.import_module('unified_system.gateway_research_identity')
        for cls in (m.ResearchPrincipalContext,m.ResearchIdentityCapture):
            with self.assertRaises(TypeError): cls()
    def test_native_session_syntax_is_distinct_and_never_a_permission(self):
        m=importlib.import_module('unified_system.gateway_research_identity')
        actual_format='01234567-89ab-1cde-0fab-0123456789ab'
        self.assertIsNone(m._native_session(actual_format))
        with self.assertRaises(m.ResearchIdentityDenied): m._uuid(actual_format)
        for invalid in (None,True,'not-a-session',actual_format.upper(),actual_format+'\n',actual_format+'x',actual_format.replace('-','')):
            with self.subTest(invalid=type(invalid)):
                with self.assertRaises(m.ResearchIdentityDenied): m._native_session(invalid)

if __name__=='__main__': unittest.main()
