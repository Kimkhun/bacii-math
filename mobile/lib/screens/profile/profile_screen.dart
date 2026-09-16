import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api/api_client.dart';
import '../../core/i18n/language_provider.dart';
import '../../core/theme/app_theme.dart';
import '../../models/profile.dart';
import '../../widgets/lesson_modal.dart';
import '../../widgets/math_text.dart';

Color _levelBar(double level) {
  if (level >= 75) return AppTheme.successGreen;
  if (level >= 55) return const Color(0xFF0EA5E9);
  if (level >= 30) return AppTheme.accentAmber;
  return AppTheme.errorRed;
}

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final ApiClient _api = ApiClient();
  Profile? _profile;
  bool _busy = true;
  String? _error;
  final Set<String> _openTopics = {};
  bool _showAllTopics = false;
  bool _rebuilding = false;

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
      final p = await _api.getProfile();
      setState(() => _profile = p);
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _rebuild() async {
    setState(() => _rebuilding = true);
    try {
      await _api.rebuildProfile();
      await _load();
    } catch (_) {
    } finally {
      if (mounted) setState(() => _rebuilding = false);
    }
  }

  String _pct(double v) => '${(v * 100).round()}%';

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
    final p = _profile;
    if (p == null) return Center(child: Text(lang.isKhmer ? 'មិនទាន់មានទិន្នន័យ។' : 'Nothing yet.'));
    final level = p.level;

    final skillsByTopic = <String, List<Skill>>{};
    for (final s in p.skills) {
      skillsByTopic.putIfAbsent(s.topic, () => []).add(s);
    }
    for (final list in skillsByTopic.values) {
      list.sort((a, b) {
        if ((a.evidence > 0) != (b.evidence > 0)) return a.evidence > 0 ? -1 : 1;
        return a.evidence > 0
            ? a.level.compareTo(b.level)
            : a.label.compareTo(b.label);
      });
    }
    final weakFormulas =
        p.formulas.where((f) => f.level < 55).take(8).toList();
    final visibleTopics =
        p.topics.where((t) => _showAllTopics || t.engaged).toList();

    return RefreshIndicator(
      onRefresh: _load,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 820),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(lang.t('profile_title'),
                          style: const TextStyle(
                              fontSize: 22,
                              fontWeight: FontWeight.bold,
                              color: AppTheme.primaryNavy)),
                    ),
                    Text(p.user.email,
                        style: const TextStyle(
                            fontSize: 12, color: AppTheme.slate600)),
                  ],
                ),
                const SizedBox(height: 12),
                _headline(level, p, lang),
                const SizedBox(height: 16),
                if (p.suggestions.isNotEmpty) ...[
                  Text(lang.t('profile_suggestions'),
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  for (final s in p.suggestions) _suggestionCard(s, lang),
                  const SizedBox(height: 8),
                ],
                Row(
                  children: [
                    Expanded(
                      child: Text(lang.t('profile_topics'),
                          style: const TextStyle(
                              fontSize: 16, fontWeight: FontWeight.bold)),
                    ),
                    TextButton(
                      onPressed: () =>
                          setState(() => _showAllTopics = !_showAllTopics),
                      child: Text(
                          _showAllTopics
                              ? (lang.isKhmer ? 'តែដែលបានចាប់ផ្ដើម' : 'Started only')
                              : (lang.isKhmer ? 'គ្រប់ប្រធានបទ' : 'Show all'),
                          style: const TextStyle(fontSize: 12)),
                    ),
                  ],
                ),
                for (final t in visibleTopics)
                  _topicCard(t, skillsByTopic[t.topic] ?? [], lang),
                if (weakFormulas.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  _formulaTable(weakFormulas, lang),
                ],
                const SizedBox(height: 24),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _bar(double level, {double height = 8}) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(4),
      child: LinearProgressIndicator(
        value: (level / 100).clamp(0, 1),
        minHeight: height,
        backgroundColor: AppTheme.slate100,
        valueColor: AlwaysStoppedAnimation(_levelBar(level)),
      ),
    );
  }

  Widget _headline(ProfileLevel level, Profile p, LanguageProvider lang) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(lang.t('profile_skill_level').toUpperCase(),
                        style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            color: AppTheme.slate600)),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.baseline,
                      textBaseline: TextBaseline.alphabetic,
                      children: [
                        Text('${level.score.round()}',
                            style: TextStyle(
                                fontSize: 44,
                                fontWeight: FontWeight.bold,
                                color: _levelBar(level.score))),
                        const Text(' / 100',
                            style: TextStyle(
                                fontSize: 16, color: AppTheme.slate600)),
                      ],
                    ),
                    Text(level.band,
                        style: const TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: AppTheme.slate600)),
                  ],
                ),
                const Spacer(),
                IconButton(
                  tooltip: 'Rebuild',
                  onPressed: _rebuilding ? null : _rebuild,
                  icon: _rebuilding
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.refresh),
                ),
              ],
            ),
            const SizedBox(height: 10),
            _bar(level.score, height: 10),
            const SizedBox(height: 14),
            Wrap(
              spacing: 20,
              runSpacing: 10,
              children: [
                _stat('${level.attempts}',
                    lang.isKhmer ? 'លំហាត់បានឆ្លើយ' : 'Answered'),
                _stat(_pct(level.accuracy), lang.t('stats_accuracy'),
                    color: AppTheme.successGreen),
                _stat('${level.topicsStarted}/${level.topicsTotal}',
                    lang.isKhmer ? 'ប្រធានបទ' : 'Topics'),
                _stat(_pct(level.coverage),
                    lang.isKhmer ? 'គ្របដណ្ដប់' : 'Syllabus'),
              ],
            ),
            const SizedBox(height: 14),
            Text(lang.t('profile_accuracy_14d'),
                style: const TextStyle(fontSize: 11, color: AppTheme.slate600)),
            const SizedBox(height: 6),
            _activityStrip(p.activity, lang),
          ],
        ),
      ),
    );
  }

  Widget _stat(String value, String label, {Color? color}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(value,
            style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: color ?? AppTheme.primaryNavy)),
        Text(label,
            style: const TextStyle(fontSize: 11, color: AppTheme.slate600)),
      ],
    );
  }

  Widget _activityStrip(List<ActivityDay> activity, LanguageProvider lang) {
    final byDate = {for (final a in activity) a.date: a};
    final now = DateTime.now().toUtc();
    final days = <ActivityDay>[];
    for (int i = 13; i >= 0; i--) {
      final d = DateTime.utc(now.year, now.month, now.day - i);
      final key =
          '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
      days.add(byDate[key] ?? ActivityDay(date: key, attempts: 0, correct: 0));
    }
    final maxA = days.fold<int>(1, (m, d) => d.attempts > m ? d.attempts : m);
    return Column(
      children: [
        SizedBox(
          height: 44,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              for (final d in days)
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 1),
                    child: d.attempts > 0
                        ? Column(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: [
                              Container(
                                  height: (d.attempts - d.correct) / maxA * 40,
                                  color: AppTheme.slate200),
                              Container(
                                  height: d.correct / maxA * 40,
                                  color: AppTheme.successGreen),
                            ],
                          )
                        : Container(height: 2, color: AppTheme.slate100),
                  ),
                ),
            ],
          ),
        ),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(lang.isKhmer ? '១៤ ថ្ងៃមុន' : '14 days ago',
                style: const TextStyle(fontSize: 10, color: AppTheme.slate600)),
            Text(lang.isKhmer ? 'ថ្ងៃនេះ' : 'Today',
                style: const TextStyle(fontSize: 10, color: AppTheme.slate600)),
          ],
        ),
      ],
    );
  }

  Widget _suggestionCard(Suggestion s, LanguageProvider lang) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                      color: AppTheme.slate100,
                      borderRadius: BorderRadius.circular(4)),
                  child: Text(lang.t('sug_${s.kind}'),
                      style: const TextStyle(
                          fontSize: 11, fontWeight: FontWeight.w600)),
                ),
                if (s.topicLabel != null) ...[
                  const SizedBox(width: 8),
                  Text(s.topicLabel!,
                      style: const TextStyle(
                          fontSize: 11, color: AppTheme.slate600)),
                ],
              ],
            ),
            const SizedBox(height: 6),
            Text(s.title,
                style: const TextStyle(
                    fontWeight: FontWeight.bold, fontSize: 14)),
            Text(s.reason, style: const TextStyle(fontSize: 13)),
            if (s.contrast != null)
              Text(s.contrast!,
                  style: const TextStyle(
                      fontSize: 13,
                      fontStyle: FontStyle.italic,
                      color: AppTheme.slate600)),
            if (s.skillKey != null)
              Align(
                alignment: Alignment.centerLeft,
                child: Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: ElevatedButton(
                    onPressed: () => context.go(
                        '/practice?skill=${Uri.encodeQueryComponent(s.skillKey!)}'),
                    style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 6),
                        visualDensity: VisualDensity.compact),
                    child: Text(lang.t('formulas_practice'),
                        style: const TextStyle(fontSize: 12)),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _topicCard(TopicProgress t, List<Skill> skills, LanguageProvider lang) {
    final open = _openTopics.contains(t.topic);
    final topicLabel = lang.t('topic_${t.topic}');
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Column(
        children: [
          InkWell(
            onTap: () => setState(() {
              if (open) {
                _openTopics.remove(t.topic);
              } else {
                _openTopics.add(t.topic);
              }
            }),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(topicLabel.isNotEmpty ? topicLabel : t.label,
                            style: const TextStyle(
                                fontWeight: FontWeight.bold, fontSize: 14)),
                        const SizedBox(height: 6),
                        _bar(t.score),
                        const SizedBox(height: 4),
                        Text(
                          t.engaged
                              ? '${t.skillsPractised}/${t.skillsTotal} ${lang.isKhmer ? "ប្រភេទ" : "types"} · ${t.correct}/${t.attempts} ${lang.isKhmer ? "ត្រូវ" : "right"}'
                              : (lang.isKhmer
                                  ? 'មិនទាន់ចាប់ផ្ដើម'
                                  : 'Not started'),
                          style: const TextStyle(
                              fontSize: 11, color: AppTheme.slate600),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(t.engaged ? '${t.score.round()}' : '–',
                      style: TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                          color: t.engaged
                              ? _levelBar(t.score)
                              : AppTheme.slate300)),
                  Icon(open ? Icons.expand_less : Icons.expand_more,
                      color: AppTheme.slate600),
                ],
              ),
            ),
          ),
          if (open)
            for (final s in skills) _skillRow(s, lang),
        ],
      ),
    );
  }

  Widget _skillRow(Skill s, LanguageProvider lang) {
    final untouched = s.evidence <= 0;
    return Container(
      decoration: const BoxDecoration(
          border: Border(top: BorderSide(color: AppTheme.slate100))),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(s.label,
                    style: TextStyle(
                        fontSize: 13,
                        color: untouched
                            ? AppTheme.slate600
                            : AppTheme.primaryNavy)),
                const SizedBox(height: 4),
                _bar(s.level, height: 6),
              ],
            ),
          ),
          const SizedBox(width: 8),
          SizedBox(
            width: 34,
            child: Text(untouched ? '–' : '${s.level.round()}',
                textAlign: TextAlign.right,
                style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                    color: untouched ? AppTheme.slate300 : _levelBar(s.level))),
          ),
          if (s.hasLesson)
            IconButton(
              tooltip: lang.t('lesson'),
              icon: const Text('📖', style: TextStyle(fontSize: 16)),
              visualDensity: VisualDensity.compact,
              onPressed: () => showDialog(
                context: context,
                builder: (_) =>
                    LessonModal(skillKey: s.key, fallbackLabel: s.label),
              ),
            ),
          IconButton(
            tooltip: lang.t('formulas_practice'),
            icon: const Icon(Icons.fitness_center, size: 16),
            visualDensity: VisualDensity.compact,
            onPressed: () => context
                .go('/practice?skill=${Uri.encodeQueryComponent(s.key)}'),
          ),
        ],
      ),
    );
  }

  Widget _formulaTable(List<FormulaSkill> formulas, LanguageProvider lang) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
                lang.isKhmer
                    ? 'ជំហាន និងរូបមន្តដែលនៅខ្វះចន្លោះ'
                    : 'Steps you keep missing',
                style:
                    const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
            const SizedBox(height: 8),
            for (final f in formulas)
              Container(
                decoration: const BoxDecoration(
                    border:
                        Border(top: BorderSide(color: AppTheme.slate100))),
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(f.name,
                              style: const TextStyle(fontSize: 13)),
                          if (f.latex != null && f.latex!.isNotEmpty)
                            MathText(
                                text: '\$${f.latex}\$',
                                textStyle: const TextStyle(
                                    fontSize: 12, color: AppTheme.slate600)),
                        ],
                      ),
                    ),
                    Text('${f.correct}/${f.attempts}',
                        style: const TextStyle(fontSize: 12)),
                    const SizedBox(width: 10),
                    Text('${f.level.round()}',
                        style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: _levelBar(f.level))),
                    if (f.skillKey != null)
                      IconButton(
                        icon: const Icon(Icons.fitness_center, size: 16),
                        visualDensity: VisualDensity.compact,
                        onPressed: () => context.go(
                            '/practice?skill=${Uri.encodeQueryComponent(f.skillKey!)}'),
                      ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}
