from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
bp = root / 'BUILD_JTDX_SUPERHOUND_MSI.ps1'
pp = root / 'patch_superhound.py'
if not bp.exists():
    raise SystemExit(f'[FAIL] builder missing: {bp}')
if not pp.exists():
    raise SystemExit(f'[FAIL] source patcher missing: {pp}')

# JTDX 2.2.159 already contains the native OmniRigTransceiver backend.
# SQ4KOU FINAL made it optional because upstream CMake relies on dumpcpp
# registry discovery.  Keep that native backend and make both the OmniRig
# server file and dumpcpp executable explicit inputs.  The dumpcpp executable
# may come from MSYS2 qt5-static; generated code is compiled against the
# normal dynamic Qt5 ActiveQt libraries used by JTDX.
p = pp.read_text(encoding='utf-8')
source_marker = '# Ensure CPack/BundleUtilities can resolve the separately built JTDX Hamlib DLL.\n'
source_overlay = r"""# SQ4KOU OmniRig x64: deterministic ActiveQt inputs.
# Replace the generated optional OmniRig block with explicit-file capable
# handling. DUMPCPP can be supplied with -DDUMPCPP=... so no binary has to be
# copied into /mingw64/bin (which would conflict with pacman-owned files).
replace_once('CMakeLists.txt',
    '''if (WIN32 AND JTDX_ENABLE_OMNIRIG)
  # generate the OmniRig COM interface source only when explicitly enabled
  find_program (DUMPCPP dumpcpp)
  if (DUMPCPP-NOTFOUND)
    message (FATAL_ERROR "dumpcpp tool not found")
  endif (DUMPCPP-NOTFOUND)
  execute_process (
    COMMAND ${DUMPCPP} -getfile {4FE359C5-A58F-459D-BE95-CA559FB4F270}
    OUTPUT_VARIABLE AXSERVER
    OUTPUT_STRIP_TRAILING_WHITESPACE
    )
  string (STRIP "${AXSERVER}" AXSERVER)
  if (NOT AXSERVER)
    message (FATAL_ERROR "You need to install OmniRig on this computer")
  endif (NOT AXSERVER)
  string (REPLACE "\\\"" "" AXSERVER ${AXSERVER})
  file (TO_CMAKE_PATH ${AXSERVER} AXSERVERSRCS)
endif ()
''',
    '''if (WIN32 AND JTDX_ENABLE_OMNIRIG)
  # Generate the native JTDX OmniRig ActiveQt interface. The build may pass
  # DUMPCPP explicitly (for example qt5-static/bin/dumpcpp.exe) to avoid
  # registry/PATH and pacman package-layout ambiguity.
  if (NOT DUMPCPP)
    find_program (DUMPCPP NAMES dumpcpp-qt5 dumpcpp)
  endif ()
  if (NOT DUMPCPP OR NOT EXISTS "${DUMPCPP}")
    message (FATAL_ERROR "Qt5 ActiveQt dumpcpp tool not found: ${DUMPCPP}")
  endif ()
  set (JTDX_OMNIRIG_SERVER "" CACHE FILEPATH "Path to OmniRig.exe/type library for ActiveQt wrapper generation")
  if (JTDX_OMNIRIG_SERVER)
    if (NOT EXISTS "${JTDX_OMNIRIG_SERVER}")
      message (FATAL_ERROR "JTDX_OMNIRIG_SERVER does not exist: ${JTDX_OMNIRIG_SERVER}")
    endif ()
    set (AXSERVER "${JTDX_OMNIRIG_SERVER}")
  else ()
    execute_process (
      COMMAND ${DUMPCPP} -getfile {4FE359C5-A58F-459D-BE95-CA559FB4F270}
      OUTPUT_VARIABLE AXSERVER
      OUTPUT_STRIP_TRAILING_WHITESPACE
      )
    string (STRIP "${AXSERVER}" AXSERVER)
    if (NOT AXSERVER)
      message (FATAL_ERROR "OmniRig type library could not be resolved; set JTDX_OMNIRIG_SERVER explicitly")
    endif ()
    string (REPLACE "\\\"" "" AXSERVER ${AXSERVER})
  endif ()
  file (TO_CMAKE_PATH "${AXSERVER}" AXSERVERSRCS)
  message (STATUS "OmniRig ActiveQt server: ${AXSERVERSRCS}")
  message (STATUS "OmniRig ActiveQt dumpcpp: ${DUMPCPP}")
endif ()
''',
    'CMake deterministic OmniRig ActiveQt inputs')

"""
if '# SQ4KOU OmniRig x64: deterministic ActiveQt inputs.' not in p:
    if p.count(source_marker) != 1:
        raise SystemExit(f'[FAIL] OmniRig source-overlay insertion anchor count={p.count(source_marker)}')
    p = p.replace(source_marker, source_overlay + source_marker, 1)

audit_old = "'CMakeLists.txt': ['wsjt_superhound_FSRCS', 'wsjt_superhound_CSRCS', 'JTDX_ENABLE_OMNIRIG', 'hamlib_bin_dir', 'CPACK_GENERATOR \"WIX\"'],"
audit_new = "'CMakeLists.txt': ['wsjt_superhound_FSRCS', 'wsjt_superhound_CSRCS', 'JTDX_ENABLE_OMNIRIG', 'JTDX_OMNIRIG_SERVER', 'DUMPCPP', 'hamlib_bin_dir', 'CPACK_GENERATOR \"WIX\"'],"
if audit_new not in p:
    if p.count(audit_old) != 1:
        raise SystemExit(f'[FAIL] OmniRig source-audit marker anchor count={p.count(audit_old)}')
    p = p.replace(audit_old, audit_new, 1)
pp.write_text(p, encoding='utf-8', newline='\n')

b = bp.read_text(encoding='utf-8')

# Re-enable the exact native backend; TCI BANDSAFE remains untouched.
old_flag = '  -DJTDX_ENABLE_OMNIRIG=OFF \\\n'
new_flag = '  -DJTDX_ENABLE_OMNIRIG=ON \\\n'
if new_flag not in b:
    if b.count(old_flag) != 1:
        raise SystemExit(f'[FAIL] OmniRig CMake flag anchor count={b.count(old_flag)}')
    b = b.replace(old_flag, new_flag, 1)

# Do not require dumpcpp in the normal /mingw64/bin PATH.  It is supplied by
# explicit path from qt5-static, avoiding conflicts with the dynamic ActiveQt
# package installed later by the original ONECLICK dependency step.
old_tools = 'for t in git gcc g++ gfortran cmake ninja autoconf automake libtoolize make pkg-config patch qmake-qt5 lrelease-qt5; do\n'
if old_tools not in b:
    # tolerate an earlier OmniRig overlay only when it is this exact form
    old_tools_with_dump = 'for t in git gcc g++ gfortran cmake ninja autoconf automake libtoolize make pkg-config patch qmake-qt5 lrelease-qt5 dumpcpp-qt5; do\n'
    if old_tools_with_dump in b:
        b = b.replace(old_tools_with_dump, old_tools, 1)
    else:
        raise SystemExit('[FAIL] build-tool gate anchor missing')

cmake_anchor = 'rm -rf jtdx/build-superhound\ncmake -S jtdx -B jtdx/build-superhound -G Ninja \\\n'
preflight = '''OMNIRIG_SERVER_WIN="${SH_OMNIRIG_SERVER_WIN:-C:/Program Files (x86)/Afreet/OmniRig/OmniRig.exe}"
OMNIRIG_SERVER_MSYS="$(cygpath -u "$OMNIRIG_SERVER_WIN")"
if [ ! -f "$OMNIRIG_SERVER_MSYS" ] && [ -f '/c/Program Files/Afreet/OmniRig/OmniRig.exe' ]; then
  OMNIRIG_SERVER_MSYS='/c/Program Files/Afreet/OmniRig/OmniRig.exe'
  OMNIRIG_SERVER_WIN='C:/Program Files/Afreet/OmniRig/OmniRig.exe'
fi
if [ ! -f "$OMNIRIG_SERVER_MSYS" ]; then
  echo "[FAIL] OmniRig server executable not found: $OMNIRIG_SERVER_WIN"
  exit 38
fi
OMNIRIG_SERVER_WIN="$(cygpath -m "$OMNIRIG_SERVER_MSYS")"

DUMPCPP_WIN="${SH_DUMPCPP_WIN:-C:/msys64/mingw64/qt5-static/bin/dumpcpp.exe}"
DUMPCPP_MSYS="$(cygpath -u "$DUMPCPP_WIN")"
if [ ! -f "$DUMPCPP_MSYS" ]; then
  echo "[FAIL] Qt5 ActiveQt dumpcpp executable not found: $DUMPCPP_WIN"
  echo '[FAIL] Install mingw-w64-x86_64-qt5-static or set SH_DUMPCPP_WIN'
  exit 39
fi
DUMPCPP_WIN="$(cygpath -m "$DUMPCPP_MSYS")"
echo "[PASS] OmniRig ActiveQt server file: $OMNIRIG_SERVER_WIN"
echo "[PASS] Qt5 ActiveQt dumpcpp file: $DUMPCPP_WIN"

rm -rf jtdx/build-superhound
cmake -S jtdx -B jtdx/build-superhound -G Ninja \\
'''
if '[PASS] Qt5 ActiveQt dumpcpp file:' not in b:
    if b.count(cmake_anchor) != 1:
        raise SystemExit(f'[FAIL] CMake preflight anchor count={b.count(cmake_anchor)}')
    b = b.replace(cmake_anchor, preflight, 1)

cmake_flag = '  -DJTDX_ENABLE_OMNIRIG=ON \\\n'
cmake_args = '  -DJTDX_ENABLE_OMNIRIG=ON \\\n  -DDUMPCPP="$DUMPCPP_WIN" \\\n  -DJTDX_OMNIRIG_SERVER="$OMNIRIG_SERVER_WIN" \\\n'
if '-DDUMPCPP="$DUMPCPP_WIN"' not in b:
    if b.count(cmake_flag) != 1:
        raise SystemExit(f'[FAIL] OmniRig CMake argument anchor count={b.count(cmake_flag)}')
    b = b.replace(cmake_flag, cmake_args, 1)

post_anchor = "echo '[PASS] CMake FFTW threads link gate'\n\ncmake --build jtdx/build-superhound --parallel\n"
post_block = '''echo '[PASS] CMake FFTW threads link gate'

grep -Fq 'JTDX_ENABLE_OMNIRIG:BOOL=ON' jtdx/build-superhound/CMakeCache.txt || {
  echo '[FAIL] OmniRig CMake option is not ON'
  exit 40
}
grep -Fq 'JTDX_OMNIRIG_SERVER:FILEPATH=' jtdx/build-superhound/CMakeCache.txt || {
  echo '[FAIL] explicit OmniRig server path is absent from CMake cache'
  exit 41
}
grep -Fq 'DUMPCPP:FILEPATH=' jtdx/build-superhound/CMakeCache.txt && true
if ! grep -Eq '^DUMPCPP(:FILEPATH)?=' jtdx/build-superhound/CMakeCache.txt; then
  echo '[FAIL] explicit dumpcpp path is absent from CMake cache'
  exit 42
fi
grep -Fq 'OmniRigTransceiver.cpp' jtdx/build-superhound/build.ninja || {
  echo '[FAIL] OmniRigTransceiver.cpp is absent from Ninja build graph'
  exit 43
}
grep -Fq 'JTDX_ENABLE_OMNIRIG' jtdx/build-superhound/build.ninja || {
  echo '[FAIL] OmniRig compile definition is absent from Ninja build graph'
  exit 44
}
echo '[PASS] OmniRig configure/source gates'

cmake --build jtdx/build-superhound --parallel

if ! find jtdx/build-superhound -type f -iname 'OmniRig.h' -print -quit | grep -q .; then
  echo '[FAIL] generated OmniRig ActiveQt wrapper header missing after build'
  exit 45
fi
if ! find jtdx/build-superhound -type f -iname 'OmniRig.cpp' -print -quit | grep -q .; then
  echo '[FAIL] generated OmniRig ActiveQt wrapper source missing after build'
  exit 46
fi
echo '[PASS] OmniRig ActiveQt wrapper generation gate'
'''
if "echo '[PASS] OmniRig ActiveQt wrapper generation gate'" not in b:
    if b.count(post_anchor) != 1:
        raise SystemExit(f'[FAIL] CMake postcheck anchor count={b.count(post_anchor)}')
    b = b.replace(post_anchor, post_block, 1)

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
    '-DDUMPCPP="$DUMPCPP_WIN"',
    '-DJTDX_OMNIRIG_SERVER="$OMNIRIG_SERVER_WIN"',
    '[PASS] OmniRig ActiveQt server file:',
    '[PASS] Qt5 ActiveQt dumpcpp file:',
    'JTDX_ENABLE_OMNIRIG:BOOL=ON',
    'JTDX_OMNIRIG_SERVER:FILEPATH=',
    'OmniRigTransceiver.cpp',
    '[PASS] OmniRig ActiveQt wrapper generation gate',
    "MSI_VERSION='2.2.177'",
    new_name,
]:
    if needle not in b:
        raise SystemExit(f'[FAIL] OmniRig builder postcheck missing {needle!r}')
for needle in [
    '# SQ4KOU OmniRig x64: deterministic ActiveQt inputs.',
    'JTDX_OMNIRIG_SERVER',
    'DUMPCPP',
    'CMake deterministic OmniRig ActiveQt inputs',
]:
    if needle not in p:
        raise SystemExit(f'[FAIL] OmniRig source-patcher postcheck missing {needle!r}')

print('[PASS] native JTDX OmniRig build/source overlay')
