from pathlib import Path

P = Path(r"Project Files/Source/Console/cwx.cs")


def read_norm(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def write_utf8_bom(path: Path, text: str) -> None:
    path.write_text(text.replace("\n", "\r\n"), encoding="utf-8-sig", newline="")


s = read_norm(P)

if "p1_cwx_ptt_hold_elements" in s:
    raise SystemExit("P1 CWX PTT hold patch already present")

anchor = "        private bool setptt_memory = false;\n"
if s.count(anchor) != 1:
    raise SystemExit(f"setptt anchor count={s.count(anchor)}")

helper = r'''        // SQ4KOU P1 CWX: keep MOX/PTT asserted across a standard 7-element
        // Morse word gap.  The user's CWX Drop Delay remains authoritative when
        // it is longer; 8 dot periods are only a Protocol-1 software-CWX minimum.
        private int p1_cwx_ptt_hold_elements()
        {
            int configured = tel > 0 ? Math.Max(0, ttdel / tel) : 0;
            if (NetworkIO.CurrentRadioProtocol == RadioProtocol.USB &&
                console.SQ4KOUP1SoftwareCWXActive)
                return Math.Max(configured, 8);

            return configured;
        }

'''
s = s.replace(anchor, helper + anchor, 1)

old = "                ttx = ttdel / tel;"
count = s.count(old)
if count != 3:
    raise SystemExit(f"ttx assignment count={count}, expected 3")
s = s.replace(old, "                ttx = p1_cwx_ptt_hold_elements();")

# Fail closed: P1 software IQ route and the immediate physical latch release must
# still exist; this patch only lengthens its countdown before setptt(false).
required = [
    "console.SQ4KOUStartP1SoftwareCWX()",
    "console.SQ4KOUSetP1SoftwareCWXKey(state)",
    "else if (NetworkIO.CurrentRadioProtocol == RadioProtocol.USB)\n                    set_cwx_mox_latch(false);",
    "set_cwx_mox_latch(false);\n            ttx = 0; pause = 0; newptt = 0;",
]
for marker in required:
    if marker not in s:
        raise SystemExit(f"required marker missing: {marker}")

write_utf8_bom(P, s)
print("PATCH_OK: P1 software-CWX PTT hold >= 8 dot periods; configured Drop Delay preserved when longer")
