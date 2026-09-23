import 'graph.dart';

class StepCheckLine {
  final int line;
  final String text;
  final bool checked;
  final bool? correct;
  final String? matches;
  final String? formula;
  final String? expected;
  final String? reason;

  StepCheckLine({
    required this.line,
    required this.text,
    required this.checked,
    this.correct,
    this.matches,
    this.formula,
    this.expected,
    this.reason,
  });

  factory StepCheckLine.fromJson(Map<String, dynamic> json) => StepCheckLine(
        line: json['line'] as int? ?? 0,
        text: json['text'] as String? ?? '',
        checked: json['checked'] as bool? ?? false,
        correct: json['correct'] as bool?,
        matches: json['matches'] as String?,
        formula: json['formula'] as String?,
        expected: json['expected'] as String?,
        reason: json['reason'] as String?,
      );
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

  factory FormulaResult.fromJson(Map<String, dynamic> json) => FormulaResult(
        formula: json['formula'] as String? ?? '',
        label: json['label'] as String? ?? '',
        reached: json['reached'] as bool? ?? false,
        line: json['line'] as int?,
      );
}

class StepCheck {
  final List<StepCheckLine> lineResults;
  final int? firstErrorLine;
  final bool reachedFinalAnswer;
  final List<FormulaResult> formulaBreakdown;

  StepCheck({
    required this.lineResults,
    this.firstErrorLine,
    this.reachedFinalAnswer = false,
    this.formulaBreakdown = const [],
  });

  factory StepCheck.fromJson(Map<String, dynamic> json) => StepCheck(
        lineResults: ((json['line_results'] as List?) ?? [])
            .map((l) => StepCheckLine.fromJson(l as Map<String, dynamic>))
            .toList(),
        firstErrorLine: json['first_error_line'] as int?,
        reachedFinalAnswer: json['reached_final_answer'] as bool? ?? false,
        formulaBreakdown: ((json['formula_breakdown'] as List?) ?? [])
            .map((f) => FormulaResult.fromJson(f as Map<String, dynamic>))
            .toList(),
      );
}

class PartVerdict {
  final String label;
  final bool correct;
  final String? reason;
  final String? given;
  final String? expected;
  final String? note;

  PartVerdict({
    required this.label,
    required this.correct,
    this.reason,
    this.given,
    this.expected,
    this.note,
  });

  factory PartVerdict.fromJson(Map<String, dynamic> json) => PartVerdict(
        label: json['label'] as String? ?? '',
        correct: json['correct'] as bool? ?? false,
        reason: json['reason'] as String?,
        given: json['given'] as String?,
        expected: json['expected'] as String?,
        note: json['note'] as String?,
      );
}

class RubricStep {
  final String item;
  final String label;
  final double pointsEarned;
  final double pointsPossible;
  final String? matchedLine;
  final bool implied;

  RubricStep({
    required this.item,
    required this.label,
    required this.pointsEarned,
    required this.pointsPossible,
    this.matchedLine,
    this.implied = false,
  });

  factory RubricStep.fromJson(Map<String, dynamic> json) => RubricStep(
        item: json['item'] as String? ?? '',
        label: json['label'] as String? ?? '',
        pointsEarned: (json['points_earned'] as num?)?.toDouble() ?? 0,
        pointsPossible: (json['points_possible'] as num?)?.toDouble() ?? 0,
        matchedLine: json['matched_line'] as String?,
        implied: json['implied'] as bool? ?? false,
      );
}

class RubricScore {
  final double earned;
  final double possible;
  final List<RubricStep> breakdown;

  RubricScore({
    required this.earned,
    required this.possible,
    required this.breakdown,
  });

  factory RubricScore.fromJson(Map<String, dynamic> json) => RubricScore(
        earned: (json['earned'] as num?)?.toDouble() ?? 0,
        possible: (json['possible'] as num?)?.toDouble() ?? 0,
        breakdown: ((json['breakdown'] as List?) ?? [])
            .map((b) => RubricStep.fromJson(b as Map<String, dynamic>))
            .toList(),
      );
}

class TextProvider {
  final String content;
  final String provider;

  TextProvider({required this.content, required this.provider});

  static TextProvider? fromJson(Map<String, dynamic>? json) {
    if (json == null) return null;
    return TextProvider(
      content: json['content'] as String? ?? '',
      provider: json['provider'] as String? ?? '',
    );
  }
}

class SolutionStep {
  final int stepOrder;
  final String title;
  final String detail;
  final String? formula;

  SolutionStep({
    required this.stepOrder,
    required this.title,
    required this.detail,
    this.formula,
  });

  factory SolutionStep.fromJson(Map<String, dynamic> json) => SolutionStep(
        stepOrder: json['step_order'] as int? ?? 1,
        title: json['title'] as String? ?? '',
        detail: json['detail'] as String? ?? '',
        formula: json['formula'] as String?,
      );
}

class Explanation {
  final String content;
  final String provider;
  final bool intervened;
  final String trigger;
  final TextProvider? workCheck;
  final TextProvider? teacherFeedback;
  final StepCheck? stepCheck;
  final List<SolutionStep> steps;
  final GraphSpec? graph;
  final GraphCheck? graphCheck;

  Explanation({
    required this.content,
    required this.provider,
    this.intervened = false,
    this.trigger = '',
    this.workCheck,
    this.teacherFeedback,
    this.stepCheck,
    this.steps = const [],
    this.graph,
    this.graphCheck,
  });

  factory Explanation.fromJson(Map<String, dynamic> json) => Explanation(
        content: json['content'] as String? ?? '',
        provider: json['provider'] as String? ?? '',
        intervened: json['intervened'] as bool? ?? false,
        trigger: json['trigger'] as String? ?? '',
        workCheck: TextProvider.fromJson(
            json['work_check'] as Map<String, dynamic>?),
        teacherFeedback: TextProvider.fromJson(
            json['teacher_feedback'] as Map<String, dynamic>?),
        stepCheck: json['step_check'] != null
            ? StepCheck.fromJson(json['step_check'] as Map<String, dynamic>)
            : null,
        steps: ((json['steps'] as List?) ?? [])
            .map((s) => SolutionStep.fromJson(s as Map<String, dynamic>))
            .toList(),
        graph: json['graph'] != null
            ? GraphSpec.fromJson(json['graph'] as Map<String, dynamic>)
            : null,
        graphCheck: json['graph_check'] != null
            ? GraphCheck.fromJson(json['graph_check'] as Map<String, dynamic>)
            : null,
      );
}

class HintResponse {
  final String hint;
  final String provider;
  final String? part;
  final String? status;
  final int? errorLine;

  HintResponse({
    required this.hint,
    required this.provider,
    this.part,
    this.status,
    this.errorLine,
  });

  factory HintResponse.fromJson(Map<String, dynamic> json) => HintResponse(
        hint: json['hint'] as String? ?? '',
        provider: json['provider'] as String? ?? '',
        part: json['part'] as String?,
        status: json['status'] as String?,
        errorLine: json['error_line'] as int?,
      );
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
  final Explanation? explanation;
  final TextProvider? workCheck;
  final TextProvider? teacherFeedback;
  final StepCheck? stepCheck;
  final GraphSpec? graph;
  final GraphCheck? graphCheck;
  final RubricScore? rubricScore;

  GradeResult({
    this.attemptId = '',
    required this.correct,
    required this.reason,
    this.given,
    this.expected = '',
    this.parts = const [],
    this.part,
    this.allComplete,
    this.explanation,
    this.workCheck,
    this.teacherFeedback,
    this.stepCheck,
    this.graph,
    this.graphCheck,
    this.rubricScore,
  });

  factory GradeResult.fromJson(Map<String, dynamic> json) => GradeResult(
        attemptId: json['attempt_id'] as String? ?? '',
        correct: json['correct'] as bool? ?? false,
        reason: json['reason'] as String? ?? '',
        given: json['given'] as String?,
        expected: json['expected'] as String? ?? '',
        parts: ((json['parts'] as List?) ?? [])
            .map((p) => PartVerdict.fromJson(p as Map<String, dynamic>))
            .toList(),
        part: json['part'] as String?,
        allComplete: json['all_complete'] as bool?,
        explanation: json['explanation'] != null
            ? Explanation.fromJson(json['explanation'] as Map<String, dynamic>)
            : null,
        workCheck:
            TextProvider.fromJson(json['work_check'] as Map<String, dynamic>?),
        teacherFeedback: TextProvider.fromJson(
            json['teacher_feedback'] as Map<String, dynamic>?),
        stepCheck: json['step_check'] != null
            ? StepCheck.fromJson(json['step_check'] as Map<String, dynamic>)
            : null,
        graph: json['graph'] != null
            ? GraphSpec.fromJson(json['graph'] as Map<String, dynamic>)
            : null,
        graphCheck: json['graph_check'] != null
            ? GraphCheck.fromJson(json['graph_check'] as Map<String, dynamic>)
            : null,
        rubricScore: json['rubric_score'] != null
            ? RubricScore.fromJson(json['rubric_score'] as Map<String, dynamic>)
            : null,
      );
}
