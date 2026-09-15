import 'dart:convert';

import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../../core/theme/app_theme.dart';
import '../../models/admin.dart';
import '../../models/formula.dart';
import '../../models/template.dart';
import '../../widgets/function_graph.dart';
import '../../widgets/math_text.dart';

class AdminScreen extends StatefulWidget {
  const AdminScreen({super.key});

  @override
  State<AdminScreen> createState() => _AdminScreenState();
}

class _AdminScreenState extends State<AdminScreen> {
  final ApiClient _api = ApiClient();

  String _tab = 'overview';
  String _topicFilter = 'all';
  bool _busy = true;
  String? _error;

  FormulaCatalog? _catalog;
  TemplateSummary? _summary;
  final Map<String, TemplateStructuresTopic> _structures = {};
  final Set<String> _loadingTopics = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final results = await Future.wait([
        _api.getFormulas(),
        _api.templateSummary(),
      ]);
      setState(() {
        _catalog = results[0] as FormulaCatalog;
        _summary = results[1] as TemplateSummary;
      });
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _loadStructures(String topic) async {
    if (_structures.containsKey(topic) || _loadingTopics.contains(topic)) return;
    setState(() => _loadingTopics.add(topic));
    try {
      final res = await _api.templateStructures(topic);
      final t = res.topics.isNotEmpty ? res.topics.first : null;
      if (t != null) setState(() => _structures[topic] = t);
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loadingTopics.remove(topic));
    }
  }

  List<String> get _topics {
    final set = <String>{'all'};
    for (final t in _catalog?.topics ?? <FormulaTopic>[]) {
      set.add(t.topic);
    }
    for (final t in _summary?.topics ?? <TemplateSummaryTopic>[]) {
      set.add(t.topic);
    }
    return set.toList();
  }

  @override
  Widget build(BuildContext context) {
    if (_busy) return const Center(child: CircularProgressIndicator());
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 900),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text('Admin',
                  style: TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                      color: AppTheme.primaryNavy)),
              const SizedBox(height: 8),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(_error!, style: const TextStyle(color: AppTheme.errorRed)),
                ),
              _tabBar(),
              const SizedBox(height: 12),
              if (_tab != 'sandbox' && _tab != 'costs' && _tab != 'settings')
                _topicPills(),
              const SizedBox(height: 8),
              _tabBody(),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  Widget _tabBar() {
    const tabs = {
      'overview': 'Overview',
      'formulas': 'Formulas',
      'templates': 'Templates',
      'sandbox': 'Sandbox',
      'costs': 'Costs',
      'settings': 'Settings',
    };
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          for (final e in tabs.entries)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: ChoiceChip(
                label: Text(e.value, style: const TextStyle(fontSize: 12)),
                selected: _tab == e.key,
                onSelected: (_) {
                  setState(() => _tab = e.key);
                  if (e.key == 'templates') {
                    final needed = _topicFilter == 'all'
                        ? (_summary?.topics ?? []).map((t) => t.topic)
                        : [_topicFilter];
                    for (final tp in needed) {
                      _loadStructures(tp);
                    }
                  }
                },
              ),
            ),
        ],
      ),
    );
  }

  Widget _topicPills() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          for (final tp in _topics)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: ChoiceChip(
                label: Text(tp == 'all' ? 'All topics' : tp.replaceAll('_', ' '),
                    style: const TextStyle(fontSize: 12)),
                selected: _topicFilter == tp,
                onSelected: (_) {
                  setState(() => _topicFilter = tp);
                  if (_tab == 'templates') {
                    final needed = tp == 'all'
                        ? (_summary?.topics ?? []).map((t) => t.topic)
                        : [tp];
                    for (final t in needed) {
                      _loadStructures(t);
                    }
                  }
                },
              ),
            ),
        ],
      ),
    );
  }

  Widget _tabBody() {
    switch (_tab) {
      case 'formulas':
        return _formulasTab();
      case 'templates':
        return _templatesTab();
      case 'sandbox':
        return const _SandboxTab();
      case 'costs':
        return const _CostsTab();
      case 'settings':
        return const _SettingsTab();
      default:
        return _overviewTab();
    }
  }

  Widget _overviewTab() {
    final summary = _summary;
    if (summary == null) return const SizedBox.shrink();
    final overview = summary.topics
        .where((t) => _topicFilter == 'all' || t.topic == _topicFilter)
        .toList();
    final totalQt = summary.topics.fold<int>(0, (n, t) => n + t.questionTypes.length);
    final totalStruct =
        summary.topics.fold<int>(0, (n, t) => n + t.structureCount);
    final totalFormulas =
        (_catalog?.topics ?? []).fold<int>(0, (n, t) => n + t.entries.length);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            _statCard('Topics', '${summary.topics.length}'),
            _statCard('Question types', '$totalQt'),
            _statCard('Exercise types', '$totalStruct'),
            _statCard('Formulas', '$totalFormulas'),
          ],
        ),
        const SizedBox(height: 16),
        for (final t in overview)
          Card(
            margin: const EdgeInsets.only(bottom: 12),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(t.topic.replaceAll('_', ' '),
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      _tag('${t.questionTypes.length} question types'),
                      _tag('${t.structureCount} exercise types'),
                      if (t.curated > 0)
                        _tag('${t.curated} curated',
                            color: AppTheme.accentAmberLight),
                      for (final d in t.difficulties)
                        _tag(d, color: AppTheme.successGreenLight),
                    ],
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }

  Widget _formulasTab() {
    final visible = (_catalog?.topics ?? [])
        .where((t) => _topicFilter == 'all' || t.topic == _topicFilter);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final topic in visible) ...[
          Text(topic.topic.replaceAll('_', ' '),
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          for (final e in topic.entries)
            Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: 6,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        _code(e.id),
                        Text(e.nameEn ?? '',
                            style: const TextStyle(fontWeight: FontWeight.bold)),
                        if (e.nameKm.isNotEmpty)
                          Text(e.nameKm,
                              style: const TextStyle(color: AppTheme.slate600)),
                      ],
                    ),
                    if (e.latex != null && e.latex!.isNotEmpty) ...[
                      const SizedBox(height: 6),
                      MathText(text: '\$\$${e.latex}\$\$'),
                    ],
                  ],
                ),
              ),
            ),
          const SizedBox(height: 12),
        ],
      ],
    );
  }

  Widget _templatesTab() {
    final topics = _topicFilter == 'all'
        ? (_summary?.topics ?? []).map((t) => t.topic).toList()
        : [_topicFilter];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final topic in topics) ...[
          Text(topic.replaceAll('_', ' '),
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          if (!_structures.containsKey(topic))
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(
                  _loadingTopics.contains(topic)
                      ? 'Loading $topic structures…'
                      : 'Not loaded.',
                  style: const TextStyle(color: AppTheme.slate600)),
            )
          else
            for (final qt in _structures[topic]!.questionTypes) ...[
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Text(
                    '${qt.questionType.replaceAll('_', ' ')} · ${qt.structures.length}',
                    style: const TextStyle(
                        fontWeight: FontWeight.w600, color: AppTheme.slate600)),
              ),
              for (final st in qt.structures)
                Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: InkWell(
                    onTap: () => _showStructure(st),
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              _code(st.id),
                              const Spacer(),
                              if (st.sourceLabels.isNotEmpty)
                                Text(st.sourceLabels.join(', '),
                                    style: const TextStyle(
                                        fontSize: 11, color: AppTheme.slate600)),
                            ],
                          ),
                          const SizedBox(height: 6),
                          st.patternLatex != null
                              ? MathText(text: '\$${st.patternLatex}\$')
                              : Text(st.pattern),
                        ],
                      ),
                    ),
                  ),
                ),
            ],
          const SizedBox(height: 12),
        ],
      ],
    );
  }

  void _showStructure(TemplateStructure st) {
    showDialog(
      context: context,
      builder: (_) => Dialog(
        insetPadding: const EdgeInsets.all(16),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 640, maxHeight: 700),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    _code(st.id),
                    const Spacer(),
                    IconButton(
                        onPressed: () => Navigator.pop(context),
                        icon: const Icon(Icons.close)),
                  ],
                ),
                if (st.technique != null) ...[
                  Text(st.technique!,
                      style: const TextStyle(color: AppTheme.slate600)),
                  const SizedBox(height: 8),
                ],
                st.samplePromptLatex != null
                    ? MathText(text: '\$${st.samplePromptLatex}\$')
                    : Text(st.samplePrompt),
                const SizedBox(height: 8),
                Row(
                  children: [
                    const Text('Answer: ',
                        style: TextStyle(fontWeight: FontWeight.bold)),
                    Flexible(
                      child: MathText(
                          text:
                              '\$${st.sampleAnswerLatex ?? st.sampleAnswer}\$'),
                    ),
                  ],
                ),
                if (st.parts.isNotEmpty) ...[
                  const Divider(),
                  const Text('Parts & answers',
                      style: TextStyle(fontWeight: FontWeight.bold)),
                  for (final p in st.parts)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(children: [
                            _code(p.label),
                            const SizedBox(width: 6),
                            Flexible(
                                child: MathText(
                                    text: (p.questionKm ?? p.want ?? '')
                                        .replaceAll(RegExp(r'\$(.+?)\$'), r'\($1\)'))),
                          ]),
                          Text('→ ${p.answerDisplay ?? p.answer}',
                              style: const TextStyle(color: AppTheme.slate800)),
                        ],
                      ),
                    ),
                ],
                if (st.graph != null) ...[
                  const Divider(),
                  FunctionGraph(graph: st.graph!),
                ],
                if (st.formulaTags.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6,
                    runSpacing: 4,
                    children: [for (final t in st.formulaTags) _code(t)],
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _statCard(String label, String value) {
    return Container(
      width: 150,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppTheme.slate200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(value,
              style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
          Text(label,
              style: const TextStyle(fontSize: 12, color: AppTheme.slate600)),
        ],
      ),
    );
  }

  Widget _tag(String text, {Color color = AppTheme.slate100}) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration:
            BoxDecoration(color: color, borderRadius: BorderRadius.circular(6)),
        child: Text(text, style: const TextStyle(fontSize: 11)),
      );

  Widget _code(String text) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(
            color: AppTheme.slate100, borderRadius: BorderRadius.circular(4)),
        child: Text(text,
            style: const TextStyle(fontFamily: 'monospace', fontSize: 11)),
      );
}

// ---------------------------------------------------------------------------
// Sandbox tab
// ---------------------------------------------------------------------------

class _SandboxTab extends StatefulWidget {
  const _SandboxTab();

  @override
  State<_SandboxTab> createState() => _SandboxTabState();
}

class _SandboxTabState extends State<_SandboxTab> {
  final ApiClient _api = ApiClient();
  TemplateSummary? _summary;
  String _topic = '';
  String _questionType = '';
  List<TemplateStructure> _structures = [];
  String? _selectedStructure;
  final Map<String, TextEditingController> _params = {};
  final TextEditingController _lines = TextEditingController();
  bool _busy = false;
  String? _error;
  SandboxSolveResult? _solve;
  SandboxGradeResult? _grade;

  @override
  void initState() {
    super.initState();
    _init();
  }

  @override
  void dispose() {
    for (final c in _params.values) {
      c.dispose();
    }
    _lines.dispose();
    super.dispose();
  }

  Future<void> _init() async {
    try {
      final s = await _api.templateSummary();
      setState(() {
        _summary = s;
        if (s.topics.isNotEmpty) {
          _topic = s.topics.first.topic;
          _questionType = s.topics.first.questionTypes.isNotEmpty
              ? s.topics.first.questionTypes.first.questionType
              : '';
        }
      });
      _loadStructures();
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    }
  }

  Future<void> _loadStructures() async {
    if (_topic.isEmpty) return;
    setState(() => _structures = []);
    try {
      final res = await _api.templateStructures(_topic);
      final t = res.topics.isNotEmpty ? res.topics.first : null;
      setState(() => _structures =
          (t?.questionTypes ?? []).expand((qt) => qt.structures).toList());
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    }
  }

  List<TemplateSummaryQuestionType> get _qtOptions =>
      _summary?.topics
          .where((t) => t.topic == _topic)
          .expand((t) => t.questionTypes)
          .toList() ??
      [];

  Future<void> _loadSample(String structureId) async {
    setState(() => _busy = true);
    try {
      final sample =
          await _api.sandboxStructureSample(_topic, _questionType, structureId);
      for (final c in _params.values) {
        c.dispose();
      }
      _params.clear();
      sample.params.forEach((k, v) {
        _params[k] = TextEditingController(
            text: v is String ? v : jsonEncode(v));
      });
      setState(() {
        _selectedStructure = structureId;
        _solve = null;
        _grade = null;
      });
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Map<String, dynamic> _sendParams() {
    final out = <String, dynamic>{};
    _params.forEach((k, c) {
      final raw = c.text.trim();
      if (raw.isEmpty) {
        out[k] = '';
        return;
      }
      try {
        out[k] = jsonDecode(raw);
      } catch (_) {
        out[k] = c.text;
      }
    });
    return out;
  }

  Future<void> _runSolve() async {
    setState(() {
      _busy = true;
      _solve = null;
      _error = null;
    });
    try {
      final res = await _api.sandboxSolve(_topic, _questionType, _sendParams());
      setState(() => _solve = res);
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _runGrade() async {
    setState(() {
      _busy = true;
      _grade = null;
      _error = null;
    });
    try {
      final res = await _api.sandboxGrade(
          _topic, _questionType, _sendParams(), _lines.text);
      setState(() => _grade = res);
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final summary = _summary;
    if (summary == null) return const Center(child: CircularProgressIndicator());
    final structuresForType =
        _structures.where((s) => s.questionType == _questionType).toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (_error != null)
          Text(_error!, style: const TextStyle(color: AppTheme.errorRed)),
        Row(
          children: [
            Expanded(
              child: DropdownButtonFormField<String>(
                initialValue: _topic.isEmpty ? null : _topic,
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Topic', isDense: true),
                items: [
                  for (final t in summary.topics)
                    DropdownMenuItem(
                        value: t.topic, child: Text(t.topic.replaceAll('_', ' ')))
                ],
                onChanged: (v) {
                  if (v == null) return;
                  setState(() {
                    _topic = v;
                    final qts = _summary!.topics
                        .firstWhere((t) => t.topic == v)
                        .questionTypes;
                    _questionType =
                        qts.isNotEmpty ? qts.first.questionType : '';
                    _selectedStructure = null;
                  });
                  _loadStructures();
                },
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: DropdownButtonFormField<String>(
                initialValue: _questionType.isEmpty ? null : _questionType,
                isExpanded: true,
                decoration:
                    const InputDecoration(labelText: 'Type', isDense: true),
                items: [
                  for (final qt in _qtOptions)
                    DropdownMenuItem(
                        value: qt.questionType,
                        child: Text(qt.questionType.replaceAll('_', ' ')))
                ],
                onChanged: (v) => setState(() {
                  _questionType = v ?? '';
                  _selectedStructure = null;
                }),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        if (structuresForType.isNotEmpty)
          Container(
            constraints: const BoxConstraints(maxHeight: 180),
            decoration: BoxDecoration(
                border: Border.all(color: AppTheme.slate200),
                borderRadius: BorderRadius.circular(8)),
            child: ListView(
              shrinkWrap: true,
              children: [
                for (final s in structuresForType)
                  InkWell(
                    onTap: _busy ? null : () => _loadSample(s.id),
                    child: Container(
                      color: _selectedStructure == s.id
                          ? AppTheme.slate100
                          : null,
                      padding: const EdgeInsets.all(8),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${s.difficulty} · ${s.id}',
                              style: const TextStyle(
                                  fontSize: 10, color: AppTheme.slate600)),
                          s.patternLatex != null
                              ? MathText(text: '\$${s.patternLatex}\$')
                              : Text(s.pattern,
                                  style: const TextStyle(
                                      fontFamily: 'monospace', fontSize: 12)),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          ),
        const SizedBox(height: 12),
        const Text('Params', style: TextStyle(fontWeight: FontWeight.bold)),
        for (final key in _params.keys)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(
              children: [
                SizedBox(
                    width: 80,
                    child: Text(key,
                        style: const TextStyle(
                            fontFamily: 'monospace', fontSize: 12))),
                Expanded(
                  child: TextField(
                    controller: _params[key],
                    style: const TextStyle(fontFamily: 'monospace', fontSize: 13),
                    decoration: const InputDecoration(isDense: true),
                  ),
                ),
              ],
            ),
          ),
        const SizedBox(height: 8),
        ElevatedButton(
          onPressed: _busy || _questionType.isEmpty ? null : _runSolve,
          child: Text(_busy ? 'Solving…' : 'Solve'),
        ),
        if (_solve != null) _solveOutput(_solve!),
        const SizedBox(height: 16),
        const Text('Test grading', style: TextStyle(fontWeight: FontWeight.bold)),
        TextField(
          controller: _lines,
          maxLines: 5,
          style: const TextStyle(fontFamily: 'monospace', fontSize: 13),
          decoration: const InputDecoration(
              hintText: 'One fact/step per line…', border: OutlineInputBorder()),
        ),
        const SizedBox(height: 8),
        ElevatedButton(
          onPressed: _busy || _lines.text.trim().isEmpty ? null : _runGrade,
          child: Text(_busy ? 'Grading…' : 'Grade'),
        ),
        if (_grade != null) _gradeOutput(_grade!),
      ],
    );
  }

  Widget _solveOutput(SandboxSolveResult s) {
    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
          color: AppTheme.slate50, borderRadius: BorderRadius.circular(8)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            const Text('Answer: ', style: TextStyle(color: AppTheme.slate600)),
            Flexible(child: MathText(text: '\$${s.answerLatex}\$')),
          ]),
          if (s.checkpoints.isNotEmpty) ...[
            const SizedBox(height: 6),
            for (final cp in s.checkpoints)
              Text('${cp.label}: ${cp.value}',
                  style: const TextStyle(fontSize: 12)),
          ],
          const SizedBox(height: 6),
          for (final step in s.steps)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(step.title,
                      style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                  MathText(text: step.detail),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _gradeOutput(SandboxGradeResult g) {
    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
          color: AppTheme.slate50, borderRadius: BorderRadius.circular(8)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Line-by-line',
              style: TextStyle(fontWeight: FontWeight.bold)),
          for (final r in g.lineResults)
            Text(
              '${r.line} ${!r.checked ? "–" : (r.correct == true ? "✓" : "✗")} ${r.text}${r.checked && r.correct != true && r.expected != null ? "  expected ${r.expected}" : ""}',
              style: TextStyle(
                  fontFamily: 'monospace',
                  fontSize: 12,
                  color: !r.checked
                      ? AppTheme.slate600
                      : (r.correct == true
                          ? AppTheme.successGreen
                          : AppTheme.errorRed)),
            ),
          if (g.rubricEarned != null) ...[
            const SizedBox(height: 8),
            Text('Rubric: ${g.rubricEarned} / ${g.rubricPossible}',
                style: const TextStyle(fontWeight: FontWeight.bold)),
            for (final b in g.rubricBreakdown)
              Text('${b.label}: ${b.pointsEarned}/${b.pointsPossible}',
                  style: const TextStyle(fontSize: 12)),
          ],
          if (g.rubricError != null)
            Text('rubric: ${g.rubricError}',
                style: const TextStyle(color: AppTheme.accentAmberDark, fontSize: 12)),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Costs tab
// ---------------------------------------------------------------------------

class _CostsTab extends StatefulWidget {
  const _CostsTab();

  @override
  State<_CostsTab> createState() => _CostsTabState();
}

class _CostsTabState extends State<_CostsTab> {
  final ApiClient _api = ApiClient();
  int _days = 30;
  String _endpoint = '';
  bool _busy = true;
  String? _error;
  AdminCostSummary? _summary;
  List<AdminUserCost> _users = [];
  List<AdminUsageLog> _logs = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final results = await Future.wait([
        _api.adminCostSummary(days: _days),
        _api.adminUserCosts(days: _days, endpoint: _endpoint),
        _api.adminUsageLogs(limit: 50, endpoint: _endpoint),
      ]);
      setState(() {
        _summary = results[0] as AdminCostSummary;
        _users = results[1] as List<AdminUserCost>;
        _logs = results[2] as List<AdminUsageLog>;
      });
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_busy) return const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator()));
    final s = _summary;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (_error != null)
          Text(_error!, style: const TextStyle(color: AppTheme.errorRed)),
        Row(
          children: [
            DropdownButton<int>(
              value: _days,
              items: const [
                DropdownMenuItem(value: 1, child: Text('24 hours')),
                DropdownMenuItem(value: 7, child: Text('7 days')),
                DropdownMenuItem(value: 30, child: Text('30 days')),
                DropdownMenuItem(value: 90, child: Text('90 days')),
              ],
              onChanged: (v) {
                if (v != null) {
                  setState(() => _days = v);
                  _load();
                }
              },
            ),
            const Spacer(),
            IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
          ],
        ),
        if (s != null) ...[
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              _kpi("Today's cost", '\$${s.today.costUsd.toStringAsFixed(4)}',
                  '${s.today.calls} calls'),
              _kpi('$_days-day spend', '\$${s.period.costUsd.toStringAsFixed(4)}',
                  '${s.period.calls} requests'),
              _kpi('Total tokens', '${s.period.totalTokens}',
                  'P:${s.period.promptTokens} C:${s.period.completionTokens}'),
              _kpi('Avg latency', '${s.period.avgLatencyMs.round()} ms', ''),
            ],
          ),
          const SizedBox(height: 16),
          _breakdown('By feature', [
            for (final e in s.byEndpoint)
              (e.endpoint.replaceAll('_', ' '),
                  '\$${e.costUsd.toStringAsFixed(4)} (${e.calls})',
                  s.period.costUsd > 0 ? e.costUsd / s.period.costUsd : 0.0)
          ], AppTheme.successGreen),
          const SizedBox(height: 12),
          _breakdown('By model', [
            for (final m in s.byModel)
              (m.modelName, '\$${m.costUsd.toStringAsFixed(4)}',
                  s.period.costUsd > 0 ? m.costUsd / s.period.costUsd : 0.0)
          ], AppTheme.primaryIndigo),
        ],
        const SizedBox(height: 16),
        const Text('User cost ranking',
            style: TextStyle(fontWeight: FontWeight.bold)),
        Card(
          child: Column(
            children: [
              for (int i = 0; i < _users.length; i++)
                ListTile(
                  dense: true,
                  leading: Text('#${i + 1}',
                      style: const TextStyle(color: AppTheme.slate600)),
                  title: Text(_users[i].email,
                      maxLines: 1, overflow: TextOverflow.ellipsis),
                  subtitle: Text(
                      '${_users[i].totalCalls} calls · ${_users[i].totalTokens} tok'),
                  trailing: Text('\$${_users[i].totalCostUsd.toStringAsFixed(4)}',
                      style: const TextStyle(
                          color: AppTheme.successGreen,
                          fontWeight: FontWeight.bold)),
                ),
              if (_users.isEmpty)
                const Padding(
                    padding: EdgeInsets.all(16),
                    child: Text('No usage recorded.')),
            ],
          ),
        ),
        const SizedBox(height: 16),
        const Text('Recent telemetry',
            style: TextStyle(fontWeight: FontWeight.bold)),
        Card(
          child: Column(
            children: [
              for (final l in _logs)
                ListTile(
                  dense: true,
                  title: Text('${l.endpoint} · ${l.modelName}',
                      style: const TextStyle(fontSize: 12)),
                  subtitle: Text('${l.email} · ${l.totalTokens} tok · ${l.latencyMs}ms',
                      style: const TextStyle(fontSize: 11)),
                  trailing: Text(
                    l.success ? 'OK' : 'FAIL',
                    style: TextStyle(
                        color: l.success ? AppTheme.successGreen : AppTheme.errorRed,
                        fontWeight: FontWeight.bold),
                  ),
                ),
              if (_logs.isEmpty)
                const Padding(
                    padding: EdgeInsets.all(16),
                    child: Text('No logs recorded.')),
            ],
          ),
        ),
      ],
    );
  }

  Widget _kpi(String label, String value, String sub) {
    return Container(
      width: 170,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: AppTheme.slate200)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label.toUpperCase(),
              style: const TextStyle(fontSize: 10, color: AppTheme.slate600)),
          const SizedBox(height: 4),
          Text(value,
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          if (sub.isNotEmpty)
            Text(sub, style: const TextStyle(fontSize: 10, color: AppTheme.slate600)),
        ],
      ),
    );
  }

  Widget _breakdown(String title, List<(String, String, double)> rows, Color color) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            if (rows.isEmpty)
              const Text('No data.',
                  style: TextStyle(color: AppTheme.slate600, fontSize: 12)),
            for (final r in rows) ...[
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Flexible(child: Text(r.$1, style: const TextStyle(fontSize: 12))),
                  Text(r.$2, style: const TextStyle(fontSize: 12)),
                ],
              ),
              const SizedBox(height: 2),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: r.$3.clamp(0.05, 1.0),
                  minHeight: 6,
                  backgroundColor: AppTheme.slate100,
                  valueColor: AlwaysStoppedAnimation(color),
                ),
              ),
              const SizedBox(height: 8),
            ],
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Settings tab (model switcher)
// ---------------------------------------------------------------------------

class _SettingsTab extends StatefulWidget {
  const _SettingsTab();

  @override
  State<_SettingsTab> createState() => _SettingsTabState();
}

class _SettingsTabState extends State<_SettingsTab> {
  final ApiClient _api = ApiClient();
  bool _busy = true;
  bool _saving = false;
  String? _error;
  String? _success;
  String _textModel = 'gemini-3.5-flash';
  String _visionModel = 'gemini-3.5-flash';
  String _visionProvider = 'gemini';

  static const _textModels = [
    'gemini-3.5-flash',
    'gemini-2.0-flash',
    'gemini-1.5-flash',
    'gemini-1.5-pro',
    'qwen2.5:3b',
  ];
  static const _visionModels = [
    'gemini-3.5-flash',
    'gemini-2.0-flash',
    'gemini-1.5-flash',
    'qwen2.5vl:3b',
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final m = await _api.adminModelSettings();
      setState(() {
        if (_textModels.contains(m.textModel)) _textModel = m.textModel;
        if (_visionModels.contains(m.visionModel)) _visionModel = m.visionModel;
        _visionProvider = m.visionProvider;
      });
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _save() async {
    setState(() {
      _saving = true;
      _success = null;
      _error = null;
    });
    try {
      await _api.updateAdminModelSettings(ModelSettings(
          textModel: _textModel,
          visionModel: _visionModel,
          visionProvider: _visionProvider));
      setState(() => _success = 'Saved & active');
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_busy) return const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator()));
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Live Model & Provider Switcher',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            _dropdown('Text & narration model', _textModel, _textModels,
                (v) => setState(() => _textModel = v)),
            const SizedBox(height: 10),
            _dropdown('Vision & OCR model', _visionModel, _visionModels,
                (v) => setState(() => _visionModel = v)),
            const SizedBox(height: 10),
            _dropdown('Vision OCR provider', _visionProvider,
                const ['gemini', 'ollama', 'fallback'],
                (v) => setState(() => _visionProvider = v)),
            const SizedBox(height: 16),
            if (_error != null)
              Text(_error!, style: const TextStyle(color: AppTheme.errorRed)),
            if (_success != null)
              Text(_success!, style: const TextStyle(color: AppTheme.successGreen)),
            const SizedBox(height: 8),
            ElevatedButton(
              onPressed: _saving ? null : _save,
              child: Text(_saving ? 'Saving…' : 'Apply'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _dropdown(String label, String value, List<String> options,
      ValueChanged<String> onChanged) {
    return DropdownButtonFormField<String>(
      initialValue: value,
      isExpanded: true,
      decoration: InputDecoration(labelText: label, isDense: true),
      items: [
        for (final o in options) DropdownMenuItem(value: o, child: Text(o))
      ],
      onChanged: (v) {
        if (v != null) onChanged(v);
      },
    );
  }
}
