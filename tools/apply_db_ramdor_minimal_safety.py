from pathlib import Path
import re

p = Path(r"Project Files/Source/Console/database.cs")
raw = p.read_bytes()
had_bom = raw.startswith(b"\xef\xbb\xbf")
text = raw.decode("utf-8-sig")
# Preserve the source file's existing line-ending convention so this remains a tiny diff.
eol = "\r\n" if text.count("\r\n") >= max(1, text.count("\n") // 2) else "\n"

def source_eol(s: str) -> str:
    return s.replace("\r\n", "\n").replace("\n", eol)

# This patch is intentionally small. Database semantics remain ramdor/Thetis.
# Only existing databases use atomic replace + last-good fallback.
# A genuinely new/missing database follows the original ramdor creation path.
for forbidden in (
    "IsDatabaseCompatible",
    "CurrentDatabaseSchemaVersion",
    "LoadedDatabaseSchemaVersion",
    "schema_mismatch",
    "MIGRATE_",
    "CHECKPOINT_",
):
    if forbidden in text:
        raise RuntimeError(f"source is not clean ramdor DB handling; forbidden token present: {forbidden}")

marker = "        #region Private Member Functions"
if marker not in text:
    raise RuntimeError("private member marker not found")

helpers = source_eol(r'''        // SQ4KOU: minimal database corruption protection only.
        // Database schema, import, migration and compatibility semantics remain ramdor/Thetis.
        private static bool _loaded_from_lastgood = false;

        private static string LastGoodFileName(string filename)
        {
            string dir = Path.GetDirectoryName(filename);
            if (string.IsNullOrEmpty(dir)) dir = ".";
            string name = Path.GetFileNameWithoutExtension(filename);
            string ext = Path.GetExtension(filename);
            return Path.Combine(dir, name + ".lastgood" + ext);
        }

        private static bool TryReadDatabase(string filename, out DataSet loaded)
        {
            loaded = null;
            if (string.IsNullOrEmpty(filename) || !File.Exists(filename)) return false;
            try
            {
                DataSet candidate = new DataSet("Data");
                candidate.ReadXml(filename);
                loaded = candidate;
                return true;
            }
            catch
            {
                return false;
            }
        }

''')

# Idempotent: the workflow can run again after the real C# source was already committed.
if "private static bool _loaded_from_lastgood = false;" not in text:
    text = text.replace(marker, helpers + marker, 1)

# Startup: normal ramdor read first. If an EXISTING database is corrupt, try
# last-good. If database.xml is simply missing, do nothing here: ramdor's
# VerifyTables() below must create a genuinely fresh database.
if "string lastGood = LastGoodFileName(_file_name);" not in text:
    read_pattern = re.compile(
        r'''\s*if\s*\(File\.Exists\(_file_name\)\)\s*\{\s*try\s*\{\s*ds\.ReadXml\(_file_name\);\s*\}\s*catch\s*\{\s*return\s+false;\s*\}\s*\}''',
        re.MULTILINE,
    )
    new_read = source_eol(r'''
            _loaded_from_lastgood = false;
            string lastGood = LastGoodFileName(_file_name);

            if (File.Exists(_file_name))
            {
                try
                {
                    ds.ReadXml(_file_name);
                }
                catch
                {
                    if (!TryReadDatabase(lastGood, out DataSet recovered))
                        return false;

                    ds = recovered;
                    _loaded_from_lastgood = true;
                    Debug.Print("Database.xml could not be read. Loaded database.lastgood.xml instead.");
                }
            }''')
    text, count = read_pattern.subn(lambda m: new_read, text, count=1)
    if count != 1:
        raise RuntimeError(f"original ramdor Init ReadXml block not found uniquely; matches={count}")
else:
    # Remove the previous over-eager behaviour which treated a deliberately
    # missing database.xml as a recovery event. Missing means: create fresh.
    missing_fallback = source_eol(r'''
            else if (TryReadDatabase(lastGood, out DataSet recovered))
            {
                ds = recovered;
                _loaded_from_lastgood = true;
                Debug.Print("Database.xml is missing. Loaded database.lastgood.xml instead.");
            }''')
    text = text.replace(missing_fallback, "", 1)

def replace_method(src: str, signature: str, replacement: str) -> str:
    start = src.find(signature)
    if start < 0:
        raise RuntimeError(f"method not found: {signature}")
    open_brace = src.find("{", start)
    if open_brace < 0:
        raise RuntimeError("opening brace not found")
    depth = 0
    i = open_brace
    while i < len(src):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[:start] + replacement + src[i + 1:]
        i += 1
    raise RuntimeError("closing brace not found")

write_method = source_eol(r'''        public static bool WriteDB(string fn, DataSet dsIN)
        {
            string temp = fn + ".tmp";
            string lastGood = LastGoodFileName(fn);
            bool primaryFile = string.Equals(Path.GetFullPath(fn), Path.GetFullPath(_file_name), StringComparison.OrdinalIgnoreCase);
            bool existedBeforeWrite = File.Exists(fn);

            try
            {
                // IMPORTANT: fresh database creation keeps the original ramdor path.
                // DBMan expects database.xml to exist immediately after DB.Init().
                if (!existedBeforeWrite)
                {
                    dsIN.WriteXml(fn, XmlWriteMode.WriteSchema);

                    // Verify the newly created file before accepting it.
                    DataSet firstWriteVerify = new DataSet("Data");
                    firstWriteVerify.ReadXml(fn);

                    if (!File.Exists(lastGood))
                        File.Copy(fn, lastGood, false);

                    if (primaryFile) _loaded_from_lastgood = false;
                    DBMan.DBWritten();
                    return true;
                }

                // Existing database: protected atomic replacement.
                if (File.Exists(temp)) File.Delete(temp);

                using (FileStream fs = new FileStream(temp, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                {
                    dsIN.WriteXml(fs, XmlWriteMode.WriteSchema);
                    fs.Flush(true);
                }

                DataSet verify = new DataSet("Data");
                verify.ReadXml(temp);

                if (primaryFile && _loaded_from_lastgood)
                {
                    // The live file was corrupt; do not overwrite the known-good backup with it.
                    File.Replace(temp, fn, null, true);
                }
                else
                {
                    File.Replace(temp, fn, lastGood, true);
                }

                if (primaryFile) _loaded_from_lastgood = false;
                DBMan.DBWritten();
            }
            catch (Exception ex)
            {
                try { if (File.Exists(temp)) File.Delete(temp); } catch { }
                // If first creation failed, leave no half-created database.xml behind.
                if (!existedBeforeWrite)
                {
                    try { if (File.Exists(fn)) File.Delete(fn); } catch { }
                }

                MessageBox.Show("A database write to file operation failed.  " +
                    "The exception error was:\n\n" + ex.Message,
                    "ERROR: Database Write Error",
                    MessageBoxButtons.OK, MessageBoxIcon.Error, MessageBoxDefaultButton.Button1, Common.MB_TOPMOST);
                return false;
            }
            return true;
        }''')
text = replace_method(text, "        public static bool WriteDB(string fn, DataSet dsIN)", write_method)

for token in (
    "dsIN.WriteXml(fn, XmlWriteMode.WriteSchema)",
    "firstWriteVerify.ReadXml(fn)",
    "File.Replace(temp, fn, lastGood, true)",
    "fs.Flush(true)",
    "verify.ReadXml(temp)",
    "_loaded_from_lastgood",
    "LastGoodFileName",
):
    if token not in text:
        raise RuntimeError(f"minimal safety verification failed: {token}")

if "Database.xml is missing. Loaded database.lastgood.xml instead." in text:
    raise RuntimeError("missing database must create fresh, not recover last-good")

for forbidden in (
    "IsDatabaseCompatible",
    "CurrentDatabaseSchemaVersion",
    "LoadedDatabaseSchemaVersion",
    "schema_mismatch",
    "MIGRATE_",
    "CHECKPOINT_",
):
    if forbidden in text:
        raise RuntimeError(f"forbidden compatibility machinery present after patch: {forbidden}")

out = text.encode("utf-8")
if had_bom:
    out = b"\xef\xbb\xbf" + out
p.write_bytes(out)
print("Applied ramdor DB semantics: original fresh creation + atomic protection for existing DB only.")
