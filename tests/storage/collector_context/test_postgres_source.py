"""Static effect guards only: these tests never parse/execute SQL in a DB."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[3]


class PostgresSourceBoundary(unittest.TestCase):
    def test_migration_has_no_host_or_existing_database_effects(self):
        sql = (ROOT/'sql/collector/001_collector_metadata_v1.sql').read_text()
        code = re.sub(r'--[^\n]*', '', sql).upper()
        self.assertTrue(code.strip().startswith('BEGIN;'))
        self.assertTrue(code.strip().endswith('COMMIT;'))
        self.assertNotRegex(code, r'\b(DROP|DELETE|TRUNCATE|ALTER|GRANT|REVOKE|COPY|DO|CALL)\b')
        self.assertNotRegex(code, r'\bCREATE\s+(DATABASE|ROLE|USER|EXTENSION|FUNCTION|TRIGGER)\b')
        self.assertNotIn('IF NOT EXISTS', code)
        self.assertNotIn('CASCADE', code)
        self.assertNotIn('BYTEA', code)
        tables = re.findall(r'CREATE TABLE\s+([\w.]+)', code)
        self.assertEqual(len(tables), 5)
        self.assertTrue(all(t.startswith('COLLECTOR_METADATA_V1.') for t in tables))

    def test_readback_is_bounded_read_only_and_binding_scoped(self):
        sql = (ROOT/'sql/collector/readback_v1.sql').read_text()
        code = re.sub(r'--[^\n]*', '', sql).upper()
        self.assertTrue(code.strip().startswith('BEGIN READ ONLY;'))
        self.assertNotRegex(code, r'\b(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|COPY|CALL)\b')
        self.assertEqual(code.count('BINDING_SHA256 = $2'), 3)
        self.assertIn('LIMIT 17;', code)
        self.assertIn('LIMIT 129;', code)


if __name__ == '__main__': unittest.main(verbosity=2)
