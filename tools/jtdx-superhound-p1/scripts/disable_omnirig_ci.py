from pathlib import Path
import re
import sys


def sub_once(text: str, pattern: str, repl: str, label: str, flags: int = 0) -> str:
    out, count = re.subn(pattern, repl, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"{label}: expected one patch point, found {count}")
    return out


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: disable_omnirig_ci.py <jtdx-source>")
        return 2

    src = Path(sys.argv[1]).resolve()
    cmake = src / "CMakeLists.txt"
    factory = src / "TransceiverFactory.cpp"

    c = cmake.read_text(encoding="utf-8", errors="strict")

    # TCI-focused Windows build: OmniRig is not used. Current upstream JTDX
    # nevertheless hard-requires a registered OmniRig COM server at CMake time.
    # Remove only that optional CAT backend; Hamlib and TCI remain intact.
    c = sub_once(
        c,
        r"(?m)^\s*OmniRigTransceiver\.cpp\s*\r?\n",
        "",
        "remove OmniRigTransceiver.cpp from source list",
    )

    c = sub_once(
        c,
        r"if \(WIN32\)\r?\n\s*# generate the OmniRig COM interface source\r?\n.*?endif \(WIN32\)\r?\n",
        "# SQ4KOU: OmniRig COM discovery disabled for TCI Windows build.\n",
        "remove OmniRig COM discovery block",
        re.S,
    )

    c = sub_once(
        c,
        r"(?m)^\s*find_package \(Qt5AxContainer REQUIRED\)\s*\r?\n",
        "  # SQ4KOU: Qt5AxContainer was required only by OmniRig.\n",
        "remove Qt5AxContainer requirement",
    )

    c = sub_once(
        c,
        r"# AX COM servers\r?\nif \(WIN32\)\r?\n\s*include \(QtAxMacros\)\r?\n\s*wrap_ax_server \(GENAXSRCS \$\{AXSERVERSRCS\}\)\r?\nendif \(WIN32\)\r?\n",
        "# SQ4KOU: OmniRig ActiveX wrapper generation disabled.\n",
        "remove ActiveX wrapper generation",
    )

    c = sub_once(
        c,
        r"if \(WIN32\)\r?\n\s*target_link_libraries \(wsjt_qt Qt5::AxContainer Qt5::AxBase\)\r?\nendif \(WIN32\)\r?\n",
        "# SQ4KOU: OmniRig ActiveQt link dependencies disabled.\n",
        "remove ActiveQt link dependencies",
    )

    cmake.write_text(c, encoding="utf-8", newline="")

    f = factory.read_text(encoding="utf-8", errors="strict")
    f = sub_once(
        f,
        r"#if defined \(WIN32\)\r?\n#include \"OmniRigTransceiver\.hpp\"\r?\n#endif\r?\n",
        "// SQ4KOU: OmniRig disabled in this TCI-focused Windows build.\n",
        "remove OmniRig include",
    )
    f = sub_once(
        f,
        r"#if defined \(WIN32\)\r?\n\s*// OmniRig is ActiveX/COM server so only on Windows\r?\n\s*OmniRigTransceiver::register_transceivers \(&transceivers_, OmniRigOneId, OmniRigTwoId\);\r?\n#endif\r?\n",
        "  // SQ4KOU: OmniRig registration disabled; TCI/Hamlib remain unchanged.\n",
        "remove OmniRig registration",
    )
    factory.write_text(f, encoding="utf-8", newline="")

    # Fail closed if a build-time OmniRig hook survived.
    checks = {
        "CMake OmniRig source": "OmniRigTransceiver.cpp" in c,
        "CMake dumpcpp": "COMMAND ${DUMPCPP} -getfile" in c,
        "CMake ActiveX wrapper": "wrap_ax_server (GENAXSRCS" in c,
        "CMake ActiveQt link": "Qt5::AxContainer" in c or "Qt5::AxBase" in c,
        "Factory OmniRig include": "#include \"OmniRigTransceiver.hpp\"" in f,
        "Factory OmniRig registration": "OmniRigTransceiver::register_transceivers" in f,
    }
    bad = [name for name, present in checks.items() if present]
    if bad:
        raise RuntimeError("OmniRig disable incomplete: " + ", ".join(bad))

    print("OMNIRIG_CI_DISABLE PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
