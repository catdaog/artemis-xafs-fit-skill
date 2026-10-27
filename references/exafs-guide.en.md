# Detailed EXAFS guide

[Home](../README.en.md) · [中文](exafs-guide.zh-CN.md) · [XANES/FDMNES guide](xanes-fdmnes.md)

This page preserves the detailed EXAFS input, workflow, parameter and delivery instructions. Use the separate XANES branch for near-edge refinement.

## Overview

`artemis-xafs-fit-skill` is a reproducible Codex workflow for XAFS/EXAFS analysis. It covers:

- Athena energy calibration, normalization, and background removal;
- same-absorber, same-edge `S0²` determination from a known-coordination standard;
- acquisition, provenance recording, and validation of experimental CIFs;
- FEFF path generation and checks of absorber, `ipot`, degeneracy, and scattering sequence;
- staged Artemis/Demeter EXAFS fitting;
- auditing of CN, `ΔE0`, `ΔR`, `σ²`, independent points, and parameter correlations;
- a default nine-file delivery: DPJ, k1/k2/k3, R1/R2/R3, one parameter table, and one workflow TXT;
- automatic verification of numerical grids, residuals, and derived-parameter arithmetic, with an optional extended audit package.

The goal is not merely to produce an attractive fit plot. The skill builds a traceable, rerunnable, and auditable evidence chain:

```text
raw data → energy calibration → Athena processing → standard S0² → CIF/FEFF
         → first shell → higher shells/multiple scattering → robustness tests
         → numerical k/R exports → parameter audit → verified delivery package
```

## Scope

Use this skill for:

- elemental foils and known-coordination compound standards;
- common K-edge, L-edge, and related XAFS/EXAFS measurements;
- Athena, Artemis, Demeter, and FEFF workflows;
- coordination-number, bond-distance, disorder, and multi-shell fitting;
- projects that require downloadable raw, fitted, and tabulated numerical files;
- automated Windows Demeter 0.9.26 execution and export.

Do not use it to:

- perform reference-spectrum linear-combination fitting (LCF); use the separate XANES guide for theoretical near-edge calculations and structural refinement;
- fabricate fitted data when raw spectra, FEFF paths, or an executed fit are missing;
- treat a low R-factor as a substitute for physical validity, identifiability, and residual inspection;
- label theoretical, simulated, reconstructed, or unexecuted output as an experimental fit.

## What to upload before fitting

The safest rule is: **raw scans provide traceability, an Athena project reproduces data processing, an Artemis project reproduces the fit, and CIF/FEFF files reproduce the structural model.** When possible, place the items below in one `.zip` archive. Do not upload fit screenshots as the only input.

### Minimum package for each use case

| Use case | Required | Strongly recommended | Consequence if missing |
|---|---|---|---|
| Start a complete fit from raw data | sample raw scans, same-edge reference foil/standard, column definitions and experiment metadata, candidate CIF | Athena `.prj` if processing has begun, every repeat scan, beamline notes | without a same-edge standard, energy calibration and `S0²`/absolute CN are less secure |
| Processing is complete in Athena | Athena `.prj`, candidate CIF | raw scans, reference foil/standard, Athena-exported unweighted `χ(k)` | a `.prj` alone supports most processing checks, but not a full audit of acquisition and every calibration issue |
| Continue an existing Artemis fit | Artemis `.fpj` or `.dpj`, `fit.log`, matching CIF/FEFF directory | Athena `.prj`, raw scans, current parameter table, identification of the intended fit snapshot | without FEFF paths or the project, path selection, constraints, and correlations cannot be recovered reliably |
| Only Athena exports are available | numerical unweighted `k, χ(k)`, Athena processing settings, candidate CIF/FEFF model | normalized `μ(E)`, numerical `χ(R)`, provenance and license | energy calibration, merging, normalization, and AUTOBK cannot be fully re-audited |
| Analyze published or external data | downloadable numerical data, source/DOI, sample and measurement conditions | author project files, CIF, license or reuse statement | a paper figure alone permits only qualitative assessment, not a reproducible quantitative fit |

### 1. Raw spectra: preferred formats

Use this order of preference:

1. **`.xdi`: preferred.** It commonly preserves energy, detector columns, units, and experimental metadata in one machine-readable file.
2. **Beamline-native `.txt`, `.dat`, or `.csv`: fully acceptable.** Keep the original header, every row, row order, delimiter, and unit. Do not manually resample, delete points, smooth the spectrum, or reduce numerical precision.
3. **Athena `.prj`: strongly recommended, but preferably together with raw scans.** It helps reproduce calibration, merging, normalization, and background removal, but it does not always replace untouched beamline files.
4. **`.xlsx`: acceptable only when the original text file is unavailable.** Every column must have a unique name and unit; merged cells, values read from a chart, and hidden manual formulas must not be the sole data source.

At minimum, the raw file should contain:

| Measurement mode | Minimum columns | Recommended additions |
|---|---|---|
| Transmission | `energy_eV`, `I0`, `It` | `Iref` or foil channel, ion-chamber definitions, gain-change records |
| Fluorescence | `energy_eV`, `I0`, `If`, or individual detector channels | `Iref`, dead-time correction status, excluded channels, definition of any summed channel |
| Precomputed `μ(E)` | `energy_eV`, `mu` | retain `I0/It/If` when available and state the equation and corrections used to calculate `mu` |
| Athena EXAFS export | `k_A^-1`, **unweighted** `chi(k)` | `kchi`, `k2chi`, and `k3chi` may be included, but do not provide only one weighted curve |

File names should distinguish the sample, repeat, and reference, for example `sampleA_scan01.xdi`, `sampleA_scan02.xdi`, and `Fe_foil_scan01.xdi`. Upload every repeat, including scans later judged abnormal. Mark the exclusion and its reason in metadata instead of silently deleting the file.

### 2. Standards and references

If absolute coordination numbers are a target, provide a metal foil or known-coordination standard measured at the **same absorption edge**, preferably during the same beamtime or under the same monochromator state:

- the raw reference-foil scan or an Athena `.prj` that contains the reference channel;
- raw data and structural information for the standard used to determine `S0²`, including its known coordination number;
- the calibration convention, `k`/`R` fit ranges, and window used for both the standard and unknown sample.

If no suitable same-edge standard exists, a justified literature value or constrained `S0²` may be used only with a cited source and sensitivity test. The resulting CN must not be presented as a model-independent absolute value.

### 3. Uploading Athena-processed data

If calibration, merging, or background removal has already been completed in Athena, upload:

- the Athena `.prj` project;
- every raw scan used to create it;
- an Athena text export of unweighted `χ(k)`;
- normalized `μ(E)` and numerical `χ(R)` exports when available;
- processing settings: `E0`, normalization ranges, `Rbkg`, `kmin/kmax`, `dk`, window type, and merge rule.

**An Athena-exported `.txt` or `.dat` file is sufficient to begin a fit** when it contains at least two numerical columns, `k` and unweighted `χ(k)`, and the processing settings above are supplied. A lone `k²χ(k)`, `|χ(R)|`, or image is not enough to reconstruct the full fitting input.

### 4. Continuing an Artemis project

Upload as many of these files together as possible:

- the Artemis `.fpj` file or complete `.dpj` project directory;
- its exact `fit.log`, plus any existing `summary.tsv`, CSV/XLSX parameter table, or fit report;
- the CIF, `feff.inp`, `paths.dat`, and `feffNNNN.dat` files that match the project; the complete FEFF calculation directory is best;
- the Athena `.prj` and original raw scans;
- a short note identifying the fit to continue, fixed parameters, enabled paths, and any unsaved manual changes.

Do not provide only a screenshot of the `.fpj/.dpj` project or a copied parameter table. Those cannot restore GDS constraints, path mappings, the correlation matrix, or the actual residuals.

### 5. Structural and experimental metadata

Prefer an experimental `.cif` that matches the measured phase. If no CIF exists, provide the chemical composition, phase, space group, unit cell, dopant/defect/surface-site hypothesis, and source. Name explicit surface, defect, or disordered models separately from the experimental average structure so that a theoretical model is not mistaken for an experimentally refined structure.

Also include a `metadata.csv` or `README.txt` containing at least:

- the sample-to-file mapping, absorber, and absorption edge;
- beamline, measurement date, transmission/fluorescence mode, temperature, atmosphere, or electrochemical condition;
- column definitions, units, reference-foil position, and calibration convention;
- repeat-merging rule and reasons for excluding scans or detector channels;
- the scientific comparison requested, such as CN, bond length, disorder, shared parameters across samples, or a multi-edge joint fit.

### 6. Files that are not sufficient on their own

These items may accompany the data, but cannot replace numerical inputs and project files:

- PNG/JPG screenshots, PDF figures, Origin plots, or an `.opju` containing plots without exported numerical worksheets;
- curves embedded in Word/PowerPoint or manually copied and rounded tables;
- `|χ(R)|` without the real/imaginary components or the original `χ(k)`;
- only one `k²χ(k)`/`k³χ(k)` curve when unweighted `χ(k)` is unavailable;
- a CIF without spectra, or spectra without a structural/FEFF model.

### 7. Recommended upload layout

```text
sample_xafs_input/
├── 01_raw/
│   ├── sampleA_scan01.xdi
│   ├── sampleA_scan02.xdi
│   └── reference_foil_scan01.xdi
├── 02_athena/
│   ├── sample_and_foil.prj
│   └── sampleA_chik.dat
├── 03_existing_fit/
│   ├── sampleA.fpj                 # or the complete .dpj directory
│   ├── fit.log
│   └── summary.tsv
├── 04_structure_and_feff/
│   ├── phase.cif
│   ├── feff.inp
│   └── feffNNNN.dat
├── metadata.csv
└── README.txt
```

If only one archive can be uploaded, prioritize: **raw sample scans + same-edge reference/standard + metadata + CIF/FEFF + Athena `.prj` + Artemis project**.

## End-to-end workflow

| Stage | Main task | Required checks | Main outputs |
|---|---|---|---|
| 1. Preserve and inventory | Copy raw inputs and record conditions and SHA256 | element, edge, beamline, mode, scan IDs, temperature, reference channel | raw inventory, hashes, measurement record |
| 2. Energy calibration | Calibrate with a simultaneously measured foil or accepted standard | `dμ/dE`, beamline convention, valid propagation group | energy shift, derivative plot, calibration record |
| 3. Athena processing | Pre-edge, normalization, AUTOBK, and χ(k) extraction | `Rbkg`, k range, glitches, scan agreement, high-k noise | Athena project and processed `χ(k)` |
| 4. Determine `S0²` | Fit a low-parameter first shell of a known-CN standard | same absorber/edge, fixed crystallographic degeneracy, window stability | `S0² ± uncertainty`, standard project and log |
| 5. CIF and FEFF | Obtain the correct experimental phase and generate paths | formula, phase, space group, occupancy, disorder, absorber, `ipot`, degeneracy | CIF, provenance, `feff.inp`, path inventory |
| 6. First-shell fit | Fix `S0²` and use the smallest identifiable model | complete first shell, justified `ΔR`/`σ²` groups, one `ΔE0` per data set | initial DPJ/FPJ, fit log, k/R fit curves |
| 7. Extend the model | Add higher shells and multiple scattering as required by the R range | no material missing paths; no parameter inflation solely to lower R-factor | candidate fits and model-comparison table |
| 8. Parameter and robustness audit | Test limits, correlations, and window dependence | `Nind/Nvar`, boundary hits, errors, correlations, k/R and k-weight perturbations | audit JSON and accepted/rejected model record |
| 9. Numerical export | Export every curve from the same accepted fit snapshot | consistent grids for k¹/k²/k³ and R magnitude/real/imaginary | raw χ(k), k-space, and R-space tables |
| 10. Package and verify | Build the default nine-file directory and verify grids, residuals, and arithmetic | DPJ load check, valid k/R grids, and `R=Reff+ΔR` | DPJ, k1/2/3, R1/2/3, one table, `FIT_WORKFLOW.txt` |

See [`references/workflow.md`](workflow.md) for the detailed procedure.

## Scientific guardrails

The values below are warning thresholds or starting ranges, not universal hard bounds for every absorber, edge, temperature, and phase.

| Parameter/metric | Recommended treatment | Warning or rejection condition |
|---|---|---|
| `S0²` | Determine from a known-CN standard at the same absorber and edge, then fix for sample fits | `<0.6` or `>1.1` usually requires investigation; reject negative values; do not freely covary with CN without an independent constraint |
| CN | Begin with theoretical degeneracy and release effective amplitude groups one at a time | negative CN, values beyond the structural model, incomplete or double-counted path sets |
| `ΔE0` | Normally one value per data set, initialized at 0 eV | `|ΔE0| > 10 eV` after calibration is a strong warning |
| `ΔR` | Initialize at 0 Å and share only across structurally related paths | `|ΔR| > 0.10 Å` requires justification; a boundary hit usually signals a model problem |
| `σ²` | `0.003–0.008 Å²` is a useful starting range for many room-temperature first shells | reject negative values; `>0.015–0.020 Å²` requires a disorder or shell-splitting review |
| Correlation | Inspect the complete matrix | `0.90–0.95` is a strong warning; absolute correlation `>0.95` usually requires reparameterization |
| Information content | `Nind ≈ 2ΔkΔR/π + 2` | require `Nvar < Nind`; prefer `Nvar ≤ 2/3 Nind` |
| Distance | Report `Rfit = Reff + ΔR` | do not report `Reff` or an uncorrected R-space peak maximum as the fitted bond distance |

Simultaneous k weights 1, 2, and 3 do not triple the independent information content. See [`references/parameter-constraints.md`](parameter-constraints.md) for the complete acceptance rules and robustness tests.

## Required delivery files

Every executed fit must return numerical files, not only plots or narrative. The default delivery contains only nine files:

```text
<sample>_xafs_delivery/
├── <final-fit>.dpj
├── k1_data_fit.csv
├── k2_data_fit.csv
├── k3_data_fit.csv
├── R1_data_fit.csv
├── R2_data_fit.csv
├── R3_data_fit.csv
├── fit_parameters.tsv
└── FIT_WORKFLOW.txt
```

The k1/k2/k3 files contain k¹/k²/k³-weighted data, fit, and residual. R1/R2/R3 are not aliases for magnitude/real/imaginary; they are the R-space transforms at k weights 1, 2, and 3. Each R file contains magnitude, real, and imaginary data, fit, and residual columns. Demeter's R-space magnitude residual is the magnitude of the complex residual,

```text
|χdata(R) - χfit(R)|
```

and is generally not equal to `|χdata(R)| - |χfit(R)|`. `FIT_WORKFLOW.txt` records the inputs, calibration and preprocessing basis, FEFF paths, fixed/fitted parameters, k/R windows, model decision, exports, and the DPJ reopen/load check.

Keep raw scans, CIF, `feff.inp`, logs, hashes, and QA records in the working directory, but do not duplicate them in the default delivery. Use `--profile audit` only when the user requests the extended provenance package. See [`references/deliverables.md`](deliverables.md) for the exact file and column contract.

## Fit-parameter table

The standardized table separates theoretical, fitted, derived, and fixed quantities:

| Field | Meaning |
|---|---|
| `sample` | sample name |
| `path_index`, `path`, `scatterer` | FEFF path index, label, and scatterer |
| `degeneracy_theory` | theoretical FEFF path degeneracy |
| `amplitude_factor` | amplitude relative to theoretical coordination |
| `cn_fit` | `degeneracy_theory × amplitude_factor` |
| `reff_A` | FEFF geometric path distance |
| `delr_A`, `delr_error_A` | fitted distance correction and uncertainty |
| `r_fit_A` | `reff_A + delr_A` |
| `sigma2_A2`, `sigma2_error_A2` | Debye–Waller factor and uncertainty |
| `e0_eV`, `e0_error_eV` | `ΔE0` and uncertainty |
| `s02`, `s02_status` | `S0²` and fixed/fitted status |
| `r_factor`, `fit_status`, `notes` | fit metric, review status, and constraint notes |

## Installation and update

Fresh installation:

```powershell
git clone https://github.com/catdaog/artemis-xafs-fit-skill.git `
  "$env:USERPROFILE\.codex\skills\artemis-xafs-fit-skill"
```

Update an existing Git installation:

```powershell
git -C "$env:USERPROFILE\.codex\skills\artemis-xafs-fit-skill" pull --ff-only
```

Alternatively, download the GitHub ZIP and copy the extracted directory to:

```text
~/.codex/skills/artemis-xafs-fit-skill
```

## Invocation example

Use the skill explicitly in Codex:

```text
Use $artemis-xafs-fit-skill to calibrate my foil, determine S0², run a first-shell fit,
and deliver the default DPJ, k1/k2/k3, R1/R2/R3, one parameter table, and workflow TXT.
```

Codex may also select the skill automatically for Athena, Artemis, FEFF, EXAFS, coordination-number fitting, and numerical R-space export requests.

## Helper scripts

| Script | Purpose |
|---|---|
| `fetch_reference.py` | download and validate CIF/XAS references with URL, SHA256, and provenance |
| `foil_calibrate.py` | list derivative candidates and apply a reviewed calibration feature |
| `suggest_xafs_settings.py` | suggest standard structures and starting k weights from absorber, edge, and scatterers |
| `run_demeter.ps1` | probe and run Windows Demeter in an isolated short-path runtime |
| `demeter_first_shell_fit.pl` | run a fixed-`S0²`, explicit-path first-shell fit with grouped `σ²` |
| `audit_fit_log.py` | audit negative `σ²`, extreme shifts, parameter counts, and high correlations |
| `build_xafs_delivery.py` | build and verify the default nine-file delivery; use `--profile audit` for the extended package |

Probe the local Demeter installation:

```powershell
.\scripts\run_demeter.ps1 -Action probe
```

Build and verify a delivery package:

```powershell
python scripts/build_xafs_delivery.py build `
  --output sample_xafs_delivery `
  --sample "Sample name" `
  --artemis-project fit.dpj `
  --fit-k1 fit_k1.dat --fit-k2 fit_k2.dat --fit-k3 fit_k3.dat `
  --fit-r1-mag fit_r1_mag.dat --fit-r1-re fit_r1_re.dat --fit-r1-im fit_r1_im.dat `
  --fit-r2-mag fit_r2_mag.dat --fit-r2-re fit_r2_re.dat --fit-r2-im fit_r2_im.dat `
  --fit-r3-mag fit_r3_mag.dat --fit-r3-re fit_r3_re.dat --fit-r3-im fit_r3_im.dat `
  --parameters fit_parameters.tsv `
  --workflow-source FIT_WORKFLOW.txt `
  --project-check "Loaded successfully with the matching Demeter project loader"

python scripts/build_xafs_delivery.py verify --package sample_xafs_delivery
```

The builder refuses to overwrite an existing destination. Use a new versioned directory for every rerun. Add `--profile audit` when raw inputs, FEFF/CIF, logs, statistics, hashes, and QA files are explicitly requested.

## Repository layout

```text
artemis-xafs-fit-skill/
├── SKILL.md                              entry point and required invariants
├── agents/openai.yaml                    Codex interface metadata
├── references/
│   ├── workflow.md                       complete standard-to-sample workflow
│   ├── basic-principles.md               EXAFS theory and parameter correlations
│   ├── parameter-constraints.md          limits and acceptance rules
│   ├── deliverables.md                   delivery-package file contract
│   ├── element-guidance.md               elements, edges, standards, and k weights
│   ├── software-and-sample-preparation.md software and transmission-sample preparation
│   ├── demeter-api.md                    Demeter automation interface
│   └── sources.md                        data, CIF, and software source policy
├── scripts/                              reusable tools
└── tests/                                standard-library unit tests
```

## Validation

Run the standard-library tests:

```powershell
python -m unittest discover -s tests -v
```

Run the Codex skill validator:

```powershell
python <skill-creator>/scripts/quick_validate.py .
```

GitHub Actions runs Python compilation and delivery-package tests on every push and pull request.

## Official software and references

- [Demeter](https://bruceravel.github.io/demeter/) — Athena, Artemis, and Hephaestus.
- [FEFF](https://feff.phys.washington.edu/feffproject-feff-download.html) — official FEFF downloads.
- [XAFSmass](https://xafsmass.readthedocs.io/) — powder mass, thickness, and edge-step calculations.
- [CatMass](https://web.slac.stanford.edu/coaccess/resources/software) — supported catalysts and complex-composition mass calculations.
- [CLS X-Mass](https://xasdb.lightsource.ca/xafsmass) — browser-based sample/diluent mass calculation.
- Teo and Lee, *J. Am. Chem. Soc.* **101** (1979) 2815–2832, [DOI: 10.1021/ja00505a003](https://doi.org/10.1021/ja00505a003).

Before using an external CIF or XAS data set, verify its phase, measurement conditions, license, landing page, and citation. See [`references/sources.md`](sources.md) for the complete source policy.
