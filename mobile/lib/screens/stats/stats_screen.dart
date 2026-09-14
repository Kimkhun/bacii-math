import 'package:flutter/material.dart';
import '../../core/api/api_client.dart';
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
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetchStats();
  }

  Future<void> _fetchStats() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final res = await _api.getStats();
      setState(() {
        _stats = res;
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
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('Failed to load stats: $_error'),
            const SizedBox(height: 12),
            ElevatedButton(onPressed: _fetchStats, child: const Text('Retry')),
          ],
        ),
      );
    }

    final s = _stats!;

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 800),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Performance & Accuracy',
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: AppTheme.primaryNavy),
              ),
              const SizedBox(height: 16),

              // Summary Row
              Row(
                children: [
                  Expanded(
                    child: Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          children: [
                            const Text('Total Attempts', style: TextStyle(color: AppTheme.slate600, fontSize: 12)),
                            const SizedBox(height: 6),
                            Text('${s.totalAttempts}', style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          children: [
                            const Text('Correct Solutions', style: TextStyle(color: AppTheme.slate600, fontSize: 12)),
                            const SizedBox(height: 6),
                            Text(
                              '${s.correct}',
                              style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: AppTheme.successGreen),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          children: [
                            const Text('Global Accuracy', style: TextStyle(color: AppTheme.slate600, fontSize: 12)),
                            const SizedBox(height: 6),
                            Text(
                              '${(s.accuracy * 100).toStringAsFixed(1)}%',
                              style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: AppTheme.accentAmberDark),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),

              const Text(
                'Topic Breakdown',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.primaryNavy),
              ),
              const SizedBox(height: 12),

              if (s.byTopic.isEmpty) ...[
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Center(
                      child: Text('No attempts recorded yet. Start practicing!'),
                    ),
                  ),
                ),
              ] else ...[
                for (final item in s.byTopic) ...[
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(item.questionType, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                              Text(
                                '${item.correct} / ${item.attempts} correct (${(item.attempts > 0 ? item.correct / item.attempts * 100 : 0).toStringAsFixed(0)}%)',
                                style: const TextStyle(fontSize: 12, color: AppTheme.slate600),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(4),
                            child: LinearProgressIndicator(
                              value: item.attempts > 0 ? item.correct / item.attempts : 0,
                              minHeight: 6,
                              backgroundColor: AppTheme.slate200,
                              valueColor: const AlwaysStoppedAnimation(AppTheme.primaryIndigo),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                ],
              ],
            ],
          ),
        ),
      ),
    );
  }
}
