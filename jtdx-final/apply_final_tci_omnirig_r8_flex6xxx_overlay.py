from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
here = Path(__file__).resolve().parent
r7 = here / 'apply_final_tci_omnirig_r7_overlay.py'
if not r7.exists():
    raise SystemExit('[FAIL] R7 overlay missing')

# R8 is deliberately narrow: keep the user-confirmed R7 TCI/OmniRig/SuperHound
# state intact and restore Hamlib to the exact source revision documented for
# the original JTDX 2.2.159 Windows release.
subprocess.run([sys.executable, str(r7), str(root)], check=True)

bp = root / 'BUILD_JTDX_SUPERHOUND_MSI.ps1'
if not bp.exists():
    raise SystemExit('[FAIL] FINAL-TCI builder missing after R7 overlay')

b = bp.read_text(encoding='utf-8')
old_hamlib = '1e70dd7b98fd715c829724313eb88884ca1cbfc1'
jtdx159_hamlib = 'c5a5276b15c251151c67e17c50b2fb712ec3809d'

if old_hamlib in b:
    b = b.replace(old_hamlib, jtdx159_hamlib)
if old_hamlib in b:
    raise SystemExit('[FAIL] obsolete post-release Hamlib commit still present')
if jtdx159_hamlib not in b:
    raise SystemExit('[FAIL] JTDX 2.2.159 release Hamlib commit missing')

# Add a real network-open regression gate for the FlexRadio 6xxx Hamlib backend.
# Model 2036 is RIG_MODEL_F6K. The mock CAT endpoint returns the same ID family
# accepted by SmartSDR CAT and answers the AI query performed by flexradio_open().
marker = '# SQ4KOU R8: FlexRadio 6xxx release-Hamlib network-open regression gate.'
if marker not in b:
    anchor = 'export PATH="$HAMLIB_PREFIX/bin:/mingw64/bin:/usr/bin:$PATH"\n'
    if b.count(anchor) != 1:
        raise SystemExit(f'[FAIL] R8 Hamlib smoke-test anchor count={b.count(anchor)}')
    block = r'''export PATH="$HAMLIB_PREFIX/bin:/mingw64/bin:/usr/bin:$PATH"

# SQ4KOU R8: FlexRadio 6xxx release-Hamlib network-open regression gate.
R8_FLEX_PORT=14532
R8_FLEX_MOCK="$WORK/flex6xxx_mock.py"
R8_FLEX_LOG="$WORK/flex6xxx_rigctl.log"
cat > "$R8_FLEX_MOCK" <<'PYFLEX'
import socket
import sys
port = int(sys.argv[1])
seen = []
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(1)
    srv.settimeout(20)
    conn, _ = srv.accept()
    with conn:
        conn.settimeout(10)
        buf = b""
        while True:
            try:
                data = conn.recv(4096)
            except socket.timeout:
                break
            if not data:
                break
            buf += data
            while b";" in buf:
                raw, buf = buf.split(b";", 1)
                cmd = raw.decode("ascii", errors="replace").strip()
                if not cmd:
                    continue
                seen.append(cmd)
                if cmd == "ID":
                    conn.sendall(b"ID909;")
                elif cmd == "AI":
                    conn.sendall(b"AI0;")
        print("FLEX6XXX_MOCK_COMMANDS=" + ",".join(seen), flush=True)
        if "ID" not in seen:
            raise SystemExit(21)
PYFLEX

test -x "$HAMLIB_PREFIX/bin/rigctl.exe" || {
  echo '[FAIL] R8 rigctl.exe missing from pinned Hamlib prefix'
  exit 81
}
"$HAMLIB_PREFIX/bin/rigctl.exe" -l | tr -d '\r' | grep -E 'FlexRadio[[:space:]]+6xxx' >/dev/null || {
  echo '[FAIL] R8 FlexRadio 6xxx model absent from Hamlib model list'
  exit 82
}
echo '[PASS] R8 FlexRadio 6xxx model present in Hamlib'

/usr/bin/python3 "$R8_FLEX_MOCK" "$R8_FLEX_PORT" > "$WORK/flex6xxx_mock.log" 2>&1 &
R8_FLEX_PID=$!
sleep 1
set +e
printf 'q\n' | "$HAMLIB_PREFIX/bin/rigctl.exe" -m 2036 -r "127.0.0.1:$R8_FLEX_PORT" -vvvv > "$R8_FLEX_LOG" 2>&1
R8_FLEX_RC=$?
set -e
wait "$R8_FLEX_PID" || R8_FLEX_MOCK_RC=$?
R8_FLEX_MOCK_RC=${R8_FLEX_MOCK_RC:-0}
cat "$R8_FLEX_LOG"
cat "$WORK/flex6xxx_mock.log"
if [ "$R8_FLEX_RC" -ne 0 ] || [ "$R8_FLEX_MOCK_RC" -ne 0 ]; then
  echo "[FAIL] R8 FlexRadio 6xxx network-open smoke test: rigctl=$R8_FLEX_RC mock=$R8_FLEX_MOCK_RC"
  exit 83
fi
grep -Fq 'FLEX6XXX_MOCK_COMMANDS=' "$WORK/flex6xxx_mock.log"
grep -Eq 'FLEX6XXX_MOCK_COMMANDS=.*ID' "$WORK/flex6xxx_mock.log" || {
  echo '[FAIL] R8 FlexRadio 6xxx mock did not receive ID query'
  exit 84
}
echo '[PASS] R8 FlexRadio 6xxx TCP open/ID/AI path'

'''
    b = b.replace(anchor, block, 1)

if "MSI_VERSION='2.2.205'" not in b:
    if b.count("MSI_VERSION='2.2.204'") != 1:
        raise SystemExit('[FAIL] R8 MSI version 2.2.204 anchor missing')
    b = b.replace("MSI_VERSION='2.2.204'", "MSI_VERSION='2.2.205'", 1)

old_name = "MSI_NAME='JTDX-SuperHound-2.2.159-FINAL-TCI-NATIVE-OMNIRIG-R7-RXACK-win64'"
new_name = "MSI_NAME='JTDX-SuperHound-2.2.159-R8-FLEX6XXX-HAMLIB159-TEST-win64'"
if new_name not in b:
    if b.count(old_name) != 1:
        raise SystemExit('[FAIL] R8 MSI name anchor missing')
    b = b.replace(old_name, new_name, 1)

bp.write_text(b, encoding='utf-8', newline='\n')

final = bp.read_text(encoding='utf-8')
for needle in [
    jtdx159_hamlib,
    marker,
    'FlexRadio[[:space:]]+6xxx',
    '-m 2036 -r "127.0.0.1:$R8_FLEX_PORT"',
    "MSI_VERSION='2.2.205'",
    new_name,
]:
    if needle not in final:
        raise SystemExit(f'[FAIL] R8 postcheck missing {needle!r}')
if old_hamlib in final:
    raise SystemExit('[FAIL] R8 postcheck found obsolete Hamlib commit')

print('[PASS] R8 = user-confirmed R7 + exact JTDX 2.2.159 Hamlib + FlexRadio 6xxx network regression gate')
