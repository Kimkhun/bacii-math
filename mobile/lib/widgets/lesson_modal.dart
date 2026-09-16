import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api/api_client.dart';
import '../core/i18n/language_provider.dart';
import '../core/theme/app_theme.dart';
import '../models/lesson.dart';
import 'math_text.dart';

/// Authored per-skill lesson viewer. Port of LessonModal.tsx — a static read,
/// bilingual, shown as a full-screen dialog.
class LessonModal extends StatefulWidget {
  final String skillKey;
  final String fallbackLabel;

  const LessonModal({
    super.key,
    required this.skillKey,
    required this.fallbackLabel,
  });

  @override
  State<LessonModal> createState() => _LessonModalState();
}

class _LessonModalState extends State<LessonModal> {
  final ApiClient _api = ApiClient();
  Lesson? _lesson;
  bool _busy = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final l = await _api.lesson(widget.skillKey);
      if (mounted) setState(() => _lesson = l);
    } catch (e) {
      if (mounted) {
        setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final lang = Provider.of<LanguageProvider>(context);
    final km = lang.isKhmer;
    final l = _lesson;
    final title = l != null ? (km ? l.titleKm : l.titleEn) : widget.fallbackLabel;

    return Dialog(
      insetPadding: const EdgeInsets.all(16),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 680, maxHeight: 720),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
              decoration: const BoxDecoration(
                color: AppTheme.slate50,
                border: Border(bottom: BorderSide(color: AppTheme.slate200)),
                borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
              ),
              child: Row(
                children: [
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: const Color(0xFFE0F2FE),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(lang.t('lesson'),
                        style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF0369A1))),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(title,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                            color: AppTheme.primaryNavy)),
                  ),
                  IconButton(
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close_rounded),
                  ),
                ],
              ),
            ),
            Flexible(
              child: _busy
                  ? Padding(
                      padding: const EdgeInsets.all(28),
                      child: Text(lang.t('lesson_loading')),
                    )
                  : (_error != null || l == null)
                      ? Padding(
                          padding: const EdgeInsets.all(28),
                          child: Text(_error ?? lang.t('lesson_none')),
                        )
                      : _content(l, km, lang),
            ),
          ],
        ),
      ),
    );
  }

  Widget _content(Lesson l, bool km, LanguageProvider lang) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          MathText(text: km ? l.summaryKm : l.summaryEn),
          if (l.formulas.isNotEmpty) ...[
            const SizedBox(height: 20),
            _sectionHeader(lang.t('lesson_key_formulas')),
            const SizedBox(height: 8),
            for (final f in l.formulas)
              Container(
                width: double.infinity,
                margin: const EdgeInsets.only(bottom: 10),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.slate50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppTheme.slate200),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    MathText(text: '\$\$${f.latex}\$\$'),
                    if ((km ? f.noteKm : f.noteEn)?.isNotEmpty ?? false)
                      Padding(
                        padding: const EdgeInsets.only(top: 6),
                        child: Text(km ? (f.noteKm ?? '') : (f.noteEn ?? ''),
                            style: const TextStyle(
                                fontSize: 12, color: AppTheme.slate600)),
                      ),
                  ],
                ),
              ),
          ],
          for (final s in l.sections) ...[
            const SizedBox(height: 16),
            Text(km ? s.headingKm : s.headingEn,
                style: const TextStyle(
                    fontWeight: FontWeight.bold, fontSize: 14)),
            const SizedBox(height: 6),
            MathText(text: km ? s.bodyKm : s.bodyEn),
          ],
          if (l.examples.isNotEmpty) ...[
            const SizedBox(height: 20),
            _sectionHeader(lang.t('lesson_worked_examples')),
            const SizedBox(height: 8),
            for (final ex in l.examples)
              Container(
                width: double.infinity,
                margin: const EdgeInsets.only(bottom: 12),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppTheme.slate200),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    MathText(
                        text: km ? ex.promptKm : ex.promptEn,
                        textStyle: const TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 8),
                    for (final st in ex.steps) ...[
                      MathText(text: km ? st.textKm : st.textEn),
                      if (st.latex != null && st.latex!.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: MathText(text: '\$\$${st.latex}\$\$'),
                        ),
                      const SizedBox(height: 4),
                    ],
                    if (ex.answerLatex != null && ex.answerLatex!.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: Row(
                          children: [
                            Text('${lang.t('lesson_answer')}: ',
                                style: const TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.bold,
                                    color: AppTheme.successGreen)),
                            Flexible(child: MathText(text: '\$${ex.answerLatex}\$')),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
          ],
        ],
      ),
    );
  }

  Widget _sectionHeader(String text) => Text(
        text.toUpperCase(),
        style: const TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.bold,
            letterSpacing: 0.5,
            color: AppTheme.slate600),
      );
}
