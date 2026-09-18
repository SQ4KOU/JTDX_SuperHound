from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
here = Path(__file__).resolve().parent
r8 = here / 'apply_final_tci_omnirig_r8_flex6xxx_overlay.py'
if not r8.exists():
    raise SystemExit('[FAIL] R8 overlay missing')

subprocess.run([sys.executable, str(r8), str(root)], check=True)

bp = root / 'BUILD_JTDX_SUPERHOUND_MSI.ps1'
b = bp.read_text(encoding='utf-8')

# Slice Master 6000 has a TCP CAT Listener explicitly documented as compatible
# with Hamlib's Flex 6xxx definition.  The user's stock JTDX 2.2.159 works
# through that path, so R9 stops rebuilding the runtime Hamlib DLL as the
# effective test target and installs the exact official JTDX 2.2.159 win64
# libhamlib-4.dll binary published by the JTDX project.
marker = '# SQ4KOU R9: exact official JTDX 2.2.159 win64 Hamlib runtime for Slice Master Flex 6xxx.'
if marker not in b:
    anchor = '# SQ4KOU R8: FlexRadio 6xxx release-Hamlib network-open regression gate.\n'
    if b.count(anchor) != 1:
        raise SystemExit(f'[FAIL] R9 R8 regression anchor count={b.count(anchor)}')
    block = r'''# SQ4KOU R9: exact official JTDX 2.2.159 win64 Hamlib runtime for Slice Master Flex 6xxx.
R9_HAMLIB_URL='https://sourceforge.net/projects/jtdx/files/jtdx_2.2.159/Microsoft%20Windows/Hamlib/win64/libhamlib-4.dll/download'
R9_HAMLIB_SHA256='8cd24f3d935c740d2c3c901ae3af786964cfdd05101d47c913073aaa24f412da'
R9_HAMLIB_TMP="$WORK/libhamlib-4.official.dll"

echo '[INFO] R9 downloading exact official JTDX 2.2.159 win64 libhamlib-4.dll'
curl.exe -L --fail --retry 5 --retry-delay 2 "$R9_HAMLIB_URL" -o "$(cygpath -w "$R9_HAMLIB_TMP")"
test -s "$R9_HAMLIB_TMP" || {
  echo '[FAIL] R9 official Hamlib download is empty'
  exit 85
}
R9_HAMLIB_ACTUAL="$(sha256sum "$R9_HAMLIB_TMP" | awk '{print $1}')"
echo "[INFO] R9 official Hamlib SHA256=$R9_HAMLIB_ACTUAL"
if [ "$R9_HAMLIB_ACTUAL" != "$R9_HAMLIB_SHA256" ]; then
  echo "[FAIL] R9 official Hamlib SHA mismatch: expected=$R9_HAMLIB_SHA256 actual=$R9_HAMLIB_ACTUAL"
  exit 86
fi
cp -f "$R9_HAMLIB_TMP" "$HAMLIB_PREFIX/bin/libhamlib-4.dll"
R9_INSTALLED_SHA="$(sha256sum "$HAMLIB_PREFIX/bin/libhamlib-4.dll" | awk '{print $1}')"
if [ "$R9_INSTALLED_SHA" != "$R9_HAMLIB_SHA256" ]; then
  echo '[FAIL] R9 official Hamlib runtime copy verification failed'
  exit 87
fi
echo '[PASS] R9 exact official JTDX 2.2.159 Hamlib runtime installed'

# Keep the R8 Flex 6xxx TCP regression, but now it runs against the exact
# official runtime DLL that the stock JTDX 2.2.159 distribution uses.
'''
    b = b.replace(anchor, block + anchor, 1)

if "MSI_VERSION='2.2.206'" not in b:
    if b.count("MSI_VERSION='2.2.205'") != 1:
        raise SystemExit('[FAIL] R9 MSI version 2.2.205 anchor missing')
    b = b.replace("MSI_VERSION='2.2.205'", "MSI_VERSION='2.2.206'", 1)

old_name = "MSI_NAME='JTDX-SuperHound-2.2.159-R8-FLEX6XXX-HAMLIB159-TEST-win64'"
new_name = "MSI_NAME='JTDX-SuperHound-2.2.159-R9-SLICEMASTER-FLEX-OFFICIAL-HAMLIB-TEST-win64'"
if new_name not in b:
    if b.count(old_name) != 1:
        raise SystemExit('[FAIL] R9 MSI name anchor missing')
    b = b.replace(old_name, new_name, 1)

bp.write_text(b, encoding='utf-8', newline='\n')

final = bp.read_text(encoding='utf-8')
for needle in [
    marker,
    '8cd24f3d935c740d2c3c901ae3af786964cfdd05101d47c913073aaa24f412da',
    'sourceforge.net/projects/jtdx/files/jtdx_2.2.159/Microsoft%20Windows/Hamlib/win64/libhamlib-4.dll/download',
    '[PASS] R9 exact official JTDX 2.2.159 Hamlib runtime installed',
    "MSI_VERSION='2.2.206'",
    new_name,
]:
    if needle not in final:
        raise SystemExit(f'[FAIL] R9 postcheck missing {needle!r}')

print('[PASS] R9 = R8 + exact official JTDX 2.2.159 win64 Hamlib runtime for Slice Master Flex 6xxx')
