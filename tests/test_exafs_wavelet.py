"""Numerical and file-contract checks for the EXAFS Morlet postprocessor."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import exafs_wavelet as wt


class WaveletTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.k = np.arange(0, 12.00001, .05)
        self.chi = np.sin(2 * self.k * 2.0) * np.exp(-((self.k - 6) / 3) ** 2)
        self.write("data.dat", self.k, self.chi)
        self.config = dict(kmin=1, kmax=11, kstep=.1, rmin=0, rmax=4, rstep=.1,
            spectra=[dict(id="data", file="data.dat")])

    def write(self, name, k, chi):
        np.savetxt(self.root / name, np.column_stack([k, chi]), fmt="%.17g")

    def run_config(self, config=None, name="out"):
        return wt.run(config or self.config, self.root / name, self.root)

    def test_direct_independent_trapezoid_complex_agreement(self):
        k = np.arange(1, 8.00001, .05)
        signal = np.sin(4.2 * k) * (1 + .1 * k)
        distances = np.array([0., 1.3, 2.1, 3.2])
        actual = wt.morlet_transform(k, signal, distances)
        expected = np.zeros_like(actual)
        for row, distance in enumerate(distances):
            if distance == 0:
                continue
            a = 10 / (2 * distance)
            for col, center in enumerate(k):
                u = (k - center) / a
                # Independent integral uses the defining conjugated mother,
                # rather than reusing the implementation's convolution kernel.
                mother = (np.exp(10j * u) - np.exp(-50)) * np.exp(-u*u/2) / np.sqrt(2*np.pi)
                expected[row, col] = np.trapezoid(signal * np.conj(mother), k) / np.sqrt(a)
        np.testing.assert_allclose(actual, expected, rtol=2e-13, atol=2e-13)
        self.assertGreater(abs(actual[2, 60].imag), .01)

    def test_sine_ridge_allows_predicted_l2_normalization_bias(self):
        k = np.arange(0, 80.0001, .05)
        r = np.arange(1.7, 2.30001, .005)
        value = wt.morlet_transform(k, np.sin(4*k), r)
        peak = r[np.argmax(np.abs(value[:, len(k)//2]))]
        predicted = 2 * (20 / (10 + np.sqrt(102)))
        self.assertAlmostEqual(peak, predicted, delta=.006)

    def test_localized_envelope(self):
        k = np.arange(0, 40.0001, .05)
        signal = np.exp(-.5*((k-17)/1.0)**2)*np.sin(6*k)
        value = wt.morlet_transform(k, signal, np.array([3.0]))
        peak = k[np.argmax(np.abs(value[0]))]
        self.assertAlmostEqual(peak, 17.0, delta=.1)
        self.assertLess(abs(value[0, 0]), np.max(np.abs(value[0])) * 1e-6)
        self.assertLess(abs(value[0, -1]), np.max(np.abs(value[0])) * 1e-6)

    def test_batch_shared_scale_orientation_and_complex_residual(self):
        self.write("fit.dat", self.k, .7*self.chi)
        cfg = copy.deepcopy(self.config)
        cfg["spectra"].append(dict(id="fit", file="fit.dat", role="fit"))
        cfg["residuals"] = [dict(id="residual", data="data", fit="fit")]
        report = self.run_config(cfg)
        self.assertEqual(report["coordinates"]["shape_R_by_k"], [41, 101])
        self.assertEqual(wt.verify_output(self.root/"out")["status"], "pass")
        raw = np.loadtxt(self.root/"out/data/WT_matrix.txt", delimiter="\t")
        normalized = np.loadtxt(self.root/"out/fit/WT_normalized.txt", delimiter="\t")
        self.assertEqual(raw.shape, (41, 101))
        self.assertTrue(np.all(raw[0] == 0))
        self.assertAlmostEqual(float(normalized.max()), .7, places=12)
        with np.load(self.root/"out/data/WT_coefficients.npz") as data, np.load(self.root/"out/fit/WT_coefficients.npz") as fit, np.load(self.root/"out/residual/WT_coefficients.npz") as residual:
            np.testing.assert_allclose(residual["coefficients"], data["coefficients"]-fit["coefficients"], atol=2e-13)
            self.assertEqual(data["coi_valid"].shape, raw.shape)
            np.testing.assert_array_equal(data["k_Ainv"], report["coordinates"]["k_Ainv"])
        instructions = (self.root/"out/ORIGIN_IMPORT.txt").read_text()
        self.assertIn("Columns map to X = k", instructions)
        self.assertIn("rows map to Y = apparent R", instructions)

    def test_undo_declared_input_weight_before_applying_output_weight(self):
        self.write("weighted.dat", self.k, self.chi*self.k**2)
        cfg = copy.deepcopy(self.config)
        cfg["spectra"].append(dict(id="weighted", file="weighted.dat", input_kweight=2))
        report = self.run_config(cfg)
        with np.load(self.root/"out/data/WT_coefficients.npz") as data, np.load(self.root/"out/weighted/WT_coefficients.npz") as weighted:
            np.testing.assert_allclose(data["coefficients"], weighted["coefficients"], atol=1e-13)
        self.assertTrue(report["inputs"][1]["excluded_weighted_k_zero"])
        cfg["kmin"] = 0
        with self.assertRaisesRegex(ValueError, "weighted-k0"):
            self.run_config(cfg, "badzero")

    def test_malformed_nonfinite_duplicate_and_gap_input_rejected(self):
        cases = [
            "k chi\n0 1\n1 bad\n2 3\n",
            "k chi\n0 1\n1 nan\n2 3\n",
            "0 1\n1 2\n1 3\n",
            "0 1\n1 2\n2 3\n4 5\n",
            "0,1\n1,,2\n2,3\n",
            "0\t1\n1\t\t2\n2\t3\n",
            "0 1\ntext header\n2 3\n",
            "2 1\n1 2\n0 3\n",
        ]
        for i, content in enumerate(cases):
            path = self.root/f"bad{i}.dat"
            path.write_text(content)
            with self.subTest(content=content), self.assertRaises(ValueError):
                wt.read_chi(path)

    def test_headers_delimiters_and_one_based_columns(self):
        for delimiter in [",", "\t", " "]:
            path = self.root/"columns.dat"
            path.write_text("measurement\nk,energy,chi\n" + "\n".join(delimiter.join(map(str,row)) for row in [(0,100,.1),(1,101,.2),(2,102,.3)]))
            k, y = wt.read_chi(path, 1, 3)
            np.testing.assert_array_equal(k, [0,1,2])
            np.testing.assert_allclose(y, [.1,.2,.3])
        with self.assertRaises(ValueError):
            wt.read_chi(path, 0, 3)

    def test_no_overwrite_extrapolation_and_memory_guard(self):
        self.run_config()
        sentinel = (self.root/"out/WT_parameters.json").read_bytes()
        with self.assertRaises(FileExistsError):
            self.run_config()
        self.assertEqual(sentinel, (self.root/"out/WT_parameters.json").read_bytes())
        for key, value in [("kmax", 12.1), ("memory_mb", .001), ("rmax", 100)]:
            cfg = copy.deepcopy(self.config)
            cfg[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.run_config(cfg, key)
            self.assertFalse((self.root/key).exists())

    def test_hanning_formula_and_none(self):
        k = np.array([0., .25, .5, .75, 1.])
        expected = .5*(1-np.cos(np.pi*k)) * .5*(1-np.cos(np.pi*(1-k)))
        np.testing.assert_allclose(wt.hanning_window(k,1), expected)
        cfg = copy.deepcopy(self.config)
        cfg["window"] = "none"
        report = self.run_config(cfg)
        self.assertTrue(all(v == 1 for v in report["preprocessing"]["window_values"]))

    def test_verifier_detects_tampering(self):
        self.run_config()
        path = self.root/"out/data/WT_matrix.txt"
        path.write_text("0\n")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            wt.verify_output(self.root/"out")

    def test_unknown_configuration_and_ignored_cli_override_rejected(self):
        cfg = copy.deepcopy(self.config)
        cfg["kapppa"] = 6
        with self.assertRaisesRegex(ValueError, "Unknown WT"):
            self.run_config(cfg)
        cfg = copy.deepcopy(self.config)
        cfg["spectra"][0]["input_k_weight"] = 2
        with self.assertRaisesRegex(ValueError, "Unknown spectrum"):
            self.run_config(cfg)
        cfg = copy.deepcopy(self.config)
        cfg["residuals"] = [dict(id="res", data="data", fit="data", data_column=2)]
        with self.assertRaisesRegex(ValueError, "Unknown residual"):
            self.run_config(cfg)
        config_file = self.root/"config.json"
        config_file.write_text(json.dumps(self.config))
        actual = subprocess.run([sys.executable, str(Path(wt.__file__)), "--config", str(config_file),
            "--out", str(self.root/"cli"), "--kappa", "6"], capture_output=True, text=True)
        self.assertNotEqual(actual.returncode, 0)
        self.assertIn("conflicting flags", actual.stderr)
        self.assertFalse((self.root/"cli").exists())

    def test_cli_single_batch_and_verify(self):
        script = Path(wt.__file__)
        command = [sys.executable, str(script), str(self.root/"data.dat"), "--out", str(self.root/"cli"),
                   "--kmin", "1", "--kmax", "11", "--kstep", ".1", "--rstep", ".1"]
        actual = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(actual.returncode, 0, actual.stderr)
        self.assertEqual(json.loads(actual.stdout)["status"], "pass")
        verified = subprocess.run([sys.executable,str(script),"verify",str(self.root/"cli")], capture_output=True,text=True)
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertEqual(json.loads(verified.stdout)["series_count"], 1)
        path = self.root/"config.json"
        path.write_text(json.dumps(self.config))
        batch = subprocess.run([sys.executable,str(script),"--config",str(path),"--out",str(self.root/"batch")],capture_output=True,text=True)
        self.assertEqual(batch.returncode, 0, batch.stderr)


if __name__ == "__main__":
    unittest.main()
