# Element, edge, standard, and k-weight guidance

## Distinguish absorber from scatterer

The absorber selects the measured edge and the central atom in FEFF. The neighboring atom controls the backscattering-amplitude shape. Therefore the historical atomic-number rule for `k^n` weighting is more correctly applied to the dominant **backscatterer** `Z`, not automatically to the absorber `Z`.

For an elemental foil, absorber and backscatterer are the same element, so the distinction disappears. For an oxide such as MoO3, the first shell is O (`Z=8`) while later shells contain Mo (`Z=42`); one absorber-based weight cannot represent both equally.

## Teo-Lee historical k-weight heuristic

Teo and Lee's 1979 amplitude/phase work motivated a commonly repeated guide:

- `Zscatterer < 36`: emphasize high k with `k³`;
- `36 < Zscatterer < 57`: use `k²`;
- `Zscatterer > 57`: use `k¹`.

The stated inequalities do not assign the boundary elements `Z=36` and `Z=57`; treat them as boundary cases and inspect the actual amplitude. This is a starting heuristic, not a universal fitting law. It compensates qualitatively for how backscattering amplitude changes with k and Z.

For modern Artemis fits:

- plot the historically suggested weight for visual inspection;
- fit/check k weights 1, 2, and 3 simultaneously when the data support them;
- use multiple weights for mixed scatterers or multiple shells;
- check whether parameters remain stable when weights/windows are varied;
- never choose weight solely to make one R-space peak look large.

Primary source: B.-K. Teo and P. A. Lee, *J. Am. Chem. Soc.* **101** (1979) 2815–2832, DOI `10.1021/ja00505a003`.

## Edge choice and S0² transfer

- Use the same absorber and absorption edge for the standard-derived `S0²` and the sample whenever possible.
- K edges are commonly used for 3d metals and many medium-Z elements when the beamline energy range allows.
- L3 edges are commonly used for lanthanides and 5d/heavier metals; high-energy K edges may be unavailable or yield different experimental constraints.
- Soft-X-ray L/M edges require vacuum-compatible detection and different practical preprocessing; do not apply a hard-X-ray foil recipe blindly.
- Obtain the reference energy and calibration convention from the beamline or a cited standard table (for example Demeter/Hephaestus), then verify the actual derivative shape.
- Do not transfer a K-edge `S0²` to an L-edge fit, or between different absorbers, merely because the materials are similar.

## Common elemental-metal standard structures

This table is for choosing a starting standard model at ambient conditions; verify the actual foil phase and temperature from a CIF/reference.

| Structure | Common examples | Nominal first-shell CN | Caution |
|---|---|---:|---|
| fcc | Al, Ni, Cu, Rh, Pd, Ag, Ir, Pt, Au, Pb | 12 | verify alloying, texture, nanoparticles, and temperature |
| bcc | V, Cr, alpha-Fe, Nb, Mo, Ta, W | 8 | second shell has 6 neighbors; phase of Fe must be explicit |
| hcp | Mg, alpha-Ti, hcp-Co, Zn, Zr, Ru, Cd, Hf, Re, Os | nominally 12 | non-ideal c/a can split the 12 neighbors into distinct distances |

Do not force simple fcc/bcc/hcp models onto alpha-Mn, Ga, In, Sn polymorphs, Hg, intermetallics, or visibly oxidized standards. Download and inspect the appropriate structure.

## Standard selection

1. Prefer a simultaneously measured elemental foil of the absorber when stable and suitable.
2. If no good foil exists, use a well-characterized compound standard with known local coordination at the same edge.
3. Fix crystallographic degeneracy for the `S0²` fit; do not fit CN and `S0²` independently from a single shell without an additional constraint.
4. Check self-absorption, pinholes/thickness, oxidation, detector nonlinearity, glitches, and scan reproducibility before blaming the model.

Run `scripts/suggest_xafs_settings.py --absorber Mo --scatterers O,Mo --edge K` (replace the elements) for a machine-readable starting report.
