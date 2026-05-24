import 'dart:convert';
import 'package:final_assignment_front/features/model/operation_log.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:final_assignment_front/utils/services/api_client.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:final_assignment_front/utils/services/auth_token_store.dart';

class OperationLogControllerApi {
  final ApiClient _apiClient;
  OperationLogControllerApi() : _apiClient = ApiClient();

  Future<void> initializeWithJwt() async {
    final jwtToken = (await AuthTokenStore.instance.getJwtToken());
    if (jwtToken == null) {
      throw Exception('api.error.notAuthenticated'.tr);
    }
    _apiClient.setJwtToken(jwtToken);
  }

  String _decode(http.Response r) => r.body;

  String _errorMessageOrHttpStatus(http.Response response) {
    return response.body.isNotEmpty
        ? _decode(response)
        : localizeHttpStatusError(response.statusCode);
  }

  // GET /api/logs/operation
  Future<List<OperationLog>> apiLogsOperationGet({
    int page = 1,
    int size = 20,
  }) async {
    final r = await _apiClient.invokeAPI(
      '/api/logs/operation',
      'GET',
      [
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      {},
      {},
      null,
      const ['bearerAuth'],
    );
    if (r.statusCode >= 400) {
      throw ApiException(r.statusCode, _errorMessageOrHttpStatus(r));
    }
    if (r.body.isEmpty) return [];
    final List<dynamic> data = jsonDecode(_decode(r));
    return data
        .map((e) => OperationLog.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // GET /api/logs/operation/{logId}
  Future<OperationLog?> apiLogsOperationLogIdGet({required int logId}) async {
    final r = await _apiClient.invokeAPI(
      '/api/logs/operation/$logId',
      'GET',
      const [],
      null,
      {},
      {},
      null,
      const ['bearerAuth'],
    );
    if (r.statusCode == 404) return null;
    if (r.statusCode >= 400) {
      throw ApiException(r.statusCode, _errorMessageOrHttpStatus(r));
    }
    return OperationLog.fromJson(jsonDecode(_decode(r)));
  }

  // GET /api/logs/operation/search/module?module=&page=&size=
  Future<List<OperationLog>> apiLogsOperationSearchModuleGet({
    required String module,
    int page = 1,
    int size = 20,
  }) async {
    final r = await _apiClient.invokeAPI(
      '/api/logs/operation/search/module',
      'GET',
      [
        QueryParam('module', module),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      {},
      {},
      null,
      const ['bearerAuth'],
    );
    if (r.statusCode >= 400) {
      throw ApiException(r.statusCode, _errorMessageOrHttpStatus(r));
    }
    if (r.body.isEmpty) return [];
    final List<dynamic> data = jsonDecode(_decode(r));
    return data
        .map((e) => OperationLog.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // GET /api/logs/operation/search/type?type=&page=&size=
  Future<List<OperationLog>> apiLogsOperationSearchTypeGet({
    required String type,
    int page = 1,
    int size = 20,
  }) async {
    final r = await _apiClient.invokeAPI(
      '/api/logs/operation/search/type',
      'GET',
      [
        QueryParam('type', type),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      {},
      {},
      null,
      const ['bearerAuth'],
    );
    if (r.statusCode >= 400) {
      throw ApiException(r.statusCode, _errorMessageOrHttpStatus(r));
    }
    if (r.body.isEmpty) return [];
    final List<dynamic> data = jsonDecode(_decode(r));
    return data
        .map((e) => OperationLog.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // GET /api/logs/operation/search/user/{userId}?page=&size=
  Future<List<OperationLog>> apiLogsOperationSearchUserUserIdGet({
    required int userId,
    int page = 1,
    int size = 20,
  }) async {
    final r = await _apiClient.invokeAPI(
      '/api/logs/operation/search/user/$userId',
      'GET',
      [
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      {},
      {},
      null,
      const ['bearerAuth'],
    );
    if (r.statusCode >= 400) {
      throw ApiException(r.statusCode, _errorMessageOrHttpStatus(r));
    }
    if (r.body.isEmpty) return [];
    final List<dynamic> data = jsonDecode(_decode(r));
    return data
        .map((e) => OperationLog.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // GET /api/logs/operation/search/time-range?startTime=&endTime=&page=&size=
  Future<List<OperationLog>> apiLogsOperationSearchTimeRangeGet({
    required String startTime,
    required String endTime,
    int page = 1,
    int size = 20,
  }) async {
    final r = await _apiClient.invokeAPI(
      '/api/logs/operation/search/time-range',
      'GET',
      [
        QueryParam('startTime', startTime),
        QueryParam('endTime', endTime),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      {},
      {},
      null,
      const ['bearerAuth'],
    );
    if (r.statusCode >= 400) {
      throw ApiException(r.statusCode, _errorMessageOrHttpStatus(r));
    }
    if (r.body.isEmpty) return [];
    final List<dynamic> data = jsonDecode(_decode(r));
    return data
        .map((e) => OperationLog.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // GET /api/logs/operation/search/username?username=&page=&size=
  Future<List<OperationLog>> apiLogsOperationSearchUsernameGet({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    final r = await _apiClient.invokeAPI(
      '/api/logs/operation/search/username',
      'GET',
      [
        QueryParam('username', username),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      {},
      {},
      null,
      const ['bearerAuth'],
    );
    if (r.statusCode >= 400) {
      throw ApiException(r.statusCode, _errorMessageOrHttpStatus(r));
    }
    if (r.body.isEmpty) return [];
    final List<dynamic> data = jsonDecode(_decode(r));
    return data
        .map((e) => OperationLog.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // GET /api/logs/operation/search/request-url?requestUrl=&page=&size=
  Future<List<OperationLog>> apiLogsOperationSearchRequestUrlGet({
    required String requestUrl,
    int page = 1,
    int size = 20,
  }) async {
    final r = await _apiClient.invokeAPI(
      '/api/logs/operation/search/request-url',
      'GET',
      [
        QueryParam('requestUrl', requestUrl),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      {},
      {},
      null,
      const ['bearerAuth'],
    );
    if (r.statusCode >= 400) {
      throw ApiException(r.statusCode, _errorMessageOrHttpStatus(r));
    }
    if (r.body.isEmpty) return [];
    final List<dynamic> data = jsonDecode(_decode(r));
    return data
        .map((e) => OperationLog.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // GET /api/logs/operation/search/request-method?requestMethod=&page=&size=
  Future<List<OperationLog>> apiLogsOperationSearchRequestMethodGet({
    required String requestMethod,
    int page = 1,
    int size = 20,
  }) async {
    final r = await _apiClient.invokeAPI(
      '/api/logs/operation/search/request-method',
      'GET',
      [
        QueryParam('requestMethod', requestMethod),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      {},
      {},
      null,
      const ['bearerAuth'],
    );
    if (r.statusCode >= 400) {
      throw ApiException(r.statusCode, _errorMessageOrHttpStatus(r));
    }
    if (r.body.isEmpty) return [];
    final List<dynamic> data = jsonDecode(_decode(r));
    return data
        .map((e) => OperationLog.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // GET /api/logs/operation/search/result?operationResult=&page=&size=
  Future<List<OperationLog>> apiLogsOperationSearchResultGet({
    required String operationResult,
    int page = 1,
    int size = 20,
  }) async {
    final r = await _apiClient.invokeAPI(
      '/api/logs/operation/search/result',
      'GET',
      [
        QueryParam('operationResult', operationResult),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      {},
      {},
      null,
      const ['bearerAuth'],
    );
    if (r.statusCode >= 400) {
      throw ApiException(r.statusCode, _errorMessageOrHttpStatus(r));
    }
    if (r.body.isEmpty) return [];
    final List<dynamic> data = jsonDecode(_decode(r));
    return data
        .map((e) => OperationLog.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}
