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

      segments.add(_MathSegment(
        text: mathContent,
        isMath: true,
        isDisplay: isDisplay,
      ));

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

  _MathSegment({
    required this.text,
    required this.isMath,
    this.isDisplay = false,
  });
}
