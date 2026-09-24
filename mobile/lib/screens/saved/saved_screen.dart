import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api/api_client.dart';
import '../../core/i18n/app_translations.dart';
import '../../core/i18n/language_provider.dart';
import '../../core/theme/app_theme.dart';
import '../../models/session.dart';
import '../../widgets/math_text.dart';

/// Mirrors web/src/app/saved/page.tsx — a shelf of all saved / in-progress
/// exercises, filterable by status and topic, each resumable via
/// PracticeScreen(initialSession: id).
class SavedScreen extends StatefulWidget {
  const SavedScreen({super.key});

  @override
  State<SavedScreen> createState() => _SavedScreenState();
}

enum _StatusFilter { all, inProgress, completed }

class _SavedScreenState extends State<SavedScreen> {
  final ApiClient _api = ApiClient();
  List<SessionSummary> _sessions = [];
  bool _busy = true;
  String? _error;
  _StatusFilter _filterStatus = _StatusFilter.all;
  String _selectedTopic = 'all';

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
      final s = await _api.myProgress();
      if (mounted) setState(() => _sessions = s);
    } catch (e) {
      if (mounted) {
        setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _delete(String id) async {
    final lang = Provider.of<LanguageProvider>(context, listen: false);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        content: Text(lang.isKhmer
            ? 'តើអ្នកប្រាកដថាចង់លុបលំហាត់នេះទេ?'
            : 'Are you sure you want to delete this saved exercise?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete',
                style: TextStyle(color: AppTheme.errorRed)),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await _api.deleteProgress(id);
      if (mounted) {
        setState(() => _sessions.removeWhere((s) => s.id == id));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
        );
      }
    }
  }

  bool _isDone(SessionSummary s) =>
      s.status == 'completed' || s.partsDone >= s.partsTotal;

  List<String> get _topics {
    final set = <String>{};
    for (final s in _sessions) {
      final t = s.question?.topic;
      if (t != null && t.isNotEmpty) set.add(t);
    }
    return set.toList();
  }

  List<SessionSummary> get _filtered {
    return _sessions.where((s) {
      final done = _isDone(s);
      if (_filterStatus == _StatusFilter.inProgress && done) return false;
      if (_filterStatus == _StatusFilter.completed && !done) return false;
      if (_selectedTopic != 'all' && s.question?.topic != _selectedTopic) {
        return false;
      }
      return true;
    }).toList();
  }

  String _topicLabel(LanguageProvider lang, String topic) {
    final l = lang.t('topic_$topic');
    return l.isNotEmpty ? l : topic.replaceAll('_', ' ');
  }

  @override
  Widget build(BuildContext context) {
    final lang = Provider.of<LanguageProvider>(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 960),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back),
                    onPressed: () => context.go('/profile'),
                  ),
                  Expanded(
                    child: Row(
                      children: [
                        Text(lang.t('saved_shelf_title'),
                            style: const TextStyle(
                                fontSize: 22,
                                fontWeight: FontWeight.bold,
                                color: AppTheme.primaryNavy)),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: AppTheme.accentAmberLight,
                            borderRadius: BorderRadius.circular(999),
                            border: Border.all(color: AppTheme.accentAmber),
                          ),
                          child: Text('${_sessions.length}',
                              style: const TextStyle(
                                  fontSize: 11, fontWeight: FontWeight.bold)),
                        ),
                      ],
                    ),
                  ),
                  ElevatedButton(
                    onPressed: () => context.go('/practice'),
                    style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primaryNavy),
                    child: Text(
                        lang.isKhmer ? 'ហ្វឹកហាត់លំហាត់ថ្មី' : 'New Practice',
                        style: const TextStyle(color: Colors.white, fontSize: 12)),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  ChoiceChip(
                    label: Text(
                        '${lang.isKhmer ? "ទាំងអស់" : "All"} (${_sessions.length})'),
                    selected: _filterStatus == _StatusFilter.all,
                    onSelected: (_) =>
                        setState(() => _filterStatus = _StatusFilter.all),
                  ),
                  ChoiceChip(
                    label: Text(
                        '${lang.t('saved_in_progress')} (${_sessions.where((s) => !_isDone(s)).length})'),
                    selected: _filterStatus == _StatusFilter.inProgress,
                    onSelected: (_) => setState(
                        () => _filterStatus = _StatusFilter.inProgress),
                  ),
                  ChoiceChip(
                    label: Text(
                        '${lang.t('saved_completed')} (${_sessions.where(_isDone).length})'),
                    selected: _filterStatus == _StatusFilter.completed,
                    onSelected: (_) =>
                        setState(() => _filterStatus = _StatusFilter.completed),
                  ),
                  if (_topics.isNotEmpty)
                    DropdownButton<String>(
                      value: _selectedTopic,
                      items: [
                        DropdownMenuItem(
                          value: 'all',
                          child: Text(
                              lang.isKhmer ? 'គ្រប់ប្រធានបទ' : 'All topics'),
                        ),
                        for (final tp in _topics)
                          DropdownMenuItem(
                              value: tp, child: Text(_topicLabel(lang, tp))),
                      ],
                      onChanged: (v) =>
                          setState(() => _selectedTopic = v ?? 'all'),
                    ),
                ],
              ),
              const SizedBox(height: 16),
              if (_error != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 12),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.red.shade200),
                  ),
                  child: Text(_error!,
                      style: TextStyle(color: Colors.red.shade700, fontSize: 13)),
                ),
              if (_busy)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 48),
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (_filtered.isEmpty)
                Container(
                  padding: const EdgeInsets.all(32),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppTheme.slate200),
                  ),
                  child: Column(
                    children: [
                      Text(lang.t('saved_empty'),
                          style: const TextStyle(
                              fontSize: 15, fontWeight: FontWeight.w600)),
                      const SizedBox(height: 12),
                      ElevatedButton(
                        onPressed: () => context.go('/practice'),
                        style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.primaryNavy),
                        child: Text(
                            lang.isKhmer
                                ? 'ចាប់ផ្ដើមធ្វើលំហាត់'
                                : 'Start Practicing',
                            style: const TextStyle(color: Colors.white)),
                      ),
                    ],
                  ),
                )
              else
                GridView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                    maxCrossAxisExtent: 340,
                    mainAxisExtent: 230,
                    crossAxisSpacing: 12,
                    mainAxisSpacing: 12,
                  ),
                  itemCount: _filtered.length,
                  itemBuilder: (ctx, i) => _card(_filtered[i], lang),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _card(SessionSummary s, LanguageProvider lang) {
    final typeLabel = questionTypeLabel(
        s.question?.questionType ?? '', lang.currentLang);
    final partsTotal = s.partsTotal < 1 ? 1 : s.partsTotal;
    final partsDone = s.partsDone;
    final isMultiPart = s.partsTotal > 1;
    final done = _isDone(s);
    final percent =
        isMultiPart ? ((partsDone / partsTotal) * 100).round() : (done ? 100 : 0);

    return Container(
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
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Wrap(
                  spacing: 4,
                  runSpacing: 4,
                  children: [
                    Container(
                      padding:
                          const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                          color: AppTheme.slate100,
                          borderRadius: BorderRadius.circular(4)),
                      child: Text(typeLabel, style: const TextStyle(fontSize: 10)),
                    ),
                    if (done)
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                            color: Colors.green.shade50,
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(color: Colors.green.shade200)),
                        child: Text(lang.t('saved_completed'),
                            style: TextStyle(
                                fontSize: 10, color: Colors.green.shade700)),
                      ),
                  ],
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close, size: 16),
                tooltip: lang.t('tip_delete_progress'),
                onPressed: () => _delete(s.id),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Expanded(
            child: s.question?.promptLatex != null &&
                    s.question!.promptLatex!.isNotEmpty
                ? MathText(text: '\\(${s.question!.promptLatex}\\)')
                : Text(s.question?.prompt ?? 'Exercise in progress...',
                    style: const TextStyle(fontSize: 12),
                    maxLines: 4,
                    overflow: TextOverflow.ellipsis),
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: AppTheme.slate100,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      isMultiPart
                          ? (lang.isKhmer
                              ? 'ផ្នែកទី $partsDone/$partsTotal'
                              : 'Part $partsDone of $partsTotal')
                          : (done
                              ? lang.t('saved_completed')
                              : lang.t('saved_in_progress')),
                      style: const TextStyle(fontSize: 10),
                    ),
                    Text(done ? (lang.isKhmer ? 'រួចរាល់' : 'Done') : '$percent%',
                        style: const TextStyle(
                            fontSize: 10, fontWeight: FontWeight.bold)),
                  ],
                ),
                const SizedBox(height: 4),
                ClipRRect(
                  borderRadius: BorderRadius.circular(999),
                  child: LinearProgressIndicator(
                    value: (percent.clamp(0, 100)) / 100,
                    minHeight: 5,
                    backgroundColor: AppTheme.slate200,
                    valueColor: AlwaysStoppedAnimation(
                        done ? Colors.green : AppTheme.accentAmber),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(s.updatedAt.isNotEmpty ? s.updatedAt.split('T').first : '',
                  style: const TextStyle(fontSize: 10, color: AppTheme.slate300)),
              TextButton(
                onPressed: () => context.go('/practice?session=${s.id}'),
                child: Text(lang.t('action_resume')),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
