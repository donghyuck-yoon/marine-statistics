import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('portal_import', ROOT / 'import_portal_daily.py')
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)

class ImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = Path(self.tmp.name)
        for sub in ('data/marine', 'data/coastal', 'uploads'):
            (self.p / sub).mkdir(parents=True, exist_ok=True)
        self.base = {('22101', '2026-10-19'): ['22101', '2026-10-19', '21.7'],
                     ('22101', '2026-10-20'): ['22101', '2026-10-20', '21.8']}
        (self.p / 'data/marine/2026.csv').write_bytes(importer.csv_bytes(self.base, importer.M))
        (self.p / 'data/coastal/2026.csv').write_bytes(importer.csv_bytes({('22441','2026-10-19'): ['22441','2026-10-19','22','22.1','21.9','.9','.5','1','1.5','4.5','5.2']}, importer.C))
        manifest={'format_version':1,'summary':{'marine':{},'coastal':{}}, 'datasets':[{'source':'marine','year':2026,'path':'data/marine/2026.csv'}, {'source':'coastal','year':2026,'path':'data/coastal/2026.csv'}]}
        (self.p / 'data/manifest.json').write_text(json.dumps(manifest))
        (self.p / 'uploads/README.md').write_text('INBOX')

    def incoming(self, text, name='OBS_BUOY_DD_20261021.csv', encoding='cp949'):
        (self.p / 'uploads' / name).write_bytes(text.encode(encoding))

    def test_new_row_and_correction_keep_other_days(self):
        self.incoming('지점,일시,평균 수온(°C)\n22101,2026-10-20,22.1\n22101,2026-10-21,22.0\n')
        result = importer.merge(self.p, self.p / 'uploads', apply=True)
        self.assertEqual((result['added'],result['corrected']), (1,1))
        rows = importer.read_csv(self.p/'data/marine/2026.csv', importer.M)
        self.assertEqual(rows[('22101','2026-10-19')][2], '21.7')
        self.assertEqual(rows[('22101','2026-10-20')][2], '22.1')
        self.assertEqual(rows[('22101','2026-10-21')][2], '22.0')
        self.assertEqual(list((self.p/'uploads').glob('*.csv')), [])
        mf=json.loads((self.p/'data/manifest.json').read_text())
        self.assertEqual(mf['summary']['marine']['records'], 3)
        self.assertEqual(mf['summary']['coastal']['records'], 1)
        self.assertEqual(mf['summary']['marine']['last_observation'], '2026-10-21')

    def test_reject_invalid_file_without_modifying_existing_data(self):
        old=(self.p/'data/marine/2026.csv').read_bytes()
        self.incoming('지점,일시,틀린열\n22101,2026-10-21,20\n')
        with self.assertRaises(ValueError): importer.merge(self.p, self.p/'uploads',apply=True)
        self.assertEqual((self.p/'data/marine/2026.csv').read_bytes(), old)
        self.assertTrue(list((self.p/'uploads').glob('*.csv')))

    def test_read_original_portal_cp949_and_keep_outliers(self):
        cols=','.join(importer.C)
        values='22441,2025-05-24,15.7,15.8,15.5,,3.6,90,90,,5.6'
        self.incoming(cols+'\n'+values+'\n','OBS_CWBUOY_DD_20261021.csv')
        result=importer.merge(self.p,self.p/'uploads',apply=True)
        self.assertEqual(result['added'],1)
        self.assertEqual(importer.read_csv(self.p/'data/coastal/2025.csv', importer.C)[('22441','2025-05-24')][7], '90')

if __name__ == '__main__': unittest.main()