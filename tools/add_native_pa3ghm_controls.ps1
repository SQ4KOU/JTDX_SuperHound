$ErrorActionPreference = 'Stop'

$divPath = 'Project Files/Source/Console/DiversityForm.cs'
$setupPath = 'Project Files/Source/Console/setup.cs'
$projPath = 'Project Files/Source/Console/Thetis.csproj'

function Read-Utf8([string]$Path) {
    return [System.IO.File]::ReadAllText($Path)
}
function Write-Utf8Bom([string]$Path, [string]$Text) {
    [System.IO.File]::WriteAllText($Path, $Text, [System.Text.UTF8Encoding]::new($true))
}
function Require([string]$Text, [string]$Needle, [string]$What) {
    if (-not $Text.Contains($Needle)) { throw "NATIVE GATE FAILED: $What" }
}

$div = Read-Utf8 $divPath
if (-not $div.Contains('NATIVE_PA3GHM_DIVERSITY_PANEL')) {
    $classOld = 'public class DiversityForm : System.Windows.Forms.Form'
    $classNew = 'public partial class DiversityForm : System.Windows.Forms.Form'
    if (-not $div.Contains($classOld) -and -not $div.Contains($classNew)) {
        throw 'Cannot locate DiversityForm class declaration'
    }
    $div = $div.Replace($classOld, $classNew)

    $anchor = '            Common.RestoreForm(this, "DiversityForm", true);'
    if (-not $div.Contains($anchor)) { throw 'Cannot locate DiversityForm RestoreForm anchor' }
    $replacement = $anchor + "`r`n            // NATIVE_PA3GHM_DIVERSITY_PANEL`r`n            InitPA3GHMNativePanel();"
    $div = $div.Replace($anchor, $replacement)
    Write-Utf8Bom $divPath $div
}

$setup = Read-Utf8 $setupPath
if (-not $setup.Contains('NATIVE_PA3GHM_SETUP_CONTROLS')) {
    $anchor = "            console = c;`r`n            this.Owner = c;"
    if (-not $setup.Contains($anchor)) {
        $anchor = "            console = c;`n            this.Owner = c;"
    }
    if (-not $setup.Contains($anchor)) { throw 'Cannot locate Setup console assignment anchor' }
    $replacement = "            console = c;`r`n            // NATIVE_PA3GHM_SETUP_CONTROLS`r`n            InitPA3GHMNativeSetupControls();`r`n            this.Owner = c;"
    $setup = $setup.Replace($anchor, $replacement)
    Write-Utf8Bom $setupPath $setup
}

$proj = Read-Utf8 $projPath
if (-not $proj.Contains('PA3GHMNativeDiversity.cs')) {
    $anchor = "    <Compile Include=\"DiversityForm.cs\">`r`n      <SubType>Form</SubType>`r`n    </Compile>"
    if (-not $proj.Contains($anchor)) {
        $anchor = "    <Compile Include=\"DiversityForm.cs\">`n      <SubType>Form</SubType>`n    </Compile>"
    }
    if (-not $proj.Contains($anchor)) { throw 'Cannot locate DiversityForm compile item in Thetis.csproj' }
    $addition = $anchor + "`r`n    <Compile Include=\"DiversityForm.PA3GHMNative.cs\">`r`n      <DependentUpon>DiversityForm.cs</DependentUpon>`r`n    </Compile>`r`n    <Compile Include=\"PA3GHMNativeDiversity.cs\" />`r`n    <Compile Include=\"Setup.PA3GHMNative.cs\">`r`n      <DependentUpon>setup.cs</DependentUpon>`r`n    </Compile>"
    $proj = $proj.Replace($anchor, $addition)
    Write-Utf8Bom $projPath $proj
}

$div = Read-Utf8 $divPath
$setup = Read-Utf8 $setupPath
$proj = Read-Utf8 $projPath
$nativeEngine = Read-Utf8 'Project Files/Source/Console/PA3GHMNativeDiversity.cs'
$nativeUi = Read-Utf8 'Project Files/Source/Console/DiversityForm.PA3GHMNative.cs'
$nativeSetup = Read-Utf8 'Project Files/Source/Console/Setup.PA3GHMNative.cs'

Require $div 'public partial class DiversityForm' 'DiversityForm must be partial'
Require $div 'InitPA3GHMNativePanel();' 'native Diversity panel init missing'
Require $setup 'InitPA3GHMNativeSetupControls();' 'native Setup init missing'
Require $proj 'DiversityForm.PA3GHMNative.cs' 'native Diversity UI not in project'
Require $proj 'PA3GHMNativeDiversity.cs' 'native Diversity engine not in project'
Require $proj 'Setup.PA3GHMNative.cs' 'native Setup UI not in project'
Require $nativeEngine 'StartSweep' 'Sweep engine missing'
Require $nativeEngine 'StartAutoNull' 'AutoNull engine missing'
Require $nativeEngine 'StartSmartNull' 'SmartNull engine missing'
Require $nativeEngine 'StartUltraNull' 'UltraNull engine missing'
Require $nativeEngine 'NetworkIO.CurrentRadioProtocol == RadioProtocol.USB' 'P1 TX safety guard missing'
Require $nativeUi 'Native control — TCI server/checkbox not required' 'native independence label missing'
Require $nativeSetup 'Custom S9 threshold' 'custom native S9 control missing'

if ($nativeEngine -match 'ThetisLinkExtensionsEnabled') {
    throw 'Native Diversity engine must not be gated by ThetisLinkExtensionsEnabled'
}

$bad = Select-String -Path $divPath,$setupPath,$projPath,'Project Files/Source/Console/PA3GHMNativeDiversity.cs','Project Files/Source/Console/DiversityForm.PA3GHMNative.cs','Project Files/Source/Console/Setup.PA3GHMNative.cs' -Pattern '^<<<<<<<|^=======|^>>>>>>>'
if ($bad) { throw 'Unresolved merge markers remain' }

Write-Host 'Native PA3GHM GUI integration gates: PASS'
