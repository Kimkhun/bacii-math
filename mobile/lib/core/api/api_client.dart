import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../../models/user.dart';
import '../../models/question.dart';
import '../../models/grade_result.dart';
import '../../models/stroke_doc.dart';
import '../../models/formula.dart';
import '../../models/profile.dart';
import '../../models/attempt.dart';

class ApiClient {
  static const String _accessKey = 'bacii_access';
  static const String _refreshKey = 'bacii_refresh';

  final String baseUrl;

  ApiClient({String? baseUrl})
      : baseUrl = baseUrl ?? _resolveDefaultBaseUrl();

  static String _resolveDefaultBaseUrl() {
    // If passed via dart-define, use it
    const envUrl = String.fromEnvironment('API_URL');
    if (envUrl.isNotEmpty) return envUrl;

    if (kIsWeb) {
      return 'http://localhost:8016';
    }
    // Android emulator alias for host
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
    final headers = <String, String>{
      'Content-Type': 'application/json',
    };

    if (auth) {
      final token = await getAccessToken();
      if (token != null) {
        headers['Authorization'] = 'Bearer $token';
      }
    }

    http.Response res;
    final encodedBody = body != null ? jsonEncode(body) : null;

    if (method == 'POST') {
      res = await http.post(url, headers: headers, body: encodedBody);
    } else if (method == 'PUT') {
      res = await http.put(url, headers: headers, body: encodedBody);
    } else if (method == 'DELETE') {
      res = await http.delete(url, headers: headers);
    } else {
      res = await http.get(url, headers: headers);
    }

    // Auto-refresh token on 401
    if (res.statusCode == 401 && auth) {
      final refreshed = await refreshToken();
      if (refreshed) {
        final newToken = await getAccessToken();
        if (newToken != null) {
          headers['Authorization'] = 'Bearer $newToken';
        }
        if (method == 'POST') {
          res = await http.post(url, headers: headers, body: encodedBody);
        } else {
          res = await http.get(url, headers: headers);
        }
      } else {
        await clearTokens();
        throw Exception('Session expired');
      }
    }

    if (res.statusCode >= 400) {
      String detail = 'Request failed: ${res.statusCode}';
      try {
        final j = jsonDecode(utf8.decode(res.bodyBytes));
        if (j is Map && j['detail'] != null) {
          detail = j['detail'].toString();
        }
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

  // --- Auth Endpoints ---
  Future<AuthResponse> signup(String email, String password) async {
    final data = await _request(
      '/auth/signup',
      method: 'POST',
      body: {'email': email, 'password': password},
      auth: false,
    );
    final authRes = AuthResponse.fromJson(data as Map<String, dynamic>);
    await setTokens(authRes.accessToken, authRes.refreshToken);
    return authRes;
  }

  Future<AuthResponse> login(String email, String password) async {
    final data = await _request(
      '/auth/login',
      method: 'POST',
      body: {'email': email, 'password': password},
      auth: false,
    );
    final authRes = AuthResponse.fromJson(data as Map<String, dynamic>);
    await setTokens(authRes.accessToken, authRes.refreshToken);
    return authRes;
  }

  Future<User> me() async {
    final data = await _request('/auth/me');
    return User.fromJson(data as Map<String, dynamic>);
  }

  // --- Problems Endpoints ---
  Future<Question> generateProblem({
    String topic = 'complex',
    String difficulty = 'medium',
    String mode = 'templates',
    String? questionType,
  }) async {
    final data = await _request(
      '/problems/generate',
      method: 'POST',
      body: {
        'topic': topic,
        'difficulty': difficulty,
        'generation_mode': mode,
        if (questionType != null) 'question_type': questionType,
      },
    );
    return Question.fromJson(data as Map<String, dynamic>);
  }

  Future<GradeResult> gradeProblem({
    required String questionId,
    required String userAnswer,
    String? workText,
    String? part,
    StrokeDocument? strokes,
    String? strokesThumb,
    String? lang = 'km',
  }) async {
    final data = await _request(
      '/problems/grade',
      method: 'POST',
      body: {
        'question_id': questionId,
        'user_answer': userAnswer,
        if (workText != null) 'work_text': workText,
        if (part != null) 'part': part,
        if (strokes != null) 'strokes': strokes.toJson(),
        if (strokesThumb != null) 'strokes_thumb': strokesThumb,
        'lang': lang,
      },
    );
    return GradeResult.fromJson(data as Map<String, dynamic>);
  }

  // --- Stats, Profile, Formulas, Attempts ---
  Future<Profile> getProfile() async {
    final data = await _request('/profile');
    return Profile.fromJson(data as Map<String, dynamic>);
  }

  Future<Stats> getStats() async {
    final data = await _request('/stats');
    return Stats.fromJson(data as Map<String, dynamic>);
  }

  Future<List<Attempt>> getAttempts() async {
    final data = await _request('/attempts');
    return ((data as List<dynamic>?) ?? [])
        .map((a) => Attempt.fromJson(a as Map<String, dynamic>))
        .toList();
  }

  Future<FormulaCatalog> getFormulas() async {
    final data = await _request('/formulas');
    return FormulaCatalog.fromJson(data as Map<String, dynamic>);
  }

  // --- Admin Endpoints ---
  Future<Map<String, dynamic>> getAdminModelSettings() async {
    final data = await _request('/admin/model-settings');
    return data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> updateAdminModelSettings(Map<String, dynamic> settings) async {
    final data = await _request('/admin/model-settings', method: 'POST', body: settings);
    return data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getAdminCostSummary({int days = 30}) async {
    final data = await _request('/admin/costs/summary?days=$days');
    return data as Map<String, dynamic>;
  }
}
