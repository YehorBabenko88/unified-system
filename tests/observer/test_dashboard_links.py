import unittest
from unified_system.observer.dashboard import render
from unified_system.observer.model import ObserverError

class DashboardLinkTests(unittest.TestCase):
    def test_only_closed_public_pr_and_run_links_are_derived(self):
        rows=[{'subject':'YehorBabenko88/unified-system#88','field':'PR_STATUS'},
              {'subject':'YehorBabenko88/unified-system#43099081596','field':'RUN_STATUS'}]
        page=render({'ci':rows}).decode()
        self.assertIn('href="https://github.com/YehorBabenko88/unified-system/pull/88"',page)
        self.assertIn('href="https://github.com/YehorBabenko88/unified-system/actions/runs/43099081596"',page)

    def test_untrusted_evidence_urls_private_addresses_and_schemes_not_linked(self):
        for subject in ('javascript:alert(1)#88','http://127.0.0.1#88',
                        'YehorBabenko88/unified-system#88\" onclick=\"x',
                        'foreign/private#88','YehorBabenko88/unified-system#-1'):
            row={'subject':subject,'field':'PR_STATUS','evidence':{'url':'https://192.168.1.2/private',
                 'source':'<script>unsafe</script>','sha256':'abc'}}
            page=render({'ci':[row]}).decode()
            self.assertNotIn('href="https://192.',page)
            self.assertNotIn('href="javascript:',page)
            self.assertNotIn('<script>unsafe',page)
            self.assertNotIn('href="https://github.com/',page)

    def test_immutable_observer_code_link_requires_explicit_validated_head(self):
        head='8d7c3c321b8b0bd7704a92721c9549b778d053f6'
        page=render({},source_head=head).decode()
        self.assertIn('/blob/'+head+'/unified_system/observer/dashboard.py',page)
        for value in ('https://127.0.0.1/x','javascript:evil',head+'\"'):
            with self.assertRaises(ObserverError):render({},source_head=value)

    def test_private_mission_evidence_does_not_get_fabricated_link(self):
        page=render({'development':[{'subject':'Master Mission','field':'MISSION_SEQUENCE',
            'value':277,'evidence':{'source':'real-mission-export','sha256':'a'*64}}]}).decode()
        self.assertIn('a'*64,page)
        self.assertNotIn('href="https://github.com/',page)
