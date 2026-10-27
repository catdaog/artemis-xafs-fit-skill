# XANES / 近边: real FDMNES calculation and structural refinement

Use this branch for the user's simulated-versus-experimental near-edge comparison,
single-atom candidate-site screening, or quantitative near-edge geometry refinement.
It supplements the existing EXAFS branch; it is not Athena reference-spectrum LCF.

## Intake and scientific decisions

Read supplied files first; ask only for consequential missing information:

- Absorber/edge, sample composition and measurement state, and the numerical
  experimental energy/absorption columns. A screenshot alone cannot support a fit.
- Calibration reference/convention, repeated scans and preprocessing where available.
  Unknown calibration can be recorded explicitly for shape screening, with limits on
  edge-shift interpretation. Never infer a calibrated oxidation state from a freely
  shifted theory curve.
- Candidate local structures, their provenance, and supporting EXAFS/chemistry/DFT.
  Do not ask the user for a CIF of an isolated site when only a proposed local model
  exists: build explicit *candidate* coordinates and explain assumptions.
- Decide whether the task is fixed-model simulation, spectral alignment, or actual
  structural optimization. Only the last may be called a structural fit.

No EXAFS S0² calibration, k/R windows, independent-point formula `2ΔkΔR/π`,
or Artemis project is required for this XANES-only branch. A measured reference is
still useful for energy calibration and validating the theory settings.

## Runtime and installation

Authoritative download entry: <https://fdmnes.neel.cnrs.fr/download/>.
Resolve its current operating-system archive link before downloading; do not assume
that the release label and the shared archive filename always match. The official
distribution contains the executable, examples and English manual. Retain its URL,
retrieval date and hashes. A recorded hash is provenance, not a publisher signature.
Do not redistribute the downloaded FDMNES executable under this skill's MIT license.

Python 3.10+ with `requirements.txt` and `requirements-xanes.txt` is required for
the full branch. The Windows launcher prefers the bundled Codex Python and then a
real `python` executable; `-Python` overrides it. It skips the WindowsApps alias.
The scripts also load optional dependencies from `skill/.deps/python`.

```powershell
# Run from the skill directory. Use absolute paths for actual user files.
.\scripts\run_xanes.ps1 -Mode probe
.\scripts\run_xanes.ps1 -Mode install -Archive C:\path\official-fdmnes.zip
# Or install using the verified HTTPS link resolved from the official page:
.\scripts\run_xanes.ps1 -Mode install -Url 'https://official-host/current-download'
```

Executable resolution: explicit `-Executable` / `--exe`, `FDMNES_EXE`, locally
installed `.deps/fdmnes/runtime.json`, then PATH. `probe` only locates and hashes
the binary; actual validation requires a successful calculation with spectra.

```powershell
# Use a real Python path; install into that environment or a dedicated environment.
& $pythonPath -m pip install -r requirements.txt -r requirements-xanes.txt
```

Each calculation gets its own directory, executable hardlink/copy, `fdmfile.txt`,
`input.txt`, logs and native output. No shared installation `fdmfile.txt` is edited.
The executable is launched directly with no shell, a timeout and no visible window.
Cache keys include deck text, executable and sibling DLL hashes; modified/missing
cached outputs fail closed. Nonzero exit, `fdmnes_error.txt`, or absent/unreadable
spectra are failures, even if a process exited with zero.

## Prepare and verify structure

For a supplied CIF, reuse `cif_tools.py inspect` and phase/source checks. Obtain
symmetry-expanded site ids before choosing the absorber. Then extract a cluster:

```powershell
& $pythonPath scripts/cif_tools.py inspect C:\data\model.cif --output C:\work\sites.json
& $pythonPath scripts/xanes_cluster.py C:\data\model.cif --absorber-id 0 --radius 8 `
  --model-id candidate1 --provenance 'Candidate from specified CIF; phase checked' `
  --out C:\work\candidate1.json
```

Insert that model object into the configuration's `models` list. The extractor
retains site ids and periodic translations, and rejects partial occupancies or
overlaps. Choose an extraction radius sufficient for the largest calculation and
potential environment; increasing FDMNES `Radius` cannot create omitted support
atoms. For finite clusters, also enlarge the explicit cluster and inspect the
FDMNES bav log's final-state/SCF/potential atom inventories. Resolve disorder as
explicit configurations rather than treating fractional atoms as full atoms.

For single atoms in carbon supports, retain relevant C/N/O and farther shells;
an isolated M–N4 fragment is a software illustration, not automatically a defensible
catalyst structure. DFT relaxation is helpful when appropriate, but label unrelaxed
candidates and never claim a calculation that was not performed.

## Configuration and preprocessing

Start from `examples/xanes/fe-n4.json`. It is an explicitly labelled five-atom toy,
not measured data or a validated Fe–N–C site. Replace the structure and assumptions.

- `absorber`, `edge`: K or L1/L2/L3; assess whether the single-particle treatment
  is suitable, especially for multiplet-dominated light transition-metal L edges.
- `calculation.method`: explicit `fdm` (full potential finite differences) or
  `green` (muffin-tin multiple scattering). Green is useful for preliminary
  screening; compare/validate before adopting it for the final interpretation.
- `calculation.scf`: explicit boolean; quadrupole, core-hole treatment and spin/
  charge assumptions must be recorded and tested when relevant. This generator
  currently uses FDMNES's default core-hole and nonmagnetic electronic treatment;
  it does not expose arbitrary magnetic/electronic-configuration refinement.
  Use a manually reviewed deck through `fdmnes_runtime.py run` for such settings
  and extend/validate the generator before claiming automated refinement of them.
- `range_eV`: energies relative to the theoretical Fermi reference, e.g.
  `[-25, 0.5, 20, 1, 90]`. Set sufficient tails for shifts and broadening.
- `convolution`: optional fixed FDMNES values `gamma_hole`, `gamma_max`, `ecent`,
  `elarg`, `e_cut`. Empty means FDMNES defaults; native logs record actual values.
- `experiment`: path relative to the JSON, zero-based columns, absolute photon
  energies in eV, explicit `edge_energy_eV`, `calibration_basis` and measured
  `calibration_shift_eV`. Uncertainties may be supplied with `sigma_column`.
  Set `data_kind` to `experimental` for measurements or `synthetic` for generated
  test targets; the latter is labelled explicitly in plots and numerical exports.
- `normalization`: `already_normalized`, or `linear_windows` with explicit
  `pre_edge_window_eV` / `post_edge_window_eV` in calibrated absolute eV. Linear
  normalization subtracts a pre-edge line and divides by the extrapolated edge
  jump at E0; it does not flatten or force a local white line to unity.
  Use a longer spectrum for reliable preprocessing; the plotted near-edge excerpt
  alone is often inadequate. For other normalization models use audited external
  preprocessing and record its settings. Raw detector counts first require the
  correct transmission/fluorescence conversion outside this two-column helper.

Raw source files are read only. Numerical rows keep their order and values in
the source record. Non-increasing energies, duplicate energies and malformed rows
after the numerical section are rejected rather than silently sorted or deleted.
The helper consumes a single processed spectrum; inspect and merge repeats with
appropriate weights beforehand, retaining scan provenance. Review fluorescence
self-absorption, detector dead time and beam damage before interpreting shape.

## Real calculation and convergence

```powershell
.\scripts\run_xanes.ps1 -Mode simulate -Config C:\work\xanes.json -Output C:\work\sim1
.\scripts\run_xanes.ps1 -Mode converge -Config C:\work\xanes.json -Output C:\work\radius1
.\scripts\run_xanes.ps1 -Mode fit -Config C:\work\xanes.json -Output C:\work\fit1
```

Outputs must be new/empty directories. Simulation needs no experiment file.
`converge` uses `convergence_radii_A` at initial geometry, reports successive
relative RMS changes and leaves scientific review pending. Inspect peak changes
in the actual fitting energy window and also test energy spacing, explicit-cluster
extent, SCF/core-hole/method assumptions. Radius agreement alone is insufficient.
Use the same settings and fit window for fair candidate comparisons; preserve
the convergence evidence separately and reference it in the final decision record.

## Refinement and model comparison

`fit.window_eV` is calibrated absolute experimental energy. The alignment equation is:

`E_theory_relative = E_experiment_calibrated - E0_experiment - shift_eV`.

Positive `shift_eV` moves theoretical features toward higher experimental energy;
this alignment parameter is separate from measured energy calibration. Do not fit
independent shifts for individual peaks. FDMNES native spectra are relatively
referenced (no `Energpho` keyword); do not silently add the edge energy twice.

The calculated native lifetime-convolved cross section receives optional additional
Gaussian instrumental broadening (`gaussian_sigma_eV`, **standard deviation**, not
FWHM), a positive amplitude, and optionally a constrained constant offset. Avoid
unnecessary free background parameters. Use the same treatment across candidates.
The full shift/4-sigma envelope must fit inside the theory domain: no extrapolation.

Geometry parameter format:

```json
{
  "name": "metal_ligand_A", "reference": 2.0,
  "initial": 1.98, "bounds": [1.85, 2.15], "step": 0.01,
  "radial_atoms": [1, 2, 3, 4]
}
```

All indices are zero based; coordinates are Cartesian Angstrom. `reference` is
the value represented by the original coordinates. Each selected ligand moves
by `(value-reference)` along its original absorber-to-ligand unit vector. For
shared shifts/out-of-plane displacement, use `displacements`, e.g.
`[{"atom": 0, "vector": [0,0,1]}]`. Vectors express Cartesian displacement per
parameter unit. Effects are summed from the original coordinates, never compounded.
Choose coordinates/effects that preserve the intended support chemistry. Angle or
spin fitting is not implemented as a special parameter type; do not label it as such.

The fitter first aligns nuisance parameters at fixed geometry, then jointly
optimizes bounded geometry and nuisance parameters. Every unique geometry launches
real FDMNES (unless its verified cache already exists); changing just energy shift,
amplitude or additional Gaussian width reuses the native spectrum. Absolute finite
steps avoid meaningless infinitesimal geometry derivatives. Vary the `step` and
inspect parameter profiles when numerical/theory noise affects derivatives.

Use `additional_starts` across plausible structural basins, or screen an explicit
geometry grid before refinement. A single optimizer's success flag can represent
a poor local minimum; the real-engine regression demonstrates this. Start-dependent
minima, boundary hits, strong correlations and rank deficiency remain warnings.
Do not automatically accept a result with such warnings. Report residual structure,
parameter stability and alternatives; widen the model set when evidence demands it.
For model-specific parameter names, set `additional_starts` inside each model;
this overrides the global list. Use an empty list for a fixed model if needed.

`limits.max_engine_runs`, `timeout_seconds` and `max_nfev` bound resource use.
Engine-budget exhaustion or a failed calculation records failure, never a completed
fit. Optimizer nonconvergence returns `incomplete` / CLI exit 3. Machine success
returns `review_required`, not scientifically accepted. Local covariance errors
are conditional linear approximations: systematic theory/calibration errors and
correlations between energy samples are excluded. Reduced chi-square is reported
only when sigma is supplied and explicitly assumes independent points. RMSE and
R-factor compare residuals descriptively; a smaller value with more parameters
does not establish a unique atomic site or prove single-atom dispersion.

## Deliverables and actual completion

For each fitted model retain `data_fit.csv`, `theory_native.csv`, `parameters.tsv`,
`fit_result.json`, `evaluations.json`, `best_structure.json`, `best_fdmnes_input.txt`,
and `comparison.png` / editable `comparison.svg`. The common run includes
`experimental_processed.csv`, `preprocessing.json`, `config.used.json`,
`model_comparison.tsv`, `xanes_run.json`, `XANES_WORKFLOW.txt` and real calculation
directories containing decks, `fdmfile.txt`, native outputs, stdout/stderr and bav.
The transformed `best_structure.json` has its coordinates already moved and its
active `parameters` cleared; the original parameterization is retained separately.
Do not reapply the original reference effects to those exported coordinates.

Check numerical curve/parameter consistency, view the exported overlay/residual,
review convergence/multistart evidence, and write the actual scientific limitations
and model decision into `XANES_WORKFLOW.txt`. Keep raw data immutable. Do not call
simulation-only or alignment-only results a structural fit. No DPJ is needed.

## Verification and sources

`python -m unittest discover -s tests -v` runs unit/regression tests. Set
`FDMNES_EXE` to opt into `tests/test_xanes_real.py`, which really computes a
synthetic target, refines geometry/shift/amplitude back toward the known values,
and also runs the finite-difference method. Set `XANES_REAL_TEST_OUT` to retain
its evidence in a new directory. Synthetic recovery tests the software and does
not validate a particular catalyst structure or replace experimental validation.

- Official theory and bibliography: <https://fdmnes.neel.cnrs.fr/theory/>.
- Official distribution and bundled `Doc/Manual_Eng.pdf`:
  <https://fdmnes.neel.cnrs.fr/download/>. The implemented deck syntax was tested
  with the Windows executable reporting Revision 21st of September 2026.
- Bunau & Joly, self-consistency: <https://doi.org/10.1088/0953-8984/21/34/345501>.
- Guda et al., full-potential finite differences:
  <https://doi.org/10.1021/acs.jctc.5b00327>.

Record the actual executable revision/hash and cite the methods used in publications;
do not copy a citation for a calculation option that was not used.
