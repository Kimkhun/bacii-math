export type Language = "en" | "km";

export interface Translations {
  // Navigation
  nav_profile: string;
  nav_practice: string;
  nav_exam: string;
  nav_history: string;
  nav_stats: string;
  nav_formulas: string;
  nav_admin: string;
  nav_logout: string;
  nav_login: string;
  nav_signup: string;
  language: string;

  // Topics
  topic_complex: string;
  topic_limit: string;
  topic_integral: string;
  topic_probability: string;
  topic_functions: string;
  topic_continuity: string;
  topic_derivatives: string;
  topic_differential_equations: string;
  topic_vectors_space: string;
  topic_conics: string;

  // Difficulties
  diff_easy: string;
  diff_medium: string;
  diff_hard: string;

  // Modes
  mode_templates: string;
  mode_gemini: string;

  // Common buttons & actions
  btn_new_question: string;
  btn_generating: string;
  btn_check_answer: string;
  btn_checking: string;
  btn_hint: string;
  btn_clear: string;
  btn_undo: string;
  btn_redo: string;
  btn_fullscreen: string;
  btn_exit_fullscreen: string;
  btn_show_steps: string;
  btn_hide_steps: string;
  btn_saved: string;
  btn_review_mode: string;
  btn_back_to_practice: string;
  btn_start_practicing: string;
  btn_start_exam: string;
  btn_submit_exam: string;
  btn_create_account: string;
  btn_practice_this: string;

  // Practice Page Headings & Notices
  prompt_select_guide: string;
  tab_substep: string;
  label_solution: string;
  label_your_work: string;
  label_work_check: string;
  label_ref_graph: string;
  label_ref_graph_compare: string;
  label_step: string;
  label_part: string;
  label_step_score: string;
  label_teacher_tip: string;
  label_practice_formula: string;
  label_expected: string;
  label_reason: string;
  label_consecutive_correct: string;
  label_disambiguation_title: string;

  // Grader Verdicts & Reasons
  verdict_correct: string;
  verdict_needs_revision: string;
  verdict_you: string;
  verdict_expected: string;
  verdict_unanswered: string;
  reason_exact: string;
  reason_numeric: string;
  reason_mismatch: string;
  reason_unparsed: string;
  reason_given: string;
  reason_identity: string;
  reason_unanswered: string;
  mark_verified_ok: string;
  mark_could_not_verify: string;

  // Formulas Page
  formulas_title: string;
  formulas_subtitle: string;
  formulas_all_topics: string;
  formulas_weight: string;
  formulas_practice: string;
  formulas_loading: string;
  lesson: string;
  lesson_loading: string;
  lesson_worked_examples: string;
  lesson_key_formulas: string;
  lesson_answer: string;
  lesson_none: string;

  // Exam Page
  exam_title: string;
  exam_duration: string;
  exam_total_points: string;
  exam_intro: string;
  exam_time_left: string;
  exam_score: string;
  exam_pts: string;
  exam_question: string;

  // History & Stats
  history_title: string;
  history_no_attempts: string;
  history_loading: string;
  stats_title: string;
  stats_attempts: string;
  stats_correct: string;
  stats_accuracy: string;
  stats_by_topic: string;
  stats_question_type: string;
  stats_formula: string;

  // Profile
  profile_title: string;
  profile_skill_level: string;
  profile_suggestions: string;
  profile_accuracy_14d: string;
  profile_topics: string;
  status_untouched: string;
  status_learning: string;
  status_shaky: string;
  status_solid: string;
  status_mastered: string;
  sug_weak_skill: string;
  sug_weak_formula: string;
  sug_rusty_skill: string;
  sug_unproven_skill: string;
  sug_new_skill: string;
  sug_new_topic: string;
  sug_first_steps: string;

  // Practice UI & Actions
  practice_reviewing_banner: string;
  practice_replay: string;
  practice_exit_review: string;
  practice_practicing: string;
  practice_back_to_profile: string;
  practice_dismiss: string;
  qtype_any: string;
  tool_pen: string;
  tool_eraser: string;
  tool_line: string;
  tool_curve: string;
  tool_ellipse: string;
  tool_select: string;
  tool_axes: string;
  tool_fit: string;
  tool_hint: string;
  tool_all_hints: string;
  tool_upload: string;
  tool_skip: string;
  tool_check_work: string;
  placeholder_type_answer: string;
  action_save: string;
  action_resume: string;
  action_next_question: string;
  verdict_complete: string;
  verdict_incorrect: string;
  label_topic: string;
  label_question_type: string;
  label_difficulty: string;
  label_mode: string;
  label_missing_labels_note: string;
  label_graph_assessment: string;
  label_curve: string;
  label_asymptotes: string;
  label_tangent: string;
  label_points: string;

  // Tooltips & accessibility labels (title=/aria-label=)
  tip_delete_progress: string;
  tip_save_progress: string;
  tip_new_question: string;
  tip_drag_move: string;
  tip_pen: string;
  tip_eraser: string;
  tip_line: string;
  tip_curve: string;
  tip_ellipse: string;
  tip_select: string;
  tip_axes: string;
  tip_zoom_unit: string;
  tip_refit: string;
  tip_zoom_out: string;
  tip_zoom_in: string;
  tip_skip_check: string;
  tip_settings: string;
  tip_debug: string;
  aria_grid_scale: string;
  aria_grid_x: string;
  aria_grid_y: string;
  aria_size: string;

  // Canvas settings popover
  set_friction_audio: string;
  set_palm_rejection: string;
  set_pressure_sensitivity: string;

  // Landing Page
  hero_title: string;
  hero_subtitle: string;
  feat_handwrite_title: string;
  feat_handwrite_desc: string;
  feat_grading_title: string;
  feat_grading_desc: string;
  feat_step_title: string;
  feat_step_desc: string;
}

export const TRANSLATIONS: Record<Language, Translations> = {
  en: {
    nav_profile: "Profile",
    nav_practice: "Practice",
    nav_exam: "Exam mode",
    nav_history: "History",
    nav_stats: "Stats",
    nav_formulas: "Formulas",
    nav_admin: "Admin",
    nav_logout: "Log out",
    nav_login: "Log in",
    nav_signup: "Sign up",
    language: "Language",

    topic_complex: "Complex numbers",
    topic_limit: "Limits",
    topic_integral: "Integrals",
    topic_probability: "Probability",
    topic_functions: "Functions",
    topic_continuity: "Continuity",
    topic_derivatives: "Derivatives",
    topic_differential_equations: "Differential equations",
    topic_vectors_space: "Vectors in space",
    topic_conics: "Conics",

    diff_easy: "Easy",
    diff_medium: "Medium",
    diff_hard: "Hard",

    mode_templates: "Templates",
    mode_gemini: "Gemini",

    btn_new_question: "New question",
    btn_generating: "Generating…",
    btn_check_answer: "Check answer",
    btn_checking: "Checking…",
    btn_hint: "Hint",
    btn_clear: "Clear",
    btn_undo: "Undo",
    btn_redo: "Redo",
    btn_fullscreen: "Full screen",
    btn_exit_fullscreen: "Exit full screen",
    btn_show_steps: "Show steps",
    btn_hide_steps: "Hide steps",
    btn_saved: "Saved",
    btn_review_mode: "Review mode",
    btn_back_to_practice: "Back to practice",
    btn_start_practicing: "Start practicing",
    btn_start_exam: "Start exam",
    btn_submit_exam: "Submit exam",
    btn_create_account: "Create account",
    btn_practice_this: "Practice",

    prompt_select_guide: "Please select a topic and difficulty, then click 'New question'.",
    tab_substep: "Step",
    label_solution: "Solution",
    label_your_work: "Your work",
    label_work_check: "Your work check",
    label_ref_graph: "Reference graph",
    label_ref_graph_compare: "Reference graph — compare with your drawing",
    label_step: "Step",
    label_part: "Part",
    label_step_score: "Step-by-step score",
    label_teacher_tip: "Teacher's Exam Rubric Tip",
    label_practice_formula: "Practice formula",
    label_expected: "Expected",
    label_reason: "Reason",
    label_consecutive_correct: "Consecutive correct answers",
    label_disambiguation_title: "Did you mean this line?",

    verdict_correct: "Correct",
    verdict_needs_revision: "Needs revision",
    verdict_you: "you",
    verdict_expected: "expected",
    verdict_unanswered: "(unanswered)",
    reason_exact: "exact match",
    reason_numeric: "numerically close",
    reason_mismatch: "mismatch",
    reason_unparsed: "could not parse answer",
    reason_given: "restatement of given",
    reason_identity: "algebraic identity",
    reason_unanswered: "unanswered",
    mark_verified_ok: "Verified OK",
    mark_could_not_verify: "Could not verify",

    formulas_title: "Formula sheet",
    formulas_subtitle: "Every technique used across the practice topics — the rule, and the specific formulas under it.",
    formulas_all_topics: "All topics",
    formulas_weight: "weight",
    formulas_practice: "Practice",
    formulas_loading: "Loading formulas…",
    lesson: "Lesson",
    lesson_loading: "Loading lesson…",
    lesson_worked_examples: "Worked examples",
    lesson_key_formulas: "Key formulas",
    lesson_answer: "Answer",
    lesson_none: "No lesson available for this exercise yet.",

    exam_title: "BAC II Mathematics",
    exam_duration: "Duration",
    exam_total_points: "Total",
    exam_intro: "The whole exam is shown at once, exactly as in the real test booklet. Work through every section, writing your steps for each question, then submit once at the end to be graded against the full rubric.",
    exam_time_left: "Time left",
    exam_score: "Score",
    exam_pts: "pts",
    exam_question: "Question",

    history_title: "History",
    history_no_attempts: "No attempts yet — head to Practice.",
    history_loading: "Loading history…",
    stats_title: "Stats",
    stats_attempts: "Attempts",
    stats_correct: "Correct",
    stats_accuracy: "Accuracy",
    stats_by_topic: "Performance by Topic",
    stats_question_type: "Question type",
    stats_formula: "Formula",

    profile_title: "Student Profile",
    profile_skill_level: "Skill Level",
    profile_suggestions: "Recommended Practice",
    profile_accuracy_14d: "Accuracy over the last 14 days",
    profile_topics: "Topic Mastery",
    status_untouched: "Not tried",
    status_learning: "Learning",
    status_shaky: "Shaky",
    status_solid: "Solid",
    status_mastered: "Mastered",
    sug_weak_skill: "Weak spot",
    sug_weak_formula: "Missing step",
    sug_rusty_skill: "Getting rusty",
    sug_unproven_skill: "Almost there",
    sug_new_skill: "Not tried yet",
    sug_new_topic: "Next topic",
    sug_first_steps: "Start here",

    practice_reviewing_banner: "Reviewing a past attempt — your writing is restored, draw on it or start fresh.",
    practice_replay: "Do the same exercise again",
    practice_exit_review: "Exit review",
    practice_practicing: "Practicing",
    practice_back_to_profile: "Back to profile",
    practice_dismiss: "Dismiss",
    qtype_any: "Any type",
    tool_pen: "Pen",
    tool_eraser: "Eraser",
    tool_line: "Line",
    tool_curve: "Curve",
    tool_ellipse: "Ellipse",
    tool_select: "Select",
    tool_axes: "Axes",
    tool_fit: "Fit",
    tool_hint: "Hint",
    tool_all_hints: "All hints shown",
    tool_upload: "Upload",
    tool_skip: "Skip",
    tool_check_work: "Check my work",
    placeholder_type_answer: "or type answer",
    action_save: "Save",
    action_resume: "Resume",
    action_next_question: "Next question →",
    verdict_complete: "Exercise complete!",
    verdict_incorrect: "Incorrect",
    label_topic: "Topic",
    label_question_type: "Question type",
    label_difficulty: "Difficulty",
    label_mode: "Generation mode",
    label_missing_labels_note: "Missing labels aren't counted wrong — add them and redraw to match the reference curve.",
    label_graph_assessment: "Graph Drawing Assessment",
    label_curve: "Curve",
    label_asymptotes: "Asymptotes",
    label_tangent: "Tangent",
    label_points: "Points",

    tip_delete_progress: "Delete saved progress",
    tip_save_progress: "Save progress for later",
    tip_new_question: "Generate a new question",
    tip_drag_move: "Drag to move",
    tip_pen: "Pen (P)",
    tip_eraser: "Eraser (E)",
    tip_line: "Straight line / ruler (R)",
    tip_curve: "Curve — drag to bend a smooth line (C)",
    tip_ellipse: "Ellipse — drag corner-to-corner (O)",
    tip_select: "Select / move — click a shape to grab its points, drag to reshape (V)",
    tip_axes: "Coordinate axes (G): select to spawn, tap the page to move the origin, use scale/Δ to resize",
    tip_zoom_unit: "Zoom: pixels per unit",
    tip_refit: "Re-fit the grid to the exercise's reference window",
    tip_zoom_out: "Zoom out",
    tip_zoom_in: "Zoom in",
    tip_skip_check: "Show the final result without waiting for the line-by-line check",
    tip_settings: "Canvas & Audio Settings",
    tip_debug: "Toggle debug panel",
    aria_grid_scale: "Grid scale (px per unit)",
    aria_grid_x: "Grid x step",
    aria_grid_y: "Grid y step",
    aria_size: "Size",

    set_friction_audio: "Friction Audio",
    set_palm_rejection: "Palm Rejection",
    set_pressure_sensitivity: "Pressure Sensitivity",

    hero_title: "BAC II Math Practice",
    hero_subtitle: "Practice Cambodian BAC II (Grade 12) math with stylus and handwriting. Get instant, mathematically-exact grading from SymPy and authentic step-by-step teacher explanations.",
    feat_handwrite_title: "Write it by hand",
    feat_handwrite_desc: "Draw your steps and answers on the infinite canvas or upload a photo — just like the real exam.",
    feat_grading_title: "Instant exact grading",
    feat_grading_desc: "Deterministic SymPy CAS computes the exact mathematical answer and grades line by line immediately.",
    feat_step_title: "Authentic step-by-step help",
    feat_step_desc: "Get concise, official exam rubric advice and teacher feedback when you get stuck.",
  },
  km: {
    nav_profile: "ព័ត៌មានរូប",
    nav_practice: "អនុវត្ត",
    nav_exam: "សម័យប្រឡង",
    nav_history: "ប្រវត្តិ",
    nav_stats: "ស្ថិតិ",
    nav_formulas: "រូបមន្ត",
    nav_admin: "គ្រប់គ្រង",
    nav_logout: "ចាកចេញ",
    nav_login: "ចូល",
    nav_signup: "ចុះឈ្មោះ",
    language: "ភាសា",

    topic_complex: "ចំនួនកុំផ្លិច",
    topic_limit: "លីមីត",
    topic_integral: "អាំងតេក្រាល",
    topic_probability: "ប្រូបាប៊ីលីតេ",
    topic_functions: "សិក្សាអនុគមន៍",
    topic_continuity: "ភាពជាប់នៃអនុគមន៍",
    topic_derivatives: "ដេរីវេ",
    topic_differential_equations: "សមីការឌីផេរ៉ង់ស្យែល",
    topic_vectors_space: "វិចទ័រក្នុងលំហ",
    topic_conics: "កោនិក",

    diff_easy: "ងាយ",
    diff_medium: "មធ្យម",
    diff_hard: "ពិបាក",

    mode_templates: "គំរូ",
    mode_gemini: "AI Gemini",

    btn_new_question: "លំហាត់ថ្មី",
    btn_generating: "កំពុងបង្កើត...",
    btn_check_answer: "ពិនិត្យចម្លើយ",
    btn_checking: "កំពុងពិនិត្យ...",
    btn_hint: "ជំនួយ",
    btn_clear: "សម្អាត",
    btn_undo: "ថយក្រោយ",
    btn_redo: "ទៅមុខ",
    btn_fullscreen: "ពេញអេក្រង់",
    btn_exit_fullscreen: "ចាកចេញពីពេញអេក្រង់",
    btn_show_steps: "បង្ហាញដំណោះស្រាយ",
    btn_hide_steps: "លាក់ដំណោះស្រាយ",
    btn_saved: "បានរក្សាទុក",
    btn_review_mode: "របៀបពិនិត្យឡើងវិញ",
    btn_back_to_practice: "ត្រឡប់ទៅការអនុវត្ត",
    btn_start_practicing: "ចាប់ផ្តើមអនុវត្ត",
    btn_start_exam: "ចាប់ផ្តើមប្រឡង",
    btn_submit_exam: "ប្រគល់វិញ្ញាសា",
    btn_create_account: "បង្កើតគណនី",
    btn_practice_this: "អនុវត្ត",

    prompt_select_guide: "សូមជ្រើសរើសប្រធានបទ និងកម្រិត រួចចុច «លំហាត់ថ្មី»។",
    tab_substep: "ជំហាន",
    label_solution: "ដំណោះស្រាយផ្លូវការ",
    label_your_work: "កិច្ចការរបស់អ្នក",
    label_work_check: "ការពិនិត្យកិច្ចការរបស់អ្នក",
    label_ref_graph: "ក្រាបយោង",
    label_ref_graph_compare: "ក្រាបយោង — ប្រៀបធៀបជាមួយគំនូររបស់អ្នក",
    label_step: "ជំហានទី",
    label_part: "ផ្នែក",
    label_step_score: "ពិន្ទុតាមជំហាន",
    label_teacher_tip: "ការណែនាំពីលោកគ្រូ (អត្រាកំណែបាក់ឌុប)",
    label_practice_formula: "អនុវត្តរូបមន្តនេះ",
    label_expected: "ចម្លើយរំពឹងទុក",
    label_reason: "មូលហេតុ",
    label_consecutive_correct: "ចម្លើយត្រឹមត្រូវជាប់ៗគ្នា",
    label_disambiguation_title: "តើអ្នកចង់សរសេរដូចបន្ទាត់នេះមែនទេ?",

    verdict_correct: "ត្រឹមត្រូវ",
    verdict_needs_revision: "ត្រូវពិនិត្យឡើងវិញ",
    verdict_you: "អ្នក",
    verdict_expected: "រំពឹងទុក",
    verdict_unanswered: "(មិនបានឆ្លើយ)",
    reason_exact: "ត្រឹមត្រូវពិតប្រាកដ",
    reason_numeric: "តម្លៃប្រហាក់ប្រហែលត្រឹមត្រូវ",
    reason_mismatch: "មិនត្រូវគ្នានឹងចម្លើយ",
    reason_unparsed: "មិនអាចអានទម្រង់ចម្លើយបាន",
    reason_given: "ការសរសេរប្រធានឡើងវិញ",
    reason_identity: "រូបមន្តសមភាពពិជគណិត",
    reason_unanswered: "មិនទាន់បានឆ្លើយ",
    mark_verified_ok: "ផ្ទៀងផ្ទាត់ត្រឹមត្រូវ",
    mark_could_not_verify: "មិនអាចផ្ទៀងផ្ទាត់បាន",

    formulas_title: "តារាងរូបមន្តគណិតវិទ្យា (បាក់ឌុប)",
    formulas_subtitle: "បណ្តុំរូបមន្ត និងវិធីសាស្រ្តដោះស្រាយលំហាត់គណិតវិទ្យាថ្នាក់ទី១២ តាមគ្រប់ប្រធានបទ។",
    formulas_all_topics: "ប្រធានបទទាំងអស់",
    formulas_weight: "ទម្ងន់ពិន្ទុ",
    formulas_practice: "អនុវត្ត",
    formulas_loading: "កំពុងផ្ទុកតារាងរូបមន្ត...",
    lesson: "មេរៀន",
    lesson_loading: "កំពុងផ្ទុកមេរៀន...",
    lesson_worked_examples: "ឧទាហរណ៍ដំណោះស្រាយ",
    lesson_key_formulas: "រូបមន្តសំខាន់",
    lesson_answer: "ចម្លើយ",
    lesson_none: "មិនទាន់មានមេរៀនសម្រាប់លំហាត់នេះនៅឡើយទេ។",

    exam_title: "វិញ្ញាសាគណិតវិទ្យា — បាក់ឌុប",
    exam_duration: "រយៈពេល",
    exam_total_points: "ពិន្ទុសរុប",
    exam_intro: "វិញ្ញាសាទាំងមូលត្រូវបង្ហាញជូនដូចក្រដាសប្រឡងផ្លូវការ។ សូមសរសេរជំហានដោះស្រាយតាមផ្នែកនីមួយៗ រួចប្រគល់វិញ្ញាសាពេលបញ្ចប់ដើម្បីទទួលបានពិន្ទុពេញ ១២៥ តាមអត្រាកំណែផ្លូវការ។",
    exam_time_left: "ពេលវេលានៅសល់",
    exam_score: "ពិន្ទុទទួលបាន",
    exam_pts: "ពិន្ទុ",
    exam_question: "សំណួរទី",

    history_title: "ប្រវត្តិនៃការអនុវត្ត",
    history_no_attempts: "មិនទាន់មានការសាកល្បងនៅឡើយ — សូមចូលទៅកាន់ទំព័រ «អនុវត្ត»។",
    history_loading: "កំពុងផ្ទុកប្រវត្តិ...",
    stats_title: "ស្ថិតិនៃការអនុវត្ត",
    stats_attempts: "ចំនួនដងសាកល្បង",
    stats_correct: "ចម្លើយត្រឹមត្រូវ",
    stats_accuracy: "ភាពត្រឹមត្រូវ",
    stats_by_topic: "លទ្ធផលតាមប្រធានបទ",
    stats_question_type: "ប្រភេទសំណួរ",
    stats_formula: "រូបមន្ត",

    profile_title: "ព័ត៌មានសមត្ថភាពសិស្ស",
    profile_skill_level: "កម្រិតសមត្ថភាពទូទៅ",
    profile_suggestions: "លំហាត់ដែលគួរអនុវត្តបន្ទាប់",
    profile_accuracy_14d: "ភាពត្រឹមត្រូវក្នុងរយៈពេល ១៤ ថ្ងៃចុងក្រោយ",
    profile_topics: "កម្រិតជំនាញតាមប្រធានបទ",
    status_untouched: "មិនទាន់បានសាកល្បង",
    status_learning: "កំពុងរៀន",
    status_shaky: "នៅស្ទើរ",
    status_solid: "រឹងមាំ",
    status_mastered: "ស្ទាត់ជំនាញ",
    sug_weak_skill: "ចំណុចខ្សោយ",
    sug_weak_formula: "ជំហានខ្វះចន្លោះ",
    sug_rusty_skill: "ចាប់ផ្តើមភ្លេច",
    sug_unproven_skill: "ជិតស្ទាត់ហើយ",
    sug_new_skill: "មិនទាន់បានសាក",
    sug_new_topic: "ប្រធានបទបន្ទាប់",
    sug_first_steps: "ចាប់ផ្តើមពីទីនេះ",

    practice_reviewing_banner: "កំពុងពិនិត្យមើលការប៉ុនប៉ងកន្លងមក — សំណេររបស់អ្នកត្រូវបានស្ដារឡើងវិញ អ្នកអាចសរសេរបន្ថែម ឬចាប់ផ្ដើមថ្មី។",
    practice_replay: "ធ្វើលំហាត់ដដែលនេះឡើងវិញ",
    practice_exit_review: "ចាកចេញពីការពិនិត្យ",
    practice_practicing: "កំពុងអនុវត្ត",
    practice_back_to_profile: "ត្រឡប់ទៅព័ត៌មានរូប",
    practice_dismiss: "បិទ",
    qtype_any: "គ្រប់ប្រភេទ",
    tool_pen: "ប៊ិច",
    tool_eraser: "ជ័រលុប",
    tool_line: "បន្ទាត់",
    tool_curve: "ខ្សែកោង",
    tool_ellipse: "ពងក្រពើ",
    tool_select: "ជ្រើសរើស",
    tool_axes: "អ័ក្សកូអរដោណេ",
    tool_fit: "តម្រឹម",
    tool_hint: "ជំនួយ",
    tool_all_hints: "បានបង្ហាញជំនួយទាំងអស់",
    tool_upload: "ផ្ទុកឡើង",
    tool_skip: "រំលង",
    tool_check_work: "ពិនិត្យមើលកិច្ចការខ្ញុំ",
    placeholder_type_answer: "ឬវាយចម្លើយនៅទីនេះ",
    action_save: "រក្សាទុក",
    action_resume: "បន្តធ្វើ",
    action_next_question: "លំហាត់បន្ទាប់ →",
    verdict_complete: "បានបញ្ចប់លំហាត់ជោគជ័យ!",
    verdict_incorrect: "មិនត្រឹមត្រូវ",
    label_topic: "ប្រធានបទ",
    label_question_type: "ប្រភេទសំណួរ",
    label_difficulty: "កម្រិតពិបាក",
    label_mode: "ទម្រង់បង្កើត",
    label_missing_labels_note: "ស្លាកដែលបាត់មិនត្រូវបានគិតថាខុសទេ — បន្ថែមពួកវាហើយគូរឡើងវិញដើម្បីផ្គូផ្គងនឹងខ្សែកោងយោង។",
    label_graph_assessment: "ការវាយតម្លៃគំនូរក្រាប",
    label_curve: "ខ្សែកោង",
    label_asymptotes: "អាស៊ីមតូត",
    label_tangent: "បន្ទាត់ប៉ះ",
    label_points: "ចំណុច",

    tip_delete_progress: "លុបវឌ្ឍនភាពដែលបានរក្សាទុក",
    tip_save_progress: "រក្សាទុកវឌ្ឍនភាពសម្រាប់ពេលក្រោយ",
    tip_new_question: "បង្កើតលំហាត់ថ្មី",
    tip_drag_move: "អូសដើម្បីផ្លាស់ទី",
    tip_pen: "ប៊ិច (P)",
    tip_eraser: "ជ័រលុប (E)",
    tip_line: "បន្ទាត់ត្រង់ / បន្ទាត់គូស (R)",
    tip_curve: "ខ្សែកោង — អូសដើម្បីបត់ខ្សែឱ្យរលូន (C)",
    tip_ellipse: "រង្វង់ពងក្រពើ — អូសពីជ្រុងមួយទៅជ្រុងម្ខាង (O)",
    tip_select: "ជ្រើសរើស / ផ្លាស់ទី — ចុចលើរូបដើម្បីចាប់ចំណុច រួចអូសដើម្បីកែរាង (V)",
    tip_axes: "អ័ក្សកូអរដោនេ (G) ៖ ជ្រើសរើសដើម្បីបង្កើត ចុចលើទំព័រដើម្បីផ្លាស់ទីគល់ ហើយប្រើ scale/Δ ដើម្បីកែទំហំ",
    tip_zoom_unit: "ពង្រីក ៖ ចំនួនភិចសែលក្នុងមួយឯកតា",
    tip_refit: "កែក្រឡាចត្រង្គឱ្យត្រូវនឹងក្របខ័ណ្ឌយោងនៃលំហាត់",
    tip_zoom_out: "បង្រួម",
    tip_zoom_in: "ពង្រីក",
    tip_skip_check: "បង្ហាញលទ្ធផលចុងក្រោយ ដោយមិនចាំការពិនិត្យមួយបន្ទាត់ម្តង",
    tip_settings: "ការកំណត់ក្តារគូរ និងសំឡេង",
    tip_debug: "បិទ/បើកផ្ទាំងបំបាត់កំហុស",
    aria_grid_scale: "មាត្រដ្ឋានក្រឡាចត្រង្គ (ភិចសែលក្នុងមួយឯកតា)",
    aria_grid_x: "ជំហានក្រឡាចត្រង្គតាមអ័ក្ស x",
    aria_grid_y: "ជំហានក្រឡាចត្រង្គតាមអ័ក្ស y",
    aria_size: "ទំហំ",

    set_friction_audio: "សំឡេងកកិតពេលគូរ",
    set_palm_rejection: "ការបដិសេធបាតដៃ",
    set_pressure_sensitivity: "ភាពប្រែប្រួលតាមកម្លាំងចុច",

    hero_title: "BAC II Math — កម្មវិធីហ្វឹកហាត់គណិតវិទ្យាបាក់ឌុប",
    hero_subtitle: "កម្មវិធីហ្វឹកហ្វឺនគណិតវិទ្យាថ្នាក់ទី១២ ដោយការសរសេរដៃលើអេក្រង់ ទទួលបានការកែយ៉ាងជាក់លាក់ដោយ SymPy និងការពន្យល់ជំហានលម្អិតបែបគរុកោសល្យខ្មែរ។",
    feat_handwrite_title: "សរសេរដោយដៃផ្ទាល់",
    feat_handwrite_desc: "គូសវាសជំហាន និងចម្លើយដោយប្រើប៊ិច Stylus ឬម្រាមដៃលើផ្ទាំងក្រដាសឌីជីថល ដូចពេលប្រឡងជាក់ស្តែង។",
    feat_grading_title: "កែភ្លាមៗដោយ SymPy",
    feat_grading_desc: "ម៉ាស៊ីនពិជគណិត SymPy CAS ផ្ទៀងផ្ទាត់រូបមន្ត និងលេខគណិតជាក់លាក់មួយបន្ទាត់ម្តងៗ ដោយមិនលម្អៀង។",
    feat_step_title: "ដំណោះស្រាយ និងអត្រាកំណែ",
    feat_step_desc: "ទទួលបានការណែនាំពីលោកគ្រូ និងគន្លឹះស្រង់ពិន្ទុតាមអត្រាកំណែផ្លូវការនៃក្រសួងអប់រំ យុវជន និងកីឡា។",
  },
};

// Question type labels dictionary for both languages
export const QUESTION_TYPE_LABELS: Record<string, { en: string; km: string }> = {
  // Complex
  modulus: { en: "Modulus", km: "ម៉ូឌុល" },
  argument: { en: "Argument", km: "អាគុយម៉ង់" },
  conjugate: { en: "Conjugate", km: "ចំនួនកុំផ្លិចឆ្លាស់" },
  real_part: { en: "Real part", km: "ផ្នែកពិត" },
  imaginary_part: { en: "Imaginary part", km: "ផ្នែកនិម្មិត" },

  // Limits
  "limit:direct_substitution": { en: "Direct substitution", km: "ជំនួសផ្ទាល់" },
  "limit:factoring_0_0": { en: "Factoring (0/0)", km: "ដាក់ជាផលគុណកត្តា (0/0)" },
  "limit:rationalization_conjugate_finite": { en: "Conjugate rationalization", km: "គុណកន្សោមឆ្លាស់" },
  "limit:sinc_standard_limit": { en: "Standard limit sin(x)/x", km: "លីមីតគំរូ sin(x)/x" },
  "limit:exponential_standard_limit": { en: "Standard limit (eˣ-1)/x", km: "លីមីតគំរូ (eˣ-1)/x" },
  "limit:rationalization_sinc_combo": { en: "Conjugate + sinc combo", km: "កន្សោមឆ្លាស់ + sinc" },
  "limit:exponential_sinc_combo": { en: "Exponential + sinc combo", km: "អិចស្បូណង់ស្យែល + sinc" },
  "limit:half_angle_sinc_combo": { en: "Half-angle + sinc combo", km: "កន្លះមុំ + sinc" },
  "limit:rational_function_infinity": { en: "Rational function at infinity", km: "អនុគមន៍សនិទាននៅអនន្ត" },
  "limit:conjugate_infinity": { en: "Conjugate at infinity", km: "កន្សោមឆ្លាស់នៅអនន្ត" },
  "limit:log_limit_infinity": { en: "Logarithmic limit at infinity", km: "លីមីតលោការីតនៅអនន្ត" },

  // Integrals
  definite_integral: { en: "Definite integral (any)", km: "អាំងតេក្រាលកំណត់ (ទាំងអស់)" },
  "definite_integral:polynomial": { en: "Definite — polynomial", km: "អាំងតេក្រាលកំណត់ — ពហុធា" },
  "definite_integral:linear_argument": { en: "Definite — linear argument", km: "អាំងតេក្រាលកំណត់ — អថេរលីនេអ៊ែរ" },
  "definite_integral:mixed_sum": { en: "Definite — mixed sum", km: "អាំងតេក្រាលកំណត់ — ផលបូកចម្រុះ" },
  "definite_integral:trig": { en: "Definite — trig", km: "អាំងតេក្រាលកំណត់ — ត្រីកោណមាត្រ" },
  "definite_integral:u_substitution": { en: "Definite — u-substitution", km: "អាំងតេក្រាលកំណត់ — ជំនួសអថេរ u" },
  "definite_integral:by_parts": { en: "Definite — by parts", km: "អាំងតេក្រាលកំណត់ — ដោយផ្នែក" },
  indefinite_integral: { en: "Indefinite integral (any)", km: "ព្រីមីទីវ (ទាំងអស់)" },
  "indefinite_integral:power": { en: "Indefinite — power", km: "ព្រីមីទីវ — ស្វ័យគុណ" },
  "indefinite_integral:expand": { en: "Indefinite — expand", km: "ព្រីមីទីវ — ពន្លាត" },
  "indefinite_integral:split": { en: "Indefinite — split", km: "ព្រីមីទីវ — បំបែកភាគយក" },
  "indefinite_integral:linear_argument": { en: "Indefinite — linear argument", km: "ព្រីមីទីវ — អថេរលីនេអ៊ែរ" },
  "indefinite_integral:usub": { en: "Indefinite — u-substitution", km: "ព្រីមីទីវ — ជំនួសអថេរ u" },
  "indefinite_integral:trig_sec": { en: "Indefinite — trig (sec²)", km: "ព្រីមីទីវ — ត្រីកោណមាត្រ (sec²)" },

  // Probability
  "probability:exercise_bag_split_atleast": { en: "Balls from a bag", km: "ចាប់បាល់ពីក្នុងថង់" },
  "probability:exercise_two_bag_odd_even": { en: "Two bags of numbered balls", km: "ថង់ពីរមានបាល់លេខ" },
  "probability:exercise_two_box_colors": { en: "Two boxes of colors", km: "ប្រអប់ពីរមានពណ៌" },
  "probability:exercise_banknotes": { en: "Banknotes", km: "ក្រដាសប្រាក់" },
  "probability:exercise_pens": { en: "Pens", km: "ប៊ិច" },
  "probability:exercise_students": { en: "Students", km: "សិស្ស" },
  counting: { en: "Counting (combinations & permutations)", km: "វិភាគបន្សំ និងតម្រៀប" },

  // Other topics
  study: { en: "Curve study & area", km: "សិក្សាខ្សែរាងកោង និងផ្ទៃ" },
  check_continuity: { en: "Check continuity / find parameter", km: "សិក្សាភាពជាប់ / រកប៉ារ៉ាម៉ែត្រ" },
  compute_derivative: { en: "Compute derivative", km: "គណនាដេរីវេ" },
  solve_ode: { en: "Solve differential equation", km: "ដោះស្រាយសមីការឌីផេរ៉ង់ស្យែល" },
  vector_ops: { en: "Vector operations", km: "ប្រមាណវិធីលើវិចទ័រ" },
  classify_conic: { en: "Classify conic / find feature", km: "កំណត់ប្រភេទកោនិក / រកលក្ខណៈ" },
};

/**
 * Translates a prompt or formats a question statement in authentic Khmer or English.
 * Follows the Khmer vs KaTeX Segregation rule:
 * Khmer words are rendered in browser typography, while mathematical symbols
 * are wrapped in $...$ or \\(...\\).
 */
/** Render `a + bi` the way a textbook writes it, or "" if either part is missing. */
function complexLiteral(a: unknown, b: unknown): string {
  if (typeof a !== "number" || typeof b !== "number") return "";
  if (b === 0) return `${a}`;
  if (b === 1) return a === 0 ? "i" : `${a} + i`;
  if (b === -1) return a === 0 ? "-i" : `${a} - i`;
  if (b > 0) return a === 0 ? `${b}i` : `${a} + ${b}i`;
  return a === 0 ? `${b}i` : `${a} - ${Math.abs(b)}i`;
}

/**
 * Pull the given complex number out of the backend's `prompt_latex`.
 *
 * The polar templates (De Moivre, n-th roots) have no a/b pair to rebuild from,
 * and their `z_display` is plain text ("27sqrt(2)(-1 - i)/2") that renders as
 * literal letters inside math mode — `prompt_latex` carries the real LaTeX.
 */
function latexGiven(rawPromptLatex: string | null | undefined): string {
  if (!rawPromptLatex) return "";
  const given = rawPromptLatex.match(/\\text\{Given \}\s*z\s*=\s*([\s\S]+?)\\text\{/);
  if (given) return given[1].trim();
  const root = rawPromptLatex.match(/w\^\{[^}]*\}\s*=\s*([\s\S]+?)\.?\s*$/);
  if (root) return root[1].trim();
  return "";
}

const COMPLEX_OP_KM: Record<string, { name: string; expr: string }> = {
  add: { name: "ផលបូក", expr: "z_1 + z_2" },
  subtract: { name: "ផលដក", expr: "z_1 - z_2" },
  multiply: { name: "ផលគុណ", expr: "z_1 \\cdot z_2" },
  divide: { name: "ផលចែក", expr: "\\dfrac{z_1}{z_2}" },
};

export function formatLocalizedPrompt(
  topic: string,
  questionType: string,
  params: Record<string, unknown> | undefined,
  rawPrompt: string | null | undefined,
  rawPromptLatex: string | null | undefined,
  lang: Language,
  zDisplay?: string | null
): { prompt: string; promptLatex?: string | null } {
  if (lang === "en" || !params) {
    return {
      prompt: rawPrompt || "",
      promptLatex: rawPromptLatex,
    };
  }

  // Check if rawPrompt is already in Khmer (e.g. probability word problems, function studies, past exams)
  if (rawPrompt && /[\u1780-\u17FF]/.test(rawPrompt)) {
    return {
      prompt: rawPrompt,
      promptLatex: rawPromptLatex,
    };
  }

  // Localize based on topic & question type
  switch (topic) {
    case "complex": {
      // Only the five single-number types carry a plain a/b pair; the power,
      // De Moivre and n-th root templates store polar coordinates instead, so
      // `z_display` (which the backend renders for every type) is the fallback.
      const zExpr =
        complexLiteral(params.a, params.b) ||
        latexGiven(rawPromptLatex) ||
        (zDisplay || "").trim();
      const mathZ = zExpr ? `$z = ${zExpr}$` : `$z$`;
      const n = params.n;

      switch (questionType) {
        case "modulus":
          return { prompt: `គណនាម៉ូឌុល $|z|$ នៃចំនួនកុំផ្លិច ${mathZ} ៖`, promptLatex: null };
        case "argument":
          return { prompt: `រកអាគុយម៉ង់ $\\arg(z)$ គិតជារ៉ាដ្យង់ នៃចំនួនកុំផ្លិច ${mathZ} ៖`, promptLatex: null };
        case "conjugate":
          return { prompt: `រកចំនួនកុំផ្លិចឆ្លាស់ $\\bar{z}$ នៃចំនួនកុំផ្លិច ${mathZ} ៖`, promptLatex: null };
        case "real_part":
          return { prompt: `រកផ្នែកពិត $\\operatorname{Re}(z)$ នៃចំនួនកុំផ្លិច ${mathZ} ៖`, promptLatex: null };
        case "imaginary_part":
          return { prompt: `រកផ្នែកនិម្មិត $\\operatorname{Im}(z)$ នៃចំនួនកុំផ្លិច ${mathZ} ៖`, promptLatex: null };
        case "complex_arithmetic": {
          const z1 = complexLiteral(params.a1, params.b1);
          const z2 = complexLiteral(params.a2, params.b2);
          const op = COMPLEX_OP_KM[String(params.operation)];
          if (z1 && z2 && op) {
            return {
              prompt: `គេឱ្យ $z_1 = ${z1}$ និង $z_2 = ${z2}$។ ចូររក${op.name} $${op.expr}$ ៖`,
              promptLatex: null,
            };
          }
          break;
        }
        case "complex_power":
        case "de_moivre_power": {
          if (zExpr && n !== undefined) {
            const viaDeMoivre =
              questionType === "de_moivre_power" ? " ដោយប្រើរូបមន្តដឺម័រ (De Moivre)" : "";
            return {
              prompt: `គេឱ្យ ${mathZ}។ ចូរគណនា $z^{${n}}$${viaDeMoivre} ៖`,
              promptLatex: null,
            };
          }
          break;
        }
        case "nth_roots": {
          if (zExpr && n !== undefined) {
            return {
              prompt: `ចូររកតម្លៃ $w$ មួយ ដែល $w^{${n}} = ${zExpr}$ ៖`,
              promptLatex: null,
            };
          }
          break;
        }
      }
      // Unknown complex type, or a template whose numbers we could not rebuild:
      // keep the original statement rather than emit a prompt with no data.
      return { prompt: rawPrompt || "", promptLatex: rawPromptLatex };
    }

    case "limit": {
      if (rawPromptLatex) {
        const cleanLatex = rawPromptLatex.replace(/^\\text\{Find\s*\}\s*/, "").replace(/^\\text\{Compute\s*\}\s*/, "");
        return {
          prompt: `គណនាលីមីត $${cleanLatex}$ ៖`,
          promptLatex: null,
        };
      }
      return {
        prompt: `គណនាលីមីតខាងក្រោម ៖\n${rawPrompt || ""}`,
        promptLatex: null,
      };
    }

    case "integral": {
      if (rawPromptLatex) {
        const cleanLatex = rawPromptLatex.replace(/^\\text\{Compute\s*\}\s*/, "");
        const isIndefinite = questionType === "indefinite_integral";
        const title = isIndefinite ? "គណនាព្រីមីទីវ" : "គណនាអាំងតេក្រាលកំណត់";
        return {
          prompt: `${title} $${cleanLatex}$ ៖`,
          promptLatex: null,
        };
      }
      return {
        prompt: `គណនាអាំងតេក្រាលខាងក្រោម ៖\n${rawPrompt || ""}`,
        promptLatex: null,
      };
    }

    case "derivatives": {
      const order = params.order === 2 ? "ដេរីវេទីពីរ $y''$" : "ដេរីវេ $y'$";
      if (rawPromptLatex) {
        const match = rawPromptLatex.match(/y\s*=\s*(.+?)(?:\.|$)/);
        const expr = match ? match[1] : "";
        if (expr) {
          return { prompt: `គណនា${order} នៃអនុគមន៍ $y = ${expr}$ ៖`, promptLatex: null };
        }
      }
      return { prompt: `គណនា${order} ៖\n${rawPrompt || ""}`, promptLatex: null };
    }

    case "continuity": {
      const point = params.point !== undefined ? `$x = ${params.point}$` : "";
      if (params.unknown) {
        return {
          prompt: `រកតម្លៃប៉ារ៉ាម៉ែត្រ $${params.unknown}$ ដើម្បីឱ្យអនុគមន៍ជាប់ត្រង់ចំណុច ${point} ៖\n${rawPrompt || ""}`,
          promptLatex: null,
        };
      }
      return {
        prompt: `សិក្សាភាពជាប់នៃអនុគមន៍ត្រង់ចំណុច ${point} ៖\n${rawPrompt || ""}`,
        promptLatex: null,
      };
    }

    case "differential_equations": {
      return {
        prompt: `ដោះស្រាយសមីការឌីផេរ៉ង់ស្យែលខាងក្រោម ៖\n${rawPrompt || ""}`,
        promptLatex: null,
      };
    }

    case "vectors_space": {
      return {
        prompt: `ក្នុងលំហប្រកបដោយតម្រុយអរតូណរម៉ាល់ គណនាប្រមាណវិធីវិចទ័រខាងក្រោម ៖\n${rawPrompt || ""}`,
        promptLatex: null,
      };
    }

    case "conics": {
      return {
        prompt: `គេឱ្យសមីការកោនិកខាងក្រោម។ ចូររកលក្ខណៈដែលបានសួរ ៖\n${rawPrompt || ""}`,
        promptLatex: null,
      };
    }

    default:
      return {
        prompt: rawPrompt || "",
        promptLatex: rawPromptLatex,
      };
  }
}
