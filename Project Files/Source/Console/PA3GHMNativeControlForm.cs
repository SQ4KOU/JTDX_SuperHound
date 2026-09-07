using System;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;

namespace Thetis
{
    /// <summary>
    /// Native operator surface for the PA3GHM TL2-4 additions.
    /// It calls Thetis' native Console/Setup paths directly and does not use TCI.
    /// Protocol-only frames (tci_caps_ex and auto_recenter_owner_ex handshake)
    /// are represented as status/maintenance information, not as operator commands.
    /// </summary>
    public sealed class PA3GHMNativeControlForm : Form
    {
        private readonly Console _console;
        private bool _updating;
        private Timer _refreshTimer;

        private CheckBoxTS chkRXOnly;
        private NumericUpDownTS udS9;
        private ComboBoxTS comboRX1Rate;
        private ComboBoxTS comboRX2Rate;
        private ComboBoxTS comboRX1Filter;
        private ComboBoxTS comboRX2Filter;
        private CheckBoxTS chkAutoRecenter;
        private LabelTS lblOwner;
        private LabelTS lblProtocol;
        private LabelTS lblStatus;

        public PA3GHMNativeControlForm(Console console)
        {
            _console = console ?? throw new ArgumentNullException(nameof(console));
            Text = "PA3GHM TL2-4 — Native Control";
            StartPosition = FormStartPosition.CenterParent;
            MinimumSize = new Size(590, 520);
            ClientSize = new Size(590, 520);
            FormBorderStyle = FormBorderStyle.Sizable;

            BuildUi();
            RefreshFromThetis();

            _refreshTimer = new Timer();
            _refreshTimer.Interval = 500;
            _refreshTimer.Tick += (s, e) => RefreshFromThetis();
            _refreshTimer.Start();

            FormClosed += (s, e) =>
            {
                if (_refreshTimer != null)
                {
                    _refreshTimer.Stop();
                    _refreshTimer.Dispose();
                    _refreshTimer = null;
                }
            };
        }

        private LabelTS Label(string text, int x, int y, int w = 135)
        {
            return new LabelTS { Text = text, Location = new Point(x, y + 3), Size = new Size(w, 20) };
        }

        private ButtonTS Button(string text, int x, int y, int w, EventHandler click)
        {
            ButtonTS b = new ButtonTS { Text = text, Location = new Point(x, y), Size = new Size(w, 26) };
            b.Click += click;
            return b;
        }

        private GroupBoxTS Group(string text, int x, int y, int w, int h)
        {
            return new GroupBoxTS { Text = text, Location = new Point(x, y), Size = new Size(w, h) };
        }

        private void BuildUi()
        {
            GroupBoxTS general = Group("Native radio controls — TCI not required", 10, 10, 565, 156);
            Controls.Add(general);

            chkRXOnly = new CheckBoxTS
            {
                Name = "chkPA3GHMNativeRXOnly",
                Text = "RX Only (TX inhibit)",
                Location = new Point(12, 26),
                Size = new Size(165, 22)
            };
            chkRXOnly.CheckedChanged += (s, e) =>
            {
                if (!_updating) _console.RXOnly = chkRXOnly.Checked;
            };
            general.Controls.Add(chkRXOnly);

            general.Controls.Add(Label("S9 HF/VHF threshold", 12, 56, 150));
            udS9 = new NumericUpDownTS
            {
                Name = "udPA3GHMNativeS9",
                Minimum = 1m,
                Maximum = 1000m,
                DecimalPlaces = 1,
                Increment = 0.1m,
                Location = new Point(166, 54),
                Size = new Size(76, 20)
            };
            udS9.ValueChanged += (s, e) =>
            {
                if (!_updating) _console.S9Frequency = (double)udS9.Value;
            };
            general.Controls.Add(udS9);
            general.Controls.Add(Label("MHz", 246, 56, 40));

            general.Controls.Add(Label("RX1 DDC sample rate", 12, 87, 145));
            comboRX1Rate = BuildRateCombo(166, 84, 0);
            general.Controls.Add(comboRX1Rate);
            general.Controls.Add(Label("RX2 DDC sample rate", 300, 87, 145));
            comboRX2Rate = BuildRateCombo(449, 84, 1);
            general.Controls.Add(comboRX2Rate);

            general.Controls.Add(Label("RX1 filter preset", 12, 118, 145));
            comboRX1Filter = BuildFilterCombo(166, 115, 0);
            general.Controls.Add(comboRX1Filter);
            general.Controls.Add(Label("RX2 filter preset", 300, 118, 145));
            comboRX2Filter = BuildFilterCombo(449, 115, 1);
            general.Controls.Add(comboRX2Filter);

            GroupBoxTS recenter = Group("Auto Recenter", 10, 175, 565, 128);
            Controls.Add(recenter);

            chkAutoRecenter = new CheckBoxTS
            {
                Name = "chkPA3GHMNativeAutoRecenter",
                Text = "Native smooth-scroll Auto Recenter",
                Location = new Point(12, 25),
                Size = new Size(245, 22)
            };
            chkAutoRecenter.CheckedChanged += (s, e) =>
            {
                if (!_updating) _console.NativeAutoRecenterEnabled = chkAutoRecenter.Checked;
            };
            recenter.Controls.Add(chkAutoRecenter);

            recenter.Controls.Add(Button("Recenter RX1 now", 12, 54, 130, (s, e) =>
            {
                _console.NativeRecenterRX1();
                SetStatus("RX1 centered on VFO A.");
            }));
            recenter.Controls.Add(Button("Recenter RX2 now", 150, 54, 130, (s, e) =>
            {
                _console.NativeRecenterRX2();
                SetStatus("RX2 centered on VFO B.");
            }));
            recenter.Controls.Add(Button("Release TCI owner", 288, 54, 125, (s, e) =>
            {
                _console.NativeReleaseExternalRecenterOwner();
                RefreshFromThetis();
                SetStatus("External recenter ownership released.");
            }));

            lblOwner = Label("External owner: --", 12, 91, 260);
            recenter.Controls.Add(lblOwner);
            lblProtocol = Label("Protocol: --", 300, 91, 220);
            recenter.Controls.Add(lblProtocol);

            GroupBoxTS diversity = Group("Diversity TL2-4", 10, 312, 565, 82);
            Controls.Add(diversity);
            diversity.Controls.Add(Label("Sweep / Fast Sweep / Auto Null / Smart Null / Ultra Null and all parameters", 12, 25, 520));
            diversity.Controls.Add(Button("Open Advanced Diversity", 12, 49, 190, (s, e) =>
            {
                _console.NativeOpenDiversityControl();
                SetStatus("Advanced Diversity opened.");
            }));

            GroupBoxTS protocol = Group("TL2-4 protocol metadata", 10, 403, 565, 73);
            Controls.Add(protocol);
            protocol.Controls.Add(Label("rx_filter_preset_ex / s9_frequency_ex: native controls above; TCI frames are state transport.", 12, 21, 535));
            protocol.Controls.Add(Label("tci_caps_ex and auto_recenter_owner_ex are protocol capability/ownership handshake, not DSP functions.", 12, 43, 535));

            lblStatus = new LabelTS
            {
                Text = "READY — native engine; TCI server and ThetisLink extensions are not required.",
                Location = new Point(12, 486),
                Size = new Size(560, 24)
            };
            Controls.Add(lblStatus);
        }

        private ComboBoxTS BuildRateCombo(int x, int y, int rx)
        {
            ComboBoxTS c = new ComboBoxTS
            {
                DropDownStyle = ComboBoxStyle.DropDownList,
                Location = new Point(x, y),
                Size = new Size(105, 21),
                Name = rx == 0 ? "comboPA3GHMNativeRX1Rate" : "comboPA3GHMNativeRX2Rate"
            };
            c.Items.AddRange(new object[] { "48000", "96000", "192000", "384000", "768000", "1536000" });
            c.SelectedIndexChanged += (s, e) =>
            {
                if (_updating || c.SelectedItem == null) return;
                if (!int.TryParse(c.SelectedItem.ToString(), out int rate)) return;
                if (_console.IsSetupFormNull) return;

                int oneBasedRx = rx + 1;
                _console.SetupForm.SetHWSampleRate(oneBasedRx, rate);
                int actual = rx == 0 ? _console.SampleRateRX1 : _console.SampleRateRX2;
                if (actual == rate)
                    SetStatus("RX" + oneBasedRx + " DDC sample rate set to " + rate + ".");
                else
                    SetStatus("RX" + oneBasedRx + " rate " + rate + " is not available for the current protocol/model.");
            };
            return c;
        }

        private ComboBoxTS BuildFilterCombo(int x, int y, int rx)
        {
            ComboBoxTS c = new ComboBoxTS
            {
                DropDownStyle = ComboBoxStyle.DropDownList,
                Location = new Point(x, y),
                Size = new Size(105, 21),
                Name = rx == 0 ? "comboPA3GHMNativeRX1Filter" : "comboPA3GHMNativeRX2Filter"
            };

            string[] names = Enum.GetNames(typeof(Filter))
                .Where(n => n != "FIRST" && n != "LAST" && (n.StartsWith("F") || n.StartsWith("VAR")))
                .ToArray();
            c.Items.AddRange(names.Cast<object>().ToArray());
            c.SelectedIndexChanged += (s, e) =>
            {
                if (_updating || c.SelectedItem == null) return;
                if (!Enum.TryParse(c.SelectedItem.ToString(), out Filter filter)) return;
                if (rx == 0) _console.RX1Filter = filter;
                else _console.RX2Filter = filter;
                SetStatus("RX" + (rx + 1) + " filter preset set to " + filter + ".");
            };
            return c;
        }

        private void RefreshFromThetis()
        {
            if (IsDisposed) return;
            _updating = true;
            try
            {
                chkRXOnly.Checked = _console.RXOnly;

                decimal s9 = (decimal)_console.S9Frequency;
                if (s9 < udS9.Minimum) s9 = udS9.Minimum;
                if (s9 > udS9.Maximum) s9 = udS9.Maximum;
                udS9.Value = s9;

                SelectCombo(comboRX1Rate, _console.SampleRateRX1.ToString());
                SelectCombo(comboRX2Rate, _console.SampleRateRX2.ToString());
                SelectCombo(comboRX1Filter, _console.RX1Filter.ToString());
                SelectCombo(comboRX2Filter, _console.RX2Filter.ToString());

                chkAutoRecenter.Checked = _console.NativeAutoRecenterEnabled;
                lblOwner.Text = "External TCI recenter owner: " + (_console.NativeExternalRecenterOwnerActive ? "ACTIVE" : "none");
                lblProtocol.Text = "Radio protocol: " + (NetworkIO.CurrentRadioProtocol == RadioProtocol.USB ? "Protocol 1" : "Protocol 2");
            }
            catch
            {
                // Thetis may be changing radio state while the form refreshes.
            }
            finally
            {
                _updating = false;
            }
        }

        private static void SelectCombo(ComboBox combo, string value)
        {
            if (combo.Items.Contains(value)) combo.SelectedItem = value;
            else combo.SelectedIndex = -1;
        }

        private void SetStatus(string text)
        {
            if (lblStatus != null) lblStatus.Text = DateTime.Now.ToString("HH:mm:ss") + "  " + text;
        }
    }
}
