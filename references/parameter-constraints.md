# EXAFS parameter constraints and acceptance rules

Use this reference before defining GDS parameters, accepting a fit, or reporting structural values. The numerical values below are warning thresholds and starting ranges, not universal physical laws. Replace them only with a documented edge-, temperature-, phase-, or experiment-specific reason.

## Information limit

Estimate the independent information content with

`Nind ≈ 2 × Δk × ΔR / π + 2`.

- Count varied `guess` parameters, not fixed `set` values or algebraically derived `def` values.
- Simultaneous k weights 1, 2, and 3 do not triple `Nind` because they are transforms of the same spectrum.
- Reject `Nvar >= Nind`.
- Prefer `Nvar <= 2/3 Nind`; if the fit exceeds this, require strong physical constraints and explicit sensitivity tests.

## Parameter table

| Parameter | Recommended starting treatment | Warning threshold | Reject or rebuild when |
|---|---|---|---|
| `S0²` | Determine from a known-CN standard at the same absorber edge, then fix | `<0.6` or `>1.1` commonly indicates a problem | negative; transferred across unrelated absorber/edge; freely covaried with CN without an independent constraint |
| effective CN | Fix to theoretical degeneracy first; release one amplitude group at a time | above the phase-specific structural maximum or uncertainty comparable to value | negative; derived from an incomplete or double-counted path set |
| `ΔE0` | one value per data set, initial value 0 eV | `|ΔE0| > 10 eV` after calibration | extreme or boundary-pinned value used to compensate for wrong calibration, edge, or phase |
| `ΔR` | initial value 0 Å; share only for structurally related paths | `|ΔR| > 0.10 Å` | boundary hit, window instability, or chemically implausible final distance |
| `σ²` | start around `0.003–0.008 Å²` for many room-temperature first shells | `>0.015–0.020 Å²` requires a disorder/shell-splitting check | negative, non-finite, or uncertainty larger than the value without qualification |
| C3/C4 | keep at zero in the initial model | sign or magnitude changes under modest window changes | released without sufficient k range, or used together with unsupported shell splitting |
| correlation | inspect the full matrix | `0.90–0.95` is a strong warning | absolute correlation `>0.95` for parameters central to the conclusion |

Do not hard-clip a parameter merely to hide an invalid solution. A value that repeatedly hits a restraint or boundary is a model warning, not an accepted measurement.

## Required distinctions

- Energy calibration shift is an instrumental correction; fitted `ΔE0` is a phase/origin correction. Do not substitute one for the other.
- FEFF degeneracy is the theoretical path multiplicity. If `s02 = S0² × amp`, report `CNfit = degeneracy × amp`.
- If all symmetry-split `deg=1` paths are included, apply `S0²` to each. Multiply a representative path by the shell degeneracy only when the omitted paths are intentionally represented by that one path.
- Report `Rfit = Reff + ΔR`; `Reff` alone is not the fitted bond distance, and an uncorrected R-space peak maximum is not a bond distance.
- A low R-factor is only a residual measure. It cannot override negative `σ²`, wrong `ipot`, incomplete shells, extreme shifts, excessive correlation, or information-limit failure.

## Robustness tests

Before accepting a central structural parameter, repeat the fit with reasonable perturbations:

- `kmin` shifted by about `±0.5 Å⁻¹` where the data permit;
- `kmax` shifted by about `±0.5–1 Å⁻¹`;
- `Rmin` shifted by about `±0.1–0.2 Å`;
- `Rmax` shifted by about `±0.2–0.3 Å`;
- individual and simultaneous k weights 1, 2, and 3;
- at least one conservative path model and one physically motivated extension.

Report the parameter spread or model dependence alongside the formal fit uncertainty when it is materially larger.

## Acceptance checklist

Accept a model only when all applicable items pass:

1. Calibration convention and propagated shift are documented.
2. `S0²` source, edge, value, uncertainty, and fixed/fitted status are explicit.
3. Absorber, edge, CIF phase, `ipot`, path sequence, degeneracy, and `Reff` are verified.
4. All material paths in the chosen R window are represented.
5. `Nvar < Nind`; correlations and uncertainties are reported.
6. `σ² >= 0`; `ΔR`, `ΔE0`, CN, and final distances are physically defensible.
7. Residuals are inspected in k space and in R-space magnitude, real, and imaginary components.
8. Parameters are stable to modest window/weight/model changes.
9. Numerical exports and the parameter table match the accepted fit snapshot.
