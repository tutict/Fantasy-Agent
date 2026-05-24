import 'dart:convert';
import 'package:final_assignment_front/features/model/driver_information.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:final_assignment_front/utils/services/api_client.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:final_assignment_front/utils/services/auth_token_store.dart';

/// Shared default ApiClient instance.

final ApiClient defaultApiClient = ApiClient();

class DriverInformationControllerApi {
  final ApiClient apiClient;

  /// Allows injecting a custom ApiClient and otherwise uses the shared default instance.


  DriverInformationControllerApi([ApiClient? apiClient])
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

  /// POST /api/drivers - create a driver record.
  Future<void> apiDriversPost({
    required DriverInformation driverInformation,
    required String idempotencyKey,
  }) async {
    const path = '/api/drivers';
    final response = await apiClient.invokeAPI(
      path,
      'POST',
      [],
      driverInformation.toJson(),
      await _getHeaders(idempotencyKey: idempotencyKey),
      {},
      'application/json',
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      if (response.statusCode == 409) {
        throw ApiException(409, localizeDuplicateRequest(idempotencyKey));
      }
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
  }

  /// GET /api/drivers/{driverId} - fetch a driver by ID.
  Future<DriverInformation?> apiDriversDriverIdGet({
    required int driverId,
  }) async {
    final path = '/api/drivers/$driverId';
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
    return DriverInformation.fromJson(data);
  }

  Future<DriverInformation?> apiDriversMeGet() async {
    const path = '/api/drivers/me';
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
    if (response.statusCode == 404) {
      return null;
    }
    if (response.statusCode >= 400) {
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return null;
    final data = apiClient.deserialize(
        _decodeBodyBytes(response), 'Map<String, dynamic>');
    return DriverInformation.fromJson(data);
  }

  /// GET /api/drivers - fetch all driver records.
  Future<List<DriverInformation>> apiDriversGet({
    int page = 1,
    int size = 20,
  }) async {
    const path = '/api/drivers';
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [
        QueryParam('page', page.toString()),
        QueryParam('size', size.toString()),
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
    return jsonList.map((json) => DriverInformation.fromJson(json)).toList();
  }

  Future<List<DriverInformation>> apiDriversSearchGet({
    required String query,
    int page = 1,
    int size = 20,
  }) async {
    if (query.trim().isEmpty) {
      return apiDriversGet(page: page, size: size);
    }
    const path = '/api/drivers/search';
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [
        QueryParam('keywords', query.trim()),
        QueryParam('page', page.toString()),
        QueryParam('size', size.toString()),
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
    return jsonList.map((json) => DriverInformation.fromJson(json)).toList();
  }

  /// PUT /api/drivers/{driverId}/name - update the driver's name.
  Future<void> apiDriversDriverIdNamePut({
    required int driverId,
    required String name,
    required String idempotencyKey,
  }) async {
    final path = '/api/drivers/$driverId/name';
    final response = await apiClient.invokeAPI(
      path,
      'PUT',
      [],
      jsonEncode(name),
      // String directly encoded as JSON
      await _getHeaders(idempotencyKey: idempotencyKey),
      {},
      'application/json',
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      if (response.statusCode == 404) {
        throw ApiException(
          404,
          localizeEntityNotFoundWithId('api.entity.driver'.tr, driverId),
        );
      } else if (response.statusCode == 409) {
        throw ApiException(409, localizeDuplicateRequest(idempotencyKey));
      }
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
  }

  /// PUT /api/drivers/{driverId}/contactNumber - update the driver's contact number.
  Future<void> apiDriversDriverIdContactNumberPut({
    required int driverId,
    required String contactNumber,
    required String idempotencyKey,
  }) async {
    final path = '/api/drivers/$driverId/contactNumber';
    final response = await apiClient.invokeAPI(
      path,
      'PUT',
      [],
      jsonEncode(contactNumber),
      // String directly encoded as JSON
      await _getHeaders(idempotencyKey: idempotencyKey),
      {},
      'application/json',
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      if (response.statusCode == 404) {
        throw ApiException(
          404,
          localizeEntityNotFoundWithId('api.entity.driver'.tr, driverId),
        );
      } else if (response.statusCode == 409) {
        throw ApiException(409, localizeDuplicateRequest(idempotencyKey));
      }
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
  }

  /// PUT /api/drivers/{driverId}/idCardNumber - update the driver's ID card number.
  Future<void> apiDriversDriverIdIdCardNumberPut({
    required int driverId,
    required String idCardNumber,
    required String idempotencyKey,
  }) async {
    final path = '/api/drivers/$driverId/idCardNumber';
    final response = await apiClient.invokeAPI(
      path,
      'PUT',
      [],
      jsonEncode(idCardNumber),
      // String directly encoded as JSON
      await _getHeaders(idempotencyKey: idempotencyKey),
      {},
      'application/json',
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      if (response.statusCode == 404) {
        throw ApiException(
          404,
          localizeEntityNotFoundWithId('api.entity.driver'.tr, driverId),
        );
      } else if (response.statusCode == 409) {
        throw ApiException(409, localizeDuplicateRequest(idempotencyKey));
      }
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
  }

  /// PUT /api/drivers/{driverId} - update the full driver record.
  Future<void> apiDriversDriverIdPut({
    required int driverId,
    required DriverInformation driverInformation,
    required String idempotencyKey,
  }) async {
    final path = '/api/drivers/$driverId';
    final response = await apiClient.invokeAPI(
      path,
      'PUT',
      [],
      driverInformation.toJson(),
      await _getHeaders(idempotencyKey: idempotencyKey),
      {},
      'application/json',
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      if (response.statusCode == 404) {
        throw ApiException(
          404,
          localizeEntityNotFoundWithId('api.entity.driver'.tr, driverId),
        );
      } else if (response.statusCode == 409) {
        throw ApiException(409, localizeDuplicateRequest(idempotencyKey));
      }
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
  }

  Future<DriverInformation?> apiDriversMePut({
    required DriverInformation driverInformation,
    String? idempotencyKey,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/drivers/me',
      'PUT',
      [],
      driverInformation.toJson(),
      await _getHeaders(idempotencyKey: idempotencyKey),
      {},
      'application/json',
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    if (response.body.isEmpty) return null;
    final data = apiClient.deserialize(
        _decodeBodyBytes(response), 'Map<String, dynamic>');
    return DriverInformation.fromJson(data);
  }

  /// DELETE /api/drivers/{driverId} - delete a driver record (admin only).

  Future<void> apiDriversDriverIdDelete({
    required int driverId,
  }) async {
    final path = '/api/drivers/$driverId';
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
          localizeEntityNotFoundWithId('api.entity.driver'.tr, driverId),
        );
      } else if (response.statusCode == 403) {
        throw ApiException(
            403, localizeAdminOnlyDelete('api.resource.drivers'.tr));
      }
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
  }

  /// GET /api/drivers/by-id-card - search drivers by ID card number.
  Future<List<DriverInformation>> apiDriversByIdCardGet({
    required String query,
    int page = 1,
    int size = 10,
  }) async {
    if (query.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('query'));
    }
    const path = '/api/drivers/search/id-card';
    final queryParams = [
      QueryParam('keywords', query),
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
    return jsonList.map((json) => DriverInformation.fromJson(json)).toList();
  }

  /// GET /api/drivers/by-license-number - search drivers by license number.
  Future<List<DriverInformation>> apiDriversByLicenseNumberGet({
    required String query,
    int page = 1,
    int size = 10,
  }) async {
    if (query.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('query'));
    }
    const path = '/api/drivers/search/license';
    final queryParams = [
      QueryParam('keywords', query),
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
    return jsonList.map((json) => DriverInformation.fromJson(json)).toList();
  }

  /// GET /api/drivers/by-name - search drivers by name.
  Future<List<DriverInformation>> apiDriversByNameGet({
    required String query,
    int page = 1,
    int size = 10,
  }) async {
    if (query.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('query'));
    }
    const path = '/api/drivers/search/name';
    final queryParams = [
      QueryParam('keywords', query),
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
    return jsonList.map((json) => DriverInformation.fromJson(json)).toList();
  }

}
