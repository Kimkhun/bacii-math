import 'package:flutter/material.dart';
import '../core/i18n/language_provider.dart';
import '../core/theme/app_theme.dart';
import 'math_text.dart';

class DisambiguationCandidate {
  final String text;
  final String? latex;
  DisambiguationCandidate({required this.text, this.latex});
}

/// Result of the disambiguation prompt.
sealed class DisambiguationChoice {}

class PickCandidate extends DisambiguationChoice {
  final int index;
  PickCandidate(this.index);
}

class PickNone extends DisambiguationChoice {}

class WriteAgain extends DisambiguationChoice {}

/// Asks the student whether an OCR'd line was actually one of the alternates.
/// Port of DisambiguationCard.tsx (rendered as a dialog here). Returns null if
/// dismissed without a choice (treated as "keep the OCR reading").
Future<DisambiguationChoice?> showDisambiguationDialog(
  BuildContext context,
  LanguageProvider lang, {
  required int lineNumber,
  required DisambiguationCandidate primary,
  required List<DisambiguationCandidate> candidates,
}) {
  String label(DisambiguationCandidate c) =>
      c.latex != null && c.latex!.isNotEmpty ? '\$${c.latex}\$' : c.text;

  return showDialog<DisambiguationChoice>(
    context: context,
    builder: (ctx) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      contentPadding: const EdgeInsets.fromLTRB(20, 18, 20, 8),
      content: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '${lang.isKhmer ? "ខ្ញុំបានអានបន្ទាត់" : "I read line"} $lineNumber ${lang.isKhmer ? "ថា" : "as"}',
              style: const TextStyle(fontSize: 12, color: AppTheme.slate600),
            ),
            const SizedBox(height: 8),
            MathText(text: label(primary), textStyle: const TextStyle(fontSize: 15)),
            const SizedBox(height: 14),
            Text(
              lang.isKhmer
                  ? 'តើអ្នកបានសរសេរមួយក្នុងចំណោមនេះឬ?'
                  : 'Did you write one of these instead?',
              style: const TextStyle(fontSize: 12, color: AppTheme.slate600),
            ),
            const SizedBox(height: 10),
            for (int i = 0; i < candidates.length; i++) ...[
              OutlinedButton(
                onPressed: () => Navigator.pop(ctx, PickCandidate(i)),
                style: OutlinedButton.styleFrom(
                  alignment: Alignment.centerLeft,
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  side: BorderSide(
                      color: i == 0 ? AppTheme.slate600 : AppTheme.slate300,
                      width: i == 0 ? 1.5 : 1),
                ),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: MathText(text: label(candidates[i])),
                ),
              ),
              const SizedBox(height: 8),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(ctx, WriteAgain()),
          child: Text(lang.isKhmer ? 'សរសេរម្តងទៀត' : 'Write it again'),
        ),
        TextButton(
          onPressed: () => Navigator.pop(ctx, PickNone()),
          child: Text(
            lang.isKhmer ? 'គ្មានមួយណាទេ' : 'None of these',
            style: const TextStyle(color: AppTheme.slate600),
          ),
        ),
      ],
    ),
  );
}
