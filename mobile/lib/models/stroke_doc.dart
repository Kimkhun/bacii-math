class CanvasPoint {
  final double x;
  final double y;
  final double? pressure;

  CanvasPoint({required this.x, required this.y, this.pressure});

  Map<String, dynamic> toJson() => {
    'x': x,
    'y': y,
    if (pressure != null) 'pressure': pressure,
  };

  factory CanvasPoint.fromJson(Map<String, dynamic> json) => CanvasPoint(
    x: (json['x'] as num).toDouble(),
    y: (json['y'] as num).toDouble(),
    pressure: json['pressure'] != null ? (json['pressure'] as num).toDouble() : null,
  );
}

class CanvasStroke {
  final String kind; // 'path', 'line', 'curve', 'ellipse'
  final List<CanvasPoint> points;
  final String tool; // 'pen', 'eraser', 'ruler', etc.
  final double width;
  final String? pointerType;

  CanvasStroke({
    required this.kind,
    required this.points,
    required this.tool,
    required this.width,
    this.pointerType,
  });

  Map<String, dynamic> toJson() => {
    'kind': kind,
    'points': points.map((p) => p.toJson()).toList(),
    'tool': tool,
    'width': width,
    if (pointerType != null) 'pointerType': pointerType,
  };

  factory CanvasStroke.fromJson(Map<String, dynamic> json) => CanvasStroke(
    kind: json['kind'] as String? ?? 'path',
    points: ((json['points'] as List<dynamic>?) ?? [])
        .map((p) => CanvasPoint.fromJson(p as Map<String, dynamic>))
        .toList(),
    tool: json['tool'] as String? ?? 'pen',
    width: (json['width'] as num?)?.toDouble() ?? 2.0,
    pointerType: json['pointerType'] as String?,
  );
}

class StrokeDocument {
  final int version;
  final List<CanvasStroke> strokes;

  StrokeDocument({this.version = 1, required this.strokes});

  Map<String, dynamic> toJson() => {
    'version': version,
    'strokes': strokes.map((s) => s.toJson()).toList(),
  };

  factory StrokeDocument.fromJson(Map<String, dynamic> json) => StrokeDocument(
    version: json['version'] as int? ?? 1,
    strokes: ((json['strokes'] as List<dynamic>?) ?? [])
        .map((s) => CanvasStroke.fromJson(s as Map<String, dynamic>))
        .toList(),
  );
}
