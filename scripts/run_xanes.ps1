param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('probe','install','simulate','converge','fit')]
    [string]$Mode,
    [string]$Config,
    [string]$Output,
    [string]$Executable,
    [string]$Archive,
    [string]$Url,
    [string]$Python
)
$ErrorActionPreference = 'Stop'
$skillRoot = Split-Path -Parent $PSScriptRoot
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
if ($Mode -in @('probe','install')) {
    $callArgs = @((Join-Path $PSScriptRoot 'fdmnes_runtime.py'), $Mode)
    if ($Mode -eq 'probe' -and $Executable) { $callArgs += @('--exe', $Executable) }
    if ($Mode -eq 'install') {
        if ($Archive) { $callArgs += @('--archive', $Archive) }
        elseif ($Url) { $callArgs += @('--url', $Url) }
        else { throw 'For install, supply -Archive or -Url from the verified official download page.' }
    }
} else {
    if (-not $Config -or -not $Output) { throw 'Supply -Config and a new/empty -Output directory.' }
    $callArgs = @((Join-Path $PSScriptRoot 'xanes_fit.py'), $Mode, $Config, '--out', $Output)
    if ($Executable) { $callArgs += @('--exe', $Executable) }
}
& $Python @callArgs
exit $LASTEXITCODE
