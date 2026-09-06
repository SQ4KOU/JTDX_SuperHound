from pathlib import Path
import sys


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8", errors="strict")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one patch point, found {count} in {path}")
    path.write_text(text.replace(old, new), encoding="utf-8", newline="")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: disable_omnirig_ci.py <jtdx-source>")
        return 2

    src = Path(sys.argv[1]).resolve()
    cmake = src / "CMakeLists.txt"
    factory = src / "TransceiverFactory.cpp"

    # SQ4KOU Windows/TCI build: OmniRig is not used.  Upstream JTDX requires a
    # registered OmniRig COM server during CMake configure, which makes a clean
    # unattended Windows build fail.  Keep all other Windows/TCI/Hamlib paths.
    replace_once(
        cmake,
        "\n  set (wsjt_qt_CXXSRCS\n"
        "    ${wsjt_qt_CXXSRCS}\n"
        "    OmniRigTransceiver.cpp\n"
        "    )\n",
        "\n",
        "remove OmniRigTransceiver.cpp from Windows sources",
    )

    text = cmake.read_text(encoding="utf-8", errors="strict")
    start_marker = "if (WIN32)\n  # generate the OmniRig COM interface source\n"
    end_marker = "endif (WIN32)\n#\n# decide on platform specifc packing and fixing up"
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError("OmniRig CMake start marker not found")
    end = text.find(end_marker, start)
    if end < 0:
        raise RuntimeError("OmniRig CMake end marker not found")
    end += len("endif (WIN32)\n")
    text = text[:start] + (
        "# SQ4KOU: OmniRig COM generation disabled for clean TCI Windows build.\n"
    ) + text[end:]
    cmake.write_text(text, encoding="utf-8", newline="")

    replace_once(
        cmake,
        "if (WIN32)\n"
        "  add_definitions (-DQT_NEEDS_QTMAIN)\n"
        "  find_package (Qt5AxContainer REQUIRED)\n"
        "endif (WIN32)",
        "if (WIN32)\n"
        "  add_definitions (-DQT_NEEDS_QTMAIN)\n"
        "  # SQ4KOU: Qt5AxContainer is only needed by disabled OmniRig support.\n"
        "endif (WIN32)",
        "remove Qt5AxContainer requirement",
    )

    replace_once(
        factory,
        "#if defined (WIN32)\n"
        "#include \"OmniRigTransceiver.hpp\"\n"
        "#endif",
        "// SQ4KOU: OmniRig disabled in this TCI-focused Windows build.",
        "remove OmniRig include",
    )

    replace_once(
        factory,
        "#if defined (WIN32)\n"
        "  // OmniRig is ActiveX/COM server so only on Windows\n"
        "  OmniRigTransceiver::register_transceivers (&transceivers_, OmniRigOneId, OmniRigTwoId);\n"
        "#endif",
        "  // SQ4KOU: OmniRig registration disabled; TCI/Hamlib remain unchanged.",
        "remove OmniRig registration",
    )

    print("OMNIRIG_CI_DISABLE PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
