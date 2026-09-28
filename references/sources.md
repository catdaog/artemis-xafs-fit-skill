# Reference-data and CIF sources

Verify these links live before use. Prefer primary repositories and the user's simultaneous foil over downloaded spectra.

## Calibration and Demeter documentation

- Demeter official home/download page: `https://bruceravel.github.io/demeter/`
- Demeter official source/releases: `https://github.com/bruceravel/demeter/releases`
- SSRL Edge Analysis: `https://www-ssrl.slac.stanford.edu/pickering/workshop/edgeanalysis.html`
  - Documents use of the first inflection for calibration and the Mo case where the strongest derivative peak is the second feature.
- Demeter/Artemis fit guide: `https://bruceravel.github.io/demeter/artug/fit/index.html`
- Demeter programming documentation: `https://bruceravel.github.io/demeter/pods/index.html`
- Artemis data/project settings: `https://bruceravel.github.io/demeter/documents/Athena/output/project.html`
- Demeter fit output formats: `https://bruceravel.github.io/demeter/documents/DPG/output.html`
- Teo and Lee amplitude/phase calculations: `https://doi.org/10.1021/ja00505a003`
  - Historical basis for choosing `k^n` with the atomic number of the dominant backscatterer; use as a heuristic and check multiple k weights.

## Sample preparation and absorption calculations

- XAFSmass documentation/source: `https://xafsmass.readthedocs.io/` and `https://github.com/kklmn/XAFSmass`
- CatMass official Co-ACCESS page/source: `https://web.slac.stanford.edu/coaccess/resources/software` and `https://github.com/ahoffm02/catMass`
- Canadian Light Source X-Mass browser calculator: `https://xasdb.lightsource.ca/xafsmass`
- Hephaestus absorption/sample-mass documentation: `https://bruceravel.github.io/demeter/documents/Athena/hephaestus.html`
- Stern and Kim thickness-effect paper: `https://doi.org/10.1103/PhysRevB.23.3781`

See [software-and-sample-preparation.md](software-and-sample-preparation.md) for formulas, target ranges, software selection, and the required calculation record.

## FEFF

- FEFF official portal: `https://feff.phys.washington.edu/feffproject-portal.html`
- FEFF official download page: `https://feff.phys.washington.edu/feffproject-feff-download.html`
- FEFF8 documentation: `https://feff.phys.washington.edu/feff/Docs/feff8/feff8web/`

## CIFs

1. Crystallography Open Database (COD): `https://www.crystallography.net/cod/`
   - A known entry can normally be fetched as `https://www.crystallography.net/cod/<COD_ID>.cif`.
   - Record COD ID and the bibliographic fields contained in the CIF.
2. ICSD: use only through an authorized institutional license; do not automate around access controls.
3. Materials Project or other computed databases: label structures as calculated. Do not silently substitute a relaxed theoretical structure for an experimental CIF.

Do not select a CIF by formula alone. Check phase, space group, cell, occupancies, disorder, temperature, publication, and whether the absorber environment matches the sample.

## XAS reference spectra

- XASLIB documentation: `https://docs.xrayabsorption.org/xaslib/`
- RefXAS publication/database description: `https://journals.iucr.org/s/issues/2024/05/00/up5002/`
- Diamond Light Source XAS resources: `https://www.diamond.ac.uk/Instruments/Techniques/Spectroscopy/XAS`
- International X-ray Absorption Society data-format guidance: `https://xrayabsorption.org/q2xafs2024_dataformats/`

Repository interfaces and direct download URLs can change. Search the official site, identify the exact record and its license, then pass a direct download URL to `scripts/fetch_reference.py`. Save XDI where available and retain metadata. External spectra are comparison standards; they do not establish the monochromator shift for the user's beamtime.

## Provenance minimum

For every downloaded file record:

- direct URL and landing-page URL;
- repository and record ID;
- retrieval UTC time and SHA256;
- license/access basis;
- material, phase, edge, temperature, and measurement mode;
- linked paper/DOI;
- any conversion, column mapping, or structural transformation.
