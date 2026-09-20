# --- MainWindow: live database + WAL watcher ---------------------------------
p, t = load('mainwindow.h')
slot_anchor = '  void logChanged();\n'
slot_new = '  void logChanged();\n  void log4omChanged(QString const& path);\n'
if 'void log4omChanged(QString const& path);' not in t:
    if t.count(slot_anchor) != 1:
        raise SystemExit(f'[FAIL] R10 MainWindow slot anchor count={t.count(slot_anchor)}')
    t = t.replace(slot_anchor, slot_new, 1)
helper_anchor = '  void readSettings();\n'
helper_new = '  void readSettings();\n  void updateLog4OMWatcher();\n'
if 'void updateLog4OMWatcher();' not in t:
    if t.count(helper_anchor) != 1:
        raise SystemExit(f'[FAIL] R10 MainWindow helper anchor count={t.count(helper_anchor)}')
    t = t.replace(helper_anchor, helper_new, 1)
watch_anchor = '  QFileSystemWatcher *fsWatcher;\n'
watch_new = '  QFileSystemWatcher *fsWatcher;\n  QFileSystemWatcher *log4omWatcher;\n'
if 'QFileSystemWatcher *log4omWatcher;' not in t:
    if t.count(watch_anchor) != 1:
        raise SystemExit(f'[FAIL] R10 MainWindow watcher member anchor count={t.count(watch_anchor)}')
    t = t.replace(watch_anchor, watch_new, 1)
save(p, t)

p, t = load('mainwindow.cpp')
watch_setup = '''  fsWatcher = new QFileSystemWatcher(this);\n  fsWatcher->addPath(m_dataDir.absoluteFilePath ("wsjtx_log.adi"));\n  connect(fsWatcher, SIGNAL(fileChanged(QString)), this, SLOT(logChanged()));\n'''
watch_new = watch_setup + '''\n  log4omWatcher = new QFileSystemWatcher(this);\n  connect(log4omWatcher, &QFileSystemWatcher::fileChanged, this, &MainWindow::log4omChanged);\n  connect(log4omWatcher, &QFileSystemWatcher::directoryChanged, this, &MainWindow::log4omChanged);\n  updateLog4OMWatcher();\n'''
if 'log4omWatcher = new QFileSystemWatcher(this);' not in t:
    if t.count(watch_setup) != 1:
        raise SystemExit(f'[FAIL] R10 Log4OM watcher setup anchor count={t.count(watch_setup)}')
    t = t.replace(watch_setup, watch_new, 1)

old_call = 'm_logBook.init(m_config.callNotif() ? m_config.my_callsign() : "",m_config.gridNotif() ? m_config.my_grid() : "",m_config.timeFrom());'
new_call = 'm_logBook.init(m_config.callNotif() ? m_config.my_callsign() : "",m_config.gridNotif() ? m_config.my_grid() : "",m_config.timeFrom(),m_config.log4om_enabled(),m_config.log4om_database());'
if new_call not in t:
    count = t.count(old_call)
    if count != 2:
        raise SystemExit(f'[FAIL] R10 m_logBook.init expected 2 anchors, found {count}')
    t = t.replace(old_call, new_call)

settings_anchor = '  bool spot_to_dxsummit = m_config.spot_to_dxsummit();\n\n'
settings_new = '''  bool spot_to_dxsummit = m_config.spot_to_dxsummit();\n  bool old_log4om_enabled = m_config.log4om_enabled();\n  QString old_log4om_database = m_config.log4om_database();\n\n'''
if 'old_log4om_enabled' not in t:
    if t.count(settings_anchor) != 1:
        raise SystemExit(f'[FAIL] R10 settings old Log4OM anchor count={t.count(settings_anchor)}')
    t = t.replace(settings_anchor, settings_new, 1)

post_settings_anchor = '      enable_DXCC_entity ();  // sets text window proportions and (re)inits the logbook\n\n'
post_settings_new = '''      enable_DXCC_entity ();  // sets text window proportions and (re)inits the logbook\n      if (old_log4om_enabled != m_config.log4om_enabled() ||\n          old_log4om_database != m_config.log4om_database()) {\n        m_logBook.init(m_config.callNotif() ? m_config.my_callsign() : "",\n                       m_config.gridNotif() ? m_config.my_grid() : "",\n                       m_config.timeFrom(), m_config.log4om_enabled(), m_config.log4om_database());\n        updateLog4OMWatcher();\n      }\n\n'''
if 'old_log4om_database != m_config.log4om_database()' not in t:
    if t.count(post_settings_anchor) != 1:
        raise SystemExit(f'[FAIL] R10 settings reload anchor count={t.count(post_settings_anchor)}')
    t = t.replace(post_settings_anchor, post_settings_new, 1)

insert_anchor = '\nvoid MainWindow::logChanged()\n{\n'
if 'void MainWindow::updateLog4OMWatcher()' not in t:
    if t.count(insert_anchor) != 1:
        raise SystemExit(f'[FAIL] R10 live watcher method insertion anchor count={t.count(insert_anchor)}')
    methods = '''\nvoid MainWindow::updateLog4OMWatcher()\n{\n  if (!log4omWatcher) return;\n  const QStringList files = log4omWatcher->files();\n  if (!files.isEmpty()) log4omWatcher->removePaths(files);\n  const QStringList dirs = log4omWatcher->directories();\n  if (!dirs.isEmpty()) log4omWatcher->removePaths(dirs);\n\n  if (!m_config.log4om_enabled()) return;\n  const QString dbPath = QDir::fromNativeSeparators(m_config.log4om_database().trimmed());\n  if (dbPath.isEmpty()) return;\n  QFileInfo dbInfo(dbPath);\n  if (dbInfo.absoluteDir().exists()) log4omWatcher->addPath(dbInfo.absolutePath());\n  if (dbInfo.exists()) log4omWatcher->addPath(dbInfo.absoluteFilePath());\n  QFileInfo walInfo(dbInfo.absoluteFilePath() + "-wal");\n  if (walInfo.exists()) log4omWatcher->addPath(walInfo.absoluteFilePath());\n}\n\nvoid MainWindow::log4omChanged(QString const& path)\n{\n  Q_UNUSED(path);\n  if (!m_config.log4om_enabled()) return;\n  m_logBook.init(m_config.callNotif() ? m_config.my_callsign() : "",\n                 m_config.gridNotif() ? m_config.my_grid() : "",\n                 m_config.timeFrom(), true, m_config.log4om_database());\n  updateLog4OMWatcher();\n  if (m_config.write_decoded_debug()) writeToALLTXT("Log4OM Worked/New history reloaded");\n}\n'''
    t = t.replace(insert_anchor, methods + insert_anchor, 1)
save(p, t)
