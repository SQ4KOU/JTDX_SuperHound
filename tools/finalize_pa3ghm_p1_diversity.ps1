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

# PA3GHM keeps Sweep/FastSweep/Auto/Smart/Ultra in one contiguous block.
# Use the DDC handler as the stable end anchor rather than the many nested TL2 END markers.
$startMarker = "`t`t// diversity_sweep_ex:type,start,end,step,settleMs;"
$endMarker = "`t`t// ddc_sample_rate_ex:rx,rate;"
$start = $text.IndexOf($startMarker)
if ($start -lt 0) {
    throw 'Cannot find start of PA3GHM asynchronous Diversity section'
}
$end = $text.IndexOf($endMarker, $start)
if ($end -lt 0) {
    throw 'Cannot find DDC marker after PA3GHM asynchronous Diversity section'
}

$before = $text.Substring(0, $start)
$section = $text.Substring($start, $end - $start)
$after = $text.Substring($end)

# First collapse compound disconnect/disposed checks, then every remaining listener
# disconnect check in the PA3GHM async block. This preserves each original control-flow
# action (return, return dbm, negated final-send check) while adding the P1 TX condition.
$section = $section.Replace(
    'listener.m_disconnected || c == null || c.IsDisposed',
    'listener.shouldAbortSq4kouP1DiversityWorker(c)')
$section = $section.Replace(
    'listener.m_disconnected',
    'listener.shouldAbortSq4kouP1DiversityWorker(c)')

$text = $before + $section + $after
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

$count = (Select-String -LiteralPath $tci -SimpleMatch 'shouldAbortSq4kouP1DiversityWorker(c)' | Measure-Object).Count
Write-Host "P1 Diversity worker guard call sites: $count"
if ($count -lt 10) {
    throw "Too few guarded PA3GHM worker call sites: $count"
}

Write-Host 'PA3GHM TL2-4 + SQ4KOU P1 finalization gates: PASS'
