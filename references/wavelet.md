# EXAFS Morlet wavelets and Origin matrices

Use this branch for a k–R transform of numerical EXAFS χ(k), standalone or after fitting. It is a diagnostic transformation, not a new fit or a substitute for energy calibration/background subtraction. Standalone WT does not need S0², a structure, FEFF, or DPJ. Raw μ(E) first needs a documented EXAFS extraction.

## Calculation convention

The defaults are κ=10, σ=1, kweight=2, kstep=0.05 Å⁻¹, R=0–6 Å with step 0.02 Å, and a Hanning taper with dk=1 Å⁻¹. These are configurable software starting values, not universally optimal experimental settings. Choose the useful k interval from the measured signal/noise and use the same settings across compared spectra.

The implemented complex Morlet mother wavelet includes its zero-mean correction:

```text
psi(u) = [exp(i*kappa*u) - exp(-0.5*(kappa*sigma)^2)]
         * exp[-u^2/(2*sigma^2)] / [sqrt(2*pi)*sigma]
f(k') = k'^kweight * chi(k') * window(k')
W(k,R) = a^(-1/2) * integral f(k') * conjugate[psi((k'-k)/a)] dk'
a = kappa/(2*R), R > 0
W(k,0) = 0  (the R→0 limit, not a coordination shell)
```

The factor 2 follows the EXAFS oscillation `sin(2*k*R + phase)`. R is a wavelet frequency coordinate in Å, **uncorrected for scattering phase**; it is not automatically an interatomic distance. The stated L2 scale normalization must be retained when comparing amplitudes. This implementation does not claim numerical amplitude identity with HAMA or another package using a different normalization, taper or discretization.

Here κ is the carrier angular frequency and σ is the Gaussian envelope width, distinct from the EXAFS Debye–Waller σ². For PyWavelets' mother-wavelet exponent convention, matching the exponents would require `B=2*sigma^2`, `C=kappa/(2*pi)`, hence B=2 and C≈1.59155 at 10/1. Merely writing `cmor10-1` specifies a different wavelet; normalization still requires separate alignment.

For `window="hanning"`, the taper is the product of two endpoint ramps:

```text
wL(k) = 0.5 * [1 - cos(pi * clip((k-kmin)/dk, 0, 1))]
wR(k) = 0.5 * [1 - cos(pi * clip((kmax-k)/dk, 0, 1))]
window(k) = wL(k) * wR(k)
```

The ramps lie inside the selected k interval and multiply if they overlap. `window="none"` applies no taper. Record this definition rather than assuming that every program's “Hanning/dk=1” is identical.

## Inputs and commands

Install the optional NumPy dependency in the Python environment used to execute this branch:

```shell
python -m pip install -r requirements-wavelet.txt
python scripts/exafs_wavelet.py chi_k.dat --out work/wt_sample --kmin 3 --kmax 12 --kweight 2
python scripts/exafs_wavelet.py verify work/wt_sample
```

On Windows the launcher avoids the WindowsApps Python alias:

```powershell
.\scripts\run_wavelet.ps1 -InputFile C:\data\sample.chi -Output C:\work\wt_sample -KMin 3 -KMax 12 -KWeight 2
.\scripts\run_wavelet.ps1 -Config C:\work\wavelet.json -Output C:\work\wt_batch
.\scripts\run_wavelet.ps1 -Verify C:\work\wt_batch
```

The output must be new or empty; earlier results are preserved. Supply column numbers as 1-based values using `--k-column` and `--chi-column`. Whitespace-, tab- or comma-delimited numerical spectra with leading headers are supported. k must be finite, strictly increasing and unique. Missing/malformed numeric rows, nonfinite values, unsupported ranges and extrapolation are errors. Uniform resampling does not create new measured support; investigate gaps rather than interpolating through missing data.

For batch comparison, copy [the template](../examples/wavelet.template.json), replace the input paths and select justified ranges:

```shell
python scripts/exafs_wavelet.py --config work/wavelet.json --out work/wt_comparison
python scripts/exafs_wavelet.py verify work/wt_comparison
```

Paths in a config are relative to that config. Each `spectra` entry declares `id`, `file`, `k_column`, `chi_column`, `input_kweight` and an optional role. `input_kweight=0` means unweighted χ(k). A nonzero declared input weight is removed before applying the requested WT k weight. The calculation never guesses a weight from the filename or column values.

For measured spectra without a fit, remove the template's `model` entry and `residuals` list; add each sample or standard as another `spectra` entry. No synthetic model is created to fill a missing fit.

The fit driver already writes **unweighted** `chi_k.dat` (k/χ in columns 1/2). Its `fit_k1.dat` and delivered `k1_data_fit.csv` have already been multiplied by k: data, fit and residual are columns 2/3/4. Use `input_kweight=1` for those columns and select positive k before inverse weighting. The analogous k2/k3 exports require input weights 2/3. An extra application of the same weight would change the map.

All spectra in one batch share the actual common measured interval, grid, taper, κ/σ and requested k weight. Explicit kmin/kmax must be inside every spectrum's support. Config `residuals` entries such as `{"id":"residual","data":"sample","fit":"model"}` transform χdata−χfit on that common grid. This gives `|WT(data-fit)|`, not `|WT(data)|-|WT(fit)|`. Additional verified FEFF path spectra can be supplied as named spectra; their **complex coefficients**, rather than their magnitudes, add coherently.

## Numerical delivery and Origin

The WT package is separate from the fitted EXAFS nine-file package:

```text
wt_comparison/
  WT_parameters.json
  ORIGIN_IMPORT.txt
  sample/
    WT_matrix.txt
    WT_normalized.txt
    WT_coefficients.npz
  model/                 # when supplied
    ...
  residual/              # when configured
    ...
```

- `WT_matrix.txt`: unnormalized `|W(k,R)|`, tab-delimited numeric cells only. **Columns run along k (X, Å⁻¹); rows run along R (Y, Å).** Shape is `(number of R points, number of k points)`.
- `WT_normalized.txt`: separate amplitude matrix divided by one shared maximum across all outputs of the run. A common denominator preserves relative amplitudes within that run; it is not individual spectrum normalization or a coordination-number calibration.
- `WT_coefficients.npz`: full-precision complex coefficients, actual k/R axes and boundary-influence information for audit and further numerical comparison.
- `WT_parameters.json`: formula, parameters, actual coordinate limits/steps/counts, window, input weighting and hashes, interpolation/support information, normalization, runtime and boundary definitions.
- `ORIGIN_IMPORT.txt`: the actual dimensions and XY mapping for the generated matrices.

In Origin, create a matrix and import a `WT_matrix.txt` as numeric Z values. In **Matrix → Set Dimension/Labels**, use the recorded column/row counts and map X from the first to last k and Y from the first to last R. Origin assumes uniform XY spacing for this matrix form. Plot a color-filled contour or heat map. Treat row/column numbers as indexes, not physical k/R values. No random XYZ gridding is needed for this regular grid. Import `WT_normalized.txt` instead only when that normalization is intended. For comparisons, use the same color limits; the normalized outputs in one run already share their denominator.

Verification rereads the saved matrices, coefficients and metadata and checks numerical agreement, finite values, dimensions, coordinates and normalization. Report the actual verifier result; generating a preview is not a substitute for numerical verification. A synthetic test demonstrates code behavior, not a measured catalyst structure.

## Optional fit-pipeline hook

Add a top-level `wavelet` object to the standard-to-samples config, for example:

```json
"wavelet": {
  "kappa": 10, "sigma": 1, "kweight": 2,
  "kmin": 3, "kmax": 12, "kstep": 0.05,
  "rmin": 0, "rmax": 6, "rstep": 0.02,
  "window": "hanning", "dk": 1
}
```

The pipeline generates experiment/fit/residual maps for all executed standards/samples in one batch at `<pipeline-output>/wavelet/`. Dataset directories are named `<id>_data`, `<id>_fit` and `<id>_residual`; the whole batch shares a grid and normalization denominator. If kmin/kmax are omitted, the hook uses the intersection of all fit windows. Explicit limits must remain within that intersection. It uses unweighted `chi_k.dat` for experiment and explicitly removes the k¹ weight of the fit column in `fit_k1.dat`. Options are checked before the external fits begin. Set `wavelet` to false or `{"enabled":false}` to disable the hook. The hook does not invent path spectra or mark a fitted model scientifically accepted. The regular fit builder continues to verify its nine-file fit package; deliver the WT directory alongside it when requested.

## Interpretation and boundaries

Finite k support affects the transform near either endpoint, especially at small R where the wavelet is broad. The exported Gaussian-envelope boundary criterion uses an endpoint margin `sqrt(2)*a*sigma`; this is an illustrative cone-of-influence convention, not a confidence interval or proof that all points inside it are reliable. Padding is computational support, never additional measurements. Inspect the recorded mask and compare relevant k-window/weight sensitivity before interpreting weak features.

WT supplies a complementary view of the **same** χ(k). It adds no independent observations for a fit. A maximum is insufficient to uniquely identify an element, establish bonding, prove single-atom dispersion, determine CN, or establish absence of a weak path. Compare chemical candidates, standard spectra, actually calculated paths, fit residuals and parameter stability. A modulus hides phase and interference; use the complex coefficients when testing sums or residuals.

## Method and format sources

- [Funke, Scheinost and Chukalina, Phys. Rev. B 71, 094110 (2005)](https://doi.org/10.1103/PhysRevB.71.094110): Morlet WT in EXAFS and the k/R resolution trade-off.
- [Funke, Chukalina and Scheinost, J. Synchrotron Rad. 14, 426–432 (2007)](https://journals.iucr.org/s/issues/2007/05/00/fh5377/): Morlet definitions, normalization/resolution conventions and FEFF-based extensions. The present engine is a Morlet transform, not the FEFF–Morlet mother wavelet introduced in that paper.
- [Yue et al., Nature Communications 15, 7820 (2024)](https://www.nature.com/articles/s41467-024-52022-0): an EXAFS application reporting HAMA Morlet κ=10/σ=1. This is a parameter example, not an amplitude-equivalence claim.
- [Origin: matrix dimensions and XY coordinates](https://docs.originlab.com/origin-help/mats-dim-xycoord/): evenly spaced columns map to X and rows to Y.
