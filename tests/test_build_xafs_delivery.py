from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_xafs_delivery.py"


class DeliveryBuilderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.raw = self.base / "raw_scan.dat"
        self.raw.write_text("# energy mu\n10000 0.1\n10001 0.2\n10002 0.4\n", encoding="utf-8")

        self.chi = self.base / "chi_k.dat"
        with self.chi.open("w", encoding="utf-8") as handle:
            handle.write("# k chi kchi k2chi k3chi window\n")
            for i in range(1, 11):
                k = float(i)
                chi = 0.01 * i
                handle.write(f"{k} {chi} {k*chi} {k*k*chi} {k*k*k*chi} 1\n")

        self.fit_files: dict[str, Path] = {}
        for label, factor in {"k1": 1.0, "k2": 2.0, "k3": 3.0}.items():
            path = self.base / f"fit_{label}.dat"
            with path.open("w", encoding="utf-8") as handle:
                handle.write("# coordinate data fit residual window\n")
                for i in range(1, 11):
                    data = factor * i / 10
                    fit = data * 0.9
                    handle.write(f"{i} {data} {fit} {data-fit} 1\n")
            self.fit_files[label] = path
        for label, factor in {"rmag": 1.0, "rre": 0.6, "rim": 0.8}.items():
            path = self.base / f"fit_{label}.dat"
            with path.open("w", encoding="utf-8") as handle:
                handle.write("# coordinate data fit residual window\n")
                for i in range(1, 11):
                    coordinate = i / 10
                    data = factor * i / 10
                    fit = data * 0.9
                    residual = abs(data - fit) * 1.7 if label == "rmag" else data - fit
                    handle.write(f"{coordinate} {data} {fit} {residual} 1\n")
            self.fit_files[label] = path
        for weight in (1, 2, 3):
            for component, factor in {"mag": 1.0, "re": 0.6, "im": 0.8}.items():
                label = f"r{weight}_{component}"
                path = self.base / f"fit_{label}.dat"
                with path.open("w", encoding="utf-8") as handle:
                    handle.write("# coordinate data fit residual window\n")
                    for i in range(1, 11):
                        coordinate = i / 10
                        data = weight * factor * i / 10
                        fit = data * 0.9
                        residual = abs(data - fit) * 1.7 if component == "mag" else data - fit
                        handle.write(f"{coordinate} {data} {fit} {residual} 1\n")
                self.fit_files[label] = path

        self.parameters = self.base / "fit_parameters.tsv"
        columns = [
            "sample", "path_index", "path", "scatterer", "degeneracy_theory",
            "amplitude_factor", "cn_fit", "reff_A", "delr_A", "delr_error_A",
            "r_fit_A", "sigma2_A2", "sigma2_error_A2", "e0_eV", "e0_error_eV",
            "s02", "s02_status", "r_factor", "fit_status", "notes",
        ]
        row = {
            "sample": "demo", "path_index": "0", "path": "M-O", "scatterer": "O",
            "degeneracy_theory": "4", "amplitude_factor": "0.75", "cn_fit": "3",
            "reff_A": "2.0", "delr_A": "0.02", "delr_error_A": "0.01",
            "r_fit_A": "2.02", "sigma2_A2": "0.004", "sigma2_error_A2": "0.001",
            "e0_eV": "2", "e0_error_eV": "0.5", "s02": "0.88",
            "s02_status": "fixed", "r_factor": "0.01", "fit_status": "accepted",
            "notes": "synthetic unit-test row",
        }
        with self.parameters.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerow(row)

        self.statistics = self.base / "fit_statistics.tsv"
        self.statistics.write_text(
            "metric\tvalue\tunit\tnotes\n"
            "nind\t12.0\t\t\n"
            "nvar\t4\t\t\n"
            "r_factor\t0.01\t\t\n",
            encoding="utf-8",
        )
        self.project = self.base / "accepted_fit.dpj"
        self.project.write_bytes(b"synthetic Artemis project for package tests\n")
        self.workflow = self.base / "executed_fit_workflow.txt"
        self.workflow.write_text(
            "Input: synthetic chi(k)\nModel: synthetic M-O first shell\n"
            "Windows: k=3-12 A^-1, R=1-2.5 A\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def command(self, output: Path) -> list[str]:
        command = [
            sys.executable, str(SCRIPT), "build", "--output", str(output),
            "--sample", "demo", "--raw", str(self.raw),
            "--artemis-project", str(self.project),
            "--fit-k1", str(self.fit_files["k1"]),
            "--fit-k2", str(self.fit_files["k2"]),
            "--fit-k3", str(self.fit_files["k3"]),
            "--parameters", str(self.parameters),
            "--workflow-source", str(self.workflow),
            "--project-check", "Loaded with the matching Demeter project loader.",
        ]
        for weight in (1, 2, 3):
            for component in ("mag", "re", "im"):
                command.extend([
                    f"--fit-r{weight}-{component}", str(self.fit_files[f"r{weight}_{component}"])
                ])
        return command

    def audit_command(self, output: Path) -> list[str]:
        return self.command(output) + [
            "--profile", "audit", "--processed-chi", str(self.chi),
            "--fit-rmag", str(self.fit_files["rmag"]),
            "--fit-rre", str(self.fit_files["rre"]),
            "--fit-rim", str(self.fit_files["rim"]),
            "--statistics", str(self.statistics),
        ]

    def test_build_and_verify_complete_package(self) -> None:
        output = self.base / "delivery"
        built = subprocess.run(self.command(output), text=True, capture_output=True)
        self.assertEqual(built.returncode, 0, built.stderr)
        payload = json.loads(built.stdout)
        self.assertEqual(payload["status"], "pass")
        packaged_project = output / "accepted_fit.dpj"
        self.assertEqual(packaged_project.read_bytes(), self.project.read_bytes())
        self.assertEqual(
            {path.name for path in output.iterdir()},
            {
                "accepted_fit.dpj", "k1_data_fit.csv", "k2_data_fit.csv", "k3_data_fit.csv",
                "R1_data_fit.csv", "R2_data_fit.csv", "R3_data_fit.csv",
                "fit_parameters.tsv", "FIT_WORKFLOW.txt",
            },
        )
        workflow = (output / "FIT_WORKFLOW.txt").read_text(encoding="utf-8")
        self.assertIn("R1_data_fit.csv = Fourier transform of k^1*chi(k)", workflow)
        self.assertIn("Loaded with the matching Demeter project loader.", workflow)

        verified = subprocess.run(
            [sys.executable, str(SCRIPT), "verify", "--package", str(output)],
            text=True, capture_output=True,
        )
        self.assertEqual(verified.returncode, 0, verified.stderr)

    def test_audit_profile_remains_available(self) -> None:
        output = self.base / "audit_delivery"
        built = subprocess.run(self.audit_command(output), text=True, capture_output=True)
        self.assertEqual(built.returncode, 0, built.stderr)
        self.assertTrue((output / "manifest.json").is_file())
        self.assertTrue((output / "00_OPEN_FIRST" / "accepted_fit.dpj").is_file())

    def test_refuses_negative_sigma2(self) -> None:
        text = self.parameters.read_text(encoding="utf-8").replace("\t0.004\t", "\t-0.004\t")
        self.parameters.write_text(text, encoding="utf-8")
        output = self.base / "bad_delivery"
        built = subprocess.run(self.command(output), text=True, capture_output=True)
        self.assertEqual(built.returncode, 2)
        self.assertIn("negative sigma2", built.stderr)

    def test_requires_openable_artemis_project(self) -> None:
        self.project = self.base / "not_a_project.txt"
        self.project.write_text("not an Artemis project\n", encoding="utf-8")
        output = self.base / "bad_project_delivery"
        built = subprocess.run(self.command(output), text=True, capture_output=True)
        self.assertEqual(built.returncode, 2)
        self.assertIn("must be an .fpj or .dpj", built.stderr)


if __name__ == "__main__":
    unittest.main()
