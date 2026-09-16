import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api/api_client.dart';
import '../../core/i18n/app_translations.dart';
import '../../core/i18n/language_provider.dart';
import '../../core/theme/app_theme.dart';
import '../../models/attempt.dart';

class StatsScreen extends StatefulWidget {
  const StatsScreen({super.key});

  @override
  State<StatsScreen> createState() => _StatsScreenState();
}

class _StatsScreenState extends State<StatsScreen> {
  final ApiClient _api = ApiClient();
  Stats? _stats;
  bool _busy = true;
  String? _error;

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
      final s = await _api.getStats();
      setState(() => _stats = s);
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
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
    final s = _stats!;
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(lang.t('stats_title'),
                  style: const TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                      color: AppTheme.primaryNavy)),
              const SizedBox(height: 12),
              Row(
                children: [
                  _summaryCard('${s.totalAttempts}', lang.t('stats_attempts')),
                  const SizedBox(width: 12),
                  _summaryCard('${s.correct}', lang.t('stats_correct'),
                      color: AppTheme.successGreen),
                  const SizedBox(width: 12),
                  _summaryCard('${(s.accuracy * 100).round()}%',
                      lang.t('stats_accuracy')),
                ],
              ),
              const SizedBox(height: 20),
              if (s.byTopic.isNotEmpty) ...[
                Text(lang.t('stats_by_topic'),
                    style: const TextStyle(
                        fontSize: 16, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Card(
                  child: Column(
                    children: [
                      for (final t in s.byTopic)
                        ListTile(
                          dense: true,
                          title: Text(questionTypeLabel(t.questionType, lang.currentLang)),
                          trailing: Text(
                              '${t.correct} / ${t.attempts} (${t.attempts > 0 ? (t.correct / t.attempts * 100).round() : 0}%)',
                              style: const TextStyle(
                                  fontSize: 12, color: AppTheme.slate600)),
                        ),
                    ],
                  ),
                ),
              ],
              if (s.byFormula.isNotEmpty) ...[
                const SizedBox(height: 20),
                Text(lang.isKhmer ? 'រូបមន្តដែលត្រូវពិនិត្យ' : 'Formulas to review',
                    style: const TextStyle(
                        fontSize: 16, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Card(
                  child: Column(
                    children: [
                      for (final f in s.byFormula)
                        ListTile(
                          dense: true,
                          title: Text(f.nameEn ?? f.formula.replaceAll('_', ' ')),
                          subtitle: Text(
                              '${lang.isKhmer ? "សម្រេច" : "Got"} ${f.reached} · ${lang.isKhmer ? "ខ្វះ" : "missed"} ${f.missed}',
                              style: const TextStyle(fontSize: 11)),
                          trailing: OutlinedButton(
                            onPressed: () =>
                                context.go('/practice?formula=${f.formula}'),
                            style: OutlinedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 10, vertical: 4),
                                visualDensity: VisualDensity.compact),
                            child: Text(lang.t('formulas_practice'),
                                style: const TextStyle(fontSize: 12)),
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _summaryCard(String value, String label, {Color? color}) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 8),
          child: Column(
            children: [
              Text(value,
                  style: TextStyle(
                      fontSize: 26,
                      fontWeight: FontWeight.bold,
                      color: color ?? AppTheme.primaryNavy)),
              const SizedBox(height: 4),
              Text(label,
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 12, color: AppTheme.slate600)),
            ],
          ),
        ),
      ),
    );
  }
}
