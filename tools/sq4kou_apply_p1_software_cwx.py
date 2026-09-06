from pathlib import Path
import re

CONSOLE = Path(r"Project Files/Source/Console/console.cs")
CWX = Path(r"Project Files/Source/Console/cwx.cs")


def read_norm(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def write_utf8_bom(path: Path, text: str) -> None:
    # GitHub Windows build uses CRLF sources; utf-8-sig preserves the existing BOM style.
    path.write_text(text.replace("\n", "\r\n"), encoding="utf-8-sig", newline="")


# -----------------------------------------------------------------------------
# console.cs: P1-only CWX software-IQ bridge.
# -----------------------------------------------------------------------------
s = read_norm(CONSOLE)
if "SQ4KOUStartP1SoftwareCWX" in s:
    raise SystemExit("console.cs already contains SQ4KOU P1 software CWX path")

anchor = "        private bool _startdiversity = false;\n"
if s.count(anchor) != 1:
    raise SystemExit(f"console.cs anchor count={s.count(anchor)}")

block = r'''        // SQ4KOU P1 CWX SOFTWARE-IQ BRIDGE
        // Red Pitaya Protocol 1 does not turn the native Hermes firmware-keyer
        // DOT/DASH/CWX encoding into RF.  CWX therefore uses the existing WDSP
        // TX post generator and sends ordinary TX IQ while CWX is active.
        // Scope is deliberately limited to CWX + Protocol 1.
        private bool _sq4kou_p1_software_cwx_active = false;
        private bool _sq4kou_p1_software_cwx_prev_fw_keyer = true;

        public bool SQ4KOUP1SoftwareCWXActive
        {
            get { return _sq4kou_p1_software_cwx_active; }
        }

        public bool SQ4KOUStartP1SoftwareCWX()
        {
            if (NetworkIO.CurrentRadioProtocol != RadioProtocol.USB) return false;

            DSPMode tx_mode = VFOBTX && RX2Enabled ? RX2DSPMode : RX1DSPMode;
            if (tx_mode != DSPMode.CWL && tx_mode != DSPMode.CWU) return false;
            if (_sq4kou_p1_software_cwx_active) return true;

            _sq4kou_p1_software_cwx_prev_fw_keyer = CWFWKeyer;

            // Must be false BEFORE MOX.  Protocol 1 then carries normal IQ instead
            // of replacing TX I/Q words with the 3-bit DOT/DASH/CWX value.
            if (CWFWKeyer)
                CWFWKeyer = false;

            radio.GetDSPTX(0).TXPostGenRun = 0;
            radio.GetDSPTX(0).TXPostGenMode = 0; // single tone
            radio.GetDSPTX(0).TXPostGenToneFreq = tx_mode == DSPMode.CWL ? -cw_pitch : +cw_pitch;
            radio.GetDSPTX(0).TXPostGenToneMag = MAX_TONE_MAG;

            _sq4kou_p1_software_cwx_active = true;
            return true;
        }

        public void SQ4KOUArmP1SoftwareCWXTX()
        {
            if (!_sq4kou_p1_software_cwx_active) return;

            // Normal MOX intentionally leaves the WDSP TX channel off in CW mode
            // because the native firmware keyer normally produces RF.  Software
            // CWX needs the TX channel running so TXPostGen reaches Protocol 1 IQ.
            WDSP.SetChannelState(WDSP.id(1, 0), 1, 0);
        }

        public void SQ4KOUSetP1SoftwareCWXKey(bool key_down)
        {
            if (!_sq4kou_p1_software_cwx_active) return;
            radio.GetDSPTX(0).TXPostGenRun = key_down ? 1 : 0;
        }

        public void SQ4KOUStopP1SoftwareCWX()
        {
            if (!_sq4kou_p1_software_cwx_active) return;

            radio.GetDSPTX(0).TXPostGenRun = 0;
            _sq4kou_p1_software_cwx_active = false;

            // Restore the exact pre-CWX keyer choice, not an assumed default.
            if (CWFWKeyer != _sq4kou_p1_software_cwx_prev_fw_keyer)
                CWFWKeyer = _sq4kou_p1_software_cwx_prev_fw_keyer;
        }

'''

s = s.replace(anchor, block + anchor, 1)
write_utf8_bom(CONSOLE, s)


# -----------------------------------------------------------------------------
# cwx.cs: route P1 CWX keying to the software-IQ bridge; keep P2 native path.
# -----------------------------------------------------------------------------
s = read_norm(CWX)
if "SQ4KOUSetP1SoftwareCWXKey" in s:
    raise SystemExit("cwx.cs already contains SQ4KOU P1 software CWX path")

latch_pattern = re.compile(
    r"        private void set_cwx_mox_latch\(bool state\)\n"
    r"        \{.*?\n"
    r"        \}\n\n"
    r"        private void setptt\(bool state\)",
    re.S,
)

new_latch = r'''        private void set_cwx_mox_latch(bool state)
        {
            RadioProtocol protocol = NetworkIO.CurrentRadioProtocol;
            bool p1 = protocol == RadioProtocol.USB;
            bool p2 = protocol == RadioProtocol.ETH;
            if (!p1 && !p2) return;
            if (cwx_mox_latched == state) return;

            if (state)
            {
                console.CurrentPTTMode = PTTMode.SPACE;

                // P1: disable firmware-keyer packing and configure normal IQ first.
                if (p1 && !console.SQ4KOUStartP1SoftwareCWX()) return;

                console.MOX = true;

                // In CW mode normal MOX does not start the WDSP TX channel.
                if (p1) console.SQ4KOUArmP1SoftwareCWXTX();
            }
            else
            {
                if (p1) console.SQ4KOUSetP1SoftwareCWXKey(false);

                // Keep software-CW mode active through the MOX->RX transition so
                // the native CW frequency/key-up handling sees the correct state.
                console.MOX = false;

                if (p1) console.SQ4KOUStopP1SoftwareCWX();
            }

            cwx_mox_latched = state;
        }

        private void setptt(bool state)'''

s, n = latch_pattern.subn(new_latch, s, count=1)
if n != 1:
    raise SystemExit(f"cwx.cs latch replacement count={n}")

old = """                if (state)\n                    set_cwx_mox_latch(true);\n\n                setptt_memory = state;"""
new = """                if (state)\n                    set_cwx_mox_latch(true);\n                else if (NetworkIO.CurrentRadioProtocol == RadioProtocol.USB)\n                    set_cwx_mox_latch(false);\n\n                setptt_memory = state;"""
if s.count(old) != 1:
    raise SystemExit(f"cwx.cs setptt anchor count={s.count(old)}")
s = s.replace(old, new, 1)

old = "                NetworkIO.SetCWX(Convert.ToInt32(state));"
new = """                if (NetworkIO.CurrentRadioProtocol == RadioProtocol.USB && console.SQ4KOUP1SoftwareCWXActive)\n                    console.SQ4KOUSetP1SoftwareCWXKey(state);\n                else\n                    NetworkIO.SetCWX(Convert.ToInt32(state));"""
if s.count(old) != 1:
    raise SystemExit(f"cwx.cs NetworkIO.SetCWX count={s.count(old)}")
s = s.replace(old, new, 1)

write_utf8_bom(CWX, s)

# Static assertions: fail closed if any intended part is missing.
cs = read_norm(CONSOLE)
cw = read_norm(CWX)
checks = [
    ("console start", "SQ4KOUStartP1SoftwareCWX" in cs),
    ("console arm", "SQ4KOUArmP1SoftwareCWXTX" in cs),
    ("console key", "TXPostGenRun = key_down ? 1 : 0;" in cs),
    ("console protocol gate", "CurrentRadioProtocol != RadioProtocol.USB" in cs),
    ("cwx p1 key route", "console.SQ4KOUSetP1SoftwareCWXKey(state);" in cw),
    ("cwx p1 mox route", "console.SQ4KOUStartP1SoftwareCWX()" in cw),
    ("p2 native preserved", "bool p2 = protocol == RadioProtocol.ETH;" in cw),
]
failed = [name for name, ok in checks if not ok]
if failed:
    raise SystemExit("static assertions failed: " + ", ".join(failed))

print("SQ4KOU P1 software CWX patch: PASS")
