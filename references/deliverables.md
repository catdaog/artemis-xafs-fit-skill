# Required XAFS delivery package

Use this reference whenever a standard or sample fit was run. The result must be a directory of numerical files, not only screenshots, plots, or prose.

## Directory contract

`scripts/build_xafs_delivery.py` creates and verifies this layout:

```text
<sample>_xafs_delivery/
├── DELIVERY.md
├── manifest.json
├── 00_OPEN_FIRST/
│   └── <final-accepted-fit>.fpj|.dpj       final fit; open directly in Artemis
├── 01_k_space/
│   ├── chi_k_source.dat                    original processed export
│   ├── chi_k.csv                           k, chi, kchi, k2chi, k3chi, window
│   ├── source_exports/                     unchanged Demeter exports
│   ├── kspace_fit_k1.csv                   k, data, fit, residual, window
│   ├── kspace_fit_k2.csv
│   └── kspace_fit_k3.csv
├── 02_r_space/
│   ├── source_exports/                     unchanged rmag/rre/rim exports
│   └── rspace_data_fit.csv                 magnitude/real/imaginary data, fit, residual
├── 03_parameters/
│   ├── source_fit_parameters.tsv           unchanged parameter export
│   ├── fit_parameters.tsv
│   ├── fit_parameters.md
│   └── fit_statistics.tsv
├── 04_raw_source/
│   └── 001_<original-name>                 byte-for-byte source copy
├── 05_models_feff/                         CIF, feff.inp, fit log, supporting models
└── 06_qa/                                  calibration, audit, comparison, provenance
```

The accepted `.fpj` or `.dpj` is the primary deliverable and must be listed and linked first in `DELIVERY.md` and in the final response. Before packaging, reopen it in Artemis or load it with the matching Demeter project loader and record that application-level check in the QA records. The builder verifies suffix, non-zero size, copy hash, and location, but those checks alone do not prove project integrity. The k-space and R-space numerical data/fit files come next. Supporting parameters, raw source, FEFF/CIF/log files, and QA records follow afterward.

The primary Artemis project, k-space tables, R-space table, parameter tables, and raw input are mandatory for a completed fit. Other files that do not apply may be omitted only with an explanation in `DELIVERY.md`. Do not create placeholder fit files for an unexecuted fit. If an openable final project cannot be saved, report the run as incomplete or blocked rather than presenting a plot as a completed delivery.

## Numerical column requirements

### Processed k-space data

`chi_k.csv` must contain every exported k point in the original order. Required columns are:

`k_A^-1, chi, k1_chi, k2_chi, k3_chi, window`

Demeter `save('chi', ...)` already exports these six columns. Do not resample, smooth, or truncate during packaging.

### k-space fit exports

Create one file for each requested k weight. Required leading columns are:

`k_A^-1, data, fit, residual`

Include the transform window and any Demeter background/running-term columns when present. Preserve every k coordinate and verify `residual ≈ data - fit` within export precision.

### R-space fit export

Combine Demeter `rmag`, `rre`, and `rim` exports only after verifying identical R grids. Required columns are:

`R_A, data_mag, fit_mag, residual_mag, data_real, fit_real, residual_real, data_imag, fit_imag, residual_imag`

Retain the R-space window and any additional source columns. Never derive real or imaginary components from magnitude alone.

For the real and imaginary exports, verify `residual ≈ data - fit`. Do **not** apply that arithmetic to the magnitude columns: Demeter's `rmag` residual is the magnitude of the complex residual, `|χdata(R) - χfit(R)|`, which is generally not equal to `|χdata(R)| - |χfit(R)|`.

## Parameter-table contract

Provide both machine-readable TSV/CSV and Markdown. Each fitted path row should contain, when applicable:

- sample and fit/model identifier;
- FEFF path index and path/scatterer label;
- theoretical FEFF degeneracy;
- fitted amplitude factor and `CNfit = degeneracy × amplitude`;
- `Reff`, `ΔR`, `ΔR` uncertainty, and `Rfit = Reff + ΔR`;
- `σ²` and uncertainty in Å²;
- `ΔE0` and uncertainty in eV;
- `S0²` value and whether fixed or fitted;
- R-factor and accepted/rejected/unreviewed status;
- notes describing shared/fixed/constrained parameters.

Keep theoretical, fitted, derived, and fixed quantities in separate columns. If a quantity was not fitted, write `fixed`, `not_applicable`, or leave it blank with a note; do not invent an uncertainty.

## Manifest and invariance checks

The package manifest records SHA256, byte size, numeric row count where applicable, and file role. Verification must confirm:

- raw copies match their recorded source hashes;
- exactly one non-empty `.fpj` or `.dpj` is present in `00_OPEN_FIRST/` and matches the manifest's primary-project entry;
- the processed and fit tables are numeric and have strictly increasing coordinates;
- k¹/k²/k³ files retain their respective source grids;
- `rmag`, `rre`, and `rim` share the same R grid before combination;
- parameter and statistics tables are present;
- mandatory model/project/log/audit files are present when the fit workflow produced them;
- no input file was overwritten.

## Build command

```powershell
python scripts/build_xafs_delivery.py build `
  --output sample_xafs_delivery `
  --sample "Sample name" `
  --artemis-project accepted_final_fit.fpj `
  --raw raw_scan_01.dat --raw raw_scan_02.dat `
  --processed-chi chi_k.dat `
  --fit-k1 fit_k1.dat --fit-k2 fit_k2.dat --fit-k3 fit_k3.dat `
  --fit-rmag fit_rmag.dat --fit-rre fit_rre.dat --fit-rim fit_rim.dat `
  --parameters fit_parameters.tsv `
  --statistics fit_statistics.tsv `
  --artifact fit.log --artifact feff.inp --artifact phase.cif `
  --qa audit.json --qa calibration.json --qa model_comparison.csv

python scripts/build_xafs_delivery.py verify --package sample_xafs_delivery
```

The builder normalizes the supplied TSV and generates the Markdown parameter table automatically. It refuses to overwrite an existing destination; create a new versioned directory for a rerun.
