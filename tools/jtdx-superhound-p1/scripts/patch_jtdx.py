from pathlib import Path
import shutil
import sys


def replace_once(path: Path, needle: str, replacement: str) -> None:
    text = path.read_text(encoding="utf-8", errors="strict")
    count = text.count(needle)
    if count != 1:
        raise RuntimeError(f"Patch-point mismatch ({count}) for {needle!r} in {path}")
    path.write_text(text.replace(needle, replacement), encoding="utf-8", newline="")


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: patch_jtdx.py <jtdx-source> <overlay-root>")
        return 2

    src = Path(sys.argv[1]).resolve()
    overlay = Path(sys.argv[2]).resolve()
    if not (src / "CMakeLists.txt").exists():
        raise RuntimeError(f"JTDX source not found: {src}")

    lib = src / "lib"
    shutil.copy2(overlay / "lib" / "superhound_external.c", lib / "superhound_external.c")
    shutil.copy2(overlay / "lib" / "superhound_external.f90", lib / "superhound_external.f90")

    cmake = src / "CMakeLists.txt"
    replace_once(
        cmake,
        "  lib/ft8_decode.f90",
        "  lib/ft8_decode.f90\n"
        "  # SQ4KOU SuperHound: external SuperFox RX bridge\n"
        "  lib/superhound_external.f90",
    )
    replace_once(
        cmake,
        "  lib/igray.c",
        "  lib/igray.c\n"
        "  # SQ4KOU SuperHound: external helper bridge\n"
        "  lib/superhound_external.c",
    )

    # SuperFox RX is additive: native JTDX FT8/Hound decoding remains intact.
    decoder = lib / "decoder.f90"
    anchor = "     if(params%nmode.eq.8) call ft8apset(params%lmycallstd,params%lhiscallstd,numthreads)"
    replacement = anchor + "\n\n" + "\n".join([
        "! SQ4KOU SUPER HOUND RX - external SuperFox helper.",
        "! Full fresh FT8 Hound cycle only. Native JTDX FT8 remains unchanged.",
        "     if(params%lhound .and. .not.params%nagain .and. params%nzhsym.ge.49) then",
        "        call superhound_external(nutc,dd8)",
        "     endif",
        "! END SQ4KOU SUPER HOUND RX",
    ])
    replace_once(decoder, anchor, replacement)

    mainwindow = src / "mainwindow.cpp"

    # Required Qt classes for the integrated bottom monitor and runtime SuperHound switch.
    replace_once(
        mainwindow,
        "#include <QButtonGroup>\n",
        "#include <QButtonGroup>\n"
        "#include <QSplitter>\n"
        "#include <QAction>\n"
        "#include <QTimer>\n",
    )

    # Keep the existing WideGraph object and all its signal wiring, but embed it as a
    # child widget under the native JTDX main splitter. This avoids any decoder/UI rewrite.
    setup_anchor = "  ui->setupUi(this);\n"
    setup_patch = setup_anchor + r'''
  // SQ4KOU: integrated Monitor / WideGraph at the bottom of the main window.
  auto *sq4kouMainMonitorSplitter = new QSplitter(Qt::Vertical, ui->centralWidget);
  sq4kouMainMonitorSplitter->setObjectName("sq4kouMainMonitorSplitter");
  sq4kouMainMonitorSplitter->setChildrenCollapsible(false);
  ui->gridLayout_3->removeWidget(ui->splitter);
  ui->gridLayout_3->addWidget(sq4kouMainMonitorSplitter, 0, 0);
  sq4kouMainMonitorSplitter->addWidget(ui->splitter);

  m_wideGraph->setParent(sq4kouMainMonitorSplitter);
  m_wideGraph->setWindowFlags(Qt::Widget);
  m_wideGraph->setMinimumHeight(120);
  m_wideGraph->setMaximumSize(16777215, 16777215);
  m_wideGraph->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
  sq4kouMainMonitorSplitter->addWidget(m_wideGraph.data());
  sq4kouMainMonitorSplitter->setStretchFactor(0, 2);
  sq4kouMainMonitorSplitter->setStretchFactor(1, 1);

  QByteArray sq4kouMonitorState = m_settings->value("SQ4KOU/IntegratedMonitorSplitter").toByteArray();
  if (!sq4kouMonitorState.isEmpty()) {
    sq4kouMainMonitorSplitter->restoreState(sq4kouMonitorState);
  } else {
    QList<int> sq4kouDefaultMonitorSizes;
    sq4kouDefaultMonitorSizes << 650 << 300;
    sq4kouMainMonitorSplitter->setSizes(sq4kouDefaultMonitorSizes);
  }
  connect(sq4kouMainMonitorSplitter, &QSplitter::splitterMoved, this,
          [this, sq4kouMainMonitorSplitter](int, int) {
            m_settings->setValue("SQ4KOU/IntegratedMonitorSplitter", sq4kouMainMonitorSplitter->saveState());
          });

  // SQ4KOU: explicit SuperHound operating switch. Classic Hound stays available;
  // SuperHound adds SuperFox RX, fixes RX at 750 Hz and suppresses classic TX jumps.
  auto *sq4kouSuperHound = new QAction(tr("Enable SuperHound mode"), this);
  sq4kouSuperHound->setObjectName("actionSQ4KOU_SuperHound");
  sq4kouSuperHound->setCheckable(true);
  ui->menuDXpedition->insertAction(ui->actionUse_TX_frequency_jumps, sq4kouSuperHound);
  ui->menuDXpedition->insertSeparator(ui->actionUse_TX_frequency_jumps);

  connect(sq4kouSuperHound, &QAction::toggled, this, [this, sq4kouSuperHound](bool checked) {
    m_settings->setValue("SQ4KOU/SuperHoundEnabled", checked);
    if (checked) {
      sq4kouSuperHound->setProperty("previousRxFreq", ui->RxFreqSpinBox->value());
      if (!ui->actionEnable_hound_mode->isChecked()) ui->actionEnable_hound_mode->setChecked(true);
      m_houndTXfreqJumps = false;
      ui->actionUse_TX_frequency_jumps->setChecked(false);
      ui->actionUse_TX_frequency_jumps->setEnabled(false);
      ui->RxFreqSpinBox->setValue(750);
      m_wideGraph->setRxFreq(750);
      ui->HoundButton->setText(tr("SUPER HOUND"));
      ui->HoundButton->setToolTip(tr("SuperHound: SuperFox RX at 750 Hz, normal FT8 Hound TX"));
    } else {
      bool ok = false;
      int previousRx = sq4kouSuperHound->property("previousRxFreq").toInt(&ok);
      if (ok && previousRx >= 0 && previousRx <= 5000) ui->RxFreqSpinBox->setValue(previousRx);
      ui->HoundButton->setText(tr("Hound"));
      ui->HoundButton->setToolTip(QString());
      if (ui->actionEnable_hound_mode->isChecked()) {
        bool allowJumps = !m_commonFT8b && m_config.split_mode() && m_config.rig_name() != "None";
        m_houndTXfreqJumps = allowJumps;
        ui->actionUse_TX_frequency_jumps->setChecked(allowJumps);
        ui->actionUse_TX_frequency_jumps->setEnabled(allowJumps);
      }
    }
  });

  connect(ui->actionEnable_hound_mode, &QAction::toggled, this, [sq4kouSuperHound](bool checked) {
    if (!checked && sq4kouSuperHound->isChecked()) sq4kouSuperHound->setChecked(false);
  });

  QTimer::singleShot(0, this, [this, sq4kouSuperHound]() {
    if (m_settings->value("SQ4KOU/SuperHoundEnabled", false).toBool()) {
      sq4kouSuperHound->setChecked(true);
    }
  });
'''
    replace_once(mainwindow, setup_anchor, setup_patch)

    # The old menu action opened a second top-level window. It now shows/hides the
    # embedded bottom monitor instead.
    replace_once(
        mainwindow,
        "void MainWindow::on_actionWide_Waterfall_triggered() { m_wideGraph->show(); } //Display Waterfalls",
        "void MainWindow::on_actionWide_Waterfall_triggered()\n"
        "{\n"
        "  bool showMonitor = !m_wideGraph->isVisible();\n"
        "  m_wideGraph->setVisible(showMonitor);\n"
        "  ui->actionWide_Waterfall->setCheckable(true);\n"
        "  ui->actionWide_Waterfall->setChecked(showMonitor);\n"
        "}\n",
    )

    # SuperHound must never inherit classic Hound TX-frequency jumping even if
    # the normal Hound handler is called again after band/rig state changes.
    hound_anchor = "  m_wideGraph->setHoundFilter(m_houndMode);"
    hound_patch = hound_anchor + r'''
  QAction *sq4kouSuperHoundActive = findChild<QAction *>("actionSQ4KOU_SuperHound");
  if (sq4kouSuperHoundActive && sq4kouSuperHoundActive->isChecked()) {
    m_houndTXfreqJumps = false;
    ui->actionUse_TX_frequency_jumps->setChecked(false);
    ui->actionUse_TX_frequency_jumps->setEnabled(false);
    if (ui->RxFreqSpinBox->value() != 750) ui->RxFreqSpinBox->setValue(750);
  }
'''
    replace_once(mainwindow, hound_anchor, hound_patch)

    replace_once(
        mainwindow,
        "void MainWindow::on_actionUse_TX_frequency_jumps_triggered (bool checked) { m_houndTXfreqJumps=checked; }",
        "void MainWindow::on_actionUse_TX_frequency_jumps_triggered (bool checked)\n"
        "{\n"
        "  QAction *sq4kouSuperHoundActive = findChild<QAction *>(\"actionSQ4KOU_SuperHound\");\n"
        "  m_houndTXfreqJumps = checked && !(sq4kouSuperHoundActive && sq4kouSuperHoundActive->isChecked());\n"
        "}\n",
    )

    print("PATCH PASS")
    print("features=superfox-rx,superhound-ui,integrated-bottom-monitor")
    print(f"source={src}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
