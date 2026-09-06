param(
    [Parameter(Mandatory=$true)][string]$BundleDir,
    [Parameter(Mandatory=$true)][string]$OutputMsi
)

$ErrorActionPreference = 'Stop'
$BundleDir = (Resolve-Path $BundleDir).Path
$OutputMsi = [IO.Path]::GetFullPath($OutputMsi)
$work = Join-Path $env:RUNNER_TEMP 'jtdx-superhound-msi'
New-Item -ItemType Directory -Force $work | Out-Null
New-Item -ItemType Directory -Force ([IO.Path]::GetDirectoryName($OutputMsi)) | Out-Null

if (-not (Test-Path (Join-Path $BundleDir 'jtdx.exe'))) { throw "jtdx.exe missing from $BundleDir" }
if (-not (Test-Path (Join-Path $BundleDir 'sfrx.exe'))) { throw "sfrx.exe missing from $BundleDir" }

function Find-Wix3Bin {
    $cmd = Get-Command heat.exe -ErrorAction SilentlyContinue
    if ($cmd) { return Split-Path $cmd.Source }
    $roots = @(
        'C:\Program Files (x86)',
        'C:\Program Files'
    )
    foreach ($root in $roots) {
        if (-not (Test-Path $root)) { continue }
        $dirs = Get-ChildItem $root -Directory -Filter 'WiX Toolset v3*' -ErrorAction SilentlyContinue | Sort-Object Name -Descending
        foreach ($d in $dirs) {
            $bin = Join-Path $d.FullName 'bin'
            if ((Test-Path (Join-Path $bin 'heat.exe')) -and (Test-Path (Join-Path $bin 'candle.exe')) -and (Test-Path (Join-Path $bin 'light.exe'))) {
                return $bin
            }
        }
    }
    return $null
}

$wixBin = Find-Wix3Bin
if (-not $wixBin) {
    Write-Host 'WiX 3 not found; installing WiX Toolset through Chocolatey...'
    choco install wixtoolset --no-progress -y | Out-Host
    $wixBin = Find-Wix3Bin
}
if (-not $wixBin) { throw 'WiX Toolset 3 (heat/candle/light) not found after installation.' }
Write-Host "Using WiX: $wixBin"

$heat = Join-Path $wixBin 'heat.exe'
$candle = Join-Path $wixBin 'candle.exe'
$light = Join-Path $wixBin 'light.exe'
$filesWxs = Join-Path $work 'Files.wxs'
$productWxs = Join-Path $work 'Product.wxs'

& $heat dir $BundleDir -nologo -cg ProductFiles -dr INSTALLFOLDER -gg -scom -sreg -sfrag -srd -var 'var.SourceDir' -out $filesWxs
if ($LASTEXITCODE -ne 0) { throw "heat.exe failed: $LASTEXITCODE" }

@'
<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="*" Name="JTDX SuperHound P1 SQ4KOU" Language="1033" Version="0.1.0.0" Manufacturer="SQ4KOU" UpgradeCode="4F578792-54D5-47F2-B2F8-BB6B1175B649">
    <Package InstallerVersion="500" Compressed="yes" InstallScope="perMachine" Description="JTDX SuperHound P1 test build by SQ4KOU" />
    <MajorUpgrade DowngradeErrorMessage="A newer JTDX SuperHound P1 build is already installed." />
    <MediaTemplate EmbedCab="yes" />

    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="ProgramFilesFolder">
        <Directory Id="ManufacturerFolder" Name="SQ4KOU">
          <Directory Id="INSTALLFOLDER" Name="JTDX SuperHound P1" />
        </Directory>
      </Directory>
      <Directory Id="ProgramMenuFolder">
        <Directory Id="ProgramMenuDir" Name="JTDX SuperHound P1" />
      </Directory>
    </Directory>

    <DirectoryRef Id="INSTALLFOLDER">
      <Component Id="AppIntegration" Guid="DDBA4FF2-17F7-48C5-894E-4C83F4AB3EAA">
        <Environment Id="JtdxSfrxPath" Name="JTDX_SFRX" Value="[INSTALLFOLDER]sfrx.exe" Action="set" Part="all" System="yes" Permanent="no" />
        <Shortcut Id="StartMenuShortcut" Directory="ProgramMenuDir" Name="JTDX SuperHound P1" WorkingDirectory="INSTALLFOLDER" Target="[INSTALLFOLDER]jtdx.exe" />
        <RemoveFolder Id="RemoveProgramMenuDir" Directory="ProgramMenuDir" On="uninstall" />
        <RegistryValue Root="HKLM" Key="Software\SQ4KOU\JTDX SuperHound P1" Name="Installed" Type="integer" Value="1" KeyPath="yes" />
      </Component>
    </DirectoryRef>

    <Feature Id="Complete" Title="JTDX SuperHound P1" Level="1">
      <ComponentGroupRef Id="ProductFiles" />
      <ComponentRef Id="AppIntegration" />
    </Feature>
  </Product>
</Wix>
'@ | Set-Content -Encoding UTF8 $productWxs

Push-Location $work
try {
    & $candle -nologo -arch x86 -dSourceDir="$BundleDir" $productWxs $filesWxs
    if ($LASTEXITCODE -ne 0) { throw "candle.exe failed: $LASTEXITCODE" }
    & $light -nologo -out $OutputMsi (Join-Path $work 'Product.wixobj') (Join-Path $work 'Files.wixobj')
    if ($LASTEXITCODE -ne 0) { throw "light.exe failed: $LASTEXITCODE" }
}
finally {
    Pop-Location
}

$msi = Get-Item $OutputMsi
if ($msi.Length -lt 100000) { throw "MSI is unexpectedly small: $($msi.Length) bytes" }
Get-FileHash $OutputMsi -Algorithm SHA256 | Format-List | Out-String | Set-Content ($OutputMsi + '.sha256.txt')
Write-Host "MSI READY: $OutputMsi ($($msi.Length) bytes)"
