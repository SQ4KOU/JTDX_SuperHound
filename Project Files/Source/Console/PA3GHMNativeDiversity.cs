using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Threading;

namespace Thetis
{
    // Native, transport-independent implementation of the PA3GHM TL2-4 Diversity algorithms.
    // It deliberately has no dependency on TCPIPtciServer/TCPIPtciSocketListener and therefore
    // works with the TCI server stopped and with "ThetisLink extensions" unchecked.
    internal sealed class PA3GHMNativeDiversityController
    {
        private readonly Console _console;
        private readonly Action<string> _status;
        private int _generation;
        private volatile bool _running;

        public PA3GHMNativeDiversityController(Console console, Action<string> status)
        {
            _console = console;
            _status = status;
        }

        public bool IsRunning { get { return _running; } }

        public void Cancel()
        {
            Interlocked.Increment(ref _generation);
            _running = false;
            Report("STOPPED");
        }

        private int BeginRun(string name)
        {
            int generation = Interlocked.Increment(ref _generation);
            _running = true;
            Report(name + " — RUNNING");
            return generation;
        }

        private void Complete(int generation, string message)
        {
            if (generation != Volatile.Read(ref _generation)) return;
            _running = false;
            Report(message);
        }

        private void Report(string message)
        {
            try { _status?.Invoke(message); }
            catch { }
        }

        private bool ShouldAbort(int generation)
        {
            if (generation != Volatile.Read(ref _generation)) return true;
            if (_console == null || _console.IsDisposed) return true;

            // Keep the already-verified SQ4KOU Protocol-1 rule: asynchronous Diversity work
            // must not continue to alter phase/gain while the P1 TX gate has stopped EXTDIV.
            if (NetworkIO.CurrentRadioProtocol == RadioProtocol.USB)
            {
                try
                {
                    bool tx = InvokeRead(() => _console.MOX || _console.TUN);
                    if (tx)
                    {
                        Report("ABORTED — Protocol 1 MOX/TUNE");
                        return true;
                    }
                }
                catch
                {
                    return true;
                }
            }
            return false;
        }

        private void InvokeWrite(Action action)
        {
            if (_console.InvokeRequired)
                _console.Invoke(new System.Windows.Forms.MethodInvoker(action));
            else
                action();
        }

        private T InvokeRead<T>(Func<T> func)
        {
            if (_console.InvokeRequired)
                return (T)_console.Invoke(func);
            return func();
        }

        private static float WrapPhase(float phase)
        {
            while (phase > 180f) phase -= 360f;
            while (phase < -180f) phase += 360f;
            return phase;
        }

        private void EnsureEnabled()
        {
            InvokeWrite(() =>
            {
                if (!_console.Diversity2) _console.Diversity2 = true;
            });
        }

        private void SetPhase(int generation, float phase)
        {
            if (ShouldAbort(generation)) return;
            phase = WrapPhase(phase);
            InvokeWrite(() => _console.CATDiversityPhase = (decimal)phase);
        }

        private void SetGain(int generation, float gainLinear)
        {
            if (ShouldAbort(generation)) return;
            gainLinear = Math.Max(0.01f, Math.Min(10f, gainLinear));
            float g = gainLinear;
            InvokeWrite(() =>
            {
                bool rx1Ref = _console.DiversityRXRef;
                if (_console.diversityForm == null) return;
                if (rx1Ref) _console.diversityForm.DiversityR2Gain = (decimal)g;
                else _console.diversityForm.DiversityGain = (decimal)g;
            });
        }

        private float GetNonReferenceGainDb()
        {
            return InvokeRead(() =>
            {
                decimal gain = _console.DiversityRXRef
                    ? (_console.diversityForm != null ? _console.diversityForm.DiversityR2Gain : 1m)
                    : (_console.diversityForm != null ? _console.diversityForm.DiversityGain : 1m);
                return (float)(20.0 * Math.Log10(Math.Max(0.01, (double)gain)));
            });
        }

        private float ReadMeter(bool average)
        {
            return InvokeRead(() => WDSP.CalculateRXMeter(0, 0,
                average ? WDSP.MeterType.AVG_SIGNAL_STRENGTH : WDSP.MeterType.SIGNAL_STRENGTH));
        }

        private void ReadIndependentRxMeters(out float rx1Dbm, out float rx2Dbm)
        {
            float a = -200f, b = -200f;
            InvokeWrite(() =>
            {
                a = WDSP.CalculateRXMeter(0, 0, WDSP.MeterType.AVG_SIGNAL_STRENGTH);
                b = WDSP.CalculateRXMeter(2, 0, WDSP.MeterType.AVG_SIGNAL_STRENGTH);
            });
            rx1Dbm = a;
            rx2Dbm = b;
        }

        private float EqualizeReferenceGain(int generation, int offSettleMs, int onSettleMs)
        {
            if (ShouldAbort(generation)) return 1f;
            InvokeWrite(() => _console.Diversity2 = false);
            Thread.Sleep(offSettleMs);
            if (ShouldAbort(generation)) return 1f;

            ReadIndependentRxMeters(out float rx1Dbm, out float rx2Dbm);
            bool rx1Ref = InvokeRead(() => _console.DiversityRXRef);
            float refDbm = rx1Ref ? rx1Dbm : rx2Dbm;
            float nonRefDbm = rx1Ref ? rx2Dbm : rx1Dbm;
            float diffDb = refDbm - nonRefDbm;
            float gain = (float)Math.Pow(10.0, diffDb / 20.0);
            gain = Math.Max(0.01f, Math.Min(10f, gain));

            InvokeWrite(() => _console.Diversity2 = true);
            Thread.Sleep(onSettleMs);
            SetGain(generation, gain);
            SetPhase(generation, 0f);
            return gain;
        }

        private float MeasureImprovement(int generation, bool average, int settleMs, out float offDbm, out float onDbm)
        {
            offDbm = -200f;
            onDbm = -200f;
            if (ShouldAbort(generation)) return 0f;

            Thread.Sleep(settleMs);
            onDbm = ReadMeter(average);
            InvokeWrite(() => _console.Diversity2 = false);
            Thread.Sleep(settleMs);
            offDbm = ReadMeter(average);
            InvokeWrite(() => _console.Diversity2 = true);
            return offDbm - onDbm;
        }

        public void StartSweep(bool fastSweep, bool phaseSweep, float start, float end, float step,
            int settleMs, bool averageMeter, bool applyBest)
        {
            if (step <= 0f || end < start) return;
            settleMs = Math.Max(0, Math.Min(1000, settleMs));
            int generation = BeginRun(fastSweep ? "FAST SWEEP" : "SWEEP");
            ThreadPool.QueueUserWorkItem(_ =>
            {
                try
                {
                    EnsureEnabled();
                    float bestValue = start;
                    float bestDbm = 999f;
                    int count = 0;

                    Func<float, bool> runPoint = value =>
                    {
                        if (ShouldAbort(generation)) return false;
                        if (phaseSweep)
                            SetPhase(generation, value);
                        else
                            SetGain(generation, (float)Math.Pow(10.0, value / 20.0));
                        if (settleMs > 0) Thread.Sleep(settleMs);
                        if (ShouldAbort(generation)) return false;
                        float dbm = ReadMeter(averageMeter);
                        count++;
                        if (dbm < bestDbm)
                        {
                            bestDbm = dbm;
                            bestValue = value;
                        }
                        if ((count % 10) == 0)
                            Report((fastSweep ? "FAST SWEEP" : "SWEEP") + " " + count + " — " + dbm.ToString("F1", CultureInfo.InvariantCulture) + " dBm");
                        return true;
                    };

                    for (float v = start; v <= end + 0.0001f && count < 5000; v += step)
                        if (!runPoint(v)) return;

                    if (fastSweep)
                    {
                        for (float v = end; v >= start - 0.0001f && count < 10000; v -= step)
                            if (!runPoint(v)) return;
                    }

                    if (applyBest && !ShouldAbort(generation))
                    {
                        if (phaseSweep) SetPhase(generation, bestValue);
                        else SetGain(generation, (float)Math.Pow(10.0, bestValue / 20.0));
                    }

                    Complete(generation, (fastSweep ? "FAST SWEEP" : "SWEEP") + " DONE — best " +
                        bestValue.ToString("F1", CultureInfo.InvariantCulture) +
                        (phaseSweep ? "°" : " dB") + " / " + bestDbm.ToString("F1", CultureInfo.InvariantCulture) + " dBm");
                }
                catch (Exception ex)
                {
                    Complete(generation, "SWEEP ERROR — " + ex.Message);
                }
            });
        }

        public void StartAutoNull(int settleMs, string plan)
        {
            settleMs = Math.Max(5, Math.Min(1000, settleMs));
            if (string.IsNullOrWhiteSpace(plan)) return;

            var steps = new List<Tuple<bool, float[]>>();
            foreach (string raw in plan.Split('|'))
            {
                string s = raw.Trim();
                if (s.Length < 3 || s[1] != ':') continue;
                bool phase = s[0] == 'P' || s[0] == 'p';
                bool gain = s[0] == 'G' || s[0] == 'g';
                if (!phase && !gain) continue;
                var values = new List<float>();
                foreach (string token in s.Substring(2).Split(':'))
                {
                    if (float.TryParse(token.Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out float f))
                        values.Add(f);
                }
                if (values.Count > 0) steps.Add(Tuple.Create(phase, values.ToArray()));
            }
            if (steps.Count == 0) return;

            int generation = BeginRun("AUTO NULL");
            ThreadPool.QueueUserWorkItem(_ =>
            {
                try
                {
                    EnsureEnabled();
                    float bestPhase = 0f;
                    float bestGainDb = GetNonReferenceGainDb();
                    float bestSmeter = 999f;
                    bool firstPhaseRound = true;

                    for (int round = 0; round < steps.Count; round++)
                    {
                        if (ShouldAbort(generation)) return;
                        bool isPhase = steps[round].Item1;
                        float[] offsets = steps[round].Item2;
                        float roundBestSmeter = 999f;
                        float roundBestValue = 0f;

                        foreach (float offset in offsets)
                        {
                            if (ShouldAbort(generation)) return;
                            if (isPhase)
                            {
                                float p = firstPhaseRound ? offset : bestPhase + offset;
                                SetPhase(generation, p);
                            }
                            else
                            {
                                float gDb = bestGainDb + offset;
                                SetGain(generation, (float)Math.Pow(10.0, gDb / 20.0));
                            }
                            Thread.Sleep(settleMs);
                            float dbm = ReadMeter(false);
                            if (dbm < roundBestSmeter)
                            {
                                roundBestSmeter = dbm;
                                roundBestValue = offset;
                            }
                        }

                        if (isPhase)
                        {
                            bestPhase = WrapPhase(firstPhaseRound ? roundBestValue : bestPhase + roundBestValue);
                            firstPhaseRound = false;
                            SetPhase(generation, bestPhase);
                        }
                        else
                        {
                            bestGainDb += roundBestValue;
                            SetGain(generation, (float)Math.Pow(10.0, bestGainDb / 20.0));
                        }
                        bestSmeter = Math.Min(bestSmeter, roundBestSmeter);
                        Report("AUTO NULL " + (round + 1) + "/" + steps.Count + " — phase " +
                            bestPhase.ToString("F1", CultureInfo.InvariantCulture) + "°, gain " +
                            bestGainDb.ToString("F1", CultureInfo.InvariantCulture) + " dB, " +
                            bestSmeter.ToString("F1", CultureInfo.InvariantCulture) + " dBm");
                    }

                    float improvement = MeasureImprovement(generation, false, 500, out float offDbm, out float onDbm);
                    if (ShouldAbort(generation)) return;
                    Complete(generation, "AUTO NULL DONE — phase " + bestPhase.ToString("F1", CultureInfo.InvariantCulture) +
                        "°, gain " + bestGainDb.ToString("F1", CultureInfo.InvariantCulture) + " dB, improvement " +
                        improvement.ToString("F1", CultureInfo.InvariantCulture) + " dB (OFF " +
                        offDbm.ToString("F1", CultureInfo.InvariantCulture) + " / ON " +
                        onDbm.ToString("F1", CultureInfo.InvariantCulture) + ")");
                }
                catch (Exception ex)
                {
                    Complete(generation, "AUTO NULL ERROR — " + ex.Message);
                }
            });
        }

        public void StartSmartNull(float coarseStep, int coarseSettle, float fineRange, float fineStep,
            int fineSettle, float gainRangeDb, float gainStepDb, int gainSettle)
        {
            coarseStep = Math.Max(0.5f, Math.Min(30f, coarseStep));
            coarseSettle = Math.Max(10, Math.Min(1000, coarseSettle));
            fineRange = Math.Max(1f, Math.Min(90f, fineRange));
            fineStep = Math.Max(0.1f, Math.Min(10f, fineStep));
            fineSettle = Math.Max(10, Math.Min(1000, fineSettle));
            gainRangeDb = Math.Max(0.5f, Math.Min(20f, gainRangeDb));
            gainStepDb = Math.Max(0.1f, Math.Min(3f, gainStepDb));
            gainSettle = Math.Max(10, Math.Min(1000, gainSettle));

            int generation = BeginRun("SMART NULL");
            ThreadPool.QueueUserWorkItem(_ =>
            {
                try
                {
                    EqualizeReferenceGain(generation, 300, 200);
                    if (ShouldAbort(generation)) return;
                    Thread.Sleep(100);

                    float bestPhase = -180f;
                    float bestSmeter = 999f;
                    int coarseSteps = (int)(450f / coarseStep);
                    for (int i = 0; i <= coarseSteps; i++)
                    {
                        if (ShouldAbort(generation)) return;
                        float p = -180f + i * coarseStep;
                        SetPhase(generation, p);
                        Thread.Sleep(coarseSettle);
                        float dbm = ReadMeter(true);
                        if (dbm < bestSmeter) { bestSmeter = dbm; bestPhase = p; }
                    }
                    bestPhase = WrapPhase(bestPhase);
                    SetPhase(generation, bestPhase);
                    Report("SMART NULL — coarse " + bestPhase.ToString("F1", CultureInfo.InvariantCulture) + "° / " + bestSmeter.ToString("F1", CultureInfo.InvariantCulture) + " dBm");

                    float coarseNull = bestPhase;
                    bestSmeter = 999f;
                    for (float offset = -fineRange; offset <= fineRange + 0.0001f; offset += fineStep)
                    {
                        if (ShouldAbort(generation)) return;
                        float p = coarseNull + offset;
                        SetPhase(generation, p);
                        Thread.Sleep(fineSettle);
                        float dbm = ReadMeter(true);
                        if (dbm < bestSmeter) { bestSmeter = dbm; bestPhase = p; }
                    }
                    bestPhase = WrapPhase(bestPhase);
                    SetPhase(generation, bestPhase);
                    Report("SMART NULL — fine " + bestPhase.ToString("F1", CultureInfo.InvariantCulture) + "° / " + bestSmeter.ToString("F1", CultureInfo.InvariantCulture) + " dBm");

                    float currentGainDb = GetNonReferenceGainDb();
                    float bestGainDb = currentGainDb;
                    for (float offset = -gainRangeDb; offset <= gainRangeDb + 0.0001f; offset += gainStepDb)
                    {
                        if (ShouldAbort(generation)) return;
                        float gDb = currentGainDb + offset;
                        SetGain(generation, (float)Math.Pow(10.0, gDb / 20.0));
                        Thread.Sleep(gainSettle);
                        float dbm = ReadMeter(true);
                        if (dbm < bestSmeter) { bestSmeter = dbm; bestGainDb = gDb; }
                    }
                    SetGain(generation, (float)Math.Pow(10.0, bestGainDb / 20.0));
                    SetPhase(generation, bestPhase);

                    float improvement = MeasureImprovement(generation, true, 500, out float offDbm, out float onDbm);
                    if (ShouldAbort(generation)) return;
                    Complete(generation, "SMART NULL DONE — phase " + bestPhase.ToString("F1", CultureInfo.InvariantCulture) +
                        "°, gain " + bestGainDb.ToString("F1", CultureInfo.InvariantCulture) + " dB, improvement " +
                        improvement.ToString("F1", CultureInfo.InvariantCulture) + " dB");
                }
                catch (Exception ex)
                {
                    Complete(generation, "SMART NULL ERROR — " + ex.Message);
                }
            });
        }

        public void StartUltraNull(float gainRangeDb, float gainStepDb, int gainSettle)
        {
            gainRangeDb = Math.Max(0.5f, Math.Min(20f, gainRangeDb));
            gainStepDb = Math.Max(0.1f, Math.Min(3f, gainStepDb));
            gainSettle = Math.Max(10, Math.Min(1000, gainSettle));

            int generation = BeginRun("ULTRA NULL");
            ThreadPool.QueueUserWorkItem(_ =>
            {
                try
                {
                    EqualizeReferenceGain(generation, 100, 100);
                    if (ShouldAbort(generation)) return;

                    const float coarseStep = 1f;
                    int totalSteps = 450;
                    float fwdBestPhase = -180f, fwdBestDbm = 999f;
                    for (int i = 0; i <= totalSteps; i++)
                    {
                        if (ShouldAbort(generation)) return;
                        float p = -180f + i * coarseStep;
                        SetPhase(generation, p);
                        float dbm = ReadMeter(true);
                        if (dbm < fwdBestDbm) { fwdBestDbm = dbm; fwdBestPhase = WrapPhase(p); }
                    }

                    float bwdBestPhase = 180f, bwdBestDbm = 999f;
                    for (int i = 0; i <= totalSteps; i++)
                    {
                        if (ShouldAbort(generation)) return;
                        float p = 180f - i * coarseStep;
                        SetPhase(generation, p);
                        float dbm = ReadMeter(true);
                        if (dbm < bwdBestDbm) { bwdBestDbm = dbm; bwdBestPhase = WrapPhase(p); }
                    }

                    float trueNull = (fwdBestPhase + bwdBestPhase) / 2f;
                    if (Math.Abs(fwdBestPhase - bwdBestPhase) > 180f)
                    {
                        trueNull = (fwdBestPhase + bwdBestPhase + 360f) / 2f;
                        if (trueNull > 180f) trueNull -= 360f;
                    }
                    float bestPhase = WrapPhase(trueNull);
                    SetPhase(generation, bestPhase);
                    Thread.Sleep(400);
                    float bestSmeter = ReadMeter(true);
                    Report("ULTRA NULL — fwd " + fwdBestPhase.ToString("F1", CultureInfo.InvariantCulture) +
                        "°, bwd " + bwdBestPhase.ToString("F1", CultureInfo.InvariantCulture) +
                        "°, true " + bestPhase.ToString("F1", CultureInfo.InvariantCulture) + "°");

                    float currentGainDb = GetNonReferenceGainDb();
                    float bestGainDb = currentGainDb;
                    for (float offset = -gainRangeDb; offset <= gainRangeDb + 0.0001f; offset += gainStepDb)
                    {
                        if (ShouldAbort(generation)) return;
                        float gDb = currentGainDb + offset;
                        SetGain(generation, (float)Math.Pow(10.0, gDb / 20.0));
                        Thread.Sleep(gainSettle);
                        float dbm = ReadMeter(true);
                        if (dbm < bestSmeter) { bestSmeter = dbm; bestGainDb = gDb; }
                    }
                    SetGain(generation, (float)Math.Pow(10.0, bestGainDb / 20.0));
                    SetPhase(generation, bestPhase);

                    float improvement = MeasureImprovement(generation, true, 500, out float offDbm, out float onDbm);
                    if (ShouldAbort(generation)) return;
                    Complete(generation, "ULTRA NULL DONE — phase " + bestPhase.ToString("F1", CultureInfo.InvariantCulture) +
                        "°, gain " + bestGainDb.ToString("F1", CultureInfo.InvariantCulture) + " dB, improvement " +
                        improvement.ToString("F1", CultureInfo.InvariantCulture) + " dB");
                }
                catch (Exception ex)
                {
                    Complete(generation, "ULTRA NULL ERROR — " + ex.Message);
                }
            });
        }
    }
}
