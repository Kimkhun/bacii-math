class Skill {
  final String key;
  final String topic;
  final String topicLabel;
  final String questionType;
  final String label;
  final String difficulty;
  final double level;
  final int attempts;
  final int correct;
  final String status;
  final bool hasLesson;

  Skill({
    required this.key,
    required this.topic,
    required this.topicLabel,
    required this.questionType,
    required this.label,
    required this.difficulty,
    required this.level,
    required this.attempts,
    required this.correct,
    required this.status,
    required this.hasLesson,
  });

  factory Skill.fromJson(Map<String, dynamic> json) {
    return Skill(
      key: json['key'] as String? ?? '',
      topic: json['topic'] as String? ?? '',
      topicLabel: json['topic_label'] as String? ?? '',
      questionType: json['question_type'] as String? ?? '',
      label: json['label'] as String? ?? '',
      difficulty: json['difficulty'] as String? ?? 'medium',
      level: (json['level'] as num?)?.toDouble() ?? 0.0,
      attempts: json['attempts'] as int? ?? 0,
      correct: json['correct'] as int? ?? 0,
      status: json['status'] as String? ?? 'untouched',
      hasLesson: json['has_lesson'] as bool? ?? false,
    );
  }
}

class Suggestion {
  final String kind;
  final String title;
  final String reason;
  final String? topic;
  final String? skillKey;
  final double level;

  Suggestion({
    required this.kind,
    required this.title,
    required this.reason,
    this.topic,
    this.skillKey,
    required this.level,
  });

  factory Suggestion.fromJson(Map<String, dynamic> json) {
    return Suggestion(
      kind: json['kind'] as String? ?? '',
      title: json['title'] as String? ?? '',
      reason: json['reason'] as String? ?? '',
      topic: json['topic'] as String?,
      skillKey: json['skill_key'] as String?,
      level: (json['level'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class Profile {
  final double score;
  final int attempts;
  final int correct;
  final double accuracy;
  final List<Skill> skills;
  final List<Suggestion> suggestions;

  Profile({
    required this.score,
    required this.attempts,
    required this.correct,
    required this.accuracy,
    required this.skills,
    required this.suggestions,
  });

  factory Profile.fromJson(Map<String, dynamic> json) {
    final level = json['level'] as Map<String, dynamic>? ?? {};
    return Profile(
      score: (level['score'] as num?)?.toDouble() ?? 0.0,
      attempts: level['attempts'] as int? ?? 0,
      correct: level['correct'] as int? ?? 0,
      accuracy: (level['accuracy'] as num?)?.toDouble() ?? 0.0,
      skills: ((json['skills'] as List<dynamic>?) ?? [])
          .map((s) => Skill.fromJson(s as Map<String, dynamic>))
          .toList(),
      suggestions: ((json['suggestions'] as List<dynamic>?) ?? [])
          .map((s) => Suggestion.fromJson(s as Map<String, dynamic>))
          .toList(),
    );
  }
}
