/**
 * Procedural Audio Engine for Paper Writing and Tablet Screen Friction.
 *
 * Layers 4 physical acoustic elements onto a stable warm baseline:
 * 1. Touchdown Tap: Instant dynamic plastic-on-glass nib contact click (8ms).
 * 2. Lift Release: Subtle micro-scrape tail upon pen lift (4ms).
 * 3. Hollow iPad Body Resonance: Wide-bandwidth 480Hz peaking filter (low Q = 0.85, non-metallic).
 * 4. Surface Tooth: Damped micro-grit chatter pulses layered onto the continuous baseline.
 *
 * Includes idle auto-silence watchdog (holding still = completely silent).
 */

class DrawingAudioEngine {
  private ctx: AudioContext | null = null;
  private noiseBuffer: AudioBuffer | null = null;
  private masterGain: GainNode | null = null;

  // Active baseline nodes
  private sourceNode: AudioBufferSourceNode | null = null;
  private gainNode: GainNode | null = null;
  private gritBandpass: BiquadFilterNode | null = null;
  private gritHighpass: BiquadFilterNode | null = null;
  private bodyBandpass: BiquadFilterNode | null = null;
  private bodyGain: GainNode | null = null;
  private chassisFilter: BiquadFilterNode | null = null;

  private isEnabled: boolean = true;
  private volumeLevel: number = 0.65;
  private currentMode: "pen" | "eraser" | null = null;
  private lastTime: number = 0;
  private lastPos: { x: number; y: number } | null = null;
  private smoothedVelocity: number = 0;
  private lastDirection: number = 0;
  private stillnessTimer: NodeJS.Timeout | null = null;
  private accumulatedDist: number = 0;

  constructor() {
    if (typeof window !== "undefined") {
      const savedEnabled = localStorage.getItem("bacii_canvas_sound_enabled");
      this.isEnabled = savedEnabled !== null ? savedEnabled === "true" : true;

      const savedVol = localStorage.getItem("bacii_canvas_sound_volume");
      if (savedVol !== null) {
        const parsed = parseFloat(savedVol);
        if (!isNaN(parsed) && parsed >= 0 && parsed <= 1) {
          this.volumeLevel = parsed;
        }
      }
    }
  }

  public get enabled(): boolean {
    return this.isEnabled;
  }

  public set enabled(val: boolean) {
    this.isEnabled = val;
    if (typeof window !== "undefined") {
      localStorage.setItem("bacii_canvas_sound_enabled", String(val));
    }
    if (!val) {
      this.stop();
    }
  }

  public get volume(): number {
    return this.volumeLevel;
  }

  public set volume(val: number) {
    this.volumeLevel = Math.max(0, Math.min(1, val));
    if (typeof window !== "undefined") {
      localStorage.setItem("bacii_canvas_sound_volume", String(this.volumeLevel));
    }
    if (this.masterGain && this.ctx) {
      const target = this.isEnabled ? this.volumeLevel : 0.0001;
      this.masterGain.gain.setTargetAtTime(target, this.ctx.currentTime, 0.02);
    }
  }

  public toggle(): boolean {
    this.enabled = !this.enabled;
    return this.enabled;
  }

  private initContext() {
    if (!this.ctx && typeof window !== "undefined") {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
        this.masterGain = this.ctx.createGain();
        this.masterGain.gain.setValueAtTime(this.isEnabled ? this.volumeLevel : 0.0001, this.ctx.currentTime);
        this.masterGain.connect(this.ctx.destination);
        this.createNoiseBuffer();
      }
    }
    if (this.ctx && this.ctx.state === "suspended") {
      this.ctx.resume().catch(() => {});
    }
  }

  private createNoiseBuffer() {
    if (!this.ctx) return;
    const bufferSize = this.ctx.sampleRate * 3;
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const data = buffer.getChannelData(0);

    let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
    for (let i = 0; i < bufferSize; i++) {
      const white = Math.random() * 2 - 1;
      b0 = 0.99886 * b0 + white * 0.0555179;
      b1 = 0.99332 * b1 + white * 0.0750759;
      b2 = 0.96900 * b2 + white * 0.1538520;
      b3 = 0.86650 * b3 + white * 0.3104856;
      b4 = 0.55000 * b4 + white * 0.5329522;
      b5 = -0.7616 * b5 - white * 0.0168980;
      data[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362) * 0.08;
      b6 = white * 0.115926;
    }
    this.noiseBuffer = buffer;
  }

  private playTouchdownTap(mode: "pen" | "eraser", pressure: number = 0.5) {
    if (!this.ctx || !this.masterGain || !this.noiseBuffer) return;
    const now = this.ctx.currentTime;
    const effectivePressure = Math.max(0.2, Math.min(1.0, pressure > 0 ? pressure : 0.5));

    const source = this.ctx.createBufferSource();
    source.buffer = this.noiseBuffer;

    const filter = this.ctx.createBiquadFilter();
    const gain = this.ctx.createGain();

    if (mode === "pen") {
      filter.type = "bandpass";
      filter.frequency.setValueAtTime(3200, now);
      filter.Q.setValueAtTime(1.1, now);

      const tapVol = 0.07 * (0.6 + 0.4 * effectivePressure);
      gain.gain.setValueAtTime(tapVol, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.008);
    } else {
      filter.type = "lowpass";
      filter.frequency.setValueAtTime(350, now);

      const tapVol = 0.06 * (0.6 + 0.4 * effectivePressure);
      gain.gain.setValueAtTime(tapVol, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.012);
    }

    source.connect(filter);
    filter.connect(gain);
    gain.connect(this.masterGain);
    source.start(now);
    source.stop(now + 0.015);
  }

  private playLiftRelease() {
    if (!this.ctx || !this.masterGain || !this.noiseBuffer || this.currentMode !== "pen") return;
    const now = this.ctx.currentTime;

    const source = this.ctx.createBufferSource();
    source.buffer = this.noiseBuffer;

    const filter = this.ctx.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.setValueAtTime(2600, now);
    filter.Q.setValueAtTime(1.2, now);

    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(0.025, now);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.004);

    source.connect(filter);
    filter.connect(gain);
    gain.connect(this.masterGain);
    source.start(now);
    source.stop(now + 0.006);
  }

  private dispatchMicroGrit(speed: number) {
    if (!this.ctx || !this.masterGain || !this.noiseBuffer || this.currentMode !== "pen") return;
    const now = this.ctx.currentTime;

    const source = this.ctx.createBufferSource();
    source.buffer = this.noiseBuffer;

    const filter = this.ctx.createBiquadFilter();
    filter.type = "bandpass";
    const gritFreq = 2800 + Math.random() * 600;
    filter.frequency.setValueAtTime(gritFreq, now);
    filter.Q.setValueAtTime(1.0, now);

    const gain = this.ctx.createGain();
    const gritVol = Math.min(0.035, 0.015 + speed * 0.01);
    gain.gain.setValueAtTime(gritVol, now);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.006);

    source.connect(filter);
    filter.connect(gain);
    gain.connect(this.masterGain);
    source.start(now);
    source.stop(now + 0.008);
  }

  public start(mode: "pen" | "eraser", x: number, y: number, pressure: number = 0.5) {
    if (!this.isEnabled || this.volumeLevel <= 0.01) return;
    this.initContext();
    if (!this.ctx || !this.noiseBuffer || !this.masterGain) return;

    this.stop();

    this.currentMode = mode;
    this.lastTime = performance.now();
    this.lastPos = { x, y };
    this.smoothedVelocity = 0;
    this.lastDirection = 0;
    this.accumulatedDist = 0;

    const ctx = this.ctx;
    const now = ctx.currentTime;

    this.masterGain.gain.setValueAtTime(this.isEnabled ? this.volumeLevel : 0.0001, now);

    this.playTouchdownTap(mode, pressure);

    this.sourceNode = ctx.createBufferSource();
    this.sourceNode.buffer = this.noiseBuffer;
    this.sourceNode.loop = true;

    this.gritHighpass = ctx.createBiquadFilter();
    this.gritBandpass = ctx.createBiquadFilter();
    this.bodyBandpass = ctx.createBiquadFilter();
    this.bodyGain = ctx.createGain();

    this.chassisFilter = ctx.createBiquadFilter();
    this.chassisFilter.type = "peaking";
    this.chassisFilter.frequency.setValueAtTime(480, now);
    this.chassisFilter.Q.setValueAtTime(0.85, now);
    this.chassisFilter.gain.setValueAtTime(2.5, now);

    if (mode === "pen") {
      this.gritHighpass.type = "highpass";
      this.gritHighpass.frequency.setValueAtTime(1100, now);

      this.gritBandpass.type = "bandpass";
      this.gritBandpass.frequency.setValueAtTime(2700, now);
      this.gritBandpass.Q.setValueAtTime(1.6, now);

      this.bodyBandpass.type = "bandpass";
      this.bodyBandpass.frequency.setValueAtTime(850, now);
      this.bodyBandpass.Q.setValueAtTime(1.8, now);
      this.bodyGain.gain.setValueAtTime(0.35, now);
    } else {
      this.gritHighpass.type = "highpass";
      this.gritHighpass.frequency.setValueAtTime(140, now);

      this.gritBandpass.type = "bandpass";
      this.gritBandpass.frequency.setValueAtTime(400, now);
      this.gritBandpass.Q.setValueAtTime(1.1, now);

      this.bodyBandpass.type = "bandpass";
      this.bodyBandpass.frequency.setValueAtTime(260, now);
      this.bodyBandpass.Q.setValueAtTime(1.0, now);
      this.bodyGain.gain.setValueAtTime(0.5, now);
    }

    this.gainNode = ctx.createGain();
    this.gainNode.gain.setValueAtTime(0.0001, now);

    this.sourceNode.connect(this.gritHighpass);
    this.gritHighpass.connect(this.gritBandpass);
    this.gritBandpass.connect(this.gainNode);

    this.sourceNode.connect(this.bodyBandpass);
    this.bodyBandpass.connect(this.bodyGain);
    this.bodyGain.connect(this.gainNode);

    this.gainNode.connect(this.chassisFilter);
    this.chassisFilter.connect(this.masterGain);

    this.sourceNode.start(now);
  }

  public move(x: number, y: number, pressure: number = 0.5) {
    if (!this.isEnabled || !this.ctx || !this.gainNode || !this.currentMode) return;

    if (this.stillnessTimer) {
      clearTimeout(this.stillnessTimer);
    }

    const nowTime = performance.now();
    const dt = Math.max(1, nowTime - this.lastTime);
    const audioTime = this.ctx.currentTime;

    let dist = 0;
    if (this.lastPos) {
      const dx = x - this.lastPos.x;
      const dy = y - this.lastPos.y;
      dist = Math.sqrt(dx * dx + dy * dy);
    }

    this.lastPos = { x, y };
    this.lastTime = nowTime;

    const instantVelocity = dist / dt;
    this.smoothedVelocity = this.smoothedVelocity * 0.6 + instantVelocity * 0.4;
    const speedFactor = Math.min(1.0, this.smoothedVelocity / 2.2);

    if (dist < 0.8) {
      this.gainNode.gain.setTargetAtTime(0.0001, audioTime, 0.02);
      return;
    }

    this.accumulatedDist += dist;

    if (this.accumulatedDist > 12) {
      this.dispatchMicroGrit(speedFactor);
      this.accumulatedDist = 0;
    }

    if (this.currentMode === "pen") {
      const effectivePressure = Math.max(0.2, Math.min(1.0, pressure > 0 ? pressure : 0.5));
      const targetGain = Math.max(0.0001, speedFactor * 0.25 * (0.6 + 0.4 * effectivePressure));
      this.gainNode.gain.setTargetAtTime(targetGain, audioTime, 0.025);

      if (this.gritBandpass) {
        const targetFreq = 2300 + speedFactor * 1100;
        this.gritBandpass.frequency.setTargetAtTime(targetFreq, audioTime, 0.03);
      }
    } else {
      const targetGain = Math.max(0.0001, speedFactor * 0.32);
      this.gainNode.gain.setTargetAtTime(targetGain, audioTime, 0.03);

      if (this.gritBandpass) {
        const targetFreq = 380 + speedFactor * 260;
        this.gritBandpass.frequency.setTargetAtTime(targetFreq, audioTime, 0.04);
      }
    }

    this.stillnessTimer = setTimeout(() => {
      if (this.gainNode && this.ctx) {
        this.gainNode.gain.setTargetAtTime(0.0001, this.ctx.currentTime, 0.02);
      }
    }, 40);
  }

  public stop() {
    if (this.stillnessTimer) {
      clearTimeout(this.stillnessTimer);
      this.stillnessTimer = null;
    }

    this.playLiftRelease();

    if (!this.gainNode || !this.ctx) {
      this.cleanup();
      return;
    }

    const now = this.ctx.currentTime;
    try {
      this.gainNode.gain.cancelScheduledValues(now);
      this.gainNode.gain.setValueAtTime(Math.max(0.0001, this.gainNode.gain.value), now);
      this.gainNode.gain.exponentialRampToValueAtTime(0.0001, now + 0.016);

      const oldSource = this.sourceNode;
      setTimeout(() => {
        try {
          oldSource?.stop();
          oldSource?.disconnect();
        } catch {}
      }, 30);
    } catch {
      this.cleanup();
    }

    this.currentMode = null;
    this.lastPos = null;
    this.smoothedVelocity = 0;
    this.accumulatedDist = 0;
  }

  public playSuccessChime() {
    if (!this.isEnabled || this.volumeLevel <= 0.01) return;
    this.initContext();
    if (!this.ctx || !this.masterGain) return;

    const ctx = this.ctx;
    const now = ctx.currentTime;

    const freqs = [1046.5, 1567.98];
    freqs.forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, now + idx * 0.08);

      gain.gain.setValueAtTime(0.0001, now + idx * 0.08);
      gain.gain.linearRampToValueAtTime(0.15, now + idx * 0.08 + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + idx * 0.08 + 0.45);

      osc.connect(gain);
      gain.connect(this.masterGain!);

      osc.start(now + idx * 0.08);
      osc.stop(now + idx * 0.08 + 0.5);
    });
  }

  private cleanup() {
    try {
      this.sourceNode?.stop();
      this.sourceNode?.disconnect();
    } catch {}
    this.sourceNode = null;
    this.gainNode = null;
    this.gritBandpass = null;
    this.gritHighpass = null;
    this.bodyBandpass = null;
    this.bodyGain = null;
    this.chassisFilter = null;
    this.currentMode = null;
    this.lastPos = null;
  }
}

export const drawingAudio = new DrawingAudioEngine();
