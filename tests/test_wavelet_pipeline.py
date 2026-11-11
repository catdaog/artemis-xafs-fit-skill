"""Integration of real Morlet calculations with synthetic pipeline exports.

Only the external fit engine is replaced; none of this is experimental fit evidence.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import fit_pipeline as pipeline


class WaveletPipelineTests(unittest.TestCase):
    def config(self):
        return {'standard': {'id': 'foil', 'kmin': 2, 'kmax': 10},
                'samples': [{'id': 'sample', 'kmin': 3, 'kmax': 12}],
                'wavelet': {'kstep': .1, 'rmax': 4, 'rstep': .1}}

    def test_common_fit_window_and_disabled_branch(self):
        cfg = self.config()
        options = pipeline.prepare_wavelet(cfg)
        self.assertEqual((options['kmin'], options['kmax']), (3, 10))
        for value in (None, False, {'enabled': False}):
            cfg['wavelet'] = value
            self.assertIsNone(pipeline.prepare_wavelet(cfg))
        cfg['wavelet'] = True
        self.assertEqual(pipeline.prepare_wavelet(cfg)['kappa'], 10)

    def test_invalid_diagnostic_stops_before_external_fit(self):
        for options in ({'kappa': -1}, {'kmin': 1}, {'kmax': 11},
                        {'spectra': []}, {'enabled': 'yes'}):
            cfg = self.config()
            cfg['wavelet'] = options
            with tempfile.TemporaryDirectory() as temp, patch.object(pipeline, 'fit_one') as fit:
                with self.assertRaises((ValueError, TypeError)):
                    pipeline.execute(cfg, Path(temp)/'output')
                fit.assert_not_called()

    def test_actual_transform_of_synthetic_fit_exports(self):
        cfg = self.config()

        def synthetic_fit(item, folder, mode, s02=None, root=None):
            folder.mkdir(parents=True)
            k = np.arange(0, 14.001, .05)
            model = np.exp(-.015*k*k)*np.sin(2*2.2*k)
            data = model + .1*np.sin(2*3.2*k)
            np.savetxt(folder/'chi_k.dat', np.column_stack([k, data]))
            np.savetxt(folder/'fit_k1.dat', np.column_stack([k, k*data, k*model, k*(data-model)]))
            return {'s02': .85, 's02_error': .02}

        with tempfile.TemporaryDirectory() as temp, patch.object(pipeline, 'fit_one', side_effect=synthetic_fit):
            out = Path(temp)/'output'
            result = pipeline.execute(copy.deepcopy(cfg), out)
            self.assertEqual(result['status'], 'review_required')
            self.assertEqual(len(result['samples']), 1)
            for name in ('foil_data', 'foil_fit', 'foil_residual', 'sample_data', 'sample_fit', 'sample_residual'):
                matrix = np.loadtxt(out/'wavelet'/name/'WT_matrix.txt')
                self.assertEqual(matrix.shape, (41, 71))
                self.assertTrue(np.isfinite(matrix).all())
            import exafs_wavelet
            exafs_wavelet.verify_output(out/'wavelet')
            saved = json.loads((out/'pipeline_result.json').read_text())
            self.assertEqual(saved['wavelet']['directory'], str(out/'wavelet'))


if __name__ == '__main__':
    unittest.main()
