from pathlib import Path
import sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('.')
pp=root/'patch_superhound.py'
bp=root/'BUILD_JTDX_SUPERHOUND_MSI.ps1'
s=pp.read_text(encoding='utf-8')
marker='# SQ4KOU JT9 shutdown return-code fix.'
block = '''

# SQ4KOU JT9 shutdown return-code fix.
# killbyname(): 0 = terminated successfully, 603 = not running.
# The original JTDX loop incorrectly displays "Error Killing" for return 0
# and can repeat modal warnings forever for a persistent real error.
p, s = load('mainwindow.cpp')
old = """          int iret=killbyname(\"jtdxjt9.exe\");
          if(iret == 603) break;
            JTDXMessageBox::warning_message (this, \"\", tr (\"Error Killing jtdxjt9.exe Process\")
                                         , tr (\"KillByName return code: %1\")
                                         .arg (iret));
"""
new = """          int iret=killbyname(\"jtdxjt9.exe\");
          if(iret == 0) continue;   // process terminated successfully; drain any stale copy
          if(iret == 603) break;    // process is already not running
          JTDXMessageBox::warning_message (this, \"\", tr (\"Error Killing jtdxjt9.exe Process\")
                                       , tr (\"KillByName return code: %1\")
                                       .arg (iret));
          break;                    // report a real error once; never loop modal warnings
"""
if new not in s:
    n=s.count(old)
    if n != 1:
        raise SystemExit(f'[FAIL] mainwindow.cpp jt9 shutdown anchor count={n}')
    s=s.replace(old,new,1)
    save(p,s)
    print('[OK] mainwindow.cpp jt9 shutdown return-code handling')
else:
    print('[SKIP] mainwindow.cpp jt9 shutdown return-code handling: already patched')
_, s = load('mainwindow.cpp')
for needle in ['if(iret == 0) continue;', 'if(iret == 603) break;', 'report a real error once; never loop modal warnings']:
    if needle not in s:
        raise SystemExit(f'[FAIL] jt9 shutdown postcheck missing {needle!r}')
print('[PASS] JT9 shutdown source postcheck')
'''
if marker not in s:
    s += block
pp.write_text(s,encoding='utf-8')
b=bp.read_text(encoding='utf-8')
oldver="MSI_VERSION='2.2.174'"
oldname="MSI_NAME='JTDX-SuperHound-2.2.159-FINAL-TCI-BANDFIX-win64'"
if oldver not in b: raise SystemExit('MSI 2.2.174 anchor missing')
if oldname not in b: raise SystemExit('MSI BANDFIX name anchor missing')
b=b.replace(oldver,"MSI_VERSION='2.2.175'",1)
b=b.replace(oldname,"MSI_NAME='JTDX-SuperHound-2.2.159-FINAL-TCI-BANDFIX-JT9FIX-win64'",1)
bp.write_text(b,encoding='utf-8')
if marker not in pp.read_text(encoding='utf-8'): raise SystemExit('JT9 patcher marker missing')
if "MSI_VERSION='2.2.175'" not in bp.read_text(encoding='utf-8'): raise SystemExit('version bump failed')
print('[PASS] JT9 shutdown overlay applied')
