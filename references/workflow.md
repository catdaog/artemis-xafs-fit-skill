# Foil-to-sample XAFS workflow

## 1. Preserve and inventory

Copy user data and projects into a work directory; record SHA256, file size, and modification time. Treat `.fpj`/`.dpj` as archives and inspect their data, GDS, FEFF, path, and fit records before changing anything. Never overwrite the only copy.

Record element/edge, beamline, transmission or fluorescence mode, reference-channel geometry, scan IDs, temperature, monochromator crystal, and whether foil and sample were acquired simultaneously.

## 2. Calibrate the foil in Athena

Use the foil measured with the experiment whenever possible. Merge repeated foil scans only after checking alignment and glitches.

1. Normalize sufficiently to inspect `dμ/dE`; energy calibration does not require a final EXAFS background model.
2. Display the derivative and identify the conventional calibration inflection for that foil/edge.
3. For Mo K-edge metal foil, choose the first clear lower-energy derivative maximum and assign 20000 eV. The strongest derivative peak is commonly the second feature and is not the calibration point.
4. Compute `energy shift = E_reference - E_observed`. Record the observed feature, assigned value, shift, and a derivative plot.
5. Apply the shift to the foil and to sample spectra acquired under the same monochromator calibration. For a different beamtime, monochromator reset, or questionable drift, calibrate independently.

Use `scripts/foil_calibrate.py` first without `--observed-energy` to list candidates. Select the feature after visual review, then rerun with `--observed-energy` and `--output`. Do not calibrate from a downloaded reference spectrum when a simultaneous foil exists.

## 3. Process foil EXAFS consistently

Choose pre-edge, normalization, `Rbkg`, spline range, and k range based on the foil data. Inspect χ(k) and χ(R), not only the XANES derivative. Save the calibrated Athena project and numerical χ(k).

When transferring settings, distinguish energy calibration from normalization/background settings. An identical energy shift can be propagated within one calibrated acquisition set; background parameters may still differ between foil and sample.

## 4. Determine S0² from the standard

Use a crystallographic model of the standard and known coordination. Consult `element-guidance.md`: common fcc elemental standards have nominal first-shell CN=12, bcc standards CN=8, and hcp standards nominal CN=12 but may split when `c/a` is non-ideal. Verify the actual phase rather than assigning coordination from the element name alone. For bcc Mo metal, for example:

- first shell: 8 Mo neighbors;
- second shell: 6 Mo neighbors;
- fit the first shell first and keep FEFF degeneracy fixed at 8.

A minimal first-shell standard model usually fits `S0²`, one `ΔE0`, one `ΔR`, and one `σ²`. Use a k range supported by the data and an R window that isolates the first standard-metal shell; k=3–12 Å⁻¹ is a common initial range for many hard-X-ray data sets, but inspect the actual spectrum rather than hard-coding it.

Accept `S0²` only when `σ² >= 0`, `ΔR` and `ΔE0` are plausible, uncertainties are finite, correlations are controlled, and the result is stable to modest window/k-weight changes. Report the fitted value and uncertainty. Repeated standards are preferable to a single scan.

## 5. Acquire and validate the sample CIF

Search by exact composition and phase. Prefer an experimental structure with a citable publication. Verify:

- formula and oxidation state plausibility;
- polymorph and space group;
- unit-cell parameters and measurement temperature;
- site occupancies, disorder, vacancies, and symmetry expansion;
- whether the structure represents the actual sample or only a starting model.

Use `scripts/fetch_reference.py --cod-id ID --kind cif` for a known COD entry, or pass a verified direct URL. Keep the provenance JSON sidecar. Convert to P1 only when FEFF/ATOMS requires it, and retain the original CIF separately.

## 6. Generate FEFF and inspect paths

Check absorber, edge, `ipot`, cluster radius, and atom count before running FEFF. Inspect every candidate path's scatterer sequence, degeneracy, and `Reff`; FEFF path order is not a scientific label.

For a distorted coordination polyhedron, include every split path needed to recover the full theoretical shell. Example: alpha-MoO3 has five distinct first-shell Mo–O paths with degeneracies `1+1+2+1+1`, total CN=6.

## 7. Fit in stages

1. Fix the foil-derived `S0²`.
2. Fit the complete first shell with one `ΔE0`, shared or minimally grouped `ΔR`, and shared or physically motivated `σ²` groups.
3. Compare a conservative low-parameter model with one additional physically motivated grouping.
4. Extend the R range only after adding the appropriate metal-metal, farther-ligand, and multiple-scattering paths.
5. If fitting effective CN, express amplitude explicitly, for example `S0² * amp`, and convert to `CN = amp * FEFF degeneracy`; do not confuse this with a fixed theoretical CN.

Use `element-guidance.md` or `scripts/suggest_xafs_settings.py` to identify the historical primary k weight from the dominant backscatterer. Use several k weights when supported (often 1, 2, 3), especially for mixed ligand/metal shells. Compare models on the same data and fit window. A lower R-factor from extra parameters is not sufficient evidence.

## 8. Audit and deliver

Run `scripts/audit_fit_log.py` and inspect the plots. Reject or clearly label results with:

- negative `σ²`;
- `|ΔR|` above the chosen physical limit (0.1 Å is a useful default warning, not a universal law);
- large `|ΔE0|` (10 eV is a useful warning after calibration);
- correlation >0.95;
- `Nvar >= Nind` or nearly saturated degrees of freedom;
- unstable values/errors, unused GDS variables, missing shell paths, or wrong degeneracies.

Deliver the calibrated data/project, foil `S0²` fit, sample DPJ/FPJ, CIF, FEFF input, fit log, numerical fit curves, parameter/path table, model comparison, calibration record, hashes, and source citations. State `R = Reff + ΔR` explicitly.
