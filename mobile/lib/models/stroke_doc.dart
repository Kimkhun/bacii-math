import 'dart:typed_data';
import 'dart:ui' as ui;

/// Serializable canvas stroke document. JSON shape matches the web
/// `StrokeDocument` (web/src/components/Canvas.tsx) so ink round-trips exactly
/// between the Flutter app, the web app, and the backend (save/resume).

class CanvasPoint {
  double x;
  double y;
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
        pressure:
            json['pressure'] != null ? (json['pressure'] as num).toDouble() : null,
      );

  CanvasPoint copy() => CanvasPoint(x: x, y: y, pressure: pressure);
}

class CurveAnchor {
  CanvasPoint p;
  CanvasPoint hIn;
  CanvasPoint hOut;

  CurveAnchor({required this.p, required this.hIn, required this.hOut});

  Map<String, dynamic> toJson() => {
        'x': p.x,
        'y': p.y,
        'hIn': {'x': hIn.x, 'y': hIn.y},
        'hOut': {'x': hOut.x, 'y': hOut.y},
      };

  factory CurveAnchor.fromJson(Map<String, dynamic> json) => CurveAnchor(
        p: CanvasPoint(
            x: (json['x'] as num).toDouble(), y: (json['y'] as num).toDouble()),
        hIn: CanvasPoint(
            x: (json['hIn']?['x'] as num?)?.toDouble() ?? 0,
            y: (json['hIn']?['y'] as num?)?.toDouble() ?? 0),
        hOut: CanvasPoint(
            x: (json['hOut']?['x'] as num?)?.toDouble() ?? 0,
            y: (json['hOut']?['y'] as num?)?.toDouble() ?? 0),
      );

  CurveAnchor copy() =>
      CurveAnchor(p: p.copy(), hIn: hIn.copy(), hOut: hOut.copy());
}

abstract class CanvasStroke {
  String get kind;
  Map<String, dynamic> toJson();
  CanvasStroke copy();

  static CanvasStroke? fromJson(Map<String, dynamic> json) {
    switch (json['kind'] as String?) {
      case 'line':
        return LineStroke.fromJson(json);
      case 'curve':
        return CurveStroke.fromJson(json);
      case 'ellipse':
        return EllipseStroke.fromJson(json);
      case 'rect':
        return RectStroke.fromJson(json);
      case 'image':
        return ImageStroke.fromJson(json);
      case 'path':
      default:
        return PathStroke.fromJson(json);
    }
  }
}

class PathStroke extends CanvasStroke {
  @override
  final String kind = 'path';
  final List<CanvasPoint> points;
  final String tool; // 'pen' | 'eraser'
  final double width;
  final String? pointerType;

  PathStroke({
    required this.points,
    required this.tool,
    required this.width,
    this.pointerType,
  });

  @override
  Map<String, dynamic> toJson() => {
        'kind': kind,
        'points': points.map((p) => p.toJson()).toList(),
        'tool': tool,
        'width': width,
        if (pointerType != null) 'pointerType': pointerType,
      };

  factory PathStroke.fromJson(Map<String, dynamic> json) => PathStroke(
        points: ((json['points'] as List?) ?? [])
            .map((p) => CanvasPoint.fromJson(p as Map<String, dynamic>))
            .toList(),
        tool: json['tool'] as String? ?? 'pen',
        width: (json['width'] as num?)?.toDouble() ?? 6,
        pointerType: json['pointerType'] as String?,
      );

  @override
  PathStroke copy() => PathStroke(
        points: points.map((p) => p.copy()).toList(),
        tool: tool,
        width: width,
        pointerType: pointerType,
      );
}

class LineStroke extends CanvasStroke {
  @override
  final String kind = 'line';
  double x1, y1, x2, y2;
  final double width;

  LineStroke({
    required this.x1,
    required this.y1,
    required this.x2,
    required this.y2,
    required this.width,
  });

  @override
  Map<String, dynamic> toJson() => {
        'kind': kind,
        'x1': x1,
        'y1': y1,
        'x2': x2,
        'y2': y2,
        'tool': 'ruler',
        'width': width,
      };

  factory LineStroke.fromJson(Map<String, dynamic> json) => LineStroke(
        x1: (json['x1'] as num?)?.toDouble() ?? 0,
        y1: (json['y1'] as num?)?.toDouble() ?? 0,
        x2: (json['x2'] as num?)?.toDouble() ?? 0,
        y2: (json['y2'] as num?)?.toDouble() ?? 0,
        width: (json['width'] as num?)?.toDouble() ?? 6,
      );

  @override
  LineStroke copy() =>
      LineStroke(x1: x1, y1: y1, x2: x2, y2: y2, width: width);
}

class CurveStroke extends CanvasStroke {
  @override
  final String kind = 'curve';
  final List<CurveAnchor> anchors;
  final double width;

  CurveStroke({required this.anchors, required this.width});

  @override
  Map<String, dynamic> toJson() => {
        'kind': kind,
        'tool': 'curve',
        'anchors': anchors.map((a) => a.toJson()).toList(),
        'width': width,
      };

  factory CurveStroke.fromJson(Map<String, dynamic> json) => CurveStroke(
        anchors: ((json['anchors'] as List?) ?? [])
            .map((a) => CurveAnchor.fromJson(a as Map<String, dynamic>))
            .toList(),
        width: (json['width'] as num?)?.toDouble() ?? 6,
      );

  @override
  CurveStroke copy() =>
      CurveStroke(anchors: anchors.map((a) => a.copy()).toList(), width: width);
}

class EllipseStroke extends CanvasStroke {
  @override
  final String kind = 'ellipse';
  double cx, cy, rx, ry;
  final double width;

  EllipseStroke({
    required this.cx,
    required this.cy,
    required this.rx,
    required this.ry,
    required this.width,
  });

  @override
  Map<String, dynamic> toJson() => {
        'kind': kind,
        'cx': cx,
        'cy': cy,
        'rx': rx,
        'ry': ry,
        'tool': 'ellipse',
        'width': width,
      };

  factory EllipseStroke.fromJson(Map<String, dynamic> json) => EllipseStroke(
        cx: (json['cx'] as num?)?.toDouble() ?? 0,
        cy: (json['cy'] as num?)?.toDouble() ?? 0,
        rx: (json['rx'] as num?)?.toDouble() ?? 0,
        ry: (json['ry'] as num?)?.toDouble() ?? 0,
        width: (json['width'] as num?)?.toDouble() ?? 6,
      );

  @override
  EllipseStroke copy() =>
      EllipseStroke(cx: cx, cy: cy, rx: rx, ry: ry, width: width);
}

class RectStroke extends CanvasStroke {
  @override
  final String kind = 'rect';
  double x1, y1, x2, y2;

  RectStroke({
    required this.x1,
    required this.y1,
    required this.x2,
    required this.y2,
  });

  @override
  Map<String, dynamic> toJson() => {
        'kind': kind,
        'rect': {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2},
      };

  factory RectStroke.fromJson(Map<String, dynamic> json) {
    final r = (json['rect'] as Map<String, dynamic>?) ?? const {};
    return RectStroke(
      x1: (r['x1'] as num?)?.toDouble() ?? 0,
      y1: (r['y1'] as num?)?.toDouble() ?? 0,
      x2: (r['x2'] as num?)?.toDouble() ?? 0,
      y2: (r['y2'] as num?)?.toDouble() ?? 0,
    );
  }

  @override
  RectStroke copy() => RectStroke(x1: x1, y1: y1, x2: x2, y2: y2);
}

class ImageStroke extends CanvasStroke {
  @override
  final String kind = 'image';
  final String src; // data URL
  double x, y, w, h;
  // Decoded image, lazily populated by the canvas painter (not serialized).
  ui.Image? decoded;

  ImageStroke({
    required this.src,
    required this.x,
    required this.y,
    required this.w,
    required this.h,
    this.decoded,
  });

  @override
  Map<String, dynamic> toJson() => {
        'kind': kind,
        'src': src,
        'x': x,
        'y': y,
        'w': w,
        'h': h,
      };

  factory ImageStroke.fromJson(Map<String, dynamic> json) => ImageStroke(
        src: json['src'] as String? ?? '',
        x: (json['x'] as num?)?.toDouble() ?? 0,
        y: (json['y'] as num?)?.toDouble() ?? 0,
        w: (json['w'] as num?)?.toDouble() ?? 0,
        h: (json['h'] as num?)?.toDouble() ?? 0,
      );

  @override
  ImageStroke copy() =>
      ImageStroke(src: src, x: x, y: y, w: w, h: h, decoded: decoded);
}

/// A restored flattened page (from loadBackgroundInk). In-memory only —
/// excluded from serialization, just like the web's RasterStroke.
class RasterStroke extends CanvasStroke {
  @override
  final String kind = 'raster';
  final ui.Image image;
  final double w;
  final double h;

  RasterStroke({required this.image, required this.w, required this.h});

  @override
  Map<String, dynamic> toJson() => {'kind': kind};

  @override
  RasterStroke copy() => this;
}

class GridState {
  double ox;
  double oy;
  double stepX;
  double stepY;
  double scale;

  GridState({
    required this.ox,
    required this.oy,
    required this.stepX,
    required this.stepY,
    required this.scale,
  });

  Map<String, dynamic> toJson() => {
        'ox': ox,
        'oy': oy,
        'stepX': stepX,
        'stepY': stepY,
        'scale': scale,
      };

  factory GridState.fromJson(Map<String, dynamic> json) => GridState(
        ox: (json['ox'] as num?)?.toDouble() ?? 0,
        oy: (json['oy'] as num?)?.toDouble() ?? 0,
        stepX: (json['stepX'] as num?)?.toDouble() ?? 1,
        stepY: (json['stepY'] as num?)?.toDouble() ?? 1,
        scale: (json['scale'] as num?)?.toDouble() ?? 40,
      );

  GridState copy() =>
      GridState(ox: ox, oy: oy, stepX: stepX, stepY: stepY, scale: scale);
}

class StrokeDocument {
  final double width;
  final double height;
  final List<CanvasStroke> strokes;
  final List<CanvasStroke> redoStack;
  final GridState? grid;

  StrokeDocument({
    required this.width,
    required this.height,
    required this.strokes,
    this.redoStack = const [],
    this.grid,
  });

  Map<String, dynamic> toJson() => {
        'width': width,
        'height': height,
        // raster strokes are not serializable (match web cloneStrokes()).
        'strokes': strokes
            .where((s) => s.kind != 'raster')
            .map((s) => s.toJson())
            .toList(),
        'redoStack': redoStack
            .where((s) => s.kind != 'raster')
            .map((s) => s.toJson())
            .toList(),
        'grid': grid?.toJson(),
      };

  factory StrokeDocument.fromJson(Map<String, dynamic> json) => StrokeDocument(
        width: (json['width'] as num?)?.toDouble() ?? 1600,
        height: (json['height'] as num?)?.toDouble() ?? 1000,
        strokes: ((json['strokes'] as List?) ?? [])
            .map((s) => CanvasStroke.fromJson(s as Map<String, dynamic>))
            .whereType<CanvasStroke>()
            .toList(),
        redoStack: ((json['redoStack'] as List?) ?? [])
            .map((s) => CanvasStroke.fromJson(s as Map<String, dynamic>))
            .whereType<CanvasStroke>()
            .toList(),
        grid: json['grid'] != null
            ? GridState.fromJson(json['grid'] as Map<String, dynamic>)
            : null,
      );
}

/// A per-line ink snapshot cut from the canvas for the "line pop" animation.
class LineSnapshot {
  final double x;
  final double y;
  final double w;
  final double h;
  final Uint8List bytes; // PNG bytes of the cropped ink

  LineSnapshot({
    required this.x,
    required this.y,
    required this.w,
    required this.h,
    required this.bytes,
  });
}

/// Maps exported-image pixel coords (OCR box space) to canvas-internal coords.
class CanvasExportMap {
  final double canvasW;
  final double canvasH;
  final double scale;
  final double offsetX;
  final double offsetY;

  CanvasExportMap({
    required this.canvasW,
    required this.canvasH,
    required this.scale,
    required this.offsetX,
    required this.offsetY,
  });
}
