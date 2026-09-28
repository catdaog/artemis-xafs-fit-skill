#!/usr/bin/env python3
"""List foil derivative candidates and apply a user-reviewed energy shift."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re


def split_fields(line: str) -> list[str]:
    return [x for x in re.split(r"[\s,]+", line.strip()) if x]


def moving_average(values: list[float], width: int) -> list[float]:
    radius = width // 2
    out = []
    for i in range(len(values)):
        lo, hi = max(0, i - radius), min(len(values), i + radius + 1)
        out.append(sum(values[lo:hi]) / (hi - lo))
    return out


def derivative(x: list[float], y: list[float]) -> list[float]:
    d = [0.0] * len(x)
    for i in range(1, len(x) - 1):
        dx = x[i + 1] - x[i - 1]
        d[i] = (y[i + 1] - y[i - 1]) / dx if dx else 0.0
    if len(x) > 1:
        d[0], d[-1] = d[1], d[-2]
    return d


def peak_candidates(x: list[float], d: list[float], lo: float, hi: float,
                    fraction: float, min_separation: float) -> list[dict]:
    raw = []
    local_max = max((v for xx, v in zip(x, d) if lo <= xx <= hi), default=0.0)
    threshold = max(0.0, local_max * fraction)
    for i in range(1, len(x) - 1):
        if lo <= x[i] <= hi and d[i] > threshold and d[i] >= d[i - 1] and d[i] > d[i + 1]:
            raw.append({"index": i, "energy": x[i], "derivative": d[i]})
    kept: list[dict] = []
    for item in sorted(raw, key=lambda z: z["derivative"], reverse=True):
        if all(abs(item["energy"] - old["energy"]) >= min_separation for old in kept):
            kept.append(item)
    kept.sort(key=lambda z: z["energy"])
    for rank, item in enumerate(kept, 1):
        item["energy_order"] = rank
    return kept


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("input", type=Path)
    p.add_argument("--energy-col", type=int, default=1, help="1-based column")
    p.add_argument("--mu-col", type=int, default=2, help="1-based column")
    p.add_argument("--reference-energy", type=float, required=True)
    p.add_argument("--window", nargs=2, type=float, metavar=("MIN", "MAX"), required=True)
    p.add_argument("--smooth-points", type=int, default=3)
    p.add_argument("--min-height-fraction", type=float, default=0.08)
    p.add_argument("--min-separation-ev", type=float, default=1.0)
    p.add_argument("--candidates", type=Path)
    p.add_argument("--observed-energy", type=float,
                   help="Feature selected after visual review; omit to list candidates only")
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    if args.smooth_points < 1 or args.smooth_points % 2 == 0:
        raise SystemExit("--smooth-points must be a positive odd integer")
    e_col, mu_col = args.energy_col - 1, args.mu_col - 1
    lines = args.input.read_text(encoding="utf-8", errors="replace").splitlines()
    parsed: list[tuple[int, list[str]]] = []
    energies, mus = [], []
    for line_no, line in enumerate(lines):
        if not line.strip() or line.lstrip().startswith(("#", ";", "!")):
            continue
        fields = split_fields(line)
        if max(e_col, mu_col) >= len(fields):
            continue
        try:
            energy, mu = float(fields[e_col]), float(fields[mu_col])
        except ValueError:
            continue
        parsed.append((line_no, fields))
        energies.append(energy)
        mus.append(mu)
    if len(energies) < 7:
        raise SystemExit("not enough numeric rows")
    if any(b <= a for a, b in zip(energies, energies[1:])):
        raise SystemExit("energy column must be strictly increasing")

    deriv = derivative(energies, moving_average(mus, args.smooth_points))
    candidates = peak_candidates(energies, deriv, args.window[0], args.window[1],
                                 args.min_height_fraction, args.min_separation_ev)
    if args.candidates:
        args.candidates.parent.mkdir(parents=True, exist_ok=True)
        with args.candidates.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=("energy_order", "energy", "derivative", "index"))
            writer.writeheader()
            writer.writerows(candidates)

    report = {
        "input": str(args.input.resolve()),
        "reference_energy": args.reference_energy,
        "window": args.window,
        "candidates": candidates,
    }
    if args.observed_energy is None:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    if not args.output:
        raise SystemExit("--output is required when --observed-energy is supplied")

    shift = args.reference_energy - args.observed_energy
    row_by_line = {line_no: fields for line_no, fields in parsed}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"# energy calibration: observed={args.observed_energy:.9g} eV; "
                 f"reference={args.reference_energy:.9g} eV; shift={shift:+.9g} eV\n")
        for line_no, line in enumerate(lines):
            fields = row_by_line.get(line_no)
            if fields is None:
                fh.write(line + "\n")
                continue
            updated = list(fields)
            updated[e_col] = f"{float(fields[e_col]) + shift:.10g}"
            fh.write("\t".join(updated) + "\n")
    report.update({"observed_energy": args.observed_energy, "shift": shift,
                   "output": str(args.output.resolve()), "numeric_rows": len(parsed)})
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
