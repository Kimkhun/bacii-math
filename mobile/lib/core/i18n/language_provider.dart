import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'app_translations.dart';

class LanguageProvider extends ChangeNotifier {
  String _lang = 'km'; // Default to Khmer as in BAC II Next.js app

  String get currentLang => _lang;
  bool get isKhmer => _lang == 'km';

  LanguageProvider() {
    _loadLang();
  }

  Future<void> _loadLang() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString('bacii_lang');
    if (saved != null && (saved == 'en' || saved == 'km')) {
      _lang = saved;
      notifyListeners();
    }
  }

  Future<void> setLanguage(String lang) async {
    if (_lang == lang) return;
    _lang = lang;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('bacii_lang', lang);
  }

  String t(String key) {
    final map = _lang == 'km' ? AppTranslations.km : AppTranslations.en;
    return map[key] ?? AppTranslations.en[key] ?? key;
  }
}
