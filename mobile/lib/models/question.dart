import 'graph.dart';

class QuestionStep {
  final int stepOrder;
  final String title;
  final String detail;
  final String? formula;

  QuestionStep({
    required this.stepOrder,
    required this.title,
    required this.detail,
    this.formula,
  });

  factory QuestionStep.fromJson(Map<String, dynamic> json) {
    return QuestionStep(
      stepOrder: json['step_order'] as int? ?? 1,
      title: json['title'] as String? ?? '',
      detail: json['detail'] as String? ?? '',
      formula: json['formula'] as String?,
    );
  }
}

class QuestionPart {
  final String label;
  final String? want;
  final String? questionKm;
  final String? technique;
  final String? answerKind;
  final String? answer;
  final String? answerLatex;
  final String? answerDisplay;

  QuestionPart({
    required this.label,
    this.want,
    this.questionKm,
    this.technique,
    this.answerKind,
    this.answer,
    this.answerLatex,
    this.answerDisplay,
  });

  factory QuestionPart.fromJson(Map<String, dynamic> json) {
    return QuestionPart(
      label: json['label'] as String? ?? '',
      want: json['want'] as String?,
      questionKm: json['question_km'] as String?,
      technique: json['technique'] as String?,
      answerKind: json['answer_kind'] as String?,
      answer: json['answer'] as String?,
      answerLatex: json['answer_latex'] as String?,
      answerDisplay: json['answer_display'] as String?,
    );
  }
}

class Question {
  final String id;
  final String topic;
  final String questionType;
  final String difficulty;
  final num? a;
  final num? b;
  final String prompt;
  final String? promptLatex;
  final String zDisplay;
  final String source;
  final List<String> formulaTags;
  final String? formulaDifficulty;
  final Map<String, dynamic> params;
  final List<QuestionStep> steps;
  final List<QuestionPart> parts;
  final GraphSpec? graph;

  Question({
    required this.id,
    required this.topic,
    required this.questionType,
    required this.difficulty,
    this.a,
    this.b,
    required this.prompt,
    this.promptLatex,
    required this.zDisplay,
    required this.source,
    this.formulaTags = const [],
    this.formulaDifficulty,
    this.params = const {},
    this.steps = const [],
    this.parts = const [],
    this.graph,
  });

  factory Question.fromJson(Map<String, dynamic> json) {
    final params = (json['params'] as Map<String, dynamic>?) ?? {};
    var rawParts = json['parts'] as List<dynamic>?;
    List<QuestionPart> parsedParts = [];
    if (rawParts != null) {
      parsedParts =
          rawParts.map((p) => QuestionPart.fromJson(p as Map<String, dynamic>)).toList();
    } else if (params['parts'] != null) {
      parsedParts = (params['parts'] as List<dynamic>)
          .map((p) => QuestionPart.fromJson(p as Map<String, dynamic>))
          .toList();
    }

    final rawGraph = json['graph'] ?? params['graph'];

    return Question(
      id: json['id'] as String? ?? '',
      topic: json['topic'] as String? ?? 'complex',
      questionType: json['question_type'] as String? ?? '',
      difficulty: json['difficulty'] as String? ?? 'medium',
      a: json['a'] as num?,
      b: json['b'] as num?,
      prompt: json['prompt'] as String? ?? '',
      promptLatex: json['prompt_latex'] as String?,
      zDisplay: json['z_display'] as String? ?? '',
      source: json['source'] as String? ?? 'template',
      formulaTags:
          (json['formula_tags'] as List<dynamic>?)?.map((e) => e.toString()).toList() ??
              [],
      formulaDifficulty: json['formula_difficulty'] as String?,
      params: params,
      steps: ((json['steps'] as List<dynamic>?) ?? [])
          .map((s) => QuestionStep.fromJson(s as Map<String, dynamic>))
          .toList(),
      parts: parsedParts,
      graph: rawGraph is Map<String, dynamic>
          ? GraphSpec.fromJson(rawGraph)
          : null,
    );
  }
}
