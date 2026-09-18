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
if not bp.exists():
    raise SystemExit('[FAIL] builder missing after R8 overlay')

b = bp.read_text(encoding='utf-8')

marker = '# SQ4KOU R9: use the exact official JTDX 2.2.159 win64 Hamlib runtime binary.'
if marker not in b:
    anchor = '# SQ4KOU R8: FlexRadio 6xxx release-Hamlib network-open regression gate.\n'
    if b.count(anchor) != 1:
        raise SystemExit(f'[FAIL] R9 insertion anchor count={b.count(anchor)}')
    block = r'''# SQ4KOU R9: use the exact official JTDX 2.2.159 win64 Hamlib runtime binary.
# Slice Master 6000 documents its TCP CAT listener as compatible with Hamlib's
# Flex 6xxx backend. The user also verified that the untouched JTDX 2.2.159
# package works with the same Slice Master setup, so for this regression build
# do not merely rebuild the same source with a 2026 MinGW toolchain: replace
# the runtime DLL with the exact 2022 binary published by the JTDX project.
R9_HAMLIB_URL='https://downloads.sourceforge.net/project/jtdx/jtdx_2.2.159/Microsoft%20Windows/Hamlib/win64/libhamlib-4.dll'
R9_HAMLIB_SHA='8cd24f3d935c740d2c3c901ae3af786964cfdd05101d47c913073aaa24f412da'
R9_HAMLIB_TMP="$WORK/libhamlib-4-official-jtdx-2.2.159.dll"

command -v curl >/dev/null 2>&1 || {
  echo '[FAIL] R9 curl missing - cannot retrieve official JTDX Hamlib DLL'
  exit 85
}
rm -f "$R9_HAMLIB_TMP"
curl -fL --retry 5 --retry-delay 2 --connect-timeout 30 \
  "$R9_HAMLIB_URL" -o "$R9_HAMLIB_TMP"

echo "$R9_HAMLIB_SHA  $R9_HAMLIB_TMP" | sha256sum -c - || {
  echo '[FAIL] R9 official Hamlib SHA256 mismatch'
  exit 86
}
cp -f "$R9_HAMLIB_TMP" "$HAMLIB_PREFIX/bin/libhamlib-4.dll"
echo '[PASS] R9 exact official JTDX 2.2.159 libhamlib-4.dll installed'
sha256sum "$HAMLIB_PREFIX/bin/libhamlib-4.dll"

'''
    b = b.replace(anchor, block + anchor, 1)

if "MSI_VERSION='2.2.206'" not in b:
    if b.count("MSI_VERSION='2.2.205'") != 1:
        raise SystemExit('[FAIL] R9 MSI version 2.2.205 anchor missing')
    b = b.replace("MSI_VERSION='2.2.205'", "MSI_VERSION='2.2.206'", 1)

old_name = "MSI_NAME='JTDX-SuperHound-2.2.159-R8-FLEX6XXX-HAMLIB159-TEST-win64'"
new_name = "MSI_NAME='JTDX-SuperHound-2.2.159-R9-FLEX6XXX-SLICEMASTER-OFFICIAL-HAMLIB-TEST-win64'"
if new_name not in b:
    if b.count(old_name) != 1:
        raise SystemExit('[FAIL] R9 MSI name anchor missing')
    b = b.replace(old_name, new_name, 1)

bp.write_text(b, encoding='utf-8', newline='\n')

final = bp.read_text(encoding='utf-8')
for needle in [
    marker,
    '8cd24f3d935c740d2c3c901ae3af786964cfdd05101d47c913073aaa24f412da',
    'downloads.sourceforge.net/project/jtdx/jtdx_2.2.159',
    '[PASS] R9 exact official JTDX 2.2.159 libhamlib-4.dll installed',
    "MSI_VERSION='2.2.206'",
    new_name,
]:
    if needle not in final:
        raise SystemExit(f'[FAIL] R9 postcheck missing {needle!r}')

print('[PASS] R9 = R8 + exact official JTDX 2.2.159 Hamlib runtime for Slice Master/Flex6xxx compatibility test')
