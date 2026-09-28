import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
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
import '../../widgets/variation_table.dart';

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

// Limits get a two-level picker: category, then technique within it. Values
// follow the same "<question_type>:<variant>" encoding as _typeOptions.
// Mirrors web LIMIT_CATEGORIES / LIMIT_SUBTOPICS (practice/page.tsx).
const List<(String, String, String)> _limitCategories = [
  ('any', 'All limit categories', 'គ្រប់ជំពូកលីមីត'),
  ('rational', '1. Rational limits', '១. លីមីតសនិទាន'),
  ('radical', '2. Radical limits', '២. លីមីតរ៉ាឌីកាល់'),
  ('trig', '3. Trigonometric limits', '៣. លីមីតត្រីកោណមាត្រ'),
  ('exponential', '4. Exponential limits', '៤. លីមីតអិចស្ប៉ូណង់ស្យែល'),
  ('logarithmic', '5. Logarithmic limits', '៥. លីមីតលោការីត'),
  ('infinity', '6. Limits at infinity', '៦. លីមីតនៅអនន្ត'),
];

const Map<String, List<(String, String, String)>> _limitSubtopics = {
  'rational': [
    ('limit:rational', 'All rational limits', 'សនិទានទាំងអស់'),
    ('limit:rational:powers', '1. Algebraic identities (squares, cubes, powers)', '១. រូបមន្តស្វ័យគុណ (ការេ គូប ដឺក្រេខ្ពស់)'),
    ('limit:rational:quadratics', '2. Quadratic trinomials', '២. បំបែកត្រីធាដឺក្រេទីពីរ'),
    ('limit:rational:binomial', '3. Shifted binomials at 0', '៣. ពន្លាតទ្វេធាត្រង់ 0'),
  ],
  'radical': [
    ('limit:radical', 'All radical limits', 'រ៉ាឌីកាល់ទាំងអស់'),
    ('limit:radical:sqrt', '1. Square root conjugates', '១. កន្សោមឆ្លាស់ឬសការេ'),
    ('limit:radical:cbrt', '2. Cube root conjugates', '២. កន្សោមឆ្លាស់ឬសគូប'),
    ('limit:radical:double_and_split', '3. Double conjugate & split trick (advanced)', '៣. ឆ្លាស់ពីរជាន់ & ថែមថយតួ (កម្រិតខ្ពស់)'),
  ],
  'trig': [
    ('limit:trig', 'All trigonometric limits', 'ត្រីកោណមាត្រទាំងអស់'),
    ('limit:trig:sinc_standard', '1. Fundamental limit sin(kx)/x at 0', '១. លីមីតគ្រឹះ sin(kx)/x ត្រង់ 0'),
    ('limit:trig:change_var', '2. Change of variable at non-zero points', '២. ប្តូរអថេរត្រង់ π/2, π/3, π/4, π'),
    ('limit:trig:half_angle', '3. Half-angle & double-angle identities', '៣. រូបមន្តកន្លះមុំ និងមុំទ្វេ'),
    ('limit:trig:sum_product', '4. Sum-to-product & linear combinations', '៤. បំប្លែងផលបូកទៅផលគុណ (Simpson)'),
    ('limit:trig:radical_trig', '5. Radicals mixed with trigonometry', '៥. កន្សោមឆ្លាស់ឬសការេចម្រុះត្រីកោណមាត្រ'),
  ],
  'exponential': [
    ('limit:exponential', 'All exponential limits', 'អិចស្ប៉ូណង់ស្យែលទាំងអស់'),
    ('limit:exponential:zero', '1. Indeterminate form 0/0', '១. រាងមិនកំណត់ 0/0'),
    ('limit:exponential:trig_combo', '2. Mixed with trigonometry', '២. រាងចម្រុះត្រីកោណមាត្រ'),
    ('limit:exponential:one_inf', '3. Indeterminate form 1^∞', '៣. រាងមិនកំណត់ 1^អនន្ត'),
    ('limit:exponential:infinity', '4. Limits at infinity & growth dominance', '៤. លីមីតនៅអនន្ត និងលំដាប់កំណើន'),
  ],
  'logarithmic': [
    ('limit:logarithmic', 'All logarithmic limits', 'លោការីតទាំងអស់'),
    ('limit:logarithmic:zero', '1. Indeterminate form 0/0', '១. រាងមិនកំណត់ 0/0'),
    ('limit:logarithmic:rational', '2. Logarithm of rational function', '២. លោការីតនៃកន្សោមសនិទាន'),
    ('limit:logarithmic:growth_zero', '3. Growth dominance at 0⁺', '៣. លំដាប់កំណើនត្រង់ 0⁺ (x ln x)'),
    ('limit:logarithmic:infinity', '4. Limits at infinity & growth dominance', '៤. លីមីតនៅអនន្ត និងលំដាប់កំណើន'),
  ],
  'infinity': [
    ('limit:infinity', 'All limits at infinity', 'នៅអនន្តទាំងអស់'),
    ('limit:infinity:conjugate', '1. Conjugate at infinity (∞ - ∞)', '១. គុណកន្សោមឆ្លាស់នៅអនន្ត (រាង ∞ - ∞)'),
    ('limit:infinity:rational', '2. Rational function at infinity', '២. លីមីតអនុគមន៍សនិទាននៅអនន្ត'),
  ],
};

String _limitCategory(String qt) {
  if (qt.isEmpty || qt == 'any') return 'any';
  bool isOrUnder(String base) => qt == base || qt.startsWith('$base:');
  if (isOrUnder('limit:rational')) return 'rational';
  if (isOrUnder('limit:radical')) return 'radical';
  if (isOrUnder('limit:trig')) return 'trig';
  if (isOrUnder('limit:exponential') ||
      qt == 'limit:exp_log' ||
      qt.startsWith('limit:exp:') ||
      qt.startsWith('limit:euler:')) {
    return 'exponential';
  }
  if (isOrUnder('limit:logarithmic') || qt.startsWith('limit:log:')) return 'logarithmic';
  if (isOrUnder('limit:infinity')) return 'infinity';
  return 'any';
}

// The integral generator needs the template's question_type; limits (and
// every other topic) use the topic name (see web newQuestion).
String _templateQuestionType(String topic, String templateId) {
  if (topic == 'integral') {
    return templateId.startsWith('indefinite_') || templateId.startsWith('curated_')
        ? 'indefinite_integral'
        : 'definite_integral';
  }
  return topic;
}

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
  final String? initialSession;
  final String? initialTemplate;
  final String? initialDifficulty;

  const PracticeScreen({
    super.key,
    this.initialTopic,
    this.initialSkill,
    this.initialFormula,
    this.initialAttempt,
    this.initialSession,
    this.initialTemplate,
    this.initialDifficulty,
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

enum _AutoSaveStatus { idle, writing, saving, saved }

class _PracticeScreenState extends State<PracticeScreen> with WidgetsBindingObserver {
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
  HintResponse? _teacherHint;
  bool _hintMinimized = false;
  bool _hintLoading = false;

  // The LLM explanation is prepared in the background right after a wrong
  // answer (see _startExplain); the Explain button just awaits that request.
  // Requests are kept per "attemptId:lang" (in flight or resolved), so
  // returning to a part, or tapping again, never re-asks the server; a failed
  // request is dropped so the next tap retries it.
  final Map<String, Future<Explanation>> _explainRequests = {};
  bool _explaining = false;
  // Key of the explanation currently shown: hides the Explain button once it
  // is displayed, and brings it back if the UI language changes.
  String? _explainedKey;
  String? _explainViewKey; // the explanation the student is waiting for

  // Autosave (web: Google Docs-style status in the header).
  static const Duration _autoSaveDebounce = Duration(milliseconds: 1500);
  _AutoSaveStatus _autoSaveStatus = _AutoSaveStatus.idle;
  bool _dirty = false;
  Timer? _autoSaveTimer;
  Timer? _savedResetTimer;

  bool _busy = false;
  String? _error;
  int _streak = 0;
  int _soundToken = 0;

  List<SessionSummary> _sessions = [];
  bool _reviewMode = false;
  String? _practicingSkillKey;
  String? _practicingSkillLabel;
  String? _practicingFormulaName;
  String? _practicingTemplateId;

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
    if (_practicingSkillKey != null) return _practicingSkillKey;
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
    WidgetsBinding.instance.addObserver(this);
    if (widget.initialTopic != null && _topics.contains(widget.initialTopic)) {
      _topic = widget.initialTopic!;
    }
    _initStreak();
    if (widget.initialAttempt != null) {
      _loadReview(widget.initialAttempt!);
    } else if (widget.initialSession != null) {
      _loadSessions();
      _resumeSession(widget.initialSession!);
    } else if (widget.initialSkill != null) {
      _loadForcedSkill(widget.initialSkill!);
    } else if (widget.initialFormula != null) {
      _loadForcedFormula(widget.initialFormula!);
    } else if (widget.initialTemplate != null) {
      _loadForcedTemplate(widget.initialTemplate!);
    } else {
      _loadSessions();
      _newQuestion();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _autoSaveTimer?.cancel();
    _savedResetTimer?.cancel();
    final parts = _parts;
    // Leaving the page with unsaved ink: save it first, then free the canvases.
    if (_dirty) {
      _performAutoSave().whenComplete(() {
        for (final p in parts) {
          p.dispose();
        }
      });
    } else {
      for (final p in parts) {
        p.dispose();
      }
    }
    super.dispose();
  }

  // App backgrounded / closed (web: pagehide, blur, visibilitychange).
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed && _dirty) _performAutoSave();
  }

  // --- autosave ---
  void _markDirty() {
    if (_question == null || _reviewMode) return;
    _dirty = true;
    _savedResetTimer?.cancel();
    _autoSaveTimer?.cancel();
    _autoSaveTimer = Timer(_autoSaveDebounce, _performAutoSave);
    if (mounted && _autoSaveStatus != _AutoSaveStatus.writing) {
      setState(() => _autoSaveStatus = _AutoSaveStatus.writing);
    }
  }

  void _resetAutoSave() {
    _dirty = false;
    _autoSaveTimer?.cancel();
    _savedResetTimer?.cancel();
    _autoSaveStatus = _AutoSaveStatus.idle;
  }

  void _setAutoSaveStatus(_AutoSaveStatus s) {
    if (mounted) setState(() => _autoSaveStatus = s);
  }

  // Saves the active part's canvas + typed answer as in-progress work. Every
  // input is captured synchronously before the first await so a question or
  // part change mid-save can't mix two exercises.
  Future<void> _performAutoSave() async {
    final q = _question;
    final part = _active;
    if (q == null || part == null || !_dirty || _reviewMode) return;
    _autoSaveTimer?.cancel();
    _dirty = false;
    final partLabel = _currentPartLabel;
    final typed = part.typed.text.trim();
    final workText = part.workText;
    final boxes = part.detect?.linesBoxes;
    final strokes = part.canvas.getStrokes();
    _setAutoSaveStatus(_AutoSaveStatus.saving);
    try {
      final thumb = await part.canvas.getStrokesThumb();
      await _api.saveProgress(
        questionId: q.id,
        part: partLabel,
        typed: typed.isNotEmpty ? typed : null,
        workText: workText,
        linesBoxes: boxes,
        strokes: strokes,
        strokesThumb: thumb,
      );
      if (!mounted || _question?.id != q.id) return;
      if (_dirty) return; // new ink arrived while saving; its timer will save it
      _setAutoSaveStatus(_AutoSaveStatus.saved);
      _loadSessions();
      _savedResetTimer?.cancel();
      _savedResetTimer = Timer(const Duration(seconds: 3), () {
        if (_autoSaveStatus == _AutoSaveStatus.saved) {
          _setAutoSaveStatus(_AutoSaveStatus.idle);
        }
      });
    } catch (_) {
      // Keep the work flagged so the next change (or leaving) retries it.
      _dirty = true;
      _setAutoSaveStatus(_AutoSaveStatus.idle);
    }
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
    _clearExplainRequests();
    _graphGrade = null;
    _hintLevel = 0;
    _teacherHint = null;
    _hintMinimized = false;
    _showResults = true;
    _resetAutoSave();
  }

  // Switch the canvas to another sub-part (saving the current one first).
  void _setActivePart(int i) {
    if (_dirty) _performAutoSave();
    setState(() {
      _partIndex = i;
      _explanation = null;
      _resetExplain();
      _teacherHint = null;
      _error = null;
    });
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
      _practicingSkillKey = null;
      _practicingSkillLabel = null;
      _practicingFormulaName = null;
    });
    try {
      final tpl = _practicingTemplateId;
      final q = tpl != null
          ? await _api.generateProblem(
              generationMode: 'templates',
              difficulty: _difficulty,
              topic: _topic,
              questionType: _templateQuestionType(_topic, tpl),
              variant: tpl,
            )
          : await _generate();
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
      setState(() {
        _practicingSkillKey = skillKey;
        _practicingSkillLabel = skill?.label ?? _questionType.replaceAll('_', ' ');
      });
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

  // Forced template practice: /practice?template=<id> (from the admin
  // template cards / structure dialog). Generates a problem straight from
  // that template; "New question" keeps drawing from it until dismissed.
  Future<void> _loadForcedTemplate(String templateId) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final colon = templateId.indexOf(':');
      final topic = widget.initialTopic ??
          (colon != -1 ? templateId.substring(0, colon) : 'limit');
      _topic = _topics.contains(topic) ? topic : _topic;
      _difficulty = widget.initialDifficulty ?? 'medium';
      _mode = 'templates';
      final qType = _templateQuestionType(topic, templateId);
      _questionType = '$qType:$templateId';
      final q = await _api.generateProblem(
        generationMode: 'templates',
        difficulty: _difficulty,
        topic: topic,
        questionType: qType,
        variant: templateId,
      );
      _loadQuestion(q);
      setState(() => _practicingTemplateId = templateId);
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
      _resetExplain();
      // Keep the hint around but out of the way of the verdict.
      _hintMinimized = true;
      _graphGrade = null;
      _showResults = true;
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
      final partLabel = _currentPartLabel;
      final strokes = part.canvas.getStrokes();
      final strokesThumb = await part.canvas.getStrokesThumb();

      final res = await _api.grade(
        questionId: q.id,
        userAnswer: answer.isNotEmpty ? answer : 'written',
        workText: work,
        linesBoxes: finalDet.linesBoxes.isNotEmpty ? finalDet.linesBoxes : null,
        part: partLabel,
        hintsUsed: _hintLevel,
        strokes: strokes,
        strokesThumb: strokesThumb,
        lang: lang,
      );

      part.result = res;
      part.correct = res.correct;
      if (res.explanation != null) _explanation = res.explanation;
      // Grading is SymPy-only and already answered. Start the slow LLM
      // explanation now so it is (usually) ready when Explain is tapped.
      if (!res.correct && res.attemptId.isNotEmpty && mounted) {
        _startExplain(res.attemptId, answer, work, partLabel);
      }

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
  // Socratic hint: asks the backend for a contextual hint based on the
  // student's current canvas/typed work, rather than revealing the full
  // explanation one step at a time (see web commit 52f6835).
  Future<void> _showHint() async {
    final q = _question;
    final part = _active;
    if (q == null) return;
    setState(() {
      _hintLoading = true;
      _error = null;
    });
    try {
      var workText = part?.workText;
      final typedText = part?.typed.text.trim() ?? '';
      // Re-read the page each time so the hint sees the latest ink, not the
      // work from the last check.
      if (typedText.isEmpty) {
        try {
          final ink = await part?.canvas.getImageBase64();
          if (ink != null) {
            final det = await _api.detect(ink);
            if (det.lines.isNotEmpty) {
              part?.detect = det;
              workText = det.lines.join('\n');
              part?.workText = workText;
            }
          }
        } catch (_) {
          // best-effort ink detect; fall back to the last read work
        }
      }
      final lang = context.read<LanguageProvider>().currentLang;
      final res = await _api.hint(
        q.id,
        part: _currentPartLabel,
        workText: workText,
        userAnswer: typedText.isNotEmpty ? typedText : null,
        lang: lang,
      );
      if (mounted) {
        setState(() {
          _teacherHint = res;
          _hintMinimized = false;
          _hintLevel += 1;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) setState(() => _hintLoading = false);
    }
  }

  String _explainKey(String attemptId) =>
      '$attemptId:${context.read<LanguageProvider>().currentLang}';

  void _resetExplain() {
    _explainViewKey = null;
    _explaining = false;
    _explainedKey = null;
  }

  void _clearExplainRequests() {
    _explainRequests.clear();
    _resetExplain();
  }

  Future<Explanation>? _startExplain(
      String attemptId, String answer, String? work, String? part) {
    final q = _question;
    if (q == null) return null;
    final key = _explainKey(attemptId);
    final existing = _explainRequests[key];
    if (existing != null) return existing;
    final future = _api.explain(
      q.id,
      userAnswer: answer.isNotEmpty ? answer : null,
      workText: work,
      lang: context.read<LanguageProvider>().currentLang,
      attemptId: attemptId,
      part: part,
    );
    _explainRequests[key] = future;
    // A failed request must not be reused: drop it so the next tap retries.
    future.catchError((Object _) {
      if (identical(_explainRequests[key], future)) _explainRequests.remove(key);
      return Explanation(content: '', provider: '');
    });
    return future;
  }

  Future<void> _showExplanation() async {
    final part = _active;
    final res = part?.result;
    if (_question == null || part == null || res == null || res.attemptId.isEmpty) {
      return;
    }
    final key = _explainKey(res.attemptId);
    _explainViewKey = key;
    setState(() => _explaining = true);
    try {
      // Reuse the request started right after grading (or an earlier tap);
      // awaiting an already-finished request is instant.
      final future = _startExplain(res.attemptId, res.given ?? part.detect?.rawText ?? '',
          part.workText, res.part ?? _currentPartLabel);
      if (future == null) return;
      final exp = await future;
      if (!mounted || _explainViewKey != key) return; // stale: part/check changed
      setState(() {
        // The tutor tip lives on the result card (with the official part
        // solution); keep it out of the explanation card so it isn't shown twice.
        part.result = res.withTutorFeedback(
          teacherFeedback: exp.teacherFeedback,
          officialPartSolution: exp.officialPartSolution,
        );
        _explanation = exp.withoutTeacherFeedback();
        _explainedKey = key;
      });
    } catch (e) {
      if (mounted && _explainViewKey == key) {
        setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted && _explainViewKey == key) setState(() => _explaining = false);
    }
  }

  // --- save / resume ---
  // The status chip in the header opens the saved-exercises page, flushing
  // any pending autosave first (web: "Saved" link to /saved).
  Future<void> _openSaved() async {
    if (_dirty) await _performAutoSave();
    if (mounted) context.go('/saved');
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
      // Phone photos can be several thousand px a side; OCR gains nothing past
      // ~1600px, so downscale on pick (web resizeImage / MAX_UPLOAD_DIM).
      final files = await picker.pickMultiImage(
          maxWidth: 1600, maxHeight: 1600, imageQuality: 92);
      if (files.isEmpty) return;
      // Each photo lands as its own movable/resizable image (cascaded).
      for (final file in files) {
        await part.canvas.loadImageStroke(await file.readAsBytes());
      }
      if (mounted) setState(() {});
      _markDirty();
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
                    if (_topic == 'limit') ...[
                      _limitCategoryDropdown(lang),
                      const SizedBox(width: 8),
                    ],
                    _typeDropdown(lang),
                    const SizedBox(width: 8),
                    _difficultyDropdown(lang),
                    if (_topic == 'complex') ...[
                      const SizedBox(width: 8),
                      _modeDropdown(lang),
                    ],
                    const SizedBox(width: 8),
                  ],
                  if (_practicingTemplateId != null)
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: _templateChip(lang),
                    ),
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
                  if (q != null && !_reviewMode) _autoSaveIndicator(lang),
                  IconButton(
                    tooltip: lang.t('tip_settings'),
                    visualDensity: VisualDensity.compact,
                    icon: const Icon(Icons.settings_outlined, size: 18),
                    onPressed: _showSettingsSheet,
                  ),
                  const SizedBox(width: 4),
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

  Widget _limitCategoryDropdown(LanguageProvider lang) => _dropdown<String>(
        value: _limitCategory(_questionType),
        items: [
          for (final c in _limitCategories) (c.$1, lang.isKhmer ? c.$3 : c.$2),
        ],
        onChanged: (cat) =>
            setState(() => _questionType = cat == 'any' ? 'any' : 'limit:$cat'),
      );

  Widget _typeDropdown(LanguageProvider lang) {
    if (_topic == 'limit') {
      final cat = _limitCategory(_questionType);
      return _dropdown<String>(
        value: _questionType,
        items: cat == 'any'
            ? [('any', lang.isKhmer ? 'គ្រប់វិធីសាស្ត្រទាំងអស់' : 'All techniques')]
            : [
                for (final sub in _limitSubtopics[cat] ?? const <(String, String, String)>[])
                  (sub.$1, lang.isKhmer ? sub.$3 : sub.$2),
              ],
        onChanged: (v) => setState(() => _questionType = v),
      );
    }
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

  Widget _templateChip(LanguageProvider lang) {
    return Container(
      padding: const EdgeInsets.only(left: 8),
      decoration: BoxDecoration(
        color: const Color(0xFFFFFBEB),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: const Color(0xFFFCD34D)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.edit_outlined, size: 14, color: Color(0xFFB45309)),
          const SizedBox(width: 4),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 160),
            child: Text(_practicingTemplateId!,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                    fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF78350F))),
          ),
          IconButton(
            tooltip: lang.isKhmer ? 'ចាកចេញពីការអនុវត្តគំរូនេះ' : 'Exit template practice',
            visualDensity: VisualDensity.compact,
            icon: const Icon(Icons.close, size: 14, color: Color(0xFFD97706)),
            // Back to the normal pickers (the forced "<type>:<template>" value
            // would otherwise keep generating the same template).
            onPressed: () => setState(() {
              _practicingTemplateId = null;
              _questionType = 'any';
            }),
          ),
        ],
      ),
    );
  }

  Widget _autoSaveIndicator(LanguageProvider lang) {
    Widget label(Widget icon, String text, Color color) => Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            icon,
            const SizedBox(width: 4),
            Text(text, style: TextStyle(fontSize: 12, color: color)),
          ],
        );
    final Widget body;
    switch (_autoSaveStatus) {
      case _AutoSaveStatus.saving:
        body = label(
            const SizedBox(
                width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2)),
            lang.t('autosave_saving'),
            AppTheme.slate600);
      case _AutoSaveStatus.writing:
        body = label(
            Container(
              width: 8,
              height: 8,
              decoration: const BoxDecoration(color: Color(0xFFF59E0B), shape: BoxShape.circle),
            ),
            lang.t('autosave_writing'),
            const Color(0xFFD97706));
      default:
        body = label(const Icon(Icons.cloud_done_outlined, size: 16, color: AppTheme.slate600),
            lang.isKhmer ? 'បានរក្សាទុក' : 'Saved', AppTheme.slate600);
    }
    return Tooltip(
      message: lang.isKhmer
          ? 'បានរក្សាទុក (ចុចដើម្បីមើលលំហាត់ដែលបានរក្សាទុក)'
          : 'All changes saved (tap to view saved exercises)',
      child: InkWell(
        onTap: _openSaved,
        borderRadius: BorderRadius.circular(6),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 6),
          child: body,
        ),
      ),
    );
  }

  // Canvas & audio settings (web: the ⚙️ popover on the practice page).
  void _showSettingsSheet() {
    final lang = context.read<LanguageProvider>();
    showModalBottomSheet(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheet) => SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('⚙️ Canvas Settings',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                const SizedBox(height: 8),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(lang.t('set_friction_audio'), style: const TextStyle(fontSize: 13)),
                  value: drawingAudio.enabled,
                  onChanged: (_) => setSheet(drawingAudio.toggle),
                ),
                Row(
                  children: [
                    Icon(
                        !drawingAudio.enabled || drawingAudio.volume == 0
                            ? Icons.volume_off
                            : Icons.volume_up,
                        size: 18,
                        color: AppTheme.slate600),
                    Expanded(
                      child: Slider(
                        value: drawingAudio.volume,
                        onChanged: (v) => setSheet(() => drawingAudio.setVolume(v)),
                      ),
                    ),
                    Text('${(drawingAudio.volume * 100).round()}%',
                        style: const TextStyle(fontSize: 12)),
                  ],
                ),
                OutlinedButton(
                  onPressed: drawingAudio.playSuccessChime,
                  child: const Text('🔔 Test Chime', style: TextStyle(fontSize: 12)),
                ),
              ],
            ),
          ),
        ),
      ),
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
          // A value set by a forced skill/formula/template or a resumed
          // exercise may not be one of the options; show it rather than crash.
          if (!items.any((it) => it.$1 == value))
            DropdownMenuItem(
                value: value,
                child: Text(value is String
                    ? (_practicingTemplateId ??
                        questionTypeLabel(value,
                            context.read<LanguageProvider>().currentLang))
                    : '$value')),
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
              Semantics(
                button: true,
                selected: i == _partIndex,
                child: GestureDetector(
                onTap: _busy ? null : () => _setActivePart(i),
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
            onChange: _markDirty,
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
        // Teacher (Socratic) hint above the results panel, stacked in one
        // right-hand column (web: the fixed right-side panel).
        if (_teacherHint != null || (part.result != null && _showResults))
          Positioned(
            right: 6,
            bottom: 70,
            width: MediaQuery.of(context).size.width < 520
                ? MediaQuery.of(context).size.width - 12
                : 360,
            child: ConstrainedBox(
              constraints:
                  BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.62),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (_teacherHint != null)
                    Flexible(
                      flex: _hintMinimized ? 0 : 2,
                      child: SingleChildScrollView(
                          child: _teacherHintPanel(lang, _teacherHint!)),
                    ),
                  if (_teacherHint != null && part.result != null && _showResults)
                    const SizedBox(height: 8),
                  if (part.result != null && _showResults)
                    Flexible(flex: 5, child: _resultsPanel(lang, part)),
                ],
              ),
            ),
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
                    _iconBtn(
                        Icons.undo,
                        c.canUndo
                            ? () {
                                setState(c.undo);
                                _markDirty();
                              }
                            : null,
                        tooltip: lang.t('btn_undo')),
                    _iconBtn(
                        Icons.redo,
                        c.canRedo
                            ? () {
                                setState(c.redo);
                                _markDirty();
                              }
                            : null,
                        tooltip: lang.t('btn_redo')),
                  ],
                ),
              ),
              _iconBtn(Icons.delete_outline, () {
                setState(() {
                  c.clear();
                  part.detect = null;
                  part.workText = null;
                  part.result = null;
                });
                _markDirty();
              }, tooltip: lang.t('btn_clear')),
              _tinyBtn(
                  _hintLoading
                      ? (lang.isKhmer ? 'កំពុងទាញយក...' : 'Loading hint...')
                      : (_explanation != null &&
                              _explanation!.steps.isNotEmpty &&
                              _hintLevel >= _explanation!.steps.length)
                          ? lang.t('tool_all_hints')
                          : lang.t('tool_hint'),
                  onTap: _busy || _hintLoading || _question == null
                      ? null
                      : _showHint),
              _iconBtn(Icons.upload_outlined, _uploadImage, tooltip: lang.t('tool_upload')),
              _iconBtn(Icons.remove, () => setState(() => c.setZoom(c.zoom - 0.2)),
                  tooltip: lang.t('tip_zoom_out')),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 2),
                child: Text('${(c.zoom * 100).round()}%',
                    style: const TextStyle(fontSize: 11)),
              ),
              _iconBtn(Icons.add, () => setState(() => c.setZoom(c.zoom + 0.2)),
                  tooltip: lang.t('tip_zoom_in')),
              SizedBox(
                width: 110,
                child: TextField(
                  controller: part.typed,
                  onChanged: (_) => _markDirty(),
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

  Widget _iconBtn(IconData icon, VoidCallback? onTap, {String? tooltip}) {
    return IconButton(
      onPressed: onTap,
      tooltip: tooltip,
      icon: Icon(icon, size: 18),
      visualDensity: VisualDensity.compact,
      constraints: const BoxConstraints(minWidth: 34, minHeight: 34),
      padding: EdgeInsets.zero,
    );
  }

  Widget _teacherHintPanel(LanguageProvider lang, HintResponse hint) {
    if (_hintMinimized) {
      return Align(
        alignment: Alignment.centerRight,
        child: Material(
          elevation: 3,
          borderRadius: BorderRadius.circular(12),
          color: const Color(0xFFFFFBEB),
          child: InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: () => setState(() => _hintMinimized = false),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFFCD34D)),
              ),
              child: Text(
                '👨‍🏫 ${lang.isKhmer ? 'ជំនួយពីគ្រូ' : 'Teacher Hint'}  ▲',
                style: const TextStyle(
                    fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF78350F)),
              ),
            ),
          ),
        ),
      );
    }
    return Material(
      elevation: 4,
      borderRadius: BorderRadius.circular(12),
      color: const Color(0xFFFFFBEB),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0xFFFCD34D)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Text('👨‍🏫', style: TextStyle(fontSize: 15)),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    lang.isKhmer ? 'ជំនួយពីគ្រូ (Teacher Hint)' : 'Teacher Hint',
                    style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                        color: Color(0xFF78350F)),
                  ),
                ),
                if (hint.errorLine != null)
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    margin: const EdgeInsets.only(right: 4),
                    decoration: BoxDecoration(
                        color: Colors.red.shade100,
                        borderRadius: BorderRadius.circular(4)),
                    child: Text(
                        lang.isKhmer
                            ? 'កំហុសនៅបន្ទាត់ទី ${hint.errorLine}'
                            : 'Line ${hint.errorLine} error',
                        style: TextStyle(
                            fontSize: 10, color: Colors.red.shade700)),
                  ),
                IconButton(
                  tooltip: lang.isKhmer ? 'បង្រួម' : 'Minimize',
                  icon: const Icon(Icons.keyboard_arrow_down, size: 16),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
                  onPressed: () => setState(() => _hintMinimized = true),
                ),
                IconButton(
                  icon: const Icon(Icons.close, size: 14),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
                  onPressed: () => setState(() => _teacherHint = null),
                ),
              ],
            ),
            const Divider(height: 12, color: Color(0xFFFCD34D)),
            MathText(text: hint.hint),
          ],
        ),
      ),
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
                ...res.parts.map((pv) => _partVerdict(lang, pv))
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
              if (_offerExplain(res))
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: OutlinedButton(
                    onPressed: _explaining ? null : _showExplanation,
                    style: OutlinedButton.styleFrom(
                      backgroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      visualDensity: VisualDensity.compact,
                    ),
                    child: Text(
                        _explaining ? lang.t('label_explaining') : lang.t('btn_explain'),
                        style: const TextStyle(fontSize: 12)),
                  ),
                ),
              if (res.rubricScore != null) _rubricWidget(lang, res),
              if (res.teacherFeedback?.content.isNotEmpty ?? false)
                _teacherTip(lang, res.teacherFeedback!.content, res.officialPartSolution),
              if (_fumbledFormula(res) != null)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      visualDensity: VisualDensity.compact,
                    ),
                    onPressed: () => context
                        .go('/practice?formula=${Uri.encodeQueryComponent(_fumbledFormula(res)!)}'),
                    child: Text(
                        '${lang.t('formulas_practice')}: ${_fumbledFormula(res)!.replaceAll('_', ' ')}',
                        style: const TextStyle(fontSize: 12)),
                  ),
                ),
              if (res.variationTable != null) ...[
                const Divider(),
                VariationTableView(vt: res.variationTable!),
              ],
              if (res.graph != null) ...[
                const Divider(),
                Text(lang.t('label_ref_graph_compare'),
                    style: const TextStyle(
                        fontSize: 11, color: AppTheme.slate600)),
                FunctionGraph(graph: res.graph!),
                if (res.graphCheck != null) _graphCheckWidget(lang, res.graphCheck!, showNote: true),
                if (_graphGrade != null && _graphGrade!.error == null)
                  _graphAssessment(lang, _graphGrade!),
                if (_graphGrade?.error == 'rate_limited')
                  const Padding(
                    padding: EdgeInsets.only(top: 6),
                    child: Text('Graph assessment unavailable (rate limited).',
                        style: TextStyle(fontSize: 11, color: AppTheme.slate600)),
                  ),
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

  // Explain is offered for a wrong answer, any functions part (restores the
  // tutor tip), and a correct answer that lost rubric points — and hidden
  // once that explanation is on screen (web practice page).
  bool _offerExplain(GradeResult res) {
    if (res.attemptId.isEmpty) return false;
    final r = res.rubricScore;
    final worthIt = !res.correct ||
        _question?.topic == 'functions' ||
        (r != null && r.earned < r.possible);
    if (!worthIt) return false;
    if (_explainedKey == _explainKey(res.attemptId)) return false;
    // A saved LLM explanation (e.g. from review) is already showing.
    if (_explainedKey == null &&
        _explanation != null &&
        _explanation!.provider != 'deterministic') {
      return false;
    }
    return true;
  }

  // The formula the student fumbled on their first wrong line, if the step
  // checker identified one — offered as a one-tap formula drill.
  String? _fumbledFormula(GradeResult res) {
    final check = res.stepCheck;
    if (res.correct || check == null || check.firstErrorLine == null) return null;
    final f = _firstOrNull(check.lineResults, (l) => l.line == check.firstErrorLine)?.formula;
    return (f != null && f.isNotEmpty) ? f : null;
  }

  Widget _partVerdict(LanguageProvider lang, PartVerdict pv) {
    final given = pv.given;
    final detail = [
      if (given != null && given.isNotEmpty) '${lang.t('verdict_you')}: $given',
      if (!pv.correct) '${lang.t('verdict_expected')} ${pv.expected ?? ''}',
      if (!pv.correct && (given == null || given.isEmpty)) lang.t('verdict_unanswered'),
    ].join(' · ');
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: 6),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: pv.correct
            ? AppTheme.successGreen.withValues(alpha: 0.15)
            : AppTheme.errorRed.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
              '${pv.correct ? "✓" : "✗"} ${pv.label} · ${pv.correct ? lang.t('verdict_correct') : lang.t('verdict_needs_revision')}',
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
          if (detail.isNotEmpty) Text(detail, style: const TextStyle(fontSize: 11)),
          if (pv.note != null && pv.note!.isNotEmpty)
            Text(pv.note!,
                style: const TextStyle(fontSize: 11, color: Color(0xFF065F46))),
        ],
      ),
    );
  }

  Widget _graphCheckWidget(LanguageProvider lang, GraphCheck gc, {bool showNote = false}) {
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('${lang.t('label_ref_graph')}:',
              style: const TextStyle(fontSize: 11, color: AppTheme.slate600)),
          Wrap(
            spacing: 8,
            children: [
              for (final it in gc.items)
                Text('${it.label} ${it.found ? "✓" : "·"}',
                    style: TextStyle(
                        fontSize: 11,
                        fontWeight: it.found ? FontWeight.w600 : FontWeight.normal,
                        color: it.found ? const Color(0xFF047857) : AppTheme.slate600)),
            ],
          ),
          if (showNote && gc.found < gc.total)
            Text(lang.t('label_missing_labels_note'),
                style: const TextStyle(fontSize: 11, color: AppTheme.slate600)),
        ],
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

  Widget _teacherTip(LanguageProvider lang, String content, [String? officialSolution]) {
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
          if (officialSolution != null && officialSolution.isNotEmpty) ...[
            const Divider(height: 14, color: Color(0xFFFCD34D)),
            Theme(
              data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
              child: ExpansionTile(
                tilePadding: EdgeInsets.zero,
                childrenPadding: EdgeInsets.zero,
                dense: true,
                visualDensity: VisualDensity.compact,
                title: Text('📋 ${lang.t('label_official_moeys_key')}',
                    style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: Colors.amber.shade900)),
                children: [
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.9),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFFFDE68A)),
                    ),
                    child: MathText(
                        text: officialSolution, textStyle: const TextStyle(fontSize: 12)),
                  ),
                ],
              ),
            ),
          ],
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
                  style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: (gg.score ?? 0) >= 80
                          ? const Color(0xFF047857)
                          : (gg.score ?? 0) >= 60
                              ? const Color(0xFFD97706)
                              : AppTheme.errorRed)),
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
          for (final sug in gg.suggestions)
            Text('• $sug', style: const TextStyle(fontSize: 11, color: AppTheme.slate600)),
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
              final formulaName = isError
                  ? (lineRes?.formulaName ?? lineRes?.formula?.replaceAll('_', ' '))
                  : null;
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
    const sectionLabel = TextStyle(
        fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.slate600);
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
          // The full narration when there is one; otherwise the steps (so
          // the solution is never shown twice).
          if (exp.content.isNotEmpty) ...[
            Text(lang.t('label_solution'), style: sectionLabel),
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: MathText(text: exp.content, textStyle: const TextStyle(fontSize: 12)),
            ),
          ] else if (steps.isNotEmpty) ...[
            Text(lang.t('label_solution'), style: sectionLabel),
            for (final s in steps.take(showCount))
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: MathText(
                    text: s.title.isNotEmpty
                        ? '${lang.t('label_step')} ${s.stepOrder}: ${s.detail}'
                        : s.detail,
                    textStyle: const TextStyle(fontSize: 12)),
              ),
          ],
          if (exp.teacherFeedback?.content.isNotEmpty ?? false)
            _teacherTip(lang, exp.teacherFeedback!.content),
          if (exp.workCheck?.content.isNotEmpty ?? false) ...[
            const Divider(),
            Text(lang.t('label_work_check'), style: sectionLabel),
            MathText(text: exp.workCheck!.content, textStyle: const TextStyle(fontSize: 12)),
          ],
          if (exp.variationTable != null) ...[
            const Divider(),
            VariationTableView(vt: exp.variationTable!),
          ],
          if (exp.graph != null) ...[
            const Divider(),
            Text(lang.t('label_ref_graph'), style: sectionLabel),
            FunctionGraph(graph: exp.graph!),
            if (exp.graphCheck != null) _graphCheckWidget(lang, exp.graphCheck!),
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
