# --- postchecks ---------------------------------------------------------------
checks = {
    'CMakeLists.txt': [
        'WebSockets Sql REQUIRED', 'Qt5::Sql', 'JTDX_QSQLITE_DLL',
        'DESTINATION plugins/sqldrivers',
    ],
    'logbook/logbook.h': ['ADIF _workedLog;', 'loadLog4OM'],
    'logbook/logbook.cpp': [
        'QSQLITE_OPEN_READONLY', 'PRAGMA query_only = ON', 'SELECT * FROM \\"Log\\"',
        '_workedLog.match', '_workedLog.add', 'return _log.getCount(mod);',
        'iMyGrid = fieldIndex', 'stationGrid.left(4) != mygrid.left(4).toUpper()',
    ],
    'Configuration.cpp': [
        'Use Log4OM SQLite database for Worked/New', 'Log4OMEnabled', 'Log4OMDatabase',
        'ui_->verticalLayout_9->insertWidget(0, log4om_group_)',
    ],
    'mainwindow.cpp': ['log4omWatcher', 'updateLog4OMWatcher', 'Log4OM Worked/New history reloaded'],
}
for path, needles in checks.items():
    _, data = load(path)
    for needle in needles:
        if needle not in data:
            raise SystemExit(f'[FAIL] R10 postcheck {path}: missing {needle!r}')

print('[PASS] R10 Log4OM SQLite Worked/New integration applied; local ADIF counter preserved; read-only fallback enabled')
