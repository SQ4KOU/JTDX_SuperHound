from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
pp = root / 'patch_superhound.py'
bp = root / 'BUILD_JTDX_SUPERHOUND_MSI.ps1'

s = pp.read_text(encoding='utf-8')
marker = '# SQ4KOU TCI band-switch stability and crash hardening.'
if marker not in s:
    block = r"""

# SQ4KOU TCI band-switch stability and crash hardening.
# Keep the existing TCI protocol behaviour, but remove three failure modes:
# 1) Qt SocketError may be -1 (UnknownSocketError), so errortable.at(err) can abort.
# 2) TCI frames are external input; unchecked args.at()/decimal splits can abort on a short frame.
# 3) The original HPSDR band-change path waits for a VFO1 echo before completing VFO0 and
#    silently drops a new frequency request while busy. Thetis does not need that coupling.
p, t = load('TCITransceiver.cpp')

old = '    error_ = tr ("TCI websocket error: %1").arg (errortable.at (err));\n'
new = '''    int const err_index = static_cast<int>(err);\n    QString const err_text = (err_index >= 0 && err_index < errortable.size())\n                           ? errortable.at(err_index)\n                           : tr("UnknownSocket");\n    error_ = tr ("TCI websocket error: %1").arg (err_text);\n'''
if new not in t:
    if t.count(old) != 1:
        raise SystemExit(f'[FAIL] TCI safe SocketError anchor count={t.count(old)}')
    t = t.replace(old, new, 1)
    print('[OK] TCI SocketError bounds hardening')

start = t.find('void TCITransceiver::onMessageReceived(const QString &str)')
end = t.find('\nvoid TCITransceiver::sendTextMessage', start)
if start < 0 or end < 0:
    raise SystemExit('[FAIL] TCI onMessageReceived boundaries missing')
mb = t[start:end]
old_head = '''void TCITransceiver::onMessageReceived(const QString &str)\n{\n//qDebug() << "From WEB" << str;\n    QStringList cmd_list = str.split(";", SkipEmptyParts);\n'''
new_head = '''void TCITransceiver::onMessageReceived(const QString &str)\n{\n//qDebug() << "From WEB" << str;\n    // WebSocket callbacks may still be queued while the TCI object is stopping.\n    if (stopping_ || !tci_timer1_ || !tci_timer2_ || !tci_timer3_) return;\n    QStringList cmd_list = str.split(";", SkipEmptyParts);\n'''
if new_head not in mb:
    if mb.count(old_head) != 1:
        raise SystemExit(f'[FAIL] TCI parser entry anchor count={mb.count(old_head)}')
    mb = mb.replace(old_head, new_head, 1)

old_parse = '''    for (QString cmds : cmd_list){\n        QStringList cmd = cmds.split(":", SkipEmptyParts);\n        QStringList args = cmd.last().split(",", SkipEmptyParts);\n        Tci_Cmd idCmd = mapCmd_[cmd.first()];\n'''
new_parse = '''    for (QString cmds : cmd_list){\n        QStringList cmd = cmds.split(":", SkipEmptyParts);\n        if (cmd.isEmpty()) continue;\n        QStringList args;\n        if (cmd.size() > 1) args = cmd.last().split(",", SkipEmptyParts);\n        Tci_Cmd idCmd = mapCmd_[cmd.first()];\n        auto arg = [&args](int index) -> QString {\n          return (index >= 0 && index < args.size()) ? args.at(index) : QString();\n        };\n'''
if new_parse not in mb:
    if mb.count(old_parse) != 1:
        raise SystemExit(f'[FAIL] TCI parser command anchor count={mb.count(old_parse)}')
    mb = mb.replace(old_parse, new_parse, 1)

# Make every TCI argument read in this callback bounds-safe. Missing fields become empty
# and therefore fail the existing comparisons instead of terminating the process.
mb = mb.replace('args.at(', 'arg(')

num_repls = {
'''            power_ = 10 * arg(3).split(".")[0].toInt() + arg(3).split(".")[1].toInt();\n            swr_ = 10 * arg(4).split(".")[0].toInt() + arg(4).split(".")[1].toInt();\n''':
'''            power_ = qRound(arg(3).toDouble() * 10.0);\n            swr_ = qRound(arg(4).toDouble() * 10.0);\n''',
'''          swr_ = 10 * arg(0).split(".")[0].toInt() + arg(0).split(".")[1].toInt();\n''':
'''          swr_ = qRound(arg(0).toDouble() * 10.0);\n''',
'''          power_ = 10 * arg(0).split(".")[0].toInt() + arg(0).split(".")[1].toInt();\n''':
'''          power_ = qRound(arg(0).toDouble() * 10.0);\n''',
}
for oldn, newn in num_repls.items():
    if newn not in mb:
        if mb.count(oldn) != 1:
            raise SystemExit('[FAIL] TCI numeric parser anchor missing')
        mb = mb.replace(oldn, newn, 1)

# HPSDR/Thetis: complete RX VFO command from its own VFO0 acknowledgement. Do not wait
# for an unrelated VFO1 echo; TX VFO is handled independently by do_tx_frequency().
old_band = '      band_change = abs(rx_frequency_.toInt()-requested_rx_frequency_.toInt()) > 1000000;\n'
new_band = '      band_change = !HPSDR && abs(rx_frequency_.toInt()-requested_rx_frequency_.toInt()) > 1000000;\n'

t = t[:start] + mb + t[end:]
if new_band not in t:
    if t.count(old_band) != 1:
        raise SystemExit(f'[FAIL] HPSDR band_change anchor count={t.count(old_band)}')
    t = t.replace(old_band, new_band, 1)

# Never dereference a stale/null WebSocket during reconnect/teardown.
old_send = '''void TCITransceiver::sendTextMessage(const QString &message)\n{\n    if (inConnected) commander_->sendTextMessage(message);\n}\n'''
new_send = '''void TCITransceiver::sendTextMessage(const QString &message)\n{\n    if (commander_ && inConnected && commander_->state() == QAbstractSocket::ConnectedState)\n      commander_->sendTextMessage(message);\n}\n'''
if new_send not in t:
    if t.count(old_send) != 1:
        raise SystemExit(f'[FAIL] TCI safe send anchor count={t.count(old_send)}')
    t = t.replace(old_send, new_send, 1)

# Preserve the newest requested RX frequency even if a nested Qt event loop re-enters
# do_frequency while an earlier request is awaiting acknowledgement.
old_busy_rx = '''  if (busy_rx_frequency_) return;\n  else {\n    requested_rx_frequency_ = f_string;\n    requested_mode_ = map_mode (m);\n  }\n'''
new_busy_rx = '''  requested_rx_frequency_ = f_string;\n  requested_mode_ = map_mode (m);\n  if (busy_rx_frequency_) return;\n'''
if new_busy_rx not in t:
    if t.count(old_busy_rx) != 1:
        raise SystemExit(f'[FAIL] TCI RX coalesce anchor count={t.count(old_busy_rx)}')
    t = t.replace(old_busy_rx, new_busy_rx, 1)

old_rx_result = '''      if (requested_rx_frequency_ == rx_frequency_) update_rx_frequency (f);\n      else {\n//        printf ("%s(%0.1f) TCI failed set rxfreq:%s->%s\\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset(),rx_frequency_.toStdString().c_str(),requested_rx_frequency_.toStdString().c_str());\n#if JTDX_DEBUG_TO_FILE\n        FILE * pFile = fopen (debug_file_.c_str(),"a");\n        fprintf (pFile,"%s(%0.1f) TCI failed set rxfreq:%s->%s\\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset(),rx_frequency_.toStdString().c_str(),requested_rx_frequency_.toStdString().c_str());\n        fclose (pFile);\n#endif\n        error_ = tr ("TCI failed set rxfreq");\n//        tci_Ready = false;\n//        throw error {tr ("TCI failed set rxfreq")};\n      }\n      busy_rx_frequency_ = false;\n'''
new_rx_result = '''      bool const rx_superseded = requested_rx_frequency_ != f_string;\n      if (f_string == rx_frequency_) update_rx_frequency (f);\n      else if (!rx_superseded) {\n#if JTDX_DEBUG_TO_FILE\n        FILE * pFile = fopen (debug_file_.c_str(),"a");\n        fprintf (pFile,"%s(%0.1f) TCI failed set rxfreq:%s->%s\\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset(),rx_frequency_.toStdString().c_str(),f_string.toStdString().c_str());\n        fclose (pFile);\n#endif\n        error_ = tr ("TCI failed set rxfreq");\n      }\n      busy_rx_frequency_ = false;\n      if (rx_superseded) {\n        QTimer::singleShot(0, this, [this]() {\n          if (!stopping_ && tci_Ready && _power_ && !busy_rx_frequency_ && !requested_rx_frequency_.isEmpty())\n            do_frequency(string_to_frequency(requested_rx_frequency_), get_mode(true), false);\n        });\n      }\n'''
if new_rx_result not in t:
    if t.count(old_rx_result) != 1:
        raise SystemExit(f'[FAIL] TCI RX completion anchor count={t.count(old_rx_result)}')
    t = t.replace(old_rx_result, new_rx_result, 1)

# Same coalescing rule for TX VFO/split requests.
old_busy_tx = '''  if (busy_other_frequency_) return;\n  requested_other_frequency_ = f_string;\n  requested_mode_ = map_mode (mode);\n  if (tx)\n    {\n      requested_split_ = true;\n'''
new_busy_tx = '''  requested_mode_ = map_mode (mode);\n  requested_split_ = tx != 0;\n  requested_other_frequency_ = tx ? f_string : QString();\n  if (busy_other_frequency_) return;\n  if (tx)\n    {\n'''
if new_busy_tx not in t:
    if t.count(old_busy_tx) != 1:
        raise SystemExit(f'[FAIL] TCI TX coalesce anchor count={t.count(old_busy_tx)}')
    t = t.replace(old_busy_tx, new_busy_tx, 1)

t = t.replace('''  else {\n    requested_split_ = false;\n    requested_other_frequency_ = "";\n''', '''  else {\n''', 1)

old_tx_result = '''          if (requested_other_frequency_ == other_frequency_) update_other_frequency (tx);\n          else {\n//            printf ("%s(%0.1f) TCI failed set txfreq:%s->%s\\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset(),other_frequency_.toStdString().c_str(),requested_other_frequency_.toStdString().c_str());\n#if JTDX_DEBUG_TO_FILE\n            FILE * pFile = fopen (debug_file_.c_str(),"a");\n            fprintf (pFile,"%s(%0.1f) TCI failed set txfreq:%s->%s\\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset(),other_frequency_.toStdString().c_str(),requested_other_frequency_.toStdString().c_str());\n            fclose (pFile);\n#endif\n            error_ = tr ("TCI failed set txfreq");\n//            tci_Ready = false;\n//            throw error {tr ("TCI failed set txfreq")};\n          }\n          busy_other_frequency_ = false;\n'''
new_tx_result = '''          bool const tx_superseded = !requested_split_ || requested_other_frequency_ != f_string;\n          if (f_string == other_frequency_) update_other_frequency (tx);\n          else if (!tx_superseded) {\n#if JTDX_DEBUG_TO_FILE\n            FILE * pFile = fopen (debug_file_.c_str(),"a");\n            fprintf (pFile,"%s(%0.1f) TCI failed set txfreq:%s->%s\\n",m_jtdxtime->currentDateTimeUtc2().toString("hh:mm:ss.zzz").toStdString().c_str(),m_jtdxtime->GetOffset(),other_frequency_.toStdString().c_str(),f_string.toStdString().c_str());\n            fclose (pFile);\n#endif\n            error_ = tr ("TCI failed set txfreq");\n          }\n          busy_other_frequency_ = false;\n          if (tx_superseded) {\n            QTimer::singleShot(0, this, [this]() {\n              if (stopping_ || !tci_Ready || !_power_ || busy_other_frequency_) return;\n              Frequency const pending_tx = (requested_split_ && !requested_other_frequency_.isEmpty())\n                                         ? string_to_frequency(requested_other_frequency_) : 0;\n              do_tx_frequency(pending_tx, get_mode(true), false);\n            });\n          }\n'''
if new_tx_result not in t:
    if t.count(old_tx_result) != 1:
        raise SystemExit(f'[FAIL] TCI TX completion anchor count={t.count(old_tx_result)}')
    t = t.replace(old_tx_result, new_tx_result, 1)

save(p, t)
for needle in [
    'err_index >= 0 && err_index < errortable.size()',
    'auto arg = [&args](int index) -> QString',
    'qRound(arg(3).toDouble() * 10.0)',
    'band_change = !HPSDR &&',
    'commander_ && inConnected && commander_->state() == QAbstractSocket::ConnectedState',
    'bool const rx_superseded',
    'bool const tx_superseded',
]:
    if needle not in t:
        raise SystemExit(f'[FAIL] TCI stability postcheck missing {needle!r}')
print('[PASS] TCI band-switch stability/crash hardening source postcheck')
"""
    s += block
    pp.write_text(s, encoding='utf-8')

b = bp.read_text(encoding='utf-8')
if "MSI_VERSION='2.2.176'" not in b:
    if "MSI_VERSION='2.2.175'" not in b:
        raise SystemExit('[FAIL] builder MSI version 2.2.175 anchor missing')
    b = b.replace("MSI_VERSION='2.2.175'", "MSI_VERSION='2.2.176'", 1)
if "MSI_NAME='JTDX-SuperHound-2.2.159-FINAL-TCI-BANDSAFE-win64'" not in b:
    oldname = "MSI_NAME='JTDX-SuperHound-2.2.159-FINAL-TCI-BANDFIX-JT9FIX-win64'"
    if oldname not in b:
        raise SystemExit('[FAIL] builder JT9FIX name anchor missing')
    b = b.replace(oldname, "MSI_NAME='JTDX-SuperHound-2.2.159-FINAL-TCI-BANDSAFE-win64'", 1)

gate_anchor = "grep -Fq 'Fail safe: a reconnect can never arm TX.' jtdx/TCITransceiver.cpp\n"
gates = gate_anchor + """grep -Fq 'err_index >= 0 && err_index < errortable.size()' jtdx/TCITransceiver.cpp\ngrep -Fq 'auto arg = [&args](int index) -> QString' jtdx/TCITransceiver.cpp\ngrep -Fq 'qRound(arg(3).toDouble() * 10.0)' jtdx/TCITransceiver.cpp\ngrep -Fq 'band_change = !HPSDR &&' jtdx/TCITransceiver.cpp\ngrep -Fq 'commander_ && inConnected && commander_->state() == QAbstractSocket::ConnectedState' jtdx/TCITransceiver.cpp\ngrep -Fq 'bool const rx_superseded' jtdx/TCITransceiver.cpp\ngrep -Fq 'bool const tx_superseded' jtdx/TCITransceiver.cpp\n"""
if "grep -Fq 'bool const rx_superseded'" not in b:
    if b.count(gate_anchor) != 1:
        raise SystemExit(f'[FAIL] builder TCI gate anchor count={b.count(gate_anchor)}')
    b = b.replace(gate_anchor, gates, 1)

bp.write_text(b, encoding='utf-8')
print('[PASS] TCI BANDSAFE overlay applied')
