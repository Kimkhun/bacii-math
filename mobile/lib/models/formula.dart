class FormulaVariant {
  final String topic;
  final String questionType;
  final String? variant;
  final String difficulty;

  FormulaVariant({
    required this.topic,
    required this.questionType,
    this.variant,
    required this.difficulty,
  });

  factory FormulaVariant.fromJson(Map<String, dynamic> json) => FormulaVariant(
        topic: json['topic'] as String? ?? '',
        questionType: json['question_type'] as String? ?? '',
        variant: json['variant'] as String?,
        difficulty: json['difficulty'] as String? ?? 'medium',
      );
}

class FormulaEntry {
  final String id;
  final String? nameEn;
  final String nameKm;
  final String? latex;
  final double weight;
  final List<String> formulas;
  final List<FormulaVariant> variants;

  FormulaEntry({
    required this.id,
    this.nameEn,
    required this.nameKm,
    this.latex,
    required this.weight,
    required this.formulas,
    this.variants = const [],
  });

  factory FormulaEntry.fromJson(Map<String, dynamic> json) {
    return FormulaEntry(
      id: json['id'] as String? ?? '',
      nameEn: json['name_en'] as String?,
      nameKm: json['name_km'] as String? ?? '',
      latex: json['latex'] as String?,
      weight: (json['weight'] as num?)?.toDouble() ?? 1.0,
      formulas:
          (json['formulas'] as List<dynamic>?)?.map((e) => e.toString()).toList() ??
              [],
      variants: ((json['variants'] as List<dynamic>?) ?? [])
          .map((v) => FormulaVariant.fromJson(v as Map<String, dynamic>))
          .toList(),
    );
  }
}

class FormulaTopic {
  final String topic;
  final List<FormulaEntry> entries;

  FormulaTopic({required this.topic, required this.entries});

  factory FormulaTopic.fromJson(Map<String, dynamic> json) {
    return FormulaTopic(
      topic: json['topic'] as String? ?? '',
      entries: ((json['entries'] as List<dynamic>?) ?? [])
          .map((e) => FormulaEntry.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class FormulaCatalog {
  final List<FormulaTopic> topics;

  FormulaCatalog({required this.topics});

  factory FormulaCatalog.fromJson(Map<String, dynamic> json) {
    return FormulaCatalog(
      topics: ((json['topics'] as List<dynamic>?) ?? [])
          .map((t) => FormulaTopic.fromJson(t as Map<String, dynamic>))
          .toList(),
    );
  }
}
