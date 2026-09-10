from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
bp = root / 'BUILD_JTDX_SUPERHOUND_MSI.ps1'
if not bp.exists():
    raise SystemExit(f'[FAIL] builder missing: {bp}')

b = bp.read_text(encoding='utf-8')

# The verified SQ4KOU FINAL source patch deliberately made the original
# JTDX 2.2.159 OmniRig backend optional so CI could build without a registered
# COM server.  Re-enable that exact upstream backend; do not add a parallel
# CAT implementation and do not touch the TCI BANDSAFE path.
old_flag = '  -DJTDX_ENABLE_OMNIRIG=OFF \\\n'
new_flag = '  -DJTDX_ENABLE_OMNIRIG=ON \\\n'
if new_flag not in b:
    if b.count(old_flag) != 1:
        raise SystemExit(f'[FAIL] OmniRig CMake flag anchor count={b.count(old_flag)}')
    b = b.replace(old_flag, new_flag, 1)

# Fail early and explicitly if the ActiveQt tool or the registered OmniRig
# type library is unavailable. CMake performs the same authoritative check.
old_tools = 'for t in git gcc g++ gfortran cmake ninja autoconf automake libtoolize make pkg-config patch qmake-qt5 lrelease-qt5; do\n'
new_tools = 'for t in git gcc g++ gfortran cmake ninja autoconf automake libtoolize make pkg-config patch qmake-qt5 lrelease-qt5 dumpcpp; do\n'
if new_tools not in b:
    if b.count(old_tools) != 1:
        raise SystemExit(f'[FAIL] build-tool gate anchor count={b.count(old_tools)}')
    b = b.replace(old_tools, new_tools, 1)

cmake_anchor = 'rm -rf jtdx/build-superhound\ncmake -S jtdx -B jtdx/build-superhound -G Ninja \\\n'
preflight = '''# OmniRig is a local COM server. The official runtime must be registered on
# the build host so Qt dumpcpp can resolve its type library.
OMNIRIG_AXSERVER="$(dumpcpp -getfile {4FE359C5-A58F-459D-BE95-CA559FB4F270} 2>/dev/null | tr -d '\\r' || true)"
if [ -z "$OMNIRIG_AXSERVER" ]; then
  echo '[FAIL] OmniRig COM server/type library is not registered on this Windows host'
  exit 38
fi
echo "[PASS] OmniRig COM type library: $OMNIRIG_AXSERVER"

rm -rf jtdx/build-superhound
cmake -S jtdx -B jtdx/build-superhound -G Ninja \\
'''
if '[PASS] OmniRig COM type library:' not in b:
    if b.count(cmake_anchor) != 1:
        raise SystemExit(f'[FAIL] CMake preflight anchor count={b.count(cmake_anchor)}')
    b = b.replace(cmake_anchor, preflight, 1)

post_anchor = "echo '[PASS] CMake FFTW threads link gate'\n\ncmake --build jtdx/build-superhound --parallel\n"
post_block = '''echo '[PASS] CMake FFTW threads link gate'

grep -Fq 'JTDX_ENABLE_OMNIRIG:BOOL=ON' jtdx/build-superhound/CMakeCache.txt || {
  echo '[FAIL] OmniRig CMake option is not ON'
  exit 39
}
grep -Fq 'OmniRigTransceiver.cpp' jtdx/build-superhound/build.ninja || {
  echo '[FAIL] OmniRigTransceiver.cpp is absent from Ninja build graph'
  exit 40
}
grep -Fq 'JTDX_ENABLE_OMNIRIG' jtdx/build-superhound/build.ninja || {
  echo '[FAIL] OmniRig compile definition is absent from Ninja build graph'
  exit 41
}
if ! find jtdx/build-superhound -type f -iname 'OmniRig.h' -print -quit | grep -q .; then
  echo '[FAIL] generated OmniRig ActiveQt wrapper header missing'
  exit 42
fi
echo '[PASS] OmniRig configure/source/generator gates'

cmake --build jtdx/build-superhound --parallel
'''
if "echo '[PASS] OmniRig configure/source/generator gates'" not in b:
    if b.count(post_anchor) != 1:
        raise SystemExit(f'[FAIL] CMake postcheck anchor count={b.count(post_anchor)}')
    b = b.replace(post_anchor, post_block, 1)

# This is an additive build variant over FINAL TCI BANDSAFE.
if "MSI_VERSION='2.2.177'" not in b:
    old_ver = "MSI_VERSION='2.2.176'"
    if b.count(old_ver) != 1:
        raise SystemExit(f'[FAIL] BANDSAFE MSI version anchor count={b.count(old_ver)}')
    b = b.replace(old_ver, "MSI_VERSION='2.2.177'", 1)

new_name = "MSI_NAME='JTDX-SuperHound-2.2.159-FINAL-TCI-BANDSAFE-OMNIRIG-win64'"
if new_name not in b:
    old_name = "MSI_NAME='JTDX-SuperHound-2.2.159-FINAL-TCI-BANDSAFE-win64'"
    if b.count(old_name) != 1:
        raise SystemExit(f'[FAIL] BANDSAFE MSI name anchor count={b.count(old_name)}')
    b = b.replace(old_name, new_name, 1)

bp.write_text(b, encoding='utf-8', newline='\n')

for needle in [
    '-DJTDX_ENABLE_OMNIRIG=ON',
    'lrelease-qt5 dumpcpp',
    '[PASS] OmniRig COM type library:',
    'JTDX_ENABLE_OMNIRIG:BOOL=ON',
    'OmniRigTransceiver.cpp',
    "MSI_VERSION='2.2.177'",
    new_name,
]:
    if needle not in b:
        raise SystemExit(f'[FAIL] OmniRig builder postcheck missing {needle!r}')

print('[PASS] native JTDX OmniRig build overlay')
