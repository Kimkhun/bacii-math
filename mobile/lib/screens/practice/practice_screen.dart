import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../../core/api/api_client.dart';
import '../../core/audio/sound_engine.dart';
import '../../core/i18n/app_translations.dart';
import '../../core/i18n/language_provider.dart';
import '../../core/i18n/prompt_localizer.dart';
import '../../core/theme/app_theme.dart';
import '../../models/detect_result.dart';
import '../../models/grade_result.dart';
import '../../models/graph.dart';
import '../../models/question.dart';
import '../../models/session.dart';
import '../../widgets/canvas/drawing_canvas.dart';
import '../../widgets/disambiguation_card.dart';
import '../../widgets/function_graph.dart';
import '../../models/formula.dart';
import '../../widgets/lesson_modal.dart';
import '../../widgets/marks_overlay.dart';
import '../../widgets/math_text.dart';

T? _firstOrNull<T>(Iterable<T> items, bool Function(T) test) {
  for (final it in items) {
    if (test(it)) return it;
  }
  return null;
}

// Question-type options per topic. Values encoded as "<question_type>:<variant>"
// where a technique/scenario axis exists (see web TYPE_OPTIONS).
const Map<String, List<List<String>>> _typeOptions = {
  'complex': [
    ['modulus', 'Modulus'],
    ['argument', 'Argument'],
    ['conjugate', 'Conjugate'],
    ['real_part', 'Real part'],
    ['imaginary_part', 'Imaginary part'],
    ['complex_arithmetic', 'Complex arithmetic'],
    ['complex_power', 'Powers of z'],
    ['de_moivre_power', "De Moivre's formula"],
    ['nth_roots', 'n-th roots'],
  ],
  'limit': [
    ['limit:rational', 'Rational limits'],
    ['limit:radical', 'Radical limits'],
    ['limit:trig', 'Trigonometric limits'],
    ['limit:exponential', 'Exponential limits'],
    ['limit:logarithmic', 'Logarithmic limits'],
    ['limit:infinity', 'Limits at infinity'],
  ],
  'integral': [
    ['definite_integral', 'Definite integral (any)'],
    ['definite_integral:polynomial', 'Definite — polynomial'],
    ['definite_integral:linear_argument', 'Definite — linear argument'],
    ['definite_integral:mixed_sum', 'Definite — mixed sum'],
    ['definite_integral:trig', 'Definite — trig'],
    ['definite_integral:u_substitution', 'Definite — u-substitution'],
    ['definite_integral:by_parts', 'Definite — by parts'],
    ['indefinite_integral', 'Indefinite integral (any)'],
    ['indefinite_integral:power', 'Indefinite — power'],
    ['indefinite_integral:expand', 'Indefinite — expand'],
    ['indefinite_integral:split', 'Indefinite — split'],
    ['indefinite_integral:linear_argument', 'Indefinite — linear argument'],
    ['indefinite_integral:usub', 'Indefinite — u-substitution'],
    ['indefinite_integral:trig_sec', 'Indefinite — trig (sec²)'],
    ['indefinite_integral:indefinite_sum', 'Indefinite — sum of several term types'],
  ],
  'probability': [
    ['probability:exercise_bag_split_atleast', 'Balls from a bag'],
    ['probability:exercise_two_bag_odd_even', 'Two bags of numbered balls'],
    ['probability:exercise_two_box_colors', 'Two boxes of colors'],
    ['probability:exercise_banknotes', 'Banknotes'],
    ['probability:exercise_pens', 'Pens'],
    ['probability:exercise_students', 'Students'],
    ['counting', 'Counting (any)'],
    ['counting:combination', 'Counting — combinations C(n, r)'],
    ['counting:permutation', 'Counting — permutations P(n, r)'],
  ],
  'functions': [
    ['study', 'Curve study & area']
  ],
  'continuity': [
    ['check_continuity', 'Continuity (any)'],
    ['check_continuity:check_at_point', 'Check continuity at a point'],
    ['check_continuity:find_parameter', 'Find the parameter that makes it continuous'],
  ],
  'derivatives': [
    ['compute_derivative', 'Compute derivative (any)'],
    ['compute_derivative:polynomial', 'Power rule, term by term'],
    ['compute_derivative:chain', 'Chain rule on a power'],
    ['compute_derivative:product', 'Product rule'],
    ['compute_derivative:quotient', 'Quotient rule'],
    ['compute_derivative:radical', 'Chain rule through a square root'],
    ['compute_derivative:trigonometric', 'Trigonometric derivatives'],
    ['compute_derivative:exponential', 'Exponential derivatives'],
    ['compute_derivative:logarithm', 'Logarithmic derivatives'],
    ['compute_derivative:second_order', 'Second derivative'],
  ],
  'differential_equations': [
    ['solve_ode', 'Differential equation (any)'],
    ['solve_ode:first_order_linear_homogeneous', "y' + ay = 0"],
    ['solve_ode:first_order_linear_nonhomogeneous', "y' + ay = g(x)"],
    ['solve_ode:second_order_homogeneous_constant_coeff', "y'' + by' + cy = 0"],
    ['solve_ode:second_order_nonhomogeneous', "y'' + by' + cy = g(x)"],
  ],
  'vectors_space': [
    ['vector_ops', 'Vector operations (any)'],
    ['vector_ops:magnitude', 'Magnitude of a vector |AB|'],
    ['vector_ops:distance', 'Distance between two points'],
    ['vector_ops:dot', 'Dot product AB · AC'],
    ['vector_ops:find_m_orthogonal', 'Find m making two vectors orthogonal'],
    ['vector_ops:cross_magnitude', 'Cross product magnitude |AB × AC|'],
    ['vector_ops:triangle_area', 'Area of a triangle'],
    ['vector_ops:scalar_triple_product', 'Scalar triple product u · (v × w)'],
  ],
  'conics': [
    ['classify_conic', 'Conics (any)'],
    ['classify_conic:vertex_x', 'Parabola — vertex (x)'],
    ['classify_conic:vertex_y', 'Parabola — vertex (y)'],
    ['classify_conic:p', 'Parabola — focal parameter p'],
    ['classify_conic:focus_x', 'Parabola — focus (x)'],
    ['classify_conic:focus_y', 'Parabola — focus (y)'],
    ['classify_conic:directrix', 'Parabola — directrix'],
    ['classify_conic:center_x', 'Ellipse / hyperbola — centre (x)'],
    ['classify_conic:center_y', 'Ellipse / hyperbola — centre (y)'],
    ['classify_conic:a', 'Ellipse / hyperbola — a'],
    ['classify_conic:b', 'Ellipse / hyperbola — b'],
    ['classify_conic:c', 'Ellipse / hyperbola — focal distance c'],
  ],
};

const List<String> _topics = [
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

({String? questionType, String? variant}) _splitType(String value) {
  if (value == 'any') return (questionType: null, variant: null);
  final i = value.indexOf(':');
  if (i == -1) return (questionType: value, variant: null);
  return (questionType: value.substring(0, i), variant: value.substring(i + 1));
}

class PracticeScreen extends StatefulWidget {
  final String? initialTopic;
  final String? initialSkill;
  final String? initialFormula;
  final String? initialAttempt;

  const PracticeScreen({
    super.key,
    this.initialTopic,
    this.initialSkill,
    this.initialFormula,
    this.initialAttempt,
  });

  @override
  State<PracticeScreen> createState() => _PracticeScreenState();
}

class _PartState {
  final DrawingCanvasController canvas = DrawingCanvasController();
  final TextEditingController typed = TextEditingController();
  DetectResult? detect;
  GradeResult? result;
  String? workText;
  bool correct = false;

  void dispose() {
    canvas.dispose();
    typed.dispose();
  }
}

class _PracticeScreenState extends State<PracticeScreen> {
  final ApiClient _api = ApiClient();

  String _topic = 'complex';
  String _questionType = 'any';
  String _difficulty = 'medium';
  String _mode = 'templates';

  Question? _question;
  List<_PartState> _parts = [];
  int _partIndex = 0;
  bool _exerciseDone = false;

  Explanation? _explanation;
  GraphGradeResult? _graphGrade;
  int _hintLevel = 0;

  bool _busy = false;
  String? _error;
  int _streak = 0;
  int _soundToken = 0;

  List<SessionSummary> _sessions = [];
  bool _reviewMode = false;
  String? _practicingSkillLabel;
  String? _practicingFormulaName;

  bool _showResults = true;

  List<String> get _partLabels =>
      _question?.parts.map((p) => p.label).where((l) => l.isNotEmpty).toList() ??
      [];

  _PartState? get _active =>
      _parts.isNotEmpty && _partIndex < _parts.length ? _parts[_partIndex] : null;

  QuestionPart? get _activePart {
    if (_question == null || _question!.parts.isEmpty) return null;
    if (_partIndex >= _question!.parts.length) return null;
    return _question!.parts[_partIndex];
  }

  String? get _currentPartLabel {
    final labels = _partLabels;
    if (labels.isEmpty) return null;
    return labels[_partIndex.clamp(0, labels.length - 1)];
  }

  String? get _lessonSkillKey {
    final q = _question;
    if (q == null) return null;
    final p = q.params;
    switch (q.topic) {
      case 'complex':
        return 'complex/${q.questionType}';
      case 'limit':
        final tech = p['technique'] ?? p['formula_name'];
        return tech != null ? 'limit/limit:$tech' : null;
      case 'derivatives':
        final tech = p['technique'];
        return tech != null ? 'derivatives/compute_derivative:$tech' : null;
      case 'continuity':
        final isParam = p['unknown'] != null && p['unknown'] != 'None';
        return 'continuity/check_continuity:${isParam ? 'find_parameter' : 'check_at_point'}';
      case 'differential_equations':
        final kind = p['kind'];
        return kind != null ? 'differential_equations/solve_ode:$kind' : null;
      case 'vectors_space':
        final op = p['op'];
        return op != null ? 'vectors_space/vector_ops:$op' : null;
      case 'conics':
        final ask = p['ask'];
        return ask != null ? 'conics/classify_conic:$ask' : null;
      case 'probability':
        if (q.questionType == 'counting') {
          final expr = (p['expr'] ?? '').toString();
          var kind = 'mixed';
          if (expr.contains('C(') && !expr.contains('P(')) kind = 'combination';
          else if (expr.contains('P(') && !expr.contains('C(')) kind = 'permutation';
          else if (expr.contains('!')) kind = 'factorial';
          return 'probability/counting:$kind';
        }
        final sid = p['scenario_id'] ?? p['variant'];
        return sid != null ? 'probability/probability:$sid' : null;
      case 'integral':
        final variant = p['variant'];
        return variant != null ? 'integral/${q.questionType}:$variant' : null;
    }
    return null;
  }

  @override
  void initState() {
    super.initState();
    if (widget.initialTopic != null && _topics.contains(widget.initialTopic)) {
      _topic = widget.initialTopic!;
    }
    _initStreak();
    if (widget.initialAttempt != null) {
      _loadReview(widget.initialAttempt!);
    } else if (widget.initialSkill != null) {
      _loadForcedSkill(widget.initialSkill!);
    } else if (widget.initialFormula != null) {
      _loadForcedFormula(widget.initialFormula!);
    } else {
      _loadSessions();
      _newQuestion();
    }
  }

  @override
  void dispose() {
    for (final p in _parts) {
      p.dispose();
    }
    super.dispose();
  }

  Future<void> _initStreak() async {
    final s = await SoundEngine.getStreak();
    if (mounted) setState(() => _streak = s);
  }

  Future<void> _loadSessions() async {
    try {
      final s = await _api.myProgress();
      if (mounted) setState(() => _sessions = s);
    } catch (_) {}
  }

  void _resetParts(int n, {int start = 0}) {
    for (final p in _parts) {
      p.dispose();
    }
    _parts = List.generate(math.max(1, n), (_) => _PartState());
    _partIndex = start.clamp(0, _parts.length - 1);
    _exerciseDone = false;
    _explanation = null;
    _graphGrade = null;
    _hintLevel = 0;
  }

  void _loadQuestion(Question q) {
    setState(() {
      _question = q;
      _resetParts(q.parts.length);
      _error = null;
      _fitGraphGrid(q);
    });
  }

  void _fitGraphGrid(Question q) {
    final g = q.graph;
    if (g == null) return;
    for (int i = 0; i < q.parts.length && i < _parts.length; i++) {
      if (q.parts[i].want == 'draw') {
        _parts[i].canvas.fitGridToWindow(g.xMin, g.xMax, g.yMin, g.yMax);
      }
    }
  }

  Future<Question> _generate() async {
    final split = _splitType(_questionType);
    return _api.generateProblem(
      generationMode: _topic == 'complex' ? _mode : 'templates',
      difficulty: _difficulty,
      topic: _topic,
      questionType: split.questionType,
      variant: split.variant,
    );
  }

  Future<void> _newQuestion() async {
    setState(() {
      _busy = true;
      _error = null;
      _practicingSkillLabel = null;
      _practicingFormulaName = null;
    });
    try {
      final q = await _generate();
      _loadQuestion(q);
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _loadForcedSkill(String skillKey) async {
    setState(() => _busy = true);
    try {
      final catalog = await _api.skillCatalog();
      final skill = _firstOrNull(catalog.skills, (s) => s.key == skillKey);
      final slash = skillKey.indexOf('/');
      _topic = skill?.topic ?? (slash == -1 ? _topic : skillKey.substring(0, slash));
      _questionType = slash == -1 ? 'any' : skillKey.substring(slash + 1);
      _difficulty = skill?.difficulty ?? _difficulty;
      _mode = 'templates';
      final q = await _generate();
      _loadQuestion(q);
      setState(() =>
          _practicingSkillLabel = skill?.label ?? _questionType.replaceAll('_', ' '));
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
    _loadSessions();
  }

  Future<void> _loadForcedFormula(String formulaId) async {
    setState(() => _busy = true);
    try {
      final catalog = await _api.getFormulas();
      FormulaEntry? entry;
      for (final t in catalog.topics) {
        entry = _firstOrNull(t.entries, (e) => e.id == formulaId);
        if (entry != null) break;
      }
      final ref =
          (entry != null && entry.variants.isNotEmpty) ? entry.variants.first : null;
      if (ref != null) {
        _topic = ref.topic;
        _questionType =
            ref.variant != null ? '${ref.questionType}:${ref.variant}' : ref.questionType;
        _difficulty = ref.difficulty;
        _mode = 'templates';
      } else {
        _questionType = 'any';
      }
      final q = await _generate();
      _loadQuestion(q);
      setState(() => _practicingFormulaName =
          entry?.nameEn ?? formulaId.replaceAll('_', ' '));
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
    _loadSessions();
  }

  Future<void> _loadReview(String attemptId) async {
    setState(() => _busy = true);
    try {
      final d = await _api.attempt(attemptId);
      if (d.question != null) {
        final labels =
            d.stepCheck != null ? <String>[] : <String>[]; // parts unknown here
        final q = Question(
          id: d.question!.id,
          topic: d.question!.topic,
          questionType: d.question!.questionType,
          difficulty: d.question!.difficulty,
          prompt: d.question!.prompt,
          promptLatex: d.question!.promptLatex,
          zDisplay: '',
          source: 'review',
          formulaTags: d.question!.formulaTags,
        );
        _question = q;
        _resetParts(math.max(1, labels.length));
        if (d.strokes != null) {
          await _parts[0].canvas.loadStrokes(d.strokes!);
        }
        _parts[0].workText = d.workText;
        _parts[0].detect = d.workText != null
            ? DetectResult(
                lines: d.workText!.split('\n'),
                linesBoxes: d.linesBoxes,
              )
            : null;
        _parts[0].result = GradeResult(
          attemptId: d.id,
          correct: d.correct,
          reason: d.reason,
          expected: d.question!.expectedAnswer,
          given: d.parsedAnswer,
          stepCheck: d.stepCheck,
        );
        if (d.explanations.isNotEmpty) {
          _explanation = Explanation(
            content: d.explanations.first.content,
            provider: d.explanations.first.provider,
            trigger: d.explanations.first.trigger,
            stepCheck: d.stepCheck,
          );
        }
        _reviewMode = true;
      }
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  // --- checking ---
  Future<void> _check() async {
    final q = _question;
    final part = _active;
    if (q == null || part == null) {
      setState(() => _error = 'Generate a question first.');
      return;
    }
    setState(() {
      _error = null;
      part.result = null;
      _explanation = null;
      _graphGrade = null;
    });

    // "Draw the graph" part → graph grading on the ink.
    if (_activePart?.want == 'draw') {
      setState(() => _busy = true);
      try {
        final thumb = await part.canvas.getInkSnapshot();
        if (thumb == null) {
          setState(() => _error = 'Draw the graph on the page first.');
          return;
        }
        final gg = await _api.gradeGraph(q.id, thumb);
        setState(() {
          _graphGrade = gg;
          part.result = GradeResult(
              correct: true,
              reason: 'graph',
              expected: '',
              part: _currentPartLabel,
              allComplete: true);
          _exerciseDone = true;
        });
      } catch (e) {
        setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
      } finally {
        if (mounted) setState(() => _busy = false);
      }
      return;
    }

    final typed = part.typed.text.trim();
    if (typed.isNotEmpty) {
      await _finalizeCheck(
          DetectResult(rawText: typed), const [], const []);
      return;
    }

    setState(() => _busy = true);
    try {
      final ink = await part.canvas.getImageBase64();
      if (ink == null) {
        setState(() {
          _error = 'Write an answer on the page, upload an image, or type one.';
          _busy = false;
        });
        return;
      }
      final det = await _api.detect(ink);
      part.detect = det;
      if (det.rawText.isEmpty && det.lines.isEmpty) {
        setState(() {
          _error = 'Could not read the handwriting. Try writing larger or clearer.';
          _busy = false;
        });
        return;
      }
      setState(() => _busy = false);

      // Disambiguation queue.
      final lines = List<String>.from(det.lines);
      final latex = List<String>.from(det.linesLatex);
      if (!mounted) return;
      final lang = context.read<LanguageProvider>();
      for (int i = 0; i < det.lines.length; i++) {
        final alts = i < det.linesAlt.length ? det.linesAlt[i] : const <String>[];
        if (alts.isEmpty) continue;
        final altLatex =
            i < det.linesAltLatex.length ? det.linesAltLatex[i] : const <String>[];
        if (!mounted) return;
        final choice = await showDisambiguationDialog(
          context,
          lang,
          lineNumber: i + 1,
          primary: DisambiguationCandidate(
              text: det.lines[i],
              latex: i < det.linesLatex.length ? det.linesLatex[i] : null),
          candidates: [
            for (int j = 0; j < alts.length; j++)
              DisambiguationCandidate(
                  text: alts[j], latex: j < altLatex.length ? altLatex[j] : null)
          ],
        );
        if (choice is PickCandidate) {
          lines[i] = alts[choice.index];
          if (choice.index < altLatex.length) latex[i] = altLatex[choice.index];
        } else if (choice is WriteAgain) {
          final box = i < det.linesBoxes.length ? det.linesBoxes[i] : null;
          if (box != null) part.canvas.eraseRegion(box);
          setState(() => _error = 'Redraw that line, then check your work again.');
          return;
        }
        // PickNone / dismissed → keep OCR reading.
      }
      await _finalizeCheck(det, lines, latex);
    } catch (e) {
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _busy = false;
      });
    }
  }

  Future<void> _finalizeCheck(
      DetectResult det, List<String> lines, List<String> latex) async {
    final q = _question;
    final part = _active;
    if (q == null || part == null) return;
    setState(() => _busy = true);
    try {
      final finalDet = det.copyWith(lines: lines, linesLatex: latex);
      final work = lines.isNotEmpty ? lines.join('\n') : null;
      part.workText = work;
      part.detect = finalDet;
      final answer = finalDet.rawText.isNotEmpty
          ? finalDet.rawText
          : (lines.isNotEmpty ? lines.last : '');
      final lang = context.read<LanguageProvider>().currentLang;
      final strokes = part.canvas.getStrokes();
      final strokesThumb = await part.canvas.getStrokesThumb();

      final res = await _api.grade(
        questionId: q.id,
        userAnswer: answer.isNotEmpty ? answer : 'written',
        workText: work,
        linesBoxes: finalDet.linesBoxes.isNotEmpty ? finalDet.linesBoxes : null,
        part: _currentPartLabel,
        hintsUsed: _hintLevel,
        strokes: strokes,
        strokesThumb: strokesThumb,
        lang: lang,
      );

      part.result = res;
      part.correct = res.correct;
      if (res.explanation != null) _explanation = res.explanation;

      final nowDone = res.correct && (res.allComplete ?? false);
      if (nowDone) {
        _exerciseDone = true;
      } else if (res.correct && _currentPartLabel != null && _partLabels.length > 1) {
        _partIndex = math.min(_partIndex + 1, _partLabels.length - 1);
      }

      if (q.topic == 'functions' && res.graph != null) {
        final thumb = await part.canvas.getInkSnapshot();
        if (thumb != null) {
          _api.gradeGraph(q.id, thumb).then((gg) {
            if (mounted) setState(() => _graphGrade = gg);
          }).catchError((_) {});
        }
      }

      final newStreak = await SoundEngine.updateStreak(res.correct);
      _streak = newStreak;
      _playGradeSounds(finalDet, res, newStreak);
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _playGradeSounds(DetectResult det, GradeResult res, int streak) {
    final token = ++_soundToken;
    final check = res.stepCheck;
    final events = <bool>[];
    if (check != null) {
      for (int i = 0; i < det.lines.length; i++) {
        final lr = _firstOrNull(check.lineResults, (r) => r.line == i + 1);
        if (lr != null && lr.checked) events.add(lr.correct == true);
      }
    }
    const stagger = Duration(milliseconds: 700);
    if (events.isEmpty) {
      drawingAudio.playGradeSound(res.correct);
      return;
    }
    if (res.correct) {
      for (int i = 0; i < events.length; i++) {
        Future.delayed(stagger * i, () {
          if (_soundToken == token) {
            drawingAudio.playMarkSound(true, math.max(streak - 1, 0) + i);
          }
        });
      }
      Future.delayed(stagger * events.length, () {
        if (_soundToken == token) {
          drawingAudio.playMarkSound(true, math.max(streak - 1, 0) + events.length);
        }
      });
    } else {
      int correctSeen = 0;
      bool thud = false;
      for (int i = 0; i < events.length; i++) {
        final e = events[i];
        final delay = stagger * i;
        if (e) {
          final seen = correctSeen++;
          Future.delayed(delay, () {
            if (_soundToken == token) drawingAudio.playMarkSound(true, seen);
          });
        } else if (!thud) {
          thud = true;
          Future.delayed(delay, () {
            if (_soundToken == token) drawingAudio.playMarkSound(false, 0);
          });
        }
      }
    }
  }

  // --- hints / explanation ---
  Future<void> _showHint() async {
    if (_explanation == null) {
      await _fetchExplanation();
      setState(() => _hintLevel = 1);
      return;
    }
    setState(() => _hintLevel =
        math.min(_hintLevel + 1, _explanation!.steps.isEmpty ? _hintLevel + 1 : _explanation!.steps.length));
  }

  Future<void> _fetchExplanation() async {
    final q = _question;
    final part = _active;
    if (q == null) return;
    setState(() => _busy = true);
    try {
      final lang = context.read<LanguageProvider>().currentLang;
      final exp = await _api.explain(q.id,
          userAnswer: part?.detect?.rawText,
          workText: part?.workText,
          lang: lang);
      setState(() => _explanation = exp);
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  // --- save / resume ---
  Future<void> _saveProgress() async {
    final q = _question;
    final part = _active;
    if (q == null || part == null) return;
    setState(() => _busy = true);
    try {
      final strokes = part.canvas.getStrokes();
      final thumb = await part.canvas.getStrokesThumb();
      final summary = await _api.saveProgress(
        questionId: q.id,
        part: _currentPartLabel,
        typed: part.typed.text.trim().isNotEmpty ? part.typed.text.trim() : null,
        workText: part.workText,
        linesBoxes: part.detect?.linesBoxes,
        strokes: strokes,
        strokesThumb: thumb,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('Saved (${summary.partsDone}/${summary.partsTotal} parts)'),
          behavior: SnackBarBehavior.floating,
        ));
      }
      _loadSessions();
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _resumeSession(String id) async {
    setState(() => _busy = true);
    try {
      final d = await _api.progress(id);
      final labels = d.parts.keys.toList();
      _question = d.question;
      _resetParts(math.max(1, labels.length));
      _reviewMode = false;
      int firstUndone = labels.length - 1;
      for (int i = 0; i < labels.length; i++) {
        final st = d.parts[labels[i]]!;
        _parts[i].typed.text = st.typed ?? '';
        _parts[i].workText = st.workText;
        if (st.strokes != null) await _parts[i].canvas.loadStrokes(st.strokes!);
        if (st.correct) {
          _parts[i].correct = true;
          _parts[i].result = GradeResult(
              correct: true, reason: 'saved', expected: '');
        } else if (firstUndone == labels.length - 1) {
          firstUndone = i;
        }
      }
      _exerciseDone = labels.isNotEmpty && labels.every((l) => d.parts[l]!.correct);
      _partIndex = firstUndone.clamp(0, _parts.length - 1);
      _topic = d.question.topic;
      _difficulty = d.question.difficulty;
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _deleteSession(String id) async {
    try {
      await _api.deleteProgress(id);
      setState(() => _sessions.removeWhere((s) => s.id == id));
    } catch (_) {}
  }

  Future<void> _replayReview() async {
    final q = _question;
    if (q == null) return;
    setState(() => _busy = true);
    try {
      final nq = await _api.replay(q.id);
      setState(() => _reviewMode = false);
      _loadQuestion(nq);
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _uploadImage() async {
    final part = _active;
    if (part == null) return;
    try {
      final picker = ImagePicker();
      final file = await picker.pickImage(source: ImageSource.gallery);
      if (file == null) return;
      final bytes = await file.readAsBytes();
      await part.canvas.loadImageStroke(bytes);
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    }
  }

  void _openLesson() {
    final key = _lessonSkillKey;
    if (key == null) return;
    showDialog(
      context: context,
      builder: (_) => LessonModal(
        skillKey: key,
        fallbackLabel: _practicingSkillLabel ??
            questionTypeLabel(_question?.questionType ?? '',
                context.read<LanguageProvider>().currentLang),
      ),
    );
  }

  // --- build ---
  @override
  Widget build(BuildContext context) {
    final lang = Provider.of<LanguageProvider>(context);
    return Column(
      children: [
        _header(lang),
        if (_partLabels.length > 1) _sectionTabs(),
        Expanded(child: _canvasArea(lang)),
      ],
    );
  }

  Widget _header(LanguageProvider lang) {
    final q = _question;
    return Material(
      elevation: 1,
      child: Container(
        color: Colors.white,
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (_reviewMode || _practicingSkillLabel != null || _practicingFormulaName != null)
              _banner(lang),
            // config row
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  if (!_reviewMode) ...[
                    _topicDropdown(lang),
                    const SizedBox(width: 8),
                    _typeDropdown(lang),
                    const SizedBox(width: 8),
                    _difficultyDropdown(lang),
                    if (_topic == 'complex') ...[
                      const SizedBox(width: 8),
                      _modeDropdown(lang),
                    ],
                    const SizedBox(width: 8),
                  ],
                  if (_streak > 0)
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: Chip(
                        visualDensity: VisualDensity.compact,
                        backgroundColor: AppTheme.accentAmberLight,
                        label: Text('🔥 $_streak',
                            style: const TextStyle(fontSize: 12)),
                      ),
                    ),
                  if (_lessonSkillKey != null)
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: OutlinedButton.icon(
                        onPressed: _openLesson,
                        icon: const Text('📖'),
                        label: Text(lang.t('lesson'),
                            style: const TextStyle(fontSize: 12)),
                      ),
                    ),
                  if (_sessions.isNotEmpty && !_reviewMode)
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: OutlinedButton(
                        onPressed: _showSessionsSheet,
                        child: Text('${lang.t('btn_saved')} (${_sessions.length})',
                            style: const TextStyle(fontSize: 12)),
                      ),
                    ),
                  OutlinedButton(
                    onPressed: _busy || q == null ? null : _saveProgress,
                    child: Text(lang.t('action_save'),
                        style: const TextStyle(fontSize: 12)),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: _busy ? null : _newQuestion,
                    child: Text(_busy ? lang.t('btn_generating') : lang.t('btn_new_question'),
                        style: const TextStyle(fontSize: 12)),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            // prompt
            if (q != null)
              _promptWidget(q, lang)
            else
              Text(lang.t('prompt_select_guide'),
                  style: const TextStyle(color: AppTheme.slate600, fontSize: 13)),
            if (_activePart != null) ...[
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppTheme.accentAmberLight,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppTheme.accentAmber),
                ),
                child: MathText(
                  text: _activePart!.questionKm ??
                      _activePart!.want ??
                      'Part ${_activePart!.label}',
                  textStyle: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: Colors.amber.shade900),
                ),
              ),
            ],
            if (_error != null) ...[
              const SizedBox(height: 6),
              Text(_error!,
                  style: const TextStyle(color: AppTheme.errorRed, fontSize: 12)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _promptWidget(Question q, LanguageProvider lang) {
    final loc = formatLocalizedPrompt(
      topic: q.topic,
      questionType: q.questionType,
      params: q.params,
      rawPrompt: q.prompt,
      rawPromptLatex: q.promptLatex,
      lang: lang.currentLang,
      zDisplay: q.zDisplay,
    );
    final text = (loc.promptLatex != null && loc.promptLatex!.isNotEmpty)
        ? '\$${loc.promptLatex}\$'
        : loc.prompt;
    return ConstrainedBox(
      constraints: const BoxConstraints(maxHeight: 140),
      child: SingleChildScrollView(
        child: MathText(
          text: text,
          textStyle: const TextStyle(
              fontSize: 15, fontWeight: FontWeight.w600, height: 1.4),
        ),
      ),
    );
  }

  Widget _banner(LanguageProvider lang) {
    String label;
    if (_reviewMode) {
      label = lang.t('practice_reviewing_banner');
    } else if (_practicingSkillLabel != null) {
      label = '${lang.t('practice_practicing')}: $_practicingSkillLabel';
    } else {
      label = '${lang.t('practice_practicing')}: $_practicingFormulaName';
    }
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppTheme.primaryNavy,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(label,
                style: const TextStyle(color: Colors.white, fontSize: 12)),
          ),
          if (_reviewMode) ...[
            TextButton(
              onPressed: _busy ? null : _replayReview,
              child: Text(lang.t('practice_replay'),
                  style: const TextStyle(color: Colors.white, fontSize: 11)),
            ),
            TextButton(
              onPressed: () {
                setState(() {
                  _reviewMode = false;
                  _question = null;
                });
                _loadSessions();
                _newQuestion();
              },
              child: Text(lang.t('practice_exit_review'),
                  style: const TextStyle(color: Colors.white70, fontSize: 11)),
            ),
          ] else
            TextButton(
              onPressed: () => setState(() {
                _practicingSkillLabel = null;
                _practicingFormulaName = null;
              }),
              child: Text(lang.t('practice_dismiss'),
                  style: const TextStyle(color: Colors.white70, fontSize: 11)),
            ),
        ],
      ),
    );
  }

  Widget _topicDropdown(LanguageProvider lang) => _dropdown<String>(
        value: _topic,
        items: [for (final t in _topics) (t, lang.t('topic_$t'))],
        onChanged: (v) => setState(() {
          _topic = v;
          _questionType = 'any';
        }),
      );

  Widget _typeDropdown(LanguageProvider lang) {
    final opts = _typeOptions[_topic] ?? const [];
    return _dropdown<String>(
      value: _questionType,
      items: [
        ('any', lang.t('qtype_any')),
        for (final o in opts) (o[0], questionTypeLabel(o[0], lang.currentLang)),
      ],
      onChanged: (v) => setState(() => _questionType = v),
    );
  }

  Widget _difficultyDropdown(LanguageProvider lang) => _dropdown<String>(
        value: _difficulty,
        items: [
          ('easy', lang.t('diff_easy')),
          ('medium', lang.t('diff_medium')),
          ('hard', lang.t('diff_hard')),
        ],
        onChanged: (v) => setState(() => _difficulty = v),
      );

  Widget _modeDropdown(LanguageProvider lang) => _dropdown<String>(
        value: _mode,
        items: [
          ('templates', lang.t('mode_templates')),
          ('gemini', lang.t('mode_gemini')),
        ],
        onChanged: (v) => setState(() => _mode = v),
      );

  Widget _dropdown<T>({
    required T value,
    required List<(T, String)> items,
    required ValueChanged<T> onChanged,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      decoration: BoxDecoration(
        border: Border.all(color: AppTheme.slate300),
        borderRadius: BorderRadius.circular(6),
      ),
      child: DropdownButton<T>(
        value: value,
        underline: const SizedBox(),
        isDense: true,
        style: const TextStyle(fontSize: 12, color: AppTheme.primaryNavy),
        items: [
          for (final it in items)
            DropdownMenuItem(value: it.$1, child: Text(it.$2))
        ],
        onChanged: (v) {
          if (v != null) onChanged(v);
        },
      ),
    );
  }

  Widget _sectionTabs() {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            for (int i = 0; i < _partLabels.length; i++) ...[
              GestureDetector(
                onTap: () => setState(() {
                  _partIndex = i;
                  _explanation = null;
                }),
                child: Container(
                  margin: const EdgeInsets.only(right: 8),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: i == _partIndex
                        ? AppTheme.primaryNavy
                        : (_parts[i].correct
                            ? AppTheme.successGreenLight
                            : AppTheme.slate100),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (_parts[i].correct)
                        const Text('✓ ',
                            style: TextStyle(color: AppTheme.successGreen)),
                      Text(_partLabels[i],
                          style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 12,
                              color: i == _partIndex
                                  ? Colors.white
                                  : AppTheme.slate700)),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _canvasArea(LanguageProvider lang) {
    final part = _active;
    if (part == null) {
      return const Center(child: Text('Generate a question to begin.'));
    }
    return Stack(
      children: [
        Positioned.fill(
          child: DrawingCanvas(
            key: ValueKey('canvas-$_partIndex-${_question?.id}'),
            controller: part.canvas,
            overlayBuilder: (map) {
              final det = part.detect;
              final res = part.result;
              if (det != null && res != null && det.linesBoxes.isNotEmpty) {
                return MarksOverlay(det: det, result: res, map: map);
              }
              return null;
            },
          ),
        ),
        // pen size + tool strip (left)
        Positioned(left: 6, top: 8, child: _toolStrip(part)),
        // results panel (right, above toolbar)
        if (part.result != null && _showResults)
          Positioned(
            right: 6,
            bottom: 70,
            width: MediaQuery.of(context).size.width < 520
                ? MediaQuery.of(context).size.width - 12
                : 360,
            child: _resultsPanel(lang, part),
          ),
        // bottom toolbar
        Positioned(
          left: 0,
          right: 0,
          bottom: 6,
          child: Center(child: _toolbar(lang, part)),
        ),
      ],
    );
  }

  Widget _toolStrip(_PartState part) {
    final c = part.canvas;
    return Material(
      elevation: 2,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 2),
        width: 44,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            RotatedBox(
              quarterTurns: 3,
              child: SizedBox(
                width: 90,
                child: Slider(
                  min: c.tool == CanvasTool.eraser ? 10.0 : 1.0,
                  max: c.tool == CanvasTool.eraser ? 100.0 : 30.0,
                  value: (c.tool == CanvasTool.eraser
                          ? c.eraserWidth
                          : c.penWidth)
                      .clamp(c.tool == CanvasTool.eraser ? 10.0 : 1.0,
                          c.tool == CanvasTool.eraser ? 100.0 : 30.0)
                      .toDouble(),
                  onChanged: (v) => setState(() => c.tool == CanvasTool.eraser
                      ? c.setEraserWidth(v)
                      : c.setPenWidth(v)),
                ),
              ),
            ),
            Text(
              '${(c.tool == CanvasTool.eraser ? c.eraserWidth : c.penWidth).round()}',
              style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
            ),
          ],
        ),
      ),
    );
  }

  Widget _toolbar(LanguageProvider lang, _PartState part) {
    final c = part.canvas;
    Widget toolBtn(CanvasTool t, String label) => _tinyBtn(
          label,
          active: c.tool == t,
          onTap: () => setState(() => c.setTool(t)),
        );
    return Material(
      elevation: 4,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width - 12),
        padding: const EdgeInsets.all(6),
        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              toolBtn(CanvasTool.pen, lang.t('tool_pen')),
              toolBtn(CanvasTool.eraser, lang.t('tool_eraser')),
              toolBtn(CanvasTool.ruler, lang.t('tool_line')),
              toolBtn(CanvasTool.curve, lang.t('tool_curve')),
              toolBtn(CanvasTool.ellipse, lang.t('tool_ellipse')),
              toolBtn(CanvasTool.select, lang.t('tool_select')),
              _tinyBtn(
                c.hasGrid ? '${lang.t('tool_axes')} ✓' : lang.t('tool_axes'),
                active: c.tool == CanvasTool.axes && c.hasGrid,
                onTap: () {
                  setState(() {
                    if (c.tool == CanvasTool.axes && c.hasGrid) {
                      c.hideGrid();
                      c.setTool(CanvasTool.pen);
                    } else {
                      if (!c.hasGrid) c.spawnGrid(1, 1);
                      c.setTool(CanvasTool.axes);
                    }
                  });
                },
              ),
              AnimatedBuilder(
                animation: c,
                builder: (context, _) => Row(
                  children: [
                    _iconBtn(Icons.undo, c.canUndo ? () => setState(c.undo) : null),
                    _iconBtn(Icons.redo, c.canRedo ? () => setState(c.redo) : null),
                  ],
                ),
              ),
              _iconBtn(Icons.delete_outline, () {
                setState(() {
                  c.clear();
                  part.detect = null;
                  part.result = null;
                });
              }),
              _tinyBtn(lang.t('tool_hint'),
                  onTap: _busy || _question == null ? null : _showHint),
              _iconBtn(Icons.upload_outlined, _uploadImage),
              _iconBtn(Icons.remove, () => setState(() => c.setZoom(c.zoom - 0.2))),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 2),
                child: Text('${(c.zoom * 100).round()}%',
                    style: const TextStyle(fontSize: 11)),
              ),
              _iconBtn(Icons.add, () => setState(() => c.setZoom(c.zoom + 0.2))),
              SizedBox(
                width: 110,
                child: TextField(
                  controller: part.typed,
                  style: const TextStyle(fontSize: 12),
                  decoration: InputDecoration(
                    isDense: true,
                    hintText: lang.t('placeholder_type_answer'),
                    contentPadding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                  ),
                ),
              ),
              const SizedBox(width: 6),
              ElevatedButton(
                onPressed: _busy ? null : _check,
                style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10)),
                child: Text(_busy ? lang.t('btn_checking') : lang.t('tool_check_work'),
                    style: const TextStyle(fontSize: 12)),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _tinyBtn(String label, {bool active = false, VoidCallback? onTap}) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 2),
      child: TextButton(
        onPressed: onTap,
        style: TextButton.styleFrom(
          backgroundColor: active ? AppTheme.primaryNavy : AppTheme.slate100,
          foregroundColor: active ? Colors.white : AppTheme.slate700,
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
          minimumSize: Size.zero,
          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        ),
        child: Text(label, style: const TextStyle(fontSize: 12)),
      ),
    );
  }

  Widget _iconBtn(IconData icon, VoidCallback? onTap) {
    return IconButton(
      onPressed: onTap,
      icon: Icon(icon, size: 18),
      visualDensity: VisualDensity.compact,
      constraints: const BoxConstraints(minWidth: 34, minHeight: 34),
      padding: EdgeInsets.zero,
    );
  }

  Widget _resultsPanel(LanguageProvider lang, _PartState part) {
    final res = part.result!;
    final correct = res.correct;
    return Material(
      elevation: 6,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        constraints: BoxConstraints(
            maxHeight: MediaQuery.of(context).size.height * 0.5),
        decoration: BoxDecoration(
          color: correct ? AppTheme.successGreenLight : AppTheme.errorRedLight,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
              color: correct ? AppTheme.successGreen : AppTheme.errorRed),
        ),
        padding: const EdgeInsets.all(12),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      _exerciseDone
                          ? lang.t('verdict_complete')
                          : correct
                              ? '${lang.t('label_part')} ${res.part ?? ''} ${lang.t('verdict_correct')}'
                              : lang.t('verdict_incorrect'),
                      style: const TextStyle(
                          fontWeight: FontWeight.bold, fontSize: 15),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, size: 16),
                    visualDensity: VisualDensity.compact,
                    onPressed: () => setState(() => _showResults = false),
                  ),
                ],
              ),
              if (_exerciseDone)
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _busy ? null : _newQuestion,
                    child: Text(lang.t('action_next_question')),
                  ),
                ),
              if (res.parts.isNotEmpty)
                ...res.parts.map((pv) => Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text(
                        '${pv.correct ? "✓" : "✗"} ${pv.label}  ${pv.correct ? "" : "${lang.t('verdict_expected')} ${pv.expected ?? ''}"}',
                        style: const TextStyle(fontSize: 12),
                      ),
                    ))
              else if (!correct)
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Row(
                    children: [
                      Text('${lang.t('label_expected')}: ',
                          style: const TextStyle(
                              fontSize: 13, fontWeight: FontWeight.bold)),
                      Flexible(child: MathText(text: '\$${res.expected}\$')),
                    ],
                  ),
                ),
              const SizedBox(height: 4),
              Text('${lang.t('label_reason')}: ${res.reason}',
                  style: const TextStyle(fontSize: 11, color: AppTheme.slate600)),
              if (res.rubricScore != null) _rubricWidget(lang, res),
              if (res.teacherFeedback?.content.isNotEmpty ?? false)
                _teacherTip(lang, res.teacherFeedback!.content),
              if (res.graph != null) ...[
                const Divider(),
                Text(lang.t('label_ref_graph_compare'),
                    style: const TextStyle(
                        fontSize: 11, color: AppTheme.slate600)),
                FunctionGraph(graph: res.graph!),
                if (_graphGrade != null && _graphGrade!.error == null)
                  _graphAssessment(lang, _graphGrade!),
              ],
              if (part.workText != null && part.workText!.split('\n').length > 1)
                _yourWorkWidget(lang, part, res),
              if (_explanation != null) _explanationWidget(lang, _explanation!),
            ],
          ),
        ),
      ),
    );
  }

  Widget _rubricWidget(LanguageProvider lang, GradeResult res) {
    final r = res.rubricScore!;
    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(lang.t('label_step_score'),
                  style: const TextStyle(
                      fontSize: 12, fontWeight: FontWeight.bold)),
              Text('${r.earned.toStringAsFixed(1)} / ${r.possible.toStringAsFixed(0)}',
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
            ],
          ),
          for (final b in r.breakdown)
            Text(
              '${b.pointsEarned > 0 ? "✓" : "✗"} ${b.label} (${b.pointsEarned.toStringAsFixed(1)}/${b.pointsPossible.toStringAsFixed(1)})',
              style: TextStyle(
                  fontSize: 11,
                  color: b.pointsEarned > 0
                      ? AppTheme.successGreen
                      : AppTheme.slate600),
            ),
        ],
      ),
    );
  }

  Widget _teacherTip(LanguageProvider lang, String content) {
    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppTheme.accentAmberLight,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.accentAmber),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('👨‍🏫 ${lang.t('label_teacher_tip')}',
              style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: Colors.amber.shade900)),
          const SizedBox(height: 4),
          MathText(text: content, textStyle: const TextStyle(fontSize: 12)),
        ],
      ),
    );
  }

  Widget _graphAssessment(LanguageProvider lang, GraphGradeResult gg) {
    Widget flag(String label, bool? ok) {
      if (ok == null) return const SizedBox.shrink();
      return Text('$label ${ok ? "✓" : "✗"}',
          style: TextStyle(
              fontSize: 11,
              color: ok ? AppTheme.successGreen : AppTheme.errorRed));
    }

    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(lang.t('label_graph_assessment'),
              style: const TextStyle(fontSize: 11, color: AppTheme.slate600)),
          Row(
            children: [
              Text('${gg.score ?? 0}/100',
                  style: const TextStyle(
                      fontSize: 16, fontWeight: FontWeight.bold)),
              const SizedBox(width: 8),
              flag(lang.t('label_curve'), gg.curveCorrect),
              const SizedBox(width: 6),
              flag(lang.t('label_asymptotes'), gg.asymptotesCorrect),
              const SizedBox(width: 6),
              flag(lang.t('label_tangent'), gg.tangentCorrect),
              const SizedBox(width: 6),
              flag(lang.t('label_points'), gg.pointsCorrect),
            ],
          ),
          if (gg.feedback != null)
            Text(gg.feedback!, style: const TextStyle(fontSize: 11)),
        ],
      ),
    );
  }

  Widget _yourWorkWidget(LanguageProvider lang, _PartState part, GradeResult res) {
    final lines = part.workText!.split('\n');
    final linesLatex = part.detect?.linesLatex ?? const <String>[];
    final errLine = res.stepCheck?.firstErrorLine;
    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(lang.t('label_your_work'),
              style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.slate600)),
          const SizedBox(height: 4),
          for (int i = 0; i < lines.length; i++)
            Builder(builder: (_) {
              final lineNo = i + 1;
              final isError = errLine == lineNo;
              final latex = i < linesLatex.length ? linesLatex[i] : null;
              final lineRes = res.stepCheck?.lineResults
                  .where((r) => r.line == lineNo)
                  .cast<StepCheckLine?>()
                  .firstWhere((_) => true, orElse: () => null);
              final formulaName = isError ? lineRes?.formula?.replaceAll('_', ' ') : null;
              final color = isError ? AppTheme.errorRed : AppTheme.slate600;
              return Padding(
                padding: const EdgeInsets.only(bottom: 2),
                child: RichText(
                  text: TextSpan(
                    children: [
                      if (isError)
                        TextSpan(
                            text: '→ ',
                            style: TextStyle(
                                color: color, fontWeight: FontWeight.bold)),
                      WidgetSpan(
                        alignment: PlaceholderAlignment.middle,
                        child: MathText(
                          text: (latex != null && latex.isNotEmpty)
                              ? '\\($latex\\)'
                              : lines[i],
                          textStyle: TextStyle(
                              fontSize: 12,
                              color: color,
                              fontWeight:
                                  isError ? FontWeight.w600 : FontWeight.normal),
                        ),
                      ),
                      if (formulaName != null && formulaName.isNotEmpty)
                        TextSpan(
                            text: ' ($formulaName)',
                            style: TextStyle(
                                fontSize: 10,
                                color: color.withValues(alpha: 0.7))),
                    ],
                  ),
                ),
              );
            }),
        ],
      ),
    );
  }

  Widget _explanationWidget(LanguageProvider lang, Explanation exp) {
    final steps = exp.steps;
    final showCount = _hintLevel > 0 ? _hintLevel : steps.length;
    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.85),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (steps.isNotEmpty) ...[
            Text(lang.t('label_solution'),
                style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.slate600)),
            for (final s in steps.take(showCount))
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: MathText(
                    text: '${lang.t('label_step')} ${s.stepOrder}: ${s.detail}',
                    textStyle: const TextStyle(fontSize: 12)),
              ),
          ],
          if (_hintLevel == 0 || _hintLevel >= steps.length)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: MathText(text: exp.content, textStyle: const TextStyle(fontSize: 12)),
            ),
          if (exp.workCheck?.content.isNotEmpty ?? false) ...[
            const Divider(),
            Text(lang.t('label_work_check'),
                style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.slate600)),
            MathText(text: exp.workCheck!.content, textStyle: const TextStyle(fontSize: 12)),
          ],
        ],
      ),
    );
  }

  void _showSessionsSheet() {
    final lang = context.read<LanguageProvider>();
    showModalBottomSheet(
      context: context,
      builder: (ctx) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          padding: const EdgeInsets.all(12),
          children: [
            for (final s in _sessions)
              ListTile(
                title: Text(
                    (s.question?.prompt ?? '').split('\n').first,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis),
                subtitle: Text(
                    '${questionTypeLabel(s.question?.questionType ?? '', lang.currentLang)} · ${s.partsDone}/${s.partsTotal}${s.status == "completed" ? " · done" : ""}'),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextButton(
                      onPressed: () {
                        Navigator.pop(ctx);
                        _resumeSession(s.id);
                      },
                      child: Text(lang.t('action_resume')),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close, size: 16),
                      onPressed: () {
                        _deleteSession(s.id);
                        Navigator.pop(ctx);
                      },
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
