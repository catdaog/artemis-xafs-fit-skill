#!/usr/bin/env python3
"""Reproducible complex Morlet EXAFS wavelets and numeric Origin matrices.

Only NumPy is required. This is post-processing of measured/simulated chi(k),
not a denoiser, fit engine, phase correction, or atom-identification algorithm.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import sys

import numpy as np

DEFAULTS = dict(kappa=10.0, sigma=1.0, kweight=2.0, kstep=0.05,
                rmin=0.0, rmax=6.0, rstep=0.02, window="hanning", dk=1.0,
                memory_mb=256.0, max_gap_factor=1.5, method="morlet")
FORMULA = {
    "mother": "psi(u)=(exp(i*kappa*u)-exp(-0.5*(kappa*sigma)^2))*exp(-u^2/(2*sigma^2))/(sqrt(2*pi)*sigma)",
    "transform": "W(k,R)=a^(-1/2)*integral[f(kprime)*conj(psi((kprime-k)/a)) dkprime]",
    "scale": "a=kappa/(2*R); W(k,0)=0 by explicit convention",
    "signal": "f(k)=k^kweight*chi(k)*window(k)",
    "quadrature": "uniform-grid composite trapezoidal rule; finite measured support; linear FFT convolution with sufficient zero padding",
    "phase_correction": False,
    "amplitude_convention": "L2 scale normalization a^(-1/2); no claim of HAMA amplitude equivalence",
}


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _number(value, key, minimum=None, positive=False):
    if isinstance(value, bool):
        raise ValueError(f"{key} must be a finite number")
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be a finite number") from exc
    if not math.isfinite(value) or (positive and value <= 0) or (minimum is not None and value < minimum):
        raise ValueError(f"Invalid {key}: {value}")
    return value


def validate_options(config):
    """Validate global options without accessing input files or creating output."""
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a JSON object")
    unknown = set(config) - set(DEFAULTS) - {"kmin", "kmax", "spectra", "residuals"}
    if unknown:
        raise ValueError("Unknown WT configuration keys: " + ", ".join(sorted(unknown)))
    result = dict(DEFAULTS)
    result.update({k: config[k] for k in DEFAULTS if k in config})
    for key in ("kappa", "sigma", "kstep", "rstep", "memory_mb"):
        result[key] = _number(result[key], key, positive=True)
    for key in ("kweight", "rmin", "rmax", "dk"):
        result[key] = _number(result[key], key, minimum=0)
    result["max_gap_factor"] = _number(result["max_gap_factor"], "max_gap_factor", minimum=1)
    for key in ("kmin", "kmax"):
        result[key] = None if config.get(key) is None else _number(config[key], key, minimum=0)
    if result["rmax"] <= result["rmin"]:
        raise ValueError("rmax must exceed rmin")
    if result["rmax"] >= math.pi / (2 * result["kstep"]):
        raise ValueError("rmax reaches/exceeds the uniform-grid sampling Nyquist R=pi/(2*kstep)")
    if result["kmin"] is not None and result["kmax"] is not None and result["kmax"] <= result["kmin"]:
        raise ValueError("kmax must exceed kmin")
    if result["method"] != "morlet":
        raise ValueError("Only the explicitly defined morlet method is implemented")
    if result["window"] not in ("hanning", "none"):
        raise ValueError("window must be hanning or none")
    if result["window"] == "hanning" and result["dk"] <= 0:
        raise ValueError("Hanning dk must be positive")
    if result["kappa"] * result["sigma"] < 1:
        raise ValueError("kappa*sigma must be at least 1 for this positive-frequency EXAFS convention")
    return result


def _column(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive 1-based integer")
    return value - 1


def read_chi(path, k_column=1, chi_column=2, max_gap_factor=1.5):
    """Read numeric chi data, allowing leading headers but never damaged rows.

    Comma/tab rows preserve empty fields. All columns of a numeric row must be
    numeric and finite, and the numeric table must have a consistent width.
    Large internal k gaps are rejected relative to its median native spacing.
    """
    path = Path(path)
    kc, cc = _column(k_column, "k_column"), _column(chi_column, "chi_column")
    rows = []
    width = None
    with path.open(encoding="utf-8-sig", errors="strict") as stream:
        for lineno, line in enumerate(stream, 1):
            line = line.strip()
            if not line or line.startswith(("#", ";", "!", "%")):
                continue
            fields = [x.strip() for x in line.split(",")] if "," in line else (
                [x.strip() for x in line.split("\t")] if "\t" in line else line.split())
            try:
                float(fields[0].replace("D", "E").replace("d", "e"))
                numeric_start = True
            except ValueError:
                numeric_start = False
            try:
                values = [float(x.replace("D", "E").replace("d", "e")) for x in fields]
            except ValueError as exc:
                if not rows and not numeric_start:
                    continue
                raise ValueError(f"{path}:{lineno}: malformed numeric row/interior header") from exc
            if len(values) <= max(kc, cc) or (width is not None and len(values) != width):
                raise ValueError(f"{path}:{lineno}: missing/inconsistent numeric columns")
            if not all(math.isfinite(x) for x in values):
                raise ValueError(f"{path}:{lineno}: non-finite numeric value")
            width = len(values)
            rows.append((values[kc], values[cc]))
    if len(rows) < 3:
        raise ValueError(f"{path}: need at least three numeric rows")
    data = np.asarray(rows, dtype=float)
    k = data[:, 0]
    delta = np.diff(k)
    if k[0] < 0 or np.any(delta <= 0):
        raise ValueError(f"{path}: k must be nonnegative, ascending, and unique")
    median = float(np.median(delta))
    if np.max(delta) > median * float(max_gap_factor) * (1 + 1e-8):
        raise ValueError(f"{path}: interior k gap exceeds max_gap_factor times median spacing")
    return k, data[:, 1]


def _axis(start, stop, step, name):
    # Do not append a fractional final interval to a uniform numerical grid.
    count = int(math.floor((stop - start) / step + 1e-9)) + 1
    if count < 2 and name == "k":
        raise ValueError("Selected k interval contains fewer than two grid points")
    if count <= 0 or count > 2_000_000:
        raise ValueError(f"Unreasonable {name} grid size: {count}")
    return start + step * np.arange(count, dtype=float)


def hanning_window(k, dk=1.0):
    """Product of left/right half-cosine ramps, including overlapping ramps."""
    left = 0.5 * (1 - np.cos(np.pi * np.clip((k - k[0]) / dk, 0, 1)))
    right = 0.5 * (1 - np.cos(np.pi * np.clip((k[-1] - k) / dk, 0, 1)))
    return left * right


def morlet_transform(k, signal, r, kappa=10.0, sigma=1.0):
    """Complex WT on uniform k, by non-circular linear convolution.

    The convolution kernel uses psi(lag/a), because the defining integral uses
    conj(psi((kprime-k)/a)). This sign matters for complex phase and residuals.
    """
    k, signal, r = np.asarray(k, float), np.asarray(signal, float), np.asarray(r, float)
    if k.ndim != 1 or signal.shape != k.shape or r.ndim != 1 or len(k) < 2:
        raise ValueError("Invalid k/signal/R shapes")
    step = float(k[1] - k[0])
    if step <= 0 or not np.allclose(np.diff(k), step, rtol=1e-8, atol=1e-12):
        raise ValueError("WT requires a strictly uniform increasing k grid")
    if not np.isfinite(signal).all() or not np.isfinite(r).all() or np.any(r < 0):
        raise ValueError("WT signal/R must be finite; R must be nonnegative")
    n = len(k)
    nfft = 1 << (3 * n - 3).bit_length()  # >= n + (2*n-1) - 1
    weighted = signal.copy()
    weighted[[0, -1]] *= 0.5
    spectrum = np.fft.fft(weighted, nfft)
    lags = np.arange(-(n - 1), n, dtype=float) * step
    result = np.zeros((len(r), n), dtype=complex)
    correction = math.exp(-0.5 * (kappa * sigma) ** 2)
    for row, distance in enumerate(r):
        if distance == 0:
            continue
        scale = kappa / (2 * distance)
        u = lags / scale
        kernel = (np.exp(1j * kappa * u) - correction) * np.exp(-u * u / (2 * sigma * sigma))
        kernel /= math.sqrt(2 * math.pi) * sigma * math.sqrt(scale)
        conv = np.fft.ifft(spectrum * np.fft.fft(kernel, nfft))
        result[row] = step * conv[n - 1:2 * n - 1]
    return result


def _safe_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", value):
        raise ValueError("Each id must contain 1–80 ASCII letters, digits, underscores or hyphens")
    return value


def _dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def run(config, output, base=Path(".")):
    """Run a batch on common grids and with one shared amplitude normalization."""
    options = validate_options(config)
    output, base = Path(output).resolve(), Path(base).resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise FileExistsError("Choose a new or empty output directory; previous results are preserved")
    entries = config.get("spectra")
    if not isinstance(entries, list) or not entries:
        raise ValueError("spectra must be a nonempty list")
    residual_entries = config.get("residuals", [])
    if not isinstance(residual_entries, list):
        raise ValueError("residuals must be a list")
    ids, source, input_records = set(), {}, []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Each spectrum must be an object")
        unknown = set(entry) - {"id", "file", "k_column", "chi_column", "input_kweight", "role"}
        if unknown:
            raise ValueError("Unknown spectrum configuration keys: " + ", ".join(sorted(unknown)))
        sid = _safe_id(entry.get("id"))
        if sid in ids:
            raise ValueError(f"Duplicate id: {sid}")
        ids.add(sid)
        if not isinstance(entry.get("file"), str) or not entry["file"]:
            raise ValueError(f"{sid}: file is required")
        path = (base / entry["file"]).resolve()
        weight = _number(entry.get("input_kweight", 0), "input_kweight", minimum=0)
        kc, cc = entry.get("k_column", 1), entry.get("chi_column", 2)
        native_k, native_y = read_chi(path, kc, cc, options["max_gap_factor"])
        original_support = [float(native_k[0]), float(native_k[-1])]
        removed_zero = bool(weight > 0 and native_k[0] == 0)
        if weight > 0:
            valid = native_k > 0
            native_k, native_y = native_k[valid], native_y[valid]
            with np.errstate(over="raise", divide="raise", invalid="raise"):
                native_y = native_y / native_k ** weight
        if len(native_k) < 2 or not np.isfinite(native_y).all():
            raise ValueError(f"{sid}: insufficient finite recoverable chi(k)")
        source[sid] = (native_k, native_y)
        input_records.append(dict(id=sid, file=str(path), sha256=sha256(path),
            k_column=kc, chi_column=cc, input_kweight=weight, role=entry.get("role", "spectrum"),
            original_support_Ainv=original_support, usable_support_Ainv=[float(native_k[0]), float(native_k[-1])],
            excluded_weighted_k_zero=removed_zero, original_rows=len(native_k) + int(removed_zero),
            maximum_native_step_Ainv=float(np.max(np.diff(native_k)))))
    residuals = []
    for entry in residual_entries:
        if not isinstance(entry, dict):
            raise ValueError("Each residual must be an object")
        unknown = set(entry) - {"id", "data", "fit"}
        if unknown:
            raise ValueError("Unknown residual configuration keys: " + ", ".join(sorted(unknown)))
        sid = _safe_id(entry.get("id"))
        if sid in ids:
            raise ValueError(f"Duplicate id: {sid}")
        if entry.get("data") not in source or entry.get("fit") not in source:
            raise ValueError(f"{sid}: residual references must name input spectrum ids")
        ids.add(sid)
        residuals.append(dict(id=sid, data=entry["data"], fit=entry["fit"]))
    overlap_min = max(x[0][0] for x in source.values())
    overlap_max = min(x[0][-1] for x in source.values())
    kmin = float(overlap_min if options["kmin"] is None else options["kmin"])
    kmax = float(overlap_max if options["kmax"] is None else options["kmax"])
    if kmax <= kmin or kmin < overlap_min - 1e-10 or kmax > overlap_max + 1e-10:
        raise ValueError("Selected k interval exceeds common usable support; extrapolation and weighted-k0 reconstruction are forbidden")
    k = _axis(kmin, kmax, options["kstep"], "k")
    r = _axis(options["rmin"], options["rmax"], options["rstep"], "R")
    nfft = 1 << (3 * len(k) - 3).bit_length()
    estimated_bytes = (len(ids) * len(k) * len(r) * 32 + len(k) * len(r) * 48
                       + nfft * 96 + len(k) * (len(ids) + 6) * 8)
    if estimated_bytes > options["memory_mb"] * 1024 ** 2:
        raise ValueError(f"Estimated WT memory {estimated_bytes / 1024**2:.1f} MiB exceeds memory_mb={options['memory_mb']}; reduce grids/batch size")
    effective_step = max(options["kstep"], *(x["maximum_native_step_Ainv"] for x in input_records))
    nyquist = math.pi / (2 * effective_step)
    if options["rmax"] >= nyquist:
        raise ValueError(f"rmax reaches/exceeds sampling Nyquist R={nyquist:.6g} A")
    window = hanning_window(k, options["dk"]) if options["window"] == "hanning" else np.ones(len(k))
    signals, coefficients = {}, {}
    for sid, (nk, ny) in source.items():
        # Bounds were checked above; tiny floating errors are clipped, never extrapolated.
        x = np.clip(k, nk[0], nk[-1])
        with np.errstate(over="raise", invalid="raise"):
            signals[sid] = np.interp(x, nk, ny) * k ** options["kweight"] * window
        coefficients[sid] = morlet_transform(k, signals[sid], r, options["kappa"], options["sigma"])
    for entry in residuals:
        signals[entry["id"]] = signals[entry["data"]] - signals[entry["fit"]]
        coefficients[entry["id"]] = morlet_transform(k, signals[entry["id"]], r, options["kappa"], options["sigma"])
    if any(not np.isfinite(value).all() for value in coefficients.values()):
        raise ValueError("Non-finite WT result; inspect amplitudes and parameters")
    maximum = max(float(np.max(np.abs(value))) for value in coefficients.values())
    denominator = maximum if maximum > 0 else 1.0
    margins = np.full(len(r), np.inf)
    nonzero = r > 0
    margins[nonzero] = math.sqrt(2) * options["sigma"] * options["kappa"] / (2 * r[nonzero])
    coi_valid = ((k - k[0])[None, :] >= margins[:, None]) & ((k[-1] - k)[None, :] >= margins[:, None])
    report = dict(schema="exafs-morlet-wt-v1", created_utc=datetime.now(timezone.utc).isoformat(),
        options=options, formula=FORMULA, inputs=input_records, residuals=residuals,
        coordinates=dict(k_Ainv=k.tolist(), R_A=r.tolist(), shape_R_by_k=[len(r), len(k)],
                         selected_interval_Ainv=[kmin, kmax], actual_interval_Ainv=[float(k[0]), float(k[-1])]),
        units=dict(k="A^-1", R="A (apparent, no phase correction)", amplitude="arbitrary units; stated transform normalization"),
        preprocessing=dict(interpolation="linear interpolation of unweighted chi(k), without extrapolation",
            undo_input_weight="divide by k^input_kweight before interpolation; zero-k weighted rows excluded as unrecoverable",
            window_formula="wL=.5*(1-cos(pi*clip((k-k_start)/dk,0,1))); wR=.5*(1-cos(pi*clip((k_end-k)/dk,0,1))); w=wL*wR" if options["window"] == "hanning" else "w=1",
            window_values=window.tolist(), interval="actual uniform grid endpoints; overlapping Hanning ramps are multiplied",
            quadrature="composite trapezoidal rule, endpoints half weighted"),
        normalization=dict(mode="one shared maximum across all input and residual spectra", raw_maximum=maximum, denominator=denominator),
        boundary=dict(note="Finite measured/selected support truncates each wavelet, especially at low R and near k endpoints. FFT padding is computational zero extension, not measured signal. COI is an envelope criterion, not a confidence interval.",
            coi_rule="valid if both distances to selected k endpoints >= sqrt(2)*a*sigma; Gaussian envelope amplitude exp(-1) at this margin",
            coi_margin_Ainv=[None if not math.isfinite(v) else float(v) for v in margins],
            valid_fraction_by_R=np.mean(coi_valid, axis=1).tolist(),
            sampling_nyquist_R_A=nyquist, near_nyquist_warning=bool(options["rmax"] > 0.8 * nyquist)),
        runtime=dict(python=sys.version, numpy=np.__version__, platform=platform.platform(),
                     engine_file=str(Path(__file__).resolve()), engine_sha256=sha256(__file__),
                     algorithm="zero-padded linear FFT convolution per R", fft_length=nfft,
                     estimated_peak_memory_MiB=estimated_bytes / 1024 ** 2),
        origin=dict(row_axis="R_A", column_axis="k_Ainv", z="abs(complex WT)",
                    matrix_format="pure numeric tab-delimited, no header or coordinate row/column", orientation="rows R; columns k"), series=[])
    output.mkdir(parents=True, exist_ok=True)
    for sid, value in coefficients.items():
        folder = output / sid
        folder.mkdir()
        np.savetxt(folder / "WT_matrix.txt", np.abs(value), delimiter="\t", fmt="%.17g")
        np.savetxt(folder / "WT_normalized.txt", np.abs(value) / denominator, delimiter="\t", fmt="%.17g")
        np.savez(folder / "WT_coefficients.npz", k_Ainv=k, R_A=r, coefficients=value,
                 coi_valid=coi_valid, coi_margin_Ainv=margins, preprocessed_signal=signals[sid], window=window)
        hashes = {name: sha256(folder / name) for name in ("WT_matrix.txt", "WT_normalized.txt", "WT_coefficients.npz")}
        report["series"].append(dict(id=sid, directory=sid, role="residual" if sid not in source else next(x["role"] for x in input_records if x["id"] == sid), files=hashes))
    origin_text = ("Origin matrix import (all files are pure numeric TSV; no header)\n"
        "For each spectrum id, import id/WT_matrix.txt as a matrix. Z = |WT|.\n"
        "Columns map to X = k (A^-1); rows map to Y = apparent R (A), without phase correction.\n"
        f"Columns: {len(k)}, X start: {k[0]:.17g}, X end: {k[-1]:.17g}, X step: {options['kstep']:.17g}\n"
        f"Rows: {len(r)}, Y start: {r[0]:.17g}, Y end: {r[-1]:.17g}, Y step: {options['rstep']:.17g}\n"
        "Use a contour/color-fill plot; compare raw matrices with the same color scale.\n"
        "WT_normalized.txt uses one shared maximum across this entire batch, including residuals.\n"
        "Exact coordinates and transform parameters: WT_parameters.json. Complex coefficients/support mask: id/WT_coefficients.npz.\n"
        "Computational zero padding does not extend measured support; inspect the recorded boundary/COI information.\n")
    (output / "ORIGIN_IMPORT.txt").write_text(origin_text, encoding="utf-8")
    report["origin"]["import_instructions_sha256"] = sha256(output / "ORIGIN_IMPORT.txt")
    _dump(output / "WT_parameters.json", report)
    verify_output(output)
    return report


def verify_output(output):
    """Verify exported matrices, orientation, coefficients, coordinates and hashes."""
    output = Path(output)
    report = json.loads((output / "WT_parameters.json").read_text(encoding="utf-8"))
    if report.get("schema") != "exafs-morlet-wt-v1":
        raise ValueError("Unknown WT output schema")
    options = validate_options(report["options"])
    k, r = np.asarray(report["coordinates"]["k_Ainv"], float), np.asarray(report["coordinates"]["R_A"], float)
    shape = (len(r), len(k))
    if list(shape) != report["coordinates"]["shape_R_by_k"] or len(k) < 2 or len(r) < 1:
        raise ValueError("Invalid output coordinate/shape record")
    if not np.isfinite(k).all() or not np.isfinite(r).all() or np.any(k < 0) or np.any(r < 0):
        raise ValueError("Non-finite/negative coordinates")
    if not np.allclose(np.diff(k), options["kstep"], rtol=1e-9, atol=1e-12) or not np.allclose(np.diff(r), options["rstep"], rtol=1e-9, atol=1e-12):
        raise ValueError("Coordinates disagree with configured spacing")
    if report["origin"]["orientation"] != "rows R; columns k" or report["origin"]["row_axis"] != "R_A" or report["origin"]["column_axis"] != "k_Ainv":
        raise ValueError("Origin axis mapping is inconsistent")
    if sha256(output / "ORIGIN_IMPORT.txt") != report["origin"]["import_instructions_sha256"]:
        raise ValueError("Origin instructions hash mismatch")
    denominator = _number(report["normalization"]["denominator"], "normalization denominator", positive=True)
    maximum, seen, coefficients = 0.0, set(), {}
    for item in report["series"]:
        sid = _safe_id(item["id"])
        if sid in seen or item["directory"] != sid:
            raise ValueError("Invalid/duplicate series directory")
        seen.add(sid)
        folder = output / sid
        if set(item["files"]) != {"WT_matrix.txt", "WT_normalized.txt", "WT_coefficients.npz"}:
            raise ValueError("Unexpected/missing WT output files")
        for name, expected in item["files"].items():
            if sha256(folder / name) != expected:
                raise ValueError(f"{sid}/{name}: hash mismatch")
        raw = np.loadtxt(folder / "WT_matrix.txt", delimiter="\t", ndmin=2)
        normalized = np.loadtxt(folder / "WT_normalized.txt", delimiter="\t", ndmin=2)
        with np.load(folder / "WT_coefficients.npz", allow_pickle=False) as data:
            value = data["coefficients"]
            if value.shape != shape or raw.shape != shape or normalized.shape != shape or not np.isfinite(value).all():
                raise ValueError(f"{sid}: invalid matrix shape or coefficients")
            if not np.array_equal(data["k_Ainv"], k) or not np.array_equal(data["R_A"], r):
                raise ValueError(f"{sid}: coefficient coordinates disagree")
            if data["coi_valid"].shape != shape or data["preprocessed_signal"].shape != k.shape:
                raise ValueError(f"{sid}: support/signal shape mismatch")
            if not np.isfinite(data["preprocessed_signal"]).all() or not np.isfinite(data["window"]).all():
                raise ValueError(f"{sid}: invalid preprocessed arrays")
            coefficients[sid] = value
        if not np.isfinite(raw).all() or not np.isfinite(normalized).all() or not np.allclose(raw, np.abs(value), rtol=2e-14, atol=1e-14) or not np.allclose(normalized, raw / denominator, rtol=2e-14, atol=1e-14):
            raise ValueError(f"{sid}: numeric export disagrees with coefficients/normalization")
        if np.any(r == 0) and not np.all(value[r == 0] == 0):
            raise ValueError(f"{sid}: R=0 row violates the zero convention")
        maximum = max(maximum, float(np.max(raw)))
    if not seen or not math.isclose(maximum, report["normalization"]["raw_maximum"], rel_tol=2e-14, abs_tol=1e-14) or denominator != (maximum if maximum > 0 else 1.0):
        raise ValueError("Shared normalization maximum is inconsistent")
    for residual in report["residuals"]:
        if not np.allclose(coefficients[residual["id"]], coefficients[residual["data"]] - coefficients[residual["fit"]], rtol=1e-10, atol=1e-11 * max(1, maximum)):
            raise ValueError("Complex residual is inconsistent with WT(data-fit)")
    return dict(status="pass", series_count=len(seen), shape_R_by_k=list(shape), output=str(output.resolve()))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "verify":
        parser = argparse.ArgumentParser(description="Verify a numeric EXAFS WT output directory")
        parser.add_argument("output", type=Path)
        args = parser.parse_args(argv[1:])
        result = verify_output(args.output)
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("input", nargs="?", type=Path)
        parser.add_argument("--config", type=Path)
        parser.add_argument("--out", type=Path, required=True)
        parser.add_argument("--id", default="spectrum")
        parser.add_argument("--k-column", type=int, default=1)
        parser.add_argument("--chi-column", type=int, default=2)
        parser.add_argument("--input-kweight", type=float, default=0)
        for key, default in DEFAULTS.items():
            if key == "method":
                continue
            parser.add_argument("--" + key.replace("_", "-"), type=str if isinstance(default, str) else float, default=default)
        parser.add_argument("--kmin", type=float)
        parser.add_argument("--kmax", type=float)
        args = parser.parse_args(argv)
        if bool(args.config) == bool(args.input):
            parser.error("Supply exactly one positional input or --config")
        if args.config:
            explicit_flags = {token.split("=", 1)[0] for token in argv if token.startswith("--")}
            conflicts = explicit_flags - {"--config", "--out"}
            if conflicts:
                parser.error("With --config, put all scientific/input options in that file; conflicting flags: " + ", ".join(sorted(conflicts)))
            config = json.loads(args.config.read_text(encoding="utf-8-sig"))
            base = args.config.resolve().parent
        else:
            config = {k: getattr(args, k) for k in DEFAULTS if k != "method"}
            config.update(kmin=args.kmin, kmax=args.kmax, spectra=[dict(id=args.id, file=str(args.input.resolve()),
                k_column=args.k_column, chi_column=args.chi_column, input_kweight=args.input_kweight)])
            base = Path(".")
        report = run(config, args.out, base)
        result = dict(status="pass", output=str(args.out.resolve()), series_count=len(report["series"]), shape_R_by_k=report["coordinates"]["shape_R_by_k"])
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, FloatingPointError) as exc:
        print(f"EXAFS WT failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
