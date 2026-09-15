import 'dart:convert';
import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

import '../../models/stroke_doc.dart';

/// Full handwriting canvas — Flutter port of web/src/components/Canvas.tsx.
/// Tools: pen (pressure), eraser, ruler (straight line), curve (smooth
/// freehand), ellipse, select (move shapes/images), axes (coordinate grid).
/// Supports pinch-zoom + two-finger pan, undo/redo, infinite-paper growth,
/// PNG/thumbnail export for OCR, and stroke serialization for save/resume.

enum CanvasTool { pen, eraser, ruler, curve, ellipse, select, axes }

const double kFullW = 1600;
const double kFullH = 1000;
const Map<String, double> kPenWidths = {'thin': 3, 'medium': 6, 'thick': 10};
const double kDefaultPenWidth = 6;
const double kDefaultEraserWidth = 32;

const Color _paperColor = Color(0xFFFDFCF8);
const Color _lineColor = Color(0xD9D6DDE8);
const Color _marginColor = Color(0xE6E6C9C4);
const Color _inkColor = Color(0xFF1E2A38);
const double _lineSpacing = 40;
const double _marginX = 64;
const double _growChunk = 700;
const double _growThreshold = 220;
const double _maxDim = 12000;

// --------------------------------------------------------------------------
// Painting helpers (shared by the on-screen painter and offscreen export)
// --------------------------------------------------------------------------

void _paintRuled(Canvas canvas, double w, double h, GridState? grid) {
  canvas.drawRect(
      Rect.fromLTWH(0, 0, w, h), Paint()..color = _paperColor);
  if (grid != null) {
    _paintGrid(canvas, w, h, grid);
    return;
  }
  final margin = Paint()
    ..color = _marginColor
    ..strokeWidth = 1;
  canvas.drawLine(Offset(_marginX, 0), Offset(_marginX, h), margin);
  final rule = Paint()
    ..color = _lineColor
    ..strokeWidth = 1;
  for (double y = _lineSpacing; y < h; y += _lineSpacing) {
    canvas.drawLine(Offset(0, y), Offset(w, y), rule);
  }
}

void _paintGrid(Canvas canvas, double w, double h, GridState g) {
  final dx = g.stepX * g.scale;
  final dy = g.stepY * g.scale;
  if (dx <= 0 || dy <= 0) return;
  String fmt(double v) {
    final r = double.parse(v.toStringAsFixed(2));
    return r == r.roundToDouble() ? r.toInt().toString() : r.toString();
  }

  final left = (g.ox / dx).ceil();
  final right = ((w - g.ox) / dx).ceil();
  final up = (g.oy / dy).ceil();
  final down = ((h - g.oy) / dy).ceil();

  final minor = Paint()
    ..color = const Color(0x0D0F172A)
    ..strokeWidth = 1;
  for (int i = -2 * left - 1; i <= 2 * right + 1; i++) {
    if (i % 2 == 0) continue;
    final x = g.ox + (i / 2) * dx;
    canvas.drawLine(Offset(x, 0), Offset(x, h), minor);
  }
  for (int i = -2 * down - 1; i <= 2 * up + 1; i++) {
    if (i % 2 == 0) continue;
    final y = g.oy - (i / 2) * dy;
    canvas.drawLine(Offset(0, y), Offset(w, y), minor);
  }
  final major = Paint()
    ..color = const Color(0x1A0F172A)
    ..strokeWidth = 1;
  for (int i = -left; i <= right; i++) {
    final x = g.ox + i * dx;
    canvas.drawLine(Offset(x, 0), Offset(x, h), major);
  }
  for (int i = -down; i <= up; i++) {
    final y = g.oy - i * dy;
    canvas.drawLine(Offset(0, y), Offset(w, y), major);
  }
  final axis = Paint()
    ..color = const Color(0xFF1E293B)
    ..strokeWidth = 1.5;
  canvas.drawLine(Offset(0, g.oy), Offset(w, g.oy), axis);
  canvas.drawLine(Offset(g.ox, 0), Offset(g.ox, h), axis);

  final tickPaint = Paint()
    ..color = const Color(0xFF334155)
    ..strokeWidth = 1;
  const tick = 5.0;
  for (int i = -left; i <= right; i++) {
    if (i == 0) continue;
    final x = g.ox + i * dx;
    canvas.drawLine(Offset(x, g.oy - tick), Offset(x, g.oy + tick), tickPaint);
  }
  for (int i = -down; i <= up; i++) {
    if (i == 0) continue;
    final y = g.oy - i * dy;
    canvas.drawLine(Offset(g.ox - tick, y), Offset(g.ox + tick, y), tickPaint);
  }

  void label(String text, double x, double y, {TextAlign align = TextAlign.center}) {
    final tp = TextPainter(
      text: TextSpan(
          text: text,
          style: const TextStyle(color: Color(0xFF334155), fontSize: 11)),
      textDirection: TextDirection.ltr,
      textAlign: align,
    )..layout();
    double ox = x;
    if (align == TextAlign.center) ox = x - tp.width / 2;
    if (align == TextAlign.right) ox = x - tp.width;
    tp.paint(canvas, Offset(ox, y));
  }

  for (int i = -left; i <= right; i++) {
    if (i == 0) continue;
    label(fmt(i * g.stepX), g.ox + i * dx, g.oy + 6);
  }
  for (int i = -down; i <= up; i++) {
    if (i == 0) continue;
    label(fmt(i * g.stepY), g.ox - 5, g.oy - i * dy - 6, align: TextAlign.right);
  }
  label('0', g.ox + 6, g.oy + 6, align: TextAlign.left);
}

Path _smoothPath(List<CanvasPoint> pts) {
  final path = Path();
  if (pts.isEmpty) return path;
  path.moveTo(pts[0].x, pts[0].y);
  if (pts.length == 2) {
    path.lineTo(pts[1].x, pts[1].y);
    return path;
  }
  for (int i = 1; i < pts.length - 1; i++) {
    final midX = (pts[i].x + pts[i + 1].x) / 2;
    final midY = (pts[i].y + pts[i + 1].y) / 2;
    path.quadraticBezierTo(pts[i].x, pts[i].y, midX, midY);
  }
  final last = pts.last;
  path.lineTo(last.x, last.y);
  return path;
}

const double _pressureMin = 0.55;
const double _pressureMax = 1.25;

void _paintPressure(Canvas canvas, List<CanvasPoint> pts, double baseWidth,
    Paint paint) {
  double widthAt(CanvasPoint p) {
    final pr = p.pressure ?? 0.5;
    final scale = _pressureMin + pr * (_pressureMax - _pressureMin);
    return math.max(1.0, baseWidth * scale);
  }

  if (pts.length == 1) {
    canvas.drawCircle(Offset(pts[0].x, pts[0].y), widthAt(pts[0]) / 2,
        Paint()..color = paint.color..blendMode = paint.blendMode);
    return;
  }
  var prevMid = pts[0];
  for (int i = 0; i < pts.length - 1; i++) {
    final p0 = pts[i];
    final p1 = pts[i + 1];
    final mid = i == pts.length - 2
        ? p1
        : CanvasPoint(x: (p0.x + p1.x) / 2, y: (p0.y + p1.y) / 2);
    final seg = Path()
      ..moveTo(prevMid.x, prevMid.y)
      ..quadraticBezierTo(p0.x, p0.y, mid.x, mid.y);
    canvas.drawPath(seg, paint..strokeWidth = widthAt(p0));
    prevMid = mid;
  }
}

Path _curvePath(CurveStroke stroke) {
  final a = stroke.anchors;
  final path = Path();
  if (a.isEmpty) return path;
  path.moveTo(a[0].p.x, a[0].p.y);
  for (int i = 0; i < a.length - 1; i++) {
    final p0 = a[i];
    final p1 = a[i + 1];
    path.cubicTo(p0.hOut.x, p0.hOut.y, p1.hIn.x, p1.hIn.y, p1.p.x, p1.p.y);
  }
  return path;
}

void _paintStroke(Canvas canvas, CanvasStroke stroke) {
  if (stroke is ImageStroke) {
    final img = stroke.decoded;
    if (img != null) {
      final src = Rect.fromLTWH(
          0, 0, img.width.toDouble(), img.height.toDouble());
      final dst = Rect.fromLTWH(stroke.x, stroke.y, stroke.w, stroke.h);
      canvas.drawImageRect(img, src, dst, Paint());
    }
    return;
  }
  if (stroke is RasterStroke) {
    final src = Rect.fromLTWH(
        0, 0, stroke.image.width.toDouble(), stroke.image.height.toDouble());
    final dst = Rect.fromLTWH(0, 0, stroke.w, stroke.h);
    canvas.drawImageRect(stroke.image, src, dst, Paint());
    return;
  }
  if (stroke is RectStroke) {
    canvas.drawRect(
      Rect.fromLTRB(stroke.x1, stroke.y1, stroke.x2, stroke.y2),
      Paint()..blendMode = BlendMode.clear,
    );
    return;
  }

  double width;
  bool eraser = false;
  if (stroke is PathStroke) {
    width = stroke.width;
    eraser = stroke.tool == 'eraser';
  } else if (stroke is LineStroke) {
    width = stroke.width;
  } else if (stroke is CurveStroke) {
    width = stroke.width;
  } else if (stroke is EllipseStroke) {
    width = stroke.width;
  } else {
    return;
  }

  final paint = Paint()
    ..style = PaintingStyle.stroke
    ..strokeCap = StrokeCap.round
    ..strokeJoin = StrokeJoin.round
    ..strokeWidth = width;
  if (eraser) {
    paint.blendMode = BlendMode.clear;
  } else {
    paint.color = _inkColor;
  }

  if (stroke is LineStroke) {
    canvas.drawLine(
        Offset(stroke.x1, stroke.y1), Offset(stroke.x2, stroke.y2), paint);
  } else if (stroke is CurveStroke) {
    if (stroke.anchors.length == 1) {
      canvas.drawCircle(Offset(stroke.anchors[0].p.x, stroke.anchors[0].p.y),
          width / 2, Paint()..color = _inkColor);
    } else {
      canvas.drawPath(_curvePath(stroke), paint);
    }
  } else if (stroke is EllipseStroke) {
    canvas.drawOval(
      Rect.fromCenter(
          center: Offset(stroke.cx, stroke.cy),
          width: math.max(1.0, stroke.rx.abs()) * 2,
          height: math.max(1.0, stroke.ry.abs()) * 2),
      paint,
    );
  } else if (stroke is PathStroke) {
    if (stroke.points.isEmpty) return;
    if (stroke.tool == 'pen' && stroke.pointerType == 'pen') {
      _paintPressure(canvas, stroke.points, width, paint);
    } else if (stroke.points.length == 1) {
      canvas.drawCircle(Offset(stroke.points[0].x, stroke.points[0].y),
          width / 2, Paint()..color = paint.color..blendMode = paint.blendMode);
    } else {
      canvas.drawPath(_smoothPath(stroke.points), paint);
    }
  }
}

/// Draws every stroke onto an isolated layer so eraser (BlendMode.clear)
/// removes ink without touching the paper/grid drawn underneath.
void _paintInk(Canvas canvas, Rect bounds, List<CanvasStroke> strokes) {
  canvas.saveLayer(bounds, Paint());
  for (final s in strokes) {
    _paintStroke(canvas, s);
  }
  canvas.restore();
}

// --------------------------------------------------------------------------
// Controller
// --------------------------------------------------------------------------

class DrawingCanvasController extends ChangeNotifier {
  double w = kFullW;
  double h = kFullH;
  List<CanvasStroke> _strokes = [];
  List<CanvasStroke> _redo = [];
  GridState? grid;

  CanvasTool tool = CanvasTool.pen;
  double penWidth = kDefaultPenWidth;
  double eraserWidth = kDefaultEraserWidth;

  double zoom = 1.0;
  Offset offset = Offset.zero;

  int? selected;

  List<CanvasStroke> get strokes => List.unmodifiable(_strokes);
  bool get hasInk => _strokes.isNotEmpty;
  bool get canUndo => _strokes.isNotEmpty;
  bool get canRedo => _redo.isNotEmpty;
  bool get hasGrid => grid != null;

  void setTool(CanvasTool t) {
    tool = t;
    if (t != CanvasTool.select) selected = null;
    notifyListeners();
  }

  void setPenWidth(double v) {
    penWidth = v;
    notifyListeners();
  }

  void setEraserWidth(double v) {
    eraserWidth = v;
    notifyListeners();
  }

  void setZoom(double z) {
    zoom = z.clamp(0.4, 2.5);
    notifyListeners();
  }

  // --- stroke management ---
  void addStroke(CanvasStroke s) {
    _strokes.add(s);
    _redo = [];
  }

  void undo() {
    if (_strokes.isEmpty) return;
    _redo.add(_strokes.removeLast());
    notifyListeners();
  }

  void redo() {
    if (_redo.isEmpty) return;
    _strokes.add(_redo.removeLast());
    notifyListeners();
  }

  void clear() {
    _strokes = [];
    _redo = [];
    grid = null;
    selected = null;
    w = kFullW;
    h = kFullH;
    offset = Offset.zero;
    notifyListeners();
  }

  void eraseRegion(List<double> box) {
    if (box.length != 4) return;
    _redo = [];
    _strokes.add(RectStroke(x1: box[0], y1: box[1], x2: box[2], y2: box[3]));
    notifyListeners();
  }

  // --- grid ---
  void spawnGrid(double stepX, double stepY, {Offset? origin, double? scale}) {
    if (stepX <= 0 || stepY <= 0) return;
    grid = GridState(
      ox: origin?.dx ?? w / 2,
      oy: origin?.dy ?? h / 2,
      stepX: stepX,
      stepY: stepY,
      scale: (scale != null && scale > 0) ? scale : 40,
    );
    notifyListeners();
  }

  void setGridSteps(double stepX, double stepY) {
    if (grid == null || stepX <= 0 || stepY <= 0) return;
    grid!.stepX = stepX;
    grid!.stepY = stepY;
    notifyListeners();
  }

  void setGridScale(double scale) {
    if (grid == null || scale <= 0) return;
    grid!.scale = scale;
    notifyListeners();
  }

  void moveGrid(double ox, double oy) {
    if (grid == null) return;
    grid!.ox = ox;
    grid!.oy = oy;
    notifyListeners();
  }

  void hideGrid() {
    grid = null;
    notifyListeners();
  }

  void fitGridToWindow(double xMin, double xMax, double yMin, double yMax) {
    final ww = xMax - xMin;
    final wh = yMax - yMin;
    if (ww <= 0 || wh <= 0) return;
    final scale =
        math.max(10, math.min(200, math.min(w / ww, h / wh) * 0.9));
    grid = GridState(
      ox: w / 2 - ((xMin + xMax) / 2) * scale,
      oy: h / 2 + ((yMin + yMax) / 2) * scale,
      stepX: grid?.stepX ?? 1,
      stepY: grid?.stepY ?? 1,
      scale: scale.toDouble(),
    );
    notifyListeners();
  }

  // --- serialization ---
  StrokeDocument? getStrokes() {
    if (_strokes.isEmpty) return null;
    return StrokeDocument(
      width: w,
      height: h,
      strokes: _strokes.map((s) => s.copy()).toList(),
      redoStack: _redo.map((s) => s.copy()).toList(),
      grid: grid?.copy(),
    );
  }

  Future<void> loadStrokes(StrokeDocument doc) async {
    _strokes = doc.strokes.map((s) => s.copy()).toList();
    _redo = doc.redoStack.map((s) => s.copy()).toList();
    grid = doc.grid?.copy();
    if (doc.width > 0) w = math.min(_maxDim, doc.width);
    if (doc.height > 0) h = math.min(_maxDim, doc.height);
    selected = null;
    await _decodeImages();
    notifyListeners();
  }

  Future<void> loadImageStroke(Uint8List bytes) async {
    final img = await _decode(bytes);
    if (img == null) return;
    final maxW = w - 64;
    final maxH = h - 64;
    final scale = math.min(
        1.0, math.min(maxW / img.width, maxH / img.height));
    final iw = img.width * scale;
    final ih = img.height * scale;
    final priorImages = _strokes.whereType<ImageStroke>().length;
    final cascade = (priorImages % 6) * 28.0;
    final stroke = ImageStroke(
      src: 'data:image/png;base64,${base64Encode(bytes)}',
      x: (w - iw) / 2 + cascade,
      y: (h - ih) / 2 + cascade,
      w: iw,
      h: ih,
      decoded: img,
    );
    _strokes.add(stroke);
    _redo = [];
    selected = _strokes.length - 1;
    tool = CanvasTool.select;
    notifyListeners();
  }

  Future<void> loadBackgroundInk(Uint8List bytes) async {
    final img = await _decode(bytes);
    if (img == null) return;
    _strokes.add(RasterStroke(
        image: img, w: img.width.toDouble(), h: img.height.toDouble()));
    _redo = [];
    notifyListeners();
  }

  Future<ui.Image?> _decode(Uint8List bytes) async {
    try {
      final codec = await ui.instantiateImageCodec(bytes);
      final frame = await codec.getNextFrame();
      return frame.image;
    } catch (_) {
      return null;
    }
  }

  Future<void> _decodeImages() async {
    for (final s in _strokes) {
      if (s is ImageStroke && s.decoded == null) {
        final prefix = s.src.indexOf(',');
        if (prefix != -1) {
          try {
            s.decoded = await _decode(base64Decode(s.src.substring(prefix + 1)));
          } catch (_) {}
        }
      }
    }
  }

  CanvasExportMap getExportMap() =>
      CanvasExportMap(canvasW: w, canvasH: h, scale: 1, offsetX: 0, offsetY: 0);

  // --- rasterization / export ---
  Future<ui.Image> _rasterizeInk({bool white = false}) async {
    await _decodeImages();
    final recorder = ui.PictureRecorder();
    final canvas = Canvas(recorder);
    final bounds = Rect.fromLTWH(0, 0, w, h);
    if (white) canvas.drawRect(bounds, Paint()..color = const Color(0xFFFFFFFF));
    _paintInk(canvas, bounds, _strokes);
    final pic = recorder.endRecording();
    return pic.toImage(w.round(), h.round());
  }

  Future<Uint8List?> _pngBytes(ui.Image img) async {
    final data = await img.toByteData(format: ui.ImageByteFormat.png);
    return data?.buffer.asUint8List();
  }

  /// White-background PNG, base64 (no data: prefix) — for OCR.
  Future<String?> getImageBase64() async {
    if (_strokes.isEmpty) return null;
    final img = await _rasterizeInk(white: true);
    final bytes = await _pngBytes(img);
    if (bytes == null) return null;
    return base64Encode(bytes);
  }

  /// Transparent-background PNG data URL — for graph grading / restore.
  Future<String?> getInkSnapshot() async {
    if (_strokes.isEmpty) return null;
    final img = await _rasterizeInk(white: false);
    final bytes = await _pngBytes(img);
    if (bytes == null) return null;
    return 'data:image/png;base64,${base64Encode(bytes)}';
  }

  /// Small white-background thumbnail data URL for history cards / save.
  Future<String?> getStrokesThumb({double maxWidth = 320}) async {
    if (_strokes.isEmpty) return null;
    final tw = math.min(maxWidth, w);
    final thInt = math.max(1, (h * tw / w).round());
    final th = thInt.toDouble();
    final recorder = ui.PictureRecorder();
    final canvas = Canvas(recorder);
    canvas.drawRect(
        Rect.fromLTWH(0, 0, tw, th), Paint()..color = const Color(0xFFFFFFFF));
    canvas.scale(tw / w, th / h);
    _paintInk(canvas, Rect.fromLTWH(0, 0, w, h), _strokes);
    final img = await recorder.endRecording().toImage(tw.round(), thInt);
    final bytes = await _pngBytes(img);
    if (bytes == null) return null;
    return 'data:image/png;base64,${base64Encode(bytes)}';
  }

  /// Per-line ink crops for the line-pop animation (logical coords).
  Future<List<LineSnapshot?>> getLineSnapshots(List<List<double>?> boxes) async {
    if (_strokes.isEmpty) return List.filled(boxes.length, null);
    final full = await _rasterizeInk(white: false);
    const pad = 6.0;
    final out = <LineSnapshot?>[];
    for (final b in boxes) {
      if (b == null || b.length != 4) {
        out.add(null);
        continue;
      }
      final sx = math.max(0.0, b[0] - pad);
      final sy = math.max(0.0, b[1] - pad);
      final sw = math.min(w, b[2] + pad) - sx;
      final sh = math.min(h, b[3] + pad) - sy;
      if (sw <= 0 || sh <= 0) {
        out.add(null);
        continue;
      }
      final recorder = ui.PictureRecorder();
      final canvas = Canvas(recorder);
      canvas.drawImageRect(
        full,
        Rect.fromLTWH(sx, sy, sw, sh),
        Rect.fromLTWH(0, 0, sw, sh),
        Paint(),
      );
      final img = await recorder.endRecording().toImage(sw.round(), sh.round());
      final bytes = await _pngBytes(img);
      out.add(bytes == null
          ? null
          : LineSnapshot(x: sx, y: sy, w: sw, h: sh, bytes: bytes));
    }
    return out;
  }

  void grow(CanvasPoint p) {
    bool changed = false;
    if (h - p.y <= _growThreshold && h < _maxDim) {
      h = math.min(_maxDim, h + _growChunk);
      changed = true;
    }
    if (w - p.x <= _growThreshold && w < _maxDim) {
      w = math.min(_maxDim, w + _growChunk);
      changed = true;
    }
    if (changed) notifyListeners();
  }

  void touched() => notifyListeners();
}

// --------------------------------------------------------------------------
// Widget
// --------------------------------------------------------------------------

class DrawingCanvas extends StatefulWidget {
  final DrawingCanvasController controller;
  final VoidCallback? onChange;
  final Widget? Function(CanvasExportMap map)? overlayBuilder;

  const DrawingCanvas({
    super.key,
    required this.controller,
    this.onChange,
    this.overlayBuilder,
  });

  @override
  State<DrawingCanvas> createState() => _DrawingCanvasState();
}

class _DrawingCanvasState extends State<DrawingCanvas> {
  final Map<int, Offset> _pointers = {};
  int? _drawingPointer;
  bool _stylusActive = false;

  // pinch state
  double? _pinchStartDist;
  double _pinchStartZoom = 1;
  Offset _pinchStartOffset = Offset.zero;
  Offset _pinchCenter = Offset.zero;

  DrawingCanvasController get c => widget.controller;

  @override
  void initState() {
    super.initState();
    c.addListener(_onChange);
  }

  @override
  void dispose() {
    c.removeListener(_onChange);
    super.dispose();
  }

  void _onChange() {
    if (mounted) setState(() {});
  }

  CanvasPoint _toContent(Offset local, {double? pressure}) {
    final p = (local - c.offset) / c.zoom;
    return CanvasPoint(x: p.dx, y: p.dy, pressure: pressure);
  }

  bool _isStylus(ui.PointerDeviceKind kind) =>
      kind == ui.PointerDeviceKind.stylus ||
      kind == ui.PointerDeviceKind.invertedStylus;
  bool _isTouch(ui.PointerDeviceKind kind) => kind == ui.PointerDeviceKind.touch;

  void _onPointerDown(PointerDownEvent e) {
    _pointers[e.pointer] = e.localPosition;
    if (_isStylus(e.kind)) _stylusActive = true;

    if (_pointers.length >= 2) {
      _cancelDrawingStroke();
      _startPinch();
      return;
    }

    // Palm rejection: while a stylus is active, ignore touch input for drawing.
    if (_stylusActive && _isTouch(e.kind)) return;

    _beginStroke(e);
  }

  void _onPointerMove(PointerMoveEvent e) {
    if (_pointers.containsKey(e.pointer)) {
      _pointers[e.pointer] = e.localPosition;
    }
    if (_pinchStartDist != null && _pointers.length >= 2) {
      _updatePinch();
      return;
    }
    if (_drawingPointer == e.pointer) {
      _appendPoint(e);
    }
  }

  void _onPointerUp(PointerUpEvent e) {
    _pointers.remove(e.pointer);
    if (_isStylus(e.kind)) _stylusActive = false;
    if (_drawingPointer == e.pointer) {
      _endStroke();
    }
    if (_pointers.length < 2) _pinchStartDist = null;
  }

  void _onPointerCancel(PointerCancelEvent e) {
    _pointers.remove(e.pointer);
    if (_drawingPointer == e.pointer) _endStroke();
    if (_pointers.length < 2) _pinchStartDist = null;
  }

  // --- pinch/pan ---
  void _startPinch() {
    final pts = _pointers.values.toList();
    if (pts.length < 2) return;
    _pinchStartDist = (pts[0] - pts[1]).distance;
    _pinchCenter = (pts[0] + pts[1]) / 2;
    _pinchStartZoom = c.zoom;
    _pinchStartOffset = c.offset;
  }

  void _updatePinch() {
    final pts = _pointers.values.toList();
    if (pts.length < 2 || _pinchStartDist == null || _pinchStartDist == 0) {
      return;
    }
    final dist = (pts[0] - pts[1]).distance;
    final center = (pts[0] + pts[1]) / 2;
    final newZoom = (_pinchStartZoom * dist / _pinchStartDist!).clamp(0.4, 2.5);
    // keep content point under the pinch center stable, plus follow drag.
    final contentPt = (_pinchCenter - _pinchStartOffset) / _pinchStartZoom;
    final newOffset = center - contentPt * newZoom;
    c.zoom = newZoom;
    c.offset = newOffset;
    c.touched();
  }

  // --- drawing ---
  void _beginStroke(PointerDownEvent e) {
    final pressure = _isStylus(e.kind) ? e.pressure : null;
    final pt = _toContent(e.localPosition, pressure: pressure);
    final pointerType = _isStylus(e.kind)
        ? 'pen'
        : (_isTouch(e.kind) ? 'touch' : 'mouse');

    switch (c.tool) {
      case CanvasTool.axes:
        // tap moves the origin
        if (c.grid != null) c.moveGrid(pt.x, pt.y);
        return;
      case CanvasTool.select:
        final hit = _hitTestShape(pt);
        c.selected = hit;
        _drawingPointer = e.pointer;
        _dragLast = pt;
        c.touched();
        return;
      case CanvasTool.pen:
      case CanvasTool.eraser:
        c.addStroke(PathStroke(
          points: [pt],
          tool: c.tool == CanvasTool.eraser ? 'eraser' : 'pen',
          width: c.tool == CanvasTool.eraser ? c.eraserWidth : c.penWidth,
          pointerType: pointerType,
        ));
        break;
      case CanvasTool.ruler:
        c.addStroke(LineStroke(
            x1: pt.x, y1: pt.y, x2: pt.x, y2: pt.y, width: c.penWidth));
        break;
      case CanvasTool.curve:
        _curveSamples = [pt];
        c.addStroke(CurveStroke(anchors: [
          CurveAnchor(p: pt.copy(), hIn: pt.copy(), hOut: pt.copy())
        ], width: c.penWidth));
        break;
      case CanvasTool.ellipse:
        _ellipseStart = pt;
        c.addStroke(EllipseStroke(
            cx: pt.x, cy: pt.y, rx: 0, ry: 0, width: c.penWidth));
        break;
    }
    _drawingPointer = e.pointer;
    c.touched();
  }

  List<CanvasPoint> _curveSamples = [];
  CanvasPoint? _ellipseStart;
  CanvasPoint? _dragLast;

  void _appendPoint(PointerMoveEvent e) {
    final pressure = _isStylus(e.kind) ? e.pressure : null;
    final pt = _toContent(e.localPosition, pressure: pressure);
    if (c.strokes.isEmpty && c.tool != CanvasTool.select) return;

    switch (c.tool) {
      case CanvasTool.select:
        if (c.selected != null && _dragLast != null) {
          _moveShape(c.selected!, pt.x - _dragLast!.x, pt.y - _dragLast!.y);
          _dragLast = pt;
        }
        break;
      case CanvasTool.pen:
      case CanvasTool.eraser:
        final s = c.strokes.last;
        if (s is PathStroke) s.points.add(pt);
        c.grow(pt);
        break;
      case CanvasTool.ruler:
        final s = c.strokes.last;
        if (s is LineStroke) {
          s.x2 = pt.x;
          s.y2 = pt.y;
        }
        break;
      case CanvasTool.curve:
        _curveSamples.add(pt);
        final s = c.strokes.last;
        if (s is CurveStroke) {
          // live preview: straight line start→current with a mid bend.
          final start = _curveSamples.first;
          final bend = _farthest(_curveSamples, start, pt);
          s.anchors
            ..clear()
            ..addAll(_anchorsFrom([start, bend, pt]));
        }
        break;
      case CanvasTool.ellipse:
        final s = c.strokes.last;
        if (s is EllipseStroke && _ellipseStart != null) {
          s.cx = (_ellipseStart!.x + pt.x) / 2;
          s.cy = (_ellipseStart!.y + pt.y) / 2;
          s.rx = (pt.x - _ellipseStart!.x).abs() / 2;
          s.ry = (pt.y - _ellipseStart!.y).abs() / 2;
        }
        break;
      case CanvasTool.axes:
        break;
    }
    c.touched();
  }

  void _endStroke() {
    _drawingPointer = null;
    _dragLast = null;
    if (c.tool == CanvasTool.curve && _curveSamples.length > 2) {
      final s = c.strokes.isNotEmpty ? c.strokes.last : null;
      if (s is CurveStroke) {
        s.anchors
          ..clear()
          ..addAll(_anchorsFrom(_downsample(_curveSamples)));
      }
    }
    _curveSamples = [];
    _ellipseStart = null;
    widget.onChange?.call();
    c.touched();
  }

  void _cancelDrawingStroke() {
    if (_drawingPointer != null &&
        c.strokes.isNotEmpty &&
        c.tool != CanvasTool.select &&
        c.tool != CanvasTool.axes) {
      // remove the just-started in-progress stroke
      c.undo();
      c._redo.clear();
    }
    _drawingPointer = null;
    _curveSamples = [];
    _ellipseStart = null;
  }

  // --- shape helpers ---
  int? _hitTestShape(CanvasPoint p) {
    for (int i = c.strokes.length - 1; i >= 0; i--) {
      final s = c.strokes[i];
      if (s is ImageStroke) {
        if (p.x >= s.x && p.x <= s.x + s.w && p.y >= s.y && p.y <= s.y + s.h) {
          return i;
        }
      } else if (s is EllipseStroke) {
        final dx = (p.x - s.cx) / math.max(1, s.rx.abs());
        final dy = (p.y - s.cy) / math.max(1, s.ry.abs());
        if (dx * dx + dy * dy <= 1.3) return i;
      } else if (s is CurveStroke) {
        for (final a in s.anchors) {
          if ((p.x - a.p.x).abs() < 24 && (p.y - a.p.y).abs() < 24) return i;
        }
      }
    }
    return null;
  }

  void _moveShape(int index, double dx, double dy) {
    if (index < 0 || index >= c.strokes.length) return;
    final s = c.strokes[index];
    if (s is ImageStroke) {
      s.x += dx;
      s.y += dy;
    } else if (s is EllipseStroke) {
      s.cx += dx;
      s.cy += dy;
    } else if (s is CurveStroke) {
      for (final a in s.anchors) {
        a.p.x += dx;
        a.p.y += dy;
        a.hIn.x += dx;
        a.hIn.y += dy;
        a.hOut.x += dx;
        a.hOut.y += dy;
      }
    } else if (s is LineStroke) {
      s.x1 += dx;
      s.y1 += dy;
      s.x2 += dx;
      s.y2 += dy;
    } else if (s is PathStroke) {
      for (final pt in s.points) {
        pt.x += dx;
        pt.y += dy;
      }
    }
  }

  CanvasPoint _farthest(List<CanvasPoint> samples, CanvasPoint a, CanvasPoint b) {
    var best = a;
    var bestDist = 0.0;
    final len = math.sqrt(math.pow(b.x - a.x, 2) + math.pow(b.y - a.y, 2));
    for (final s in samples) {
      double d;
      if (len < 1e-6) {
        d = math.sqrt(math.pow(s.x - a.x, 2) + math.pow(s.y - a.y, 2));
      } else {
        final t = (((s.x - a.x) * (b.x - a.x) + (s.y - a.y) * (b.y - a.y)) /
                (len * len))
            .clamp(0.0, 1.0);
        final px = a.x + t * (b.x - a.x);
        final py = a.y + t * (b.y - a.y);
        d = math.sqrt(math.pow(s.x - px, 2) + math.pow(s.y - py, 2));
      }
      if (d > bestDist) {
        bestDist = d;
        best = s;
      }
    }
    return best;
  }

  List<CanvasPoint> _downsample(List<CanvasPoint> points) {
    if (points.isEmpty) return [];
    const minDist = 14.0;
    final kept = <CanvasPoint>[points.first];
    for (int i = 1; i < points.length; i++) {
      final l = kept.last;
      if (math.sqrt(
              math.pow(points[i].x - l.x, 2) + math.pow(points[i].y - l.y, 2)) >=
          minDist) {
        kept.add(points[i]);
      }
    }
    if (kept.length == 1) kept.add(points.last);
    const maxN = 80;
    if (kept.length > maxN) {
      final step = (kept.length - 1) / (maxN - 1);
      final out = <CanvasPoint>[kept.first];
      for (int i = 1; i < maxN - 1; i++) {
        out.add(kept[(i * step).round()]);
      }
      out.add(kept.last);
      return out;
    }
    return kept;
  }

  List<CurveAnchor> _anchorsFrom(List<CanvasPoint> pts) {
    final n = pts.length;
    final out = <CurveAnchor>[];
    for (int i = 0; i < n; i++) {
      final p = pts[i];
      CanvasPoint hIn, hOut;
      if (n == 1) {
        hIn = p.copy();
        hOut = p.copy();
      } else if (i == 0) {
        final dx = (pts[1].x - pts[0].x) / 3;
        final dy = (pts[1].y - pts[0].y) / 3;
        hIn = CanvasPoint(x: p.x, y: p.y);
        hOut = CanvasPoint(x: p.x + dx, y: p.y + dy);
      } else if (i == n - 1) {
        final dx = (pts[n - 1].x - pts[n - 2].x) / 3;
        final dy = (pts[n - 1].y - pts[n - 2].y) / 3;
        hIn = CanvasPoint(x: p.x - dx, y: p.y - dy);
        hOut = CanvasPoint(x: p.x, y: p.y);
      } else {
        final mx = (pts[i + 1].x - pts[i - 1].x) / 6;
        final my = (pts[i + 1].y - pts[i - 1].y) / 6;
        hIn = CanvasPoint(x: p.x - mx, y: p.y - my);
        hOut = CanvasPoint(x: p.x + mx, y: p.y + my);
      }
      out.add(CurveAnchor(p: p.copy(), hIn: hIn, hOut: hOut));
    }
    return out;
  }

  @override
  Widget build(BuildContext context) {
    final overlay = widget.overlayBuilder?.call(c.getExportMap());
    return ClipRect(
      child: Container(
        color: const Color(0xFFF2F1ED),
        child: Listener(
          behavior: HitTestBehavior.opaque,
          onPointerDown: _onPointerDown,
          onPointerMove: _onPointerMove,
          onPointerUp: _onPointerUp,
          onPointerCancel: _onPointerCancel,
          child: Transform(
            transform: Matrix4.identity()
              ..setEntry(0, 0, c.zoom)
              ..setEntry(1, 1, c.zoom)
              ..setEntry(0, 3, c.offset.dx)
              ..setEntry(1, 3, c.offset.dy),
            child: SizedBox(
              width: c.w,
              height: c.h,
              child: Stack(
                clipBehavior: Clip.none,
                children: [
                  CustomPaint(
                    size: Size(c.w, c.h),
                    painter: _CanvasPainter(c),
                  ),
                  if (overlay != null)
                    SizedBox(width: c.w, height: c.h, child: overlay),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _CanvasPainter extends CustomPainter {
  final DrawingCanvasController c;
  _CanvasPainter(this.c) : super(repaint: c);

  @override
  void paint(Canvas canvas, Size size) {
    final bounds = Rect.fromLTWH(0, 0, c.w, c.h);
    _paintRuled(canvas, c.w, c.h, c.grid);
    _paintInk(canvas, bounds, c.strokes);
    // selection outline
    final sel = c.selected;
    if (sel != null && sel >= 0 && sel < c.strokes.length) {
      final s = c.strokes[sel];
      final p = Paint()
        ..style = PaintingStyle.stroke
        ..color = const Color(0xFF0EA5E9)
        ..strokeWidth = 1.5;
      if (s is ImageStroke) {
        canvas.drawRect(Rect.fromLTWH(s.x, s.y, s.w, s.h), p);
      } else if (s is EllipseStroke) {
        canvas.drawRect(
            Rect.fromCenter(
                center: Offset(s.cx, s.cy),
                width: s.rx.abs() * 2 + 12,
                height: s.ry.abs() * 2 + 12),
            p);
      }
    }
  }

  @override
  bool shouldRepaint(covariant _CanvasPainter old) => true;
}
