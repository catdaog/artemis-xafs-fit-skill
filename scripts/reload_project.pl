use strict;
use warnings;
use JSON::PP;
use File::Spec;
our $OK=0;
END { $?=0 if $OK; }
use Demeter;
my ($project,$out)=@ARGV;
die "usage: reload_project.pl PROJECT OUTDIR\n" unless $project && -d $out;
my $fit=Demeter::Fit->new;
$fit->set_mode(screen=>0);
$fit->thaw(file=>$project);
die "project did not load\n" unless $fit->thawed;
my @data=@{$fit->data};my @paths=@{$fit->paths};my @gds=@{$fit->gds};
die "project missing data, paths or parameters\n" unless @data && @paths && @gds;
die "only single-data final projects supported\n" unless @data==1;
die "project is not a completed fit\n" unless $fit->fitted;
my $d=$data[0];
for my $kw (1,2,3) {
 $d->save('fit',File::Spec->catfile($out,"k$kw.dat"),"k$kw");
 $d->po->kweight($kw);
 for my $c (['mag','rmag'],['re','rre'],['im','rim']) {
  $d->save('fit',File::Spec->catfile($out,"r${kw}_".$c->[0].'.dat'),$c->[1]);
 }
}
my @records;
for my $p (@paths) {
 push @records,{name=>$p->name,n=>0+$p->n,reff=>0+$p->sp->halflength,
  delr=>0+$p->delr_value,sigma2=>0+$p->sigma2_value,e0=>0+$p->e0_value,
  amplitude=>0+$p->s02_value};
}
my $report={status=>'pass',data_count=>scalar(@data),path_count=>scalar(@paths),
 paths=>\@records,gds=>[map {{name=>$_->name,value=>0+$_->bestfit,error=>0+$_->error}} @gds],
 fitted=>$fit->fitted?JSON::PP::true:JSON::PP::false};
open my $f,'>',File::Spec->catfile($out,'reload.json') or die $!;
print $f JSON::PP->new->canonical->pretty->encode($report);close $f;
$OK=1;
