import 'package:bacii_mobile/core/i18n/language_provider.dart';
import 'package:bacii_mobile/models/grade_result.dart';
import 'package:bacii_mobile/models/profile.dart';
import 'package:bacii_mobile/models/session.dart';
import 'package:bacii_mobile/models/template.dart';
import 'package:bacii_mobile/models/variation_table.dart';
import 'package:bacii_mobile/widgets/math_text.dart';
import 'package:bacii_mobile/widgets/saved_exercises_shelf.dart';
import 'package:bacii_mobile/widgets/structure_dialog.dart';
import 'package:bacii_mobile/widgets/variation_table.dart';
import 'package:flutter/material.dart';
import 'package:flutter_math_fork/flutter_math.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

Widget _wrap(Widget child) => ChangeNotifierProvider(
      create: (_) => LanguageProvider(),
      child: MaterialApp(home: Scaffold(body: SingleChildScrollView(child: child))),
    );

final _vtJson = {
  'columns': ['-oo', '-1', '1', '+oo'],
  'derivative_sign': ['+', '-', '+'],
  'arrows': ['↗', '↘', '↗'],
  'func_values': ['-oo', '2', '-2', '+oo'],
};

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({'bacii_lang': 'en'}));

  group('grade/explain models', () {
    test('GradeResult reads variation table + official part solution', () {
      final r = GradeResult.fromJson({
        'attempt_id': 'a1',
        'correct': false,
        'reason': 'mismatch',
        'expected': '-2',
        'variation_table': _vtJson,
        'official_part_solution': 'ដូចនេះ f(1) = -2',
        'step_check': {
          'line_results': [
            {'line': 1, 'text': 'x', 'checked': true, 'correct': false, 'formula': 'chain_rule', 'formula_name': 'Chain rule'}
          ],
          'first_error_line': 1,
        },
      });
      expect(r.variationTable!.columns, ['-oo', '-1', '1', '+oo']);
      expect(r.officialPartSolution, startsWith('ដូចនេះ'));
      expect(r.stepCheck!.lineResults.first.formulaName, 'Chain rule');
    });

    test('tutor feedback from /explain moves onto the result card', () {
      final r = GradeResult(attemptId: 'a1', correct: false, reason: 'x', variationTable: VariationTable.fromJson(_vtJson));
      final exp = Explanation.fromJson({
        'content': 'narration',
        'provider': 'gemini',
        'teacher_feedback': {'content': 'tip', 'provider': 'gemini'},
        'official_part_solution': 'official',
      });
      final merged = r.withTutorFeedback(
          teacherFeedback: exp.teacherFeedback, officialPartSolution: exp.officialPartSolution);
      expect(merged.teacherFeedback!.content, 'tip');
      expect(merged.officialPartSolution, 'official');
      expect(merged.variationTable, isNotNull); // untouched fields survive
      final shown = exp.withoutTeacherFeedback();
      expect(shown.teacherFeedback, isNull);
      expect(shown.content, 'narration');
    });

    test('profile tolerates fractional numbers (days_idle, priority)', () {
      // Shapes from a real account: days since last practice and the
      // suggestion ranking score are floats on the backend.
      final p = Profile.fromJson({
        'user': {'id': 'u', 'email': 'e', 'plan': 'free'},
        'level': {'score': 12.5, 'attempts': 30, 'topics_started': 2},
        'skills': [
          {'key': 'limit/limit', 'label': 'Limit', 'level': 4.2, 'attempts': 3, 'correct': 0, 'days_idle': 11.3}
        ],
        'formulas': [
          {'formula': 'f', 'name': 'F', 'level': 20.0, 'attempts': 2, 'correct': 1, 'days_idle': 11.3}
        ],
        'suggestions': [
          {'kind': 'weak_skill', 'priority': 75.255, 'title': 't', 'reason': 'r', 'level': 4.3}
        ],
        'topics': [],
        'activity': [],
      });
      expect(p.skills.single.daysIdle, 11);
      expect(p.formulas.single.daysIdle, 11);
      expect(p.suggestions.single.priority, closeTo(75.255, 1e-9));
    });

    test('malformed variation table is ignored', () {
      expect(VariationTable.fromJson(null), isNull);
      expect(VariationTable.fromJson({'columns': ['x']}), isNull);
    });

    test('template structure parses variants, params and KM solution', () {
      final st = TemplateStructure.fromJson({
        'id': 'limit:rational:diff_squares_linear',
        'question_type': 'limit',
        'difficulty': 'easy',
        'pattern': 'x',
        'sample_prompt': 'p',
        'sample_answer': '1',
        'sample_params': {'a': 5, 'expr': 'x'},
        'variants': [
          {'variant_index': 1, 'params': {'a': 5}, 'answer_latex': '10', 'steps': [{'title': '', 'detail': 'd'}]},
        ],
        'solution_km_json': {
          'parts': [
            {'label': '1.a', 'steps': [{'khmer': 'k', 'latex': 'l'}], 'answer_khmer': 'ak', 'answer_latex': 'al'}
          ]
        },
        'parts': [
          {'label': '1.a', 'answer': '1', 'sign_table': {'cols': ['-oo', '0', '+oo'], 'rows': [{'label': 'f', 'cols': [{'val': '-'}, {'val': '0'}, {'val': '+'}]}]}}
        ],
      });
      expect(st.variants.single.steps.single.detail, 'd');
      expect(st.sampleParams!['a'], 5);
      expect(st.solutionKmParts.single.steps.single.$1, 'k');
      expect(st.parts.single.signTable!.values, ['-', '0', '+']);
    });
  });

  testWidgets('VariationTableView renders values and signs', (tester) async {
    await tester.pumpWidget(_wrap(VariationTableView(vt: VariationTable.fromJson(_vtJson)!)));
    await tester.pumpAndSettle();
    expect(find.text("f'(x)"), findsOneWidget);
    expect(find.text('+'), findsNWidgets(2));
    expect(find.text('-'), findsOneWidget);
    expect(find.text('0'), findsNWidgets(2)); // zeros of f' at the two extrema
    expect(tester.takeException(), isNull);
  });

  testWidgets('VariationTableView draws a pole as a double bar', (tester) async {
    final vt = VariationTable.fromJson({
      'columns': ['-oo', '2', '+oo'],
      'derivative_sign': ['-', '-'],
      'arrows': ['↘', '↘'],
      'func_values': ['0', '-oo/+oo', '0'],
    })!;
    await tester.pumpWidget(_wrap(VariationTableView(vt: vt)));
    await tester.pumpAndSettle();
    expect(find.text('0'), findsNothing); // no zero marker at a pole
    expect(tester.takeException(), isNull);
  });

  testWidgets('MathText keeps Khmer \\text{} out of TeX', (tester) async {
    await tester.pumpWidget(_wrap(const MathText(
        text: r'\(\lim_{x\to 2} \frac{x^2-4}{x-2} \left(\text{រាងមិនកំណត់ } \frac{0}{0}\right)\)')));
    await tester.pumpAndSettle();
    expect(find.text('រាងមិនកំណត់'), findsOneWidget);
    final texs = tester.widgetList<Math>(find.byType(Math)).toList();
    expect(texs, hasLength(2));
    for (final m in texs) {
      expect(m.parseError, isNull);
    }
    expect(tester.takeException(), isNull);
  });

  testWidgets('MathText turns top-level \\\\ into line breaks', (tester) async {
    await tester.pumpWidget(_wrap(const MathText(text: r'$f(x) = x^2 \\ (O, \vec{i}, \vec{j}) .\\$')));
    await tester.pumpAndSettle();
    final texs = tester.widgetList<Math>(find.byType(Math)).toList();
    expect(texs, hasLength(2));
    for (final m in texs) {
      expect(m.parseError, isNull);
    }
    // ...but not inside an environment, where \\ is a row separator.
    await tester.pumpWidget(_wrap(const MathText(
        text: r'$f(x) = \begin{cases} x & x > 0 \\ 0 & x \le 0 \end{cases}$')));
    await tester.pumpAndSettle();
    expect(find.byType(Math), findsOneWidget);
    expect(tester.widget<Math>(find.byType(Math)).parseError, isNull);
  });

  testWidgets('MathText renders a real multi-line Khmer exam prompt without TeX errors',
      (tester) async {
    // Verbatim functions prompt_latex from the backend (control spaces,
    // \\ line breaks, Khmer \text{} runs, \left( \right)).
    const prompt = r'\text{គេមានអនុគមន៍ } g \text{ ដែល } g(x)=\ln\left(\frac{-x-3}{x-3}\right) .\\ '
        r'\text{1. រកដែនកំណត់នៃអនុគមន៍ } g \text{ និងសិក្សាថាតើ } g \text{ ជាអនុគមន៍គូ ឬសេស?}\\ '
        r'\text{4. } (a)\ \text{គណនាដេរីវេនៃអនុគមន៍ } h \text{ ដែល } h(x)=x\,g(x) .\quad (b)\ '
        r'\text{រកផ្ទៃក្រឡានៃផ្នែកប្លង់នៅចន្លោះក្រាប } C \text{ អ័ក្ស } x \text{ និងបន្ទាត់ } x=0,\ x=1 .';
    await tester.pumpWidget(_wrap(const MathText(text: '\$$prompt\$')));
    await tester.pumpAndSettle();
    final texs = tester.widgetList<Math>(find.byType(Math)).toList();
    expect(texs, isNotEmpty);
    for (final m in texs) {
      expect(m.parseError, isNull, reason: '${m.parseError}');
    }
    expect(find.textContaining(r'$'), findsNothing); // no raw-TeX fallback
    expect(find.text('គណនាដេរីវេនៃអនុគមន៍'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('MathText leaves Latin \\text{} inside TeX', (tester) async {
    await tester.pumpWidget(_wrap(const MathText(text: r'\(x = 2 \text{ or } x = 3\)')));
    await tester.pumpAndSettle();
    expect(find.byType(Math), findsOneWidget);
  });

  testWidgets('StructureDialog shows variants, parameters and solution', (tester) async {
    tester.view.physicalSize = const Size(1200, 1600);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final st = TemplateStructure.fromJson({
      'id': 'derivatives:chain_power',
      'question_type': 'compute_derivative',
      'difficulty': 'medium',
      'pattern': 'f(x) = (ax+b)^n',
      'sample_prompt': 'f(x)',
      'sample_answer': 'x',
      'variants': [
        {'variant_index': 1, 'params': {'a': 2, 'n': 3}, 'answer_latex': '6(2x+1)^2', 'steps': [{'title': 'Chain rule', 'detail': 'u = 2x+1', 'formula': 'chain_rule'}]},
        {'variant_index': 2, 'params': {'a': 3, 'n': 3}, 'answer_latex': '9(3x+1)^2', 'steps': []},
      ],
      'formula_tags': ['chain_rule'],
    });
    await tester.pumpWidget(ChangeNotifierProvider(
      create: (_) => LanguageProvider(),
      child: MaterialApp(home: Scaffold(body: StructureDialog(structure: st, topic: 'derivatives'))),
    ));
    await tester.pumpAndSettle();
    expect(find.text('Variant 1 (a = 2, n = 3)'), findsOneWidget);
    expect(find.text('a:'), findsOneWidget);
    expect(find.text('Practice'), findsOneWidget);
    expect(find.text('Formula tags:'), findsOneWidget);
    // Selecting a preset variant switches the solution.
    await tester.tap(find.text('Variant 2 (a = 3, n = 3)'));
    await tester.pumpAndSettle();
    expect(find.text('Formula: '), findsNothing); // variant 2 has no steps
    expect(tester.takeException(), isNull);
  });

  testWidgets('SavedExercisesShelf lists sessions with resume + progress', (tester) async {
    final s = SessionSummary.fromJson({
      'id': 's1',
      'question_id': 'q1',
      'status': 'in_progress',
      'parts_done': 1,
      'parts_total': 4,
      'updated_at': DateTime.now().toUtc().subtract(const Duration(minutes: 5)).toIso8601String(),
      'question': {'id': 'q1', 'topic': 'functions', 'question_type': 'study', 'difficulty': 'hard', 'prompt': 'Study f'},
    });
    String? deleted;
    await tester.pumpWidget(_wrap(SavedExercisesShelf(sessions: [s], onDelete: (id) => deleted = id)));
    await tester.pumpAndSettle();
    expect(find.text('1/4 parts done'), findsOneWidget);
    expect(find.text('25%'), findsOneWidget);
    expect(find.text('5m ago'), findsOneWidget);
    expect(find.text('Resume'), findsOneWidget);
    await tester.tap(find.byIcon(Icons.close));
    expect(deleted, 's1');
  });
}
