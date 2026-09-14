class FormulaEntry {
  final String id;
  final String? nameEn;
  final String nameKm;
  final String? latex;
  final double weight;
  final List<String> formulas;

  FormulaEntry({
    required this.id,
    this.nameEn,
    required this.nameKm,
    this.latex,
    required this.weight,
    required this.formulas,
  });

  factory FormulaEntry.fromJson(Map<String, dynamic> json) {
    return FormulaEntry(
      id: json['id'] as String? ?? '',
      nameEn: json['name_en'] as String?,
      nameKm: json['name_km'] as String? ?? '',
      latex: json['latex'] as String?,
      weight: (json['weight'] as num?)?.toDouble() ?? 1.0,
      formulas: (json['formulas'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
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
