# Artemis XAFS Fit Skill

A reusable Codex skill for an evidence-traceable XAFS workflow:

1. calibrate a simultaneously measured foil or accepted standard in Athena;
2. determine `S0²` from a known-coordination standard at the same absorber edge;
3. download and validate experimental CIFs with provenance;
4. generate/inspect FEFF paths and fit staged shell models through Demeter/Artemis;
5. reject physically invalid or statistically unidentifiable fits;
6. export a rerunnable project, logs, numerical curves, and model comparison.

It also includes a compact EXAFS theory reference and a transmission-sample preparation guide covering absorber loading, pellet/diluent mass, total optical thickness, and edge-step calculation.

The skill covers multiple absorber elements and edges. It includes the historical Teo–Lee `k^n` heuristic based on the dominant **backscatterer** atomic number, plus modern multi-k validation:

- `Zscatterer < 36`: `k³`
- `36 < Zscatterer < 57`: `k²`
- `Zscatterer > 57`: `k¹`

For mixed shells, the workflow recommends testing k weights 1, 2, and 3 simultaneously rather than relying on a single absorber-based weight.

## Install

Copy this folder to:

```text
~/.codex/skills/artemis-xafs-fit-skill
```

Then invoke it with `$artemis-xafs-fit-skill` or let Codex select it for Artemis/EXAFS fitting tasks.

## Included helpers

- `fetch_reference.py` — COD/direct CIF or XAS download, validation, SHA256, provenance sidecar.
- `foil_calibrate.py` — derivative candidate listing and reviewed energy-shift application.
- `suggest_xafs_settings.py` — absorber/edge, standard structure/CN, and scatterer-aware k-weight suggestions.
- `run_demeter.ps1` — isolated Windows Demeter/FEFF runtime wrapper.
- `demeter_first_shell_fit.pl` — fixed-`S0²`, explicit-path first-shell fit driver.
- `audit_fit_log.py` — checks negative `σ²`, extreme shifts, excessive correlations, S0² mismatch, and parameter count.

## Official software and mass calculators

- [Demeter](https://bruceravel.github.io/demeter/) — official Athena, Artemis, and Hephaestus download/documentation page.
- [FEFF](https://feff.phys.washington.edu/feffproject-feff-download.html) — official FEFF download page, including free EXAFS-focused lite builds.
- [XAFSmass](https://xafsmass.readthedocs.io/) — calculates XAFS powder mass, thickness, gas pressure, and expected edge step; [source](https://github.com/kklmn/XAFSmass) and [PyPI](https://pypi.org/project/XAFSmass/).
- [CatMass](https://web.slac.stanford.edu/coaccess/resources/software) — suited to supported catalysts, diluents, complex compositions, and competing edges; [source](https://github.com/ahoffm02/catMass).
- [CLS X-Mass](https://xasdb.lightsource.ca/xafsmass) — browser-based sample/diluent mass and target-edge-step calculator.

Read `references/software-and-sample-preparation.md` before reusing a sample:BN ratio. The skill distinguishes active-metal loading, absorber mass fraction, catalyst powder mass, diluent mass, total optical thickness, and measured edge step.

## Basic principles added

`references/basic-principles.md` summarizes the EXAFS equation, `N`–`S0²` and `Delta E0`–`Delta R` correlations, phase-shifted Fourier-transform peaks, `R = Reff + Delta R`, radial resolution, the independent-point limit, FEFF path selection, and minimum physical fit checks.

Read `SKILL.md` for the routing instructions and `references/` for the scientific workflow and source policy.

## Scientific note

The Teo–Lee rule is a historical starting heuristic, not a substitute for data inspection. Source: B.-K. Teo and P. A. Lee, *J. Am. Chem. Soc.* **101** (1979) 2815–2832, [DOI: 10.1021/ja00505a003](https://doi.org/10.1021/ja00505a003).
