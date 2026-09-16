import 'package:flutter/material.dart';
import '../api/api_client.dart';
import '../../models/user.dart';

class AuthProvider extends ChangeNotifier {
  final ApiClient apiClient;

  User? _user;
  bool _isLoading = true;
  String? _error;

  User? get user => _user;
  bool get isAuthenticated => _user != null;
  bool get isLoading => _isLoading;
  String? get error => _error;

  AuthProvider({required this.apiClient}) {
    checkAuth();
  }

  Future<void> checkAuth() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final token = await apiClient.getAccessToken();
      if (token != null) {
        _user = await apiClient.me();
      } else {
        _user = null;
      }
    } catch (e) {
      _user = null;
      await apiClient.clearTokens();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> login(String email, String password) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final res = await apiClient.login(email, password);
      _user = res.user;
      return true;
    } catch (e) {
      _error = e.toString().replaceFirst('Exception: ', '');
      return false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> signup(String email, String password) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final res = await apiClient.signup(email, password);
      _user = res.user;
      return true;
    } catch (e) {
      _error = e.toString().replaceFirst('Exception: ', '');
      return false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    await apiClient.clearTokens();
    _user = null;
    notifyListeners();
  }
}
