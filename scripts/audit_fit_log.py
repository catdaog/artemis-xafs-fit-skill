#!/usr/bin/env python3
"""Audit a Demeter/Artemis fit log for common physical/statistical failures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"


def scalar(text: str, label: str):
    m = re.search(rf"(?mi)^\s*{re.escape(label)}\s*:\s*({NUMBER})", text)
    return float(m.group(1)) if m else None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("log", type=Path)
    p.add_argument("--expected-s02", type=float)
    p.add_argument("--s02-tolerance", type=float, default=1e-6)
    p.add_argument("--max-correlation", type=float, default=0.95)
    p.add_argument("--max-abs-delr", type=float, default=0.10)
    p.add_argument("--max-abs-e0", type=float, default=10.0)
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    text = args.log.read_text(encoding="utf-8", errors="replace")
    result = {
        "log": str(args.log.resolve()),
        "nind": scalar(text, "Independent points"),
        "nvar": scalar(text, "Number of variables"),
        "r_factor": scalar(text, "R-factor"),
        "chi_square": scalar(text, "Chi-square"),
        "reduced_chi_square": scalar(text, "Reduced chi-square"),
        "paths": [],
        "correlations": [],
        "flags": [],
    }

    for line in text.splitlines():
        m = re.search(rf"(.+?)\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})\s*$", line)
        if not m:
            continue
        name = m.group(1).strip()
        if name.lower().startswith(("name", "=")):
            continue
        vals = [float(m.group(i)) for i in range(2, 9)]
        path = dict(name=name, n=vals[0], s02=vals[1], sigma2=vals[2],
                    e0=vals[3], delr=vals[4], reff=vals[5], r=vals[6])
        result["paths"].append(path)
    for a, b, value in re.findall(rf"(?m)^\s*(\S+)\s*&\s*(\S+)\s*-->\s*({NUMBER})", text):
        result["correlations"].append({"a": a, "b": b, "value": float(value)})

    nind, nvar = result["nind"], result["nvar"]
    if nind is not None and nvar is not None and nvar >= nind:
        result["flags"].append(f"Nvar ({nvar:g}) is not smaller than Nind ({nind:g})")
    for path in result["paths"]:
        if path["sigma2"] < 0:
            result["flags"].append(f"negative sigma2 on {path['name']}: {path['sigma2']:.6g}")
        if abs(path["delr"]) > args.max_abs_delr:
            result["flags"].append(f"large |delr| on {path['name']}: {path['delr']:.6g} A")
        if abs(path["e0"]) > args.max_abs_e0:
            result["flags"].append(f"large |e0| on {path['name']}: {path['e0']:.6g} eV")
        if args.expected_s02 is not None and abs(path["s02"] - args.expected_s02) > args.s02_tolerance:
            result["flags"].append(
                f"S02 mismatch on {path['name']}: {path['s02']:.6g} != {args.expected_s02:.6g}")
    for corr in result["correlations"]:
        if abs(corr["value"]) > args.max_correlation:
            result["flags"].append(
                f"high correlation {corr['a']}/{corr['b']}: {corr['value']:.4f}")

    result["path_degeneracy_sum"] = sum(p["n"] for p in result["paths"])
    result["status"] = "fail" if result["flags"] else "pass"
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 2 if result["flags"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
