[CmdletBinding(DefaultParameterSetName='File')]
param(
    [Parameter(Mandatory=$true, ParameterSetName='File')]
    [string]$InputFile,
    [Parameter(Mandatory=$true, ParameterSetName='Config')]
    [string]$Config,
    [Parameter(Mandatory=$true, ParameterSetName='Verify')]
    [string]$Verify,
    [Parameter(Mandatory=$true, ParameterSetName='File')]
    [Parameter(Mandatory=$true, ParameterSetName='Config')]
    [string]$Output,
    [Parameter(ParameterSetName='File')][double]$Kappa = 10,
    [Parameter(ParameterSetName='File')][double]$Sigma = 1,
    [Parameter(ParameterSetName='File')][int]$KWeight = 2,
    [Parameter(ParameterSetName='File')][int]$InputKWeight = 0,
    [Parameter(ParameterSetName='File')][int]$KColumn = 1,
    [Parameter(ParameterSetName='File')][int]$ChiColumn = 2,
    [Parameter(ParameterSetName='File')][double]$KMin,
    [Parameter(ParameterSetName='File')][double]$KMax,
    [Parameter(ParameterSetName='File')][double]$KStep = 0.05,
    [Parameter(ParameterSetName='File')][double]$RMin = 0,
    [Parameter(ParameterSetName='File')][double]$RMax = 6,
    [Parameter(ParameterSetName='File')][double]$RStep = 0.02,
    [Parameter(ParameterSetName='File')][ValidateSet('hanning','none')][string]$Window = 'hanning',
    [Parameter(ParameterSetName='File')][double]$Dk = 1,
    [string]$Python
)
$ErrorActionPreference = 'Stop'
if (-not $Python) {
    $candidatePaths = @(
        (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'),
        (Join-Path $env:USERPROFILE 'AppData\Local\Programs\DeepSeek Harness\resources\runtime\primary-runtime\dependencies\python\python.exe')
    )
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand -and $pythonCommand.Source -notmatch 'WindowsApps') {
        $candidatePaths += $pythonCommand.Source
    }
    $Python = $candidatePaths | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
}
if (-not $Python) { throw 'Python not found. Pass -Python with a real Python executable.' }
$scriptPath = Join-Path $PSScriptRoot 'exafs_wavelet.py'
if ($PSCmdlet.ParameterSetName -eq 'Verify') {
    $callArgs = @($scriptPath, 'verify', $Verify)
} elseif ($PSCmdlet.ParameterSetName -eq 'Config') {
    $callArgs = @($scriptPath, '--config', $Config, '--out', $Output)
} else {
    $inv = [System.Globalization.CultureInfo]::InvariantCulture
    $callArgs = @($scriptPath, $InputFile, '--out', $Output,
        '--kappa', $Kappa.ToString($inv), '--sigma', $Sigma.ToString($inv),
        '--kweight', "$KWeight", '--input-kweight', "$InputKWeight",
        '--k-column', "$KColumn", '--chi-column', "$ChiColumn",
        '--kstep', $KStep.ToString($inv), '--rmin', $RMin.ToString($inv),
        '--rmax', $RMax.ToString($inv), '--rstep', $RStep.ToString($inv),
        '--window', $Window, '--dk', $Dk.ToString($inv))
    if ($PSBoundParameters.ContainsKey('KMin')) { $callArgs += @('--kmin', $KMin.ToString($inv)) }
    if ($PSBoundParameters.ContainsKey('KMax')) { $callArgs += @('--kmax', $KMax.ToString($inv)) }
}
& $Python -B @callArgs
exit $LASTEXITCODE
