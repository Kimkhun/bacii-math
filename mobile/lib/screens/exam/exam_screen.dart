import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api/api_client.dart';
import '../../core/i18n/language_provider.dart';
import '../../core/theme/app_theme.dart';
import '../../models/exam.dart';
import '../../widgets/math_text.dart';

const String _examId = '2018';

class ExamScreen extends StatefulWidget {
  const ExamScreen({super.key});

  @override
  State<ExamScreen> createState() => _ExamScreenState();
}

class _ExamScreenState extends State<ExamScreen> {
  final ApiClient _api = ApiClient();
  Exam? _exam;
  String? _error;
  bool _started = false;
  bool _submitting = false;
  ExamResult? _result;
  int? _secondsLeft;
  Timer? _timer;
  final Map<String, TextEditingController> _answers = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _timer?.cancel();
    for (final c in _answers.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final e = await _api.exam(_examId);
      setState(() {
        _exam = e;
        _secondsLeft = (e.durationMinutes ?? 150) * 60;
      });
    } catch (err) {
      setState(() => _error = err.toString().replaceFirst('Exception: ', ''));
    }
  }

  TextEditingController _ctrl(String key) =>
      _answers.putIfAbsent(key, () => TextEditingController());

  void _startExam() {
    setState(() => _started = true);
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (_result != null) {
        t.cancel();
        return;
      }
      setState(() {
        if ((_secondsLeft ?? 0) <= 1) {
          _secondsLeft = 0;
          t.cancel();
          _submitExam();
        } else {
          _secondsLeft = _secondsLeft! - 1;
        }
      });
    });
  }

  Future<void> _submitExam() async {
    if (_submitting || _result != null) return;
    setState(() {
      _submitting = true;
      _error = null;
    });
    _timer?.cancel();
    try {
      final answers = <String, String>{};
      _answers.forEach((k, v) {
        if (v.text.trim().isNotEmpty) answers[k] = v.text;
      });
      final res = await _api.submitExam(_examId, answers);
      setState(() => _result = res);
    } catch (err) {
      setState(() => _error = err.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  String _clock(int s) {
    final m = s ~/ 60;
    final sec = s % 60;
    return '$m:${sec.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final lang = Provider.of<LanguageProvider>(context);
    if (_error != null && _exam == null) {
      return Center(child: Text(_error!, style: const TextStyle(color: AppTheme.errorRed)));
    }
    final exam = _exam;
    if (exam == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (!_started) {
      return _intro(exam, lang);
    }
    return _examBody(exam, lang);
  }

  Widget _intro(Exam exam, LanguageProvider lang) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('${lang.t('exam_title')} — ${exam.examDate ?? ''}',
                  style: const TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                      color: AppTheme.primaryNavy)),
              const SizedBox(height: 8),
              Text('${lang.t('exam_duration')}: ${exam.durationMinutes} ${lang.isKhmer ? "នាទី" : "minutes"}',
                  style: const TextStyle(color: AppTheme.slate600)),
              Text(
                  '${lang.t('exam_total_points')}: ${exam.totalPoints} ${lang.t('exam_pts')} (${exam.sections.length} ${lang.isKhmer ? "ផ្នែក" : "sections"})',
                  style: const TextStyle(color: AppTheme.slate600)),
              const SizedBox(height: 16),
              Text(lang.t('exam_intro'),
                  style: const TextStyle(height: 1.5, color: AppTheme.slate700)),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: _startExam,
                icon: const Icon(Icons.timer_outlined),
                label: Text(lang.t('btn_start_exam')),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _examBody(Exam exam, LanguageProvider lang) {
    return Column(
      children: [
        Material(
          elevation: 1,
          child: Container(
            color: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            child: Row(
              children: [
                Expanded(
                  child: Text('${lang.t('exam_title')} — ${exam.examDate ?? ''}',
                      style: const TextStyle(
                          fontWeight: FontWeight.bold, fontSize: 15)),
                ),
                if (_result == null && _secondsLeft != null)
                  Text(_clock(_secondsLeft!),
                      style: TextStyle(
                          fontFamily: 'monospace',
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: _secondsLeft! < 600
                              ? AppTheme.errorRed
                              : AppTheme.slate700))
                else if (_result != null)
                  Text(
                      '${lang.t('exam_score')}: ${_result!.earned.toStringAsFixed(1)} / ${_result!.possible.toStringAsFixed(0)}',
                      style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          color: AppTheme.primaryNavy)),
              ],
            ),
          ),
        ),
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 720),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (_error != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: Text(_error!,
                            style: const TextStyle(color: AppTheme.errorRed)),
                      ),
                    for (int idx = 0; idx < exam.sections.length; idx++)
                      _sectionCard(exam.sections[idx], idx, lang),
                    if (_result == null) ...[
                      const SizedBox(height: 8),
                      ElevatedButton(
                        onPressed: _submitting ? null : _submitExam,
                        style: ElevatedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 16)),
                        child: Text(_submitting
                            ? lang.t('btn_checking')
                            : lang.t('btn_submit_exam')),
                      ),
                    ],
                    const SizedBox(height: 40),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _sectionCard(ExamSection section, int idx, LanguageProvider lang) {
    final key = '${idx + 1}';
    final qResult = _result?.perQuestion[key];
    final title = (lang.isKhmer && (section.titleKm?.isNotEmpty ?? false))
        ? section.titleKm!
        : (section.titleEn ?? 'Part ${section.id}');
    final given = (lang.isKhmer && (section.givenKm?.isNotEmpty ?? false))
        ? section.givenKm
        : section.givenEn;

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text('${lang.t('exam_question')} ${section.id} — $title',
                      style: const TextStyle(
                          fontWeight: FontWeight.bold, fontSize: 15)),
                ),
                if (qResult != null)
                  Text(
                      '${qResult.earned.toStringAsFixed(1)} / ${qResult.possible.toStringAsFixed(0)} ${lang.t('exam_pts')}',
                      style: const TextStyle(
                          fontSize: 13, color: AppTheme.slate600)),
              ],
            ),
            if ((given?.isNotEmpty ?? false) ||
                (section.givenLatex?.isNotEmpty ?? false)) ...[
              const SizedBox(height: 8),
              if (given?.isNotEmpty ?? false) MathText(text: given!),
              if (section.givenLatex?.isNotEmpty ?? false)
                MathText(text: '\$${section.givenLatex}\$'),
            ],
            const SizedBox(height: 8),
            for (final q in section.questions)
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${q.label}) ',
                        style: const TextStyle(fontWeight: FontWeight.bold)),
                    Expanded(
                      child: Wrap(
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          if (q.promptEn?.isNotEmpty ?? false)
                            MathText(text: q.promptEn!),
                          if (q.promptLatex?.isNotEmpty ?? false)
                            MathText(text: '\$${q.promptLatex}\$'),
                          if (!q.gradable)
                            Text(
                                lang.isKhmer
                                    ? ' (សម្រាប់ផ្ទៀងផ្ទាត់ខ្លួនឯង)'
                                    : ' (self-check only)',
                                style: const TextStyle(
                                    fontSize: 11,
                                    fontStyle: FontStyle.italic,
                                    color: AppTheme.slate600)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            const SizedBox(height: 10),
            TextField(
              controller: _ctrl(key),
              enabled: _result == null,
              maxLines: 5,
              style: const TextStyle(fontFamily: 'monospace', fontSize: 13),
              decoration: InputDecoration(
                hintText: lang.isKhmer
                    ? 'សូមសរសេរជំហានដោះស្រាយនៅទីនេះ មួយបន្ទាត់ម្តងៗ...'
                    : 'Write your work here, one fact/step per line…',
              ),
            ),
            if (qResult != null && qResult.breakdown.isNotEmpty) ...[
              const SizedBox(height: 8),
              for (final b in qResult.breakdown)
                Text(
                  '${b.pointsEarned > 0 ? "✓" : "✗"} ${b.item}: ${b.label} (${b.pointsEarned.toStringAsFixed(1)}/${b.pointsPossible.toStringAsFixed(1)})',
                  style: TextStyle(
                      fontSize: 11,
                      color: b.pointsEarned > 0
                          ? AppTheme.successGreen
                          : AppTheme.slate600),
                ),
            ],
          ],
        ),
      ),
    );
  }
}
