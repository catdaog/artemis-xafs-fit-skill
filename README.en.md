# XAFS Fit Skill · EXAFS + XANES + Wavelets

[![test](https://github.com/catdaog/artemis-xafs-fit-skill/actions/workflows/test.yml/badge.svg)](https://github.com/catdaog/artemis-xafs-fit-skill/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[中文](README.md) · [English](README.en.md) · [Deutsch](README.de.md) · [日本語](README.ja.md) · [Français](README.fr.md)

**One skill for quantitative EXAFS fitting, XANES structural refinement, and Morlet EXAFS wavelet matrices ready for Origin.**

`artemis-xafs-fit-skill` runs real local calculation engines and preserves source data, structure provenance, inputs, outputs and fit records. Use either branch independently, or combine their evidence to assess the same candidate structure.

The wavelet branch defaults to κ=10 and σ=1. Transform existing χ(k) independently, or compare experiment, fit and residual after EXAFS fitting. Outputs include numeric amplitude matrices (columns k, rows R), coordinate mappings, parameters and complex coefficients. See the [wavelet guide](references/wavelet.md) for the exact convention.

## Choose a fitting workflow

| Item | EXAFS fitting | XANES near-edge fitting |
|---|---|---|
| Main question | Coordination numbers, bond lengths, Debye–Waller factors and scattering paths | Whether candidate coordination geometries and near-edge spectral shapes agree with the data |
| Engine | Athena / Artemis / Demeter + FEFF | FDMNES: Green multiple scattering or finite differences |
| Core inputs | Numerical spectra or unweighted χ(k), processing settings, a same-edge standard and a structure/FEFF model | Energy–absorption data, calibration/normalization records and candidate atomic structures |
| Workflow | Determine S₀² from a standard → validate paths → staged fitting → review parameters | Build clusters → check convergence → align spectra → refine a few geometry parameters → compare multiple starts |
| Outputs | Reloadable DPJ, k1/k2/k3 and R1/R2/R3 tables, parameters and workflow record | Data/calculation/residual tables, parameters and model comparison, PNG/SVG, structures, inputs and logs |
| Details | [EXAFS guide](references/exafs-guide.en.md) | [XANES / FDMNES guide](references/xanes-fdmnes.md) |

**XANES has its own workflow and deliverables; EXAFS S₀² calibration, k/R windows and a DPJ are not prerequisites.** Reference-spectrum linear-combination fitting (LCF) is a different method and is not implemented by this XANES branch.

## Quick invocation

**EXAFS:**

```text
Use $artemis-xafs-fit-skill to fit my EXAFS data. Determine S₀² from a same-edge standard with known coordination, fit the sample, and deliver a reloadable DPJ, numerical k/R tables, parameters and a workflow record.
```

**XANES:**

```text
Use $artemis-xafs-fit-skill for FDMNES near-edge calculations and structural refinement of my single-atom sample. Build candidate models from composition and existing EXAFS evidence, check convergence, compare multiple starts, and deliver overlays, residuals and reproducible files.
```

**EXAFS wavelets:**

```text
Use $artemis-xafs-fit-skill for Morlet transforms of these χ(k) spectra, κ=10 and σ=1, with a common k interval, weight and color scale. Deliver Origin-ready matrices, axes, parameters and raw amplitudes, saving normalized matrices separately. If an actual fit spectrum exists, also transform the experiment-minus-fit residual.
```

## What to provide

- For both: absorber/edge, sample-to-file mapping, measurement conditions, column definitions, energy-calibration basis and numerical spectra; preserve repeated scans.
- EXAFS: preferably a same-edge standard, Athena `.prj`, unweighted χ(k) with processing settings, and CIF/FEFF files. For an existing fit, add the `.fpj`/`.dpj` and logs.
- XANES: normalized μ(E), or μ(E) with suitable normalization windows. Raw detector counts first need conversion for the measurement mode. Use a CIF or explicit coordinates, and label hypothetical structures as candidates.
- Wavelets: numerical χ(k), column definitions, preprocessing records and any existing k weighting. A standalone transform does not require a standard, S₀² calibration or a DPJ.

Screenshots help explain a problem; actual fitting needs numerical data. If no structure file exists, candidate models can first be built from composition and independent evidence.

## Installation and execution

Download a [release](https://github.com/catdaog/artemis-xafs-fit-skill/releases) or clone the repository. Place the folder, named `artemis-xafs-fit-skill`, in your skills directory, for example `~/.codex/skills/`. From that folder, install dependencies in the Python environment you will use:

```shell
python -m pip install -r requirements.txt -r requirements-xanes.txt
```

EXAFS needs a separate [Demeter](https://bruceravel.github.io/demeter/) / [FEFF](https://feff.phys.washington.edu/feffproject-feff-download.html) installation. Obtain XANES binaries from the [official FDMNES distribution](https://fdmnes.neel.cnrs.fr/download/). These external programs are not bundled. On Windows:

```powershell
.\scripts\run_xanes.ps1 -Mode install -Archive C:\path\fdmnes.zip
.\scripts\run_xanes.ps1 -Mode probe
.\scripts\run_xanes.ps1 -Mode simulate -Config examples\xanes\fe-n4.json -Output C:\work\xanes_sim
.\scripts\run_xanes.ps1 -Mode fit -Config C:\work\xanes.json -Output C:\work\xanes_fit
```

Alternatively, set `FDMNES_EXE` to an existing executable. See the XANES guide for configuration and commands. These language pages translate the instructions; program arguments and filenames stay the same.

The wavelet branch requires only NumPy, without a Demeter, FDMNES or Origin runtime:

```shell
python -m pip install -r requirements-wavelet.txt
python scripts/exafs_wavelet.py chi_k.dat --out work/wt_sample --kmin 3 --kmax 12 --kweight 2
python scripts/exafs_wavelet.py verify work/wt_sample
```

For batch comparisons, use `--config examples/wavelet.template.json --out work/wt_comparison` after replacing its paths and ranges. Existing k1/k2/k3 fit exports are already weighted: declare `input_kweight` to prevent repeated weighting. The default 10/1 parameters refer to the guide's explicit Morlet formula, not PyWavelets' `cmor10-1`.

## Results and validation

v1.4.0 passed 23 local tests, including real FDMNES synthetic-spectrum recovery and a finite-difference calculation. GitHub CI runs the tests that require no external engine. Synthetic recovery verifies software execution and parameter recovery, not an actual catalyst structure.

v1.5.0 adds Morlet calculation, Origin matrix exports and numerical readback verification. Raw amplitude and shared-maximum-normalized matrices are saved separately. R is an apparent coordinate without scattering-phase correction, and the package records boundary influence. Wavelet maxima alone do not identify an element, determine CN or establish bonding, and do not add independent EXAFS observations.

Simulation, spectral alignment and structural fitting are labelled separately. Numerical convergence still requires review of residuals, correlations, bounds and starting-point dependence. XANES agreement alone does not establish single-atom dispersion or a unique structure.

## Documentation and examples

- [Detailed EXAFS guide](references/exafs-guide.en.md)
- [XANES / FDMNES workflow](references/xanes-fdmnes.md)
- [Morlet wavelets and Origin matrices](references/wavelet.md)
- [Wavelet batch-configuration template](examples/wavelet.template.json)
- [EXAFS batch-workflow template](examples/pipeline.template.json)
- [XANES configuration: illustrative five-atom model](examples/xanes/fe-n4.json)
- [Skill entry point and constraints](SKILL.md)
- [Changelog](CHANGELOG.md)

License: the skill source uses [MIT](LICENSE); external calculation engines retain their own licenses.

[中文](README.md) · [English](README.en.md) · [Deutsch](README.de.md) · [日本語](README.ja.md) · [Français](README.fr.md)
