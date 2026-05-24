import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AuthTokenStore {
  AuthTokenStore._();

  static final AuthTokenStore instance = AuthTokenStore._();

  static const String _jwtKey = 'jwtToken';
  static const String _refreshKey = 'refreshToken';
  static const FlutterSecureStorage _secureStorage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  String? _jwtToken;
  String? _refreshToken;
  bool _loaded = false;

  Future<void> _ensureLoaded() async {
    if (_loaded) return;
    _jwtToken = await _secureStorage.read(key: _jwtKey);
    _refreshToken = await _secureStorage.read(key: _refreshKey);

    final prefs = await SharedPreferences.getInstance();
    final legacyJwtToken = prefs.getString(_jwtKey);
    final legacyRefreshToken = prefs.getString(_refreshKey);

    if ((_jwtToken == null || _jwtToken!.isEmpty) &&
        legacyJwtToken != null &&
        legacyJwtToken.isNotEmpty) {
      _jwtToken = legacyJwtToken;
      await _secureStorage.write(key: _jwtKey, value: legacyJwtToken);
    }
    if ((_refreshToken == null || _refreshToken!.isEmpty) &&
        legacyRefreshToken != null &&
        legacyRefreshToken.isNotEmpty) {
      _refreshToken = legacyRefreshToken;
      await _secureStorage.write(key: _refreshKey, value: legacyRefreshToken);
    }

    await prefs.remove(_jwtKey);
    await prefs.remove(_refreshKey);
    _loaded = true;
  }

  Future<String?> getJwtToken() async {
    await _ensureLoaded();
    return _jwtToken;
  }

  String? peekJwtToken() => _jwtToken;

  Future<void> setJwtToken(String? token) async {
    await _ensureLoaded();
    _jwtToken = token;
    _loaded = true;
    if (token == null || token.isEmpty) {
      await _secureStorage.delete(key: _jwtKey);
    } else {
      await _secureStorage.write(key: _jwtKey, value: token);
    }
  }

  Future<void> clearJwtToken() async {
    await setJwtToken(null);
  }

  Future<String?> getRefreshToken() async {
    await _ensureLoaded();
    return _refreshToken;
  }

  String? peekRefreshToken() => _refreshToken;

  Future<void> setRefreshToken(String? token) async {
    await _ensureLoaded();
    _refreshToken = token;
    _loaded = true;
    if (token == null || token.isEmpty) {
      await _secureStorage.delete(key: _refreshKey);
    } else {
      await _secureStorage.write(key: _refreshKey, value: token);
    }
  }

  Future<void> clearRefreshToken() async {
    await setRefreshToken(null);
  }

  Future<void> clearAllTokens() async {
    await _ensureLoaded();
    _jwtToken = null;
    _refreshToken = null;
    await _secureStorage.delete(key: _jwtKey);
    await _secureStorage.delete(key: _refreshKey);
  }
}
