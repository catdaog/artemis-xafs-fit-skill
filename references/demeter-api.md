# Demeter programmatic interface

## Windows runtime

Demeter 0.9.26 Windows bundles commonly ship their own Perl, IFEFFIT, FEFF6, PGPLOT, and gnuplot. Use `scripts/run_demeter.ps1 -Action probe` to locate and validate the bundle. For a run, the wrapper sets `DEMETER_BASE`, `IFEFFIT_DIR`, `PGPLOT_FONT`, `FONTCONFIG_FILE`, locale variables, and an isolated `APPDATA`.

Legacy FEFF6 has fixed-width path buffers. Keep the runtime/output path short. A failure in a deep directory can be a path-length problem even when `feff.inp` is valid.

## Object graph

A fit consists of:

- one or more `Demeter::Data` objects;
- a `Demeter::Feff` calculation and selected scattering paths;
- `Demeter::GDS` parameters;
- `Demeter::Path` objects connecting FEFF paths to data;
- a `Demeter::Fit` object.

Every `guess`/`def` should be used, every path expression should reference a defined GDS parameter, and every intended path must be included.

Minimal pattern:

```perl
use Demeter;
my $data = Demeter::Data->new;
$data->deserialize($data_yaml);
my $feff = Demeter::Feff->new(file => $feff_inp);
$feff->set(workspace => $short_workspace, screen => 0);
$feff->make_workspace;
$feff->run;
my @sp = $feff->list_of_paths;
my $enot = Demeter::GDS->new(gds=>'guess', name=>'enot', mathexp=>'0');
my $dr   = Demeter::GDS->new(gds=>'guess', name=>'dr',   mathexp=>'0');
my $ss   = Demeter::GDS->new(gds=>'guess', name=>'ss',   mathexp=>'0.003');
my $path = Demeter::Path->new(
  parent=>$feff, sp=>$sp[0], data=>$data,
  n=>$sp[0]->n, s02=>'0.90', e0=>'enot', delr=>'dr', sigma2=>'ss'
);
my $fit = Demeter::Fit->new(data=>[$data], paths=>[$path],
                            gds=>[$enot,$dr,$ss], interface=>'automation');
$fit->fit;
$fit->logfile($log, 'data', 'model');
$fit->freeze(file=>$dpj);
```

`scripts/demeter_first_shell_fit.pl` generalizes this to explicit zero-based FEFF path indices and `σ²` groups. Always inspect the path list before choosing indices.

## Data and project handling

- Prefer calibrated Athena project data or serialized Demeter YAML over re-reading ambiguous columns.
- Some serialized YAML contains a read-only `xdifile` attribute; the provided driver writes a sanitized copy in its output directory before deserializing.
- An FPJ is a project archive with fit snapshots. Inspect `order`, current fit, data YAML, GDS, paths, FEFF input, and logs before deciding which state is authoritative.
- Preserve the input FPJ/DPJ. Write a new project and verify it by reloading and refitting.

## Fit settings and exports

Set k/R windows and weights explicitly. Typical calls use R-space fitting with k weights 1, 2, and 3, but the data determine the valid range.

Useful exports:

```perl
$data->save('chi', $chi_file);
for my $kw (1, 2, 3) {
    $data->save('fit', $k_file[$kw], "k$kw");
    $data->po->kweight($kw);
    $data->save('fit', $rmag_file[$kw], 'rmag');
    $data->save('fit', $rre_file[$kw],  'rre');
    $data->save('fit', $rim_file[$kw],  'rim');
}
```

For `save('chi', ...)`, Demeter writes k, χ(k), kχ(k), k²χ(k), k³χ(k), and the k window. Fit exports contain coordinate, data, fit, residual, optional background/running term, and window. Report the exact export mode.

Export k1, k2, and k3 from the same accepted fit snapshot. For each R1/R2/R3 file, first set the plot k-weight to 1/2/3 and then export rmag, rre, and rim on the same R grid. Use `scripts/build_xafs_delivery.py` to combine each weight's three components and verify grids, residual columns, and parameter arithmetic. Do not derive R-space real/imaginary values from magnitude or from a screenshot.

## Parameterization

- `s02` is the path amplitude expression. Fix it to the foil-derived `S0²` for sample fits.
- FEFF degeneracy `n` supplies theoretical path multiplicity. To fit effective CN, use an explicit amplitude factor and state `CN = amp × n`.
- Tie related paths only with a structural reason. Split shells can share `ΔR` while using a small number of `σ²` groups.
- A low R-factor does not rescue negative `σ²`, extreme shifts, missing paths, or unidentifiable variables.

## Parameter and statistics files

The provided `demeter_first_shell_fit.pl` writes:

- `chi_k.dat`;
- `fit_k1.dat`, `fit_k2.dat`, `fit_k3.dat`;
- `fit_r1_mag/re/im.dat`, `fit_r2_mag/re/im.dat`, and `fit_r3_mag/re/im.dat`;
- one `fit_parameters.tsv` table;
- `FIT_WORKFLOW.txt`, `fit_statistics.tsv`, `summary.tsv`, `fit.log`, and `fit.dpj`.

The parameter table separates FEFF degeneracy, amplitude factor, fitted CN, `Reff`, `ΔR`, final `R`, uncertainties, fixed `S0²`, and fit status. Mark the initial automated result `unreviewed`; only change it to accepted after the fit-log audit and visual/residual checks pass.
