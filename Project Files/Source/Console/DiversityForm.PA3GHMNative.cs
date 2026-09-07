using System;
using System.Drawing;
using System.Windows.Forms;

namespace Thetis
{
    public partial class DiversityForm
    {
        private PA3GHMNativeDiversityController _pa3ghmNative;
        private GroupBoxTS grpPA3GHMNative;
        private TextBoxTS txtPA3GHMStatus;
        private ComboBoxTS comboPA3GHMSweepType;
        private CheckBoxTS chkPA3GHMAvgMeter;
        private CheckBoxTS chkPA3GHMApplyBest;
        private NumericUpDownTS udPA3GHMSweepStart;
        private NumericUpDownTS udPA3GHMSweepEnd;
        private NumericUpDownTS udPA3GHMSweepStep;
        private NumericUpDownTS udPA3GHMSweepSettle;
        private NumericUpDownTS udPA3GHMCoarseStep;
        private NumericUpDownTS udPA3GHMCoarseSettle;
        private NumericUpDownTS udPA3GHMFineRange;
        private NumericUpDownTS udPA3GHMFineStep;
        private NumericUpDownTS udPA3GHMFineSettle;
        private NumericUpDownTS udPA3GHMGainRange;
        private NumericUpDownTS udPA3GHMGainStep;
        private NumericUpDownTS udPA3GHMGainSettle;
        private NumericUpDownTS udPA3GHMAutoSettle;
        private TextBoxTS txtPA3GHMAutoPlan;

        private NumericUpDownTS NativeNumeric(string name, decimal min, decimal max, decimal value, decimal increment, int decimals, int x, int y, int width = 74)
        {
            NumericUpDownTS n = new NumericUpDownTS();
            n.Name = name;
            n.Minimum = min;
            n.Maximum = max;
            n.Value = Math.Max(min, Math.Min(max, value));
            n.Increment = increment;
            n.DecimalPlaces = decimals;
            n.Location = new Point(x, y);
            n.Size = new Size(width, 20);
            return n;
        }

        private LabelTS NativeLabel(string text, int x, int y, int width = 90)
        {
            LabelTS l = new LabelTS();
            l.Text = text;
            l.Location = new Point(x, y + 3);
            l.Size = new Size(width, 18);
            return l;
        }

        private ButtonTS NativeButton(string text, int x, int y, int width, EventHandler handler)
        {
            ButtonTS b = new ButtonTS();
            b.Text = text;
            b.Location = new Point(x, y);
            b.Size = new Size(width, 26);
            b.Click += handler;
            return b;
        }

        private void EnsurePA3GHMNativePanelSize()
        {
            Size min = this.MinimumSize;
            if (min.Width < 736 || min.Height < 637)
                this.MinimumSize = new Size(Math.Max(736, min.Width), Math.Max(637, min.Height));

            if (this.ClientSize.Width < 720 || this.ClientSize.Height < 598)
                this.ClientSize = new Size(Math.Max(720, this.ClientSize.Width), Math.Max(598, this.ClientSize.Height));
        }

        private void InitPA3GHMNativePanel()
        {
            if (grpPA3GHMNative != null) return;

            // Native controls are deliberately independent from the TCI server and from
            // Setup > TCI > "ThetisLink extensions". Controls are created before RestoreForm
            // so their operator settings persist exactly like the original Diversity controls.
            grpPA3GHMNative = new GroupBoxTS();
            grpPA3GHMNative.Name = "grpPA3GHMNative";
            grpPA3GHMNative.Text = "PA3GHM TL2-4 — Native Diversity";
            grpPA3GHMNative.Location = new Point(320, 6);
            grpPA3GHMNative.Size = new Size(392, 582);
            this.Controls.Add(grpPA3GHMNative);

            LabelTS mode = NativeLabel("Native control — TCI server/checkbox not required", 10, 20, 365);
            grpPA3GHMNative.Controls.Add(mode);

            comboPA3GHMSweepType = new ComboBoxTS();
            comboPA3GHMSweepType.Name = "comboPA3GHMSweepType";
            comboPA3GHMSweepType.DropDownStyle = ComboBoxStyle.DropDownList;
            comboPA3GHMSweepType.Items.AddRange(new object[] { "Phase", "Gain dB" });
            comboPA3GHMSweepType.SelectedIndex = 0;
            comboPA3GHMSweepType.Location = new Point(94, 48);
            comboPA3GHMSweepType.Size = new Size(90, 21);
            grpPA3GHMNative.Controls.Add(NativeLabel("Sweep", 10, 48, 80));
            grpPA3GHMNative.Controls.Add(comboPA3GHMSweepType);

            chkPA3GHMAvgMeter = new CheckBoxTS();
            chkPA3GHMAvgMeter.Name = "chkPA3GHMAvgMeter";
            chkPA3GHMAvgMeter.Text = "AVG meter";
            chkPA3GHMAvgMeter.Checked = false;
            chkPA3GHMAvgMeter.Location = new Point(195, 49);
            chkPA3GHMAvgMeter.Size = new Size(86, 20);
            grpPA3GHMNative.Controls.Add(chkPA3GHMAvgMeter);

            chkPA3GHMApplyBest = new CheckBoxTS();
            chkPA3GHMApplyBest.Name = "chkPA3GHMApplyBest";
            chkPA3GHMApplyBest.Text = "Apply best";
            chkPA3GHMApplyBest.Checked = true;
            chkPA3GHMApplyBest.Location = new Point(286, 49);
            chkPA3GHMApplyBest.Size = new Size(90, 20);
            grpPA3GHMNative.Controls.Add(chkPA3GHMApplyBest);

            grpPA3GHMNative.Controls.Add(NativeLabel("Start", 10, 78, 55));
            udPA3GHMSweepStart = NativeNumeric("udPA3GHMSweepStart", -180m, 180m, -180m, 1m, 1, 58, 76, 65);
            grpPA3GHMNative.Controls.Add(udPA3GHMSweepStart);
            grpPA3GHMNative.Controls.Add(NativeLabel("End", 130, 78, 45));
            udPA3GHMSweepEnd = NativeNumeric("udPA3GHMSweepEnd", -180m, 360m, 180m, 1m, 1, 168, 76, 65);
            grpPA3GHMNative.Controls.Add(udPA3GHMSweepEnd);
            grpPA3GHMNative.Controls.Add(NativeLabel("Step", 240, 78, 45));
            udPA3GHMSweepStep = NativeNumeric("udPA3GHMSweepStep", 0.1m, 90m, 5m, 0.5m, 1, 280, 76, 58);
            grpPA3GHMNative.Controls.Add(udPA3GHMSweepStep);
            grpPA3GHMNative.Controls.Add(NativeLabel("ms", 342, 78, 25));
            udPA3GHMSweepSettle = NativeNumeric("udPA3GHMSweepSettle", 0m, 1000m, 50m, 10m, 0, 10, 104, 65);
            grpPA3GHMNative.Controls.Add(NativeLabel("Settle", 80, 106, 50));
            grpPA3GHMNative.Controls.Add(udPA3GHMSweepSettle);

            grpPA3GHMNative.Controls.Add(NativeButton("Sweep", 155, 102, 70, (s, e) => StartNativeSweep(false)));
            grpPA3GHMNative.Controls.Add(NativeButton("Fast Sweep", 230, 102, 82, (s, e) => StartNativeSweep(true)));
            grpPA3GHMNative.Controls.Add(NativeButton("STOP", 317, 102, 60, (s, e) => _pa3ghmNative?.Cancel()));

            LabelTS smartTitle = NativeLabel("Smart / Ultra parameters", 10, 142, 200);
            smartTitle.Font = new Font(smartTitle.Font, FontStyle.Bold);
            grpPA3GHMNative.Controls.Add(smartTitle);

            grpPA3GHMNative.Controls.Add(NativeLabel("Coarse step °", 10, 168, 92));
            udPA3GHMCoarseStep = NativeNumeric("udPA3GHMCoarseStep", 0.5m, 30m, 5m, 0.5m, 1, 105, 166);
            grpPA3GHMNative.Controls.Add(udPA3GHMCoarseStep);
            grpPA3GHMNative.Controls.Add(NativeLabel("Coarse ms", 195, 168, 78));
            udPA3GHMCoarseSettle = NativeNumeric("udPA3GHMCoarseSettle", 10m, 1000m, 50m, 10m, 0, 275, 166);
            grpPA3GHMNative.Controls.Add(udPA3GHMCoarseSettle);

            grpPA3GHMNative.Controls.Add(NativeLabel("Fine range °", 10, 196, 92));
            udPA3GHMFineRange = NativeNumeric("udPA3GHMFineRange", 1m, 90m, 15m, 1m, 1, 105, 194);
            grpPA3GHMNative.Controls.Add(udPA3GHMFineRange);
            grpPA3GHMNative.Controls.Add(NativeLabel("Fine step °", 195, 196, 78));
            udPA3GHMFineStep = NativeNumeric("udPA3GHMFineStep", 0.1m, 10m, 1m, 0.1m, 1, 275, 194);
            grpPA3GHMNative.Controls.Add(udPA3GHMFineStep);

            grpPA3GHMNative.Controls.Add(NativeLabel("Fine ms", 10, 224, 92));
            udPA3GHMFineSettle = NativeNumeric("udPA3GHMFineSettle", 10m, 1000m, 50m, 10m, 0, 105, 222);
            grpPA3GHMNative.Controls.Add(udPA3GHMFineSettle);
            grpPA3GHMNative.Controls.Add(NativeLabel("Gain range dB", 195, 224, 80));
            udPA3GHMGainRange = NativeNumeric("udPA3GHMGainRange", 0.5m, 20m, 6m, 0.5m, 1, 275, 222);
            grpPA3GHMNative.Controls.Add(udPA3GHMGainRange);

            grpPA3GHMNative.Controls.Add(NativeLabel("Gain step dB", 10, 252, 92));
            udPA3GHMGainStep = NativeNumeric("udPA3GHMGainStep", 0.1m, 3m, 0.5m, 0.1m, 1, 105, 250);
            grpPA3GHMNative.Controls.Add(udPA3GHMGainStep);
            grpPA3GHMNative.Controls.Add(NativeLabel("Gain ms", 195, 252, 80));
            udPA3GHMGainSettle = NativeNumeric("udPA3GHMGainSettle", 10m, 1000m, 50m, 10m, 0, 275, 250);
            grpPA3GHMNative.Controls.Add(udPA3GHMGainSettle);

            grpPA3GHMNative.Controls.Add(NativeButton("Smart Null", 105, 280, 100, (s, e) => StartNativeSmartNull()));
            grpPA3GHMNative.Controls.Add(NativeButton("Ultra Null", 215, 280, 100, (s, e) => StartNativeUltraNull()));

            LabelTS autoTitle = NativeLabel("Auto Null plan", 10, 320, 120);
            autoTitle.Font = new Font(autoTitle.Font, FontStyle.Bold);
            grpPA3GHMNative.Controls.Add(autoTitle);
            grpPA3GHMNative.Controls.Add(NativeLabel("Settle ms", 195, 320, 72));
            udPA3GHMAutoSettle = NativeNumeric("udPA3GHMAutoSettle", 5m, 1000m, 50m, 10m, 0, 275, 318);
            grpPA3GHMNative.Controls.Add(udPA3GHMAutoSettle);

            txtPA3GHMAutoPlan = new TextBoxTS();
            txtPA3GHMAutoPlan.Name = "txtPA3GHMAutoPlan";
            txtPA3GHMAutoPlan.Multiline = true;
            txtPA3GHMAutoPlan.ScrollBars = ScrollBars.Vertical;
            txtPA3GHMAutoPlan.Location = new Point(10, 346);
            txtPA3GHMAutoPlan.Size = new Size(366, 68);
            txtPA3GHMAutoPlan.Text = "P:0:90:180:270|P:-45:-20:-10:0:10:20:45|P:-5:-2:-1:0:1:2:5|G:-6:-3:-1:0:1:3:6|G:-1:-0.5:0:0.5:1";
            grpPA3GHMNative.Controls.Add(txtPA3GHMAutoPlan);
            grpPA3GHMNative.Controls.Add(NativeButton("Auto Null", 105, 420, 100, (s, e) => StartNativeAutoNull()));
            grpPA3GHMNative.Controls.Add(NativeButton("STOP", 215, 420, 100, (s, e) => _pa3ghmNative?.Cancel()));

            txtPA3GHMStatus = new TextBoxTS();
            txtPA3GHMStatus.Name = "txtPA3GHMStatus";
            txtPA3GHMStatus.Multiline = true;
            txtPA3GHMStatus.ReadOnly = true;
            txtPA3GHMStatus.ScrollBars = ScrollBars.Vertical;
            txtPA3GHMStatus.Location = new Point(10, 458);
            txtPA3GHMStatus.Size = new Size(366, 108);
            txtPA3GHMStatus.Text = "READY — native engine; TCI not required.";
            grpPA3GHMNative.Controls.Add(txtPA3GHMStatus);

            _pa3ghmNative = new PA3GHMNativeDiversityController(console, SetPA3GHMNativeStatus);
            this.FormClosed += (s, e) => _pa3ghmNative?.Cancel();
        }

        private void SetPA3GHMNativeStatus(string text)
        {
            if (txtPA3GHMStatus == null || txtPA3GHMStatus.IsDisposed) return;
            if (txtPA3GHMStatus.InvokeRequired)
            {
                try { txtPA3GHMStatus.BeginInvoke(new Action<string>(SetPA3GHMNativeStatus), text); }
                catch { }
                return;
            }
            txtPA3GHMStatus.AppendText(Environment.NewLine + DateTime.Now.ToString("HH:mm:ss") + "  " + text);
        }

        private void StartNativeSweep(bool fast)
        {
            bool phase = comboPA3GHMSweepType.SelectedIndex == 0;
            _pa3ghmNative.StartSweep(fast, phase,
                (float)udPA3GHMSweepStart.Value,
                (float)udPA3GHMSweepEnd.Value,
                (float)udPA3GHMSweepStep.Value,
                (int)udPA3GHMSweepSettle.Value,
                chkPA3GHMAvgMeter.Checked,
                chkPA3GHMApplyBest.Checked);
        }

        private void StartNativeAutoNull()
        {
            _pa3ghmNative.StartAutoNull((int)udPA3GHMAutoSettle.Value, txtPA3GHMAutoPlan.Text);
        }

        private void StartNativeSmartNull()
        {
            _pa3ghmNative.StartSmartNull(
                (float)udPA3GHMCoarseStep.Value,
                (int)udPA3GHMCoarseSettle.Value,
                (float)udPA3GHMFineRange.Value,
                (float)udPA3GHMFineStep.Value,
                (int)udPA3GHMFineSettle.Value,
                (float)udPA3GHMGainRange.Value,
                (float)udPA3GHMGainStep.Value,
                (int)udPA3GHMGainSettle.Value);
        }

        private void StartNativeUltraNull()
        {
            _pa3ghmNative.StartUltraNull(
                (float)udPA3GHMGainRange.Value,
                (float)udPA3GHMGainStep.Value,
                (int)udPA3GHMGainSettle.Value);
        }
    }
}
