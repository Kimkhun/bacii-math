// SymPy-sampled reference graph + graph-drawing assessment models.
// Mirrors GraphSpec / GraphCheck / GraphGradeResult in web/src/lib/api.ts.

class GraphPoint {
  final double x;
  final double y;
  final String? label;

  GraphPoint({required this.x, required this.y, this.label});

  factory GraphPoint.fromJson(Map<String, dynamic> json) => GraphPoint(
        x: (json['x'] as num?)?.toDouble() ?? 0,
        y: (json['y'] as num?)?.toDouble() ?? 0,
        label: json['label'] as String?,
      );
}

class AsymptoteLine {
  final String kind;
  final List<List<double>> points;
  final String line;
  final String? label;

  AsymptoteLine({
    required this.kind,
    required this.points,
    required this.line,
    this.label,
  });

  factory AsymptoteLine.fromJson(Map<String, dynamic> json) => AsymptoteLine(
        kind: json['kind'] as String? ?? '',
        points: _pointList(json['points']),
        line: json['line'] as String? ?? '',
        label: json['label'] as String?,
      );
}

List<List<double>> _pointList(dynamic raw) {
  if (raw is! List) return const [];
  return raw
      .map<List<double>>((p) =>
          (p as List).map((n) => (n as num).toDouble()).toList())
      .toList();
}

List<List<List<double>>> _segments(dynamic raw) {
  if (raw is! List) return const [];
  return raw.map<List<List<double>>>((seg) => _pointList(seg)).toList();
}

class GraphSpec {
  final double xMin;
  final double xMax;
  final double yMin;
  final double yMax;
  final List<List<List<double>>> curve; // list of segments, each a list of [x,y]
  final List<double> verticalAsymptotes;
  final List<List<double>>? tangent;
  final List<List<List<double>>>? tangents;
  final List<AsymptoteLine> asymptoteLines;
  final List<GraphPoint> points;

  GraphSpec({
    required this.xMin,
    required this.xMax,
    required this.yMin,
    required this.yMax,
    required this.curve,
    required this.verticalAsymptotes,
    this.tangent,
    this.tangents,
    this.asymptoteLines = const [],
    this.points = const [],
  });

  factory GraphSpec.fromJson(Map<String, dynamic> json) => GraphSpec(
        xMin: (json['x_min'] as num?)?.toDouble() ?? -10,
        xMax: (json['x_max'] as num?)?.toDouble() ?? 10,
        yMin: (json['y_min'] as num?)?.toDouble() ?? -10,
        yMax: (json['y_max'] as num?)?.toDouble() ?? 10,
        curve: _segments(json['curve']),
        verticalAsymptotes: ((json['vertical_asymptotes'] as List?) ?? [])
            .map((v) => (v as num).toDouble())
            .toList(),
        tangent: json['tangent'] != null ? _pointList(json['tangent']) : null,
        tangents:
            json['tangents'] != null ? _segments(json['tangents']) : null,
        asymptoteLines: ((json['asymptote_lines'] as List?) ?? [])
            .map((a) => AsymptoteLine.fromJson(a as Map<String, dynamic>))
            .toList(),
        points: ((json['points'] as List?) ?? [])
            .map((p) => GraphPoint.fromJson(p as Map<String, dynamic>))
            .toList(),
      );
}

class GraphCheckItem {
  final String label;
  final bool found;

  GraphCheckItem({required this.label, required this.found});

  factory GraphCheckItem.fromJson(Map<String, dynamic> json) => GraphCheckItem(
        label: json['label'] as String? ?? '',
        found: json['found'] as bool? ?? false,
      );
}

class GraphCheck {
  final List<GraphCheckItem> items;
  final int found;
  final int total;

  GraphCheck({required this.items, required this.found, required this.total});

  factory GraphCheck.fromJson(Map<String, dynamic> json) => GraphCheck(
        items: ((json['items'] as List?) ?? [])
            .map((i) => GraphCheckItem.fromJson(i as Map<String, dynamic>))
            .toList(),
        found: json['found'] as int? ?? 0,
        total: json['total'] as int? ?? 0,
      );
}

class GraphGradeResult {
  final int? score;
  final bool? curveCorrect;
  final bool? asymptotesCorrect;
  final bool? tangentCorrect;
  final bool? pointsCorrect;
  final String? feedback;
  final List<String> suggestions;
  final String? error;
  final String? message;

  GraphGradeResult({
    this.score,
    this.curveCorrect,
    this.asymptotesCorrect,
    this.tangentCorrect,
    this.pointsCorrect,
    this.feedback,
    this.suggestions = const [],
    this.error,
    this.message,
  });

  factory GraphGradeResult.fromJson(Map<String, dynamic> json) =>
      GraphGradeResult(
        score: (json['score'] as num?)?.toInt(),
        curveCorrect: json['curve_correct'] as bool?,
        asymptotesCorrect: json['asymptotes_correct'] as bool?,
        tangentCorrect: json['tangent_correct'] as bool?,
        pointsCorrect: json['points_correct'] as bool?,
        feedback: json['feedback'] as String?,
        suggestions: ((json['suggestions'] as List?) ?? [])
            .map((s) => s.toString())
            .toList(),
        error: json['error'] as String?,
        message: json['message'] as String?,
      );
}
