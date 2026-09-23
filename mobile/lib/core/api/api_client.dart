import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../../models/user.dart';
import '../../models/question.dart';
import '../../models/grade_result.dart';
import '../../models/detect_result.dart';
import '../../models/stroke_doc.dart';
import '../../models/formula.dart';
import '../../models/profile.dart';
import '../../models/attempt.dart';
import '../../models/lesson.dart';
import '../../models/exam.dart';
import '../../models/session.dart';
import '../../models/template.dart';
import '../../models/graph.dart';
import '../../models/admin.dart';

class ApiClient {
  static const String _accessKey = 'bacii_access';
  static const String _refreshKey = 'bacii_refresh';

  final String baseUrl;

  ApiClient({String? baseUrl}) : baseUrl = baseUrl ?? _resolveDefaultBaseUrl();

  static String _resolveDefaultBaseUrl() {
    const envUrl = String.fromEnvironment('API_URL');
    if (envUrl.isNotEmpty) return envUrl;
    if (kIsWeb) return 'http://localhost:8016';
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8016';
    }
    return 'http://localhost:8016';
  }

  Future<String?> getAccessToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_accessKey);
  }

  Future<String?> getRefreshToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_refreshKey);
  }

  Future<void> setTokens(String access, String refresh) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_accessKey, access);
    await prefs.setString(_refreshKey, refresh);
  }

  Future<void> clearTokens() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_accessKey);
    await prefs.remove(_refreshKey);
  }

  Future<dynamic> _request(
    String path, {
    String method = 'GET',
    dynamic body,
    bool auth = true,
  }) async {
    final url = Uri.parse('$baseUrl$path');
    final headers = <String, String>{'Content-Type': 'application/json'};

    if (auth) {
      final token = await getAccessToken();
      if (token != null) headers['Authorization'] = 'Bearer $token';
    }

    final encodedBody = body != null ? jsonEncode(body) : null;

    Future<http.Response> send() {
      switch (method) {
        case 'POST':
          return http.post(url, headers: headers, body: encodedBody);
        case 'PUT':
          return http.put(url, headers: headers, body: encodedBody);
        case 'DELETE':
          return http.delete(url, headers: headers);
        default:
          return http.get(url, headers: headers);
      }
    }

    var res = await send();

    if (res.statusCode == 401 && auth) {
      final refreshed = await refreshToken();
      if (refreshed) {
        final newToken = await getAccessToken();
        if (newToken != null) headers['Authorization'] = 'Bearer $newToken';
        res = await send();
      } else {
        await clearTokens();
        throw Exception('Session expired');
      }
    }

    if (res.statusCode >= 400) {
      String detail = 'Request failed: ${res.statusCode}';
      try {
        final j = jsonDecode(utf8.decode(res.bodyBytes));
        if (j is Map && j['detail'] != null) detail = j['detail'].toString();
      } catch (_) {}
      throw Exception(detail);
    }

    if (res.body.isEmpty) return null;
    return jsonDecode(utf8.decode(res.bodyBytes));
  }

  Future<bool> refreshToken() async {
    final rt = await getRefreshToken();
    if (rt == null) return false;
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/auth/refresh'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'refresh_token': rt}),
      );
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        await setTokens(data['access_token'], data['refresh_token']);
        return true;
      }
    } catch (_) {}
    return false;
  }

  // --- Auth ---
  Future<AuthResponse> signup(String email, String password) async {
    final data = await _request('/auth/signup',
        method: 'POST', body: {'email': email, 'password': password}, auth: false);
    final authRes = AuthResponse.fromJson(data as Map<String, dynamic>);
    await setTokens(authRes.accessToken, authRes.refreshToken);
    return authRes;
  }

  Future<AuthResponse> login(String email, String password) async {
    final data = await _request('/auth/login',
        method: 'POST', body: {'email': email, 'password': password}, auth: false);
    final authRes = AuthResponse.fromJson(data as Map<String, dynamic>);
    await setTokens(authRes.accessToken, authRes.refreshToken);
    return authRes;
  }

  Future<User> me() async {
    final data = await _request('/auth/me');
    return User.fromJson(data as Map<String, dynamic>);
  }

  // --- Problems ---
  Future<Question> generateProblem({
    String generationMode = 'templates',
    String difficulty = 'medium',
    String topic = 'complex',
    String? questionType,
    String? variant,
  }) async {
    final data = await _request('/problems/generate', method: 'POST', body: {
      'generation_mode': generationMode,
      'difficulty': difficulty,
      'topic': topic,
      if (questionType != null) 'question_type': questionType,
      if (variant != null) 'variant': variant,
    });
    return Question.fromJson(data as Map<String, dynamic>);
  }

  Future<Question> replay(String questionId) async {
    final data = await _request('/problems/replay',
        method: 'POST', body: {'question_id': questionId});
    return Question.fromJson(data as Map<String, dynamic>);
  }

  Future<Question> question(String questionId) async {
    final data = await _request('/problems/$questionId');
    return Question.fromJson(data as Map<String, dynamic>);
  }

  Future<DetectResult> detect(String imageBase64) async {
    final data = await _request('/vision/detect',
        method: 'POST', body: {'image_base64': imageBase64});
    return DetectResult.fromJson(data as Map<String, dynamic>);
  }

  Future<GradeResult> grade({
    required String questionId,
    required String userAnswer,
    String? workText,
    List<List<double>?>? linesBoxes,
    String? part,
    int? hintsUsed,
    StrokeDocument? strokes,
    String? strokesThumb,
    String? lang,
  }) async {
    final data = await _request('/problems/grade', method: 'POST', body: {
      'question_id': questionId,
      'user_answer': userAnswer,
      if (workText != null) 'work_text': workText,
      if (linesBoxes != null) 'lines_boxes': linesBoxes,
      if (part != null) 'part': part,
      if (hintsUsed != null) 'hints_used': hintsUsed,
      if (strokes != null) 'strokes': strokes.toJson(),
      if (strokesThumb != null) 'strokes_thumb': strokesThumb,
      if (lang != null) 'lang': lang,
    });
    return GradeResult.fromJson(data as Map<String, dynamic>);
  }

  Future<Explanation> explain(String questionId,
      {String? userAnswer, String? workText, String? lang}) async {
    final data = await _request('/problems/explain', method: 'POST', body: {
      'question_id': questionId,
      if (userAnswer != null) 'user_answer': userAnswer,
      if (workText != null) 'work_text': workText,
      if (lang != null) 'lang': lang,
    });
    return Explanation.fromJson(data as Map<String, dynamic>);
  }

  Future<HintResponse> hint(String questionId,
      {String? part, String? workText, String? userAnswer, String? lang}) async {
    final data = await _request('/problems/hint', method: 'POST', body: {
      'question_id': questionId,
      if (part != null) 'part': part,
      if (workText != null) 'work_text': workText,
      if (userAnswer != null) 'user_answer': userAnswer,
      if (lang != null) 'lang': lang,
    });
    return HintResponse.fromJson(data as Map<String, dynamic>);
  }

  Future<GraphGradeResult> gradeGraph(
      String questionId, String strokesThumb) async {
    final data = await _request('/problems/grade-graph',
        method: 'POST',
        body: {'question_id': questionId, 'strokes_thumb': strokesThumb});
    return GraphGradeResult.fromJson(data as Map<String, dynamic>);
  }

  // --- Saved progress ---
  Future<SessionSummary> saveProgress({
    required String questionId,
    String? part,
    String? typed,
    String? workText,
    List<List<double>?>? linesBoxes,
    StrokeDocument? strokes,
    String? strokesThumb,
  }) async {
    final data = await _request('/problems/progress/save', method: 'POST', body: {
      'question_id': questionId,
      if (part != null) 'part': part,
      if (typed != null) 'typed': typed,
      if (workText != null) 'work_text': workText,
      if (linesBoxes != null) 'lines_boxes': linesBoxes,
      if (strokes != null) 'strokes': strokes.toJson(),
      if (strokesThumb != null) 'strokes_thumb': strokesThumb,
    });
    return SessionSummary.fromJson(data as Map<String, dynamic>);
  }

  Future<List<SessionSummary>> myProgress() async {
    final data = await _request('/progress');
    return ((data as List<dynamic>?) ?? [])
        .map((s) => SessionSummary.fromJson(s as Map<String, dynamic>))
        .toList();
  }

  Future<SessionDetail> progress(String id) async {
    final data = await _request('/progress/$id');
    return SessionDetail.fromJson(data as Map<String, dynamic>);
  }

  Future<void> deleteProgress(String id) async {
    await _request('/progress/$id', method: 'DELETE');
  }

  // --- History / stats / profile ---
  Future<List<Attempt>> getAttempts() async {
    final data = await _request('/attempts');
    return ((data as List<dynamic>?) ?? [])
        .map((a) => Attempt.fromJson(a as Map<String, dynamic>))
        .toList();
  }

  Future<AttemptDetail> attempt(String id) async {
    final data = await _request('/attempts/$id');
    return AttemptDetail.fromJson(data as Map<String, dynamic>);
  }

  Future<Stats> getStats() async {
    final data = await _request('/stats');
    return Stats.fromJson(data as Map<String, dynamic>);
  }

  Future<Profile> getProfile() async {
    final data = await _request('/profile');
    return Profile.fromJson(data as Map<String, dynamic>);
  }

  Future<Map<String, dynamic>> rebuildProfile() async {
    final data = await _request('/profile/rebuild', method: 'POST');
    return (data as Map<String, dynamic>?) ?? {};
  }

  Future<SkillCatalog> skillCatalog() async {
    final data = await _request('/skills');
    return SkillCatalog.fromJson(data as Map<String, dynamic>);
  }

  Future<Lesson> lesson(String skillKey) async {
    final data =
        await _request('/lessons?skill=${Uri.encodeQueryComponent(skillKey)}');
    return Lesson.fromJson(data as Map<String, dynamic>);
  }

  // --- Formulas ---
  Future<FormulaCatalog> getFormulas() async {
    final data = await _request('/formulas');
    return FormulaCatalog.fromJson(data as Map<String, dynamic>);
  }

  // --- Exam ---
  Future<Exam> exam(String examId) async {
    final data = await _request('/problems/exam/$examId');
    return Exam.fromJson(data as Map<String, dynamic>);
  }

  Future<ExamResult> submitExam(
      String examId, Map<String, String> answers) async {
    final data = await _request('/problems/exam/$examId/submit',
        method: 'POST', body: {'answers': answers});
    return ExamResult.fromJson(data as Map<String, dynamic>);
  }

  // --- Templates (admin) ---
  Future<TemplateSummary> templateSummary() async {
    final data = await _request('/templates/summary');
    return TemplateSummary.fromJson(data as Map<String, dynamic>);
  }

  Future<TemplateStructures> templateStructures([String? topic]) async {
    final q = topic != null ? '?topic=$topic' : '';
    final data = await _request('/templates/structures$q');
    return TemplateStructures.fromJson(data as Map<String, dynamic>);
  }

  Future<TemplateStructure> regenerateStructure(String structureId) async {
    final data = await _request('/templates/structures/regenerate',
        method: 'POST', body: {'structure_id': structureId});
    return TemplateStructure.fromJson(
        (data as Map<String, dynamic>)['structure'] as Map<String, dynamic>);
  }

  // --- Sandbox (admin) ---
  Future<SandboxSample> sandboxSample(
      String topic, String questionType, {String difficulty = 'medium'}) async {
    final data = await _request(
        '/sandbox/sample?topic=${Uri.encodeQueryComponent(topic)}&question_type=${Uri.encodeQueryComponent(questionType)}&difficulty=$difficulty');
    return SandboxSample.fromJson(data as Map<String, dynamic>);
  }

  Future<SandboxSample> sandboxStructureSample(
      String topic, String questionType, String structureId) async {
    final data = await _request(
        '/sandbox/structure-sample?topic=${Uri.encodeQueryComponent(topic)}&question_type=${Uri.encodeQueryComponent(questionType)}&structure_id=${Uri.encodeQueryComponent(structureId)}');
    return SandboxSample.fromJson(data as Map<String, dynamic>);
  }

  Future<SandboxSolveResult> sandboxSolve(
      String topic, String questionType, Map<String, dynamic> params) async {
    final data = await _request('/sandbox/solve', method: 'POST', body: {
      'topic': topic,
      'question_type': questionType,
      'params': params,
    });
    return SandboxSolveResult.fromJson(data as Map<String, dynamic>);
  }

  Future<SandboxGradeResult> sandboxGrade(String topic, String questionType,
      Map<String, dynamic> params, String lines) async {
    final data = await _request('/sandbox/grade', method: 'POST', body: {
      'topic': topic,
      'question_type': questionType,
      'params': params,
      'lines': lines,
    });
    return SandboxGradeResult.fromJson(data as Map<String, dynamic>);
  }

  // --- Admin: model settings + costs ---
  Future<ModelSettings> adminModelSettings() async {
    final data = await _request('/admin/model-settings');
    return ModelSettings.fromJson(data as Map<String, dynamic>);
  }

  Future<void> updateAdminModelSettings(ModelSettings settings) async {
    await _request('/admin/model-settings',
        method: 'POST', body: settings.toJson());
  }

  Future<AdminCostSummary> adminCostSummary({int days = 30}) async {
    final data = await _request('/admin/costs/summary?days=$days');
    return AdminCostSummary.fromJson(data as Map<String, dynamic>);
  }

  Future<List<AdminUserCost>> adminUserCosts(
      {int days = 30, String? endpoint}) async {
    final ep = (endpoint != null && endpoint.isNotEmpty) ? '&endpoint=$endpoint' : '';
    final data = await _request('/admin/costs/users?days=$days$ep');
    return ((data as List<dynamic>?) ?? [])
        .map((u) => AdminUserCost.fromJson(u as Map<String, dynamic>))
        .toList();
  }

  Future<List<AdminUsageLog>> adminUsageLogs(
      {int limit = 50, String? endpoint}) async {
    final ep = (endpoint != null && endpoint.isNotEmpty) ? '&endpoint=$endpoint' : '';
    final data = await _request('/admin/costs/logs?limit=$limit$ep');
    return ((data as List<dynamic>?) ?? [])
        .map((l) => AdminUsageLog.fromJson(l as Map<String, dynamic>))
        .toList();
  }
}
