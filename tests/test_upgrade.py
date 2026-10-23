import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import cif_tools as cif
import fit_pipeline as pipeline
from check_project import structural_check, compare
import build_xafs_delivery as delivery

class UpgradeTests(unittest.TestCase):
    def test_empty_and_partial_logs_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fit.log'
            for text in ('','unrecognized content','Independent points : 10\nNumber of variables : 2'):
                p.write_text(text)
                r=subprocess.run([sys.executable,str(Path(cif.__file__).with_name('audit_fit_log.py')),str(p)],capture_output=True,text=True)
                self.assertEqual(r.returncode,3)
                self.assertEqual(json.loads(r.stdout)['status'],'incomplete')

    def test_fake_dpj_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fake.dpj';p.write_text('not a project')
            with self.assertRaises(ValueError): structural_check(p)

    def test_mismatched_export_rejected(self):
        with self.assertRaises(ValueError): compare([[1,2,3]],[[1,2,4]],'test')

    def test_cif_roundtrip_supercell_vacancy_and_feff(self):
        spec={'cell':[4,4,4,90,90,90],'sites':[{'id':'0','element':'Mo','frac':[0,0,0]},{'id':'1','element':'O','frac':[.5,.5,.5]}]}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'base.cif';cif.write_cif(cif.construct(spec),p)
            self.assertEqual(len(cif.inspect(p)['sites']),2)
            model=cif.construct({'supercell':[2,1,1],'remove':['1@1,0,0'],'substitute':{'0@0,0,0':'W'}},p)
            self.assertEqual(len(model['sites']),3)
            self.assertEqual(model['cell'][0],8)
            cif.write_cif(model,Path(d)/'defect.cif')
            cif.feff_input(p,'0',5,Path(d)/'feff.inp')
            self.assertIn('POTENTIALS',(Path(d)/'feff.inp').read_text())
            with self.assertRaises(ValueError): cif.construct({'remove':['missing']},p)

    def test_invalid_cells_and_overlap(self):
        for cell,sites in [([0,4,4,90,90,90],[{'id':'0','element':'Mo','frac':[0,0,0]}]),([4,4,4,90,90,90],[{'id':'0','element':'Mo','frac':[0,0,0]},{'id':'1','element':'O','frac':[0,0,0]}])]:
            with self.assertRaises(ValueError): cif.construct({'cell':cell,'sites':sites})

    def test_failed_standard_never_fits_sample(self):
        with tempfile.TemporaryDirectory() as d, patch.object(pipeline,'fit_one',return_value={'s02':-1,'s02_error':.02}) as mock:
            with self.assertRaises(ValueError): pipeline.execute({'standard':{},'samples':[{'id':'MoO3'}]},Path(d)/'run')
            self.assertEqual(mock.call_count,1)
            self.assertEqual(json.loads((Path(d)/'run/pipeline_result.json').read_text())['status'],'failed')

    def test_standard_s02_is_propagated(self):
        with tempfile.TemporaryDirectory() as d, patch.object(pipeline,'fit_one',side_effect=[{'s02':.83,'s02_error':.02},{'s02':.83}]) as mock:
            result=pipeline.execute({'standard':{},'samples':[{'id':'MoO2'}]},Path(d)/'run')
            self.assertEqual(mock.call_args_list[1].args[3],.83)
            self.assertEqual(result['status'],'review_required')

if __name__=='__main__': unittest.main()
