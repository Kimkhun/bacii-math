import 'grade_result.dart';
import 'stroke_doc.dart';

class Attempt {
  final String id;
  final String questionId;
  final String topic;
  final String questionType;
  final String difficulty;
  final String prompt;
  final String? promptLatex;
  final String expectedAnswer;
  final String userAnswer;
  final bool correct;
  final String reason;
  final List<FormulaResult> formulaBreakdown;
  final String? workText;
  final StepCheck? stepCheck;
  final int hintsUsed;
  final String? strokesThumb;
  final String createdAt;

  Attempt({
    required this.id,
    this.questionId = '',
    required this.topic,
    required this.questionType,
    required this.difficulty,
    required this.prompt,
    this.promptLatex,
    required this.expectedAnswer,
    required this.userAnswer,
    required this.correct,
    required this.reason,
    this.formulaBreakdown = const [],
    this.workText,
    this.stepCheck,
    this.hintsUsed = 0,
    this.strokesThumb,
    required this.createdAt,
  });

  factory Attempt.fromJson(Map<String, dynamic> json) {
    return Attempt(
      id: json['id'] as String? ?? '',
      questionId: json['question_id'] as String? ?? '',
      topic: json['topic'] as String? ?? '',
      questionType: json['question_type'] as String? ?? '',
      difficulty: json['difficulty'] as String? ?? 'medium',
      prompt: json['prompt'] as String? ?? '',
      promptLatex: json['prompt_latex'] as String?,
      expectedAnswer: json['expected_answer'] as String? ?? '',
      userAnswer: json['user_answer'] as String? ?? '',
      correct: json['correct'] as bool? ?? false,
      reason: json['reason'] as String? ?? '',
      formulaBreakdown: ((json['formula_breakdown'] as List<dynamic>?) ?? [])
          .map((f) => FormulaResult.fromJson(f as Map<String, dynamic>))
          .toList(),
      workText: json['work_text'] as String?,
      stepCheck: json['step_check'] != null
          ? StepCheck.fromJson(json['step_check'] as Map<String, dynamic>)
          : null,
      hintsUsed: json['hints_used'] as int? ?? 0,
      strokesThumb: json['strokes_thumb'] as String?,
      createdAt: json['created_at'] as String? ?? '',
    );
  }
}

class AttemptQuestion {
  final String id;
  final String topic;
  final String questionType;
  final String difficulty;
  final String prompt;
  final String? promptLatex;
  final String expectedAnswer;
  final List<String> formulaTags;
  final List<QuestionStepLite> steps;

  AttemptQuestion({
    required this.id,
    required this.topic,
    required this.questionType,
    required this.difficulty,
    required this.prompt,
    this.promptLatex,
    required this.expectedAnswer,
    this.formulaTags = const [],
    this.steps = const [],
  });

  factory AttemptQuestion.fromJson(Map<String, dynamic> json) => AttemptQuestion(
        id: json['id'] as String? ?? '',
        topic: json['topic'] as String? ?? '',
        questionType: json['question_type'] as String? ?? '',
        difficulty: json['difficulty'] as String? ?? '',
        prompt: json['prompt'] as String? ?? '',
        promptLatex: json['prompt_latex'] as String?,
        expectedAnswer: json['expected_answer'] as String? ?? '',
        formulaTags: (json['formula_tags'] as List<dynamic>?)
                ?.map((e) => e.toString())
                .toList() ??
            [],
        steps: ((json['steps'] as List<dynamic>?) ?? [])
            .map((s) => QuestionStepLite.fromJson(s as Map<String, dynamic>))
            .toList(),
      );
}

class QuestionStepLite {
  final int stepOrder;
  final String title;
  final String detail;
  final String? formula;

  QuestionStepLite({
    required this.stepOrder,
    required this.title,
    required this.detail,
    this.formula,
  });

  factory QuestionStepLite.fromJson(Map<String, dynamic> json) =>
      QuestionStepLite(
        stepOrder: json['step_order'] as int? ?? 1,
        title: json['title'] as String? ?? '',
        detail: json['detail'] as String? ?? '',
        formula: json['formula'] as String?,
      );
}

class AttemptExplanation {
  final String provider;
  final String content;
  final String trigger;
  final String createdAt;

  AttemptExplanation({
    required this.provider,
    required this.content,
    required this.trigger,
    required this.createdAt,
  });

  factory AttemptExplanation.fromJson(Map<String, dynamic> json) =>
      AttemptExplanation(
        provider: json['provider'] as String? ?? '',
        content: json['content'] as String? ?? '',
        trigger: json['trigger'] as String? ?? '',
        createdAt: json['created_at'] as String? ?? '',
      );
}

class AttemptDetail {
  final String id;
  final String userAnswer;
  final String? parsedAnswer;
  final bool correct;
  final String reason;
  final String? workText;
  final StepCheck? stepCheck;
  final List<List<double>?> linesBoxes;
  final List<FormulaResult> formulaBreakdown;
  final int hintsUsed;
  final StrokeDocument? strokes;
  final String? strokesThumb;
  final String createdAt;
  final AttemptQuestion? question;
  final List<AttemptExplanation> explanations;

  AttemptDetail({
    required this.id,
    required this.userAnswer,
    this.parsedAnswer,
    required this.correct,
    required this.reason,
    this.workText,
    this.stepCheck,
    this.linesBoxes = const [],
    this.formulaBreakdown = const [],
    this.hintsUsed = 0,
    this.strokes,
    this.strokesThumb,
    required this.createdAt,
    this.question,
    this.explanations = const [],
  });

  static List<double>? _box(dynamic raw) {
    if (raw is! List) return null;
    return raw.map((n) => (n as num).toDouble()).toList();
  }

  factory AttemptDetail.fromJson(Map<String, dynamic> json) => AttemptDetail(
        id: json['id'] as String? ?? '',
        userAnswer: json['user_answer'] as String? ?? '',
        parsedAnswer: json['parsed_answer'] as String?,
        correct: json['correct'] as bool? ?? false,
        reason: json['reason'] as String? ?? '',
        workText: json['work_text'] as String?,
        stepCheck: json['step_check'] != null
            ? StepCheck.fromJson(json['step_check'] as Map<String, dynamic>)
            : null,
        linesBoxes:
            ((json['lines_boxes'] as List?) ?? []).map((b) => _box(b)).toList(),
        formulaBreakdown: ((json['formula_breakdown'] as List<dynamic>?) ?? [])
            .map((f) => FormulaResult.fromJson(f as Map<String, dynamic>))
            .toList(),
        hintsUsed: json['hints_used'] as int? ?? 0,
        strokes: json['strokes'] != null
            ? StrokeDocument.fromJson(json['strokes'] as Map<String, dynamic>)
            : null,
        strokesThumb: json['strokes_thumb'] as String?,
        createdAt: json['created_at'] as String? ?? '',
        question: json['question'] != null
            ? AttemptQuestion.fromJson(json['question'] as Map<String, dynamic>)
            : null,
        explanations: ((json['explanations'] as List<dynamic>?) ?? [])
            .map((e) => AttemptExplanation.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class TopicStat {
  final String questionType;
  final int attempts;
  final int correct;

  TopicStat({
    required this.questionType,
    required this.attempts,
    required this.correct,
  });

  factory TopicStat.fromJson(Map<String, dynamic> json) => TopicStat(
        questionType: json['question_type'] as String? ?? '',
        attempts: json['attempts'] as int? ?? 0,
        correct: json['correct'] as int? ?? 0,
      );
}

class FormulaStat {
  final String formula;
  final String? nameEn;
  final int attempts;
  final int reached;
  final int missed;

  FormulaStat({
    required this.formula,
    this.nameEn,
    required this.attempts,
    required this.reached,
    required this.missed,
  });

  factory FormulaStat.fromJson(Map<String, dynamic> json) => FormulaStat(
        formula: json['formula'] as String? ?? '',
        nameEn: json['name_en'] as String?,
        attempts: json['attempts'] as int? ?? 0,
        reached: json['reached'] as int? ?? 0,
        missed: json['missed'] as int? ?? 0,
      );
}

class Stats {
  final int totalAttempts;
  final int correct;
  final double accuracy;
  final List<TopicStat> byTopic;
  final List<FormulaStat> byFormula;

  Stats({
    required this.totalAttempts,
    required this.correct,
    required this.accuracy,
    required this.byTopic,
    this.byFormula = const [],
  });

  factory Stats.fromJson(Map<String, dynamic> json) => Stats(
        totalAttempts: json['total_attempts'] as int? ?? 0,
        correct: json['correct'] as int? ?? 0,
        accuracy: (json['accuracy'] as num?)?.toDouble() ?? 0.0,
        byTopic: ((json['by_topic'] as List<dynamic>?) ?? [])
            .map((t) => TopicStat.fromJson(t as Map<String, dynamic>))
            .toList(),
        byFormula: ((json['by_formula'] as List<dynamic>?) ?? [])
            .map((f) => FormulaStat.fromJson(f as Map<String, dynamic>))
            .toList(),
      );
}
