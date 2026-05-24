import 'package:final_assignment_front/features/model/system_settings.dart';
import 'package:final_assignment_front/features/model/sys_dict.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:final_assignment_front/utils/services/api_client.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:final_assignment_front/utils/services/auth_token_store.dart';

/// Shared default ApiClient instance.

final ApiClient defaultApiClient = ApiClient();

class SystemSettingsControllerApi {
  final ApiClient apiClient;

  /// Allows injecting a custom ApiClient and otherwise uses the shared default instance.


  SystemSettingsControllerApi([ApiClient? apiClient])
      : apiClient = apiClient ?? defaultApiClient;

  /// Loads the JWT token from storage and applies it to the ApiClient.
  Future<void> initializeWithJwt() async {
    final jwtToken = (await AuthTokenStore.instance.getJwtToken());
    if (jwtToken == null) {
      throw Exception('api.error.notAuthenticated'.tr);
    }
    apiClient.setJwtToken(jwtToken);
  }

  String _decodeBodyBytes(http.Response response) {
    return response.body;
  }

  void _throwIfError(http.Response response) {
    if (response.statusCode >= 400) {
      final message = response.body.isNotEmpty
          ? _decodeBodyBytes(response)
          : localizeHttpStatusError(response.statusCode);
      throw ApiException(response.statusCode, message);
    }
  }

  Future<Map<String, String>> _getHeaders({String? idempotencyKey}) async {
    final token = (await AuthTokenStore.instance.getJwtToken()) ?? '';
    final headers = <String, String>{
      'Content-Type': 'application/json; charset=utf-8',
    };
    if (token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    if (idempotencyKey != null && idempotencyKey.trim().isNotEmpty) {
      headers['Idempotency-Key'] = idempotencyKey.trim();
    }
    return headers;
  }

  /// GET /api/systemSettings/copyrightInfo - fetch copyright information.
  Future<String?> apiSystemSettingsCopyrightInfoGet() async {
    final response = await apiClient.invokeAPI(
      '/api/systemSettings/copyrightInfo',
      'GET',
      [],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    if (response.body.isEmpty) return null;
    return apiClient.deserialize(_decodeBodyBytes(response), 'String')
        as String?;
  }

  /// GET /api/systemSettings/dateFormat - fetch the date format.
  Future<String?> apiSystemSettingsDateFormatGet() async {
    final response = await apiClient.invokeAPI(
      '/api/systemSettings/dateFormat',
      'GET',
      [],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    if (response.body.isEmpty) return null;
    return apiClient.deserialize(_decodeBodyBytes(response), 'String')
        as String?;
  }

  /// GET /api/systemSettings/emailAccount - fetch the email account.
  Future<String?> apiSystemSettingsEmailAccountGet() async {
    final response = await apiClient.invokeAPI(
      '/api/systemSettings/emailAccount',
      'GET',
      [],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    if (response.body.isEmpty) return null;
    return apiClient.deserialize(_decodeBodyBytes(response), 'String')
        as String?;
  }

  /// GET /api/systemSettings/emailPassword - fetch the email password.
  Future<String?> apiSystemSettingsEmailPasswordGet() async {
    final response = await apiClient.invokeAPI(
      '/api/systemSettings/emailPassword',
      'GET',
      [],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    if (response.body.isEmpty) return null;
    return apiClient.deserialize(_decodeBodyBytes(response), 'String')
        as String?;
  }

  /// GET /api/systemSettings - fetch all system settings.
  Future<SystemSettings?> apiSystemSettingsGet() async {
    final response = await apiClient.invokeAPI(
      '/api/systemSettings',
      'GET',
      [],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    if (response.body.isEmpty) return null;
    final data = apiClient.deserialize(
        _decodeBodyBytes(response), 'Map<String, dynamic>');
    return SystemSettings.fromJson(data);
  }

  /// GET /api/systemSettings/loginTimeout - fetch the login timeout.

  Future<int?> apiSystemSettingsLoginTimeoutGet() async {
    final response = await apiClient.invokeAPI(
      '/api/systemSettings/loginTimeout',
      'GET',
      [],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    if (response.body.isEmpty) return null;
    return apiClient.deserialize(_decodeBodyBytes(response), 'int') as int?;
  }

  /// GET /api/systemSettings/pageSize - fetch the default page size.
  Future<int?> apiSystemSettingsPageSizeGet() async {
    final response = await apiClient.invokeAPI(
      '/api/systemSettings/pageSize',
      'GET',
      [],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    if (response.body.isEmpty) return null;
    return apiClient.deserialize(_decodeBodyBytes(response), 'int') as int?;
  }

  /// PUT /api/systemSettings - update system settings (admin only).

  Future<SystemSettings> apiSystemSettingsPut(
      {required SystemSettings systemSettings}) async {
    final response = await apiClient.invokeAPI(
      '/api/systemSettings',
      'PUT',
      [],
      systemSettings.toJson(),
      {},
      {},
      'application/json',
      ['bearerAuth'],
    );
    _throwIfError(response);
    final data = apiClient.deserialize(
        _decodeBodyBytes(response), 'Map<String, dynamic>');
    return SystemSettings.fromJson(data);
  }

  /// GET /api/systemSettings/sessionTimeout - fetch the session timeout.

  Future<int?> apiSystemSettingsSessionTimeoutGet() async {
    final response = await apiClient.invokeAPI(
      '/api/systemSettings/sessionTimeout',
      'GET',
      [],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    if (response.body.isEmpty) return null;
    return apiClient.deserialize(_decodeBodyBytes(response), 'int') as int?;
  }

  /// GET /api/systemSettings/smtpServer - fetch the SMTP server.
  Future<String?> apiSystemSettingsSmtpServerGet() async {
    final response = await apiClient.invokeAPI(
      '/api/systemSettings/smtpServer',
      'GET',
      [],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    if (response.body.isEmpty) return null;
    return apiClient.deserialize(_decodeBodyBytes(response), 'String')
        as String?;
  }

  /// GET /api/systemSettings/storagePath - fetch the storage path.
  Future<String?> apiSystemSettingsStoragePathGet() async {
    final response = await apiClient.invokeAPI(
      '/api/systemSettings/storagePath',
      'GET',
      [],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    if (response.body.isEmpty) return null;
    return apiClient.deserialize(_decodeBodyBytes(response), 'String')
        as String?;
  }

  /// GET /api/systemSettings/systemDescription - fetch the system description.
  Future<String?> apiSystemSettingsSystemDescriptionGet() async {
    final response = await apiClient.invokeAPI(
      '/api/systemSettings/systemDescription',
      'GET',
      [],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    if (response.body.isEmpty) return null;
    return apiClient.deserialize(_decodeBodyBytes(response), 'String')
        as String?;
  }

  /// GET /api/systemSettings/systemName - fetch the system name.
  Future<String?> apiSystemSettingsSystemNameGet() async {
    final response = await apiClient.invokeAPI(
      '/api/systemSettings/systemName',
      'GET',
      [],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    if (response.body.isEmpty) return null;
    return apiClient.deserialize(_decodeBodyBytes(response), 'String')
        as String?;
  }

  /// GET /api/systemSettings/systemVersion - fetch the system version.
  Future<String?> apiSystemSettingsSystemVersionGet() async {
    final response = await apiClient.invokeAPI(
      '/api/systemSettings/systemVersion',
      'GET',
      [],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    if (response.body.isEmpty) return null;
    return apiClient.deserialize(_decodeBodyBytes(response), 'String')
        as String?;
  }

  // --- New endpoints: /api/system/settings ---

  /// POST /api/system/settings
  Future<SystemSettings> apiSystemSettingsPost({
    required SystemSettings systemSettings,
    String? idempotencyKey,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings',
      'POST',
      const [],
      systemSettings.toJson(),
      await _getHeaders(idempotencyKey: idempotencyKey),
      {},
      'application/json',
      ['bearerAuth'],
    );
    _throwIfError(response);
    final data = apiClient.deserialize(
        _decodeBodyBytes(response), 'Map<String, dynamic>');
    return SystemSettings.fromJson(data);
  }

  /// PUT /api/system/settings/{settingId}
  Future<SystemSettings> apiSystemSettingsSettingIdPut({
    required int settingId,
    required SystemSettings systemSettings,
    String? idempotencyKey,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/$settingId',
      'PUT',
      const [],
      systemSettings.toJson(),
      await _getHeaders(idempotencyKey: idempotencyKey),
      {},
      'application/json',
      ['bearerAuth'],
    );
    _throwIfError(response);
    final data = apiClient.deserialize(
        _decodeBodyBytes(response), 'Map<String, dynamic>');
    return SystemSettings.fromJson(data);
  }

  /// DELETE /api/system/settings/{settingId}
  Future<void> apiSystemSettingsSettingIdDelete({
    required int settingId,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/$settingId',
      'DELETE',
      const [],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode != 204) {
      _throwIfError(response);
    }
  }

  /// GET /api/system/settings/{settingId}
  Future<SystemSettings?> apiSystemSettingsSettingIdGet({
    required int settingId,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/$settingId',
      'GET',
      const [],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode == 404) return null;
    _throwIfError(response);
    if (response.body.isEmpty) return null;
    final data = apiClient.deserialize(
        _decodeBodyBytes(response), 'Map<String, dynamic>');
    return SystemSettings.fromJson(data);
  }

  /// GET /api/system/settings
  Future<List<SystemSettings>> apiSystemSettingsListGet({
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings',
      'GET',
      [
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return SystemSettings.listFromJson(data);
  }

  /// GET /api/system/settings/key/{settingKey}
  Future<SystemSettings?> apiSystemSettingsKeyGet({
    required String settingKey,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/key/$settingKey',
      'GET',
      const [],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode == 404) return null;
    _throwIfError(response);
    if (response.body.isEmpty) return null;
    final data = apiClient.deserialize(
        _decodeBodyBytes(response), 'Map<String, dynamic>');
    return SystemSettings.fromJson(data);
  }

  /// GET /api/system/settings/category/{category}
  Future<List<SystemSettings>> apiSystemSettingsCategoryGet({
    required String category,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/category/$category',
      'GET',
      [
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return SystemSettings.listFromJson(data);
  }

  /// GET /api/system/settings/search/key/prefix
  Future<List<SystemSettings>> apiSystemSettingsSearchKeyPrefixGet({
    required String settingKey,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/search/key/prefix',
      'GET',
      [
        QueryParam('settingKey', settingKey),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return SystemSettings.listFromJson(data);
  }

  /// GET /api/system/settings/search/key/fuzzy
  Future<List<SystemSettings>> apiSystemSettingsSearchKeyFuzzyGet({
    required String settingKey,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/search/key/fuzzy',
      'GET',
      [
        QueryParam('settingKey', settingKey),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return SystemSettings.listFromJson(data);
  }

  /// GET /api/system/settings/search/type
  Future<List<SystemSettings>> apiSystemSettingsSearchTypeGet({
    required String settingType,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/search/type',
      'GET',
      [
        QueryParam('settingType', settingType),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return SystemSettings.listFromJson(data);
  }

  /// GET /api/system/settings/search/editable
  Future<List<SystemSettings>> apiSystemSettingsSearchEditableGet({
    required bool isEditable,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/search/editable',
      'GET',
      [
        QueryParam('isEditable', isEditable.toString()),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return SystemSettings.listFromJson(data);
  }

  /// GET /api/system/settings/search/encrypted
  Future<List<SystemSettings>> apiSystemSettingsSearchEncryptedGet({
    required bool isEncrypted,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/search/encrypted',
      'GET',
      [
        QueryParam('isEncrypted', isEncrypted.toString()),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return SystemSettings.listFromJson(data);
  }

  // --- Dict endpoints under /api/system/settings/dicts ---

  /// POST /api/system/settings/dicts
  Future<SysDictModel> apiSystemSettingsDictsPost({
    required SysDictModel sysDict,
    String? idempotencyKey,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/dicts',
      'POST',
      const [],
      sysDict.toJson(),
      await _getHeaders(idempotencyKey: idempotencyKey),
      {},
      'application/json',
      ['bearerAuth'],
    );
    _throwIfError(response);
    final data = apiClient.deserialize(
        _decodeBodyBytes(response), 'Map<String, dynamic>');
    return SysDictModel.fromJson(data);
  }

  /// PUT /api/system/settings/dicts/{dictId}
  Future<SysDictModel> apiSystemSettingsDictsDictIdPut({
    required int dictId,
    required SysDictModel sysDict,
    String? idempotencyKey,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/dicts/$dictId',
      'PUT',
      const [],
      sysDict.toJson(),
      await _getHeaders(idempotencyKey: idempotencyKey),
      {},
      'application/json',
      ['bearerAuth'],
    );
    _throwIfError(response);
    final data = apiClient.deserialize(
        _decodeBodyBytes(response), 'Map<String, dynamic>');
    return SysDictModel.fromJson(data);
  }

  /// DELETE /api/system/settings/dicts/{dictId}
  Future<void> apiSystemSettingsDictsDictIdDelete({
    required int dictId,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/dicts/$dictId',
      'DELETE',
      const [],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode != 204) {
      _throwIfError(response);
    }
  }

  /// GET /api/system/settings/dicts/{dictId}
  Future<SysDictModel?> apiSystemSettingsDictsDictIdGet({
    required int dictId,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/dicts/$dictId',
      'GET',
      const [],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode == 404) return null;
    _throwIfError(response);
    if (response.body.isEmpty) return null;
    final data = apiClient.deserialize(
        _decodeBodyBytes(response), 'Map<String, dynamic>');
    return SysDictModel.fromJson(data);
  }

  /// GET /api/system/settings/dicts
  Future<List<SysDictModel>> apiSystemSettingsDictsGet({
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/dicts',
      'GET',
      [
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return SysDictModel.listFromJson(data);
  }

  /// GET /api/system/settings/dicts/search/type
  Future<List<SysDictModel>> apiSystemSettingsDictsSearchTypeGet({
    required String dictType,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/dicts/search/type',
      'GET',
      [
        QueryParam('dictType', dictType),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return SysDictModel.listFromJson(data);
  }

  /// GET /api/system/settings/dicts/search/code
  Future<List<SysDictModel>> apiSystemSettingsDictsSearchCodeGet({
    required String dictCode,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/dicts/search/code',
      'GET',
      [
        QueryParam('dictCode', dictCode),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return SysDictModel.listFromJson(data);
  }

  /// GET /api/system/settings/dicts/search/label/prefix
  Future<List<SysDictModel>> apiSystemSettingsDictsSearchLabelPrefixGet({
    required String dictLabel,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/dicts/search/label/prefix',
      'GET',
      [
        QueryParam('dictLabel', dictLabel),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return SysDictModel.listFromJson(data);
  }

  /// GET /api/system/settings/dicts/search/label/fuzzy
  Future<List<SysDictModel>> apiSystemSettingsDictsSearchLabelFuzzyGet({
    required String dictLabel,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/dicts/search/label/fuzzy',
      'GET',
      [
        QueryParam('dictLabel', dictLabel),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return SysDictModel.listFromJson(data);
  }

  /// GET /api/system/settings/dicts/search/parent
  Future<List<SysDictModel>> apiSystemSettingsDictsSearchParentGet({
    required int parentId,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/dicts/search/parent',
      'GET',
      [
        QueryParam('parentId', '$parentId'),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return SysDictModel.listFromJson(data);
  }

  /// GET /api/system/settings/dicts/search/default
  Future<List<SysDictModel>> apiSystemSettingsDictsSearchDefaultGet({
    required bool isDefault,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/dicts/search/default',
      'GET',
      [
        QueryParam('isDefault', isDefault.toString()),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return SysDictModel.listFromJson(data);
  }

  /// GET /api/system/settings/dicts/search/status
  Future<List<SysDictModel>> apiSystemSettingsDictsSearchStatusGet({
    required String status,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/system/settings/dicts/search/status',
      'GET',
      [
        QueryParam('status', status),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return SysDictModel.listFromJson(data);
  }

}
