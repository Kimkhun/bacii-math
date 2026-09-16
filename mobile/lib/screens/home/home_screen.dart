import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/i18n/language_provider.dart';
import '../../core/theme/app_theme.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final lang = Provider.of<LanguageProvider>(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 32),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 800),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              // Hero Badge
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: AppTheme.accentAmberLight,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: AppTheme.accentAmber.withValues(alpha: 0.5)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.verified_rounded, size: 16, color: AppTheme.accentAmberDark),
                    const SizedBox(width: 6),
                    Text(
                      'Cambodian National Curriculum 2026',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: Colors.amber.shade900,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              // Hero Title
              Text(
                lang.t('hero_title'),
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.w800,
                  color: AppTheme.primaryNavy,
                  height: 1.3,
                ),
              ),
              const SizedBox(height: 16),

              // Hero Subtitle
              Text(
                lang.t('hero_subtitle'),
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 15,
                  color: AppTheme.slate600,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: 28),

              // Action Buttons
              Wrap(
                spacing: 12,
                runSpacing: 12,
                alignment: WrapAlignment.center,
                children: [
                  ElevatedButton.icon(
                    onPressed: () => context.go('/practice'),
                    icon: const Icon(Icons.rocket_launch_rounded),
                    label: Text(lang.t('btn_start_practicing')),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                    ),
                  ),
                  OutlinedButton.icon(
                    onPressed: () => context.go('/exam'),
                    icon: const Icon(Icons.assignment_outlined),
                    label: Text(lang.t('nav_exam')),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 48),

              // Feature Cards
              LayoutBuilder(
                builder: (context, constraints) {
                  final isWide = constraints.maxWidth > 600;
                  if (isWide) {
                    return Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: _FeatureCard(
                            icon: Icons.edit_note_rounded,
                            title: lang.t('feat_handwrite_title'),
                            description: lang.t('feat_handwrite_desc'),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: _FeatureCard(
                            icon: Icons.auto_awesome_rounded,
                            title: lang.t('feat_grading_title'),
                            description: lang.t('feat_grading_desc'),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: _FeatureCard(
                            icon: Icons.checklist_rounded,
                            title: lang.t('feat_step_title'),
                            description: lang.t('feat_step_desc'),
                          ),
                        ),
                      ],
                    );
                  } else {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _FeatureCard(
                          icon: Icons.edit_note_rounded,
                          title: lang.t('feat_handwrite_title'),
                          description: lang.t('feat_handwrite_desc'),
                        ),
                        const SizedBox(height: 16),
                        _FeatureCard(
                          icon: Icons.auto_awesome_rounded,
                          title: lang.t('feat_grading_title'),
                          description: lang.t('feat_grading_desc'),
                        ),
                        const SizedBox(height: 16),
                        _FeatureCard(
                          icon: Icons.checklist_rounded,
                          title: lang.t('feat_step_title'),
                          description: lang.t('feat_step_desc'),
                        ),
                      ],
                    );
                  }
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _FeatureCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String description;

  const _FeatureCard({
    required this.icon,
    required this.title,
    required this.description,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppTheme.slate100,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: AppTheme.primaryIndigo, size: 24),
            ),
            const SizedBox(height: 12),
            Text(
              title,
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: AppTheme.primaryNavy),
            ),
            const SizedBox(height: 6),
            Text(
              description,
              style: const TextStyle(fontSize: 13, color: AppTheme.slate600, height: 1.4),
            ),
          ],
        ),
      ),
    );
  }
}
