# PA3GHM TL2-4 full synthesis provenance

Target branch: synthesis/pa3ghm-tl2-4-full
Base: SQ4KOU branch sq4kou
PA3GHM functional source: cjenschede/Thetis tag TL2-4 (7c97c803)
PA3GHM upstream reference: ramdor/Thetis tag v2.10.3.15 (3759d096)

Runtime files integrated:
- TCIServer.cs
- console.cs
- DiversityForm.cs
- cmaster.cs
- setup.cs
- setup.designer.cs

Intentionally excluded:
- PA3GHM title/About branding
- ReleaseNotes/README/NOTICE/ATTRIBUTION packaging changes
- VS project toolset substitutions (v145 -> v143)

Mandatory retained SQ4KOU functions:
- Protocol-1 software CWX IQ bridge
- Protocol-1 Diversity TX gate
- WideBand/PAN/ZOOM and P1 changes outside the TL2 file set
- GPS/CMD07 telemetry
- hardware snapshot telemetry and antenna TCI
- SQ4KOU database safety/compatibility changes
