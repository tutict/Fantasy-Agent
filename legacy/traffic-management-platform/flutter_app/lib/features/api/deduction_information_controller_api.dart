import 'dart:convert';
import 'package:final_assignment_front/features/model/deduction_record.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:final_assignment_front/utils/services/api_client.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:final_assignment_front/utils/services/auth_token_store.dart';

final ApiClient defaultApiClient = ApiClient();

class DeductionInformationControllerApi {
  final ApiClient apiClient;
  DeductionInformationControllerApi([ApiClient? client])
      : apiClient = client ?? defaultApiClient;

  Future<void> initializeWithJwt() async {
    final jwtToken = (await AuthTokenStore.instance.getJwtToken());
    if (jwtToken == null) {
      throw Exception('api.error.notAuthenticated'.tr);
    }
    apiClient.setJwtToken(jwtToken);
  }

  String _decode(http.Response r) => r.body;

  String _errorMessageOrHttpStatus(http.Response response) {
    return response.body.isNotEmpty
        ? _decode(response)
        : localizeHttpStatusError(response.statusCode);
  }

  Future<Map<String, String>> _headers({String? idempotencyKey}) async {
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

  // POST /api/deductions
  Future<DeductionRecordModel> apiDeductionsPost({
    required DeductionRecordModel body,
    required String idempotencyKey,
  }) async {
    if (idempotencyKey.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('idempotencyKey'));
    }
    final r = await apiClient.invokeAPI(
      '/api/deductions',
      'POST',
      const [],
      body.toJson(),
      await _headers(idempotencyKey: idempotencyKey),
      const {},
      'application/json',
      const ['bearerAuth'],
    );
    if (r.statusCode >= 400) {
      throw ApiException(r.statusCode, _errorMessageOrHttpStatus(r));
    }
    return DeductionRecordModel.fromJson(jsonDecode(_decode(r)));
  }

  // GET /api/deductions/{deductionId}
  Future<DeductionRecordModel?> apiDeductionsDeductionIdGet({
    required int deductionId,
  }) async {
    final r = await apiClient.invokeAPI(
      '/api/deductions/$deductionId',
      'GET',
      const [],
      null,
      await _headers(),
      const {},
      null,
      const ['bearerAuth'],
    );
    if (r.statusCode == 404) return null;
    if (r.statusCode >= 400) {
      throw ApiException(r.statusCode, _errorMessageOrHttpStatus(r));
    }
    if (r.body.isEmpty) return null;
    return DeductionRecordModel.fromJson(jsonDecode(_decode(r)));
  }

  // GET /api/deductions
  Future<List<DeductionRecordModel>> apiDeductionsGet({
    int page = 1,
    int size = 20,
  }) async {
    final r = await apiClient.invokeAPI(
      '/api/deductions',
      'GET',
      [QueryParam('page', '$page'), QueryParam('size', '$size')],
      null,
      await _headers(),
      const {},
      null,
      const ['bearerAuth'],
    );
    if (r.statusCode >= 400) {
      throw ApiException(r.statusCode, _errorMessageOrHttpStatus(r));
    }
    if (r.body.isEmpty) return [];
    final List<dynamic> data = jsonDecode(_decode(r));
    return data.map((e) => DeductionRecordModel.fromJson(e)).toList();
  }

  // GET /api/deductions/driver/{driverId}?page=&size=
  Future<List<DeductionRecordModel>> apiDeductionsDriverDriverIdGet({
    required int driverId,
    int page = 1,
    int size = 20,
  }) async {
    final r = await apiClient.invokeAPI(
      '/api/deductions/driver/$driverId',
      'GET',
      [QueryParam('page', '$page'), QueryParam('size', '$size')],
      null,
      await _headers(),
      const {},
      null,
      const ['bearerAuth'],
    );
    if (r.statusCode >= 400) {
      throw ApiException(r.statusCode, _errorMessageOrHttpStatus(r));
    }
    if (r.body.isEmpty) return [];
    final List<dynamic> data = jsonDecode(_decode(r));
    return data.map((e) => DeductionRecordModel.fromJson(e)).toList();
  }

  // GET /api/deductions/offense/{offenseId}?page=&size=
  Future<List<DeductionRecordModel>> apiDeductionsOffenseOffenseIdGet({
    required int offenseId,
    int page = 1,
    int size = 20,
  }) async {
    final r = await apiClient.invokeAPI(
      '/api/deductions/offense/$offenseId',
      'GET',
      [QueryParam('page', '$page'), QueryParam('size', '$size')],
      null,
      await _headers(),
      const {},
      null,
      const ['bearerAuth'],
    );
    if (r.statusCode >= 400) {
      throw ApiException(r.statusCode, _errorMessageOrHttpStatus(r));
    }
    if (r.body.isEmpty) return [];
    final List<dynamic> data = jsonDecode(_decode(r));
    return data.map((e) => DeductionRecordModel.fromJson(e)).toList();
  }

  // GET /api/deductions/search/handler?handler=&mode=&page=&size=
  Future<List<DeductionRecordModel>> apiDeductionsSearchHandlerGet({
    required String handler,
    String mode = 'prefix',
    int page = 1,
    int size = 20,
  }) async {
    final r = await apiClient.invokeAPI(
      '/api/deductions/search/handler',
      'GET',
      [
        QueryParam('handler', handler),
        QueryParam('mode', mode),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _headers(),
      const {},
      null,
      const ['bearerAuth'],
    );
    if (r.statusCode >= 400) {
      throw ApiException(r.statusCode, _errorMessageOrHttpStatus(r));
    }
    if (r.body.isEmpty) return [];
    final List<dynamic> data = jsonDecode(_decode(r));
    return data.map((e) => DeductionRecordModel.fromJson(e)).toList();
  }

  // GET /api/deductions/search/status?status=&page=&size=
  Future<List<DeductionRecordModel>> apiDeductionsSearchStatusGet({
    required String status,
    int page = 1,
    int size = 20,
  }) async {
    final r = await apiClient.invokeAPI(
      '/api/deductions/search/status',
      'GET',
      [
        QueryParam('status', status),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _headers(),
      const {},
      null,
      const ['bearerAuth'],
    );
    if (r.statusCode >= 400) {
      throw ApiException(r.statusCode, _errorMessageOrHttpStatus(r));
    }
    if (r.body.isEmpty) return [];
    final List<dynamic> data = jsonDecode(_decode(r));
    return data.map((e) => DeductionRecordModel.fromJson(e)).toList();
  }

  // GET /api/deductions/search/time-range?startTime=&endTime=&page=&size=
  Future<List<DeductionRecordModel>> apiDeductionsSearchTimeRangeGet({
    required String startTime,
    required String endTime,
    int page = 1,
    int size = 20,
  }) async {
    final r = await apiClient.invokeAPI(
      '/api/deductions/search/time-range',
      'GET',
      [
        QueryParam('startTime', startTime),
        QueryParam('endTime', endTime),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _headers(),
      const {},
      null,
      const ['bearerAuth'],
    );
    if (r.statusCode >= 400) {
      throw ApiException(r.statusCode, _errorMessageOrHttpStatus(r));
    }
    if (r.body.isEmpty) return [];
    final List<dynamic> data = jsonDecode(_decode(r));
    return data.map((e) => DeductionRecordModel.fromJson(e)).toList();
  }
}
