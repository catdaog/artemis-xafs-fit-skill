#!/usr/bin/env python3
"""Audit a Demeter/Artemis fit log for common physical/statistical failures."""

from __future__ import annotations

import argparse
import json
import math
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
    p.add_argument("--s02-tolerance", type=float, default=5.1e-4,
                   help="Rounded path amplitude tolerance; use expected-s02 only for fixed unit-amplitude paths")
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

    in_paths = False
    malformed = []
    paths_closed = False
    for line in text.splitlines():
        if re.search(r"\bname\s+N\s+S02\s+sigma", line, re.I):
            in_paths = True
            continue
        if in_paths and re.search(r"\bname\s+ei\s+third", line, re.I):
            in_paths = False
            paths_closed = True
        if not in_paths:
            continue
        m = re.search(rf"(.+?)\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})\s+({NUMBER})\s*$", line)
        if not m:
            if line.strip() and not re.fullmatch(r'[=\-\s]+', line):
                malformed.append(line.strip())
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

    missing = [key for key in ("nind", "nvar", "r_factor", "chi_square", "reduced_chi_square")
               if result[key] is None or not math.isfinite(result[key])]
    if not result["paths"]:
        missing.append("paths")
    if malformed or not paths_closed:
        missing.append("complete parseable path table")
    if not re.search(r"Correlations between variables|All other correlations", text, re.I):
        missing.append("correlation section")
    result["missing_fields"] = missing
    if re.search(r"\b(?:nan|inf|infinity)\b|fatal error|fit failed|failed to converge", text, re.I):
        result["flags"].append("non-finite value or execution failure in log")
    nind, nvar = result["nind"], result["nvar"]
    if nind is not None and nind <= 0:
        result["flags"].append("nonpositive independent point count")
    if nvar is not None and (nvar < 0 or not nvar.is_integer()):
        result["flags"].append("invalid variable count")
    if nind is not None and nvar is not None and nvar >= nind:
        result["flags"].append(f"Nvar ({nvar:g}) is not smaller than Nind ({nind:g})")
    for path in result["paths"]:
        if path["n"] <= 0 or path["s02"] <= 0:
            result["flags"].append(f"nonpositive degeneracy/amplitude on {path['name']}")
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
    result["status"] = "incomplete" if missing else ("fail" if result["flags"] else "pass")
    result["scope"] = "log checks only; not scientific acceptance"
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 3 if missing else (2 if result["flags"] else 0)


if __name__ == "__main__":
    raise SystemExit(main())
