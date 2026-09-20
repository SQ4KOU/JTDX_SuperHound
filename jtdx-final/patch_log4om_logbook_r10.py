# --- LogBook: local ADIF + independent Worked/New history --------------------
p, t = load('logbook/logbook.h')
old = '    void init(const QString mycall,const QString mygrid,const QString mydate);'
new = '    void init(const QString mycall,const QString mygrid,const QString mydate, bool useLog4OM=false, const QString log4omDatabase=QString());'
if new not in t:
    if t.count(old) != 1:
        raise SystemExit(f'[FAIL] R10 LogBook init declaration anchor count={t.count(old)}')
    t = t.replace(old, new, 1)
old = '''private:\n   CountryDat _countries;\n   ADIF _log;\n};'''
new = '''private:\n   bool loadLog4OM(const QString database,const QString mycall,const QString mygrid,const QString mydate);\n   CountryDat _countries;\n   ADIF _log;       // local wsjtx_log.adi: local counter + immediate local QSO state\n   ADIF _workedLog; // Worked/New source: Log4OM when healthy, otherwise local ADIF\n};'''
if new not in t:
    if t.count(old) != 1:
        raise SystemExit(f'[FAIL] R10 LogBook private anchor count={t.count(old)}')
    t = t.replace(old, new, 1)
save(p, t)

p, t = load('logbook/logbook.cpp')
inc_anchor = '#include <iostream>\n'
inc_block = '''#include <iostream>\n#include <QFileInfo>\n#include <QRegularExpression>\n#include <QSqlDatabase>\n#include <QSqlError>\n#include <QSqlQuery>\n#include <QSqlRecord>\n#include <QVariant>\n#include <initializer_list>\n'''
if '#include <QSqlDatabase>' not in t:
    if t.count(inc_anchor) != 1:
        raise SystemExit(f'[FAIL] R10 LogBook include anchor count={t.count(inc_anchor)}')
    t = t.replace(inc_anchor, inc_block, 1)

old_init = '''void LogBook::init(const QString mycall,const QString mygrid,const QString mydate)\n{\n  QDir dataPath {QStandardPaths::writableLocation (QStandardPaths::DataLocation)};\n  QString countryDataFilename,lotwDataFilename;'''
new_init = '''void LogBook::init(const QString mycall,const QString mygrid,const QString mydate, bool useLog4OM, const QString log4omDatabase)\n{\n  QDir dataPath {QStandardPaths::writableLocation (QStandardPaths::DataLocation)};\n  QString countryDataFilename,lotwDataFilename;'''
if new_init not in t:
    if t.count(old_init) != 1:
        raise SystemExit(f'[FAIL] R10 LogBook init definition anchor count={t.count(old_init)}')
    t = t.replace(old_init, new_init, 1)

old_load = '''  _log.init(dataPath.absoluteFilePath (logFileName), &_countries);\n  _log.load(mycall,mygrid,mydate);\n'''
new_load = '''  const QString localLog = dataPath.absoluteFilePath (logFileName);\n  _log.init(localLog, &_countries);\n  _log.load(mycall,mygrid,mydate);\n\n  bool log4omLoaded = false;\n  if (useLog4OM && !log4omDatabase.trimmed().isEmpty()) {\n    log4omLoaded = loadLog4OM(log4omDatabase.trimmed(), mycall, mygrid, mydate);\n  }\n  if (!log4omLoaded) {\n    _workedLog.init(localLog, &_countries);\n    _workedLog.load(mycall,mygrid,mydate);\n  }\n'''
if new_load not in t:
    if t.count(old_load) != 1:
        raise SystemExit(f'[FAIL] R10 LogBook local load anchor count={t.count(old_load)}')
    t = t.replace(old_load, new_load, 1)

insert_before = '\nvoid LogBook::matchCQZ('
if 'bool LogBook::loadLog4OM(' not in t:
    if t.count(insert_before) != 1:
        raise SystemExit(f'[FAIL] R10 loadLog4OM insertion anchor count={t.count(insert_before)}')
    impl = '''\nbool LogBook::loadLog4OM(const QString database,const QString mycall,const QString mygrid,const QString mydate)\n{\n  QFileInfo dbInfo(database);\n  if (!dbInfo.exists() || !dbInfo.isFile() || !dbInfo.isReadable()) {\n    qWarning() << "Log4OM database unavailable, using wsjtx_log.adi:" << database;\n    return false;\n  }\n\n  const QString connectionName = QString("jtdx_log4om_%1")\n      .arg(static_cast<qulonglong>(reinterpret_cast<quintptr>(this)), 0, 16);\n  bool success = false;\n  {\n    QSqlDatabase db = QSqlDatabase::addDatabase("QSQLITE", connectionName);\n    db.setConnectOptions("QSQLITE_OPEN_READONLY");\n    db.setDatabaseName(dbInfo.absoluteFilePath());\n    if (!db.open()) {\n      qWarning() << "Log4OM database open failed, using wsjtx_log.adi:" << db.lastError().text();\n    } else {\n      QSqlQuery pragma(db);\n      if (!pragma.exec("PRAGMA query_only = ON")) {\n        qWarning() << "Log4OM PRAGMA query_only failed:" << pragma.lastError().text();\n      } else {\n        QSqlQuery query(db);\n        query.setForwardOnly(true);\n        if (!query.exec("SELECT * FROM \\\"Log\\\"")) {\n          qWarning() << "Log4OM Log query failed, using wsjtx_log.adi:" << query.lastError().text();\n        } else {\n          QSqlRecord record = query.record();\n          auto fieldIndex = [&record](std::initializer_list<const char *> names) -> int {\n            for (const char * wanted : names) {\n              for (int i = 0; i < record.count(); ++i) {\n                if (record.fieldName(i).compare(QString::fromLatin1(wanted), Qt::CaseInsensitive) == 0)\n                  return i;\n              }\n            }\n            return -1;\n          };\n\n          const int iCall = fieldIndex({"Callsign", "Call"});\n          const int iBand = fieldIndex({"Band"});\n          const int iMode = fieldIndex({"Mode"});\n          const int iSubMode = fieldIndex({"SubMode", "Submode"});\n          const int iDate = fieldIndex({"QsoDate", "QSODate", "QSO_DATE"});\n          const int iGrid = fieldIndex({"GridSquare", "Gridsquare", "Grid"});\n          const int iName = fieldIndex({"Name"});\n          const int iStation = fieldIndex({"StationCallsign", "StationCall", "Station_Callsign"});\n          const int iMyGrid = fieldIndex({"MyGridSquare", "MyGridsquare", "MyGrid"});\n\n          if (iCall < 0 || iBand < 0 || iMode < 0) {\n            qWarning() << "Log4OM schema missing required Callsign/Call, Band or Mode column; using wsjtx_log.adi";\n          } else {\n            ADIF candidate;\n            candidate.init(QString(), &_countries);\n            candidate.load(QString(), QString(), QString()); // clear all indexes\n            int accepted = 0;\n            while (query.next()) {\n              QString call = query.value(iCall).toString().trimmed().toUpper();\n              QString band = query.value(iBand).toString().trimmed().toLower();\n              QString mode = query.value(iMode).toString().trimmed().toUpper();\n              QString subMode = iSubMode >= 0 ? query.value(iSubMode).toString().trimmed().toUpper() : QString();\n              QString date = iDate >= 0 ? query.value(iDate).toString().trimmed() : QString();\n              QString grid = iGrid >= 0 ? query.value(iGrid).toString().trimmed().toUpper() : QString();\n              QString name = iName >= 0 ? query.value(iName).toString().trimmed() : QString();\n\n              if (call.isEmpty() || band.isEmpty() || mode.isEmpty()) continue;\n\n              if (!mycall.isEmpty() && iStation >= 0) {\n                QString station = query.value(iStation).toString().trimmed().toUpper();\n                if (!station.isEmpty() && station != mycall.toUpper()) continue;\n              }\n              if (!mygrid.isEmpty() && iMyGrid >= 0) {\n                QString stationGrid = query.value(iMyGrid).toString().trimmed().toUpper();\n                if (!stationGrid.isEmpty() && stationGrid.left(4) != mygrid.left(4).toUpper()) continue;\n              }\n\n              date.remove(QRegularExpression("[^0-9]"));\n              if (!mydate.isEmpty() && !date.isEmpty()) {\n                QString compareDate = date.left(14);\n                while (compareDate.length() < 14) compareDate += '0';\n                if (compareDate.toLongLong() < mydate.toLongLong()) continue;\n              }\n\n              if (mode == "MFSK" && !subMode.isEmpty()) mode = subMode;\n              if (mode.startsWith("JT9")) mode = "JT9";\n              else if (mode.startsWith("JT65")) mode = "JT65";\n\n              candidate.add(call, band, mode, date.left(8), grid, name);\n              ++accepted;\n            }\n            _workedLog = candidate;\n            success = true;\n            qDebug() << "Log4OM Worked/New history loaded read-only:" << accepted << "QSO from" << database;\n          }\n        }\n      }\n      db.close();\n    }\n  }\n  QSqlDatabase::removeDatabase(connectionName);\n  return success;\n}\n'''
    t = t.replace(insert_before, impl + insert_before, 1)

# Route Worked/New lookups to the independent history while keeping local counter local.
for old, new in [
    ('_log.matchCqz(', '_workedLog.matchCqz('),
    ('_log.matchItuz(', '_workedLog.matchItuz('),
    ('_log.matchCountry(', '_workedLog.matchCountry('),
    ('_log.matchGrid(', '_workedLog.matchGrid('),
    ('_log.matchPx(', '_workedLog.matchPx('),
    ('_log.match(call,', '_workedLog.match(call,'),
    ('return _log.getData(call,gridsquare,name);', 'return _workedLog.getData(call,gridsquare,name);'),
]:
    if new not in t:
        count = t.count(old)
        if count < 1:
            raise SystemExit(f'[FAIL] R10 Worked/New routing anchor missing {old!r}')
        t = t.replace(old, new)

# Some upstream Worked/New lines carry trailing spaces. Once those lines are
# modified, git diff --check treats the inherited whitespace as a new error.
t = '\n'.join(line.rstrip() if '_workedLog.match' in line else line for line in t.split('\n'))

old_add = '''    _log.add(call,band,mode,date,gridsquare,name);'''
new_add = '''    _log.add(call,band,mode,date,gridsquare,name);\n    _workedLog.add(call,band,mode,date,gridsquare,name);'''
if new_add not in t:
    if t.count(old_add) != 1:
        raise SystemExit(f'[FAIL] R10 addAsWorked anchor count={t.count(old_add)}')
    t = t.replace(old_add, new_add, 1)

if 'return _log.getCount(mod);' not in t:
    raise SystemExit('[FAIL] R10 local QSO counter was not preserved')

# The upstream JTDX source carries three trailing spaces on these match lines.
# Replacing only _log -> _workedLog would make git diff --check reject R10.
for old, new in [
    ('_workedLog.matchCqz(items[3], band, mode);   ', '_workedLog.matchCqz(items[3], band, mode);'),
    ('_workedLog.matchItuz(items[4], band, mode);   ', '_workedLog.matchItuz(items[4], band, mode);'),
    ('_workedLog.matchCountry(country, band, mode);   ', '_workedLog.matchCountry(country, band, mode);'),
]:
    t = t.replace(old, new)

save(p, t)
