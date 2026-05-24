import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

class LocaleController extends GetxController {
  LocaleController(this._locale);

  static const _languageCodeKey = 'app.languageCode';
  static const _countryCodeKey = 'app.countryCode';

  Locale _locale;

  Locale get locale => _locale;

  bool get isChinese => _locale.languageCode == 'zh';

  static Future<LocaleController> create() async {
    final prefs = await SharedPreferences.getInstance();
    final languageCode = prefs.getString(_languageCodeKey) ?? 'zh';
    final countryCode = prefs.getString(_countryCodeKey) ?? 'CN';
    return LocaleController(Locale(languageCode, countryCode));
  }

  Future<void> updateLocale(Locale locale) async {
    if (_locale == locale) return;

    _locale = locale;
    update();
    await Get.updateLocale(locale);

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_languageCodeKey, locale.languageCode);
    await prefs.setString(_countryCodeKey, locale.countryCode ?? '');
  }
}
