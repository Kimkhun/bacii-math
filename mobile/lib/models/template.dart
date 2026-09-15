import 'graph.dart';

/// Admin template-introspection + sandbox models. Mirrors TemplateSummary /
/// TemplateStructures / TemplateStructure / Sandbox* in web/src/lib/api.ts.

class TemplateSummaryQuestionType {
  final String questionType;
  final int count;

  TemplateSummaryQuestionType({required this.questionType, required this.count});

  factory TemplateSummaryQuestionType.fromJson(Map<String, dynamic> json) =>
      TemplateSummaryQuestionType(
        questionType: json['question_type'] as String? ?? '',
        count: json['count'] as int? ?? 0,
      );
}

class TemplateSummaryTopic {
  final String topic;
  final List<TemplateSummaryQuestionType> questionTypes;
  final int structureCount;
  final List<String> difficulties;
  final int curated;

  TemplateSummaryTopic({
    required this.topic,
    required this.questionTypes,
    required this.structureCount,
    required this.difficulties,
    required this.curated,
  });

  factory TemplateSummaryTopic.fromJson(Map<String, dynamic> json) =>
      TemplateSummaryTopic(
        topic: json['topic'] as String? ?? '',
        questionTypes: ((json['question_types'] as List?) ?? [])
            .map((q) =>
                TemplateSummaryQuestionType.fromJson(q as Map<String, dynamic>))
            .toList(),
        structureCount: json['structure_count'] as int? ?? 0,
        difficulties: ((json['difficulties'] as List?) ?? [])
            .map((e) => e.toString())
            .toList(),
        curated: json['curated'] as int? ?? 0,
      );
}

class TemplateSummary {
  final List<TemplateSummaryTopic> topics;

  TemplateSummary({required this.topics});

  factory TemplateSummary.fromJson(Map<String, dynamic> json) => TemplateSummary(
        topics: ((json['topics'] as List?) ?? [])
            .map((t) => TemplateSummaryTopic.fromJson(t as Map<String, dynamic>))
            .toList(),
      );
}

class TemplateStructurePart {
  final String label;
  final String? want;
  final String? answerKind;
  final String? questionKm;
  final String? technique;
  final String answer;
  final String? answerLatex;
  final String? answerDisplay;

  TemplateStructurePart({
    required this.label,
    this.want,
    this.answerKind,
    this.questionKm,
    this.technique,
    required this.answer,
    this.answerLatex,
    this.answerDisplay,
  });

  factory TemplateStructurePart.fromJson(Map<String, dynamic> json) =>
      TemplateStructurePart(
        label: json['label'] as String? ?? '',
        want: json['want'] as String?,
        answerKind: json['answer_kind'] as String?,
        questionKm: json['question_km'] as String?,
        technique: json['technique'] as String?,
        answer: json['answer'] as String? ?? '',
        answerLatex: json['answer_latex'] as String?,
        answerDisplay: json['answer_display'] as String?,
      );
}

class TemplateStructure {
  final String id;
  final String questionType;
  final String difficulty;
  final String pattern;
  final String? patternLatex;
  final String? technique;
  final String samplePrompt;
  final String? samplePromptLatex;
  final String sampleAnswer;
  final String? sampleAnswerLatex;
  final List<String> formulaTags;
  final List<String> sourceLabels;
  final GraphSpec? graph;
  final String? solutionKm;
  final List<TemplateStructurePart> parts;

  TemplateStructure({
    required this.id,
    required this.questionType,
    required this.difficulty,
    required this.pattern,
    this.patternLatex,
    this.technique,
    required this.samplePrompt,
    this.samplePromptLatex,
    required this.sampleAnswer,
    this.sampleAnswerLatex,
    this.formulaTags = const [],
    this.sourceLabels = const [],
    this.graph,
    this.solutionKm,
    this.parts = const [],
  });

  factory TemplateStructure.fromJson(Map<String, dynamic> json) =>
      TemplateStructure(
        id: json['id'] as String? ?? '',
        questionType: json['question_type'] as String? ?? '',
        difficulty: json['difficulty'] as String? ?? '',
        pattern: json['pattern'] as String? ?? '',
        patternLatex: json['pattern_latex'] as String?,
        technique: json['technique'] as String?,
        samplePrompt: json['sample_prompt'] as String? ?? '',
        samplePromptLatex: json['sample_prompt_latex'] as String?,
        sampleAnswer: json['sample_answer'] as String? ?? '',
        sampleAnswerLatex: json['sample_answer_latex'] as String?,
        formulaTags: ((json['formula_tags'] as List?) ?? [])
            .map((e) => e.toString())
            .toList(),
        sourceLabels: ((json['source_labels'] as List?) ?? [])
            .map((e) => e.toString())
            .toList(),
        graph: json['graph'] != null
            ? GraphSpec.fromJson(json['graph'] as Map<String, dynamic>)
            : null,
        solutionKm: json['solution_km'] as String?,
        parts: ((json['parts'] as List?) ?? [])
            .map((p) =>
                TemplateStructurePart.fromJson(p as Map<String, dynamic>))
            .toList(),
      );
}

class TemplateStructuresQuestionType {
  final String questionType;
  final List<TemplateStructure> structures;

  TemplateStructuresQuestionType({
    required this.questionType,
    required this.structures,
  });

  factory TemplateStructuresQuestionType.fromJson(Map<String, dynamic> json) =>
      TemplateStructuresQuestionType(
        questionType: json['question_type'] as String? ?? '',
        structures: ((json['structures'] as List?) ?? [])
            .map((s) => TemplateStructure.fromJson(s as Map<String, dynamic>))
            .toList(),
      );
}

class TemplateStructuresTopic {
  final String topic;
  final List<TemplateStructuresQuestionType> questionTypes;

  TemplateStructuresTopic({required this.topic, required this.questionTypes});

  factory TemplateStructuresTopic.fromJson(Map<String, dynamic> json) =>
      TemplateStructuresTopic(
        topic: json['topic'] as String? ?? '',
        questionTypes: ((json['question_types'] as List?) ?? [])
            .map((q) => TemplateStructuresQuestionType.fromJson(
                q as Map<String, dynamic>))
            .toList(),
      );
}

class TemplateStructures {
  final List<TemplateStructuresTopic> topics;

  TemplateStructures({required this.topics});

  factory TemplateStructures.fromJson(Map<String, dynamic> json) =>
      TemplateStructures(
        topics: ((json['topics'] as List?) ?? [])
            .map((t) => TemplateStructuresTopic.fromJson(t as Map<String, dynamic>))
            .toList(),
      );
}

class SandboxSample {
  final Map<String, dynamic> params;
  final String? prompt;
  final String? promptLatex;

  SandboxSample({required this.params, this.prompt, this.promptLatex});

  factory SandboxSample.fromJson(Map<String, dynamic> json) => SandboxSample(
        params: (json['params'] as Map<String, dynamic>?) ?? {},
        prompt: json['prompt'] as String?,
        promptLatex: json['prompt_latex'] as String?,
      );
}

class SandboxCheckpoint {
  final String label;
  final String value;
  final String? formula;

  SandboxCheckpoint({required this.label, required this.value, this.formula});

  factory SandboxCheckpoint.fromJson(Map<String, dynamic> json) =>
      SandboxCheckpoint(
        label: json['label'] as String? ?? '',
        value: json['value']?.toString() ?? '',
        formula: json['formula'] as String?,
      );
}

class SandboxSolveStep {
  final String title;
  final String detail;
  final String? formula;

  SandboxSolveStep({required this.title, required this.detail, this.formula});

  factory SandboxSolveStep.fromJson(Map<String, dynamic> json) =>
      SandboxSolveStep(
        title: json['title'] as String? ?? '',
        detail: json['detail'] as String? ?? '',
        formula: json['formula'] as String?,
      );
}

class SandboxSolveResult {
  final String answerExact;
  final dynamic answerDecimal;
  final String answerLatex;
  final List<SandboxSolveStep> steps;
  final List<String> formulaTags;
  final List<SandboxCheckpoint> checkpoints;
  final Map<String, dynamic> paramsUsed;

  SandboxSolveResult({
    required this.answerExact,
    this.answerDecimal,
    required this.answerLatex,
    required this.steps,
    required this.formulaTags,
    required this.checkpoints,
    required this.paramsUsed,
  });

  factory SandboxSolveResult.fromJson(Map<String, dynamic> json) =>
      SandboxSolveResult(
        answerExact: json['answer_exact'] as String? ?? '',
        answerDecimal: json['answer_decimal'],
        answerLatex: json['answer_latex'] as String? ?? '',
        steps: ((json['steps'] as List?) ?? [])
            .map((s) => SandboxSolveStep.fromJson(s as Map<String, dynamic>))
            .toList(),
        formulaTags: ((json['formula_tags'] as List?) ?? [])
            .map((e) => e.toString())
            .toList(),
        checkpoints: ((json['checkpoints'] as List?) ?? [])
            .map((c) => SandboxCheckpoint.fromJson(c as Map<String, dynamic>))
            .toList(),
        paramsUsed: (json['params_used'] as Map<String, dynamic>?) ?? {},
      );
}

class SandboxLineResult {
  final int line;
  final String text;
  final bool checked;
  final bool? correct;
  final String? matches;
  final String? formula;
  final String? expected;
  final String? reason;

  SandboxLineResult({
    required this.line,
    required this.text,
    required this.checked,
    this.correct,
    this.matches,
    this.formula,
    this.expected,
    this.reason,
  });

  factory SandboxLineResult.fromJson(Map<String, dynamic> json) =>
      SandboxLineResult(
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

class SandboxRubricStep {
  final String item;
  final String label;
  final double pointsEarned;
  final double pointsPossible;
  final String? matchedLine;
  final bool implied;

  SandboxRubricStep({
    required this.item,
    required this.label,
    required this.pointsEarned,
    required this.pointsPossible,
    this.matchedLine,
    this.implied = false,
  });

  factory SandboxRubricStep.fromJson(Map<String, dynamic> json) =>
      SandboxRubricStep(
        item: json['item'] as String? ?? '',
        label: json['label'] as String? ?? '',
        pointsEarned: (json['points_earned'] as num?)?.toDouble() ?? 0,
        pointsPossible: (json['points_possible'] as num?)?.toDouble() ?? 0,
        matchedLine: json['matched_line'] as String?,
        implied: json['implied'] as bool? ?? false,
      );
}

class SandboxGradeResult {
  final List<SandboxLineResult> lineResults;
  final int? firstErrorLine;
  final double? rubricEarned;
  final double? rubricPossible;
  final List<SandboxRubricStep> rubricBreakdown;
  final String? rubricError;

  SandboxGradeResult({
    required this.lineResults,
    this.firstErrorLine,
    this.rubricEarned,
    this.rubricPossible,
    this.rubricBreakdown = const [],
    this.rubricError,
  });

  factory SandboxGradeResult.fromJson(Map<String, dynamic> json) {
    final sc = (json['step_check'] as Map<String, dynamic>?) ?? {};
    final rubric = json['rubric_score'] as Map<String, dynamic>?;
    return SandboxGradeResult(
      lineResults: ((sc['line_results'] as List?) ?? [])
          .map((r) => SandboxLineResult.fromJson(r as Map<String, dynamic>))
          .toList(),
      firstErrorLine: sc['first_error_line'] as int?,
      rubricEarned: (rubric?['earned'] as num?)?.toDouble(),
      rubricPossible: (rubric?['possible'] as num?)?.toDouble(),
      rubricBreakdown: ((rubric?['breakdown'] as List?) ?? [])
          .map((b) => SandboxRubricStep.fromJson(b as Map<String, dynamic>))
          .toList(),
      rubricError: json['rubric_error'] as String?,
    );
  }
}
