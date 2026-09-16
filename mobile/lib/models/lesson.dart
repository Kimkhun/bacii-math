/// Authored, reusable per-skill lesson content. Mirrors Lesson in
/// web/src/lib/api.ts. Bilingual: pick the _en/_km field for the reader.

class LessonFormula {
  final String latex;
  final String? noteEn;
  final String? noteKm;

  LessonFormula({required this.latex, this.noteEn, this.noteKm});

  factory LessonFormula.fromJson(Map<String, dynamic> json) => LessonFormula(
        latex: json['latex'] as String? ?? '',
        noteEn: json['note_en'] as String?,
        noteKm: json['note_km'] as String?,
      );
}

class LessonSection {
  final String headingEn;
  final String headingKm;
  final String bodyEn;
  final String bodyKm;

  LessonSection({
    required this.headingEn,
    required this.headingKm,
    required this.bodyEn,
    required this.bodyKm,
  });

  factory LessonSection.fromJson(Map<String, dynamic> json) => LessonSection(
        headingEn: json['heading_en'] as String? ?? '',
        headingKm: json['heading_km'] as String? ?? '',
        bodyEn: json['body_en'] as String? ?? '',
        bodyKm: json['body_km'] as String? ?? '',
      );
}

class LessonStep {
  final String textEn;
  final String textKm;
  final String? latex;

  LessonStep({required this.textEn, required this.textKm, this.latex});

  factory LessonStep.fromJson(Map<String, dynamic> json) => LessonStep(
        textEn: json['text_en'] as String? ?? '',
        textKm: json['text_km'] as String? ?? '',
        latex: json['latex'] as String?,
      );
}

class LessonExample {
  final String promptEn;
  final String promptKm;
  final List<LessonStep> steps;
  final String? answerLatex;

  LessonExample({
    required this.promptEn,
    required this.promptKm,
    required this.steps,
    this.answerLatex,
  });

  factory LessonExample.fromJson(Map<String, dynamic> json) => LessonExample(
        promptEn: json['prompt_en'] as String? ?? '',
        promptKm: json['prompt_km'] as String? ?? '',
        steps: ((json['steps'] as List?) ?? [])
            .map((s) => LessonStep.fromJson(s as Map<String, dynamic>))
            .toList(),
        answerLatex: json['answer_latex'] as String?,
      );
}

class Lesson {
  final String topic;
  final String questionType;
  final String titleEn;
  final String titleKm;
  final String summaryEn;
  final String summaryKm;
  final List<LessonFormula> formulas;
  final List<LessonSection> sections;
  final List<LessonExample> examples;

  Lesson({
    required this.topic,
    required this.questionType,
    required this.titleEn,
    required this.titleKm,
    required this.summaryEn,
    required this.summaryKm,
    required this.formulas,
    required this.sections,
    required this.examples,
  });

  factory Lesson.fromJson(Map<String, dynamic> json) => Lesson(
        topic: json['topic'] as String? ?? '',
        questionType: json['question_type'] as String? ?? '',
        titleEn: json['title_en'] as String? ?? '',
        titleKm: json['title_km'] as String? ?? '',
        summaryEn: json['summary_en'] as String? ?? '',
        summaryKm: json['summary_km'] as String? ?? '',
        formulas: ((json['formulas'] as List?) ?? [])
            .map((f) => LessonFormula.fromJson(f as Map<String, dynamic>))
            .toList(),
        sections: ((json['sections'] as List?) ?? [])
            .map((s) => LessonSection.fromJson(s as Map<String, dynamic>))
            .toList(),
        examples: ((json['examples'] as List?) ?? [])
            .map((e) => LessonExample.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
