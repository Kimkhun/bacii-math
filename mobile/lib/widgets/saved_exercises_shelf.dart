import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../core/i18n/app_translations.dart';
import '../core/i18n/language_provider.dart';
import '../core/theme/app_theme.dart';
import '../models/session.dart';
import 'math_text.dart';

String _timeAgo(String iso, bool km) {
  final d = DateTime.tryParse(iso);
  if (d == null) return '';
  final diff = DateTime.now().difference(d.toLocal());
  if (diff.inSeconds < 60) return km ? 'មុននេះបន្តិច' : 'Just now';
  if (diff.inMinutes < 60) return km ? '${diff.inMinutes} នាទីមុន' : '${diff.inMinutes}m ago';
  if (diff.inHours < 24) return km ? '${diff.inHours} ម៉ោងមុន' : '${diff.inHours}h ago';
  return km ? '${diff.inDays} ថ្ងៃមុន' : '${diff.inDays}d ago';
}

/// Horizontal "Continue practicing" carousel of in-progress / saved
/// exercises (port of web SavedExercisesShelf, shown on the profile).
class SavedExercisesShelf extends StatelessWidget {
  final List<SessionSummary> sessions;
  final ValueChanged<String>? onDelete;

  const SavedExercisesShelf({super.key, required this.sessions, this.onDelete});

  @override
  Widget build(BuildContext context) {
    final lang = context.watch<LanguageProvider>();
    const title = TextStyle(fontSize: 16, fontWeight: FontWeight.bold);

    if (sessions.isEmpty) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(lang.t('saved_shelf_title'), style: title),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppTheme.slate200),
            ),
            child: Column(
              children: [
                Text(lang.t('saved_empty'),
                    style: const TextStyle(fontSize: 12, color: AppTheme.slate600)),
                const SizedBox(height: 8),
                ElevatedButton(
                  onPressed: () => context.go('/practice'),
                  child: Text(lang.isKhmer ? 'ចាប់ផ្ដើមធ្វើលំហាត់' : 'Start Practicing',
                      style: const TextStyle(fontSize: 12)),
                ),
              ],
            ),
          ),
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Text(lang.t('saved_shelf_title'), style: title),
            const SizedBox(width: 6),
            Text('(${sessions.length})',
                style: const TextStyle(fontSize: 12, color: AppTheme.slate600)),
            const Spacer(),
            TextButton(
              onPressed: () => context.go('/saved'),
              child: Text('${lang.t('saved_see_all')} →', style: const TextStyle(fontSize: 12)),
            ),
          ],
        ),
        const SizedBox(height: 4),
        SizedBox(
          height: 200,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: sessions.length,
            separatorBuilder: (_, __) => const SizedBox(width: 12),
            itemBuilder: (context, i) => _card(context, lang, sessions[i]),
          ),
        ),
      ],
    );
  }

  Widget _card(BuildContext context, LanguageProvider lang, SessionSummary s) {
    final q = s.question;
    final typeLabel =
        q != null ? questionTypeLabel(q.questionType, lang.currentLang) : 'Exercise';
    final latexPreview = (q?.promptLatex ?? '').split('\n').first;
    final textPreview = (q?.prompt ?? '').split('\n').first;
    final total = s.partsTotal < 1 ? 1 : s.partsTotal;
    final done = s.partsDone;
    final multi = s.partsTotal > 1;
    final isDone = s.status == 'completed' || done >= total;
    final pct = multi ? (done * 100 / total).round() : (isDone ? 100 : 0);
    final barFraction = multi ? (pct < 6 ? 6 : pct) / 100 : (isDone ? 1.0 : 0.4);

    return Container(
      width: 260,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppTheme.slate200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Flexible(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                      color: AppTheme.slate100, borderRadius: BorderRadius.circular(4)),
                  child: Text(typeLabel,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 11, color: AppTheme.slate700)),
                ),
              ),
              if (q != null && q.difficulty.isNotEmpty) ...[
                const SizedBox(width: 6),
                Text(q.difficulty.toUpperCase(),
                    style: const TextStyle(
                        fontSize: 10, fontWeight: FontWeight.w600, color: AppTheme.slate600)),
              ],
              const Spacer(),
              if (onDelete != null)
                InkWell(
                  onTap: () => onDelete!(s.id),
                  child: Tooltip(
                    message: lang.t('tip_delete_progress'),
                    child: const Icon(Icons.close, size: 14, color: AppTheme.slate600),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 10),
          // The preview takes whatever height is left (Khmer script and large
          // font settings are taller), clipped rather than overflowing.
          Expanded(
            child: ClipRect(
              child: latexPreview.isNotEmpty
                  ? MathText(
                      text: '\\($latexPreview\\)',
                      textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500))
                  : Text(textPreview.isNotEmpty ? textPreview : 'Exercise in progress...',
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
            ),
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              Expanded(
                child: Text(
                  multi
                      ? (lang.isKhmer
                          ? '$done/$total ផ្នែកបានរួចរាល់'
                          : '$done/$total parts done')
                      : isDone
                          ? lang.t('saved_completed')
                          : lang.t('saved_in_progress'),
                  style: const TextStyle(fontSize: 11, color: AppTheme.slate600),
                ),
              ),
              Text(
                  isDone
                      ? (lang.isKhmer ? 'រួចរាល់' : 'Done')
                      : (multi ? '$pct%' : ''),
                  style: const TextStyle(
                      fontSize: 11, fontWeight: FontWeight.w600, color: AppTheme.slate600)),
            ],
          ),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: barFraction.toDouble(),
              minHeight: 6,
              backgroundColor: AppTheme.slate100,
              color: isDone ? AppTheme.successGreen : AppTheme.accentAmber,
            ),
          ),
          const Divider(height: 18, color: AppTheme.slate100),
          Row(
            children: [
              Expanded(
                child: Text(_timeAgo(s.updatedAt, lang.isKhmer),
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 11, color: AppTheme.slate600)),
              ),
              ElevatedButton(
                onPressed: () => context.go('/practice?session=${s.id}'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  visualDensity: VisualDensity.compact,
                ),
                child: Text(lang.t('action_resume'), style: const TextStyle(fontSize: 12)),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
