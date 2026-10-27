import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fdmnes_runtime as runtime
import xanes_fit as xanes
import xanes_cluster
import cif_tools
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


class XanesTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'examples/xanes/fe-n4.json').read_text())

    def test_structure_parameter_moves_real_deck(self):
        m = self.config['models'][0]
        xyz = xanes.coordinates(m, {'fe_n_A': 2.08})
        self.assertAlmostEqual(np.linalg.norm(xyz[1] - xyz[0]), 2.08)
        deck = xanes.make_deck(self.config, m, {'fe_n_A': 2.08})
        self.assertIn('7 2.080000000', deck)
        self.assertIn('Absorber\n1', deck)
        self.assertNotIn('Energpho', deck)
        xanes.validate_config(self.config)

    def test_overlap_and_invalid_absorber_rejected(self):
        self.config['models'][0]['atoms'][1]['xyz'] = [0, 0, 0]
        with self.assertRaises(ValueError):
            xanes.validate_config(self.config)
        self.setUp()
        self.config['absorber'] = 'Pt'
        with self.assertRaises(ValueError):
            xanes.validate_config(self.config)

    def test_native_spectrum_does_not_read_metadata_as_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'spec.txt'
            p.write_text('7112 26 1 1 = E_edge, Z\n Energy <xanes>\n-2 0.1\n-1 0.2\n0 0.5\n1 1\n')
            a = runtime.read_spectrum(p)
            self.assertEqual(a.shape, (4, 2))
            self.assertEqual(a[0, 0], -2)
            p.write_text('7112 26 1 1 = E_edge, Z\n')
            with self.assertRaises(ValueError):
                runtime.read_spectrum(p)

    def test_alignment_sign_and_no_extrapolation(self):
        a = np.column_stack([np.arange(-20, 21), np.arange(-20, 21)**2])
        signal = xanes.aligned_spectrum(a, np.array([0., 1., 2.]), 1, 0)
        np.testing.assert_allclose(signal, [1, 0, 1])
        with self.assertRaises(ValueError):
            xanes.aligned_spectrum(a, [19.], 0, 1)

    def test_normalization_preserves_source_and_raw_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'raw.csv'
            energy = np.arange(7090, 7141)
            mu = .002 * (energy - 7112) + 2 + 3 * (energy >= 7112)
            np.savetxt(p, np.column_stack([energy, mu]), delimiter=',')
            digest = runtime.sha256(p)
            spec = {'path': 'raw.csv', 'edge_energy_eV': 7112, 'calibration_basis': 'test',
                    'normalization': 'linear_windows', 'pre_edge_window_eV': [7090, 7100],
                    'post_edge_window_eV': [7130, 7140]}
            result = xanes.prepare_experiment(spec, Path(tmp))
            np.testing.assert_allclose(result['mu'], energy >= 7112, atol=1e-10)
            self.assertEqual(runtime.sha256(p), digest)
            np.testing.assert_array_equal(result['raw'][:, 0], energy)

    def test_budget_failure_is_recorded_not_fabricated(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = copy.deepcopy(self.config)
            config['limits']['max_engine_runs'] = 0
            path = Path(tmp) / 'config.json'
            runtime.save_json(path, config)
            exe = Path(tmp) / 'fdmnes.exe'
            exe.write_bytes(b'not executed')
            with self.assertRaises(RuntimeError):
                xanes.execute(path, Path(tmp) / 'run', exe, 'simulate')
            record = json.loads((Path(tmp) / 'run/xanes_run.json').read_text())
            self.assertEqual(record['status'], 'failed')
            self.assertFalse(list((Path(tmp) / 'run').rglob('data_fit.csv')))

    def test_zero_exit_without_spectrum_is_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / 'engine.exe'
            exe.write_bytes(b'not executed')
            with patch.object(runtime.subprocess, 'run', return_value=type('Result', (), {'returncode': 0})()):
                with self.assertRaises(RuntimeError):
                    runtime.run_deck(exe, 'End\n', Path(tmp) / 'jobs')
            records = list((Path(tmp) / 'jobs').glob('*/execution.json'))
            self.assertEqual(json.loads(records[0].read_text())['status'], 'failed')

    def test_zip_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / 'unsafe.zip'
            with zipfile.ZipFile(archive, 'w') as zipped:
                zipped.writestr('../escape.exe', b'unsafe')
            with self.assertRaises(ValueError):
                runtime.install_runtime(Path(tmp) / 'runtime', archive=archive)
            self.assertFalse((Path(tmp) / 'escape.exe').exists())

    def test_cif_cluster_keeps_absorber_and_periodic_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'model.cif'
            spec = {'cell': [4, 4, 4, 90, 90, 90], 'sites': [
                {'id': '0', 'element': 'Fe', 'frac': [0, 0, 0]},
                {'id': '1', 'element': 'N', 'frac': [.5, 0, 0]}]}
            cif_tools.write_cif(cif_tools.construct(spec), p)
            cluster = xanes_cluster.extract(p, '0', 2.1, 'test', 'Illustrative test CIF')
            self.assertEqual(cluster['atoms'][0]['element'], 'Fe')
            self.assertEqual(len(cluster['atoms']), 3)
            self.assertEqual(cluster['source_cif_sha256'], runtime.sha256(p))
            translations = [a['source_translation'] for a in cluster['atoms'][1:]]
            self.assertIn([-1, 0, 0], translations)
            spec['sites'][1]['occupancy'] = .5
            q = Path(tmp) / 'partial.cif'
            cif_tools.write_cif(cif_tools.construct(spec), q)
            with self.assertRaises(ValueError):
                xanes_cluster.extract(q, '0', 2.1, 'test', 'Partial occupancy test')


if __name__ == '__main__':
    unittest.main()
