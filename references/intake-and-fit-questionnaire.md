# Intake before fitting

## First message

Inspect the files and conversation first. If critical information is still missing, ask only: (1) what structure or coordination the fit should establish, (2) which files are the sample and same-edge standard and what the absorber edge is, and (3) which phase/CIF should be used. Do not ask the user to choose a numerical `S0²`; determine it by fitting the standard. If these items are already clear, start the workflow without repeating them.

Check the supplied files first, then ask only what is still missing:

1. **Purpose:** What should the experiment establish: oxidation state, a specific path, bond distance, CN, disorder, or phase?
2. **Data:** Which sample, reference, absorber, and edge correspond to each file? Were they measured and calibrated in the same run?
3. **Calibration:** What reference feature/energy was used, and what Athena processing has already been applied?
4. **Model:** Which phase/CIF is correct, and which paths are expected or must be tested?
5. **Parameters:** Which file is the same-edge, known-CN standard used to determine `S0²`, and which CN, `Delta E0`, `Delta R`, and `sigma²` values should be fixed, shared, or fitted?

Do not ask questions already answered by the user or metadata. If the goal is to support a specific path, compare a base model without it with a model containing it; use residuals, physical parameters, and complementary evidence rather than peak position alone.

## Defaults when unanswered

- Treat the task as a conservative structural-screening fit and write conclusions as “supports” or “is consistent with,” not “proves.”
- Infer file roles from metadata; if sample/reference mapping or the absorption edge is ambiguous, stop and ask instead of guessing.
- Preserve verified Athena settings. Reuse an energy correction only for spectra acquired in the same run; otherwise do not invent a shift and mark calibration as unverified.
- Always determine `S0²` first from a same-edge, known-CN standard, then fix that fitted value in the sample fit. If no suitable standard is available, ask for one or state that absolute CN cannot be determined reliably; never substitute an assumed default `S0²`.
- Initially fix CN to crystallographic degeneracy. Start with `Delta E0 = 0 eV`, `Delta R = 0 Å`, and `sigma² = 0.006 Å²`, then fit them within physically reasonable bounds.
- If data quality permits, start with `k = 3–12 Å⁻¹`, simultaneous `k` weights 1/2/3, and a Hanning window. Keep `Rmin >= Rbkg` and choose `Rmax` only to cover the modeled shells.
- Use the experimental CIF matching the known phase, include the complete first shell first, and add only the higher-shell or multiple-scattering paths needed by the fitting range and scientific question.
