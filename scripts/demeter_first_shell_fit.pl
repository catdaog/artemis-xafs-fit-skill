#!/usr/bin/env perl
use strict;
use warnings;
use Getopt::Long qw(GetOptions);
use File::Path qw(make_path);
use File::Spec;
use Demeter;

my ($datafile, $feffinp, $outdir, $s02, $path_csv, $group_csv);
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
) or die "invalid arguments\n";
die "usage: demeter_first_shell_fit.pl --data DATA --feff FEFF.INP --out DIR "
  . "--s02 VALUE --paths 0,1,... --sigma-groups 0,0,... [--rmin 1 --rmax 2.5]\n"
  unless defined $datafile && defined $feffinp && defined $outdir
      && defined $s02 && defined $path_csv && defined $group_csv;
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
    $data->name('XAFS data');
} else {
    $data = Demeter::Data->new(
        file => $loadfile, datatype => 'chi', chi_column => '2', name => 'XAFS data'
    );
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

my @paths;
for my $i (0 .. $#indices) {
    my $idx = $indices[$i];
    my $sp = $sp[$idx];
    my $name = sprintf('FEFF[%d] %s Reff=%.5f', $idx, $sp->scatterer, $sp->halflength);
    push @paths, Demeter::Path->new(
        name => $name, parent => $feff, sp => $sp, data => $data, n => $sp->n,
        s02 => "$s02", e0 => 'enot', delr => 'dr_all', sigma2 => "ss_$groups[$i]",
    );
}

my $fit = Demeter::Fit->new(
    data => [$data], paths => \@paths, gds => \@gds,
    interface => 'artemis-xafs-fit-skill first-shell driver',
);
my $returned = $fit->fit;
die "fit did not return its Fit object\n" unless $returned eq $fit;

$fit->logfile(File::Spec->catfile($outdir, 'fit.log'), 'XAFS data', 'first shell');
$fit->freeze(file => File::Spec->catfile($outdir, 'fit.dpj'));
$data->save('fit', File::Spec->catfile($outdir, 'fit_k1.dat'), 'k1');
$data->save('fit', File::Spec->catfile($outdir, 'fit_k2.dat'), 'k2');
$data->save('fit', File::Spec->catfile($outdir, 'fit_k3.dat'), 'k3');
$data->save('fit', File::Spec->catfile($outdir, 'fit_rmag.dat'), 'rmag');
$data->save('fit', File::Spec->catfile($outdir, 'fit_rre.dat'), 'rre');
$data->save('fit', File::Spec->catfile($outdir, 'fit_rim.dat'), 'rim');

open my $summary, '>', File::Spec->catfile($outdir, 'summary.tsv')
  or die "cannot write summary.tsv: $!\n";
print {$summary} "s02_fixed\t$s02\n";
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

print "DEMETER_FIRST_SHELL_OK r_factor=" . $fit->r_factor
    . " n_idp=" . $fit->n_idp . " n_varys=" . $fit->n_varys . "\n";
