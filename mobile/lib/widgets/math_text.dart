import 'package:flutter/material.dart';
import 'package:flutter_math_fork/flutter_math.dart';

class MathText extends StatelessWidget {
  final String text;
  final TextStyle? textStyle;
  final MathStyle mathStyle;
  final TextAlign textAlign;

  const MathText({
    super.key,
    required this.text,
    this.textStyle,
    this.mathStyle = MathStyle.text,
    this.textAlign = TextAlign.start,
  });

  /// Segregates Khmer/plain text from LaTeX math segments as required by
  /// Cambodian BAC II rendering rules (never pass raw Khmer to TeX).
  List<_MathSegment> _parseSegments(String input) {
    if (input.isEmpty) return [];

    // Normalize \( ... \) and \[ ... \] to $ ... $ and $$ ... $$
    String normalized = input
        .replaceAll(r'\(', r'$')
        .replaceAll(r'\)', r'$')
        .replaceAll(r'\[', r'$$')
        .replaceAll(r'\]', r'$$');

    // Auto-wrap bare math formulas that lack delimiters
    if (!normalized.contains(r'$') &&
        RegExp(r'\\(lim|frac|int|sqrt|log|ln|infty|to|pm|times|div|cdot|approx|neq|le|ge|[a-zA-Z]+)\b')
            .hasMatch(normalized)) {
      normalized = normalized.replaceAllMapped(
        RegExp(
          r'((?:\\[a-zA-Z]+(?:\{[^{}]*\}|\[[^[\]]*\]|_\{[^{}]*\}|\^[^{}]*\}|_[a-zA-Z0-9\+\-]+|\^[a-zA-Z0-9\+\-]+|[ \t]*=[ \t]*|[ \t]*\+[ \t]*|[ \t]*\-[ \t]*|[ \t]*\*[ \t]*|[ \t]*\/[ \t]*|[a-zA-Z0-9\(\)\+\-\*\/\,\. ])*)+)',
        ),
        (m) {
          final s = m[1]?.trim() ?? '';
          if (RegExp(r'\\(lim|frac|int|sqrt|log|ln|infty|to|pm|times|div|cdot|approx|neq|le|ge)').hasMatch(s)) {
            return ' \$$s\$ ';
          }
          return m[1] ?? '';
        },
      );
    }

    final segments = <_MathSegment>[];
    // Match $$...$$ or $...$
    final pattern = RegExp(r'(\$\$[\s\S]*?\$\$|\$[^$\n]*?\$)');
    int lastIndex = 0;

    for (final match in pattern.allMatches(normalized)) {
      if (match.start > lastIndex) {
        final plainText = normalized.substring(lastIndex, match.start);
        if (plainText.isNotEmpty) {
          segments.add(_MathSegment(text: plainText, isMath: false));
        }
      }

      String mathContent = match.group(0) ?? '';
      bool isDisplay = mathContent.startsWith(r'$$');
      if (isDisplay) {
        mathContent = mathContent.substring(2, mathContent.length - 2).trim();
      } else {
        mathContent = mathContent.substring(1, mathContent.length - 1).trim();
      }

      // A top-level `\\` is a line break (multi-line exam prompts); flutter_math
      // can't parse it in inline math. Inside \begin{...} it belongs to the
      // environment, so leave those alone.
      final lines = mathContent.contains(r'\begin{')
          ? [mathContent]
          : mathContent.split(RegExp(r'\\\\(\[[^\]]*\])?'));
      for (int li = 0; li < lines.length; li++) {
        if (li > 0) segments.add(_MathSegment.lineBreak());
        final line = lines[li].trim();
        if (line.isNotEmpty) segments.addAll(_splitKhmerText(line, isDisplay));
      }

      lastIndex = match.end;
    }

    if (lastIndex < normalized.length) {
      final remaining = normalized.substring(lastIndex);
      if (remaining.isNotEmpty) {
        segments.add(_MathSegment(text: remaining, isMath: false));
      }
    }

    return segments;
  }

  static final RegExp _khmer = RegExp('[\u1780-\u17FF\u19E0-\u19FF]');

  /// flutter_math lays glyphs out one by one, which breaks Khmer shaping, so
  /// a `\text{...}` run containing Khmer is pulled out of the TeX and shown as
  /// plain text between the math pieces (like web's latexToMixedText).
  /// `\left`/`\right` are dropped from split math since a delimiter pair may
  /// now straddle two pieces.
  static List<_MathSegment> _splitKhmerText(String math, bool isDisplay) {
    if (!math.contains(r'\text{') || !_khmer.hasMatch(math)) {
      return [_MathSegment(text: math, isMath: true, isDisplay: isDisplay)];
    }
    final out = <_MathSegment>[];
    void addMath(String m) {
      var cleaned = m
          .replaceAll(RegExp(r'\\(left|right)\s*\.'), '')
          .replaceAll(RegExp(r'\\(left|right)(?![a-zA-Z])'), '')
          .trim();
      // A control space (`\ `) before the removed text leaves a lone `\`.
      if (cleaned.endsWith(r'\')) cleaned = cleaned.substring(0, cleaned.length - 1).trim();
      if (cleaned.isNotEmpty) {
        out.add(_MathSegment(text: cleaned, isMath: true, isDisplay: isDisplay));
      }
    }

    int i = 0;
    var pendingMath = StringBuffer();
    while (i < math.length) {
      final start = math.indexOf(r'\text{', i);
      if (start == -1) {
        pendingMath.write(math.substring(i));
        break;
      }
      // Find the matching close brace of \text{...}.
      int depth = 1, j = start + 6;
      while (j < math.length && depth > 0) {
        if (math[j] == '{') depth++;
        if (math[j] == '}') depth--;
        j++;
      }
      final inner = math.substring(start + 6, depth == 0 ? j - 1 : j);
      if (_khmer.hasMatch(inner)) {
        pendingMath.write(math.substring(i, start));
        addMath(pendingMath.toString());
        pendingMath = StringBuffer();
        if (inner.trim().isNotEmpty) out.add(_MathSegment(text: inner.trim(), isMath: false));
      } else {
        pendingMath.write(math.substring(i, j)); // Latin \text{} is fine in TeX
      }
      i = j;
    }
    addMath(pendingMath.toString());
    return out;
  }

  @override
  Widget build(BuildContext context) {
    final defaultStyle = textStyle ??
        Theme.of(context).textTheme.bodyMedium?.copyWith(
              fontSize: 15,
              height: 1.5,
              color: const Color(0xFF1E293B),
            ) ??
        const TextStyle(fontSize: 15, height: 1.5);

    final segments = _parseSegments(text);
    if (segments.isEmpty) {
      return const SizedBox.shrink();
    }

    // Split at line breaks; one Wrap per line.
    final lines = <List<_MathSegment>>[[]];
    for (final seg in segments) {
      if (seg.isLineBreak) {
        lines.add([]);
      } else {
        lines.last.add(seg);
      }
    }
    lines.removeWhere((l) => l.isEmpty);
    if (lines.length > 1) {
      return Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: textAlign == TextAlign.center
            ? CrossAxisAlignment.center
            : (textAlign == TextAlign.right ? CrossAxisAlignment.end : CrossAxisAlignment.start),
        children: [for (final l in lines) _line(l, defaultStyle)],
      );
    }
    return _line(lines.isEmpty ? const [] : lines.first, defaultStyle);
  }

  Widget _line(List<_MathSegment> segments, TextStyle defaultStyle) {
    return Wrap(
      alignment: textAlign == TextAlign.center
          ? WrapAlignment.center
          : (textAlign == TextAlign.right ? WrapAlignment.end : WrapAlignment.start),
      crossAxisAlignment: WrapCrossAlignment.center,
      spacing: 3.0,
      runSpacing: 4.0,
      children: segments.map((seg) {
        if (!seg.isMath) {
          return Text(
            seg.text,
            style: defaultStyle,
          );
        }

        try {
          return Math.tex(
            seg.text,
            mathStyle: seg.isDisplay ? MathStyle.display : mathStyle,
            textStyle: defaultStyle.copyWith(
              fontSize: (defaultStyle.fontSize ?? 15) * 1.05,
              fontWeight: FontWeight.w500,
            ),
            onErrorFallback: (err) {
              return Text(
                '\$${seg.text}\$',
                style: defaultStyle.copyWith(fontFamily: 'monospace', color: Colors.blueGrey),
              );
            },
          );
        } catch (_) {
          return Text(
            '\$${seg.text}\$',
            style: defaultStyle.copyWith(fontFamily: 'monospace'),
          );
        }
      }).toList(),
    );
  }
}

class _MathSegment {
  final String text;
  final bool isMath;
  final bool isDisplay;
  final bool isLineBreak;

  _MathSegment({
    required this.text,
    required this.isMath,
    this.isDisplay = false,
  }) : isLineBreak = false;

  _MathSegment.lineBreak()
      : text = '',
        isMath = false,
        isDisplay = false,
        isLineBreak = true;
}
