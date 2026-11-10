"""Pure mandatory-ID validation; never execute LAN or native fixtures."""
import copy
import hashlib
import json
import re
from pathlib import Path
import unittest


PRIOR50_SHA256 = '63ee17edad67dbabd4d1a36681eb2485b52696ad44e097428f878d234b57021c'
PR77_SHA256 = 'ffe6ce63be80e7dae82fc6a969dc2556feee97140a19e9fd961a0cc5f2fe40c3'
CURRENT_SHA256 = '42065166ac47ba96dfce42821eb1b1f13fda03fce6e28614ca92fa83e838f18a'


def validate_inventory(document, actual_ids):
    """Exact v1 inventory, with independently pinned historical preservation."""
    def need(value):
        if not value:
            raise ValueError('LAN_MUX_TEST_INVENTORY_REJECTED')

    def ids(value):
        need(type(value) is list and 0 < len(value) <= 256)
        need(all(type(x) is str and len(x) <= 240 and re.fullmatch(r'test_[a-z_]+\.[A-Za-z_][A-Za-z_0-9]*\.test_[a-z_0-9]+', x) for x in value))
        need(len(value) == len(set(value)))
        return sorted(value)

    def digest(value):
        return hashlib.sha256(('\n'.join(value) + '\n').encode('ascii')).hexdigest()

    fields = {'schema','version','scope','modules','required_count','prior50_source','pr77_source','assembly_source',
              'prior50_ids_sha256','pr77_ids_sha256','prior50_test_ids','pr77_added_test_ids','assembly_added_test_ids','test_ids'}
    need(type(document) is dict and set(document) == fields)
    need(document['schema'] == 'unified.lan-mux-test-inventory.v1' and type(document['version']) is int and document['version'] == 1)
    need(document['scope'] == 'ISOLATED_LOOPBACK_COMPONENT_ONLY')
    modules = ['test_lan_transport','test_network_budget','test_lan_mux_channel']
    need(document['modules'] == modules)
    prior = ids(document['prior50_test_ids'])
    pr77_added = ids(document['pr77_added_test_ids'])
    added = ids(document['assembly_added_test_ids'])
    expected = ids(document['test_ids'])
    need(document['prior50_test_ids'] == prior and document['test_ids'] == expected)
    need(digest(prior) == document['prior50_ids_sha256'] == PRIOR50_SHA256)
    need(not set(prior) & set(pr77_added) and not (set(prior) | set(pr77_added)) & set(added))
    need(digest(sorted(prior + pr77_added)) == document['pr77_ids_sha256'] == PR77_SHA256)
    need(sorted(prior + pr77_added + added) == expected)
    need(digest(expected) == CURRENT_SHA256)
    need(type(document['required_count']) is int and document['required_count'] == len(expected))
    for field, head in [('prior50_source','9680babc85ca605f8450936f5410728898d5b71e'),
                        ('pr77_source','dd4ef015d9ed20065ccdc2c563e80046015d9193'),
                        ('assembly_source','b48ddc5ff083deeecfdf76185117d0e86aa23e2a')]:
        source = document[field]
        need(type(source) is dict and set(source) == {'head','sources'} and source['head'] == head)
        need(type(source['sources']) is dict and set(source['sources']) == {'tests/' + m + '.py' for m in modules})
        need(all(type(x) is str and re.fullmatch('[0-9a-f]{64}',x) for x in source['sources'].values()))
    need(ids(actual_ids) == expected)
    return expected


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads((Path(__file__).resolve().parents[1] / 'release/lan-mux-test-inventory.json').read_text(encoding='utf-8'))
        self.ids = list(self.document['test_ids'])

    def test_exact_inventory_preserves_all_prior_ids(self):
        self.assertEqual(validate_inventory(self.document, self.ids), self.ids)
        self.assertTrue(set(self.document['prior50_test_ids']) <= set(self.ids))

    def test_missing_case_rejected(self):
        with self.assertRaises(ValueError):
            validate_inventory(self.document, self.ids[1:])

    def test_duplicate_case_rejected(self):
        with self.assertRaises(ValueError):
            validate_inventory(self.document, self.ids + self.ids[:1])

    def test_extra_case_rejected(self):
        with self.assertRaises(ValueError):
            validate_inventory(self.document, self.ids + ['test_lan_transport.Foreign.test_extra'])

    def test_prior_case_removal_cannot_be_resealed_by_count_change(self):
        old = self.document['prior50_test_ids'][0]
        self.document['prior50_test_ids'].remove(old)
        self.document['test_ids'].remove(old)
        self.document['required_count'] -= 1
        with self.assertRaises(ValueError):
            validate_inventory(self.document, self.document['test_ids'])

    def test_pr77_case_removal_cannot_mask_old_count_fifty(self):
        self.document['test_ids'] = self.document['prior50_test_ids'][:]
        self.document['pr77_added_test_ids'] = []
        self.document['assembly_added_test_ids'] = []
        self.document['required_count'] = 50
        with self.assertRaises(ValueError):
            validate_inventory(self.document, self.document['test_ids'])

    def test_assembly_case_removal_cannot_be_resealed(self):
        case = self.document['assembly_added_test_ids'].pop()
        self.document['test_ids'].remove(case)
        self.document['required_count'] -= 1
        with self.assertRaises(ValueError):
            validate_inventory(self.document, self.document['test_ids'])

    def test_manifest_duplicate_and_wrong_count_rejected(self):
        for change in ('duplicate', 'count'):
            d = copy.deepcopy(self.document)
            if change == 'duplicate':
                d['test_ids'].append(d['test_ids'][0])
            else:
                d['required_count'] = True
            with self.assertRaises(ValueError):
                validate_inventory(d, self.ids)

    def test_closed_schema_and_foreign_origin_rejected(self):
        for key, value in (('private', 'unexpected'), ('schema', 'foreign'), ('version', True)):
            d = dict(self.document)
            d[key] = value
            with self.assertRaises(ValueError):
                validate_inventory(d, self.ids)


if __name__ == '__main__':
    unittest.main()
