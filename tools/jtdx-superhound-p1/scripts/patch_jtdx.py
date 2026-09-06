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
        "  # SQ4KOU SuperHound P1: external SuperFox RX bridge\n"
        "  lib/superhound_external.f90",
    )
    replace_once(
        cmake,
        "  lib/igray.c",
        "  lib/igray.c\n"
        "  # SQ4KOU SuperHound P1: external helper bridge\n"
        "  lib/superhound_external.c",
    )

    decoder = lib / "decoder.f90"
    anchor = "     if(params%nmode.eq.8) call ft8apset(params%lmycallstd,params%lhiscallstd,numthreads)"
    replacement = anchor + "\n\n" + "\n".join([
        "! SQ4KOU SUPER HOUND P1 RX - external SuperFox helper.",
        "! Full fresh FT8 Hound cycle only. Native JTDX FT8 remains unchanged.",
        "     if(params%lhound .and. .not.params%nagain .and. params%nzhsym.ge.49) then",
        "        call superhound_external(nutc,dd8)",
        "     endif",
        "! END SQ4KOU SUPER HOUND P1 RX",
    ])
    replace_once(decoder, anchor, replacement)

    print("PATCH PASS")
    print(f"source={src}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
