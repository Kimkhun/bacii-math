/// OCR handwriting-detection response. Mirrors DetectResult in
/// web/src/lib/api.ts. `linesBoxes` are in the exported-image (canvas logical)
/// coordinate space; `linesAlt`/`linesAltLatex` drive the disambiguation card.
class DetectResult {
  final List<String> lines;
  final List<String> linesLatex;
  final String rawText;
  final String latex;
  final List<String> tokens;
  final double confidence;
  final String? provider;
  final List<List<double>?> linesBoxes;
  final List<double> linesConfidence;
  final List<List<String>> linesAlt;
  final List<List<String>> linesAltLatex;

  DetectResult({
    this.lines = const [],
    this.linesLatex = const [],
    this.rawText = '',
    this.latex = '',
    this.tokens = const [],
    this.confidence = 0,
    this.provider,
    this.linesBoxes = const [],
    this.linesConfidence = const [],
    this.linesAlt = const [],
    this.linesAltLatex = const [],
  });

  DetectResult copyWith({
    List<String>? lines,
    List<String>? linesLatex,
  }) =>
      DetectResult(
        lines: lines ?? this.lines,
        linesLatex: linesLatex ?? this.linesLatex,
        rawText: rawText,
        latex: latex,
        tokens: tokens,
        confidence: confidence,
        provider: provider,
        linesBoxes: linesBoxes,
        linesConfidence: linesConfidence,
        linesAlt: linesAlt,
        linesAltLatex: linesAltLatex,
      );

  static List<double>? _box(dynamic raw) {
    if (raw is! List) return null;
    return raw.map((n) => (n as num).toDouble()).toList();
  }

  factory DetectResult.fromJson(Map<String, dynamic> json) => DetectResult(
        lines: ((json['lines'] as List?) ?? []).map((e) => e.toString()).toList(),
        linesLatex:
            ((json['lines_latex'] as List?) ?? []).map((e) => e.toString()).toList(),
        rawText: json['raw_text'] as String? ?? '',
        latex: json['latex'] as String? ?? '',
        tokens: ((json['tokens'] as List?) ?? []).map((e) => e.toString()).toList(),
        confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
        provider: json['provider'] as String?,
        linesBoxes:
            ((json['lines_boxes'] as List?) ?? []).map((b) => _box(b)).toList(),
        linesConfidence: ((json['lines_confidence'] as List?) ?? [])
            .map((n) => (n as num).toDouble())
            .toList(),
        linesAlt: ((json['lines_alt'] as List?) ?? [])
            .map<List<String>>(
                (l) => ((l as List?) ?? []).map((e) => e.toString()).toList())
            .toList(),
        linesAltLatex: ((json['lines_alt_latex'] as List?) ?? [])
            .map<List<String>>(
                (l) => ((l as List?) ?? []).map((e) => e.toString()).toList())
            .toList(),
      );
}
