import 'dart:math' as math;
import 'package:flutter/material.dart';

import '../models/detect_result.dart';
import '../models/grade_result.dart';
import '../models/stroke_doc.dart';

/// Red-pen teacher marks drawn over the canvas ink, in logical (W×H) coords —
/// port of buildMarks()/buildWriting() from web/src/app/practice/page.tsx.
class MarksOverlay extends StatelessWidget {
  final DetectResult det;
  final GradeResult result;
  final CanvasExportMap map;

  const MarksOverlay({
    super.key,
    required this.det,
    required this.result,
    required this.map,
  });

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      size: Size(map.canvasW, map.canvasH),
      painter: _MarksPainter(det, result, map),
    );
  }
}

class _Rect4 {
  final double x1, y1, x2, y2;
  _Rect4(this.x1, this.y1, this.x2, this.y2);
}

class _MarksPainter extends CustomPainter {
  final DetectResult det;
  final GradeResult res;
  final CanvasExportMap map;

  _MarksPainter(this.det, this.res, this.map);

  _Rect4? _rectOf(int i) {
    if (i < 0 || i >= det.linesBoxes.length) return null;
    final b = det.linesBoxes[i];
    if (b == null || b.length != 4) return null;
    return _Rect4(
      map.offsetX + b[0] * map.scale,
      map.offsetY + b[1] * map.scale,
      map.offsetX + b[2] * map.scale,
      map.offsetY + b[3] * map.scale,
    );
  }

  void _text(Canvas canvas, String s, Offset pos, double size, Color color,
      {TextAlign anchor = TextAlign.left, bool bold = true, bool halo = true}) {
    if (halo) {
      final haloTp = TextPainter(
        text: TextSpan(
            text: s,
            style: TextStyle(
              fontSize: size,
              fontWeight: bold ? FontWeight.w800 : FontWeight.normal,
              foreground: Paint()
                ..style = PaintingStyle.stroke
                ..strokeWidth = 6
                ..strokeJoin = StrokeJoin.round
                ..color = const Color(0xFFFFFFFF),
            )),
        textDirection: TextDirection.ltr,
      )..layout();
      double hx = pos.dx;
      if (anchor == TextAlign.center) hx = pos.dx - haloTp.width / 2;
      if (anchor == TextAlign.right) hx = pos.dx - haloTp.width;
      haloTp.paint(canvas, Offset(hx, pos.dy - haloTp.height / 2));
    }
    final tp = TextPainter(
      text: TextSpan(
          text: s,
          style: TextStyle(
              color: color,
              fontSize: size,
              fontWeight: bold ? FontWeight.w800 : FontWeight.normal)),
      textDirection: TextDirection.ltr,
    )..layout();
    double x = pos.dx;
    if (anchor == TextAlign.center) x = pos.dx - tp.width / 2;
    if (anchor == TextAlign.right) x = pos.dx - tp.width;
    tp.paint(canvas, Offset(x, pos.dy - tp.height / 2));
  }

  @override
  void paint(Canvas canvas, Size size) {
    final check = res.stepCheck;
    final lines = det.lines;

    for (int i = 0; i < lines.length; i++) {
      final r = _rectOf(i);
      if (r == null) continue;
      StepCheckLine? lineRes;
      if (check != null) {
        for (final l in check.lineResults) {
          if (l.line == i + 1) {
            lineRes = l;
            break;
          }
        }
      }
      if (lineRes == null || !lineRes.checked) continue;
      final hgt = r.y2 - r.y1;
      final fs = math.min(math.max(22, hgt * 0.85), 42).toDouble();

      // pick a free spot: right, else left, else below.
      double sx;
      double sy = (r.y1 + r.y2) / 2;
      TextAlign anchor;
      if (r.x2 + 16 + 28 <= map.canvasW - 8) {
        sx = r.x2 + 16;
        anchor = TextAlign.left;
      } else if (r.x1 - 16 - 28 >= 8) {
        sx = r.x1 - 16;
        anchor = TextAlign.right;
      } else {
        sx = r.x1;
        sy = r.y2 + 22;
        anchor = TextAlign.left;
      }

      if (lineRes.correct == true) {
        _text(canvas, '✓', Offset(sx, sy), fs, const Color(0xFF16A34A),
            anchor: anchor);
      } else {
        // red ellipse around the line
        canvas.drawOval(
          Rect.fromCenter(
            center: Offset((r.x1 + r.x2) / 2, (r.y1 + r.y2) / 2),
            width: (r.x2 - r.x1) + 20,
            height: hgt + 16,
          ),
          Paint()
            ..style = PaintingStyle.stroke
            ..color = const Color(0xFFDC2626)
            ..strokeWidth = 3.5,
        );
        _text(canvas, '✗', Offset(sx, sy), fs, const Color(0xFFDC2626),
            anchor: anchor);
        final label = lineRes.formula?.replaceAll('_', ' ');
        if (label != null && label.isNotEmpty) {
          final lfs = math.min(math.max(16, hgt * 0.5), 24).toDouble();
          final lx = anchor == TextAlign.left ? sx + 38 : sx - 6;
          _text(canvas, label, Offset(lx, sy), lfs, const Color(0xFFDC2626),
              anchor: anchor, bold: true);
        }
      }
    }

    // teacher stamp
    if (res.correct) {
      _text(canvas, '✓ Correct!', Offset(map.canvasW - 28, 70), 40,
          const Color(0xFF16A34A), anchor: TextAlign.right);
    } else {
      final err = check?.firstErrorLine;
      final r = err != null ? _rectOf(err - 1) : null;
      if (r != null) {
        _text(canvas, 'Check line $err', Offset(r.x1, r.y2 + 48), 28,
            const Color(0xFFDC2626), anchor: TextAlign.left);
      } else {
        _text(canvas, '✗ Incorrect', Offset(map.canvasW - 28, 70), 40,
            const Color(0xFFDC2626), anchor: TextAlign.right);
      }
    }
  }

  @override
  bool shouldRepaint(covariant _MarksPainter old) =>
      old.det != det || old.res != res;
}
