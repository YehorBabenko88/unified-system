import tempfile
import unittest
from pathlib import Path
from unified_system.integration import synthetic_pipeline
from unified_system.contracts import ContractError

class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"journal.db"
    def test_runtime_failure_annotation_uses_only_fixed_public_enums(self):
        from integration.verify_terminan_runtime import failure_annotation
        self.assertEqual(failure_annotation({'failure_stage':'OWNED_STOP','error_class':'AssertionError'}),
                         '::error::TERMINAN_RUNTIME phase=OWNED_STOP exception=AssertionError reason=OTHER')
        report={'failure_stage':'private/path\n::error::secret','error_class':'token=value',
                'message':'https://private.invalid/credential'}
        self.assertEqual(failure_annotation(report),'::error::TERMINAN_RUNTIME phase=OTHER exception=OTHER reason=OTHER')
    def test_source_failure_reason_drops_private_suffix_and_rejects_forged_prefix(self):
        from integration.verify_terminan_runtime import failure_annotation,source_failure_reason
        from integration.source_guard import SourceQualificationError
        for message,expected in [('TRACKED_BYTES_MISMATCH:private/path?token=secret','TRACKED_BYTES_MISMATCH'),
                                 ('TRACKED_BYTES_MISMATCH_FORGED:private','OTHER'),
                                 ('private/path:TRACKED_BYTES_MISMATCH','OTHER')]:
            exc=SourceQualificationError(message)
            self.assertEqual(source_failure_reason(exc),expected)
            report={'failure_stage':'TERMINAN_SOURCE_PRECHECK','error_class':'SourceQualificationError',
                    'source_reason':source_failure_reason(exc)}
            self.assertEqual(failure_annotation(report),'::error::TERMINAN_RUNTIME phase=TERMINAN_SOURCE_PRECHECK exception=SourceQualificationError reason='+expected)
        self.assertEqual(source_failure_reason(ValueError('TRACKED_BYTES_MISMATCH:private')),'OTHER')
    def test_full_offline(self):
        result=synthetic_pipeline(self.path)
        self.assertEqual(result["lifecycle"]["state"],"OBSERVING")
        self.assertEqual(result["dashboard"]["overall"],"SYNTHETIC_READY")
        self.assertFalse(result["terminan_connected"])
    def test_missing_grid(self):
        result=synthetic_pipeline(self.path,modules=("strattester","terminan"))
        self.assertEqual(result["lifecycle"]["state"],"DEGRADED")
        self.assertEqual(result["dashboard"]["overall"],"DEGRADED")
    def test_restart_blocked(self):
        synthetic_pipeline(self.path)
        with self.assertRaises(ContractError):synthetic_pipeline(self.path)
if __name__=="__main__":unittest.main()
