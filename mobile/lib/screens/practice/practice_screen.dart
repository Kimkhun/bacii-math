import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/api/api_client.dart';
import '../../core/i18n/language_provider.dart';
import '../../core/theme/app_theme.dart';
import '../../models/question.dart';
import '../../models/grade_result.dart';
import '../../widgets/math_text.dart';
import '../../widgets/canvas/drawing_canvas.dart';
import '../../widgets/math_keypad.dart';

class PracticeScreen extends StatefulWidget {
  final String? initialTopic;

  const PracticeScreen({super.key, this.initialTopic});

  @override
  State<PracticeScreen> createState() => _PracticeScreenState();
}

class _PracticeScreenState extends State<PracticeScreen> {
  late final ApiClient _api;
  final _canvasController = DrawingCanvasController();
  final _answerController = TextEditingController();

  String _topic = 'complex';
  String _difficulty = 'medium';
  bool _isGenerating = false;
  bool _isGrading = false;
  bool _showKeypad = false;
  bool _showSteps = false;

  Question? _currentQuestion;
  int _activePartIndex = 0;
  GradeResult? _gradeResult;
  String? _errorMessage;

  final List<String> _topics = [
    'complex',
    'limit',
    'integral',
    'probability',
    'functions',
    'continuity',
    'derivatives',
    'differential_equations',
    'vectors_space',
    'conics',
  ];

  @override
  void initState() {
    super.initState();
    _api = ApiClient();
    if (widget.initialTopic != null && _topics.contains(widget.initialTopic)) {
      _topic = widget.initialTopic!;
    }
    _loadNewQuestion();
  }

  @override
  void dispose() {
    _canvasController.dispose();
    _answerController.dispose();
    super.dispose();
  }

  Future<void> _loadNewQuestion() async {
    setState(() {
      _isGenerating = true;
      _gradeResult = null;
      _errorMessage = null;
      _showSteps = false;
      _activePartIndex = 0;
    });
    _canvasController.clear();
    _answerController.clear();

    try {
      final q = await _api.generateProblem(
        topic: _topic,
        difficulty: _difficulty,
      );
      setState(() {
        _currentQuestion = q;
        _isGenerating = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString().replaceFirst('Exception: ', '');
        _isGenerating = false;
      });
    }
  }

  Future<void> _checkAnswer() async {
    if (_currentQuestion == null) return;
    final lang = Provider.of<LanguageProvider>(context, listen: false);

    final userAnswer = _answerController.text.trim();
    if (userAnswer.isEmpty && !_canvasController.hasInk) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please enter an answer or draw on the canvas'),
          behavior: SnackBarBehavior.floating,
        ),
      );
      return;
    }

    setState(() {
      _isGrading = true;
      _errorMessage = null;
    });

    try {
      String? partLabel;
      if (_currentQuestion!.parts.isNotEmpty && _activePartIndex < _currentQuestion!.parts.length) {
        partLabel = _currentQuestion!.parts[_activePartIndex].label;
      }

      final res = await _api.gradeProblem(
        questionId: _currentQuestion!.id,
        userAnswer: userAnswer.isNotEmpty ? userAnswer : 'written',
        part: partLabel,
        strokes: _canvasController.hasInk ? _canvasController.toStrokeDocument() : null,
        lang: lang.currentLang,
      );

      setState(() {
        _gradeResult = res;
        _isGrading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString().replaceFirst('Exception: ', '');
        _isGrading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final lang = Provider.of<LanguageProvider>(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 900),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // 1. Topic & Difficulty Controls Bar
              _buildTopicControls(lang),
              const SizedBox(height: 16),

              if (_errorMessage != null) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.errorRedLight,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppTheme.errorRed.withValues(alpha: 0.5)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.error_outline, color: AppTheme.errorRed, size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(_errorMessage!, style: const TextStyle(color: AppTheme.errorRed, fontSize: 13)),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],

              // 2. Full Problem Statement Header (Rule 3: Never slice exam questions; keep preamble visible)
              if (_currentQuestion != null) ...[
                _buildProblemHeader(lang),
                const SizedBox(height: 16),
              ],

              // 3. Drawing Canvas Section
              SizedBox(
                height: 380,
                child: DrawingCanvas(
                  controller: _canvasController,
                  showGrid: true,
                ),
              ),
              const SizedBox(height: 14),

              // 4. Answer Input & Action Buttons
              _buildAnswerInputSection(lang),
              const SizedBox(height: 16),

              // 5. Math Keypad (Expandable)
              if (_showKeypad) ...[
                MathKeypad(
                  controller: _answerController,
                  onSubmitted: () => setState(() => _showKeypad = false),
                ),
                const SizedBox(height: 16),
              ],

              // 6. Grade Verdict & Sequential Step Check (Rule 4: Sequential Line-by-Line checking)
              if (_gradeResult != null) ...[
                _buildGradeVerdictSection(lang),
                const SizedBox(height: 16),
              ],

              // 7. Full Solution Steps (Collapsible)
              if (_currentQuestion != null && _currentQuestion!.steps.isNotEmpty) ...[
                _buildSolutionSection(lang),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTopicControls(LanguageProvider lang) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Wrap(
          spacing: 12,
          runSpacing: 10,
          crossAxisAlignment: WrapCrossAlignment.center,
          alignment: WrapAlignment.spaceBetween,
          children: [
            // Topic Dropdown
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.category_outlined, size: 18, color: AppTheme.slate600),
                const SizedBox(width: 6),
                DropdownButton<String>(
                  value: _topic,
                  underline: const SizedBox(),
                  style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.primaryNavy, fontSize: 14),
                  onChanged: (val) {
                    if (val != null) {
                      setState(() => _topic = val);
                      _loadNewQuestion();
                    }
                  },
                  items: _topics.map((t) {
                    return DropdownMenuItem(
                      value: t,
                      child: Text(lang.t('topic_$t')),
                    );
                  }).toList(),
                ),
              ],
            ),

            // Difficulty Segment
            SegmentedButton<String>(
              segments: [
                ButtonSegment(value: 'easy', label: Text(lang.t('diff_easy'))),
                ButtonSegment(value: 'medium', label: Text(lang.t('diff_medium'))),
                ButtonSegment(value: 'hard', label: Text(lang.t('diff_hard'))),
              ],
              selected: {_difficulty},
              onSelectionChanged: (newVal) {
                setState(() => _difficulty = newVal.first);
                _loadNewQuestion();
              },
              style: ButtonStyle(
                visualDensity: VisualDensity.compact,
                textStyle: WidgetStateProperty.all(const TextStyle(fontSize: 12)),
              ),
            ),

            // New Question Button
            ElevatedButton.icon(
              onPressed: _isGenerating ? null : _loadNewQuestion,
              icon: _isGenerating
                  ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.refresh_rounded, size: 16),
              label: Text(_isGenerating ? lang.t('btn_generating') : lang.t('btn_new_question')),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProblemHeader(LanguageProvider lang) {
    final q = _currentQuestion!;
    final hasParts = q.parts.isNotEmpty;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Preamble / Prompt Text
            MathText(
              text: q.prompt,
              textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, height: 1.5),
            ),

            if (q.zDisplay.isNotEmpty) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: AppTheme.slate100,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: MathText(
                  text: '\$\$${q.zDisplay}\$\$',
                  textStyle: const TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
            ],

            // Clean Numbered Part Tabs (Rule 3: Clean digits or letters, no confusing sub-steps)
            if (hasParts) ...[
              const SizedBox(height: 14),
              const Divider(color: AppTheme.slate200, height: 1),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: List.generate(q.parts.length, (idx) {
                  final part = q.parts[idx];
                  final isSelected = idx == _activePartIndex;
                  final label = part.label.isNotEmpty ? part.label : '${idx + 1}';

                  return ChoiceChip(
                    label: Text(
                      'Part $label',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 13,
                        color: isSelected ? Colors.amber.shade900 : AppTheme.slate700,
                      ),
                    ),
                    selected: isSelected,
                    selectedColor: AppTheme.accentAmberLight,
                    backgroundColor: Colors.white,
                    side: BorderSide(
                      color: isSelected ? AppTheme.accentAmber : AppTheme.slate300,
                      width: isSelected ? 2 : 1,
                    ),
                    onSelected: (selected) {
                      if (selected) {
                        setState(() {
                          _activePartIndex = idx;
                          _gradeResult = null;
                        });
                      }
                    },
                  );
                }),
              ),

              // Active Part Question Highlight Card (Rule 3: amber accent card)
              const SizedBox(height: 10),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.accentAmberLight,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppTheme.accentAmber, width: 1.5),
                ),
                child: MathText(
                  text: q.parts[_activePartIndex].questionKm ??
                      q.parts[_activePartIndex].want ??
                      'Question Part ${q.parts[_activePartIndex].label}',
                  textStyle: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: Colors.amber.shade900,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildAnswerInputSection(LanguageProvider lang) {
    return Row(
      children: [
        // Answer TextField
        Expanded(
          child: TextField(
            controller: _answerController,
            decoration: InputDecoration(
              hintText: 'Enter your final answer here (e.g. 2 + 3i, \u03c0/2, 4)',
              suffixIcon: IconButton(
                icon: Icon(
                  _showKeypad ? Icons.keyboard_hide_outlined : Icons.keyboard_alt_outlined,
                  color: AppTheme.primaryNavy,
                ),
                onPressed: () => setState(() => _showKeypad = !_showKeypad),
                tooltip: 'Math Symbols Keyboard',
              ),
            ),
            onSubmitted: (_) => _checkAnswer(),
          ),
        ),
        const SizedBox(width: 12),

        // Check Answer Button
        ElevatedButton.icon(
          onPressed: _isGrading ? null : _checkAnswer,
          icon: _isGrading
              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
              : const Icon(Icons.check_circle_rounded, size: 18),
          label: Text(_isGrading ? lang.t('btn_checking') : lang.t('btn_check_answer')),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primaryNavy,
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          ),
        ),
      ],
    );
  }

  Widget _buildGradeVerdictSection(LanguageProvider lang) {
    final res = _gradeResult!;
    final isCorrect = res.correct;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: isCorrect ? AppTheme.successGreenLight : AppTheme.errorRedLight,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isCorrect ? AppTheme.successGreen : AppTheme.errorRed,
          width: 1.5,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                isCorrect ? Icons.check_circle_rounded : Icons.cancel_rounded,
                color: isCorrect ? AppTheme.successGreen : AppTheme.errorRed,
                size: 26,
              ),
              const SizedBox(width: 8),
              Text(
                isCorrect ? lang.t('verdict_correct') : lang.t('verdict_needs_revision'),
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: isCorrect ? Colors.green.shade900 : Colors.red.shade900,
                ),
              ),
            ],
          ),
          if (res.reason.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              '${lang.t('label_reason')} ${res.reason}',
              style: TextStyle(
                fontSize: 13,
                color: isCorrect ? Colors.green.shade800 : Colors.red.shade800,
              ),
            ),
          ],
          if (res.expected.isNotEmpty && !isCorrect) ...[
            const SizedBox(height: 6),
            Row(
              children: [
                Text(
                  lang.t('label_expected'),
                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.red.shade900),
                ),
                const SizedBox(width: 6),
                MathText(
                  text: '\$${res.expected}\$',
                  textStyle: TextStyle(fontWeight: FontWeight.bold, color: Colors.red.shade900),
                ),
              ],
            ),
          ],

          // Sequential Line-by-Line Breakdown if available
          if (res.stepCheck != null && res.stepCheck!.lineResults.isNotEmpty) ...[
            const SizedBox(height: 12),
            const Divider(),
            const SizedBox(height: 6),
            Text(
              lang.t('label_work_check'),
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
            ),
            const SizedBox(height: 6),
            for (final line in res.stepCheck!.lineResults) ...[
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 2.0),
                child: Row(
                  children: [
                    Icon(
                      line.correct == true ? Icons.check_circle_outline : Icons.highlight_off,
                      size: 16,
                      color: line.correct == true ? AppTheme.successGreen : AppTheme.errorRed,
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        'Line ${line.line}: ${line.text}',
                        style: const TextStyle(fontSize: 12, fontFamily: 'monospace'),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ],
      ),
    );
  }

  Widget _buildSolutionSection(LanguageProvider lang) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  lang.t('label_solution'),
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: AppTheme.primaryNavy),
                ),
                TextButton.icon(
                  onPressed: () => setState(() => _showSteps = !_showSteps),
                  icon: Icon(_showSteps ? Icons.visibility_off : Icons.visibility, size: 16),
                  label: Text(_showSteps ? lang.t('btn_hide_steps') : lang.t('btn_show_steps')),
                ),
              ],
            ),
            if (_showSteps) ...[
              const SizedBox(height: 12),
              for (final s in _currentQuestion!.steps) ...[
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Step ${s.stepOrder}: ${s.title}',
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                      ),
                      const SizedBox(height: 4),
                      MathText(
                        text: s.detail,
                        textStyle: const TextStyle(fontSize: 13, color: AppTheme.slate700),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }
}
