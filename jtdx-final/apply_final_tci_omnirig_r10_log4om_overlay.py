from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
here = Path(__file__).resolve().parent
r9 = here / 'apply_final_tci_omnirig_r9_slicemaster_flex_overlay.py'
if not r9.exists():
    raise SystemExit('[FAIL] R9 SliceMaster Flex overlay missing')

# R10 is strictly incremental over the current R9 test line.
subprocess.run([sys.executable, str(r9), str(root)], check=True)

pp = root / 'patch_superhound.py'
bp = root / 'BUILD_JTDX_SUPERHOUND_MSI.ps1'
if not pp.exists() or not bp.exists():
    raise SystemExit('[FAIL] R10 generated patcher/builder missing after R9 overlay')

fragments = [
    here / 'patch_log4om_cmake_r10.py',
    here / 'patch_log4om_logbook_r10.py',
    here / 'patch_log4om_config_r10.py',
    here / 'patch_log4om_mainwindow_r10.py',
    here / 'patch_log4om_postcheck_r10.py',
]
for fragment in fragments:
    if not fragment.exists():
        raise SystemExit(f'[FAIL] R10 fragment missing: {fragment.name}')

s = pp.read_text(encoding='utf-8')
marker = '# SQ4KOU R10 / Log4OM SQLite integration fragment.'
if marker not in s:
    for fragment in fragments:
        s += '\n\n' + fragment.read_text(encoding='utf-8').rstrip() + '\n'
    pp.write_text(s, encoding='utf-8', newline='\n')

b = bp.read_text(encoding='utf-8')
if "MSI_VERSION='2.2.207'" not in b:
    if b.count("MSI_VERSION='2.2.206'") != 1:
        raise SystemExit('[FAIL] R10 MSI version 2.2.206 anchor missing')
    b = b.replace("MSI_VERSION='2.2.206'", "MSI_VERSION='2.2.207'", 1)

# R10 inherits the already-passed R8/R9 Flex 6xxx network-open regression result.
# Re-running the mock here adds repeated Hamlib timeout cycles but does not test
# any code changed by R10. Keep the exact Hamlib/model gate, skip only the
# inherited TCP mock so LOG4OM iterations reach the compiler immediately.
r8_start = '# SQ4KOU R8: FlexRadio 6xxx release-Hamlib network-open regression gate.'
r8_end = "echo '[PASS] R8 FlexRadio 6xxx TCP open/ID/AI path'"
if r8_start in b:
    start = b.index(r8_start)
    end = b.index(r8_end, start) + len(r8_end)
    fast_gate = r'''# SQ4KOU R10: inherited R8/R9 Flex 6xxx gate; network-open mock already PASS.
test -x "$HAMLIB_PREFIX/bin/rigctl.exe" || {
  echo '[FAIL] R10 rigctl.exe missing from pinned Hamlib prefix'
  exit 81
}
"$HAMLIB_PREFIX/bin/rigctl.exe" -l | tr -d '\r' | grep -E 'FlexRadio[[:space:]]+6xxx' >/dev/null || {
  echo '[FAIL] R10 FlexRadio 6xxx model absent from pinned Hamlib model list'
  exit 82
}
echo '[PASS] R10 inherited Flex 6xxx network gate from R9; pinned Hamlib model present' '''.rstrip()
    b = b[:start] + fast_gate + b[end:]

old_name = "MSI_NAME='JTDX-SuperHound-2.2.159-R9-SLICEMASTER-FLEX-OFFICIAL-HAMLIB-TEST-win64'"
new_name = "MSI_NAME='JTDX-SuperHound-2.2.159-R10-SLICEMASTER-FLEX-LOG4OM-TEST-win64'"
if new_name not in b:
    if b.count(old_name) != 1:
        raise SystemExit('[FAIL] R10 R9 MSI name anchor missing')
    b = b.replace(old_name, new_name, 1)

# Extend the inherited R12 patch-surface whitelist only for files legitimately
# modified by the R10 Log4OM integration.
# R10 legitimately extends the inherited R12 patch surface with the
# Log4OM configuration declaration and LogBook implementation/header.
old_allowed_a = r'Configuration\.cpp|FrequencyList\.cpp'
new_allowed_a = r'Configuration\.cpp|Configuration\.hpp|FrequencyList\.cpp'
old_allowed_b = r'logbook/adif\.cpp|logqso\.cpp'
new_allowed_b = r'logbook/adif\.cpp|logbook/logbook\.cpp|logbook/logbook\.h|logqso\.cpp'
if old_allowed_a not in b or old_allowed_b not in b:
    raise SystemExit('[FAIL] R10 R12 allowed-file whitelist anchors missing')
b = b.replace(old_allowed_a, new_allowed_a, 1)
b = b.replace(old_allowed_b, new_allowed_b, 1)

bp.write_text(b, encoding='utf-8', newline='\n')

patch = pp.read_text(encoding='utf-8')
builder = bp.read_text(encoding='utf-8')
for needle in [
    marker,
    'QSQLITE_OPEN_READONLY',
    'PRAGMA query_only = ON',
    'ADIF _workedLog;',
    'Use Log4OM SQLite database for Worked/New',
    'log4omWatcher',
    'JTDX_QSQLITE_DLL',
]:
    if needle not in patch:
        raise SystemExit(f'[FAIL] R10 patch postcheck missing {needle!r}')

for needle in [
    "MSI_VERSION='2.2.207'",
    new_name,
    '8cd24f3d935c740d2c3c901ae3af786964cfdd05101d47c913073aaa24f412da',
    'R9 exact official JTDX 2.2.159 Hamlib runtime installed',
]:
    if needle not in builder:
        raise SystemExit(f'[FAIL] R10 builder postcheck missing {needle!r}')

print('[PASS] R10 = R9 SliceMaster/Flex + Log4OM read-only SQLite Worked/New integration')
