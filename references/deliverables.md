# XAFS delivery contract

Use this reference whenever a standard or sample fit was run. Return numerical files, not only plots or prose.

## Default: minimal nine-file package

The default package is flat and contains only:

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

Do not add plots, duplicate Markdown/CSV parameter tables, raw scans, CIF/FEFF files, logs, manifests, or QA folders to the default package. Preserve those source and audit materials in the working directory and include them only when the user requests the `audit` profile.

The DPJ is the primary deliverable. Reopen it in Artemis or load it with the matching Demeter project loader before packaging, and write the actual check in `FIT_WORKFLOW.txt`. Extension and non-zero size alone do not prove project integrity.

## k1, k2 and k3 files

Each file contains every exported k point, in order, with leading columns:

`k_A^-1, data, fit, residual`

Retain the transform window and any additional Demeter columns. Verify `residual ~= data - fit` within export precision. The three files must come from the same accepted fit and use the same k grid.

## R1, R2 and R3 files

`R1`, `R2`, and `R3` are **not** aliases for magnitude, real, and imaginary parts. They mean the Fourier transforms of `k^1 chi(k)`, `k^2 chi(k)`, and `k^3 chi(k)`, respectively.

Before each R-space export, set the Demeter plot k-weight to the corresponding value. Each combined file contains:

`R_A, data_mag, fit_mag, residual_mag, data_real, fit_real, residual_real, data_imag, fit_imag, residual_imag, window`

Combine magnitude, real, and imaginary exports only after verifying identical R grids. For real and imaginary columns, verify `residual ~= data - fit`. Do not apply that arithmetic to magnitude: Demeter's magnitude residual is `|chi_data(R) - chi_fit(R)|`, which is generally not `|chi_data(R)| - |chi_fit(R)|`.

## One parameter table

Deliver only `fit_parameters.tsv` by default. Each fitted path row should contain, when applicable:

- sample, fit/model identifier, FEFF path index, path and scatterer;
- theoretical degeneracy, fitted amplitude factor, and `CNfit = degeneracy * amplitude`;
- `Reff`, `DeltaR`, its uncertainty, and `Rfit = Reff + DeltaR`;
- `sigma2` and uncertainty in A^2;
- `DeltaE0` and uncertainty in eV;
- `S0^2` and whether it was fixed or fitted;
- R-factor, accepted/rejected/unreviewed status, and constraint notes.

Keep theoretical, fitted, derived, and fixed quantities in separate columns. Do not invent an uncertainty for a fixed quantity.

## FIT_WORKFLOW.txt

This text file must let another researcher reconstruct how the delivered result was produced. Record:

1. input spectrum/project and FEFF structural source;
2. energy calibration and Athena preprocessing choices when applicable;
3. fixed `S0^2`, selected paths, parameter sharing/fixing, and constraints;
4. k/R ranges, windows, simultaneous fit weights, `Nind`, and `Nvar`;
5. model-comparison/acceptance decision and any rejected alternatives;
6. exact k1/k2/k3 and R1/R2/R3 export procedure;
7. DPJ reopen/load check and the tool/version used;
8. whether any source file was modified.

The driver writes an executed-fit record. The delivery builder adds the export definitions and project-check statement. Never state that Artemis reopened a project unless that check actually occurred.

## Optional audit profile

Use `--profile audit` only when the user requests raw inputs, processed chi(k), source exports, fit statistics, CIF/FEFF/log files, QA records, hashes, or the previous extended directory layout. The audit profile does not change the fit; it only preserves more provenance.

## Default build command

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
  --project-check "Loaded successfully with Demeter 0.9.26 project loader"

python scripts/build_xafs_delivery.py verify --package sample_xafs_delivery
```

The builder refuses to overwrite an existing destination. Use a new versioned directory for each rerun.
