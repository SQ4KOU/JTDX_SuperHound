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

old_name = "MSI_NAME='JTDX-SuperHound-2.2.159-R9-SLICEMASTER-FLEX-OFFICIAL-HAMLIB-TEST-win64'"
new_name = "MSI_NAME='JTDX-SuperHound-2.2.159-R10-SLICEMASTER-FLEX-LOG4OM-TEST-win64'"
if new_name not in b:
    if b.count(old_name) != 1:
        raise SystemExit('[FAIL] R10 R9 MSI name anchor missing')
    b = b.replace(old_name, new_name, 1)

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
