import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../models/graph.dart';

/// Renders a SymPy-sampled reference graph. Port of web FunctionGraph.tsx.
class FunctionGraph extends StatelessWidget {
  final GraphSpec graph;
  final double height;

  const FunctionGraph({super.key, required this.graph, this.height = 240});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final w = constraints.maxWidth.isFinite ? constraints.maxWidth : 340.0;
        return SizedBox(
          width: w,
          height: height,
          child: CustomPaint(
            painter: _GraphPainter(graph),
            size: Size(w, height),
          ),
        );
      },
    );
  }
}

class _GraphPainter extends CustomPainter {
  final GraphSpec g;
  _GraphPainter(this.g);

  @override
  void paint(Canvas canvas, Size size) {
    const pad = 26.0;
    final w = size.width;
    final h = size.height;
    canvas.drawRect(Rect.fromLTWH(0, 0, w, h),
        Paint()..color = const Color(0xFFFFFFFF));

    final xr = (g.xMax - g.xMin) == 0 ? 1 : (g.xMax - g.xMin);
    final yr = (g.yMax - g.yMin) == 0 ? 1 : (g.yMax - g.yMin);
    double xTo(double x) => pad + ((x - g.xMin) / xr) * (w - 2 * pad);
    double yTo(double y) => h - pad - ((y - g.yMin) / yr) * (h - 2 * pad);

    final axisX = yTo(0);
    final axisY = xTo(0);
    bool inX(double v) => v >= g.xMin && v <= g.xMax;
    bool inY(double v) => v >= g.yMin && v <= g.yMax;

    final range = math.max(g.xMax - g.xMin, g.yMax - g.yMin);
    final step = range <= 12 ? 1.0 : (range <= 24 ? 2.0 : 5.0);
    final xTicks = <double>[];
    final yTicks = <double>[];
    for (double v = (g.xMin / step).ceil() * step; v <= g.xMax; v += step) {
      xTicks.add(v);
    }
    for (double v = (g.yMin / step).ceil() * step; v <= g.yMax; v += step) {
      yTicks.add(v);
    }

    final gridPaint = Paint()
      ..color = const Color(0xFFEEF2F7)
      ..strokeWidth = 1;
    for (final v in xTicks) {
      canvas.drawLine(Offset(xTo(v), pad), Offset(xTo(v), h - pad), gridPaint);
    }
    for (final v in yTicks) {
      canvas.drawLine(Offset(pad, yTo(v)), Offset(w - pad, yTo(v)), gridPaint);
    }

    final axisPaint = Paint()
      ..color = const Color(0xFF334155)
      ..strokeWidth = 1.5;
    canvas.drawLine(Offset(pad, axisX), Offset(w - pad, axisX), axisPaint);
    canvas.drawLine(Offset(axisY, pad), Offset(axisY, h - pad), axisPaint);

    void text(String s, double x, double y, {double size = 9, Color color = const Color(0xFF64748B), TextAlign align = TextAlign.center, bool bold = false}) {
      final tp = TextPainter(
        text: TextSpan(
            text: s,
            style: TextStyle(
                color: color,
                fontSize: size,
                fontWeight: bold ? FontWeight.bold : FontWeight.normal)),
        textDirection: TextDirection.ltr,
      )..layout();
      double ox = x;
      if (align == TextAlign.center) ox = x - tp.width / 2;
      if (align == TextAlign.right) ox = x - tp.width;
      tp.paint(canvas, Offset(ox, y - tp.height / 2));
    }

    text('x', w - pad + 6, axisX, color: const Color(0xFF334155), size: 12, bold: true, align: TextAlign.left);
    text('y', axisY, pad - 2, color: const Color(0xFF334155), size: 12, bold: true);
    String fmtTick(double v) =>
        v == v.roundToDouble() ? v.toInt().toString() : v.toString();
    for (final v in xTicks) {
      if (v == 0 || !inX(v)) continue;
      text(fmtTick(v), xTo(v), axisX + 12);
    }
    for (final v in yTicks) {
      if (v == 0 || !inY(v)) continue;
      text(fmtTick(v), axisY - 6, yTo(v), align: TextAlign.right);
    }

    // vertical asymptotes
    final vaPaint = Paint()
      ..color = const Color(0xFFDC2626)
      ..strokeWidth = 1.5;
    for (final v in g.verticalAsymptotes) {
      if (!inX(v)) continue;
      _dashedLine(canvas, Offset(xTo(v), pad), Offset(xTo(v), h - pad), vaPaint);
    }

    // oblique / horizontal asymptote lines
    for (final al in g.asymptoteLines) {
      if (al.points.length < 2) continue;
      final p1 = al.points[0];
      final p2 = al.points[1];
      canvas.drawLine(Offset(xTo(p1[0]), yTo(p1[1])),
          Offset(xTo(p2[0]), yTo(p2[1])), vaPaint..strokeWidth = 1.3);
    }

    // curve
    final curvePaint = Paint()
      ..color = const Color(0xFF2563EB)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.2
      ..strokeJoin = StrokeJoin.round;
    for (final seg in g.curve) {
      if (seg.isEmpty) continue;
      final path = Path()..moveTo(xTo(seg[0][0]), yTo(seg[0][1]));
      for (int i = 1; i < seg.length; i++) {
        path.lineTo(xTo(seg[i][0]), yTo(seg[i][1]));
      }
      canvas.drawPath(path, curvePaint);
    }

    // tangents
    final tanPaint = Paint()
      ..color = const Color(0xFF16A34A)
      ..strokeWidth = 2;
    final tangents = (g.tangents != null && g.tangents!.isNotEmpty)
        ? g.tangents!
        : (g.tangent != null ? [g.tangent!] : const <List<List<double>>>[]);
    for (final t in tangents) {
      if (t.length < 2) continue;
      canvas.drawLine(Offset(xTo(t[0][0]), yTo(t[0][1])),
          Offset(xTo(t[1][0]), yTo(t[1][1])), tanPaint);
    }

    // labeled points
    final ptPaint = Paint()..color = const Color(0xFF334155);
    for (final p in g.points) {
      if (!inX(p.x) || !inY(p.y)) continue;
      canvas.drawCircle(Offset(xTo(p.x), yTo(p.y)), 3.2, ptPaint);
      if (p.label != null && p.label!.isNotEmpty) {
        text(p.label!, xTo(p.x) + 12, yTo(p.y) - 10,
            size: 11, color: const Color(0xFF334155), bold: true, align: TextAlign.left);
      }
    }
  }

  void _dashedLine(Canvas canvas, Offset a, Offset b, Paint paint) {
    const dash = 6.0;
    const gap = 4.0;
    final total = (b - a).distance;
    final dir = (b - a) / total;
    double d = 0;
    while (d < total) {
      final start = a + dir * d;
      final end = a + dir * math.min(d + dash, total);
      canvas.drawLine(start, end, paint);
      d += dash + gap;
    }
  }

  @override
  bool shouldRepaint(covariant _GraphPainter old) => old.g != g;
}
