import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../core/api/api_client.dart';
import '../core/theme/app_theme.dart';
import '../models/template.dart';
import 'function_graph.dart';
import 'math_text.dart';
import 'variation_table.dart';

// Params that describe the rendered problem rather than a tunable knob.
const _hiddenParams = {
  'expr', 'var', 'variant', 'lower', 'upper', 'point', 'formula_name', 'curated_technique',
};

// Backend question_km strings use $...$ math markers; normalise to \( \).
String _kmMath(String s) => s.replaceAllMapped(RegExp(r'\$(.+?)\$'), (m) => '\\(${m[1]}\\)');

List<String> _cleanLines(String raw) =>
    raw.split(RegExp(r'\\\\|\r?\n')).map((s) => s.trim()).where((s) => s.isNotEmpty).toList();

/// Opens the admin template inspector (port of web StructureModal).
Future<void> showStructureDialog(BuildContext context, TemplateStructure st, {String? topic}) {
  return showDialog(
    context: context,
    builder: (_) => StructureDialog(structure: st, topic: topic),
  );
}

/// Admin template inspector: the exam statement, pre-generated variants and
/// an interactive parameter picker (re-solved by SymPy on the server), the
/// step-by-step solution (per part, Khmer AI or file override), plus
/// "Practice" (open it on the canvas) and "Generate" (re-verify + narrate).
class StructureDialog extends StatefulWidget {
  final TemplateStructure structure;
  final String? topic;

  const StructureDialog({super.key, required this.structure, this.topic});

  @override
  State<StructureDialog> createState() => _StructureDialogState();
}

class _StructureDialogState extends State<StructureDialog> {
  final ApiClient _api = ApiClient();
  late TemplateStructure _st = widget.structure;
  int _variantIdx = 0;
  Map<String, dynamic>? _customParams;
  CustomSolveResult? _custom;
  bool _solving = false;
  bool _regenerating = false;
  bool _aiMode = true; // "ខ្មែរ (AI)" vs "ខ្មែរ (Override)"
  String? _error;

  @override
  void initState() {
    super.initState();
    final id = _st.id;
    // Variants for these families are only produced on demand.
    if ((id.startsWith('limit:') ||
            id.startsWith('integral:') ||
            id.startsWith('curated_') ||
            id.startsWith('int_')) &&
        _st.variants.isEmpty) {
      _regenerate();
    }
  }

  Future<void> _regenerate() async {
    setState(() {
      _regenerating = true;
      _error = null;
    });
    try {
      final fresh = await _api.regenerateStructure(_st.id);
      if (!mounted) return;
      setState(() {
        _st = fresh;
        _variantIdx = 0;
        _customParams = null;
        _custom = null;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _regenerating = false);
    }
  }

  TemplateVariant? get _activeVariant => _st.variants.isEmpty
      ? null
      : _st.variants[_variantIdx.clamp(0, _st.variants.length - 1)];

  Map<String, dynamic>? get _activeParams =>
      _customParams ?? _activeVariant?.params ?? _st.sampleParams;

  // Values seen for each tunable param across variants + the sample.
  Map<String, List<Object?>> get _paramChoices {
    final choices = <String, List<Object?>>{};
    void collect(Map<String, dynamic>? params) {
      params?.forEach((k, v) {
        if (_hiddenParams.contains(k)) return;
        final list = choices.putIfAbsent(k, () => []);
        if (!list.any((e) => '$e' == '$v')) list.add(v);
      });
    }

    for (final v in _st.variants) {
      collect(v.params);
    }
    collect(_st.sampleParams);
    for (final list in choices.values) {
      list.sort((a, b) {
        final na = num.tryParse('$a'), nb = num.tryParse('$b');
        if (na != null && nb != null) return na.compareTo(nb);
        return '$a'.compareTo('$b');
      });
    }
    return choices;
  }

  Future<void> _selectParam(String key, Object? value) async {
    final updated = {
      ...(_activeVariant?.params ?? _st.sampleParams ?? const {}),
      ...?_customParams,
      key: value,
    };
    setState(() => _customParams = updated);
    // Picking a combination that is already a preset just selects it.
    final match = _st.variants.indexWhere((v) => updated.keys
        .where((k) => !_hiddenParams.contains(k))
        .every((k) => '${v.params[k]}' == '${updated[k]}'));
    if (match >= 0) {
      setState(() {
        _variantIdx = match;
        _custom = null;
      });
      return;
    }
    setState(() => _solving = true);
    try {
      final res = await _api.solveCustomStructure(_st.id, updated);
      if (mounted) setState(() => _custom = res);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _solving = false);
    }
  }

  void _practice() {
    final q = <String, String>{
      'template': _st.id,
      if (widget.topic != null) 'topic': widget.topic!,
      if (_st.difficulty.isNotEmpty) 'difficulty': _st.difficulty,
    };
    final router = GoRouter.of(context);
    Navigator.of(context).pop();
    router.go(Uri(path: '/practice', queryParameters: q).toString());
  }

  @override
  Widget build(BuildContext context) {
    final custom = _custom;
    final v = _activeVariant;
    final rawPrompt = custom != null
        ? (custom.promptLatex.isNotEmpty ? custom.promptLatex : custom.prompt)
        : v != null
            ? (v.promptLatex ?? v.prompt ?? '')
            : (_st.samplePromptLatex ?? _st.samplePrompt);
    final prompt = rawPrompt.replaceFirst(RegExp(r'^Find\s+', caseSensitive: false), '')
        .replaceAll(r'\log', r'\ln');
    final rawAnswer = custom != null
        ? (custom.answerLatex.isNotEmpty ? custom.answerLatex : custom.answerExact)
        : v != null
            ? (v.answerLatex ?? v.answerExact ?? '')
            : (_st.sampleAnswerLatex ?? _st.sampleAnswer);
    final answer = rawAnswer.replaceAll(r'\log', r'\ln');
    final steps = custom?.steps ?? v?.steps ?? const <VariantStep>[];

    // Group parts by exam section (label prefix before the first '.').
    final sections = <String, List<TemplateStructurePart>>{};
    for (final p in _st.parts) {
      sections.putIfAbsent(p.label.split('.').first, () => []).add(p);
    }

    return Dialog(
      insetPadding: const EdgeInsets.all(12),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 820, maxHeight: 760),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _topBar(),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                child: Text(_error!, style: const TextStyle(color: AppTheme.errorRed, fontSize: 12)),
              ),
            Flexible(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _examHeader(prompt),
                    const SizedBox(height: 16),
                    Text(
                      _aiMode
                          ? 'ដំណោះស្រាយលម្អិតផ្លូវការ (Official Step-by-Step Solution)'
                          : 'ដំណោះស្រាយឯកសារ (File Override Solution)',
                      style: const TextStyle(
                          fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.slate600),
                    ),
                    const Divider(),
                    if (sections.isNotEmpty)
                      for (final e in sections.entries) _sectionCard(e.key, e.value, prompt)
                    else if (steps.isNotEmpty)
                      _card(Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          for (int i = 0; i < steps.length; i++) _stepTile(i, steps[i]),
                          if (answer.isNotEmpty) _answerLine('\\($answer\\)'),
                        ],
                      ))
                    else if (answer.isNotEmpty)
                      _card(_answerLine('\\($answer\\)'))
                    else if (_regenerating)
                      _card(const Padding(
                        padding: EdgeInsets.all(16),
                        child: Center(
                            child: Text('កំពុងទាញយកដំណោះស្រាយលម្អិត... (Loading solution...)',
                                style: TextStyle(color: AppTheme.slate600))),
                      ))
                    else
                      _card(Column(
                        children: [
                          const Text('មិនទាន់មានទិន្នន័យដំណោះស្រាយនៅក្នុងម៉ូដាល់នេះនៅឡើយទេ',
                              style: TextStyle(color: AppTheme.slate600, fontSize: 13)),
                          const SizedBox(height: 8),
                          ElevatedButton(
                            onPressed: _regenerate,
                            child: const Text('ទាញយកដំណោះស្រាយ និងវ៉ារ្យ៉ង់ឥឡូវនេះ (Fetch Variants & Solution)',
                                style: TextStyle(fontSize: 12)),
                          ),
                        ],
                      )),
                    if (_st.formulaTags.isNotEmpty) ...[
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 6,
                        runSpacing: 4,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          const Text('Formula tags:',
                              style: TextStyle(fontSize: 12, color: AppTheme.slate600)),
                          for (final t in _st.formulaTags) _code(t),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _topBar() {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 10, 8, 10),
      decoration: const BoxDecoration(
        color: AppTheme.slate50,
        border: Border(bottom: BorderSide(color: AppTheme.slate200)),
      ),
      child: Wrap(
        spacing: 8,
        runSpacing: 6,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          _code(_st.id),
          if (_st.sourceLabels.isNotEmpty)
            Text(_st.sourceLabels.join(', '),
                style: const TextStyle(fontSize: 12, color: AppTheme.slate600)),
          OutlinedButton.icon(
            onPressed: _practice,
            icon: const Icon(Icons.edit_outlined, size: 14),
            label: const Text('Practice', style: TextStyle(fontSize: 12)),
            style: OutlinedButton.styleFrom(
              foregroundColor: const Color(0xFF78350F),
              backgroundColor: const Color(0xFFFFFBEB),
              side: const BorderSide(color: Color(0xFFFCD34D)),
              visualDensity: VisualDensity.compact,
            ),
          ),
          OutlinedButton(
            onPressed: _regenerating ? null : _regenerate,
            style: OutlinedButton.styleFrom(visualDensity: VisualDensity.compact),
            child: Text(_regenerating ? '🔄 Generating...' : '🔄 Generate',
                style: const TextStyle(fontSize: 12)),
          ),
          ToggleButtons(
            isSelected: [_aiMode, !_aiMode],
            onPressed: (i) => setState(() => _aiMode = i == 0),
            borderRadius: BorderRadius.circular(6),
            constraints: const BoxConstraints(minHeight: 30, minWidth: 64),
            textStyle: const TextStyle(fontSize: 12),
            children: const [Text('ខ្មែរ (AI)'), Text('ខ្មែរ (Override)')],
          ),
          IconButton(
            onPressed: () => Navigator.of(context).pop(),
            icon: const Icon(Icons.close),
            tooltip: 'Close',
          ),
        ],
      ),
    );
  }

  Widget _examHeader(String prompt) {
    final params = (_activeParams ?? const <String, dynamic>{})
        .entries
        .where((e) => !_hiddenParams.contains(e.key))
        .toList();
    final choices = _paramChoices;
    const sky = Color(0xFF0369A1);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF0F9FF),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFBAE6FD)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('ប្រធានវិញ្ញាសា (Exam Problem)',
              style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: sky)),
          const SizedBox(height: 4),
          MathText(
            text: _st.patternLatex != null ? '\\(${_st.patternLatex}\\)' : _st.pattern,
            textStyle: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          if (_st.variants.length > 1) ...[
            const Divider(color: Color(0xFFE0F2FE)),
            const Text('វ៉ារ្យ៉ង់គំរូ (Variants):',
                style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: sky)),
            const SizedBox(height: 4),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (int i = 0; i < _st.variants.length; i++)
                  ChoiceChip(
                    visualDensity: VisualDensity.compact,
                    selected: _custom == null && i == _variantIdx,
                    label: Text(_variantLabel(_st.variants[i]),
                        style: const TextStyle(fontSize: 11, fontFamily: 'monospace')),
                    onSelected: (_) => setState(() {
                      _variantIdx = i;
                      _customParams = null;
                      _custom = null;
                    }),
                  ),
                if (_custom != null)
                  const Chip(
                    visualDensity: VisualDensity.compact,
                    backgroundColor: AppTheme.accentAmber,
                    label: Text('Custom Mix ✨',
                        style: TextStyle(fontSize: 11, color: Colors.white)),
                  ),
              ],
            ),
          ],
          if (params.isNotEmpty) ...[
            const Divider(color: Color(0xFFE0F2FE)),
            Row(
              children: [
                const Expanded(
                  child: Text('ប៉ារ៉ាម៉ែត្រ (Interactive Parameters):',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: sky)),
                ),
                if (_solving)
                  const Text('កំពុងគណនា (Calculating)...',
                      style: TextStyle(fontSize: 11, color: AppTheme.accentAmberDark)),
              ],
            ),
            const SizedBox(height: 4),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: [
                for (final p in params)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFFBAE6FD)),
                    ),
                    child: Wrap(
                      spacing: 4,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        Text('${p.key}:',
                            style: const TextStyle(
                                fontSize: 12, fontWeight: FontWeight.bold, fontFamily: 'monospace')),
                        for (final val in (choices[p.key]?.isNotEmpty ?? false)
                            ? choices[p.key]!
                            : <Object?>[p.value])
                          InkWell(
                            onTap: _solving ? null : () => _selectParam(p.key, val),
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: '${p.value}' == '$val' ? sky : const Color(0xFFF0F9FF),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text('$val',
                                  style: TextStyle(
                                      fontSize: 12,
                                      fontFamily: 'monospace',
                                      color: '${p.value}' == '$val' ? Colors.white : sky)),
                            ),
                          ),
                      ],
                    ),
                  ),
              ],
            ),
          ],
          if (_st.technique != null && _st.technique!.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(_st.technique!, style: const TextStyle(fontSize: 13, color: AppTheme.slate600)),
          ],
          if (prompt.isNotEmpty) ...[
            const SizedBox(height: 8),
            for (final line in _cleanLines(prompt))
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: MathText(
                  text: line.contains(r'$') || line.contains(r'\(') || line.contains(r'\[')
                      ? line
                      : '\\($line\\)',
                  textStyle: const TextStyle(fontSize: 15),
                ),
              ),
          ],
        ],
      ),
    );
  }

  String _variantLabel(TemplateVariant v) {
    final summary = v.params.entries
        .where((e) => !_hiddenParams.contains(e.key))
        .map((e) => '${e.key} = ${e.value}')
        .join(', ');
    return 'Variant ${v.variantIndex}${summary.isNotEmpty ? ' ($summary)' : ''}';
  }

  Widget _sectionCard(String sec, List<TemplateStructurePart> parts, String prompt) {
    return _card(Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        MathText(
          text: _kmMath(_sectionPrompt(sec, prompt, parts)),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        const Divider(),
        for (final p in parts) _partBlock(p),
      ],
    ));
  }

  static const _kmDigits = {
    '1': '១', '2': '២', '3': '៣', '4': '៤', '5': '៥', '6': '៦', '7': '៧', '8': '៨', '9': '៩',
  };

  String _sectionPrompt(String sec, String prompt, List<TemplateStructurePart> parts) {
    final kmSec = _kmDigits[sec] ?? sec;
    final re = RegExp('^(?:${RegExp.escape(sec)}|$kmSec)[.\\s]', caseSensitive: false);
    for (final l in _cleanLines(prompt)) {
      if (re.hasMatch(l)) return l;
    }
    final qs = parts.map((p) => p.questionKm?.trim() ?? '').where((q) => q.isNotEmpty).toList();
    if (qs.isNotEmpty) return '$kmSec. ${qs.join(' ')}';
    return 'សំណួរទី $kmSec';
  }

  Widget _partBlock(TemplateStructurePart part) {
    final kmPart = _aiMode
        ? _st.solutionKmParts.where((k) => k.label == part.label).firstOrNull
        : null;
    final isDraw = part.want == 'draw' || part.answerKind == 'draw';
    final question = part.questionKm;
    final answer = (kmPart != null && kmPart.answerKhmer.isNotEmpty)
        ? kmPart.answerKhmer
        : (part.answerDisplay ?? part.answerLatex ?? part.answer);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (question != null && question.isNotEmpty)
            MathText(
              text: '+ ${_kmMath(question.endsWith('៖') || question.endsWith(':') ? question : '$question ៖')}',
              textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
            ),
          if (kmPart != null)
            for (final s in kmPart.steps)
              Padding(
                padding: const EdgeInsets.only(left: 12, top: 4),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    MathText(text: _kmMath(s.$1), textStyle: const TextStyle(fontSize: 14)),
                    // Show the display equation unless the sentence already has it.
                    if (s.$2.isNotEmpty && !(s.$1.contains('=') || s.$1.contains(s.$2)))
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 2),
                        child: SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: MathText(text: '\\[${s.$2}\\]'),
                        ),
                      ),
                  ],
                ),
              ),
          if (part.signTable != null)
            Padding(
              padding: const EdgeInsets.only(left: 12, top: 6),
              child: _SignTableView(st: part.signTable!),
            ),
          if (part.variationTable != null)
            Padding(
              padding: const EdgeInsets.only(left: 12, top: 6),
              child: VariationTableView(vt: part.variationTable!),
            ),
          if (isDraw && _st.graph != null)
            Padding(
              padding: const EdgeInsets.only(left: 12, top: 6),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('ក្រាប C និងបន្ទាត់ប៉ះ T ៖',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                  FunctionGraph(graph: _st.graph!),
                ],
              ),
            ),
          if (!_aiMode && part.technique != null && part.technique!.isNotEmpty)
            for (final ln in part.technique!
                .replaceFirst('។', '។\n')
                .split('\n')
                .map((l) => l.trim())
                .where((l) => l.isNotEmpty))
              Padding(
                padding: const EdgeInsets.only(left: 12, top: 4),
                child: MathText(text: _kmMath(ln), textStyle: const TextStyle(fontSize: 14)),
              ),
          if (answer.isNotEmpty && !isDraw)
            Padding(
              padding: const EdgeInsets.only(left: 12, top: 4),
              child: _answerLine(_kmMath(answer),
                  prefix: !(answer.startsWith('ដូចនេះ') || answer.startsWith('ចម្លើយ'))),
            ),
        ],
      ),
    );
  }

  Widget _stepTile(int i, VariantStep step) {
    final detail = step.detail.replaceAll(r'\log', r'\ln');
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (step.title.isNotEmpty)
            Row(
              children: [
                CircleAvatar(
                  radius: 10,
                  backgroundColor: const Color(0xFFE0F2FE),
                  child: Text('${i + 1}',
                      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                ),
                const SizedBox(width: 8),
                Flexible(
                  child: MathText(
                      text: _kmMath(step.title),
                      textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                ),
              ],
            ),
          if (detail.isNotEmpty)
            Padding(
              padding: EdgeInsets.only(left: step.title.isNotEmpty ? 28 : 0, top: 2),
              child: MathText(text: _kmMath(detail), textStyle: const TextStyle(fontSize: 13)),
            ),
          if (step.formula != null && step.formula!.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(left: 28, top: 2),
              child: Row(children: [
                const Text('Formula: ', style: TextStyle(fontSize: 11, color: AppTheme.slate600)),
                _code(step.formula!),
              ]),
            ),
        ],
      ),
    );
  }

  Widget _answerLine(String math, {bool prefix = true}) => Wrap(
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          if (prefix)
            const Text('ចម្លើយ៖ ',
                style: TextStyle(fontWeight: FontWeight.w600, color: AppTheme.slate600)),
          MathText(text: math, textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
        ],
      );

  Widget _card(Widget child) => Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppTheme.slate200),
        ),
        child: child,
      );

  Widget _code(String text) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration:
            BoxDecoration(color: AppTheme.slate100, borderRadius: BorderRadius.circular(4)),
        child: Text(text, style: const TextStyle(fontFamily: 'monospace', fontSize: 11)),
      );
}

/// Sign table: x row with the roots, then the expression's sign per
/// interval — a 0 on a root, a double bar where it is undefined.
class _SignTableView extends StatelessWidget {
  final SignTable st;
  const _SignTableView({required this.st});

  @override
  Widget build(BuildContext context) {
    const ink = Color(0xFF0F172A);
    Widget math(String s) => MathText(text: '\\($s\\)', textStyle: const TextStyle(fontSize: 12));
    final roots = st.cols.sublist(1, st.cols.length - 1);
    // sign, root marker, sign, ... — exactly one cell per x-row slot.
    final cells = List<String>.generate(
        2 * roots.length + 1, (i) => i < st.values.length ? st.values[i] : '');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('តារាងសញ្ញា (Sign Table)',
            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppTheme.slate600)),
        const SizedBox(height: 6),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppTheme.slate200),
            ),
            child: Table(
              defaultColumnWidth: const IntrinsicColumnWidth(),
              defaultVerticalAlignment: TableCellVerticalAlignment.middle,
              children: [
                TableRow(
                  decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: ink))),
                  children: [
                    const Padding(
                      padding: EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                      child: Text('x', style: TextStyle(fontStyle: FontStyle.italic)),
                    ),
                    Padding(padding: const EdgeInsets.all(6), child: math(st.cols.first)),
                    for (final r in roots) ...[
                      const SizedBox(width: 36),
                      Padding(padding: const EdgeInsets.all(6), child: math(r)),
                    ],
                    const SizedBox(width: 36),
                    Padding(padding: const EdgeInsets.all(6), child: math(st.cols.last)),
                  ],
                ),
                TableRow(children: [
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                    child: math(st.label),
                  ),
                  const SizedBox(),
                  for (int i = 0; i < cells.length; i++)
                    Center(
                      child: i.isOdd
                          ? Text(cells[i] == '‖' || cells[i] == '||' ? '‖' : '0',
                              style: const TextStyle(fontWeight: FontWeight.bold))
                          : Text(cells[i],
                              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
                    ),
                  const SizedBox(),
                ]),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
