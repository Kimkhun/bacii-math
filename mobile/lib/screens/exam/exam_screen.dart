import 'dart:async';
import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/math_text.dart';

class ExamScreen extends StatefulWidget {
  const ExamScreen({super.key});

  @override
  State<ExamScreen> createState() => _ExamScreenState();
}

class _ExamScreenState extends State<ExamScreen> {
  bool _isExamActive = false;
  int _remainingSeconds = 150 * 60; // 2.5 hours standard BAC II Exam
  Timer? _timer;

  final Map<String, TextEditingController> _controllers = {};

  final List<Map<String, dynamic>> _mockExamSections = [
    {
      'title': 'ផ្នែកទី ១៖ ចំនួនកុំផ្លិច (Complex Numbers - 25 ពិន្ទុ)',
      'questions': [
        {'id': 'q1_1', 'prompt': r'គណនាផលបូក $z_1 + z_2$ និងផលគុណ $z_1 \cdot z_2$ ដោយដឹងថា $z_1 = 3 + 4i$ និង $z_2 = 1 - 2i$'},
        {'id': 'q1_2', 'prompt': r'សរសេរចំនួនកុំផ្លិច $z = 1 + i\sqrt{3}$ ជាទម្រង់ត្រីកោណមាត្រ។'},
      ]
    },
    {
      'title': 'ផ្នែកទី ២៖ លីមីត និងដេរីវេ (Limits & Derivatives - 35 ពិន្ទុ)',
      'questions': [
        {'id': 'q2_1', 'prompt': r'គណនាលីមីត $\lim_{x \to 0} \frac{\sin(3x)}{x}$'},
        {'id': 'q2_2', 'prompt': r'គណនាដេរីវេនៃអនុគមន៍ $f(x) = x^3 - 3x^2 + 2x - 5$'},
      ]
    },
    {
      'title': 'ផ្នែកទី ៣៖ អាំងតេក្រាល (Integrals - 40 ពិន្ទុ)',
      'questions': [
        {'id': 'q3_1', 'prompt': r'គណនាអាំងតេក្រាល $\int (3x^2 + 2x + 1) dx$'},
        {'id': 'q3_2', 'prompt': r'គណនាអាំងតេក្រាលកំណត់ $\int_{0}^{1} e^{2x} dx$'},
      ]
    },
  ];

  @override
  void dispose() {
    _timer?.cancel();
    for (final c in _controllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  void _startExam() {
    setState(() {
      _isExamActive = true;
      _remainingSeconds = 150 * 60;
    });
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (_remainingSeconds > 0) {
        setState(() => _remainingSeconds--);
      } else {
        t.cancel();
        _submitExam();
      }
    });
  }

  void _submitExam() {
    _timer?.cancel();
    setState(() => _isExamActive = false);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Exam Completed'),
        content: const Text('Your exam submission has been recorded for evaluation.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  String _formatTime(int seconds) {
    final m = seconds ~/ 60;
    final s = seconds % 60;
    final h = m ~/ 60;
    final remM = m % 60;
    return '${h.toString().padLeft(2, '0')}:${remM.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 850),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header Card
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    children: [
                      const Text(
                        'វិញ្ញាសាប្រឡងសញ្ញាបត្រមធ្យមសិក្សាទុតិយភូមិ (BAC II)',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppTheme.primaryNavy),
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Cambodian National Mock Exam \u2022 Duration: 2 Hours 30 Minutes',
                        style: TextStyle(fontSize: 13, color: AppTheme.slate600),
                      ),
                      const SizedBox(height: 16),

                      if (!_isExamActive) ...[
                        ElevatedButton.icon(
                          onPressed: _startExam,
                          icon: const Icon(Icons.timer_outlined),
                          label: const Text('Start Timed Exam'),
                          style: ElevatedButton.styleFrom(
                            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                          ),
                        ),
                      ] else ...[
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                          decoration: BoxDecoration(
                            color: AppTheme.accentAmberLight,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: AppTheme.accentAmber),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.alarm_rounded, color: AppTheme.accentAmberDark, size: 20),
                              const SizedBox(width: 8),
                              Text(
                                'Time Remaining: ${_formatTime(_remainingSeconds)}',
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: AppTheme.accentAmberDark),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // Exam Sections & Questions
              for (final sec in _mockExamSections) ...[
                Text(
                  sec['title'] as String,
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.primaryNavy),
                ),
                const SizedBox(height: 10),
                for (final q in (sec['questions'] as List<dynamic>)) ...[
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          MathText(text: q['prompt'] as String, textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w500)),
                          const SizedBox(height: 12),
                          TextField(
                            enabled: _isExamActive,
                            decoration: InputDecoration(
                              hintText: _isExamActive ? 'Enter your derivation or answer' : 'Start exam to answer',
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                ],
                const SizedBox(height: 16),
              ],

              if (_isExamActive) ...[
                ElevatedButton.icon(
                  onPressed: _submitExam,
                  icon: const Icon(Icons.done_all_rounded),
                  label: const Text('Submit Exam Paper'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.successGreen,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
