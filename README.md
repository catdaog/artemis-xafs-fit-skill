# Artemis XAFS Fit Skill

A reusable Codex skill for an evidence-traceable XAFS workflow:

1. calibrate a simultaneously measured foil or accepted standard in Athena;
2. determine `S0²` from a known-coordination standard at the same absorber edge;
3. download and validate experimental CIFs with provenance;
4. generate/inspect FEFF paths and fit staged shell models through Demeter/Artemis;
5. reject physically invalid or statistically unidentifiable fits;
6. export untouched raw inputs, processed χ(k), k¹/k²/k³ fit tables, complex R-space fit tables, parameter tables, projects, logs, audits, and hashes;
7. verify the final delivery package before reporting results.

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
- `build_xafs_delivery.py` — builds and verifies the complete raw/k-space/R-space/parameter/project delivery package.

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

## Required numerical output

An executed fit is not complete until it includes files for:

- untouched raw energy-space inputs;
- processed `χ(k)` with k¹/k²/k³ columns;
- k¹/k²/k³ data, fit, residual, and window values;
- R-space magnitude, real, and imaginary data/fit/residual values;
- machine-readable and Markdown fit-parameter tables;
- fit statistics, DPJ/FPJ, log, CIF, FEFF input, audit, and SHA256 manifest where applicable.

See [`references/deliverables.md`](references/deliverables.md) for the exact schema and build command. The packager never overwrites an existing destination.

## Validation

Run the standard-library tests with:

```text
python -m unittest discover -s tests -v
```

For a completed fit package:

```text
python scripts/build_xafs_delivery.py verify --package <delivery-directory>
```

## Scientific note

The Teo–Lee rule is a historical starting heuristic, not a substitute for data inspection. Source: B.-K. Teo and P. A. Lee, *J. Am. Chem. Soc.* **101** (1979) 2815–2832, [DOI: 10.1021/ja00505a003](https://doi.org/10.1021/ja00505a003).

## License

MIT. See [`LICENSE`](LICENSE).
