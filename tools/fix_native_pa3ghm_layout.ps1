$ErrorActionPreference = 'Stop'

$path = 'Project Files/Source/Console/DiversityForm.PA3GHMNative.cs'
if (-not (Test-Path -LiteralPath $path)) { throw "Missing $path" }

$text = [System.IO.File]::ReadAllText($path)

$pattern = '(?s)        private void EnsurePA3GHMNativePanelSize\(\)\s*\{.*?\n        \}\s*\n\s*        private void InitPA3GHMNativePanel\(\)'
if (-not [regex]::IsMatch($text, $pattern)) {
    throw 'Cannot locate EnsurePA3GHMNativePanelSize() block'
}

$replacement = @'
        private void EnsurePA3GHMNativePanelSize()
        {
            // RestoreForm may restore a stale child GroupBox height. The operator controls
            // must always remain fully visible, so final layout wins after RestoreForm.
            Size min = this.MinimumSize;
            if (min.Width < 736 || min.Height < 637)
                this.MinimumSize = new Size(Math.Max(736, min.Width), Math.Max(637, min.Height));

            if (this.ClientSize.Width < 720 || this.ClientSize.Height < 598)
                this.ClientSize = new Size(Math.Max(720, this.ClientSize.Width), Math.Max(598, this.ClientSize.Height));

            if (grpPA3GHMNative != null)
            {
                grpPA3GHMNative.Location = new Point(320, 6);
                grpPA3GHMNative.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
                grpPA3GHMNative.Size = new Size(
                    Math.Max(392, this.ClientSize.Width - 328),
                    Math.Max(582, this.ClientSize.Height - 12));
                grpPA3GHMNative.BringToFront();
            }
        }

        private void InitPA3GHMNativePanel()
'@

$text = [regex]::Replace($text, $pattern, $replacement, 1)

# Static gates: exact post-RestoreForm behavior and bottom controls must remain inside the panel.
foreach ($needle in @(
    'grpPA3GHMNative.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;',
    'Math.Max(582, this.ClientSize.Height - 12)',
    'txtPA3GHMAutoPlan.Location = new Point(10, 346);',
    'txtPA3GHMStatus.Location = new Point(10, 458);'
)) {
    if (-not $text.Contains($needle)) { throw "Layout gate missing: $needle" }
}

$utf8bom = New-Object System.Text.UTF8Encoding($true)
[System.IO.File]::WriteAllText($path, $text, $utf8bom)
Write-Host 'PA3GHM native Diversity full-height layout fix: PASS'
