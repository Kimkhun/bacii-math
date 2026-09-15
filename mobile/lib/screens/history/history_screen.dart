import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api/api_client.dart';
import '../../core/i18n/app_translations.dart';
import '../../core/i18n/language_provider.dart';
import '../../core/theme/app_theme.dart';
import '../../models/attempt.dart';
import '../../widgets/math_text.dart';

Uint8List? _dataUrlBytes(String? dataUrl) {
  if (dataUrl == null) return null;
  final i = dataUrl.indexOf(',');
  if (i == -1) return null;
  try {
    return base64Decode(dataUrl.substring(i + 1));
  } catch (_) {
    return null;
  }
}

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  final ApiClient _api = ApiClient();
  List<Attempt> _attempts = [];
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
      final a = await _api.getAttempts();
      setState(() => _attempts = a);
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
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(lang.t('history_title'),
                  style: const TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                      color: AppTheme.primaryNavy)),
              const SizedBox(height: 12),
              if (_attempts.isEmpty)
                Padding(
                  padding: const EdgeInsets.all(24),
                  child: Text(lang.t('history_no_attempts'),
                      style: const TextStyle(color: AppTheme.slate600)),
                )
              else
                for (final a in _attempts) _attemptCard(a, lang),
            ],
          ),
        ),
      ),
    );
  }

  Widget _attemptCard(Attempt a, LanguageProvider lang) {
    final missed = a.formulaBreakdown.where((f) => !f.reached).toList();
    final thumb = _dataUrlBytes(a.strokesThumb);
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
            color: a.correct
                ? AppTheme.successGreen.withValues(alpha: 0.4)
                : AppTheme.errorRed.withValues(alpha: 0.4)),
      ),
      child: InkWell(
        onTap: () => context.go('/practice?attempt=${a.id}'),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 6,
                runSpacing: 6,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  _pill(lang.t('topic_${a.topic}').isNotEmpty
                      ? lang.t('topic_${a.topic}')
                      : a.topic),
                  _pill(questionTypeLabel(a.questionType, lang.currentLang)),
                  _pill(lang.t('diff_${a.difficulty}')),
                  _pill(a.correct ? lang.t('verdict_correct') : lang.t('verdict_incorrect'),
                      color: a.correct
                          ? AppTheme.successGreenLight
                          : AppTheme.errorRedLight,
                      textColor: a.correct
                          ? Colors.green.shade900
                          : Colors.red.shade900),
                  if (a.hintsUsed > 0)
                    _pill('${a.hintsUsed} ${lang.isKhmer ? "ជំនួយ" : "hint"}',
                        color: AppTheme.accentAmberLight),
                ],
              ),
              const SizedBox(height: 8),
              a.promptLatex != null && a.promptLatex!.isNotEmpty
                  ? MathText(text: '\$${a.promptLatex}\$')
                  : MathText(text: a.prompt),
              const SizedBox(height: 6),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${lang.t('verdict_you')}: ',
                      style: const TextStyle(
                          fontSize: 13, color: AppTheme.slate600)),
                  Expanded(child: MathText(text: '\$${a.userAnswer}\$')),
                ],
              ),
              if (!a.correct)
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${lang.t('label_expected')}: ',
                        style: const TextStyle(
                            fontSize: 13, color: AppTheme.slate600)),
                    Expanded(child: MathText(text: '\$${a.expectedAnswer}\$')),
                  ],
                ),
              if (thumb != null) ...[
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: BorderRadius.circular(6),
                  child: Image.memory(thumb,
                      height: 120, fit: BoxFit.contain, alignment: Alignment.centerLeft),
                ),
              ],
              if (missed.isNotEmpty) ...[
                const SizedBox(height: 8),
                Wrap(
                  spacing: 6,
                  runSpacing: 4,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(lang.isKhmer ? 'រូបមន្តខ្វះ:' : 'Missed:',
                        style: const TextStyle(
                            fontSize: 11, color: AppTheme.slate600)),
                    for (final f in missed)
                      _pill(f.formula.replaceAll('_', ' '),
                          color: AppTheme.errorRedLight,
                          textColor: Colors.red.shade900),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _pill(String text,
      {Color color = AppTheme.slate100, Color textColor = AppTheme.slate700}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration:
          BoxDecoration(color: color, borderRadius: BorderRadius.circular(6)),
      child: Text(text,
          style: TextStyle(
              fontSize: 11, color: textColor, fontWeight: FontWeight.w500)),
    );
  }
}
