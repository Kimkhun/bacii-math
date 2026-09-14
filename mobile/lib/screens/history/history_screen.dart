import 'package:flutter/material.dart';
import '../../core/api/api_client.dart';
import '../../core/theme/app_theme.dart';
import '../../models/attempt.dart';
import '../../widgets/math_text.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  final ApiClient _api = ApiClient();
  List<Attempt> _attempts = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetchAttempts();
  }

  Future<void> _fetchAttempts() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final res = await _api.getAttempts();
      setState(() {
        _attempts = res;
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
            Text('Failed to load history: $_error'),
            const SizedBox(height: 12),
            ElevatedButton(onPressed: _fetchAttempts, child: const Text('Retry')),
          ],
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 800),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Attempt History & Review',
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: AppTheme.primaryNavy),
              ),
              const SizedBox(height: 16),

              if (_attempts.isEmpty) ...[
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(32),
                    child: Center(
                      child: Text('No attempts recorded yet.'),
                    ),
                  ),
                ),
              ] else ...[
                for (final a in _attempts) ...[
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                decoration: BoxDecoration(
                                  color: a.correct ? AppTheme.successGreenLight : AppTheme.errorRedLight,
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(
                                      a.correct ? Icons.check_circle : Icons.cancel,
                                      size: 14,
                                      color: a.correct ? AppTheme.successGreen : AppTheme.errorRed,
                                    ),
                                    const SizedBox(width: 4),
                                    Text(
                                      a.correct ? 'Correct' : 'Needs Work',
                                      style: TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.bold,
                                        color: a.correct ? Colors.green.shade900 : Colors.red.shade900,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 8),
                              Text(
                                '${a.topic.toUpperCase()} \u2022 ${a.difficulty}',
                                style: const TextStyle(fontSize: 12, color: AppTheme.slate600, fontWeight: FontWeight.w600),
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          MathText(text: a.prompt, textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500)),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              const Text('Your Answer: ', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                              Expanded(
                                child: Text(a.userAnswer, style: const TextStyle(fontSize: 13, fontFamily: 'monospace')),
                              ),
                            ],
                          ),
                          if (!a.correct) ...[
                            const SizedBox(height: 4),
                            Row(
                              children: [
                                const Text('Expected: ', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.errorRed)),
                                Expanded(
                                  child: MathText(text: '\$${a.expectedAnswer}\$', textStyle: const TextStyle(color: AppTheme.errorRed)),
                                ),
                              ],
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),
                ],
              ],
            ],
          ),
        ),
      ),
    );
  }
}
