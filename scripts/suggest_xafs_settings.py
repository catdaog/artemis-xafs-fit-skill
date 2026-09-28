#!/usr/bin/env python3
"""Suggest element-aware XAFS starting settings without replacing data inspection."""

from __future__ import annotations

import argparse
import json


SYMBOLS = """H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og""".split()
Z_BY_SYMBOL = {symbol: z for z, symbol in enumerate(SYMBOLS, 1)}

FCC = set("Al Ni Cu Rh Pd Ag Ir Pt Au Pb".split())
BCC = set("V Cr Fe Nb Mo Ta W".split())
HCP = set("Be Mg Ti Co Zn Zr Ru Cd Hf Re Os".split())


def normalize_symbol(value: str) -> str:
    value = value.strip()
    symbol = value[:1].upper() + value[1:].lower()
    if symbol not in Z_BY_SYMBOL:
        raise ValueError(f"unknown element symbol: {value}")
    return symbol


def teo_lee_weight(z: int):
    if z < 36:
        return 3
    if 36 < z < 57:
        return 2
    if z > 57:
        return 1
    return None


def foil_model(symbol: str) -> dict:
    if symbol in FCC:
        return {"structure": "fcc", "nominal_first_shell_cn": 12}
    if symbol in BCC:
        note = "alpha-Fe at ambient conditions" if symbol == "Fe" else None
        return {"structure": "bcc", "nominal_first_shell_cn": 8, "note": note}
    if symbol in HCP:
        return {"structure": "hcp", "nominal_first_shell_cn": 12,
                "note": "nominal CN; non-ideal c/a can split first-shell distances"}
    return {"structure": None, "nominal_first_shell_cn": None,
            "note": "download and verify the ambient experimental structure; do not assume fcc/bcc/hcp"}


def edge_note(z: int) -> str:
    if z <= 50:
        return "K edge is commonly used when accessible; verify beamline range and calibration convention."
    if z <= 71:
        return "K or L3 may be practical depending on beamline energy and scientific target; derive S0^2 at the same edge."
    return "L3 is commonly used for heavy metals/lanthanides; K edges may require a high-energy beamline."


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--absorber", required=True)
    p.add_argument("--scatterers", help="Comma-separated dominant neighboring elements; defaults to absorber for a foil")
    p.add_argument("--edge", help="Requested edge label, e.g. K or L3")
    args = p.parse_args()

    absorber = normalize_symbol(args.absorber)
    scatterers = ([normalize_symbol(x) for x in args.scatterers.split(",")]
                  if args.scatterers else [absorber])
    scatterer_rows = []
    for symbol in scatterers:
        z = Z_BY_SYMBOL[symbol]
        weight = teo_lee_weight(z)
        scatterer_rows.append({
            "element": symbol,
            "Z": z,
            "teo_lee_primary_k_weight": weight,
            "note": None if weight else "boundary Z=36 or Z=57; inspect amplitude and use multi-k checks",
        })
    report = {
        "absorber": absorber,
        "absorber_Z": Z_BY_SYMBOL[absorber],
        "edge": args.edge,
        "edge_guidance": edge_note(Z_BY_SYMBOL[absorber]),
        "scatterers": scatterer_rows,
        "recommended_quantitative_fit_weights": [1, 2, 3],
        "weighting_basis": "dominant backscatterer Z, not absorber Z unless they are the same element",
        "elemental_standard_starting_model": foil_model(absorber),
        "warnings": [
            "Verify the experimental foil/standard phase and first-shell splitting from a cited structure.",
            "Use the same absorber edge for S0^2 calibration and sample fitting.",
            "Treat the Teo-Lee rule as a starting heuristic; inspect data quality and parameter stability.",
        ],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
