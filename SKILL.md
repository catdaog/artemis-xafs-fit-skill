---
name: artemis-xafs-fit-skill
description: Calibrate XAFS standards, determine S0², build verified FEFF paths, run and audit staged Athena/Artemis EXAFS fits, and deliver reproducible raw, k-space, R-space, project, log, and parameter-table files. Use for energy correction, foil or compound standards, CIF/FEFF setup, coordination-number fits, numerical fit exports, or reproducible multi-element XAFS workflows; not for XANES linear-combination fitting alone.
---

# Artemis XAFS Fit Skill

Build a reproducible chain from raw/reference data to a checked Artemis project. Keep downloaded evidence, calibration choices, FEFF input, fit project, logs, numerical exports, and a short decision record together. Never overwrite the user's source project.

## Route the task

- For the complete foil → S0² → sample workflow, read [references/workflow.md](references/workflow.md).
- For absorber-edge choice, elemental-standard structures, coordination, and k-weight selection across elements, read [references/element-guidance.md](references/element-guidance.md).
- Before interpreting or reporting a fit, read [references/basic-principles.md](references/basic-principles.md) for the EXAFS equation, parameter correlations, Fourier-transform meaning, independent-point limit, and calibration-versus-`Delta E0` distinction.
- Before setting bounds, accepting parameters, or comparing models, read [references/parameter-constraints.md](references/parameter-constraints.md).
- For Athena/Artemis/FEFF downloads or transmission-sample mass, absorber loading, dilution, and edge-step calculations, read [references/software-and-sample-preparation.md](references/software-and-sample-preparation.md).
- Before returning results, read [references/deliverables.md](references/deliverables.md) and build the required file package. Numerical files are mandatory when a fit was run.
- Before downloading spectra or CIFs, read [references/sources.md](references/sources.md). Verify live URLs and licensing; record URL, retrieval time, hash, phase, and citation.
- When calling Demeter programmatically or repairing/rerunning an FPJ/DPJ, read [references/demeter-api.md](references/demeter-api.md).

## Required scientific invariants

1. Calibrate the simultaneously measured foil or accepted compound standard before fitting the standard or sample. Inspect `dμ/dE`; do not equate “highest derivative peak” with the correct feature for every edge. Use the beamline's stated calibration convention and record it. For Mo K-edge foil, use the first clear lower-energy inflection feature and set it to 20000 eV; the stronger second peak is not the calibration point.
2. Propagate one measured energy shift only to spectra collected under the same beamline/monochromator calibration. Do not copy a shift across unrelated runs merely because the element is the same.
3. Determine `S0²` using a standard measured at the same absorber edge, with known coordination and a physically defensible FEFF model. Fix the standard's crystallographic degeneracy while fitting `S0²`, `ΔE0`, `ΔR`, and `σ²` with a low-parameter model. Do not transfer `S0²` between unrelated absorber elements or edges without validation.
4. Fix the derived `S0²` for sample fitting unless the user explicitly requests a sensitivity analysis. Distinguish theoretical FEFF degeneracy, fitted effective CN, and fixed values.
5. Download an experimental CIF for the correct phase and verify formula, polymorph, space group, cell, occupancies, disorder, temperature, and source. A convenient structure is not automatically the right structure.
6. Add all materially contributing paths for the chosen R range. Start with the complete first shell, then extend to metal-metal, farther ligand, and multiple-scattering paths only when the window requires them. Select k weighting primarily from the dominant backscatterer, not automatically from the absorber. The historical Teo-Lee heuristic is `k³` for `Zscatterer < 36`, `k²` for `36 < Zscatterer < 57`, and `k¹` for `Zscatterer > 57`; mixed shells and modern quantitative fits should normally be checked with simultaneous k weights 1, 2, and 3.
7. Prefer the smallest identifiable parameterization. Reject negative `σ²`, unreasonable `|ΔR|`, extreme `ΔE0`, boundary hits, `Nvar >= Nind`, correlations above 0.95, or an inconsistent path/`ipot` mapping even if the R-factor is low.
8. Report distances as `R = Reff + ΔR`, not `Reff` alone. Report k/R windows, weights, windows, fixed parameters, path degeneracies, uncertainties, correlations, `Nind`, `Nvar`, reduced χ², and R-factor.
9. For transmission samples, calculate absorber mass from composition, edge, illuminated area, and target edge step. Do not reuse a fixed sample:BN ratio across materials. Treat total catalyst mass, absorber mass fraction, diluent mass, total optical thickness, and edge step as different quantities. A practical starting target is an edge step near 1, total optical thickness around 2–3, and edge step below about 1.5; verify with the beamline and measurement geometry.
10. Do not return plots or prose alone after fitting. The first and primary deliverable must be the final accepted `.fpj` or `.dpj` that Artemis can open directly. Reopen it in Artemis or load it with the matching Demeter project loader before delivery, and record the check; extension and non-zero file size alone do not prove project integrity. Next provide the processed `χ(k)` and k-weighted data/fit/residual tables, followed by the R-space magnitude/real/imaginary data/fit/residual table. Preserve untouched raw inputs, parameter tables, log, structural inputs, audit, and hashes as supporting files.
11. Never label simulated, reconstructed, example, or unexecuted output as fitted data. If Demeter/FEFF cannot run or required inputs are absent, return a missing-input or blocked-run record instead of fabricating numerical fit files.

## Reusable helpers

- `scripts/fetch_reference.py`: download a direct XAS/CIF URL or COD CIF ID, validate the payload, and write a provenance sidecar.
- `scripts/foil_calibrate.py`: list derivative-peak candidates, then apply a user-reviewed calibration feature without changing row order or non-energy columns.
- `scripts/run_demeter.ps1`: probe a Windows Demeter bundle and run a Perl/Demeter script in an isolated short-path runtime.
- `scripts/demeter_first_shell_fit.pl`: reproducible low-parameter first-shell fit with fixed `S0²`, explicit FEFF path indices, and configurable `σ²` grouping.
- `scripts/audit_fit_log.py`: machine-check common Artemis/Demeter failure modes.
- `scripts/suggest_xafs_settings.py`: report absorber/edge cautions, likely elemental-foil structure/CN, and Teo-Lee k-weight suggestions from the actual scatterers.
- `scripts/build_xafs_delivery.py`: validate and assemble the primary openable Artemis project first, k-space and R-space numerical data/fit exports next, then untouched raw files, parameter tables, models, logs, audit files, and a SHA256 manifest.

Use the helpers as building blocks, not as permission to select a phase, derivative peak, or FEFF paths without scientific inspection. If automatic and visual checks disagree, pause before changing calibration or the structural model.

## Completion contract

When a fit was actually run, completion requires a validated delivery directory following [references/deliverables.md](references/deliverables.md). At minimum it contains:

- `00_OPEN_FIRST/<final-fit>.fpj|.dpj`: exactly one non-empty final accepted project that opens directly in Artemis; this file must be linked first in the final response;
- `01_k_space/`: processed unweighted `χ(k)` plus k¹/k²/k³ data, fit, residual, and window columns, linked after the project;
- `02_r_space/`: unchanged magnitude/real/imaginary source exports and one combined R-space data/fit/residual table, linked after k-space;
- CSV/TSV and Markdown parameter tables that distinguish theoretical degeneracy, amplitude factor, fitted CN, fixed values, uncertainties, `Reff`, `ΔR`, and `R = Reff + ΔR`;
- byte-for-byte copies of all user raw inputs;
- fit log, CIF, `feff.inp`, calibration record, audit JSON, model comparison, and SHA256 manifest when applicable.

Reopen the primary project in Artemis (or load it with the matching Demeter project loader), record that application-level check, run `scripts/build_xafs_delivery.py` with `--artemis-project`, then run its `verify` mode on the result. The builder verifies suffix, non-zero size, copy hash, and package position; it does not replace the application-level reopen test. Preserve the original files and explicitly state whether any source file was modified. If the primary `.fpj`/`.dpj` is absent or cannot be opened, do not call the delivery complete. A fit is not complete merely because an Artemis plot or low R-factor exists.
