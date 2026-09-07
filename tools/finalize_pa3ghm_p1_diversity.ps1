$ErrorActionPreference = 'Stop'

$path = 'Project Files/Source/Console/TCIServer.cs'
$text = [System.IO.File]::ReadAllText($path)

$helperMarker = 'SQ4KOU_P1_DIVERSITY_WORKER_TX_GUARD'
if (-not $text.Contains($helperMarker)) {
    $anchor = "`t`t// diversity_sweep_ex:type,start,end,step,settleMs;"
    if (-not $text.Contains($anchor)) {
        throw 'Cannot find PA3GHM Diversity sweep anchor'
    }

    $helper = @"
`t`t// SQ4KOU_P1_DIVERSITY_WORKER_TX_GUARD
`t`t// PA3GHM null/sweep workers run asynchronously. In Protocol 1 our
`t`t// cmaster TX gate deliberately stops EXTDIV for MOX. Do not let a
`t`t// background worker keep changing phase/gain while that gate is active.
`t`t// Protocol 2 and normal RX behaviour are unchanged.
`t`tprivate bool shouldAbortSq4kouP1DiversityWorker(Console c)
`t`t{
`t`t`tif (m_disconnected || c == null || c.IsDisposed) return true;
`t`t`tif (NetworkIO.CurrentRadioProtocol != RadioProtocol.USB) return false;

`t`t`ttry
`t`t`t{
`t`t`t`tif (c.InvokeRequired)
`t`t`t`t`treturn (bool)c.Invoke(new Func<bool>(() => c.MOX || c.TUN));

`t`t`t`treturn c.MOX || c.TUN;
`t`t`t}
`t`t`tcatch
`t`t`t{
`t`t`t`t// Fail safe: an invalid UI state must never let the P1 worker
`t`t`t`t// alter Diversity during a possible TX transition.
`t`t`t`treturn true;
`t`t`t}
`t`t}

"@
    $text = $text.Replace($anchor, $helper + $anchor)
}

# Return one complete top-level method body. All TCI listener members use two-tab
# indentation; the next member declaration is therefore a stable semantic boundary
# even though the PA3GHM null suite is separated from Sweep/FastSweep by DDC/S9 code.
function Get-HandlerSection([string]$Source, [string]$HandlerName) {
    $signature = "`t`tprivate void $HandlerName(string[] args)"
    $start = $Source.IndexOf($signature, [System.StringComparison]::Ordinal)
    if ($start -lt 0) {
        throw "Cannot find PA3GHM handler $HandlerName"
    }

    $memberRegex = [regex]::new('(?m)^\t\t(?:private|public|internal|protected)\s')
    $next = $memberRegex.Match($Source, $start + $signature.Length)
    $end = if ($next.Success) { $next.Index } else { $Source.Length }
    return $Source.Substring($start, $end - $start)
}

function Patch-Handler([string]$Source, [string]$HandlerName) {
    $section = Get-HandlerSection $Source $HandlerName
    $patched = $section.Replace(
        'listener.m_disconnected || c == null || c.IsDisposed',
        'listener.shouldAbortSq4kouP1DiversityWorker(c)')
    $patched = $patched.Replace(
        'listener.m_disconnected',
        'listener.shouldAbortSq4kouP1DiversityWorker(c)')

    if ($patched -eq $section -and -not $section.Contains('shouldAbortSq4kouP1DiversityWorker(c)')) {
        throw "No guardable disconnect control point found in $HandlerName"
    }
    return $Source.Replace($section, $patched)
}

$handlers = @(
    'handleDiversitySweepEx',
    'handleDiversityFastsweepEx',
    'handleDiversityAutonullEx',
    'handleDiversitySmartNullEx',
    'handleDiversityUltraNullEx'
)

foreach ($handler in $handlers) {
    $text = Patch-Handler $text $handler
}

[System.IO.File]::WriteAllText($path, $text, [System.Text.UTF8Encoding]::new($true))

function Require-Text([string]$Path, [string]$Text) {
    if (-not (Select-String -LiteralPath $Path -SimpleMatch $Text -Quiet)) {
        throw "SYNTHESIS GATE FAILED: '$Text' missing in $Path"
    }
}

$tci = 'Project Files/Source/Console/TCIServer.cs'
$con = 'Project Files/Source/Console/console.cs'
$cm = 'Project Files/Source/Console/cmaster.cs'
$div = 'Project Files/Source/Console/DiversityForm.cs'
$setup = 'Project Files/Source/Console/setup.cs'
$designer = 'Project Files/Source/Console/setup.designer.cs'

# PA3GHM TL2-4 surface
Require-Text $tci 'tci_caps_ex'
Require-Text $tci 'rx_filter_preset_ex'
Require-Text $tci 'diversity_enable_ex'
Require-Text $tci 'diversity_sweep_ex'
Require-Text $tci 'diversity_fastsweep_ex'
Require-Text $tci 'diversity_autonull_ex'
Require-Text $tci 'diversity_smartnull_ex'
Require-Text $tci 'diversity_ultranull_ex'
Require-Text $tci 'ddc_sample_rate_ex'
Require-Text $tci 'auto_recenter_ex'
Require-Text $tci 'auto_recenter_owner_ex'
Require-Text $tci 's9_frequency_ex'
Require-Text $tci 'rx_only_ex'
Require-Text $tci 'BroadcastFilterBand'
Require-Text $tci $helperMarker
Require-Text $con 'ThetisLinkExtensionsEnabled'
Require-Text $con 'ThetisLinkRecenterOwnerActive'
Require-Text $div 'DiversityGainMulti'
Require-Text $setup 'chkThetisLinkExtensions_CheckedChanged'
Require-Text $designer 'chkThetisLinkExtensions'

# SQ4KOU functions that must survive
Require-Text $tci 'sq4kou_cmd07_ex'
Require-Text $tci 'sq4kou_radio_hw_ex'
Require-Text $tci 'sq4kou_rx_antenna_selected_ex'
Require-Text $tci 'sq4kou_tx_antenna_selected_ex'
Require-Text $con 'SQ4KOUStartP1SoftwareCWX'
Require-Text $cm 'ApplyDiversityP1TxGate'

$bad = Select-String -Path $tci,$con,$cm,$div,$setup,$designer -Pattern '^<<<<<<<|^=======|^>>>>>>>'
if ($bad) {
    throw 'Unresolved merge markers remain'
}

# Structural audit: each of the five PA3GHM asynchronous Diversity handlers must
# contain exactly one ThreadPool worker, at least one P1-aware guard and no legacy
# listener.m_disconnected checks. This avoids arbitrary global call-count thresholds.
$finalText = [System.IO.File]::ReadAllText($tci)
$totalGuards = 0
foreach ($handler in $handlers) {
    $section = Get-HandlerSection $finalText $handler
    $workers = ([regex]::Matches($section, 'System\.Threading\.ThreadPool\.QueueUserWorkItem\(_ =>')).Count
    $guards = ([regex]::Matches($section, 'shouldAbortSq4kouP1DiversityWorker\(c\)')).Count
    $legacy = ([regex]::Matches($section, 'listener\.m_disconnected')).Count

    Write-Host "$handler : workers=$workers guards=$guards legacy_disconnect=$legacy"

    if ($workers -ne 1) {
        throw "$handler has unexpected ThreadPool worker count: $workers (expected 1)"
    }
    if ($guards -lt 1) {
        throw "$handler has no SQ4KOU P1 Diversity TX guard"
    }
    if ($legacy -ne 0) {
        throw "$handler still has $legacy legacy listener.m_disconnected checks"
    }
    $totalGuards += $guards
}

Write-Host "PA3GHM async Diversity handlers verified: $($handlers.Count)"
Write-Host "Total P1-aware worker control points: $totalGuards"
Write-Host 'PA3GHM TL2-4 + SQ4KOU P1 finalization gates: PASS'
