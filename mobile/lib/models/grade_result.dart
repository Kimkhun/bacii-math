class StepCheckLine {
  final int line;
  final String text;
  final bool checked;
  final bool? correct;
  final String? matches;
  final String? formula;
  final String? reason;

  StepCheckLine({
    required this.line,
    required this.text,
    required this.checked,
    this.correct,
    this.matches,
    this.formula,
    this.reason,
  });

  factory StepCheckLine.fromJson(Map<String, dynamic> json) {
    return StepCheckLine(
      line: json['line'] as int? ?? 0,
      text: json['text'] as String? ?? '',
      checked: json['checked'] as bool? ?? false,
      correct: json['correct'] as bool?,
      matches: json['matches'] as String?,
      formula: json['formula'] as String?,
      reason: json['reason'] as String?,
    );
  }
}

class FormulaResult {
  final String formula;
  final String label;
  final bool reached;
  final int? line;

  FormulaResult({
    required this.formula,
    required this.label,
    required this.reached,
    this.line,
  });

  factory FormulaResult.fromJson(Map<String, dynamic> json) {
    return FormulaResult(
      formula: json['formula'] as String? ?? '',
      label: json['label'] as String? ?? '',
      reached: json['reached'] as bool? ?? false,
      line: json['line'] as int?,
    );
  }
}

class StepCheck {
  final List<StepCheckLine> lineResults;
  final int? firstErrorLine;
  final bool reachedFinalAnswer;
  final List<FormulaResult> formulaBreakdown;

  StepCheck({
    required this.lineResults,
    this.firstErrorLine,
    required this.reachedFinalAnswer,
    this.formulaBreakdown = const [],
  });

  factory StepCheck.fromJson(Map<String, dynamic> json) {
    return StepCheck(
      lineResults: ((json['line_results'] as List<dynamic>?) ?? [])
          .map((l) => StepCheckLine.fromJson(l as Map<String, dynamic>))
          .toList(),
      firstErrorLine: json['first_error_line'] as int?,
      reachedFinalAnswer: json['reached_final_answer'] as bool? ?? false,
      formulaBreakdown: ((json['formula_breakdown'] as List<dynamic>?) ?? [])
          .map((f) => FormulaResult.fromJson(f as Map<String, dynamic>))
          .toList(),
    );
  }
}

class PartVerdict {
  final String label;
  final bool correct;
  final String? reason;
  final String? given;
  final String? expected;

  PartVerdict({
    required this.label,
    required this.correct,
    this.reason,
    this.given,
    this.expected,
  });

  factory PartVerdict.fromJson(Map<String, dynamic> json) {
    return PartVerdict(
      label: json['label'] as String? ?? '',
      correct: json['correct'] as bool? ?? false,
      reason: json['reason'] as String?,
      given: json['given'] as String?,
      expected: json['expected'] as String?,
    );
  }
}

class GradeResult {
  final String attemptId;
  final bool correct;
  final String reason;
  final String? given;
  final String expected;
  final List<PartVerdict> parts;
  final String? part;
  final bool? allComplete;
  final StepCheck? stepCheck;

  GradeResult({
    required this.attemptId,
    required this.correct,
    required this.reason,
    this.given,
    required this.expected,
    this.parts = const [],
    this.part,
    this.allComplete,
    this.stepCheck,
  });

  factory GradeResult.fromJson(Map<String, dynamic> json) {
    return GradeResult(
      attemptId: json['attempt_id'] as String? ?? '',
      correct: json['correct'] as bool? ?? false,
      reason: json['reason'] as String? ?? '',
      given: json['given'] as String?,
      expected: json['expected'] as String? ?? '',
      parts: ((json['parts'] as List<dynamic>?) ?? [])
          .map((p) => PartVerdict.fromJson(p as Map<String, dynamic>))
          .toList(),
      part: json['part'] as String?,
      allComplete: json['all_complete'] as bool?,
      stepCheck: json['step_check'] != null
          ? StepCheck.fromJson(json['step_check'] as Map<String, dynamic>)
          : null,
    );
  }
}
