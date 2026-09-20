# SQ4KOU R10 / Log4OM SQLite integration fragment.
# This file is appended to the generated patch_superhound.py by the R10 overlay.

# --- helpers -----------------------------------------------------------------
def r10_replace_once(path, old, new, label):
    p, t = load(path)
    if new in t:
        print(f'[SKIP] R10 {label} already present')
        return
    count = t.count(old)
    if count != 1:
        raise SystemExit(f'[FAIL] R10 {label} anchor count={count}')
    t = t.replace(old, new, 1)
    save(p, t)
    print(f'[OK] R10 {label}')

# --- CMake / QtSql ------------------------------------------------------------
p, t = load('CMakeLists.txt')
old = 'find_package (Qt5 COMPONENTS Widgets SerialPort Multimedia LinguistTools WebSockets REQUIRED)'
new = 'find_package (Qt5 COMPONENTS Widgets SerialPort Multimedia LinguistTools WebSockets Sql REQUIRED)'
if new not in t:
    if t.count(old) != 1:
        raise SystemExit(f'[FAIL] R10 QtSql find_package anchor count={t.count(old)}')
    t = t.replace(old, new, 1)

old_apple = 'target_link_libraries (jtdx Qt5::SerialPort wsjt_fort wsjt_cxx wsjt_qt wsjt_qtmm ${FFTW3_LIBRARIES})'
new_apple = 'target_link_libraries (jtdx Qt5::SerialPort Qt5::Sql wsjt_fort wsjt_cxx wsjt_qt wsjt_qtmm ${FFTW3_LIBRARIES})'
if new_apple not in t:
    if t.count(old_apple) != 1:
        raise SystemExit(f'[FAIL] R10 QtSql Apple link anchor count={t.count(old_apple)}')
    t = t.replace(old_apple, new_apple, 1)

old_other = 'target_link_libraries (jtdx Qt5::SerialPort wsjt_fort_omp wsjt_cxx wsjt_qt wsjt_qtmm ${FFTW3_LIBRARIES})'
new_other = 'target_link_libraries (jtdx Qt5::SerialPort Qt5::Sql wsjt_fort_omp wsjt_cxx wsjt_qt wsjt_qtmm ${FFTW3_LIBRARIES})'
if new_other not in t:
    if t.count(old_other) != 1:
        raise SystemExit(f'[FAIL] R10 QtSql non-Apple link anchor count={t.count(old_other)}')
    t = t.replace(old_other, new_other, 1)

marker = '# SQ4KOU R10: install only the SQLite Qt SQL driver.'
if marker not in t:
    anchor = '''#\n# installation\n#\ninstall (TARGETS jtdx\n'''
    if t.count(anchor) != 1:
        raise SystemExit(f'[FAIL] R10 qsqlite install anchor count={t.count(anchor)}')
    block = '''#\n# installation\n#\n# SQ4KOU R10: install only the SQLite Qt SQL driver.\nif (WIN32)\n  get_filename_component (JTDX_QT5_PREFIX "${Qt5_DIR}/../../.." ABSOLUTE)\n  set (JTDX_QSQLITE_CANDIDATES\n    "${JTDX_QT5_PREFIX}/share/qt5/plugins/sqldrivers/qsqlite.dll"\n    "${JTDX_QT5_PREFIX}/lib/qt5/plugins/sqldrivers/qsqlite.dll"\n    )\n  set (JTDX_QSQLITE_DLL "")\n  foreach (candidate ${JTDX_QSQLITE_CANDIDATES})\n    if (EXISTS "${candidate}")\n      set (JTDX_QSQLITE_DLL "${candidate}")\n      break ()\n    endif ()\n  endforeach ()\n  if (NOT JTDX_QSQLITE_DLL)\n    message (FATAL_ERROR "R10 qsqlite.dll not found below Qt5 prefix ${JTDX_QT5_PREFIX}")\n  endif ()\n  message (STATUS "R10 qsqlite.dll: ${JTDX_QSQLITE_DLL}")\n  install (FILES "${JTDX_QSQLITE_DLL}" DESTINATION plugins/sqldrivers)\nendif ()\n\ninstall (TARGETS jtdx\n'''
    t = t.replace(anchor, block, 1)

save(p, t)
