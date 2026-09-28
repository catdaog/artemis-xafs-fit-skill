# Software, downloads, and transmission-sample calculations

Verify the live landing page before downloading. Prefer official project or facility pages over third-party mirrors.

## 1. Athena, Artemis, and Hephaestus

Athena, Artemis, and Hephaestus are applications in the **Demeter** package; they are not separate Windows installers.

- Official Demeter home and Windows installer: `https://bruceravel.github.io/demeter/`
- Official source and releases: `https://github.com/bruceravel/demeter/releases`
- Athena user guide: `https://bruceravel.github.io/demeter/documents/Athena/index.html`
- Artemis user guide: `https://bruceravel.github.io/demeter/documents/Artemis/index.html`
- Hephaestus absorption/sample-mass guide: `https://bruceravel.github.io/demeter/documents/Athena/hephaestus.html`

The official Demeter page links its supported Windows installer and documents which version it contains. Record the installer version used in the fit provenance.

## 2. FEFF

- Official FEFF portal: `https://feff.phys.washington.edu/feffproject-portal.html`
- Official FEFF download page: `https://feff.phys.washington.edu/feffproject-feff-download.html`
- FEFF8 documentation: `https://feff.phys.washington.edu/feff/Docs/feff8/feff8web/`

The official download page distinguishes licensed FEFF releases from free FEFF6-lite/FEFF8-lite builds for EXAFS analysis. Confirm the executable and version actually used by Artemis rather than assuming that the newest installed FEFF is active.

## 3. Sample-mass and edge-step calculators

### XAFSmass

Use for powder mass, thickness, gas pressure, expected edge step, and formulas containing weight percentages.

- Documentation: `https://xafsmass.readthedocs.io/`
- Source: `https://github.com/kklmn/XAFSmass`
- PyPI: `https://pypi.org/project/XAFSmass/`
- Paper: `https://doi.org/10.1088/1742-6596/712/1/012008`

Install with `pip install xafsmass`, or run the source package as documented. Save the formula string, cross-section table, edge/energy, target optical thickness, pellet area, and calculated edge step.

### CatMass

Prefer CatMass for supported catalysts, several phases/metals, diluents, competing edges, or complex operando-cell compositions.

- Official Co-ACCESS software page: `https://web.slac.stanford.edu/coaccess/resources/software`
- Source: `https://github.com/ahoffm02/catMass`
- Documentation: `https://catmass.readthedocs.io/`
- Paper: `https://doi.org/10.1107/S160057752300615X`

### Hephaestus

Hephaestus is installed with Demeter. Its Formulas tool calculates absorption length, sample mass per illuminated area, transmitted fraction, and unit edge-step length from composition, density, and energy.

### Browser calculator

- Canadian Light Source X-Mass: `https://xasdb.lightsource.ca/xafsmass`

This browser tool calculates compound and diluent mass for a target edge step. Record all inputs and do not treat a web result as a substitute for beamline-specific advice.

## 4. Distinguish catalyst loading from XAS pellet mass

These quantities are related but are not interchangeable:

```text
absorber mass fraction, f_abs = mass of absorber element / mass of catalyst powder
catalyst loading, w_active = mass of active phase or metal / total catalyst mass
pellet mass = catalyst powder mass + diluent mass + other beam-path material
```

For a compound, obtain `f_abs` from stoichiometry. For a supported catalyst, use the measured metal loading if available; do not substitute the nominal synthesis loading without saying so. Include binder, support, cell windows, solvent, and other phases when they materially contribute to absorption.

For a target edge step, the edge-step method can be written:

```text
m_sample / A = Delta(mu*t)_target /
               [Delta(mu/rho)_absorber * f_abs]
```

where:

- `m_sample` is catalyst or compound mass, excluding separately calculated diluent;
- `A` is the illuminated pellet area, not automatically the full die area;
- `Delta(mu/rho)_absorber` is the mass-attenuation jump of the absorber at the selected edge;
- `f_abs` is the absorber-element mass fraction in the sample;
- `Delta(mu*t)_target` is the desired edge step.

Use a calculator rather than hand-tabulated coefficients for final preparation because the background matrix and chosen cross-section table matter.

## 5. Practical transmission targets

Beer-Lambert absorption is:

```text
mu*t = ln(I0 / It)
It/I0 = exp(-mu*t)
```

A robust starting design is:

- target edge step near `1`;
- total optical thickness around `2–3` above the edge;
- avoid edge step above about `1.5` for an inhomogeneous powder pellet;
- grind and mix until the absorber is uniform on a scale smaller than the absorption length;
- use BN, cellulose, PEG, graphite, or another matrix only after checking its absorption and chemical compatibility.

These are design targets, not universal acceptance limits. Cell windows and in situ hardware consume part of the total absorption budget. If a dilute absorber gives a very small edge step at the optimum total thickness, making the pellet thicker may only attenuate the beam; fluorescence detection may be the correct mode.

## 6. Calculation record template

Record the following before weighing:

```text
sample ID:
absorber and edge:
measured or nominal absorber loading:
full composition / formula string:
calculator and version:
cross-section table:
scan energy or edge + offset:
beam footprint and illuminated area:
holder area and thickness:
target edge step:
target total optical thickness:
sample mass:
diluent identity and mass:
predicted edge step and transmission:
measurement mode and cell-window contribution:
```

Never reuse an illustrative BN ratio for a new material. Recalculate when the absorber, edge, loading, support, pellet diameter, beam footprint, scan energy, or cell changes.
