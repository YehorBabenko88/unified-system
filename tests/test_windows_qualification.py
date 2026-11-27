"""Edition/role/claim boundaries; no Windows runtime qualification by fixture."""
import copy
import json
from pathlib import Path
import unittest
from unified_system.windows_qualification import review_matrix, QualificationError


class WindowsQualificationTests(unittest.TestCase):
    def matrix(self):
        return json.loads((Path(__file__).resolve().parents[1]/'release/windows-edition-qualification.json').read_bytes())

    def test_valid_pending_matrix_never_admits_installation(self):
        result=review_matrix(self.matrix())
        self.assertEqual(result['home_nodes'],['LS7','PC1'])
        self.assertEqual(result['pending_home_checks'],28)
        self.assertFalse(result['runtime_qualified'])
        self.assertFalse(result['physical_deployment_authorized'])

    def test_home_cannot_be_assigned_coordinator(self):
        v=self.matrix();v['tracks']['WINDOWS_HOME_QUALIFICATION']['nodes']['PC1']['role']='COORDINATOR'
        with self.assertRaises(QualificationError):review_matrix(v)

    def test_pro_receipt_or_status_cannot_be_adopted_for_home(self):
        for mutation in ['edition','pass']:
            v=self.matrix();n=v['tracks']['WINDOWS_HOME_QUALIFICATION']['nodes']['LS7']
            if mutation=='edition':n['edition']='Windows 11 Pro'
            else:n['checks'][0].update(status='PASS',evidence=[{'node':'LS5','edition':'Windows 11 Pro'}])
            with self.assertRaises(QualificationError):review_matrix(v)

    def test_all_fourteen_unique_checks_required_independently(self):
        for node in ['PC1','LS7']:
            v=self.matrix();v['tracks']['WINDOWS_HOME_QUALIFICATION']['nodes'][node]['checks'].pop()
            with self.assertRaises(QualificationError):review_matrix(v)
        v=self.matrix();c=v['tracks']['WINDOWS_HOME_QUALIFICATION']['nodes']['PC1']['checks'];c[-1]=copy.deepcopy(c[0])
        with self.assertRaises(QualificationError):review_matrix(v)

    def test_unqualified_physical_admission_cannot_be_enabled(self):
        v=self.matrix();v['tracks']['WINDOWS_HOME_QUALIFICATION']['nodes']['PC1']['physical_deployment']='AUTHORIZED'
        with self.assertRaises(QualificationError):review_matrix(v)

    def test_missing_node_or_unknown_track_rejected(self):
        v=self.matrix();v['tracks']['WINDOWS_HOME_QUALIFICATION']['nodes'].pop('LS7')
        with self.assertRaises(QualificationError):review_matrix(v)
        v=self.matrix();v['tracks']['WINDOWS_SERVER_QUALIFICATION']={}
        with self.assertRaises(QualificationError):review_matrix(v)


if __name__=='__main__':unittest.main()
