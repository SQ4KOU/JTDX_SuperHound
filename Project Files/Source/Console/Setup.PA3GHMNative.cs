using System;
using System.Drawing;
using System.Windows.Forms;

namespace Thetis
{
    public partial class Setup
    {
        private CheckBoxTS chkPA3GHMCustomS9;
        private NumericUpDownTS udPA3GHMCustomS9;
        private LabelTS lblPA3GHMCustomS9;
        private ButtonTS btnPA3GHMNativeControl;
        private PA3GHMNativeControlForm frmPA3GHMNativeControl;

        private void InitPA3GHMNativeSetupControls()
        {
            // Native custom S9 threshold beside the original 30/144 MHz choices.
            if (groupBoxTS34 != null && chkPA3GHMCustomS9 == null)
            {
                chkPA3GHMCustomS9 = new CheckBoxTS();
                chkPA3GHMCustomS9.Name = "chkPA3GHMCustomS9";
                chkPA3GHMCustomS9.Text = "Custom S9 threshold";
                chkPA3GHMCustomS9.Location = new Point(14, 81);
                chkPA3GHMCustomS9.Size = new Size(135, 20);
                chkPA3GHMCustomS9.Checked = false;

                udPA3GHMCustomS9 = new NumericUpDownTS();
                udPA3GHMCustomS9.Name = "udPA3GHMCustomS9";
                udPA3GHMCustomS9.Minimum = 1m;
                udPA3GHMCustomS9.Maximum = 1000m;
                udPA3GHMCustomS9.DecimalPlaces = 1;
                udPA3GHMCustomS9.Increment = 0.1m;
                decimal initial = 30m;
                if (console != null)
                {
                    try { initial = (decimal)console.S9Frequency; }
                    catch { }
                }
                udPA3GHMCustomS9.Value = Math.Max(udPA3GHMCustomS9.Minimum, Math.Min(udPA3GHMCustomS9.Maximum, initial));
                udPA3GHMCustomS9.Location = new Point(151, 80);
                udPA3GHMCustomS9.Size = new Size(64, 20);
                udPA3GHMCustomS9.Enabled = false;

                lblPA3GHMCustomS9 = new LabelTS();
                lblPA3GHMCustomS9.Name = "lblPA3GHMCustomS9";
                lblPA3GHMCustomS9.Text = "MHz";
                lblPA3GHMCustomS9.Location = new Point(217, 83);
                lblPA3GHMCustomS9.Size = new Size(32, 18);

                groupBoxTS34.Controls.Add(chkPA3GHMCustomS9);
                groupBoxTS34.Controls.Add(udPA3GHMCustomS9);
                groupBoxTS34.Controls.Add(lblPA3GHMCustomS9);

                chkPA3GHMCustomS9.CheckedChanged += (s, e) =>
                {
                    bool custom = chkPA3GHMCustomS9.Checked;
                    udPA3GHMCustomS9.Enabled = custom;
                    radBelow30.Enabled = !custom;
                    radBelow144.Enabled = !custom;
                    if (custom && console != null)
                        console.S9Frequency = (double)udPA3GHMCustomS9.Value;
                };

                udPA3GHMCustomS9.ValueChanged += (s, e) =>
                {
                    if (chkPA3GHMCustomS9.Checked && console != null)
                        console.S9Frequency = (double)udPA3GHMCustomS9.Value;
                };

                toolTip1.SetToolTip(chkPA3GHMCustomS9,
                    "Native PA3GHM control. Sets the S9 HF/VHF threshold directly in Thetis; TCI is not required.");
            }

            // One obvious entry point for every operator-facing TL2-4 feature.
            // It sits next to the ThetisLink-extension checkbox, but is intentionally
            // independent of that checkbox and of the TCI server itself.
            if (groupBoxTS69 != null && btnPA3GHMNativeControl == null)
            {
                btnPA3GHMNativeControl = new ButtonTS();
                btnPA3GHMNativeControl.Name = "btnPA3GHMNativeControl";
                btnPA3GHMNativeControl.Text = "Native TL2-4 Control...";
                btnPA3GHMNativeControl.Location = new Point(158, 72);
                btnPA3GHMNativeControl.Size = new Size(164, 24);
                btnPA3GHMNativeControl.Click += (s, e) => ShowPA3GHMNativeControl();
                groupBoxTS69.Controls.Add(btnPA3GHMNativeControl);
                btnPA3GHMNativeControl.BringToFront();

                toolTip1.SetToolTip(btnPA3GHMNativeControl,
                    "Open all operator-facing PA3GHM TL2-4 controls locally in Thetis. TCI/ThetisLink is not required.");
            }
        }

        private void ShowPA3GHMNativeControl()
        {
            if (console == null) return;

            if (frmPA3GHMNativeControl == null || frmPA3GHMNativeControl.IsDisposed)
                frmPA3GHMNativeControl = new PA3GHMNativeControlForm(console);

            if (!frmPA3GHMNativeControl.Visible)
                frmPA3GHMNativeControl.Show(console);

            frmPA3GHMNativeControl.BringToFront();
            frmPA3GHMNativeControl.Focus();
        }
    }
}
