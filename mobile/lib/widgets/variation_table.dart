import 'package:flutter/material.dart';

import '../models/variation_table.dart';
import 'math_text.dart';

/// Tableau de variations (x / f'(x) / f(x) with arrows), a port of web's
/// VariationTable in web/src/components/StructureModal.tsx. Boundary columns
/// alternate with interval columns; a pole (vertical asymptote) is drawn as a
/// double bar with the one-sided limits on either side.
class VariationTableView extends StatelessWidget {
  final VariationTable vt;

  const VariationTableView({super.key, required this.vt});

  static const double _labelW = 64;
  static const double _pointW = 44;
  static const double _poleW = 80;
  static const double _intervalW = 64;
  static const double _xRowH = 34;
  static const double _signRowH = 30;
  static const double _fRowH = 92;
  static const Color _ink = Color(0xFF1E293B);

  static String _norm(String? v) {
    if (v == null) return '';
    final s = v.trim().replaceAll('∞', r'\infty');
    if (s == 'oo' || s == '+oo' || s == r'\infty' || s == r'+\infty') return r'+\infty';
    if (s == '-oo' || s == r'-\infty') return r'-\infty';
    return s;
  }

  String _at(List<String> l, int i) => i >= 0 && i < l.length ? l[i] : '';

  bool _isPole(int idx) {
    final n = vt.columns.length;
    if (idx <= 0 || idx >= n - 1) return false;
    final val = _at(vt.funcValues, idx);
    return val.contains('/') ||
        val.contains('||') ||
        (_at(vt.arrows, idx - 1) == '↘' && _at(vt.arrows, idx) == '↘');
  }

  (String, String) _poleLimits(int idx) {
    final raw = _at(vt.funcValues, idx);
    if (raw.contains('/')) {
      final p = raw.split('/').map((e) => _norm(e.trim())).toList();
      return (
        p.isNotEmpty && p[0].isNotEmpty ? p[0] : r'-\infty',
        p.length > 1 && p[1].isNotEmpty ? p[1] : r'+\infty',
      );
    }
    final left = _at(vt.arrows, idx - 1) == '↗' ? r'+\infty' : r'-\infty';
    final right = _at(vt.arrows, idx) == '↘' ? r'+\infty' : r'-\infty';
    return (left, right);
  }

  Widget _math(String latex) => MathText(
        text: latex.isEmpty ? '' : '\\($latex\\)',
        textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: _ink),
      );

  Widget _cell(double w, double h, Widget child, {bool rightBorder = false}) => Container(
        width: w,
        height: h,
        alignment: Alignment.center,
        decoration: rightBorder
            ? const BoxDecoration(border: Border(right: BorderSide(color: _ink, width: 1.2)))
            : null,
        child: child,
      );

  @override
  Widget build(BuildContext context) {
    final cols = vt.columns;
    final intervals = cols.length - 1;
    double boundaryW(int idx) => _isPole(idx) ? _poleW : _pointW;

    // Row 1: x
    final xRow = <Widget>[
      _cell(_labelW, _xRowH,
          const Text('x', style: TextStyle(fontStyle: FontStyle.italic, fontWeight: FontWeight.bold)),
          rightBorder: true),
      _cell(_pointW, _xRowH, _math(_norm(cols[0]))),
      for (int i = 0; i < intervals; i++) ...[
        const SizedBox(width: _intervalW, height: _xRowH),
        _cell(i == intervals - 1 ? _pointW : boundaryW(i + 1), _xRowH, _math(_norm(cols[i + 1]))),
      ],
    ];

    // Row 2: f'(x)
    final signRow = <Widget>[
      _cell(_labelW, _signRowH,
          const Text("f'(x)", style: TextStyle(fontWeight: FontWeight.w600)),
          rightBorder: true),
      const SizedBox(width: _pointW, height: _signRowH),
      for (int i = 0; i < intervals; i++) ...[
        Builder(builder: (_) {
          final sign = _at(vt.derivativeSign, i).isEmpty ? '+' : _at(vt.derivativeSign, i);
          return _cell(
            _intervalW,
            _signRowH,
            Text(sign,
                style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: sign == '+' ? const Color(0xFF047857) : const Color(0xFFBE123C))),
          );
        }),
        if (i == intervals - 1)
          const SizedBox(width: _pointW, height: _signRowH)
        else if (_isPole(i + 1))
          _cell(_poleW, _signRowH, const _DoubleBar(height: _signRowH))
        else
          _cell(
            _pointW,
            _signRowH,
            Stack(alignment: Alignment.center, children: [
              Container(width: 1.5, height: _signRowH, color: _ink),
              Container(
                color: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 3),
                child: const Text('0',
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: _ink)),
              ),
            ]),
          ),
      ],
    ];

    // Row 3: f(x) with arrows
    final arrow0Up = (_at(vt.arrows, 0).isEmpty ? '↗' : _at(vt.arrows, 0)) == '↗';
    final fRow = <Widget>[
      _cell(_labelW, _fRowH, const Text('f(x)', style: TextStyle(fontWeight: FontWeight.w600)),
          rightBorder: true),
      SizedBox(
        width: _pointW,
        height: _fRowH,
        child: Align(
          alignment: arrow0Up ? Alignment.bottomCenter : Alignment.topCenter,
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: _math(_norm(_at(vt.funcValues, 0))),
          ),
        ),
      ),
      for (int i = 0; i < intervals; i++) ...[
        Builder(builder: (_) {
          final up = (_at(vt.arrows, i).isEmpty ? '↗' : _at(vt.arrows, i)) == '↗';
          return SizedBox(
            width: _intervalW,
            height: _fRowH,
            child: CustomPaint(painter: _ArrowPainter(up: up)),
          );
        }),
        Builder(builder: (_) {
          final up = (_at(vt.arrows, i).isEmpty ? '↗' : _at(vt.arrows, i)) == '↗';
          final isLast = i == intervals - 1;
          final idx = i + 1;
          if (!isLast && _isPole(idx)) {
            final lim = _poleLimits(idx);
            final leftDown = _at(vt.arrows, i) == '↘';
            final rightDown = _at(vt.arrows, i + 1) == '↘';
            return SizedBox(
              width: _poleW,
              height: _fRowH,
              child: Stack(children: [
                const Center(child: _DoubleBar(height: _fRowH)),
                Positioned(
                  right: _poleW / 2 + 6,
                  top: leftDown ? null : 6,
                  bottom: leftDown ? 6 : null,
                  child: _math(lim.$1),
                ),
                Positioned(
                  left: _poleW / 2 + 6,
                  top: rightDown ? 6 : null,
                  bottom: rightDown ? null : 6,
                  child: _math(lim.$2),
                ),
              ]),
            );
          }
          return SizedBox(
            width: _pointW,
            height: _fRowH,
            child: Align(
              alignment: up ? Alignment.topCenter : Alignment.bottomCenter,
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 6),
                child: _math(_norm(_at(vt.funcValues, idx))),
              ),
            ),
          );
        }),
      ],
    ];

    const rowBorder = BoxDecoration(border: Border(bottom: BorderSide(color: _ink, width: 1.2)));
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('តារាងអថេរភាព (Variation Table)',
            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Color(0xFF475569))),
        const SizedBox(height: 6),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFFE2E8F0)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(decoration: rowBorder, child: Row(children: xRow)),
                Container(decoration: rowBorder, child: Row(children: signRow)),
                Row(children: fRow),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _DoubleBar extends StatelessWidget {
  final double height;
  const _DoubleBar({required this.height});

  @override
  Widget build(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(width: 1.5, height: height, color: VariationTableView._ink),
          const SizedBox(width: 3),
          Container(width: 1.5, height: height, color: VariationTableView._ink),
        ],
      );
}

class _ArrowPainter extends CustomPainter {
  final bool up;
  _ArrowPainter({required this.up});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = VariationTableView._ink
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke;
    final start = Offset(2, size.height * (up ? 0.76 : 0.20));
    final end = Offset(size.width - 2, size.height * (up ? 0.20 : 0.76));
    canvas.drawLine(start, end, paint);
    final dir = (end - start) / (end - start).distance;
    final normal = Offset(-dir.dy, dir.dx);
    const head = 7.0;
    final base = end - dir * head;
    final path = Path()
      ..moveTo(end.dx, end.dy)
      ..lineTo(base.dx + normal.dx * head / 2, base.dy + normal.dy * head / 2)
      ..lineTo(base.dx - normal.dx * head / 2, base.dy - normal.dy * head / 2)
      ..close();
    canvas.drawPath(path, Paint()..color = VariationTableView._ink);
  }

  @override
  bool shouldRepaint(covariant _ArrowPainter old) => old.up != up;
}
