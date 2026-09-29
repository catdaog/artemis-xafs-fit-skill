#!/usr/bin/env python3
"""Build and verify a reproducible numerical XAFS fit delivery package."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import sys
from typing import Iterable


SCHEMA_VERSION = 2
PARAMETER_COLUMNS = [
    "sample", "path_index", "path", "scatterer", "degeneracy_theory",
    "amplitude_factor", "cn_fit", "reff_A", "delr_A", "delr_error_A",
    "r_fit_A", "sigma2_A2", "sigma2_error_A2", "e0_eV", "e0_error_eV",
    "s02", "s02_status", "r_factor", "fit_status", "notes",
]
MANDATORY_FILES = [
    "DELIVERY.md",
    "01_k_space/chi_k_source.dat",
    "01_k_space/chi_k.csv",
    "01_k_space/kspace_fit_k1.csv",
    "01_k_space/kspace_fit_k2.csv",
    "01_k_space/kspace_fit_k3.csv",
    "02_r_space/rspace_data_fit.csv",
    "03_parameters/fit_parameters.tsv",
    "03_parameters/fit_parameters.md",
    "03_parameters/fit_statistics.tsv",
]
ARTEMIS_PROJECT_SUFFIXES = {".fpj", ".dpj"}
MINIMAL_FILENAMES = {
    "k1_data_fit.csv", "k2_data_fit.csv", "k3_data_fit.csv",
    "R1_data_fit.csv", "R2_data_fit.csv", "R3_data_fit.csv",
    "fit_parameters.tsv", "FIT_WORKFLOW.txt",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def numeric_rows(path: Path, min_columns: int) -> list[list[float]]:
    rows: list[list[float]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";", "!", "%")):
            continue
        fields = [item for item in re.split(r"[\s,]+", stripped) if item]
        try:
            values = [float(item) for item in fields]
        except ValueError:
            continue
        if len(values) >= min_columns:
            rows.append(values)
    if len(rows) < 3:
        raise ValueError(f"{path} has fewer than 3 numeric rows with {min_columns} columns")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError(f"{path} has inconsistent numeric column counts")
    return rows


def ensure_increasing(rows: list[list[float]], label: str) -> None:
    if any(b[0] <= a[0] for a, b in zip(rows, rows[1:])):
        raise ValueError(f"{label} coordinate must be strictly increasing")


def same_grid(a: list[list[float]], b: list[list[float]], label: str) -> None:
    if len(a) != len(b):
        raise ValueError(f"{label} grids have different row counts")
    for index, (ra, rb) in enumerate(zip(a, b), 1):
        if not math.isclose(ra[0], rb[0], rel_tol=1e-10, abs_tol=1e-10):
            raise ValueError(f"{label} grid differs at numeric row {index}")


def write_csv(path: Path, header: list[str], rows: Iterable[Iterable[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def fit_header(width: int, coordinate: str) -> list[str]:
    if width < 4:
        raise ValueError("fit export requires at least four columns")
    header = [coordinate, "data", "fit", "residual"]
    extras = width - 4
    if extras == 1:
        header.append("window")
    elif extras == 2:
        header.extend(["background", "window"])
    elif extras > 1:
        header.extend([f"extra_{i}" for i in range(1, extras)])
        header.append("window")
    return header


def check_residual(rows: list[list[float]], label: str) -> None:
    scale = max(1.0, max(abs(row[1]) for row in rows), max(abs(row[2]) for row in rows))
    tolerance = 5e-6 * scale
    worst = max(abs((row[1] - row[2]) - row[3]) for row in rows)
    if worst > tolerance:
        raise ValueError(
            f"{label} residual column is inconsistent with data-fit: "
            f"max error {worst:.6g} > {tolerance:.6g}"
        )


def copy_unique(source: Path, destination: Path) -> None:
    source = source.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def validate_artemis_project(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.suffix.lower() not in ARTEMIS_PROJECT_SUFFIXES:
        raise ValueError("primary Artemis project must be an .fpj or .dpj file")
    if path.stat().st_size == 0:
        raise ValueError("primary Artemis project is empty")


def read_delimited(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    text = path.read_text(encoding="utf-8-sig", errors="strict")
    first = next((line for line in text.splitlines() if line.strip()), "")
    delimiter = "\t" if "\t" in first else ","
    reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError(f"{path} has no header")
    header = [str(item).strip() for item in reader.fieldnames]
    rows = [{key: (value or "").strip() for key, value in row.items()} for row in reader]
    return header, rows


def normalize_parameters(source: Path, tsv_out: Path, md_out: Path | None = None) -> int:
    header, rows = read_delimited(source)
    missing = [name for name in PARAMETER_COLUMNS if name not in header]
    if missing:
        raise ValueError(f"parameter table is missing columns: {', '.join(missing)}")
    with tsv_out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PARAMETER_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows({name: row.get(name, "") for name in PARAMETER_COLUMNS} for row in rows)

    if md_out is not None:
        display = [
            ("sample", "Sample"), ("path", "Path"), ("degeneracy_theory", "N theory"),
            ("cn_fit", "CN fit"), ("reff_A", "Reff (Å)"), ("delr_A", "ΔR (Å)"),
            ("r_fit_A", "R fit (Å)"), ("sigma2_A2", "σ² (Å²)"),
            ("e0_eV", "ΔE0 (eV)"), ("s02", "S0²"),
            ("r_factor", "R-factor"), ("fit_status", "Status"),
        ]
        with md_out.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write("| " + " | ".join(label for _, label in display) + " |\n")
            handle.write("| " + " | ".join("---" for _ in display) + " |\n")
            for row in rows:
                values = [row.get(name, "").replace("|", "\\|").replace("\n", " ") for name, _ in display]
                handle.write("| " + " | ".join(values) + " |\n")
    return len(rows)


def parameter_invariants(path: Path) -> None:
    _, rows = read_delimited(path)
    for line_no, row in enumerate(rows, 2):
        def number(name: str) -> float | None:
            value = row.get(name, "").strip()
            return float(value) if value else None

        reff, delr, rfit = number("reff_A"), number("delr_A"), number("r_fit_A")
        if None not in (reff, delr, rfit) and not math.isclose(
            reff + delr, rfit, rel_tol=1e-7, abs_tol=1e-7
        ):
            raise ValueError(f"parameter row {line_no}: r_fit_A != reff_A + delr_A")
        deg, amp, cn = number("degeneracy_theory"), number("amplitude_factor"), number("cn_fit")
        if None not in (deg, amp, cn) and not math.isclose(
            deg * amp, cn, rel_tol=1e-7, abs_tol=1e-7
        ):
            raise ValueError(f"parameter row {line_no}: cn_fit != degeneracy_theory * amplitude_factor")
        sigma2 = number("sigma2_A2")
        if sigma2 is not None and sigma2 < 0:
            raise ValueError(f"parameter row {line_no}: negative sigma2")


def inventory(package: Path, roles: dict[str, str]) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for path in sorted(p for p in package.rglob("*") if p.is_file() and p.name != "manifest.json"):
        relative = path.relative_to(package).as_posix()
        entry: dict[str, object] = {
            "path": relative,
            "role": roles.get(relative, "supporting_file"),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        if path.suffix.lower() in {".csv", ".tsv", ".dat"}:
            try:
                entry["numeric_rows"] = len(numeric_rows(path, 2))
            except ValueError:
                pass
        items.append(entry)
    return items


def require_paths(args: argparse.Namespace, names: Iterable[str], profile: str) -> None:
    missing = [f"--{name.replace('_', '-')}" for name in names if getattr(args, name) is None]
    if missing:
        raise ValueError(f"{profile} profile requires: {', '.join(missing)}")


def normalized_fit(source: Path, destination: Path, coordinate: str, label: str) -> list[list[float]]:
    rows = numeric_rows(source, 4)
    ensure_increasing(rows, label)
    if "mag" not in label:
        check_residual(rows, label)
    write_csv(destination, fit_header(len(rows[0]), coordinate), rows)
    return rows


def combine_r_components(
    magnitude: Path, real: Path, imaginary: Path, destination: Path, weight: int
) -> None:
    mag_rows = numeric_rows(magnitude, 4)
    real_rows = numeric_rows(real, 4)
    imag_rows = numeric_rows(imaginary, 4)
    for label, rows in (("magnitude", mag_rows), ("real", real_rows), ("imaginary", imag_rows)):
        ensure_increasing(rows, f"R{weight} {label}")
    check_residual(real_rows, f"R{weight} real")
    check_residual(imag_rows, f"R{weight} imaginary")
    same_grid(mag_rows, real_rows, f"R{weight} magnitude/real")
    same_grid(mag_rows, imag_rows, f"R{weight} magnitude/imaginary")
    combined = []
    for mag, real_row, imag in zip(mag_rows, real_rows, imag_rows):
        window = mag[-1] if len(mag) > 4 else ""
        combined.append([
            mag[0], mag[1], mag[2], mag[3],
            real_row[1], real_row[2], real_row[3],
            imag[1], imag[2], imag[3], window,
        ])
    write_csv(destination, [
        "R_A", "data_mag", "fit_mag", "residual_mag",
        "data_real", "fit_real", "residual_real",
        "data_imag", "fit_imag", "residual_imag", "window",
    ], combined)


def write_workflow(args: argparse.Namespace, destination: Path) -> None:
    source_text = ""
    if args.workflow_source is not None:
        source_text = args.workflow_source.read_text(encoding="utf-8-sig", errors="strict").strip()
        if not source_text:
            raise ValueError("workflow source is empty")
    raw_names = ", ".join(str(path.resolve()) for path in args.raw) or "not packaged in minimal profile"
    lines = [
        f"XAFS FIT WORKFLOW — {args.sample}",
        "=" * (20 + len(args.sample)),
        "",
        "Purpose",
        "-------",
        "This file records how the delivered Artemis project and numerical fit tables were generated.",
        "",
        "Inputs",
        "------",
        f"Raw/Athena inputs: {raw_names}",
        f"Final Artemis project source: {args.artemis_project.resolve()}",
        f"Parameter-table source: {args.parameters.resolve()}",
        "",
        "Fit and export sequence",
        "-----------------------",
        "1. Import and preprocess the measured spectrum in Athena/Demeter without altering the source file.",
        "2. Calibrate energy, choose the FEFF model and paths, and run the accepted Artemis/Demeter fit.",
        "3. Save one final DPJ project after the accepted fit.",
        "4. Export k1, k2 and k3 data/fit/residual tables from the same fit result.",
        "5. For each R file, set Demeter's plot k-weight to 1, 2 or 3 before exporting magnitude, real and imaginary components.",
        "6. Combine only components with identical R grids. Magnitude residual is |chi_data(R)-chi_fit(R)|; real and imaginary residuals are data-fit.",
        "7. Normalize one parameter table and verify CN, R=Reff+DeltaR and non-negative sigma2 invariants.",
        "8. Recheck the DPJ and package exactly the default nine deliverables.",
        "",
        "R-file meaning",
        "--------------",
        "R1_data_fit.csv = Fourier transform of k^1*chi(k)",
        "R2_data_fit.csv = Fourier transform of k^2*chi(k)",
        "R3_data_fit.csv = Fourier transform of k^3*chi(k)",
        "Each R file contains magnitude, real and imaginary data, fit and residual columns.",
        "",
        "Project integrity check",
        "-----------------------",
        args.project_check.strip(),
    ]
    if args.notes:
        lines.extend(["", "Packaging notes", "---------------", args.notes.strip()])
    if source_text:
        lines.extend(["", "Executed fit record", "-------------------", source_text])
    destination.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def build_minimal(args: argparse.Namespace) -> int:
    required = [
        "fit_k1", "fit_k2", "fit_k3",
        "fit_r1_mag", "fit_r1_re", "fit_r1_im",
        "fit_r2_mag", "fit_r2_re", "fit_r2_im",
        "fit_r3_mag", "fit_r3_re", "fit_r3_im",
        "parameters", "workflow_source",
    ]
    require_paths(args, required, "minimal")
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing destination: {output}")
    validate_artemis_project(args.artemis_project)
    if args.artemis_project.suffix.lower() != ".dpj":
        raise ValueError("minimal profile requires a final .dpj project")
    if not args.project_check.strip():
        raise ValueError("--project-check must record how the final DPJ was reopened or loaded")
    output.mkdir(parents=True)
    copy_unique(args.artemis_project, output / args.artemis_project.name)

    k_rows = {}
    for weight in (1, 2, 3):
        source = getattr(args, f"fit_k{weight}")
        k_rows[weight] = normalized_fit(
            source, output / f"k{weight}_data_fit.csv", "k_A^-1", f"k{weight}"
        )
    same_grid(k_rows[1], k_rows[2], "k1/k2")
    same_grid(k_rows[1], k_rows[3], "k1/k3")

    for weight in (1, 2, 3):
        combine_r_components(
            getattr(args, f"fit_r{weight}_mag"),
            getattr(args, f"fit_r{weight}_re"),
            getattr(args, f"fit_r{weight}_im"),
            output / f"R{weight}_data_fit.csv", weight,
        )

    parameter_count = normalize_parameters(args.parameters, output / "fit_parameters.tsv")
    parameter_invariants(output / "fit_parameters.tsv")
    write_workflow(args, output / "FIT_WORKFLOW.txt")
    result = verify_minimal(output)
    print(json.dumps({
        **result, "sample": args.sample, "parameter_rows": parameter_count,
    }, ensure_ascii=False))
    return 0


def build_audit(args: argparse.Namespace) -> int:
    require_paths(args, [
        "processed_chi", "fit_k1", "fit_k2", "fit_k3",
        "fit_rmag", "fit_rre", "fit_rim", "parameters", "statistics",
    ], "audit")
    if not args.raw:
        raise ValueError("audit profile requires at least one --raw input")
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing destination: {output}")
    roles: dict[str, str] = {}
    sources: list[dict[str, str]] = []
    output.mkdir(parents=True)

    def remember(source: Path, destination: Path, role: str) -> None:
        copy_unique(source, destination)
        relative = destination.relative_to(output).as_posix()
        roles[relative] = role
        sources.append({
            "source": str(source.resolve()),
            "source_sha256": sha256(source.resolve()),
            "packaged_path": relative,
        })

    validate_artemis_project(args.artemis_project)
    project_out = output / "00_OPEN_FIRST" / args.artemis_project.name
    remember(args.artemis_project, project_out, "primary_openable_artemis_project")

    for index, source in enumerate(args.raw, 1):
        destination = output / "04_raw_source" / f"{index:03d}_{source.name}"
        remember(source, destination, "untouched_raw_input")

    processed_source = output / "01_k_space" / "chi_k_source.dat"
    remember(args.processed_chi, processed_source, "processed_chi_source_export")
    chi_rows = numeric_rows(args.processed_chi, 6)
    ensure_increasing(chi_rows, "processed chi(k)")
    chi_out = output / "01_k_space" / "chi_k.csv"
    write_csv(
        chi_out,
        ["k_A^-1", "chi", "k1_chi", "k2_chi", "k3_chi", "window"],
        (row[:6] for row in chi_rows),
    )
    roles[chi_out.relative_to(output).as_posix()] = "normalized_processed_chi"

    fit_inputs = {
        "k1": args.fit_k1, "k2": args.fit_k2, "k3": args.fit_k3,
        "rmag": args.fit_rmag, "rre": args.fit_rre, "rim": args.fit_rim,
    }
    fit_rows: dict[str, list[list[float]]] = {}
    for label, source in fit_inputs.items():
        fit_directory = "01_k_space" if label.startswith("k") else "02_r_space"
        source_copy = output / fit_directory / "source_exports" / f"fit_{label}{source.suffix or '.dat'}"
        remember(source, source_copy, f"demeter_fit_{label}_source_export")
        rows = numeric_rows(source, 4)
        ensure_increasing(rows, f"fit {label}")
        # rmag residual is |complex(data-fit)|, not |data|-|fit|.
        if label != "rmag":
            check_residual(rows, f"fit {label}")
        fit_rows[label] = rows

    same_grid(fit_rows["k1"], fit_rows["k2"], "k1/k2")
    same_grid(fit_rows["k1"], fit_rows["k3"], "k1/k3")
    for label in ("k1", "k2", "k3"):
        destination = output / "01_k_space" / f"kspace_fit_{label}.csv"
        write_csv(destination, fit_header(len(fit_rows[label][0]), "k_A^-1"), fit_rows[label])
        roles[destination.relative_to(output).as_posix()] = f"normalized_kspace_fit_{label}"

    same_grid(fit_rows["rmag"], fit_rows["rre"], "rmag/rre")
    same_grid(fit_rows["rmag"], fit_rows["rim"], "rmag/rim")
    r_rows = []
    for mag, real, imag in zip(fit_rows["rmag"], fit_rows["rre"], fit_rows["rim"]):
        window = mag[-1] if len(mag) > 4 else ""
        r_rows.append([
            mag[0], mag[1], mag[2], mag[3],
            real[1], real[2], real[3], imag[1], imag[2], imag[3], window,
        ])
    r_out = output / "02_r_space" / "rspace_data_fit.csv"
    write_csv(r_out, [
        "R_A", "data_mag", "fit_mag", "residual_mag",
        "data_real", "fit_real", "residual_real",
        "data_imag", "fit_imag", "residual_imag", "window",
    ], r_rows)
    roles[r_out.relative_to(output).as_posix()] = "combined_rspace_fit"

    parameter_out = output / "03_parameters" / "fit_parameters.tsv"
    parameter_md = output / "03_parameters" / "fit_parameters.md"
    parameter_out.parent.mkdir(parents=True, exist_ok=True)
    parameter_source = output / "03_parameters" / "source_fit_parameters.tsv"
    remember(args.parameters, parameter_source, "source_parameter_table")
    parameter_count = normalize_parameters(parameter_source, parameter_out, parameter_md)
    parameter_invariants(parameter_out)
    roles[parameter_out.relative_to(output).as_posix()] = "machine_readable_parameter_table"
    roles[parameter_md.relative_to(output).as_posix()] = "human_readable_parameter_table"
    statistics_out = output / "03_parameters" / "fit_statistics.tsv"
    remember(args.statistics, statistics_out, "fit_statistics")

    for source in args.artifact:
        if source.resolve() == args.artemis_project.resolve():
            continue
        remember(source, output / "05_models_feff" / source.name, "model_feff_or_log")
    for source in args.qa:
        remember(source, output / "06_qa" / source.name, "qa_calibration_or_provenance")

    delivery = output / "DELIVERY.md"
    raw_lines = "\n".join(
        f"- `{item['packaged_path']}`"
        for item in sources if item["packaged_path"].startswith("04_raw_source/")
    )
    delivery.write_text(
        f"# {args.sample} XAFS fit delivery\n\n"
        f"This package contains numerical data and artifacts from an executed XAFS fit. "
        f"The raw files below are byte-for-byte copies; no source file was overwritten.\n\n"
        f"## 1. OPEN FIRST — fitted Artemis project\n\n"
        f"- `{project_out.relative_to(output).as_posix()}`: final accepted fit, directly openable in Artemis.\n\n"
        f"## 2. k-space original data and fit\n\n"
        f"- `01_k_space/chi_k_source.dat`: unchanged processed χ(k) export.\n"
        f"- `01_k_space/chi_k.csv`: processed χ(k) and k¹/k²/k³-weighted data.\n"
        f"- `01_k_space/kspace_fit_k1.csv`, `kspace_fit_k2.csv`, `kspace_fit_k3.csv`: data, fit, residual, and window.\n\n"
        f"## 3. R-space original data and fit\n\n"
        f"- `02_r_space/source_exports/`: unchanged Demeter magnitude, real, and imaginary exports.\n"
        f"- `02_r_space/rspace_data_fit.csv`: magnitude, real, and imaginary data/fit/residual on one verified R grid.\n\n"
        f"## Supporting files\n\n"
        f"- `03_parameters/fit_parameters.tsv` and `.md`: {parameter_count} path parameter rows.\n"
        f"- Raw inputs:\n{raw_lines}\n"
        f"- `manifest.json`: hashes and provenance for packaged files.\n\n"
        f"## Notes\n\n{args.notes or 'No additional packaging note was supplied.'}\n",
        encoding="utf-8",
    )
    roles["DELIVERY.md"] = "delivery_readme"

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "sample": args.sample,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "builder": "artemis-xafs-fit-skill/scripts/build_xafs_delivery.py",
        "primary_artemis_project": project_out.relative_to(output).as_posix(),
        "source_inputs": sources,
        "files": inventory(output, roles),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    verify_package(output)
    print(json.dumps({
        "status": "pass", "package": str(output), "sample": args.sample,
        "files": len(manifest["files"]), "parameter_rows": parameter_count,
    }, ensure_ascii=False))
    return 0


def verify_minimal(package: Path) -> dict[str, object]:
    package = package.resolve()
    projects = [
        path for path in package.iterdir()
        if path.is_file() and path.suffix.lower() == ".dpj"
    ]
    if len(projects) != 1:
        raise ValueError("minimal package must contain exactly one .dpj file")
    validate_artemis_project(projects[0])
    expected = MINIMAL_FILENAMES | {projects[0].name}
    actual = {path.name for path in package.iterdir() if path.is_file()}
    nested = [path for path in package.iterdir() if path.is_dir()]
    if nested:
        raise ValueError("minimal package must be flat and contain no subdirectories")
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if extra:
            details.append(f"unexpected: {', '.join(extra)}")
        raise ValueError("minimal package file set mismatch (" + "; ".join(details) + ")")
    k_rows = {}
    for weight in (1, 2, 3):
        rows = numeric_rows(package / f"k{weight}_data_fit.csv", 4)
        ensure_increasing(rows, f"k{weight}")
        check_residual(rows, f"k{weight}")
        k_rows[weight] = rows
    same_grid(k_rows[1], k_rows[2], "k1/k2")
    same_grid(k_rows[1], k_rows[3], "k1/k3")
    for weight in (1, 2, 3):
        rows = numeric_rows(package / f"R{weight}_data_fit.csv", 10)
        ensure_increasing(rows, f"R{weight}")
        for component, indices in {
            "real": (4, 5, 6), "imaginary": (7, 8, 9),
        }.items():
            pseudo = [[row[0], row[indices[0]], row[indices[1]], row[indices[2]]] for row in rows]
            check_residual(pseudo, f"R{weight} {component}")
    parameter_invariants(package / "fit_parameters.tsv")
    workflow = (package / "FIT_WORKFLOW.txt").read_text(encoding="utf-8")
    for token in ("k1", "k2", "k3", "R1_data_fit.csv", "R2_data_fit.csv", "R3_data_fit.csv"):
        if token not in workflow:
            raise ValueError(f"FIT_WORKFLOW.txt does not explain {token}")
    return {"status": "pass", "profile": "minimal", "package": str(package), "files": len(actual)}


def verify_package(package: Path) -> dict[str, object]:
    package = package.resolve()
    manifest_path = package / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported manifest schema version")
    if not any((package / "04_raw_source").glob("*")):
        raise ValueError("package has no untouched raw input")
    project_directory = package / "00_OPEN_FIRST"
    projects = [
        path for path in project_directory.glob("*")
        if path.is_file() and path.suffix.lower() in ARTEMIS_PROJECT_SUFFIXES
    ]
    if len(projects) != 1:
        raise ValueError("package must contain exactly one .fpj or .dpj in 00_OPEN_FIRST")
    validate_artemis_project(projects[0])
    expected_project = manifest.get("primary_artemis_project")
    if expected_project != projects[0].relative_to(package).as_posix():
        raise ValueError("manifest primary_artemis_project does not match 00_OPEN_FIRST")
    missing = [name for name in MANDATORY_FILES if not (package / name).is_file()]
    if missing:
        raise ValueError(f"package is missing mandatory files: {', '.join(missing)}")
    listed = {entry["path"]: entry for entry in manifest.get("files", [])}
    for relative, entry in listed.items():
        path = package / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.stat().st_size != entry["bytes"] or sha256(path) != entry["sha256"]:
            raise ValueError(f"manifest mismatch: {relative}")
    actual = {
        path.relative_to(package).as_posix()
        for path in package.rglob("*") if path.is_file() and path.name != "manifest.json"
    }
    unlisted = sorted(actual - set(listed))
    if unlisted:
        raise ValueError(f"unlisted package files: {', '.join(unlisted)}")
    for source in manifest.get("source_inputs", []):
        packaged_path = source.get("packaged_path")
        if packaged_path not in listed:
            raise ValueError(f"source input is not represented in file inventory: {packaged_path}")
        if listed[packaged_path]["sha256"] != source.get("source_sha256"):
            raise ValueError(f"source-copy hash mismatch: {packaged_path}")

    for name in ("k1", "k2", "k3"):
        rows = numeric_rows(package / "01_k_space" / f"kspace_fit_{name}.csv", 4)
        ensure_increasing(rows, f"normalized {name}")
        check_residual(rows, f"normalized {name}")
    r_rows = numeric_rows(package / "02_r_space" / "rspace_data_fit.csv", 10)
    ensure_increasing(r_rows, "normalized R-space")
    for component, indices in {
        "real": (4, 5, 6), "imaginary": (7, 8, 9)
    }.items():
        pseudo = [[row[0], row[indices[0]], row[indices[1]], row[indices[2]]] for row in r_rows]
        check_residual(pseudo, f"R-space {component}")
    parameter_invariants(package / "03_parameters" / "fit_parameters.tsv")
    return {"status": "pass", "package": str(package), "files": len(listed)}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    build_p = sub.add_parser("build", help="assemble a new delivery package")
    build_p.add_argument("--output", type=Path, required=True)
    build_p.add_argument("--sample", required=True)
    build_p.add_argument(
        "--profile", choices=("minimal", "audit"), default="minimal",
        help="minimal is the default nine-file delivery; audit preserves the extended package",
    )
    build_p.add_argument(
        "--artemis-project", type=Path, required=True,
        help="final accepted Artemis .fpj or .dpj; packaged as the primary file",
    )
    build_p.add_argument("--raw", type=Path, action="append", default=[])
    build_p.add_argument("--processed-chi", type=Path)
    build_p.add_argument("--fit-k1", type=Path, required=True)
    build_p.add_argument("--fit-k2", type=Path, required=True)
    build_p.add_argument("--fit-k3", type=Path, required=True)
    for weight in (1, 2, 3):
        build_p.add_argument(f"--fit-r{weight}-mag", type=Path)
        build_p.add_argument(f"--fit-r{weight}-re", type=Path)
        build_p.add_argument(f"--fit-r{weight}-im", type=Path)
    build_p.add_argument("--fit-rmag", type=Path, help="audit profile legacy R-magnitude export")
    build_p.add_argument("--fit-rre", type=Path, help="audit profile legacy R-real export")
    build_p.add_argument("--fit-rim", type=Path, help="audit profile legacy R-imaginary export")
    build_p.add_argument("--parameters", type=Path, required=True)
    build_p.add_argument("--statistics", type=Path)
    build_p.add_argument("--artifact", type=Path, action="append", default=[])
    build_p.add_argument("--qa", type=Path, action="append", default=[])
    build_p.add_argument("--workflow-source", type=Path)
    build_p.add_argument(
        "--project-check", default="",
        help="record of reopening the final DPJ in Artemis or loading it with Demeter",
    )
    build_p.add_argument("--notes")
    verify_p = sub.add_parser("verify", help="verify hashes and numerical invariants")
    verify_p.add_argument("--package", type=Path, required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "build":
            return build_minimal(args) if args.profile == "minimal" else build_audit(args)
        result = (
            verify_package(args.package)
            if (args.package / "manifest.json").is_file()
            else verify_minimal(args.package)
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
