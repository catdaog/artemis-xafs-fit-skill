# CIF discovery, construction and standard-to-sample execution

## Dependencies and boundaries

Python 3.10+; `pip install -r requirements.txt`. Gemmi may alternatively be installed in skill/.deps. Fitting/reload requires a working Windows Demeter bundle (default ~/DemeterPerl). Set XAFS_RUNTIME_ROOT to a short writable directory if the default temporary directory is unsuitable. Use short ASCII output paths for FEFF.

The helpers perform first-shell fits with shared DeltaE0/DeltaR, grouped sigma2 and optional grouped effective CN. They do not automatically perform full-shell model selection, fluorescence self-absorption correction, DFT relaxation, or uncertainty propagation from S02 into CN. XANES LCF remains outside this skill. Raw xmu input must be calibrated, two columns E[eV], mu; chi/YAML must have recorded preprocessing. Never relabel preprocessed chi as newly energy-calibrated.

## Find and verify a standard structure

```
python scripts/cif_tools.py search --formula MoO3 --output work/MoO3_candidates.json
python scripts/cif_tools.py search --formula MoO2 --output work/MoO2_candidates.json
python scripts/fetch_reference.py --cod-id SELECTED_ID --kind cif --output work/selected.cif
python scripts/cif_tools.py inspect work/selected.cif --output work/sites.json
```

Search uses the official COD JSON endpoint and retains all returned metadata. Formula alone does not select a polymorph. Inspect publication, phase, space group, cell, occupancies and measurement conditions before selecting. Record the selection rationale. If the endpoint fails, report network failure rather than a nonexistent structure. Downloaded CIF provenance comes from fetch_reference.py. COD: https://wiki.crystallography.net/RESTful_API/ ; Gemmi: https://gemmi.readthedocs.io/en/stable/chemistry.html .

## Generate or modify a CIF

`python scripts/cif_tools.py build --source work/selected.cif --spec work/change.json --output work/candidate.cif`

Example modification spec:
```json
{"supercell":[2,1,1],"remove":["3@1,0,0"],"substitute":{"0@0,0,0":"W"}}
```

IDs refer to the expanded unit-cell inventory from inspect; supercell IDs append `@i,j,k`. Do not reuse the example IDs without inspecting the actual structure. Supports an explicit six-value `cell`, `occupancies` map, atom deletion and element substitution. New structures omit --source and provide `cell` plus `sites` with element, frac, optional id and occupancy. New coordinates must come from an explicit user specification or cited structure; never invent a phase from its formula.

Output is an explicit P1 cell plus provenance JSON containing parent hash, operations and `constructed_unrelaxed_candidate`. P1 conversion changes the representation, not a claim of symmetry lowering. Partial occupancies are retained in CIF but rejected by FEFF export until an explicit ordered configuration is chosen. This helper checks syntax, finite positions, cell validity and exact overlap; it does not prove bond plausibility or thermodynamic stability. Inspect coordination and minimum distances before use. A generated CIF is not a relaxed structure.

## CIF -> FEFF input

```
python scripts/cif_tools.py feff work/candidate.cif --absorber-id 0 --radius 6 --output work/feff.inp
```

Currently K-edge FEFF6 clusters only (HOLE 1). Choose the actual absorber site from inspect. Check POTENTIALS/ATOMS, radius convergence and path degeneracies in Artemis before recording explicit path indices. Other edges require reviewed FEFF settings. Multiple inequivalent absorber sites require site-specific calculations; a single selected site is not a population average.

## One command: standard -> samples

Use examples/pipeline.template.json as a schema example; replace every placeholder, known CN, path index, range and review record with verified values. Standard and samples must share absorber/edge; calibration records must describe each acquisition batch. Apply energy corrections first using foil_calibrate.py; never propagate a shift across unrelated batches.

```
python scripts/fit_pipeline.py work/run.json --output C:/xafs/run_001
```

The runner validates inputs and stores hashes, fits the known-CN standard with free S02, audits the log, actually reloads the DPJ and compares all k/R exports and parameter values. It checks S02 and its uncertainty before fixing that S02 for each sample. The default S02 range 0.6–1.1 and maximum relative uncertainty 0.3 are screening gates, not universal physical laws; any override requires a recorded scientific rationale. A failure stops the run and writes pipeline_result.json; samples are never fitted after a failed standard.

Sample `amplitude_groups` uses `fixed` for crystallographic CN or group labels (e.g. `oxygen`) for shared amplitudes. Free effective CN is available only for single-scattering paths. Standard CN is fixed; standard S02 is fitted. Sample S02 is fixed; sample CN may be fixed or fitted. Fixed CN leaves cn_fit/cn_error blank and records cn_status=fixed; free CN reports degeneracy*amplitude plus conditional fitting error. Standard S02 uncertainty remains separate.

Successful execution ends at `review_required`, with real fit outputs, not automatic scientific acceptance. Inspect residuals, path completeness, correlations and window sensitivity; record acceptance/rejection in FIT_WORKFLOW.txt and set fit_status only for accepted parameter rows. Run build_xafs_delivery.py as documented in deliverables.md to assemble the nine files. `--project-check` text cannot bypass real reload. Both build and verify compare exports with the reloaded DPJ. A DPJ loading successfully does not make its model scientifically acceptable.
