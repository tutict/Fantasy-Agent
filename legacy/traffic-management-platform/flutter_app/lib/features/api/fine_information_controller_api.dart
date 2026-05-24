import 'dart:convert';
import 'package:final_assignment_front/features/model/fine_information.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:final_assignment_front/utils/services/api_client.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:final_assignment_front/utils/services/auth_token_store.dart';

final ApiClient defaultApiClient = ApiClient();

class FineInformationControllerApi {
  final ApiClient apiClient;

  FineInformationControllerApi([ApiClient? apiClient])
      : apiClient = apiClient ?? defaultApiClient;

  /// Loads the JWT token from storage and applies it to the ApiClient.
  Future<void> initializeWithJwt() async {
    final jwtToken = (await AuthTokenStore.instance.getJwtToken());
    if (jwtToken == null) {
      throw Exception('api.error.notAuthenticated'.tr);
    }
    apiClient.setJwtToken(jwtToken);
  }

  /// Decodes response bytes as UTF-8 text.
  String _decodeBodyBytes(http.Response response) {
    return utf8.decode(response.bodyBytes); // Properly decode UTF-8
  }

  String _errorMessageOrHttpStatus(http.Response response) {
    return response.bodyBytes.isNotEmpty
        ? _decodeBodyBytes(response)
        : localizeHttpStatusError(response.statusCode);
  }

  /// Builds request headers and adds JWT plus idempotency support when needed.
  Future<Map<String, String>> _getHeaders({String? idempotencyKey}) async {
    final token = (await AuthTokenStore.instance.getJwtToken()) ?? '';
    final headers = <String, String>{
      'Content-Type': 'application/json; charset=utf-8',
      if (token.isNotEmpty) 'Authorization': 'Bearer $token',
    };
    if (idempotencyKey != null && idempotencyKey.trim().isNotEmpty) {
      headers['Idempotency-Key'] = idempotencyKey.trim();
    }
    return headers;
  }

  /// HTTP methods.
  // HTTP Methods

  /// POST /api/fines - create a fine record (admin only).

  Future<void> apiFinesPost({
    required FineInformation fineInformation,
    required String idempotencyKey,
  }) async {
    const path = '/api/fines';
    final response = await apiClient.invokeAPI(
      path,
      'POST',
      [],
      fineInformation.toJson(),
      await _getHeaders(idempotencyKey: idempotencyKey),
      {},
      'application/json',
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
  }

  /// GET /api/fines/{fineId} - fetch fine details by ID.
  Future<FineInformation?> apiFinesFineIdGet({
    required int fineId,
  }) async {
    final path = '/api/fines/$fineId';
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [],
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      if (response.statusCode == 404) {
        return null; // Not found, return null
      }
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return null;
    final data = apiClient.deserialize(
        _decodeBodyBytes(response), 'Map<String, dynamic>');
    return FineInformation.fromJson(data);
  }

  /// GET /api/fines - fetch all fine records.
  Future<List<FineInformation>> apiFinesGet({
    int page = 1,
    int size = 20,
  }) async {
    const path = '/api/fines';
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [QueryParam('page', '$page'), QueryParam('size', '$size')],
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => FineInformation.fromJson(json)).toList();
  }

  Future<List<FineInformation>> apiFinesMeGet({
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/fines/me',
      'GET',
      [QueryParam('page', '$page'), QueryParam('size', '$size')],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      if (response.statusCode == 204 || response.statusCode == 404) return [];
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => FineInformation.fromJson(json)).toList();
  }

  /// PUT /api/fines/{fineId} - update a fine record (admin only).

  /// DELETE /api/fines/{fineId} - delete a fine record (admin only).

  /// GET /api/fines/payee/{payee} - fetch fines by payee.
  Future<List<FineInformation>> apiFinesPayeePayeeGet({
    required String payee,
    String mode = 'fuzzy',
    int page = 1,
    int size = 20,
  }) async {
    if (payee.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('payee'));
    }
    const path = '/api/fines/search/handler';
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [
        QueryParam('handler', payee),
        QueryParam('mode', mode),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => FineInformation.fromJson(json)).toList();
  }

  /// GET /api/fines/search/date-range - fetch fines within a date range.
  Future<List<FineInformation>> apiFinesTimeRangeGet({
    String startDate = '1970-01-01', // Default matches backend
    String endDate = '2100-01-01', // Default matches backend
    int page = 1,
    int size = 20,
  }) async {
    const path = '/api/fines/search/date-range';
    final queryParams = [
      QueryParam('startDate', startDate),
      QueryParam('endDate', endDate),
      QueryParam('page', '$page'),
      QueryParam('size', '$size'),
    ];
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      queryParams,
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => FineInformation.fromJson(json)).toList();
  }

  /// GET /api/fines/receiptNumber/{receiptNumber} - fetch a fine by receipt number.
  Future<FineInformation?> apiFinesReceiptNumberReceiptNumberGet({
    required String receiptNumber,
  }) async {
    if (receiptNumber.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('receiptNumber'));
    }
    final path =
        '/api/fines/receiptNumber/${Uri.encodeComponent(receiptNumber)}';
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [],
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      if (response.statusCode == 404) {
        return null; // Not found, return null
      }
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return null;
    final data = apiClient.deserialize(
        _decodeBodyBytes(response), 'Map<String, dynamic>');
    return FineInformation.fromJson(data);
  }

  /// GET /api/fines/offense/{offenseId} - fetch fines by offense ID.
  Future<List<FineInformation>> apiFinesOffenseOffenseIdGet({
    required int offenseId,
    int page = 1,
    int size = 20,
  }) async {
    final path = '/api/fines/offense/$offenseId';
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [QueryParam('page', '$page'), QueryParam('size', '$size')],
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => FineInformation.fromJson(json)).toList();
  }

  /// GET /api/fines/search/handler - search fines by handler.
  Future<List<FineInformation>> apiFinesSearchHandlerGet({
    required String handler,
    String mode = 'prefix', // or 'fuzzy'
    int page = 1,
    int size = 20,
  }) async {
    const path = '/api/fines/search/handler';
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [
        QueryParam('handler', handler),
        QueryParam('mode', mode),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => FineInformation.fromJson(json)).toList();
  }

  /// GET /api/fines/search/status - search fines by payment status.
  Future<List<FineInformation>> apiFinesSearchStatusGet({
    required String status,
    int page = 1,
    int size = 20,
  }) async {
    const path = '/api/fines/search/status';
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [
        QueryParam('status', status),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => FineInformation.fromJson(json)).toList();
  }

  /// GET /api/fines/by-time-range - search fines by time range.
  Future<List<FineInformation>> apiFinesByTimeRangeGet({
    required String startTime,
    required String endTime,
    int maxSuggestions = 10,
  }) async {
    if (startTime.isEmpty || endTime.isEmpty) {
      throw ApiException(
        400,
        localizeMissingRequiredParams(['startTime', 'endTime']),
      );
    }
    const path = '/api/fines/by-time-range';
    final queryParams = [
      QueryParam('startTime', startTime),
      QueryParam('endTime', endTime),
      QueryParam('maxSuggestions', maxSuggestions.toString()),
    ];
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      queryParams,
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      if (response.statusCode == 204) {
        return []; // No content, return empty list
      }
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => FineInformation.fromJson(json)).toList();
  }

}
