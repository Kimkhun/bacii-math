import 'dart:math' as math;
import 'dart:typed_data';

import 'package:audioplayers/audioplayers.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Synthesized grade feedback + drawing friction sounds. Port of
/// web/src/lib/sounds.ts (grade dings/thuds) and the friction toggle from
/// web/src/lib/audioEngine.ts. Tones are synthesized to 16-bit PCM WAV at
/// runtime — no asset files — and played via audioplayers so they overlap.

const int _sampleRate = 44100;

enum _Wave { sine, triangle, sawtooth }

/// A single oscillator description within a synthesized sound.
class _ToneSpec {
  final double freq;
  final double start; // seconds from sound start
  final double duration;
  final _Wave wave;
  final double gainPeak;
  final double? endFreq;

  _ToneSpec(this.freq, this.start, this.duration,
      {this.wave = _Wave.sine, this.gainPeak = 0.25, this.endFreq});
}

double _sample(_Wave wave, double phase) {
  final t = phase % (2 * math.pi);
  switch (wave) {
    case _Wave.sine:
      return math.sin(t);
    case _Wave.triangle:
      final x = t / (2 * math.pi); // 0..1
      return 4 * (x < 0.5 ? x : 1 - x) - 1;
    case _Wave.sawtooth:
      return 2 * (t / (2 * math.pi)) - 1;
  }
}

Uint8List _renderWav(List<_ToneSpec> tones, {double? masterVolume}) {
  final vol = (masterVolume ?? 1.0).clamp(0.0, 1.0);
  double totalDur = 0;
  for (final s in tones) {
    totalDur = math.max(totalDur, s.start + s.duration + 0.06);
  }
  final n = math.max(1, (totalDur * _sampleRate).ceil());
  final buf = Float64List(n);

  for (final s in tones) {
    final startIdx = (s.start * _sampleRate).floor();
    final durSamples = math.max(1, (s.duration * _sampleRate).ceil());
    double phase = 0;
    final f0 = s.freq;
    final f1 = s.endFreq ?? s.freq;
    for (int i = 0; i < durSamples; i++) {
      final idx = startIdx + i;
      if (idx < 0 || idx >= n) continue;
      final tt = i / durSamples; // 0..1 across the tone
      // Exponential frequency glide (matches WebAudio exponentialRamp).
      final freq = f1 != f0 ? f0 * math.pow(f1 / f0, tt) : f0;
      phase += 2 * math.pi * freq / _sampleRate;
      // Gain envelope: 10ms linear attack, exponential decay to ~0.
      final tSec = i / _sampleRate;
      double gain;
      const attack = 0.01;
      if (tSec < attack) {
        gain = s.gainPeak * (tSec / attack);
      } else {
        final decayT = (tSec - attack) / math.max(1e-4, s.duration - attack);
        gain = s.gainPeak * math.pow(0.0004, decayT).toDouble();
      }
      buf[idx] += _sample(s.wave, phase) * gain;
    }
  }

  // Encode to 16-bit PCM WAV.
  final bytesPerSample = 2;
  final dataSize = n * bytesPerSample;
  final out = BytesBuilder();
  void writeStr(String s) => out.add(s.codeUnits);
  void writeU32(int v) {
    final b = ByteData(4)..setUint32(0, v, Endian.little);
    out.add(b.buffer.asUint8List());
  }

  void writeU16(int v) {
    final b = ByteData(2)..setUint16(0, v, Endian.little);
    out.add(b.buffer.asUint8List());
  }

  writeStr('RIFF');
  writeU32(36 + dataSize);
  writeStr('WAVE');
  writeStr('fmt ');
  writeU32(16);
  writeU16(1); // PCM
  writeU16(1); // mono
  writeU32(_sampleRate);
  writeU32(_sampleRate * bytesPerSample);
  writeU16(bytesPerSample);
  writeU16(16);
  writeStr('data');
  writeU32(dataSize);

  final pcm = ByteData(dataSize);
  for (int i = 0; i < n; i++) {
    var v = (buf[i] * vol).clamp(-1.0, 1.0);
    pcm.setInt16(i * 2, (v * 32767).round(), Endian.little);
  }
  out.add(pcm.buffer.asUint8List());
  return out.toBytes();
}

class SoundEngine {
  static const String _streakKey = 'bacii_streak';

  bool enabled = true;
  double volume = 0.7;

  final List<AudioPlayer> _pool = [];
  int _poolIdx = 0;

  SoundEngine() {
    for (int i = 0; i < 6; i++) {
      _pool.add(AudioPlayer(playerId: 'bacii_sfx_$i'));
    }
  }

  Future<void> _play(Uint8List wav) async {
    if (!enabled || volume <= 0) return;
    final player = _pool[_poolIdx];
    _poolIdx = (_poolIdx + 1) % _pool.length;
    try {
      await player.stop();
      await player.play(BytesSource(wav, mimeType: 'audio/wav'));
    } catch (_) {
      /* audio unavailable on this platform — ignore */
    }
  }

  // --- streak persistence (matches web localStorage) ---
  static Future<int> getStreak() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getInt(_streakKey) ?? 0;
    return raw > 0 ? raw : 0;
  }

  static Future<int> updateStreak(bool correct) async {
    final prefs = await SharedPreferences.getInstance();
    final next = correct ? (await getStreak()) + 1 : 0;
    await prefs.setInt(_streakKey, next);
    return next;
  }

  // One correct mark: bright ping `step` semitones above base (cap octave),
  // octave shimmer, plus a grace note from step 3 on.
  void playMarkSound(bool correct, int step) {
    if (correct) {
      final steps = step.clamp(0, 12);
      final base = 440 * math.pow(2, steps / 12).toDouble();
      final tones = <_ToneSpec>[
        _ToneSpec(base, 0, 0.35, wave: _Wave.sine, gainPeak: 0.22),
        _ToneSpec(base * 2, 0, 0.28, wave: _Wave.sine, gainPeak: 0.08),
      ];
      if (steps >= 3) {
        tones.add(_ToneSpec(base / 2, 0, 0.18,
            wave: _Wave.triangle, gainPeak: 0.1, endFreq: base * 0.75));
      }
      _play(_renderWav(tones, masterVolume: volume));
    } else {
      _play(_renderWav([
        _ToneSpec(165, 0, 0.28, wave: _Wave.sawtooth, gainPeak: 0.12, endFreq: 110),
        _ToneSpec(82, 0.05, 0.32, wave: _Wave.sine, gainPeak: 0.15, endFreq: 60),
      ], masterVolume: volume));
    }
  }

  Future<void> playGradeSound(bool correct) async {
    playMarkSound(correct, correct ? await getStreak() : 0);
  }

  void playSuccessChime() {
    // Rising major arpeggio.
    _play(_renderWav([
      _ToneSpec(523.25, 0, 0.3, gainPeak: 0.18),
      _ToneSpec(659.25, 0.08, 0.3, gainPeak: 0.18),
      _ToneSpec(783.99, 0.16, 0.4, gainPeak: 0.2),
    ], masterVolume: volume));
  }

  bool toggle() {
    enabled = !enabled;
    return enabled;
  }

  // Friction audio (drawing) is a no-op stub on mobile — kept so the settings
  // popover's "Test Pencil" affordance has something to call. A soft tick is
  // played once instead of continuous synthesis.
  void start(String tool, double x, double y) {}
  void move(double x, double y, double speed) {}
  void stop() {}

  void dispose() {
    for (final p in _pool) {
      p.dispose();
    }
  }
}

/// Global instance (mirrors the web `drawingAudio` singleton).
final SoundEngine drawingAudio = SoundEngine();
