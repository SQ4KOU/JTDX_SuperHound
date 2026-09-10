from pathlib import Path
import sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('.')
pp=root/'patch_superhound.py'
bp=root/'BUILD_JTDX_SUPERHOUND_MSI.ps1'
s=pp.read_text(encoding='utf-8')
old='''    busy_rx2_ = false;\n\n    // A lost TCI host must never leave JTDX logically in TX.\n'''
new='''    busy_rx2_ = false;\n\n    // Cancel any half-finished VFO/split transaction. These timers and\n    // band_change belong to the original JTDX TCI sequencing state machine;\n    // carrying them across a WebSocket reconnect can make the next band QSY\n    // look like the tail of the previous one.\n    band_change = false;\n    if (tci_timer1_ && tci_timer1_->isActive()) tci_timer1_->stop();\n    if (tci_timer2_ && tci_timer2_->isActive()) tci_timer2_->stop();\n    if (tci_timer3_ && tci_timer3_->isActive()) tci_timer3_->stop();\n\n    // A lost TCI host must never leave JTDX logically in TX.\n'''
if s.count(old)!=1: raise SystemExit(f'disconnect anchor count={s.count(old)}')
s=s.replace(old,new,1)
old2='''    // Re-apply JTDX's requested rig state after a TCI server restart.  The\n    // requested_* values survive the drop, while *_ state is refreshed by\n    // the host snapshot received just after WebSocket connect.\n    if (!requested_mode_.isEmpty() && requested_mode_ != mode_)\n      sendTextMessage(mode_to_command(requested_mode_));\n\n    if (!requested_rx_frequency_.isEmpty() && requested_rx_frequency_ != rx_frequency_) {\n      const QString cmd = CmdVFO + SmDP + rx_ + SmCM + "0" + SmCM + requested_rx_frequency_ + SmTZ;\n      sendTextMessage(cmd);\n    }\n\n    if (requested_split_ != split_) {\n      const QString cmd = CmdSplitEnable + SmDP + rx_ + SmCM + (requested_split_ ? SmTrue : SmFalse) + SmTZ;\n      sendTextMessage(cmd);\n    }\n    if (requested_split_ && !requested_other_frequency_.isEmpty() && requested_other_frequency_ != other_frequency_) {\n      const QString cmd = CmdVFO + SmDP + rx_ + SmCM + "1" + SmCM + requested_other_frequency_ + SmTZ;\n      sendTextMessage(cmd);\n    }\n'''
new2='''    // Re-apply JTDX's requested rig state after a TCI server restart through\n    // the native JTDX TCI state machine. Raw vfo/split writes here bypass\n    // busy_rx_frequency_, band_change and timer1/timer2 sequencing and can\n    // corrupt the next band selection after a reconnect.\n    const QString restore_rx = requested_rx_frequency_;\n    const QString restore_tx = requested_other_frequency_;\n    const bool restore_split = requested_split_;\n    MODE restore_mode = get_mode(true);\n\n    band_change = false;\n    if (!restore_rx.isEmpty())\n      do_frequency(string_to_frequency(restore_rx), restore_mode, false);\n    else if (!requested_mode_.isEmpty() && requested_mode_ != mode_)\n      do_mode(restore_mode);\n\n    if (restore_split && !restore_tx.isEmpty())\n      do_tx_frequency(string_to_frequency(restore_tx), restore_mode, false);\n    else if (restore_split != split_)\n      rig_split();\n'''
if s.count(old2)!=1: raise SystemExit(f'reconnect replay anchor count={s.count(old2)}')
s=s.replace(old2,new2,1)
oldcheck="'requested_rx_frequency_ != rx_frequency_', 'requested_split_ != split_',"
newcheck="'Cancel any half-finished VFO/split transaction.', 'do_frequency(string_to_frequency(restore_rx), restore_mode, false)', 'do_tx_frequency(string_to_frequency(restore_tx), restore_mode, false)',"
if oldcheck not in s: raise SystemExit('postcheck anchor missing')
s=s.replace(oldcheck,newcheck,1)
pp.write_text(s,encoding='utf-8')
b=bp.read_text(encoding='utf-8')
b=b.replace("MSI_VERSION='2.2.173'", "MSI_VERSION='2.2.174'", 1)
b=b.replace("MSI_NAME='JTDX-SuperHound-2.2.159-FINAL-win64'", "MSI_NAME='JTDX-SuperHound-2.2.159-FINAL-TCI-BANDFIX-win64'", 1)
b=b.replace("grep -Fq 'requested_rx_frequency_ != rx_frequency_' jtdx/TCITransceiver.cpp\ngrep -Fq 'requested_split_ != split_' jtdx/TCITransceiver.cpp", "grep -Fq 'Cancel any half-finished VFO/split transaction.' jtdx/TCITransceiver.cpp\ngrep -Fq 'do_frequency(string_to_frequency(restore_rx), restore_mode, false)' jtdx/TCITransceiver.cpp\ngrep -Fq 'do_tx_frequency(string_to_frequency(restore_tx), restore_mode, false)' jtdx/TCITransceiver.cpp",1)
bp.write_text(b,encoding='utf-8')
for needle in ['band_change = false;','do_frequency(string_to_frequency(restore_rx), restore_mode, false)','do_tx_frequency(string_to_frequency(restore_tx), restore_mode, false)']:
    if needle not in pp.read_text(encoding='utf-8'): raise SystemExit('missing '+needle)
if "MSI_VERSION='2.2.174'" not in bp.read_text(encoding='utf-8'): raise SystemExit('version bump failed')
print('[PASS] TCI BANDFIX overlay applied')
