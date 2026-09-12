# Migration audit — legacy JTDX branches

Migration date: 2026-09-12

Source repository: `SQ4KOU/SQ4KOU-THETIS`
Destination repository: `SQ4KOU/JTDX_SuperHound`

The active JTDX `main` line was preserved. Legacy JTDX branches formerly stored in `SQ4KOU-THETIS` were migrated under `archive/from-sq4kou-thetis/`.

Foreign `.github/workflows/` files were intentionally removed during history filtering because CI definitions are repository-specific. This rewrites destination commit SHAs while retaining the JTDX project-source history and commit messages.

| Source branch | Source SHA | Destination branch | Destination SHA |
|---|---|---|---|
| `jtdx-final-build` | `9390011f05925dc5fac11c17c0c3357204a0d84e` | `archive/from-sq4kou-thetis/jtdx-final-build` | `9b2250c6e5041f6bf675b60cd8d8ba4282433635` |
| `jtdx-final-build-2` | `b59f2071193de0a8ffdd53710dbdeacb98884ab4` | `archive/from-sq4kou-thetis/jtdx-final-build-2` | `cecc6b31dde3b9f52f9236d5dd436d838749de95` |
| `jtdx-superhound-p1-ci` | `e23e709e25f8d37fa4d6eecedea03502fba7c3e4` | `archive/from-sq4kou-thetis/jtdx-superhound-p1-ci` | `24bee050b231224a8cb338b2ba9d3db669b2d691` |

These branches are archival references. Current JTDX development remains on this repository's own active lines.
