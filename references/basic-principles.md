# XAFS and EXAFS fitting principles

Use this reference to explain what the workflow is fitting and to prevent numerically good but physically invalid models.

## 1. From absorption to EXAFS

For transmission XAS,

```text
mu(E)t = ln(I0 / It)
```

The absorption edge appears when the photon energy is sufficient to excite a core electron. XANES is dominated by electronic structure and multiple scattering near the edge. EXAFS is the oscillatory region farther above the edge, caused by interference between the outgoing photoelectron wave and waves scattered by neighboring atoms.

Convert energy above the threshold to photoelectron wave number:

```text
k = sqrt(2 me (E - E0)) / hbar
```

Changing `E0` therefore changes the phase of `chi(k)` and correlates strongly with fitted distance.

## 2. The working EXAFS equation

A standard single-scattering representation is:

```text
chi(k) = sum_j [Nj S0^2 Fj(k) / (k Rj^2)]
         * exp[-2Rj/lambda(k)]
         * exp[-2 sigma_j^2 k^2]
         * sin[2kRj + delta_j(k)]
```

Interpret the parameters as follows:

- `Nj`: coordination number or effective path degeneracy for shell `j`.
- `S0^2`: passive-electron amplitude reduction factor. Determine it from a known-coordination standard at the same absorber edge whenever possible.
- `Fj(k)`: backscattering amplitude calculated by FEFF; it depends strongly on the scatterer.
- `Rj`: absorber-scatterer distance.
- `lambda(k)`: photoelectron mean free path.
- `sigma_j^2`: mean-square relative displacement, including thermal and static disorder. A negative fitted value is not physical.
- `delta_j(k)`: total phase shift calculated by FEFF.
- `Delta E0`: fitted threshold correction that changes the k scale and phase.

The dominant amplitude scales approximately as `N*S0^2/R^2`. Consequently, `N` and `S0^2` are strongly correlated. Do not freely refine both without independent information. Fit `S0^2` on a standard with fixed known coordination, then fix it for related samples.

## 3. Fourier transform is not a literal radial distribution

Fourier transforming `k^n chi(k)` produces a complex `chi(R)` representation that separates contributions by apparent distance. The magnitude peak is normally shifted to lower R than the crystallographic distance because of the scattering phase. Do not read a bond length directly from an uncorrected magnitude peak. Obtain the final distance from the FEFF model and fitted shift:

```text
R = Reff + Delta R
```

Fit the real and imaginary information through the complex data/model, not only the magnitude envelope.

## 4. Energy calibration and fitted Delta E0 are different

- **Athena energy calibration** corrects the experimental monochromator energy scale using a simultaneously measured foil or accepted standard and a documented derivative feature.
- **Artemis `Delta E0`** compensates the residual difference between the chosen experimental threshold and FEFF's theoretical phase reference.

`Delta E0` is not a substitute for bad calibration. Propagate one measured calibration shift only to spectra collected under the same beamline and monochromator condition. For Mo K-edge foil, use the first clear lower-energy inflection feature at 20000 eV under the documented convention, not automatically the highest derivative peak.

## 5. Windows, k weighting, and resolution

- `kmin`/`kmax` control the usable oscillation range. Truncate before noise or another absorption edge dominates.
- `Rmin`/`Rmax` define which shells the model must explain.
- `dk` and `dR` are taper widths, not extra data range.
- A larger k weight emphasizes high-k signal; it does not create information. Choose weights from data quality and dominant backscatterers and validate mixed systems with simultaneous weights 1, 2, and 3.

Finite k range limits radial resolution approximately as:

```text
Delta R_resolution ~= pi / (2 Delta k)
```

Two shells closer than this are unlikely to be independently identifiable without strong constraints or complementary evidence.

## 6. Independent points and parameter budget

Use the usual Stern estimate:

```text
Nind ~= 2 Delta k Delta R / pi + 2
```

Keep `Nvar` comfortably below `Nind`; merely satisfying `Nvar < Nind` does not prove uniqueness. Count shared and constrained variables honestly. Review the correlation matrix, especially `N` versus `S0^2`, `Delta E0` versus `Delta R`, and `N` versus `sigma^2`.

## 7. FEFF paths and structural models

FEFF generates path geometry, degeneracy, scattering amplitude, and phase from the structural model. `ipot` identifies scattering species; a wrong `ipot` mapping invalidates the path even if the curve looks good.

Start with all materially contributing paths in the selected R window:

1. complete nearest-neighbor shell;
2. metal-metal or farther ligand shells required by the window;
3. focused or important multiple-scattering paths;
4. only then optional weak paths supported by the residuals and chemistry.

Compare nested models using residual structure, parameter stability, uncertainty, correlations, and physical plausibility. A lower R-factor alone does not justify another shell.

## 8. Minimum physical audit

Reject or repair a model when it has negative `sigma^2`, extreme `Delta E0`, implausible `Delta R`, a parameter pinned at a boundary, correlation above about 0.95, missing dominant paths, inconsistent `ipot`, or unstable results across reasonable k/R windows. Report both the accepted model and the key rejected alternative.

## Primary learning references

- Demeter/Athena/Artemis documentation: `https://bruceravel.github.io/demeter/`
- Artemis fitting guide: `https://bruceravel.github.io/demeter/artug/fit/index.html`
- FEFF project documentation: `https://feff.phys.washington.edu/feffproject-portal.html`
- Ravel and Newville, *J. Synchrotron Rad.* 12 (2005) 537–541: `https://doi.org/10.1107/S0909049505012719`
- Stern's independent-point discussion: `https://doi.org/10.1103/PhysRevB.48.9825`
