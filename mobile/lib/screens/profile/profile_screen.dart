import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/api/api_client.dart';
import '../../core/i18n/language_provider.dart';
import '../../core/auth/auth_provider.dart';
import '../../core/theme/app_theme.dart';
import '../../models/profile.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final ApiClient _api = ApiClient();
  Profile? _profile;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetchProfile();
  }

  Future<void> _fetchProfile() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final res = await _api.getProfile();
      setState(() {
        _profile = res;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final lang = Provider.of<LanguageProvider>(context);
    final auth = Provider.of<AuthProvider>(context);

    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('Failed to load profile: $_error'),
            const SizedBox(height: 12),
            ElevatedButton(onPressed: _fetchProfile, child: const Text('Retry')),
          ],
        ),
      );
    }

    final p = _profile!;

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 800),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // User Card
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Row(
                    children: [
                      const CircleAvatar(
                        radius: 28,
                        backgroundColor: AppTheme.primaryNavy,
                        child: Icon(Icons.school_rounded, color: AppTheme.accentAmber, size: 28),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              auth.user?.email ?? 'Student',
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: AppTheme.primaryNavy),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Plan: ${auth.user?.plan.toUpperCase() ?? "FREE"} \u2022 BAC II Math Candidate',
                              style: const TextStyle(fontSize: 13, color: AppTheme.slate600),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Headline Stats
              Row(
                children: [
                  Expanded(
                    child: _StatCard(
                      title: 'Mastery Score',
                      value: '${p.score.toStringAsFixed(1)}%',
                      icon: Icons.emoji_events_rounded,
                      color: AppTheme.accentAmber,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _StatCard(
                      title: 'Accuracy',
                      value: '${(p.accuracy * 100).toStringAsFixed(0)}%',
                      icon: Icons.track_changes_rounded,
                      color: AppTheme.successGreen,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _StatCard(
                      title: 'Exercises',
                      value: '${p.attempts}',
                      icon: Icons.fitness_center_rounded,
                      color: AppTheme.primaryIndigo,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),

              // Recommendations Section
              if (p.suggestions.isNotEmpty) ...[
                const Text(
                  'Recommended Practice',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.primaryNavy),
                ),
                const SizedBox(height: 12),
                for (final s in p.suggestions.take(3)) ...[
                  Card(
                    color: AppTheme.accentAmberLight.withValues(alpha: 0.4),
                    child: ListTile(
                      leading: const Icon(Icons.lightbulb_rounded, color: AppTheme.accentAmberDark),
                      title: Text(s.title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                      subtitle: Text(s.reason, style: const TextStyle(fontSize: 12)),
                      trailing: ElevatedButton(
                        onPressed: () {
                          if (s.topic != null) {
                            context.go('/practice?topic=${s.topic}');
                          } else {
                            context.go('/practice');
                          }
                        },
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          visualDensity: VisualDensity.compact,
                        ),
                        child: const Text('Practise', style: TextStyle(fontSize: 12)),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                ],
                const SizedBox(height: 16),
              ],

              Text(
                '${lang.t('nav_profile')} \u2022 Skill Mastery',
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.primaryNavy),
              ),
              const SizedBox(height: 12),
              for (final sk in p.skills) ...[
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(sk.label, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                            Text(
                              '${sk.level.toStringAsFixed(0)}%',
                              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(4),
                          child: LinearProgressIndicator(
                            value: sk.level / 100.0,
                            minHeight: 6,
                            backgroundColor: AppTheme.slate200,
                            valueColor: AlwaysStoppedAnimation(
                              sk.level >= 80
                                  ? AppTheme.successGreen
                                  : (sk.level >= 50 ? AppTheme.accentAmber : AppTheme.primaryIndigo),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 8),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final Color color;

  const _StatCard({
    required this.title,
    required this.value,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
        child: Column(
          children: [
            Icon(icon, color: color, size: 24),
            const SizedBox(height: 8),
            Text(value, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppTheme.primaryNavy)),
            const SizedBox(height: 2),
            Text(title, style: const TextStyle(fontSize: 11, color: AppTheme.slate600)),
          ],
        ),
      ),
    );
  }
}
