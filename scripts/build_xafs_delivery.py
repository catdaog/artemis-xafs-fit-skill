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


SCHEMA_VERSION = 1
PARAMETER_COLUMNS = [
    "sample", "path_index", "path", "scatterer", "degeneracy_theory",
    "amplitude_factor", "cn_fit", "reff_A", "delr_A", "delr_error_A",
    "r_fit_A", "sigma2_A2", "sigma2_error_A2", "e0_eV", "e0_error_eV",
    "s02", "s02_status", "r_factor", "fit_status", "notes",
]
MANDATORY_FILES = [
    "DELIVERY.md",
    "02_processed/chi_k_source.dat",
    "02_processed/chi_k.csv",
    "03_fit/kspace_fit_k1.csv",
    "03_fit/kspace_fit_k2.csv",
    "03_fit/kspace_fit_k3.csv",
    "03_fit/rspace_fit.csv",
    "04_parameters/fit_parameters.tsv",
    "04_parameters/fit_parameters.md",
    "04_parameters/fit_statistics.tsv",
]


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


def normalize_parameters(source: Path, tsv_out: Path, md_out: Path) -> int:
    header, rows = read_delimited(source)
    missing = [name for name in PARAMETER_COLUMNS if name not in header]
    if missing:
        raise ValueError(f"parameter table is missing columns: {', '.join(missing)}")
    with tsv_out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PARAMETER_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows({name: row.get(name, "") for name in PARAMETER_COLUMNS} for row in rows)

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


def build(args: argparse.Namespace) -> int:
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

    for index, source in enumerate(args.raw, 1):
        destination = output / "01_raw" / f"{index:03d}_{source.name}"
        remember(source, destination, "untouched_raw_input")

    processed_source = output / "02_processed" / "chi_k_source.dat"
    remember(args.processed_chi, processed_source, "processed_chi_source_export")
    chi_rows = numeric_rows(args.processed_chi, 6)
    ensure_increasing(chi_rows, "processed chi(k)")
    chi_out = output / "02_processed" / "chi_k.csv"
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
        source_copy = output / "03_fit" / "source_exports" / f"fit_{label}{source.suffix or '.dat'}"
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
        destination = output / "03_fit" / f"kspace_fit_{label}.csv"
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
    r_out = output / "03_fit" / "rspace_fit.csv"
    write_csv(r_out, [
        "R_A", "data_mag", "fit_mag", "residual_mag",
        "data_real", "fit_real", "residual_real",
        "data_imag", "fit_imag", "residual_imag", "window",
    ], r_rows)
    roles[r_out.relative_to(output).as_posix()] = "combined_rspace_fit"

    parameter_out = output / "04_parameters" / "fit_parameters.tsv"
    parameter_md = output / "04_parameters" / "fit_parameters.md"
    parameter_out.parent.mkdir(parents=True, exist_ok=True)
    parameter_source = output / "04_parameters" / "source_fit_parameters.tsv"
    remember(args.parameters, parameter_source, "source_parameter_table")
    parameter_count = normalize_parameters(parameter_source, parameter_out, parameter_md)
    parameter_invariants(parameter_out)
    roles[parameter_out.relative_to(output).as_posix()] = "machine_readable_parameter_table"
    roles[parameter_md.relative_to(output).as_posix()] = "human_readable_parameter_table"
    statistics_out = output / "04_parameters" / "fit_statistics.tsv"
    remember(args.statistics, statistics_out, "fit_statistics")

    for source in args.artifact:
        remember(source, output / "05_models_projects" / source.name, "model_project_or_log")
    for source in args.qa:
        remember(source, output / "06_qa" / source.name, "qa_calibration_or_provenance")

    delivery = output / "DELIVERY.md"
    raw_lines = "\n".join(f"- `{item['packaged_path']}`" for item in sources if item["packaged_path"].startswith("01_raw/"))
    delivery.write_text(
        f"# {args.sample} XAFS fit delivery\n\n"
        f"This package contains numerical data and artifacts from an executed XAFS fit. "
        f"The raw files below are byte-for-byte copies; no source file was overwritten.\n\n"
        f"## Raw inputs\n\n{raw_lines}\n\n"
        f"## Core outputs\n\n"
        f"- `02_processed/chi_k.csv`: processed χ(k) and k¹/k²/k³-weighted data.\n"
        f"- `03_fit/kspace_fit_k1.csv`, `kspace_fit_k2.csv`, `kspace_fit_k3.csv`: data, fit, residual, and window.\n"
        f"- `03_fit/rspace_fit.csv`: magnitude, real, and imaginary data/fit/residual on one verified R grid.\n"
        f"- `04_parameters/fit_parameters.tsv` and `.md`: {parameter_count} path parameter rows.\n"
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


def verify_package(package: Path) -> dict[str, object]:
    package = package.resolve()
    manifest_path = package / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported manifest schema version")
    if not any((package / "01_raw").glob("*")):
        raise ValueError("package has no untouched raw input")
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
        rows = numeric_rows(package / "03_fit" / f"kspace_fit_{name}.csv", 4)
        ensure_increasing(rows, f"normalized {name}")
        check_residual(rows, f"normalized {name}")
    r_rows = numeric_rows(package / "03_fit" / "rspace_fit.csv", 10)
    ensure_increasing(r_rows, "normalized R-space")
    for component, indices in {
        "real": (4, 5, 6), "imaginary": (7, 8, 9)
    }.items():
        pseudo = [[row[0], row[indices[0]], row[indices[1]], row[indices[2]]] for row in r_rows]
        check_residual(pseudo, f"R-space {component}")
    parameter_invariants(package / "04_parameters" / "fit_parameters.tsv")
    return {"status": "pass", "package": str(package), "files": len(listed)}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    build_p = sub.add_parser("build", help="assemble a new delivery package")
    build_p.add_argument("--output", type=Path, required=True)
    build_p.add_argument("--sample", required=True)
    build_p.add_argument("--raw", type=Path, action="append", required=True)
    build_p.add_argument("--processed-chi", type=Path, required=True)
    build_p.add_argument("--fit-k1", type=Path, required=True)
    build_p.add_argument("--fit-k2", type=Path, required=True)
    build_p.add_argument("--fit-k3", type=Path, required=True)
    build_p.add_argument("--fit-rmag", type=Path, required=True)
    build_p.add_argument("--fit-rre", type=Path, required=True)
    build_p.add_argument("--fit-rim", type=Path, required=True)
    build_p.add_argument("--parameters", type=Path, required=True)
    build_p.add_argument("--statistics", type=Path, required=True)
    build_p.add_argument("--artifact", type=Path, action="append", default=[])
    build_p.add_argument("--qa", type=Path, action="append", default=[])
    build_p.add_argument("--notes")
    verify_p = sub.add_parser("verify", help="verify hashes and numerical invariants")
    verify_p.add_argument("--package", type=Path, required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "build":
            return build(args)
        result = verify_package(args.package)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
