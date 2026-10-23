#!/usr/bin/env perl
use strict;
use warnings;
use Getopt::Long qw(GetOptions);
use File::Path qw(make_path);
use File::Spec;
use JSON::PP;

# Demeter 0.9.26 on Windows can leave a nonzero $? during Larch cleanup even
# after every fit/export operation succeeds. Register this END block before
# loading Demeter so it runs last, and clear the status only after this script
# has written every required output.
our $RUN_COMPLETED = 0;
END { $? = 0 if $RUN_COMPLETED; }

use Demeter;

sub tsv_clean {
    my ($value) = @_;
    $value = '' unless defined $value;
    $value =~ s/[\t\r\n]+/ /g;
    return $value;
}

my ($datafile, $feffinp, $outdir, $s02, $path_csv, $group_csv);
my ($mode,$datatype,$sample_name)=('sample','chi','XAFS data');
my ($amp_csv,$expected_cn,$bkg_e0);
my $rbkg=1.0;
my ($rmin, $rmax, $kmin, $kmax) = (1.0, 2.5, 3.0, 12.0);
my $kweights = '1,2,3';
GetOptions(
    'data=s'         => \$datafile,
    'feff=s'         => \$feffinp,
    'out=s'          => \$outdir,
    's02=f'          => \$s02,
    'paths=s'        => \$path_csv,
    'sigma-groups=s' => \$group_csv,
    'rmin=f'         => \$rmin,
    'rmax=f'         => \$rmax,
    'kmin=f'         => \$kmin,
    'kmax=f'         => \$kmax,
    'kweights=s'     => \$kweights,
    'mode=s'         => \$mode,
    'amplitude-groups=s' => \$amp_csv,
    'expected-cn=f'  => \$expected_cn,
    'datatype=s'     => \$datatype,
    'sample-name=s'  => \$sample_name,
    'bkg-e0=f'       => \$bkg_e0,
    'rbkg=f'         => \$rbkg,
) or die "invalid arguments\n";
die "usage: demeter_first_shell_fit.pl --data DATA --feff FEFF.INP --out DIR "
  . "--s02 VALUE --paths 0,1,... --sigma-groups 0,0,... [--rmin 1 --rmax 2.5]\n"
  unless defined $datafile && defined $feffinp && defined $outdir
      && defined $path_csv && defined $group_csv;
die "mode must be standard or sample\n" unless $mode eq 'standard' || $mode eq 'sample';
die "datatype must be chi or xmu\n" unless $datatype eq 'chi' || $datatype eq 'xmu';
die "standard requires independently known --expected-cn and no amplitude groups\n"
 if $mode eq 'standard' && (!defined($expected_cn) || $expected_cn<=0 || defined($amp_csv));
$s02=0.9 if $mode eq 'standard' && !defined($s02);
die "sample requires standard-derived --s02\n" unless defined $s02;
die "S02 must be >0 and <=1.5\n" unless $s02 > 0 && $s02 <= 1.5;
die "invalid k or R range\n" unless $kmax > $kmin && $rmax > $rmin;
my %use_kw = map { int($_) => 1 } split /,/, $kweights;
die "kweights must be a comma-separated subset of 1,2,3\n"
  if !%use_kw || grep { $_ < 1 || $_ > 3 } keys %use_kw;

my @indices = map { int($_) } split /,/, $path_csv;
my @groups  = split /,/, $group_csv;
die "paths and sigma-groups must have equal nonzero length\n"
  unless @indices && @indices == @groups;
for (@groups) {
    s/^\s+|\s+$//g;
    die "sigma group names may contain only letters, digits, underscore, or dash\n"
      unless /^[A-Za-z0-9_-]+$/;
    tr/-/_/;
}
my @amps = defined($amp_csv) ? split(/,/, $amp_csv) : map {'fixed'} @indices;
die "amplitude groups must match path count\n" unless @amps==@indices;
for (@amps) { die "invalid amplitude group\n" unless /^[A-Za-z][A-Za-z0-9_]*$/; }
die "duplicate path indices\n" unless scalar(keys %{ {map {$_=>1} @indices} })==@indices;
make_path($outdir) unless -d $outdir;

my $loadfile = $datafile;
if ($datafile =~ /\.ya?ml\z/i) {
    $loadfile = File::Spec->catfile($outdir, 'data.sanitized.yaml');
    open my $in, '<', $datafile or die "cannot read $datafile: $!\n";
    open my $out, '>', $loadfile or die "cannot write $loadfile: $!\n";
    while (my $line = <$in>) {
        next if $line =~ /^xdifile\s*:/;
        print {$out} $line;
    }
    close $in;
    close $out;
}

my $data;
if ($loadfile =~ /\.ya?ml\z/i) {
    $data = Demeter::Data->new;
    $data->deserialize($loadfile);
    $data->name($sample_name);
} else {
    $data = $datatype eq 'chi'
      ? Demeter::Data->new(file=>$loadfile, datatype=>'chi', chi_column=>'2', name=>$sample_name)
      : Demeter::Data->new(file=>$loadfile, datatype=>'xmu', energy=>'1', numerator=>'2', denominator=>'', ln=>0, name=>$sample_name);
    $data->set(bkg_rbkg=>$rbkg) if $datatype eq 'xmu';
    $data->set(bkg_e0=>$bkg_e0) if $datatype eq 'xmu' && defined($bkg_e0);
    $data->_update('data');
}
my $transcript = File::Spec->catfile($outdir, 'ifeffit_transcript.iff');
$data->set_mode(screen => 0, backend => 1, file => ">$transcript");
$data->set(
    fft_kmin => $kmin, fft_kmax => $kmax, fft_dk => 1.0, fft_kwindow => 'Hanning',
    bft_rmin => $rmin, bft_rmax => $rmax, bft_dr => 0.0, bft_rwindow => 'Hanning',
    fit_space => 'r', fit_k1 => ($use_kw{1} ? 1 : 0),
    fit_k2 => ($use_kw{2} ? 1 : 0), fit_k3 => ($use_kw{3} ? 1 : 0),
    fit_do_bkg => 0, fit_epsilon => 0,
);

my $feffwork = File::Spec->catdir($outdir, 'feff');
my $feff = Demeter::Feff->new(file => $feffinp);
$feff->set(workspace => $feffwork, screen => 0);
$feff->make_workspace;
$feff->run;
my @sp = $feff->list_of_paths;
for my $idx (@indices) {
    die "FEFF path index $idx is unavailable; inspect the path list first\n"
      if $idx < 0 || $idx > $#sp;
}
if ($mode eq 'standard') {
 my $total=0; $total+=$sp[$_]->n for @indices;
 die "selected standard paths do not sum to expected known CN\n" if abs($total-$expected_cn)>1e-8;
 die "known CN calibration requires single-scattering paths\n" if grep {$sp[$_]->nleg != 2} @indices;
}
for my $i (0 .. $#indices) {
 die "effective CN fitting requires single-scattering paths\n" if $amps[$i] ne 'fixed' && $sp[$indices[$i]]->nleg != 2;
}

my @gds = (
    Demeter::GDS->new(gds => 'guess', name => 'enot',   mathexp => '0'),
    Demeter::GDS->new(gds => 'guess', name => 'dr_all', mathexp => '0'),
);
my %seen;
for my $group (@groups) {
    next if $seen{$group}++;
    push @gds, Demeter::GDS->new(
        gds => 'guess', name => "ss_$group", mathexp => '0.003'
    );
}
push @gds, Demeter::GDS->new(gds=>'guess',name=>'s02_std',mathexp=>"$s02") if $mode eq 'standard';
my %seen_amp;
for my $g (@amps) {
 next if $g eq 'fixed' || $seen_amp{$g}++;
 push @gds, Demeter::GDS->new(gds=>'guess',name=>"amp_$g",mathexp=>'1');
}

my @paths;
for my $i (0 .. $#indices) {
    my $idx = $indices[$i];
    my $sp = $sp[$idx];
    my $name = sprintf('FEFF[%d] %s Reff=%.5f', $idx, $sp->scatterer, $sp->halflength);
    push @paths, Demeter::Path->new(
        name => $name, parent => $feff, sp => $sp, data => $data, n => $sp->n,
        s02 => ($mode eq 'standard' ? 's02_std' : ($amps[$i] eq 'fixed' ? "$s02" : "$s02 * amp_$amps[$i]")),
        e0 => 'enot', delr => 'dr_all', sigma2 => "ss_$groups[$i]",
    );
}

my $fit = Demeter::Fit->new(
    data => [$data], paths => \@paths, gds => \@gds,
    interface => 'artemis-xafs-fit-skill first-shell driver',
);
my $returned = $fit->fit;
die "fit did not return its Fit object\n" unless $returned eq $fit;
my %fitted_gds=map {$_->name=>$_} @gds;
my $s02_error='';
if ($mode eq 'standard') {
 $s02=$fitted_gds{s02_std}->bestfit;
 $s02_error=$fitted_gds{s02_std}->error;
}

$fit->logfile(File::Spec->catfile($outdir, 'fit.log'), 'XAFS data', 'first shell');
$fit->freeze(file => File::Spec->catfile($outdir, 'fit.dpj'));
$data->save('chi', File::Spec->catfile($outdir, 'chi_k.dat'));
$data->save('fit', File::Spec->catfile($outdir, 'fit_k1.dat'), 'k1');
$data->save('fit', File::Spec->catfile($outdir, 'fit_k2.dat'), 'k2');
$data->save('fit', File::Spec->catfile($outdir, 'fit_k3.dat'), 'k3');
for my $kw (1, 2, 3) {
    $data->po->kweight($kw);
    $data->save('fit', File::Spec->catfile($outdir, "fit_r${kw}_mag.dat"), 'rmag');
    $data->save('fit', File::Spec->catfile($outdir, "fit_r${kw}_re.dat"),  'rre');
    $data->save('fit', File::Spec->catfile($outdir, "fit_r${kw}_im.dat"),  'rim');
}
# Retain explicit k2 aliases only for the optional legacy audit profile.
$data->po->kweight(2);
$data->save('fit', File::Spec->catfile($outdir, 'fit_rmag.dat'), 'rmag');
$data->save('fit', File::Spec->catfile($outdir, 'fit_rre.dat'),  'rre');
$data->save('fit', File::Spec->catfile($outdir, 'fit_rim.dat'),  'rim');

open my $summary, '>', File::Spec->catfile($outdir, 'summary.tsv')
  or die "cannot write summary.tsv: $!\n";
print {$summary} "s02_$mode\t$s02\n";
print {$summary} "k_range\t$kmin-$kmax\n";
print {$summary} "kweights\t" . join(',', sort { $a <=> $b } keys %use_kw) . "\n";
print {$summary} "r_range\t$rmin-$rmax\n";
print {$summary} "r_factor\t" . $fit->r_factor . "\n";
print {$summary} "chi_square\t" . $fit->chi_square . "\n";
print {$summary} "chi_reduced\t" . $fit->chi_reduced . "\n";
print {$summary} "n_idp\t" . $fit->n_idp . "\n";
print {$summary} "n_varys\t" . $fit->n_varys . "\n";
print {$summary} "parameter\tvalue\terror\n";
for my $g (@gds) {
    print {$summary} join("\t", $g->name, $g->bestfit, $g->error), "\n";
}
print {$summary} "path_index\tscatterer\tdegeneracy\treff\tdelr\tsigma2_group\n";
for my $i (0 .. $#indices) {
    my $sp = $sp[$indices[$i]];
    print {$summary} join("\t", $indices[$i], $sp->scatterer, $sp->n,
                          $sp->halflength, 'dr_all', "ss_$groups[$i]"), "\n";
}
close $summary;

my %gds_by_name = map { $_->name => $_ } @gds;
my $e0_value = $gds_by_name{enot}->bestfit;
my $e0_error = $gds_by_name{enot}->error;
my $dr_value = $gds_by_name{dr_all}->bestfit;
my $dr_error = $gds_by_name{dr_all}->error;

my @parameter_columns = qw(
    sample path_index path scatterer degeneracy_theory amplitude_factor cn_fit
    reff_A delr_A delr_error_A r_fit_A sigma2_A2 sigma2_error_A2
    e0_eV e0_error_eV s02 s02_status r_factor fit_status notes cn_status cn_error s02_error
);
open my $ptable, '>', File::Spec->catfile($outdir, 'fit_parameters.tsv')
  or die "cannot write fit_parameters.tsv: $!\n";
print {$ptable} join("\t", @parameter_columns), "\n";

for my $i (0 .. $#indices) {
    my $sp = $sp[$indices[$i]];
    my $ss_name = "ss_$groups[$i]";
    my $ss_value = $gds_by_name{$ss_name}->bestfit;
    my $ss_error = $gds_by_name{$ss_name}->error;
    my $reff = $sp->halflength;
    my $rfit = $reff + $dr_value;
    my $degeneracy = $sp->n;
    my $path_name = sprintf('FEFF[%d] %s', $indices[$i], $sp->scatterer);
    my $amp=$amps[$i] eq 'fixed' ? 1 : $gds_by_name{"amp_$amps[$i]"}->bestfit;
    my $cn=$amps[$i] eq 'fixed' ? '' : $degeneracy*$amp;
    my $cn_error=$amps[$i] eq 'fixed' ? '' : $degeneracy*$gds_by_name{"amp_$amps[$i]"}->error;
    my @values = (
        $sample_name, $indices[$i], $path_name, $sp->scatterer,
        $degeneracy, $amp, $cn, $reff, $dr_value, $dr_error, $rfit,
        $ss_value, $ss_error, $e0_value, $e0_error, $s02, ($mode eq 'standard' ? 'fitted' : 'fixed'),
        $fit->r_factor, 'unreviewed', "first-shell; delR=dr_all; sigma2=$ss_name",
        ($amps[$i] eq 'fixed' ? 'fixed' : 'fitted'), $cn_error, $s02_error,
    );
    print {$ptable} join("\t", map { tsv_clean($_) } @values), "\n";
}
close $ptable;

open my $stats, '>', File::Spec->catfile($outdir, 'fit_statistics.tsv')
  or die "cannot write fit_statistics.tsv: $!\n";
print {$stats} "metric\tvalue\tunit\tnotes\n";
print {$stats} "sample\tXAFS data\t\t\n";
print {$stats} "fit_space\tr\t\tcomplex R-space fit\n";
print {$stats} "kmin\t$kmin\tA^-1\t\n";
print {$stats} "kmax\t$kmax\tA^-1\t\n";
print {$stats} "kweights\t" . join(',', sort { $a <=> $b } keys %use_kw) . "\t\t\n";
print {$stats} "rmin\t$rmin\tA\t\n";
print {$stats} "rmax\t$rmax\tA\t\n";
print {$stats} "nind\t" . $fit->n_idp . "\t\t\n";
print {$stats} "nvar\t" . $fit->n_varys . "\t\t\n";
print {$stats} "r_factor\t" . $fit->r_factor . "\t\t\n";
print {$stats} "chi_square\t" . $fit->chi_square . "\t\t\n";
print {$stats} "reduced_chi_square\t" . $fit->chi_reduced . "\t\t\n";
print {$stats} "s02\t$s02\t\tmode=$mode; standard fitted, sample fixed\n";
close $stats;

open my $workflow, '>', File::Spec->catfile($outdir, 'FIT_WORKFLOW.txt')
  or die "cannot write FIT_WORKFLOW.txt: $!\n";
print {$workflow} "XAFS FIT WORKFLOW — XAFS data\n";
print {$workflow} "=================================\n\n";
print {$workflow} "Input spectrum: $datafile\n";
print {$workflow} "FEFF input: $feffinp\n";
print {$workflow} "S0^2: $s02; mode=$mode (standard fitted, sample fixed)\n";
print {$workflow} "k range: $kmin-$kmax A^-1\n";
print {$workflow} "simultaneous k weights: " . join(',', sort { $a <=> $b } keys %use_kw) . "\n";
print {$workflow} "R fit range: $rmin-$rmax A\n";
print {$workflow} "FEFF path indices: " . join(',', @indices) . "\n";
print {$workflow} "sigma2 groups: " . join(',', @groups) . "\n\n";
print {$workflow} "Generation sequence\n";
print {$workflow} "-------------------\n";
print {$workflow} "1. Load chi(k), apply the stated k/R windows, and run one complex R-space fit.\n";
print {$workflow} "2. Use the selected FEFF paths with shared DeltaE0=enot and DeltaR=dr_all.\n";
print {$workflow} "3. Save the fitted project as fit.dpj and export k1/k2/k3 data, fit and residual.\n";
print {$workflow} "4. Set Demeter plot k-weight separately to 1, 2 and 3, then export R-space magnitude, real and imaginary data/fit/residual.\n";
print {$workflow} "5. Export one fit_parameters.tsv table; report R=Reff+DeltaR.\n\n";
print {$workflow} "Fit result\n";
print {$workflow} "----------\n";
print {$workflow} "R-factor: " . $fit->r_factor . "\n";
print {$workflow} "chi-square: " . $fit->chi_square . "\n";
print {$workflow} "reduced chi-square: " . $fit->chi_reduced . "\n";
print {$workflow} "Nind: " . $fit->n_idp . "\n";
print {$workflow} "Nvar: " . $fit->n_varys . "\n";
print {$workflow} "Review status: unreviewed; inspect bounds, correlations and chemical plausibility before acceptance.\n";
print {$workflow} "Project check: generated by Demeter; reopen in Artemis or load with Demeter before final delivery.\n";
close $workflow;

open my $result,'>',File::Spec->catfile($outdir,'fit_result.json') or die $!;
print $result JSON::PP->new->canonical->pretty->encode({
 mode=>$mode,sample=>$sample_name,s02=>0+$s02,
 s02_error=>($mode eq 'standard' ? 0+$s02_error : undef),
 s02_status=>($mode eq 'standard' ? 'fitted' : 'fixed'),
 r_factor=>0+$fit->r_factor,nind=>0+$fit->n_idp,nvar=>0+$fit->n_varys,
 review_status=>'unreviewed',data=>$datafile,feff=>$feffinp,
 paths=>[map {{index=>$_,scatterer=>$sp[$_]->scatterer,degeneracy=>0+$sp[$_]->n,reff=>0+$sp[$_]->halflength}} @indices],
});
close $result;

print "DEMETER_FIRST_SHELL_OK r_factor=" . $fit->r_factor
    . " n_idp=" . $fit->n_idp . " n_varys=" . $fit->n_varys . "\n";
$RUN_COMPLETED = 1;
