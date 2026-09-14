class Attempt {
  final String id;
  final String topic;
  final String questionType;
  final String difficulty;
  final String prompt;
  final String expectedAnswer;
  final String userAnswer;
  final bool correct;
  final String reason;
  final String createdAt;

  Attempt({
    required this.id,
    required this.topic,
    required this.questionType,
    required this.difficulty,
    required this.prompt,
    required this.expectedAnswer,
    required this.userAnswer,
    required this.correct,
    required this.reason,
    required this.createdAt,
  });

  factory Attempt.fromJson(Map<String, dynamic> json) {
    return Attempt(
      id: json['id'] as String? ?? '',
      topic: json['topic'] as String? ?? '',
      questionType: json['question_type'] as String? ?? '',
      difficulty: json['difficulty'] as String? ?? 'medium',
      prompt: json['prompt'] as String? ?? '',
      expectedAnswer: json['expected_answer'] as String? ?? '',
      userAnswer: json['user_answer'] as String? ?? '',
      correct: json['correct'] as bool? ?? false,
      reason: json['reason'] as String? ?? '',
      createdAt: json['created_at'] as String? ?? '',
    );
  }
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

  factory TopicStat.fromJson(Map<String, dynamic> json) {
    return TopicStat(
      questionType: json['question_type'] as String? ?? '',
      attempts: json['attempts'] as int? ?? 0,
      correct: json['correct'] as int? ?? 0,
    );
  }
}

class Stats {
  final int totalAttempts;
  final int correct;
  final double accuracy;
  final List<TopicStat> byTopic;

  Stats({
    required this.totalAttempts,
    required this.correct,
    required this.accuracy,
    required this.byTopic,
  });

  factory Stats.fromJson(Map<String, dynamic> json) {
    return Stats(
      totalAttempts: json['total_attempts'] as int? ?? 0,
      correct: json['correct'] as int? ?? 0,
      accuracy: (json['accuracy'] as num?)?.toDouble() ?? 0.0,
      byTopic: ((json['by_topic'] as List<dynamic>?) ?? [])
          .map((t) => TopicStat.fromJson(t as Map<String, dynamic>))
          .toList(),
    );
  }
}
