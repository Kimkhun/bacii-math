import 'question.dart';
import 'stroke_doc.dart';

/// Saved-progress models. Mirrors SessionSummary / SessionDetail /
/// SavedPartState in web/src/lib/api.ts.

class SessionQuestionLite {
  final String id;
  final String topic;
  final String questionType;
  final String difficulty;
  final String prompt;
  final String? promptLatex;

  SessionQuestionLite({
    required this.id,
    required this.topic,
    required this.questionType,
    required this.difficulty,
    required this.prompt,
    this.promptLatex,
  });

  factory SessionQuestionLite.fromJson(Map<String, dynamic> json) =>
      SessionQuestionLite(
        id: json['id'] as String? ?? '',
        topic: json['topic'] as String? ?? '',
        questionType: json['question_type'] as String? ?? '',
        difficulty: json['difficulty'] as String? ?? '',
        prompt: json['prompt'] as String? ?? '',
        promptLatex: json['prompt_latex'] as String?,
      );
}

class SessionSummary {
  final String id;
  final String questionId;
  final String status;
  final int partsDone;
  final int partsTotal;
  final String updatedAt;
  final SessionQuestionLite? question;

  SessionSummary({
    required this.id,
    required this.questionId,
    required this.status,
    required this.partsDone,
    required this.partsTotal,
    required this.updatedAt,
    this.question,
  });

  factory SessionSummary.fromJson(Map<String, dynamic> json) => SessionSummary(
        id: json['id'] as String? ?? '',
        questionId: json['question_id'] as String? ?? '',
        status: json['status'] as String? ?? '',
        partsDone: json['parts_done'] as int? ?? 0,
        partsTotal: json['parts_total'] as int? ?? 0,
        updatedAt: json['updated_at'] as String? ?? '',
        question: json['question'] != null
            ? SessionQuestionLite.fromJson(
                json['question'] as Map<String, dynamic>)
            : null,
      );
}

class SavedPartState {
  final String? typed;
  final String? workText;
  final List<List<double>?> linesBoxes;
  final StrokeDocument? strokes;
  final String? strokesThumb;
  final bool correct;

  SavedPartState({
    this.typed,
    this.workText,
    this.linesBoxes = const [],
    this.strokes,
    this.strokesThumb,
    this.correct = false,
  });

  static List<double>? _box(dynamic raw) {
    if (raw is! List) return null;
    return raw.map((n) => (n as num).toDouble()).toList();
  }

  factory SavedPartState.fromJson(Map<String, dynamic> json) => SavedPartState(
        typed: json['typed'] as String?,
        workText: json['work_text'] as String?,
        linesBoxes:
            ((json['lines_boxes'] as List?) ?? []).map((b) => _box(b)).toList(),
        strokes: json['strokes'] != null
            ? StrokeDocument.fromJson(json['strokes'] as Map<String, dynamic>)
            : null,
        strokesThumb: json['strokes_thumb'] as String?,
        correct: json['correct'] as bool? ?? false,
      );
}

class SessionDetail {
  final String id;
  final String status;
  final String updatedAt;
  final Question question;
  final Map<String, SavedPartState> parts;

  SessionDetail({
    required this.id,
    required this.status,
    required this.updatedAt,
    required this.question,
    required this.parts,
  });

  factory SessionDetail.fromJson(Map<String, dynamic> json) => SessionDetail(
        id: json['id'] as String? ?? '',
        status: json['status'] as String? ?? '',
        updatedAt: json['updated_at'] as String? ?? '',
        question:
            Question.fromJson((json['question'] as Map<String, dynamic>?) ?? {}),
        parts: ((json['parts'] as Map<String, dynamic>?) ?? {}).map(
          (k, v) => MapEntry(k, SavedPartState.fromJson(v as Map<String, dynamic>)),
        ),
      );
}
