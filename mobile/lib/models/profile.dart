/// Skill-progress / profile models. Mirrors the Profile tree in
/// web/src/lib/api.ts (SkillEstimate, Skill, FormulaSkill, TopicProgress,
/// Aggregate, Suggestion, Profile).

class WeakFormula {
  final String formula;
  final String name;
  final double level;

  WeakFormula({required this.formula, required this.name, required this.level});

  factory WeakFormula.fromJson(Map<String, dynamic> json) => WeakFormula(
        formula: json['formula'] as String? ?? '',
        name: json['name'] as String? ?? '',
        level: (json['level'] as num?)?.toDouble() ?? 0,
      );
}

class Skill {
  final String key;
  final String topic;
  final String topicLabel;
  final String questionType;
  final String? variant;
  final String label;
  final String difficulty;
  final bool practice;
  final bool forceable;
  final double rate;
  final double evidence;
  final double ability;
  final double confidence;
  final double level;
  final int attempts;
  final int correct;
  final int streak;
  final int bestStreak;
  final int daysIdle;
  final String? lastSeenAt;
  final String status;
  final String band;
  final List<WeakFormula> weakFormulas;
  final bool hasLesson;

  Skill({
    required this.key,
    required this.topic,
    required this.topicLabel,
    required this.questionType,
    this.variant,
    required this.label,
    required this.difficulty,
    this.practice = true,
    this.forceable = false,
    this.rate = 0,
    this.evidence = 0,
    this.ability = 0,
    this.confidence = 0,
    required this.level,
    required this.attempts,
    required this.correct,
    this.streak = 0,
    this.bestStreak = 0,
    this.daysIdle = 0,
    this.lastSeenAt,
    required this.status,
    this.band = '',
    this.weakFormulas = const [],
    this.hasLesson = false,
  });

  factory Skill.fromJson(Map<String, dynamic> json) => Skill(
        key: json['key'] as String? ?? '',
        topic: json['topic'] as String? ?? '',
        topicLabel: json['topic_label'] as String? ?? '',
        questionType: json['question_type'] as String? ?? '',
        variant: json['variant'] as String?,
        label: json['label'] as String? ?? '',
        difficulty: json['difficulty'] as String? ?? 'medium',
        practice: json['practice'] as bool? ?? true,
        forceable: json['forceable'] as bool? ?? false,
        rate: (json['rate'] as num?)?.toDouble() ?? 0,
        evidence: (json['evidence'] as num?)?.toDouble() ?? 0,
        ability: (json['ability'] as num?)?.toDouble() ?? 0,
        confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
        level: (json['level'] as num?)?.toDouble() ?? 0,
        attempts: json['attempts'] as int? ?? 0,
        correct: json['correct'] as int? ?? 0,
        streak: json['streak'] as int? ?? 0,
        bestStreak: json['best_streak'] as int? ?? 0,
        daysIdle: json['days_idle'] as int? ?? 0,
        lastSeenAt: json['last_seen_at'] as String?,
        status: json['status'] as String? ?? 'untouched',
        band: json['band'] as String? ?? '',
        weakFormulas: ((json['weak_formulas'] as List?) ?? [])
            .map((f) => WeakFormula.fromJson(f as Map<String, dynamic>))
            .toList(),
        hasLesson: json['has_lesson'] as bool? ?? false,
      );
}

class FormulaSkill {
  final String formula;
  final String name;
  final String? latex;
  final String? topic;
  final String? topicLabel;
  final double level;
  final int attempts;
  final int correct;
  final int daysIdle;
  final String status;
  final String? skillKey;

  FormulaSkill({
    required this.formula,
    required this.name,
    this.latex,
    this.topic,
    this.topicLabel,
    required this.level,
    required this.attempts,
    required this.correct,
    this.daysIdle = 0,
    this.status = '',
    this.skillKey,
  });

  factory FormulaSkill.fromJson(Map<String, dynamic> json) => FormulaSkill(
        formula: json['formula'] as String? ?? '',
        name: json['name'] as String? ?? '',
        latex: json['latex'] as String?,
        topic: json['topic'] as String?,
        topicLabel: json['topic_label'] as String?,
        level: (json['level'] as num?)?.toDouble() ?? 0,
        attempts: json['attempts'] as int? ?? 0,
        correct: json['correct'] as int? ?? 0,
        daysIdle: json['days_idle'] as int? ?? 0,
        status: json['status'] as String? ?? '',
        skillKey: json['skill_key'] as String?,
      );
}

class TopicProgress {
  final String topic;
  final String label;
  final bool practice;
  final bool engaged;
  final double score;
  final double syllabusScore;
  final double mastery;
  final double coverage;
  final int practised;
  final int total;
  final String band;
  final int skillsTotal;
  final int skillsPractised;
  final int attempts;
  final int correct;
  final String? strongest;
  final String? weakest;

  TopicProgress({
    required this.topic,
    required this.label,
    this.practice = true,
    this.engaged = false,
    required this.score,
    this.syllabusScore = 0,
    this.mastery = 0,
    this.coverage = 0,
    this.practised = 0,
    this.total = 0,
    this.band = '',
    this.skillsTotal = 0,
    this.skillsPractised = 0,
    this.attempts = 0,
    this.correct = 0,
    this.strongest,
    this.weakest,
  });

  factory TopicProgress.fromJson(Map<String, dynamic> json) => TopicProgress(
        topic: json['topic'] as String? ?? '',
        label: json['label'] as String? ?? '',
        practice: json['practice'] as bool? ?? true,
        engaged: json['engaged'] as bool? ?? false,
        score: (json['score'] as num?)?.toDouble() ?? 0,
        syllabusScore: (json['syllabus_score'] as num?)?.toDouble() ?? 0,
        mastery: (json['mastery'] as num?)?.toDouble() ?? 0,
        coverage: (json['coverage'] as num?)?.toDouble() ?? 0,
        practised: json['practised'] as int? ?? 0,
        total: json['total'] as int? ?? 0,
        band: json['band'] as String? ?? '',
        skillsTotal: json['skills_total'] as int? ?? 0,
        skillsPractised: json['skills_practised'] as int? ?? 0,
        attempts: json['attempts'] as int? ?? 0,
        correct: json['correct'] as int? ?? 0,
        strongest: json['strongest'] as String?,
        weakest: json['weakest'] as String?,
      );
}

class Suggestion {
  final String kind;
  final int priority;
  final String title;
  final String reason;
  final String? contrast;
  final String? detail;
  final String? topic;
  final String? topicLabel;
  final String? skillKey;
  final String? formula;
  final double level;

  Suggestion({
    required this.kind,
    this.priority = 0,
    required this.title,
    required this.reason,
    this.contrast,
    this.detail,
    this.topic,
    this.topicLabel,
    this.skillKey,
    this.formula,
    this.level = 0,
  });

  factory Suggestion.fromJson(Map<String, dynamic> json) => Suggestion(
        kind: json['kind'] as String? ?? '',
        priority: json['priority'] as int? ?? 0,
        title: json['title'] as String? ?? '',
        reason: json['reason'] as String? ?? '',
        contrast: json['contrast'] as String?,
        detail: json['detail'] as String?,
        topic: json['topic'] as String?,
        topicLabel: json['topic_label'] as String?,
        skillKey: json['skill_key'] as String?,
        formula: json['formula'] as String?,
        level: (json['level'] as num?)?.toDouble() ?? 0,
      );
}

class ProfileLevel {
  final double score;
  final double syllabusScore;
  final double mastery;
  final double coverage;
  final int practised;
  final int total;
  final String band;
  final int attempts;
  final int correct;
  final double accuracy;
  final int topicsStarted;
  final int topicsTotal;

  ProfileLevel({
    required this.score,
    this.syllabusScore = 0,
    this.mastery = 0,
    this.coverage = 0,
    this.practised = 0,
    this.total = 0,
    this.band = '',
    this.attempts = 0,
    this.correct = 0,
    this.accuracy = 0,
    this.topicsStarted = 0,
    this.topicsTotal = 0,
  });

  factory ProfileLevel.fromJson(Map<String, dynamic> json) => ProfileLevel(
        score: (json['score'] as num?)?.toDouble() ?? 0,
        syllabusScore: (json['syllabus_score'] as num?)?.toDouble() ?? 0,
        mastery: (json['mastery'] as num?)?.toDouble() ?? 0,
        coverage: (json['coverage'] as num?)?.toDouble() ?? 0,
        practised: json['practised'] as int? ?? 0,
        total: json['total'] as int? ?? 0,
        band: json['band'] as String? ?? '',
        attempts: json['attempts'] as int? ?? 0,
        correct: json['correct'] as int? ?? 0,
        accuracy: (json['accuracy'] as num?)?.toDouble() ?? 0,
        topicsStarted: json['topics_started'] as int? ?? 0,
        topicsTotal: json['topics_total'] as int? ?? 0,
      );
}

class ActivityDay {
  final String date;
  final int attempts;
  final int correct;

  ActivityDay({required this.date, required this.attempts, required this.correct});

  factory ActivityDay.fromJson(Map<String, dynamic> json) => ActivityDay(
        date: json['date'] as String? ?? '',
        attempts: json['attempts'] as int? ?? 0,
        correct: json['correct'] as int? ?? 0,
      );
}

class ProfileUser {
  final String id;
  final String email;
  final String plan;
  final String? memberSince;

  ProfileUser({
    required this.id,
    required this.email,
    required this.plan,
    this.memberSince,
  });

  factory ProfileUser.fromJson(Map<String, dynamic> json) => ProfileUser(
        id: json['id'] as String? ?? '',
        email: json['email'] as String? ?? '',
        plan: json['plan'] as String? ?? 'free',
        memberSince: json['member_since'] as String?,
      );
}

class Profile {
  final ProfileUser user;
  final ProfileLevel level;
  final List<TopicProgress> topics;
  final List<Skill> skills;
  final List<FormulaSkill> formulas;
  final List<Suggestion> suggestions;
  final List<ActivityDay> activity;

  Profile({
    required this.user,
    required this.level,
    required this.topics,
    required this.skills,
    required this.formulas,
    required this.suggestions,
    required this.activity,
  });

  factory Profile.fromJson(Map<String, dynamic> json) => Profile(
        user: ProfileUser.fromJson(
            (json['user'] as Map<String, dynamic>?) ?? const {}),
        level: ProfileLevel.fromJson(
            (json['level'] as Map<String, dynamic>?) ?? const {}),
        topics: ((json['topics'] as List?) ?? [])
            .map((t) => TopicProgress.fromJson(t as Map<String, dynamic>))
            .toList(),
        skills: ((json['skills'] as List?) ?? [])
            .map((s) => Skill.fromJson(s as Map<String, dynamic>))
            .toList(),
        formulas: ((json['formulas'] as List?) ?? [])
            .map((f) => FormulaSkill.fromJson(f as Map<String, dynamic>))
            .toList(),
        suggestions: ((json['suggestions'] as List?) ?? [])
            .map((s) => Suggestion.fromJson(s as Map<String, dynamic>))
            .toList(),
        activity: ((json['activity'] as List?) ?? [])
            .map((a) => ActivityDay.fromJson(a as Map<String, dynamic>))
            .toList(),
      );
}

class SkillCatalog {
  final List<String> topics;
  final Map<String, String> labels;
  final List<Skill> skills;

  SkillCatalog({required this.topics, required this.labels, required this.skills});

  factory SkillCatalog.fromJson(Map<String, dynamic> json) => SkillCatalog(
        topics:
            ((json['topics'] as List?) ?? []).map((e) => e.toString()).toList(),
        labels: ((json['labels'] as Map<String, dynamic>?) ?? {})
            .map((k, v) => MapEntry(k, v.toString())),
        skills: ((json['skills'] as List?) ?? [])
            .map((s) => Skill.fromJson(s as Map<String, dynamic>))
            .toList(),
      );
}
