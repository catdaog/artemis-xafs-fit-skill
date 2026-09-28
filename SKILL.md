---
name: artemis-xafs-fit-skill
description: Calibrate elemental or compound XAFS standards across absorber elements and edges, determine S0² from known coordination, select k weights from scatterer chemistry and data quality, obtain verified CIF structures, run FEFF/Demeter/Artemis EXAFS fits, and audit fit quality. Use for Athena energy correction, Artemis fitting, FEFF path setup, foil calibration, coordination-number standards, CIF acquisition, or reproducible multi-element XAFS workflows; not for XANES linear-combination fitting alone.
---

# Artemis XAFS Fit Skill

Build a reproducible chain from raw/reference data to a checked Artemis project. Keep downloaded evidence, calibration choices, FEFF input, fit project, logs, numerical exports, and a short decision record together. Never overwrite the user's source project.

## Route the task

- For the complete foil → S0² → sample workflow, read [references/workflow.md](references/workflow.md).
- For absorber-edge choice, elemental-standard structures, coordination, and k-weight selection across elements, read [references/element-guidance.md](references/element-guidance.md).
- Before interpreting or reporting a fit, read [references/basic-principles.md](references/basic-principles.md) for the EXAFS equation, parameter correlations, Fourier-transform meaning, independent-point limit, and calibration-versus-`Delta E0` distinction.
- For Athena/Artemis/FEFF downloads or transmission-sample mass, absorber loading, dilution, and edge-step calculations, read [references/software-and-sample-preparation.md](references/software-and-sample-preparation.md).
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

## Reusable helpers

- `scripts/fetch_reference.py`: download a direct XAS/CIF URL or COD CIF ID, validate the payload, and write a provenance sidecar.
- `scripts/foil_calibrate.py`: list derivative-peak candidates, then apply a user-reviewed calibration feature without changing row order or non-energy columns.
- `scripts/run_demeter.ps1`: probe a Windows Demeter bundle and run a Perl/Demeter script in an isolated short-path runtime.
- `scripts/demeter_first_shell_fit.pl`: reproducible low-parameter first-shell fit with fixed `S0²`, explicit FEFF path indices, and configurable `σ²` grouping.
- `scripts/audit_fit_log.py`: machine-check common Artemis/Demeter failure modes.
- `scripts/suggest_xafs_settings.py`: report absorber/edge cautions, likely elemental-foil structure/CN, and Teo-Lee k-weight suggestions from the actual scatterers.

Use the helpers as building blocks, not as permission to select a phase, derivative peak, or FEFF paths without scientific inspection. If automatic and visual checks disagree, pause before changing calibration or the structural model.

## Deliverables

Return a runnable DPJ/FPJ or exact Artemis parameter table, fit log, fit curves as numerical data, CIF and FEFF input with provenance, calibration record, model-comparison table, and a concise note separating accepted results from rejected alternatives. Preserve the original files and explicitly state whether they were modified.
