using System;
using System.Windows.Forms;

namespace Thetis
{
    public partial class Console
    {
        private bool _pa3ghmNativeAutoRecenterEnabled = true;

        /// <summary>
        /// Native Thetis smooth-scroll auto-recenter master switch.
        /// This is deliberately independent from TCI and ThetisLink ownership.
        /// Default true preserves the normal standalone Thetis behaviour.
        /// </summary>
        public bool NativeAutoRecenterEnabled
        {
            get { return _pa3ghmNativeAutoRecenterEnabled; }
            set { _pa3ghmNativeAutoRecenterEnabled = value; }
        }

        public bool NativeExternalRecenterOwnerActive
        {
            get { return ThetisLinkRecenterOwnerActive; }
        }

        public void NativeReleaseExternalRecenterOwner()
        {
            if (InvokeRequired)
            {
                Invoke(new MethodInvoker(NativeReleaseExternalRecenterOwner));
                return;
            }
            ThetisLinkRecenterOwnerActive = false;
        }

        public void NativeRecenterRX1()
        {
            if (InvokeRequired)
            {
                Invoke(new MethodInvoker(NativeRecenterRX1));
                return;
            }

            CentreFrequency = VFOAFreq;
            rx1_osc = 0.0;
        }

        public void NativeRecenterRX2()
        {
            if (InvokeRequired)
            {
                Invoke(new MethodInvoker(NativeRecenterRX2));
                return;
            }

            CentreRX2Frequency = VFOBFreq;
            rx2_osc = 0.0;
        }

        public void NativeOpenDiversityControl()
        {
            if (InvokeRequired)
            {
                Invoke(new MethodInvoker(NativeOpenDiversityControl));
                return;
            }

            if (diversityForm == null || diversityForm.IsDisposed)
                diversityForm = new DiversityForm(this);

            if (!diversityForm.Visible)
                diversityForm.Show();

            diversityForm.Opacity = 1.0;
            diversityForm.BringToFront();
            diversityForm.Focus();
            UpdateDiversityValues();
            UpdateDiversityMenuItem();
        }
    }
}
