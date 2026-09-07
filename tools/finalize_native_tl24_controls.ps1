$ErrorActionPreference = 'Stop'

$consolePath = 'Project Files/Source/Console/console.cs'
$projPath = 'Project Files/Source/Console/Thetis.csproj'
$setupNativePath = 'Project Files/Source/Console/Setup.PA3GHMNative.cs'
$consoleNativePath = 'Project Files/Source/Console/Console.PA3GHMNative.cs'
$controlFormPath = 'Project Files/Source/Console/PA3GHMNativeControlForm.cs'

function Read-Utf8([string]$Path) {
    return [System.IO.File]::ReadAllText($Path)
}
function Write-Utf8Bom([string]$Path, [string]$Text) {
    [System.IO.File]::WriteAllText($Path, $Text, [System.Text.UTF8Encoding]::new($true))
}
function Require([string]$Text, [string]$Needle, [string]$What) {
    if (-not $Text.Contains($Needle)) { throw "FINAL TL2-4 GATE FAILED: $What" }
}

foreach ($p in @($consolePath,$projPath,$setupNativePath,$consoleNativePath,$controlFormPath)) {
    if (-not (Test-Path -LiteralPath $p)) { throw "Required file missing: $p" }
}

# Native Auto Recenter must be independent of the TCI owner handshake.  The original
# PA3GHM condition remains, but the local master switch is evaluated first.  Four
# smooth-scroll paths exist: RX1 left/right and RX2 left/right.
$console = Read-Utf8 $consolePath
$oldGate = 'if (!(ThetisLinkExtensionsEnabled && ThetisLinkRecenterOwnerActive) && !bLimitToSpectral'
$newGate = 'if (NativeAutoRecenterEnabled && !(ThetisLinkExtensionsEnabled && ThetisLinkRecenterOwnerActive) && !bLimitToSpectral'
$oldCount = ([regex]::Matches($console, [regex]::Escape($oldGate))).Count
$newCount = ([regex]::Matches($console, [regex]::Escape($newGate))).Count

if ($oldCount -eq 4 -and $newCount -eq 0) {
    $console = $console.Replace($oldGate, $newGate)
    Write-Utf8Bom $consolePath $console
}
elif ($oldCount -eq 0 -and $newCount -eq 4) {
    # already integrated
}
else {
    throw "Unexpected auto-recenter gate counts: old=$oldCount new=$newCount (expected 4/0 or 0/4)"
}

# Add native source files to the legacy non-SDK project.
$proj = Read-Utf8 $projPath
if (-not $proj.Contains('Console.PA3GHMNative.cs')) {
    $anchor = '    <Compile Include="PA3GHMNativeDiversity.cs" />'
    if (-not $proj.Contains($anchor)) { throw 'Cannot locate native Diversity compile anchor in Thetis.csproj' }
    $addition = @'
    <Compile Include="PA3GHMNativeDiversity.cs" />
    <Compile Include="Console.PA3GHMNative.cs">
      <DependentUpon>console.cs</DependentUpon>
    </Compile>
    <Compile Include="PA3GHMNativeControlForm.cs">
      <SubType>Form</SubType>
    </Compile>
'@
    $addition = $addition.TrimEnd("`r", "`n")
    $proj = $proj.Replace($anchor, $addition)
    Write-Utf8Bom $projPath $proj
}

$console = Read-Utf8 $consolePath
$proj = Read-Utf8 $projPath
$setupNative = Read-Utf8 $setupNativePath
$consoleNative = Read-Utf8 $consoleNativePath
$controlForm = Read-Utf8 $controlFormPath

# Four local auto-recenter gates are mandatory.
$finalGateCount = ([regex]::Matches($console, [regex]::Escape($newGate))).Count
if ($finalGateCount -ne 4) { throw "Native Auto Recenter gates: expected 4, found $finalGateCount" }

Require $proj 'Console.PA3GHMNative.cs' 'Console native partial is not compiled'
Require $proj 'PA3GHMNativeControlForm.cs' 'native TL2-4 control form is not compiled'
Require $setupNative 'Native TL2-4 Control...' 'Setup entry point missing'
Require $setupNative 'groupBoxTS69.Controls.Add(btnPA3GHMNativeControl)' 'Setup > Network > IQ Stream placement missing'

Require $consoleNative 'NativeAutoRecenterEnabled' 'native Auto Recenter master switch missing'
Require $consoleNative 'NativeRecenterRX1' 'RX1 immediate recenter missing'
Require $consoleNative 'NativeRecenterRX2' 'RX2 immediate recenter missing'
Require $consoleNative 'NativeReleaseExternalRecenterOwner' 'recenter ownership release missing'
Require $consoleNative 'NativeOpenDiversityControl' 'Advanced Diversity opener missing'

# Every operator-facing TL2-4 addition must have a local path.
Require $controlForm 'RX Only (TX inhibit)' 'native rx_only_ex equivalent missing'
Require $controlForm 'SetHWSampleRate' 'native ddc_sample_rate_ex equivalent missing'
Require $controlForm 'RX1 filter preset' 'native rx_filter_preset_ex RX1 control missing'
Require $controlForm 'RX2 filter preset' 'native rx_filter_preset_ex RX2 control missing'
Require $controlForm 'S9 HF/VHF threshold' 'native s9_frequency_ex equivalent missing'
Require $controlForm 'Native smooth-scroll Auto Recenter' 'native auto_recenter_ex operator control missing'
Require $controlForm 'Recenter RX1 now' 'RX1 recenter action missing'
Require $controlForm 'Recenter RX2 now' 'RX2 recenter action missing'
Require $controlForm 'Open Advanced Diversity' 'native advanced Diversity access missing'
Require $controlForm 'Sweep / Fast Sweep / Auto Null / Smart Null / Ultra Null' 'advanced Diversity feature list missing'

# Protocol metadata/handshake are explicitly classified rather than exposed as fake DSP knobs.
Require $controlForm 'tci_caps_ex and auto_recenter_owner_ex are protocol capability/ownership handshake' 'protocol-only capability explanation missing'

# Native operator controls must never be gated by the TCI extension checkbox.
if ($controlForm -match 'ThetisLinkExtensionsEnabled') {
    throw 'Native TL2-4 control form must not depend on ThetisLinkExtensionsEnabled'
}
if ($consoleNative -match 'ThetisLinkExtensionsEnabled') {
    throw 'Native TL2-4 console hooks must not depend on ThetisLinkExtensionsEnabled'
}

$bad = Select-String -Path $consolePath,$projPath,$setupNativePath,$consoleNativePath,$controlFormPath -Pattern '^<<<<<<<|^=======|^>>>>>>>'
if ($bad) { throw 'Unresolved merge markers remain' }

Write-Host "Final native TL2-4 integration gates: PASS (Auto Recenter paths=$finalGateCount)"
