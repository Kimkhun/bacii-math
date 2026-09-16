/// Past-exam replay models. Mirrors Exam / ExamResult in web/src/lib/api.ts.

class ExamQuestion {
  final String label;
  final String? promptEn;
  final String? promptLatex;
  final String? answerLatex;
  final bool gradable;

  ExamQuestion({
    required this.label,
    this.promptEn,
    this.promptLatex,
    this.answerLatex,
    this.gradable = true,
  });

  factory ExamQuestion.fromJson(Map<String, dynamic> json) => ExamQuestion(
        label: json['label'] as String? ?? '',
        promptEn: json['prompt_en'] as String?,
        promptLatex: json['prompt_latex'] as String?,
        answerLatex: json['answer_latex'] as String?,
        gradable: json['gradable'] as bool? ?? true,
      );
}

class ExamSection {
  final String id;
  final String? titleEn;
  final String? titleKm;
  final String? givenEn;
  final String? givenKm;
  final String? givenLatex;
  final List<ExamQuestion> questions;

  ExamSection({
    required this.id,
    this.titleEn,
    this.titleKm,
    this.givenEn,
    this.givenKm,
    this.givenLatex,
    required this.questions,
  });

  factory ExamSection.fromJson(Map<String, dynamic> json) => ExamSection(
        id: json['id'] as String? ?? '',
        titleEn: json['title_en'] as String?,
        titleKm: json['title_km'] as String?,
        givenEn: json['given_en'] as String?,
        givenKm: json['given_km'] as String?,
        givenLatex: json['given_latex'] as String?,
        questions: ((json['questions'] as List?) ?? [])
            .map((q) => ExamQuestion.fromJson(q as Map<String, dynamic>))
            .toList(),
      );
}

class Exam {
  final String examId;
  final String? examDate;
  final int? durationMinutes;
  final num? totalPoints;
  final List<ExamSection> sections;

  Exam({
    required this.examId,
    this.examDate,
    this.durationMinutes,
    this.totalPoints,
    required this.sections,
  });

  factory Exam.fromJson(Map<String, dynamic> json) => Exam(
        examId: json['exam_id'] as String? ?? '',
        examDate: json['exam_date'] as String?,
        durationMinutes: json['duration_minutes'] as int?,
        totalPoints: json['total_points'] as num?,
        sections: ((json['sections'] as List?) ?? [])
            .map((s) => ExamSection.fromJson(s as Map<String, dynamic>))
            .toList(),
      );
}

class ExamRubricItem {
  final String item;
  final String label;
  final double pointsEarned;
  final double pointsPossible;
  final String? matchedLine;

  ExamRubricItem({
    required this.item,
    required this.label,
    required this.pointsEarned,
    required this.pointsPossible,
    this.matchedLine,
  });

  factory ExamRubricItem.fromJson(Map<String, dynamic> json) => ExamRubricItem(
        item: json['item'] as String? ?? '',
        label: json['label'] as String? ?? '',
        pointsEarned: (json['points_earned'] as num?)?.toDouble() ?? 0,
        pointsPossible: (json['points_possible'] as num?)?.toDouble() ?? 0,
        matchedLine: json['matched_line'] as String?,
      );
}

class ExamQuestionResult {
  final double earned;
  final double possible;
  final List<ExamRubricItem> breakdown;

  ExamQuestionResult({
    required this.earned,
    required this.possible,
    required this.breakdown,
  });

  factory ExamQuestionResult.fromJson(Map<String, dynamic> json) =>
      ExamQuestionResult(
        earned: (json['earned'] as num?)?.toDouble() ?? 0,
        possible: (json['possible'] as num?)?.toDouble() ?? 0,
        breakdown: ((json['breakdown'] as List?) ?? [])
            .map((b) => ExamRubricItem.fromJson(b as Map<String, dynamic>))
            .toList(),
      );
}

class ExamResult {
  final double earned;
  final double possible;
  final Map<String, ExamQuestionResult> perQuestion;

  ExamResult({
    required this.earned,
    required this.possible,
    required this.perQuestion,
  });

  factory ExamResult.fromJson(Map<String, dynamic> json) => ExamResult(
        earned: (json['earned'] as num?)?.toDouble() ?? 0,
        possible: (json['possible'] as num?)?.toDouble() ?? 0,
        perQuestion:
            ((json['per_question'] as Map<String, dynamic>?) ?? {}).map(
          (k, v) =>
              MapEntry(k, ExamQuestionResult.fromJson(v as Map<String, dynamic>)),
        ),
      );
}
