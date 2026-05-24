import 'dart:convert';
import 'package:final_assignment_front/features/model/offense_information.dart';
import 'package:final_assignment_front/features/model/driver_information.dart';
import 'package:final_assignment_front/features/model/vehicle_information.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:final_assignment_front/utils/services/api_client.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:final_assignment_front/utils/services/auth_token_store.dart';

/// Shared default ApiClient instance.

final ApiClient defaultApiClient = ApiClient();

class OffenseInformationControllerApi {
  final ApiClient apiClient;

  OffenseInformationControllerApi([ApiClient? apiClient])
      : apiClient = apiClient ?? defaultApiClient;

  /// Loads the JWT token from storage and applies it to the ApiClient.
  Future<void> initializeWithJwt() async {
    final jwtToken = (await AuthTokenStore.instance.getJwtToken());
    if (jwtToken == null || jwtToken.isEmpty) {
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

  /// POST /api/offenses - create an offense record (admin only).

  Future<void> apiOffensesPost({
    required OffenseInformation offenseInformation,
    required String idempotencyKey,
  }) async {
    const path = '/api/offenses';
    final response = await apiClient.invokeAPI(
      path,
      'POST',
      [],
      offenseInformation.toJson(),
      await _getHeaders(idempotencyKey: idempotencyKey),
      {},
      'application/json',
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      if (response.statusCode == 400) {
        throw ApiException(400, localizeInvalidRequestData());
      } else if (response.statusCode == 409) {
        throw ApiException(409, localizeDuplicateRequest(idempotencyKey));
      }
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
  }

  /// GET /api/offenses/{offenseId} - fetch offense details by ID.
  Future<OffenseInformation?> apiOffensesOffenseIdGet({
    required int offenseId,
  }) async {
    final path = '/api/offenses/$offenseId';
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
    return OffenseInformation.fromJson(data);
  }

  /// GET /api/offenses - fetch all offense records.
  Future<List<OffenseInformation>> apiOffensesGet({
    int page = 1,
    int size = 20,
  }) async {
    const path = '/api/offenses';
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [
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
    return jsonList.map((json) => OffenseInformation.fromJson(json)).toList();
  }

  Future<List<OffenseInformation>> apiOffensesMeGet({
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/offenses/me',
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
    return jsonList.map((json) => OffenseInformation.fromJson(json)).toList();
  }

  /// PUT /api/offenses/{offenseId} - update an offense record (admin only).

  Future<OffenseInformation> apiOffensesOffenseIdPut({
    required int offenseId,
    required OffenseInformation offenseInformation,
    required String idempotencyKey,
  }) async {
    final path = '/api/offenses/$offenseId';
    final response = await apiClient.invokeAPI(
      path,
      'PUT',
      [],
      offenseInformation.toJson(),
      await _getHeaders(idempotencyKey: idempotencyKey),
      {},
      'application/json',
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      if (response.statusCode == 404) {
        throw ApiException(
          404,
          localizeEntityNotFoundWithId('api.entity.offense'.tr, offenseId),
        );
      } else if (response.statusCode == 409) {
        throw ApiException(409, localizeDuplicateRequest(idempotencyKey));
      }
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    final data = apiClient.deserialize(
        _decodeBodyBytes(response), 'Map<String, dynamic>');
    return OffenseInformation.fromJson(data);
  }

  /// DELETE /api/offenses/{offenseId} - delete an offense record (admin only).

  Future<void> apiOffensesOffenseIdDelete({
    required int offenseId,
  }) async {
    final path = '/api/offenses/$offenseId';
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'DELETE',
      [],
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      if (response.statusCode == 404) {
        throw ApiException(
          404,
          localizeEntityNotFoundWithId('api.entity.offense'.tr, offenseId),
        );
      } else if (response.statusCode == 403) {
        throw ApiException(
            403, localizeAdminOnlyDelete('api.resource.offenses'.tr));
      }
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
  }

  /// GET /api/offenses/timeRange - fetch offenses within a time range.
  Future<List<OffenseInformation>> apiOffensesTimeRangeGet({
    String startTime = '1970-01-01', // Default matches backend
    String endTime = '2100-01-01', // Default matches backend
    int page = 1,
    int size = 20,
  }) async {
    const path = '/api/offenses/search/time-range';
    final queryParams = [
      QueryParam('startTime', startTime),
      QueryParam('endTime', endTime),
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
    return jsonList.map((json) => OffenseInformation.fromJson(json)).toList();
  }

  /// GET /api/offenses/by-offense-type - search offenses by offense type.
  Future<List<OffenseInformation>> apiOffensesByOffenseTypeGet({
    required String query,
    int page = 1,
    int size = 10,
  }) async {
    if (query.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('query'));
    }
    const path = '/api/offenses/search/type';
    final queryParams = [
      QueryParam('offenseType', query),
      QueryParam('page', page.toString()),
      QueryParam('size', size.toString()),
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
    return jsonList.map((json) => OffenseInformation.fromJson(json)).toList();
  }

  /// GET /api/offenses/by-driver-name - search offenses by driver name.
  Future<List<OffenseInformation>> apiOffensesByDriverNameGet({
    required String query,
    int page = 1,
    int size = 10,
  }) async {
    if (query.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('query'));
    }
    // Composite: drivers by name -> offenses by driverId
    const driverPath = '/api/drivers/search/name';
    final headerParams = await _getHeaders();
    final driverResp = await apiClient.invokeAPI(
      driverPath,
      'GET',
      [
        QueryParam('keywords', query),
        QueryParam('page', '1'),
        QueryParam('size', '20'),
      ],
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
    if (driverResp.statusCode >= 400) {
      throw ApiException(
        driverResp.statusCode,
        _errorMessageOrHttpStatus(driverResp),
      );
    }
    if (driverResp.body.isEmpty) return [];
    final List<dynamic> driversJson = jsonDecode(_decodeBodyBytes(driverResp));
    final drivers =
        driversJson.map((e) => DriverInformation.fromJson(e)).toList();
    if (drivers.isEmpty) return [];

    final Map<int, OffenseInformation> merged = {};
    for (final d in drivers) {
      final did = d.driverId;
      if (did == null) continue;
      final offensesResp = await apiClient.invokeAPI(
        '/api/offenses/driver/$did',
        'GET',
        [QueryParam('page', '$page'), QueryParam('size', '$size')],
        null,
        headerParams,
        {},
        null,
        ['bearerAuth'],
      );
      if (offensesResp.statusCode >= 400 || offensesResp.body.isEmpty) {
        continue;
      }
      final List<dynamic> oJson = jsonDecode(_decodeBodyBytes(offensesResp));
      for (final oj in oJson) {
        final oi = OffenseInformation.fromJson(oj);
        if (oi.offenseId != null) {
          merged[oi.offenseId!] = oi;
        }
      }
    }
    return merged.values.toList();
  }

  /// GET /api/offenses/driver/{driverId} - fetch offenses by driver ID.
  Future<List<OffenseInformation>> apiOffensesDriverDriverIdGet({
    required int driverId,
    int page = 1,
    int size = 20,
  }) async {
    final path = '/api/offenses/driver/$driverId';
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
      if (response.statusCode == 204) return [];
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => OffenseInformation.fromJson(json)).toList();
  }

  /// GET /api/offenses/vehicle/{vehicleId} - fetch offenses by vehicle ID.
  Future<List<OffenseInformation>> apiOffensesVehicleVehicleIdGet({
    required int vehicleId,
    int page = 1,
    int size = 20,
  }) async {
    final path = '/api/offenses/vehicle/$vehicleId';
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
      if (response.statusCode == 204) return [];
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => OffenseInformation.fromJson(json)).toList();
  }

  /// GET /api/offenses/search/status - search offenses by process status.
  Future<List<OffenseInformation>> apiOffensesSearchStatusGet({
    required String processStatus,
    int page = 1,
    int size = 20,
  }) async {
    const path = '/api/offenses/search/status';
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [
        QueryParam('status', processStatus),
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
      if (response.statusCode == 204) return [];
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => OffenseInformation.fromJson(json)).toList();
  }

  /// GET /api/offenses/search/number - search offenses by offense number.
  Future<List<OffenseInformation>> apiOffensesSearchNumberGet({
    required String offenseNumber,
    int page = 1,
    int size = 20,
  }) async {
    const path = '/api/offenses/search/number';
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [
        QueryParam('offenseNumber', offenseNumber),
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
      if (response.statusCode == 204) return [];
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => OffenseInformation.fromJson(json)).toList();
  }

  /// GET /api/offenses/search/location?offenseLocation=...
  Future<List<OffenseInformation>> apiOffensesSearchLocationGet({
    required String offenseLocation,
    int page = 1,
    int size = 20,
  }) async {
    const path = '/api/offenses/search/location';
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [
        QueryParam('offenseLocation', offenseLocation),
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
      if (response.statusCode == 204) return [];
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => OffenseInformation.fromJson(json)).toList();
  }

  /// GET /api/offenses/search/province?offenseProvince=...
  Future<List<OffenseInformation>> apiOffensesSearchProvinceGet({
    required String offenseProvince,
    int page = 1,
    int size = 20,
  }) async {
    const path = '/api/offenses/search/province';
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [
        QueryParam('offenseProvince', offenseProvince),
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
      if (response.statusCode == 204) return [];
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => OffenseInformation.fromJson(json)).toList();
  }

  /// GET /api/offenses/search/city?offenseCity=...
  Future<List<OffenseInformation>> apiOffensesSearchCityGet({
    required String offenseCity,
    int page = 1,
    int size = 20,
  }) async {
    const path = '/api/offenses/search/city';
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [
        QueryParam('offenseCity', offenseCity),
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
      if (response.statusCode == 204) return [];
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => OffenseInformation.fromJson(json)).toList();
  }

  /// GET /api/offenses/search/notification?notificationStatus=...
  Future<List<OffenseInformation>> apiOffensesSearchNotificationGet({
    required String notificationStatus,
    int page = 1,
    int size = 20,
  }) async {
    const path = '/api/offenses/search/notification';
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [
        QueryParam('notificationStatus', notificationStatus),
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
      if (response.statusCode == 204) return [];
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => OffenseInformation.fromJson(json)).toList();
  }

  /// GET /api/offenses/search/agency?enforcementAgency=...
  Future<List<OffenseInformation>> apiOffensesSearchAgencyGet({
    required String enforcementAgency,
    int page = 1,
    int size = 20,
  }) async {
    const path = '/api/offenses/search/agency';
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [
        QueryParam('enforcementAgency', enforcementAgency),
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
      if (response.statusCode == 204) return [];
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => OffenseInformation.fromJson(json)).toList();
  }

  /// GET /api/offenses/search/fine-range?minAmount=&maxAmount=&page=&size=
  Future<List<OffenseInformation>> apiOffensesSearchFineRangeGet({
    required double minAmount,
    required double maxAmount,
    int page = 1,
    int size = 20,
  }) async {
    const path = '/api/offenses/search/fine-range';
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [
        QueryParam('minAmount', '$minAmount'),
        QueryParam('maxAmount', '$maxAmount'),
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
      if (response.statusCode == 204) return [];
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => OffenseInformation.fromJson(json)).toList();
  }

  /// GET /api/offenses/by-license-plate - search offenses by license plate.
  Future<List<OffenseInformation>> apiOffensesByLicensePlateGet({
    required String query,
    int page = 1,
    int size = 10,
  }) async {
    if (query.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('query'));
    }
    final headerParams = await _getHeaders();
    // Step1: exact search vehicle by license plate
    final vResp = await apiClient.invokeAPI(
      '/api/vehicles/search/license',
      'GET',
      [QueryParam('licensePlate', query)],
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
    if (vResp.statusCode == 404 || vResp.body.isEmpty) {
      return [];
    }
    if (vResp.statusCode >= 400) {
      throw ApiException(vResp.statusCode, _errorMessageOrHttpStatus(vResp));
    }
    final vehicle = VehicleInformation.fromJson(
        jsonDecode(_decodeBodyBytes(vResp)) as Map<String, dynamic>);
    if (vehicle.vehicleId == null) return [];

    // Step2: offenses by vehicle id
    final oResp = await apiClient.invokeAPI(
      '/api/offenses/vehicle/${vehicle.vehicleId}',
      'GET',
      [QueryParam('page', '$page'), QueryParam('size', '$size')],
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
    if (oResp.statusCode >= 400) {
      throw ApiException(oResp.statusCode, _errorMessageOrHttpStatus(oResp));
    }
    if (oResp.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(oResp));
    return jsonList.map((json) => OffenseInformation.fromJson(json)).toList();
  }

}
