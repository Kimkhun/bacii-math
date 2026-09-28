/// Variation table of a function study (sign of f' + arrows + values).
/// Mirrors the `variation_table` payload rendered by web's VariationTable
/// (web/src/components/StructureModal.tsx).
class VariationTable {
  final List<String> columns;
  final List<String> derivativeSign;
  final List<String> arrows;
  final List<String> funcValues;

  VariationTable({
    required this.columns,
    this.derivativeSign = const [],
    this.arrows = const [],
    this.funcValues = const [],
  });

  static List<String> _strings(dynamic v) =>
      ((v as List?) ?? const []).map((e) => e?.toString() ?? '').toList();

  static VariationTable? fromJson(dynamic json) {
    if (json is! Map<String, dynamic>) return null;
    final cols = _strings(json['columns']);
    if (cols.length < 2) return null;
    return VariationTable(
      columns: cols,
      derivativeSign: _strings(json['derivative_sign']),
      arrows: _strings(json['arrows']),
      funcValues: _strings(json['func_values']),
    );
  }
}
