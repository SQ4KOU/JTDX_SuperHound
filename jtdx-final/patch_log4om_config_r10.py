# --- Configuration: Advanced / Log4OM 2 --------------------------------------
p, t = load('Configuration.hpp')
old = '  QString my_grid () const;\n'
new = '  QString my_grid () const;\n  bool log4om_enabled () const;\n  QString log4om_database () const;\n'
if new not in t:
    if t.count(old) != 1:
        raise SystemExit(f'[FAIL] R10 Configuration.hpp getter anchor count={t.count(old)}')
    t = t.replace(old, new, 1)
save(p, t)

p, t = load('Configuration.cpp')
include_anchor = '#include <QLineEdit>\n'
include_block = '''#include <QLineEdit>\n#include <QFileInfo>\n#include <QGroupBox>\n#include <QCheckBox>\n#include <QPushButton>\n#include <QLabel>\n#include <QHBoxLayout>\n#include <QVBoxLayout>\n'''
if '#include <QGroupBox>' not in t:
    if t.count(include_anchor) != 1:
        raise SystemExit(f'[FAIL] R10 Configuration include anchor count={t.count(include_anchor)}')
    t = t.replace(include_anchor, include_block, 1)

slot_anchor = '  Q_SLOT void on_decoded_text_font_push_button_clicked ();\n'
slot_new = slot_anchor + '  Q_SLOT void browse_log4om_database ();\n'
if 'Q_SLOT void browse_log4om_database ();' not in t:
    if t.count(slot_anchor) != 1:
        raise SystemExit(f'[FAIL] R10 Log4OM browse slot anchor count={t.count(slot_anchor)}')
    t = t.replace(slot_anchor, slot_new, 1)

ui_anchor = '  QScopedPointer<Ui::configuration_dialog> ui_;\n\n  QSettings * settings_;\n'
ui_new = '''  QScopedPointer<Ui::configuration_dialog> ui_;\n  QGroupBox * log4om_group_ = nullptr;\n  QCheckBox * log4om_enable_check_ = nullptr;\n  QLineEdit * log4om_database_edit_ = nullptr;\n  QPushButton * log4om_browse_button_ = nullptr;\n\n  QSettings * settings_;\n'''
if 'QGroupBox * log4om_group_' not in t:
    if t.count(ui_anchor) != 1:
        raise SystemExit(f'[FAIL] R10 Log4OM UI member anchor count={t.count(ui_anchor)}')
    t = t.replace(ui_anchor, ui_new, 1)

pub_anchor = '  QString my_callsign_;\n  QString my_grid_;\n  QString timeFrom_;\n'
pub_new = '''  QString my_callsign_;\n  QString my_grid_;\n  bool log4om_enabled_ = false;\n  QString log4om_database_;\n  QString timeFrom_;\n'''
if 'bool log4om_enabled_' not in t:
    if t.count(pub_anchor) != 1:
        raise SystemExit(f'[FAIL] R10 Log4OM state anchor count={t.count(pub_anchor)}')
    t = t.replace(pub_anchor, pub_new, 1)

getter_anchor = 'QString Configuration::my_grid () const {return m_->my_grid_;}\n'
getter_new = getter_anchor + 'bool Configuration::log4om_enabled () const {return m_->log4om_enabled_;}\nQString Configuration::log4om_database () const {return m_->log4om_database_;}\n'
if 'Configuration::log4om_enabled () const' not in t:
    if t.count(getter_anchor) != 1:
        raise SystemExit(f'[FAIL] R10 getter implementation anchor count={t.count(getter_anchor)}')
    t = t.replace(getter_anchor, getter_new, 1)

setup_anchor = '  ui_->setupUi (this);\n\n  {\n'
setup_new = '''  ui_->setupUi (this);\n\n  // SQ4KOU R10: add Log4OM controls to the free right-hand column of Advanced.\n  // Do not replace label_11: it owns the original decpasses.png panel.\n  log4om_group_ = new QGroupBox(tr("Log4OM 2"), ui_->advanced_tab);\n  auto log4om_layout = new QVBoxLayout(log4om_group_);\n  log4om_enable_check_ = new QCheckBox(tr("Use Log4OM SQLite database for Worked/New"), log4om_group_);\n  auto log4om_path_layout = new QHBoxLayout;\n  log4om_database_edit_ = new QLineEdit(log4om_group_);\n  log4om_database_edit_->setPlaceholderText(tr("Path to Log4OM SQLite database"));\n  log4om_browse_button_ = new QPushButton(tr("..."), log4om_group_);\n  log4om_browse_button_->setMaximumWidth(36);\n  log4om_path_layout->addWidget(log4om_database_edit_, 1);\n  log4om_path_layout->addWidget(log4om_browse_button_);\n  auto log4om_hint = new QLabel(tr("Read-only source for Worked/New. If unavailable or invalid, JTDX automatically falls back to wsjtx_log.adi."), log4om_group_);\n  log4om_hint->setWordWrap(true);\n  log4om_layout->addWidget(log4om_enable_check_);\n  log4om_layout->addLayout(log4om_path_layout);\n  log4om_layout->addWidget(log4om_hint);\n  ui_->verticalLayout_9->insertWidget(0, log4om_group_);\n  connect(log4om_browse_button_, &QPushButton::clicked, this, &Configuration::impl::browse_log4om_database);\n\n  {\n'''
if 'Use Log4OM SQLite database for Worked/New' not in t:
    if t.count(setup_anchor) != 1:
        raise SystemExit(f'[FAIL] R10 dynamic Advanced UI anchor count={t.count(setup_anchor)}')
    t = t.replace(setup_anchor, setup_new, 1)

read_anchor = '  my_grid_ = settings_->value ("MyGrid", "").toString ();\n\n'
read_new = '''  my_grid_ = settings_->value ("MyGrid", "").toString ();\n  log4om_enabled_ = settings_->value ("Log4OMEnabled", false).toBool ();\n  log4om_database_ = settings_->value ("Log4OMDatabase", "").toString ();\n\n'''
if 'settings_->value ("Log4OMEnabled"' not in t:
    if t.count(read_anchor) != 1:
        raise SystemExit(f'[FAIL] R10 read_settings anchor count={t.count(read_anchor)}')
    t = t.replace(read_anchor, read_new, 1)

write_anchor = '  settings_->setValue ("MyGrid", my_grid_);\n'
write_new = '''  settings_->setValue ("MyGrid", my_grid_);\n  settings_->setValue ("Log4OMEnabled", log4om_enabled_);\n  settings_->setValue ("Log4OMDatabase", log4om_database_);\n'''
if 'settings_->setValue ("Log4OMEnabled"' not in t:
    if t.count(write_anchor) != 1:
        raise SystemExit(f'[FAIL] R10 write_settings anchor count={t.count(write_anchor)}')
    t = t.replace(write_anchor, write_new, 1)

model_anchor = '  ui_->grid_line_edit->setText (my_grid_);\n'
model_new = '''  ui_->grid_line_edit->setText (my_grid_);\n  log4om_enable_check_->setChecked(log4om_enabled_);\n  log4om_database_edit_->setText(log4om_database_);\n'''
if 'log4om_enable_check_->setChecked' not in t:
    if t.count(model_anchor) != 1:
        raise SystemExit(f'[FAIL] R10 initialize_models anchor count={t.count(model_anchor)}')
    t = t.replace(model_anchor, model_new, 1)

accept_anchor = '  my_grid_ = ui_->grid_line_edit->text ();\n'
accept_new = '''  my_grid_ = ui_->grid_line_edit->text ();\n  log4om_enabled_ = log4om_enable_check_->isChecked();\n  log4om_database_ = log4om_database_edit_->text().trimmed();\n'''
if 'log4om_enabled_ = log4om_enable_check_' not in t:
    if t.count(accept_anchor) != 1:
        raise SystemExit(f'[FAIL] R10 accept anchor count={t.count(accept_anchor)}')
    t = t.replace(accept_anchor, accept_new, 1)

browse_marker = 'void Configuration::impl::browse_log4om_database ()'
if browse_marker not in t:
    insert_anchor = '\nvoid Configuration::impl::on_eqsluser_edit_textEdited(const QString &user)\n'
    if t.count(insert_anchor) != 1:
        raise SystemExit(f'[FAIL] R10 browse method insertion anchor count={t.count(insert_anchor)}')
    browse_impl = '''\nvoid Configuration::impl::browse_log4om_database ()\n{\n  QString start = log4om_database_edit_->text().trimmed();\n  if (!start.isEmpty()) start = QFileInfo(start).absolutePath();\n  QString selected = QFileDialog::getOpenFileName(this, tr("Select Log4OM SQLite database"), start,\n      tr("SQLite database (*.sqlite *.sqlite3 *.db);;All files (*)"));\n  if (!selected.isEmpty()) log4om_database_edit_->setText(QDir::toNativeSeparators(selected));\n}\n'''
    t = t.replace(insert_anchor, browse_impl + insert_anchor, 1)

# R10 does not rewrite the existing Advanced illustration area; do not gate on
# a particular upstream/baseline label_11/decpasses implementation.
save(p, t)
