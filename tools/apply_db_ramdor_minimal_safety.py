from pathlib import Path

p = Path(r"Project Files/Source/Console/database.cs")
text = p.read_text(encoding="utf-8-sig")

# This patch is intentionally small.  The database semantics remain ramdor/Thetis.
# We add only: (1) atomic write with previous good copy, (2) startup fallback.

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

# -----------------------------------------------------------------------------
# Small safety helpers/state.
# -----------------------------------------------------------------------------
marker = "        #region Private Member Functions"
if marker not in text:
    raise RuntimeError("private member marker not found")

helpers = r'''        // SQ4KOU: minimal database corruption protection only.
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

'''
text = text.replace(marker, helpers + marker, 1)

# -----------------------------------------------------------------------------
# Startup: normal ramdor read first.  Only if that XML cannot be read, use the
# previous atomically replaced database.  Nothing is migrated or normalized.
# -----------------------------------------------------------------------------
old_read = r'''            if (File.Exists(_file_name))
            {
                try
                {
                    ds.ReadXml(_file_name);
                }
                catch
                {
                    return false;
                }
            }
'''
new_read = r'''            _loaded_from_lastgood = false;
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
            }
            else if (TryReadDatabase(lastGood, out DataSet recovered))
            {
                ds = recovered;
                _loaded_from_lastgood = true;
                Debug.Print("Database.xml is missing. Loaded database.lastgood.xml instead.");
            }
'''
if old_read not in text:
    raise RuntimeError("original ramdor Init ReadXml block not found")
text = text.replace(old_read, new_read, 1)

# -----------------------------------------------------------------------------
# Atomic write.  Same public method/signature and same DBMan callback as ramdor.
# The temp file is fully flushed and read back before it may replace database.xml.
# -----------------------------------------------------------------------------
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

write_method = r'''        public static bool WriteDB(string fn, DataSet dsIN)
        {
            string temp = fn + ".tmp";
            string lastGood = LastGoodFileName(fn);
            bool primaryFile = string.Equals(Path.GetFullPath(fn), Path.GetFullPath(_file_name), StringComparison.OrdinalIgnoreCase);

            try
            {
                if (File.Exists(temp)) File.Delete(temp);

                using (FileStream fs = new FileStream(temp, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                {
                    dsIN.WriteXml(fs, XmlWriteMode.WriteSchema);
                    fs.Flush(true);
                }

                // A successfully written but unreadable XML file must never replace the live DB.
                DataSet verify = new DataSet("Data");
                verify.ReadXml(temp);

                if (File.Exists(fn))
                {
                    if (primaryFile && _loaded_from_lastgood)
                    {
                        // The current destination is the corrupt file which caused recovery.
                        // Replace it without overwriting the known-good backup with bad data.
                        File.Replace(temp, fn, null, true);
                    }
                    else
                    {
                        File.Replace(temp, fn, lastGood, true);
                    }
                }
                else
                {
                    File.Move(temp, fn);
                    if (!File.Exists(lastGood)) File.Copy(fn, lastGood, false);
                }

                if (primaryFile) _loaded_from_lastgood = false;
                DBMan.DBWritten();
            }
            catch (Exception ex)
            {
                try { if (File.Exists(temp)) File.Delete(temp); } catch { }

                MessageBox.Show("A database write to file operation failed.  " +
                    "The exception error was:\n\n" + ex.Message,
                    "ERROR: Database Write Error",
                    MessageBoxButtons.OK, MessageBoxIcon.Error, MessageBoxDefaultButton.Button1, Common.MB_TOPMOST);
                return false;
            }
            return true;
        }'''

text = replace_method(text, "        public static bool WriteDB(string fn, DataSet dsIN)", write_method)

required = (
    "File.Replace(temp, fn, lastGood, true)",
    "fs.Flush(true)",
    "verify.ReadXml(temp)",
    "database.lastgood.xml",
    "_loaded_from_lastgood",
)
for token in required:
    if token not in text:
        raise RuntimeError(f"minimal safety verification failed: {token}")

# Verify that no prior over-engineered compatibility system has crept back in.
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

p.write_text(text, encoding="utf-8-sig", newline="\n")
print("Applied minimal ramdor DB safety: atomic write + last-good fallback only.")
