import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api/api_client.dart';
import '../../core/i18n/language_provider.dart';
import '../../core/theme/app_theme.dart';
import '../../models/formula.dart';
import '../../widgets/math_text.dart';

// Avoid double-wrapping a formula string that's already Khmer text or
// already contains its own $-delimited math (mirrors web's
// renderMathFormula in formulas/page.tsx).
String _renderMathFormula(String s) {
  if (s.isEmpty) return s;
  final hasKhmer = RegExp(r'[ក-៿]').hasMatch(s);
  if (s.contains(r'$') || hasKhmer) return s;
  return '\$${s}\$';
}

String? _difficultyFromWeight(double weight) {
  if (weight <= 0) return null;
  if (weight == 1) return 'easy';
  if (weight == 2) return 'medium';
  return 'hard';
}

class FormulasScreen extends StatefulWidget {
  const FormulasScreen({super.key});

  @override
  State<FormulasScreen> createState() => _FormulasScreenState();
}

class _FormulasScreenState extends State<FormulasScreen> {
  final ApiClient _api = ApiClient();
  FormulaCatalog? _catalog;
  bool _busy = true;
  String? _error;
  String _filter = 'all';

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
      final c = await _api.getFormulas();
      setState(() {
        _catalog = c;
      });
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _topicLabel(LanguageProvider lang, String topic) {
    final l = lang.t('topic_$topic');
    return l.isNotEmpty ? l : topic.replaceAll('_', ' ');
  }

  @override
  Widget build(BuildContext context) {
    final lang = Provider.of<LanguageProvider>(context);
    if (_busy) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          Text('Failed: $_error'),
          const SizedBox(height: 12),
          ElevatedButton(onPressed: _load, child: const Text('Retry')),
        ]),
      );
    }
    final catalog = _catalog!;
    final topics = ['all', ...catalog.topics.map((t) => t.topic)];
    final visible = catalog.topics
        .where((t) => _filter == 'all' || t.topic == _filter)
        .toList();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(lang.t('formulas_title'),
                  style: const TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                      color: AppTheme.primaryNavy)),
              const SizedBox(height: 4),
              Text(lang.t('formulas_subtitle'),
                  style: const TextStyle(fontSize: 13, color: AppTheme.slate600)),
              const SizedBox(height: 12),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    for (final tp in topics)
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: ChoiceChip(
                          label: Text(
                              tp == 'all'
                                  ? lang.t('formulas_all_topics')
                                  : _topicLabel(lang, tp),
                              style: const TextStyle(fontSize: 12)),
                          selected: _filter == tp,
                          onSelected: (_) => setState(() => _filter = tp),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              for (final topic in visible) ...[
                Text(_topicLabel(lang, topic.topic),
                    style: const TextStyle(
                        fontSize: 17, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                for (final e in topic.entries) _entryCard(e, lang),
                const SizedBox(height: 16),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _entryCard(FormulaEntry e, LanguageProvider lang) {
    final primary = lang.isKhmer
        ? (e.nameKm.isNotEmpty ? e.nameKm : (e.nameEn ?? e.id.replaceAll('_', ' ')))
        : (e.nameEn ?? e.id.replaceAll('_', ' '));
    final secondary = lang.isKhmer ? e.nameEn : e.nameKm;
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Wrap(
                    spacing: 6,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      Text(primary,
                          style: const TextStyle(
                              fontWeight: FontWeight.bold, fontSize: 15)),
                      if (secondary != null &&
                          secondary.isNotEmpty &&
                          secondary != primary)
                        Text('($secondary)',
                            style: const TextStyle(
                                fontSize: 13, color: AppTheme.slate600)),
                      if (_difficultyFromWeight(e.weight) != null)
                        Builder(builder: (context) {
                          final diff = _difficultyFromWeight(e.weight)!;
                          final colors = {
                            'easy': (Colors.green.shade100, Colors.green.shade800),
                            'medium': (Colors.amber.shade100, Colors.amber.shade800),
                            'hard': (Colors.red.shade100, Colors.red.shade800),
                          }[diff]!;
                          return Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                                color: colors.$1,
                                borderRadius: BorderRadius.circular(4)),
                            child: Text(
                                lang.t('formulas_difficulty_$diff'),
                                style: TextStyle(
                                    fontSize: 11, color: colors.$2)),
                          );
                        }),
                    ],
                  ),
                ),
                if (e.variants.isNotEmpty)
                  OutlinedButton(
                    onPressed: () => context.go('/practice?formula=${e.id}'),
                    style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 4),
                        visualDensity: VisualDensity.compact),
                    child: Text(lang.t('formulas_practice'),
                        style: const TextStyle(fontSize: 12)),
                  ),
              ],
            ),
            if (e.latex != null && e.latex!.isNotEmpty) ...[
              const SizedBox(height: 8),
              MathText(text: _renderMathFormula(e.latex!)),
            ],
            if (e.formulas.isNotEmpty) ...[
              const SizedBox(height: 6),
              for (final f in e.formulas)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: MathText(text: _renderMathFormula(f)),
                ),
            ],
          ],
        ),
      ),
    );
  }
}
