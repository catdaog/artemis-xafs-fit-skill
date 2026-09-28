[CmdletBinding()]
param(
    [ValidateSet('probe', 'run')]
    [string]$Action = 'probe',
    [string]$DemeterRoot,
    [string]$Script,
    [string[]]$ScriptArgs = @(),
    [string]$RuntimeRoot
)

$ErrorActionPreference = 'Stop'

$candidates = @()
if ($DemeterRoot) { $candidates += $DemeterRoot }
if ($env:DEMETER_BASE) { $candidates += $env:DEMETER_BASE }
$candidates += (Join-Path $env:USERPROFILE 'DemeterPerl')
$demeter = $candidates | Where-Object {
    Test-Path -LiteralPath (Join-Path $_ 'perl\bin\perl.exe')
} | Select-Object -First 1
if (-not $demeter) {
    throw 'Demeter bundle not found. Pass -DemeterRoot or set DEMETER_BASE.'
}

$perl = Join-Path $demeter 'perl\bin\perl.exe'
$feff6 = Join-Path $demeter 'c\bin\feff6.exe'
$gnuplot = Join-Path $demeter 'c\bin\gnuplot\bin\gnuplot.exe'
$probe = [ordered]@{
    demeter_root = $demeter
    perl = $perl
    perl_exists = Test-Path -LiteralPath $perl
    feff6 = $feff6
    feff6_exists = Test-Path -LiteralPath $feff6
    gnuplot = $gnuplot
    gnuplot_exists = Test-Path -LiteralPath $gnuplot
}
if ($Action -eq 'probe') {
    $probe | ConvertTo-Json
    exit 0
}

if (-not $Script) { throw '-Script is required for -Action run.' }
$scriptFull = [IO.Path]::GetFullPath($Script)
if (-not (Test-Path -LiteralPath $scriptFull)) { throw "Script not found: $scriptFull" }
if (-not $RuntimeRoot) {
    $RuntimeRoot = Join-Path $env:TEMP ("demeter-xafs-" + $PID)
}
$runtimeFull = [IO.Path]::GetFullPath($RuntimeRoot)
New-Item -ItemType Directory -Force -Path $runtimeFull | Out-Null

$env:APPDATA = $runtimeFull
$env:DEMETER_BASE = $demeter
$env:FONTCONFIG_FILE = Join-Path $demeter 'c\bin\gnuplot\etc\fonts\fonts.conf'
$env:IFEFFIT_DIR = (Join-Path $demeter 'c\share\ifeffit') + '\'
$env:PGPLOT_FONT = Join-Path $demeter 'c\lib\pgplot\grfont.dat'
$env:Path = @(
    'C:\Windows\system32', 'C:\Windows',
    (Join-Path $demeter 'c\bin'),
    (Join-Path $demeter 'perl\site\bin'),
    (Join-Path $demeter 'perl\bin'),
    (Join-Path $demeter 'c\bin\gnuplot\bin')
) -join ';'
$env:LC_ALL = ''
$env:LC_CTYPE = ''
$env:LANG = ''

& $perl $scriptFull @ScriptArgs
exit $LASTEXITCODE
