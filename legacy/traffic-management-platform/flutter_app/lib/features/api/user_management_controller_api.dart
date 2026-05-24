import 'dart:convert';
import 'package:final_assignment_front/features/model/user_management.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:final_assignment_front/utils/services/api_client.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';

final ApiClient defaultApiClient = ApiClient();

class UserManagementControllerApi {
  final ApiClient apiClient;

  UserManagementControllerApi([ApiClient? apiClient])
      : apiClient = apiClient ?? defaultApiClient;

  // Loads the JWT token into the ApiClient.
  Future<void> initializeWithJwt() async {
    final jwtToken = (await AuthTokenStore.instance.getJwtToken());
    if (jwtToken == null) {
      throw Exception('api.error.notAuthenticated'.tr);
    }
    apiClient.setJwtToken(jwtToken);
  }

  // Decodes the response body.
  String _decodeBodyBytes(http.Response response) => response.body;

  String _errorMessageOrUnknown(http.Response response) {
    return response.body.isNotEmpty
        ? _decodeBodyBytes(response)
        : localizeUnknownApiError();
  }

  // Builds common request headers.
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

// --- GET /api/users ---
  Future<http.Response> apiUsersGetWithHttpInfo({
    int page = 1,
    int size = 20,
  }) async {
    final path = "/api/users".replaceAll("{format}", "json");
    final headerParams = await _getHeaders();

    return await apiClient.invokeAPI(
      path,
      'GET',
      [QueryParam('page', '$page'), QueryParam('size', '$size')],
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
  }

  Future<List<UserManagement>> apiUsersGet({
    int page = 1,
    int size = 20,
  }) async {
    try {
      final response = await apiUsersGetWithHttpInfo(page: page, size: size);
      debugPrint('Users get response status: ${response.statusCode}');
      debugPrint('Users get response body: ${response.body}');

      if (response.statusCode >= 400) {
        final errorMessage = _errorMessageOrUnknown(response);
        throw ApiException(response.statusCode, errorMessage);
      } else if (response.body.isNotEmpty) {
        final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
        return jsonList.map((json) => UserManagement.fromJson(json)).toList();
      } else {
        return [];
      }
    } catch (e) {
      debugPrint('Users get error: $e');
      rethrow;
    }
  }

  // --- GET /api/users/me ---
  Future<http.Response> apiUsersMeGetWithHttpInfo() async {
    final path = "/api/users/me".replaceAll("{format}", "json");
    final headerParams = await _getHeaders();

    return await apiClient.invokeAPI(
      path,
      'GET',
      [],
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
  }

  Future<UserManagement?> apiUsersMeGet() async {
    try {
      final response = await apiUsersMeGetWithHttpInfo();
      debugPrint('Users me get response status: ${response.statusCode}');
      debugPrint('Users me get response body: ${response.body}');

      if (response.statusCode >= 400) {
        final errorMessage = _errorMessageOrUnknown(response);
        throw ApiException(response.statusCode, errorMessage);
      } else if (response.body.isNotEmpty) {
        return UserManagement.fromJson(jsonDecode(_decodeBodyBytes(response)));
      } else {
        return null;
      }
    } catch (e) {
      debugPrint('Users me get error: $e');
      rethrow;
    }
  }

  // --- PUT /api/users/me ---
  Future<UserManagement?> apiUsersMePut({
    required UserManagement userManagement,
  }) async {
    try {
      final response = await apiClient.invokeAPI(
        '/api/users/me',
        'PUT',
        [],
        userManagement.toJson(),
        await _getHeaders(),
        {},
        'application/json',
        ['bearerAuth'],
      );

      debugPrint('Users me put response status: ${response.statusCode}');
      debugPrint('Users me put response body: ${response.body}');

      if (response.statusCode >= 400) {
        final errorMessage = _errorMessageOrUnknown(response);
        throw ApiException(response.statusCode, errorMessage);
      } else if (response.body.isNotEmpty) {
        return UserManagement.fromJson(jsonDecode(_decodeBodyBytes(response)));
      } else {
        return null;
      }
    } catch (e) {
      debugPrint('Users me put error: $e');
      rethrow;
    }
  }

  // --- PUT /api/users/me/password ---
  Future<void> apiUsersMePasswordPut({
    required String currentPassword,
    required String newPassword,
    required String idempotencyKey,
  }) async {
    if (currentPassword.trim().isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('currentPassword'));
    }
    if (newPassword.trim().isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('newPassword'));
    }
    if (idempotencyKey.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('idempotencyKey'));
    }

    final response = await apiClient.invokeAPI(
      '/api/users/me/password',
      'PUT',
      [],
      {
        'currentPassword': currentPassword.trim(),
        'newPassword': newPassword.trim(),
      },
      await _getHeaders(idempotencyKey: idempotencyKey),
      {},
      'application/json',
      ['bearerAuth'],
    );

    if (response.statusCode >= 400) {
      final errorMessage = _errorMessageOrUnknown(response);
      throw ApiException(response.statusCode, errorMessage);
    }
  }

  // --- POST /api/users ---
  Future<http.Response> apiUsersPostWithHttpInfo({
    required UserManagement userManagement,
    required String idempotencyKey,
  }) async {
    if (idempotencyKey.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('idempotencyKey'));
    }

    final path = "/api/users".replaceAll("{format}", "json");
    final headerParams = await _getHeaders(idempotencyKey: idempotencyKey);

    return await apiClient.invokeAPI(
      path,
      'POST',
      [],
      userManagement.toJson(),
      headerParams,
      {},
      'application/json',
      ['bearerAuth'],
    );
  }

  Future<UserManagement?> apiUsersPost({
    required UserManagement userManagement,
    required String idempotencyKey,
  }) async {
    try {
      final response = await apiUsersPostWithHttpInfo(
        userManagement: userManagement,
        idempotencyKey: idempotencyKey,
      );
      debugPrint('Users post response status: ${response.statusCode}');
      debugPrint('Users post response body: ${response.body}');

      if (response.statusCode >= 400) {
        final errorMessage = _errorMessageOrUnknown(response);
        throw ApiException(response.statusCode, errorMessage);
      } else if (response.body.isNotEmpty) {
        return UserManagement.fromJson(jsonDecode(_decodeBodyBytes(response)));
      } else if (response.statusCode == 201) {
        return null; // 201 Created with an empty response body.
      } else {
        throw ApiException(
            response.statusCode, localizeEmptyResponseApiError());
      }
    } catch (e) {
      debugPrint('Users post error: $e');
      rethrow;
    }
  }

  // --- GET /api/users/search/status?status=&page=&size= ---
  Future<http.Response> apiUsersSearchStatusGetWithHttpInfo({
    required String status,
    int page = 1,
    int size = 20,
  }) async {
    if (status.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('status'));
    }
    final path = "/api/users/search/status".replaceAll("{format}", "json");
    final headerParams = await _getHeaders();
    final queryParams = [
      QueryParam("status", status),
      QueryParam("page", page.toString()),
      QueryParam("size", size.toString()),
    ];
    return await apiClient.invokeAPI(
      path,
      'GET',
      queryParams,
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
  }

  // --- GET /api/users/search/department?department=&page=&size= ---
  Future<http.Response> apiUsersSearchDepartmentGetWithHttpInfo({
    required String department,
    int page = 1,
    int size = 20,
  }) async {
    if (department.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('department'));
    }
    final path = "/api/users/search/department".replaceAll("{format}", "json");
    final headerParams = await _getHeaders();
    final queryParams = [
      QueryParam("department", department),
      QueryParam("page", page.toString()),
      QueryParam("size", size.toString()),
    ];
    return await apiClient.invokeAPI(
      path,
      'GET',
      queryParams,
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
  }

  Future<List<UserManagement>> apiUsersSearchDepartmentGet({
    required String department,
    int page = 1,
    int size = 20,
  }) async {
    try {
      final response = await apiUsersSearchDepartmentGetWithHttpInfo(
          department: department, page: page, size: size);
      debugPrint(
          'Users search department response status: ${response.statusCode}');
      debugPrint('Users search department response body: ${response.body}');

      if (response.statusCode >= 400) {
        final errorMessage = _errorMessageOrUnknown(response);
        throw ApiException(response.statusCode, errorMessage);
      } else if (response.body.isNotEmpty) {
        final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
        return jsonList.map((json) => UserManagement.fromJson(json)).toList();
      } else {
        return [];
      }
    } catch (e) {
      debugPrint('Users search department error: $e');
      rethrow;
    }
  }

  // --- GET /api/users/search/username/prefix?username=&page=&size= ---
  Future<List<UserManagement>> apiUsersSearchUsernamePrefixGet({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/users/search/username/prefix',
      'GET',
      [
        QueryParam('username', username),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      final errorMessage = _errorMessageOrUnknown(response);
      throw ApiException(response.statusCode, errorMessage);
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => UserManagement.fromJson(json)).toList();
  }

  // --- GET /api/users/search/username/fuzzy?username=&page=&size= ---
  Future<List<UserManagement>> apiUsersSearchUsernameFuzzyGet({
    required String username,
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/users/search/username/fuzzy',
      'GET',
      [
        QueryParam('username', username),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      final errorMessage = _errorMessageOrUnknown(response);
      throw ApiException(response.statusCode, errorMessage);
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => UserManagement.fromJson(json)).toList();
  }

  // --- GET /api/users/search/real-name/prefix?realName=&page=&size= ---
  Future<List<UserManagement>> apiUsersSearchRealNamePrefixGet({
    required String realName,
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/users/search/real-name/prefix',
      'GET',
      [
        QueryParam('realName', realName),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      final errorMessage = _errorMessageOrUnknown(response);
      throw ApiException(response.statusCode, errorMessage);
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => UserManagement.fromJson(json)).toList();
  }

  // --- GET /api/users/search/real-name/fuzzy?realName=&page=&size= ---
  Future<List<UserManagement>> apiUsersSearchRealNameFuzzyGet({
    required String realName,
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/users/search/real-name/fuzzy',
      'GET',
      [
        QueryParam('realName', realName),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      final errorMessage = _errorMessageOrUnknown(response);
      throw ApiException(response.statusCode, errorMessage);
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => UserManagement.fromJson(json)).toList();
  }

  // --- GET /api/users/search/id-card?idCardNumber=&page=&size= ---
  Future<List<UserManagement>> apiUsersSearchIdCardGet({
    required String idCardNumber,
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/users/search/id-card',
      'GET',
      [
        QueryParam('idCardNumber', idCardNumber),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      final errorMessage = _errorMessageOrUnknown(response);
      throw ApiException(response.statusCode, errorMessage);
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => UserManagement.fromJson(json)).toList();
  }

  // --- GET /api/users/search/contact?contactNumber=&page=&size= ---
  Future<List<UserManagement>> apiUsersSearchContactGet({
    required String contactNumber,
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/users/search/contact',
      'GET',
      [
        QueryParam('contactNumber', contactNumber),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      final errorMessage = _errorMessageOrUnknown(response);
      throw ApiException(response.statusCode, errorMessage);
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => UserManagement.fromJson(json)).toList();
  }

  Future<List<UserManagement>> apiUsersSearchEmailGet({
    required String email,
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/users/search/email',
      'GET',
      [
        QueryParam('email', email),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      final errorMessage = _errorMessageOrUnknown(response);
      throw ApiException(response.statusCode, errorMessage);
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => UserManagement.fromJson(json)).toList();
  }

  // --- POST /api/users/{userId}/roles --- bind user role
  Future<http.Response> apiUsersUserIdRolesPostWithHttpInfo({
    required int userId,
    required Map<String, dynamic> body, // expects SysUserRoleModel.toJson()
    required String idempotencyKey,
  }) async {
    if (idempotencyKey.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('idempotencyKey'));
    }
    final path = "/api/users/$userId/roles".replaceAll("{format}", "json");
    final headerParams = await _getHeaders(idempotencyKey: idempotencyKey);
    return await apiClient.invokeAPI(
      path,
      'POST',
      [],
      body,
      headerParams,
      {},
      'application/json',
      ['bearerAuth'],
    );
  }

  Future<Map<String, dynamic>?> apiUsersUserIdRolesPost({
    required int userId,
    required Map<String, dynamic> body,
    required String idempotencyKey,
  }) async {
    final response = await apiUsersUserIdRolesPostWithHttpInfo(
      userId: userId,
      body: body,
      idempotencyKey: idempotencyKey,
    );
    if (response.statusCode >= 400) {
      final errorMessage = _errorMessageOrUnknown(response);
      throw ApiException(response.statusCode, errorMessage);
    }
    return response.body.isNotEmpty
        ? jsonDecode(_decodeBodyBytes(response)) as Map<String, dynamic>
        : null;
  }

  // --- DELETE /api/users/roles/{relationId} ---
  Future<void> apiUsersRolesRelationIdDelete({required int relationId}) async {
    final path = "/api/users/roles/$relationId".replaceAll("{format}", "json");
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
      final errorMessage = _errorMessageOrUnknown(response);
      throw ApiException(response.statusCode, errorMessage);
    }
  }

  // --- GET /api/users/{userId}/roles?page=&size= ---
  Future<List<Map<String, dynamic>>> apiUsersUserIdRolesGet({
    required int userId,
    int page = 1,
    int size = 20,
  }) async {
    final path = "/api/users/$userId/roles".replaceAll("{format}", "json");
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [QueryParam("page", "$page"), QueryParam("size", "$size")],
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      final errorMessage = _errorMessageOrUnknown(response);
      throw ApiException(response.statusCode, errorMessage);
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.cast<Map<String, dynamic>>();
  }

  // --- PUT /api/users/role-bindings/{relationId} ---
  Future<Map<String, dynamic>?> apiUsersRoleBindingsRelationIdPut({
    required int relationId,
    required Map<String, dynamic> body,
    required String idempotencyKey,
  }) async {
    if (idempotencyKey.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('idempotencyKey'));
    }
    final path =
        "/api/users/role-bindings/$relationId".replaceAll("{format}", "json");
    final headerParams = await _getHeaders(idempotencyKey: idempotencyKey);
    final response = await apiClient.invokeAPI(
      path,
      'PUT',
      [],
      body,
      headerParams,
      {},
      'application/json',
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      final errorMessage = _errorMessageOrUnknown(response);
      throw ApiException(response.statusCode, errorMessage);
    }
    return response.body.isNotEmpty
        ? jsonDecode(_decodeBodyBytes(response)) as Map<String, dynamic>
        : null;
  }

  // --- GET /api/users/role-bindings/{relationId} ---
  Future<Map<String, dynamic>?> apiUsersRoleBindingsRelationIdGet({
    required int relationId,
  }) async {
    final path =
        "/api/users/role-bindings/$relationId".replaceAll("{format}", "json");
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
      final errorMessage = _errorMessageOrUnknown(response);
      throw ApiException(response.statusCode, errorMessage);
    }
    return response.body.isNotEmpty
        ? jsonDecode(_decodeBodyBytes(response)) as Map<String, dynamic>
        : null;
  }

  // --- GET /api/users/role-bindings?page=&size= ---
  Future<List<Map<String, dynamic>>> apiUsersRoleBindingsGet({
    int page = 1,
    int size = 20,
  }) async {
    final path = "/api/users/role-bindings".replaceAll("{format}", "json");
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [QueryParam("page", "$page"), QueryParam("size", "$size")],
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      final errorMessage = _errorMessageOrUnknown(response);
      throw ApiException(response.statusCode, errorMessage);
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.cast<Map<String, dynamic>>();
  }

  // --- GET /api/users/role-bindings/by-role/{roleId}?page=&size= ---
  Future<List<Map<String, dynamic>>> apiUsersRoleBindingsByRoleRoleIdGet({
    required int roleId,
    int page = 1,
    int size = 20,
  }) async {
    final path = "/api/users/role-bindings/by-role/$roleId"
        .replaceAll("{format}", "json");
    final headerParams = await _getHeaders();
    final response = await apiClient.invokeAPI(
      path,
      'GET',
      [QueryParam("page", "$page"), QueryParam("size", "$size")],
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      final errorMessage = _errorMessageOrUnknown(response);
      throw ApiException(response.statusCode, errorMessage);
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.cast<Map<String, dynamic>>();
  }

  // --- GET /api/users/search/department/prefix?department=&page=&size= ---
  Future<List<UserManagement>> apiUsersSearchDepartmentPrefixGet({
    required String department,
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/users/search/department/prefix',
      'GET',
      [
        QueryParam('department', department),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      final errorMessage = _errorMessageOrUnknown(response);
      throw ApiException(response.statusCode, errorMessage);
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => UserManagement.fromJson(json)).toList();
  }

  // --- GET /api/users/search/employee-number?employeeNumber=&page=&size= ---
  Future<List<UserManagement>> apiUsersSearchEmployeeNumberGet({
    required String employeeNumber,
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/users/search/employee-number',
      'GET',
      [
        QueryParam('employeeNumber', employeeNumber),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      final errorMessage = _errorMessageOrUnknown(response);
      throw ApiException(response.statusCode, errorMessage);
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => UserManagement.fromJson(json)).toList();
  }

  // --- GET /api/users/search/last-login-range?startTime=&endTime=&page=&size= ---
  Future<List<UserManagement>> apiUsersSearchLastLoginRangeGet({
    required String startTime,
    required String endTime,
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/users/search/last-login-range',
      'GET',
      [
        QueryParam('startTime', startTime),
        QueryParam('endTime', endTime),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      final errorMessage = _errorMessageOrUnknown(response);
      throw ApiException(response.statusCode, errorMessage);
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.map((json) => UserManagement.fromJson(json)).toList();
  }

  // --- GET /api/users/role-bindings/search?userId=&roleId=&page=&size= ---
  Future<List<Map<String, dynamic>>> apiUsersRoleBindingsSearchGet({
    required int userId,
    required int roleId,
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/users/role-bindings/search',
      'GET',
      [
        QueryParam('userId', '$userId'),
        QueryParam('roleId', '$roleId'),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      null,
      await _getHeaders(),
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode >= 400) {
      final errorMessage = _errorMessageOrUnknown(response);
      throw ApiException(response.statusCode, errorMessage);
    }
    if (response.body.isEmpty) return [];
    final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
    return jsonList.cast<Map<String, dynamic>>();
  }

  Future<List<UserManagement>> apiUsersSearchStatusGet({
    required String status,
    int page = 1,
    int size = 20,
  }) async {
    try {
      final response = await apiUsersSearchStatusGetWithHttpInfo(
          status: status, page: page, size: size);
      debugPrint('Users search status response status: ${response.statusCode}');
      debugPrint('Users search status response body: ${response.body}');

      if (response.statusCode >= 400) {
        final errorMessage = _errorMessageOrUnknown(response);
        throw ApiException(response.statusCode, errorMessage);
      } else if (response.body.isNotEmpty) {
        final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
        return jsonList.map((json) => UserManagement.fromJson(json)).toList();
      } else {
        return [];
      }
    } catch (e) {
      debugPrint('Users search status error: $e');
      rethrow;
    }
  }

  // removed: /api/users/type/{userType} (not provided by backend controllers)

  // --- DELETE /api/users/{userId} ---
  Future<http.Response> apiUsersUserIdDeleteWithHttpInfo({
    required String userId,
  }) async {
    if (userId.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('userId'));
    }

    final path = "/api/users/$userId".replaceAll("{format}", "json");
    final headerParams = await _getHeaders();

    return await apiClient.invokeAPI(
      path,
      'DELETE',
      [],
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
  }

  Future<void> apiUsersUserIdDelete({
    required String userId,
  }) async {
    try {
      final response = await apiUsersUserIdDeleteWithHttpInfo(userId: userId);
      debugPrint('Users delete response status: ${response.statusCode}');
      debugPrint('Users delete response body: ${response.body}');

      if (response.statusCode >= 400) {
        final errorMessage = _errorMessageOrUnknown(response);
        throw ApiException(response.statusCode, errorMessage);
      }
    } catch (e) {
      debugPrint('Users delete error: $e');
      rethrow;
    }
  }

  // --- GET /api/users/{userId} ---
  Future<http.Response> apiUsersUserIdGetWithHttpInfo({
    required String userId,
  }) async {
    if (userId.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('userId'));
    }

    final path = "/api/users/$userId".replaceAll("{format}", "json");
    final headerParams = await _getHeaders();

    return await apiClient.invokeAPI(
      path,
      'GET',
      [],
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
  }

  Future<UserManagement?> apiUsersUserIdGet({
    required String userId,
  }) async {
    try {
      final response = await apiUsersUserIdGetWithHttpInfo(userId: userId);
      debugPrint('Users userId get response status: ${response.statusCode}');
      debugPrint('Users userId get response body: ${response.body}');

      if (response.statusCode >= 400) {
        final errorMessage = _errorMessageOrUnknown(response);
        throw ApiException(response.statusCode, errorMessage);
      } else if (response.body.isNotEmpty) {
        return UserManagement.fromJson(jsonDecode(_decodeBodyBytes(response)));
      } else {
        return null;
      }
    } catch (e) {
      debugPrint('Users userId get error: $e');
      rethrow;
    }
  }

  // --- PUT /api/users/{userId} ---
  Future<http.Response> apiUsersUserIdPutWithHttpInfo({
    required String userId,
    required UserManagement userManagement,
    required String idempotencyKey,
  }) async {
    if (userId.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('userId'));
    }
    if (idempotencyKey.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('idempotencyKey'));
    }

    final path = "/api/users/$userId".replaceAll("{format}", "json");
    final headerParams = await _getHeaders(idempotencyKey: idempotencyKey);

    return await apiClient.invokeAPI(
      path,
      'PUT',
      [],
      userManagement.toJson(),
      headerParams,
      {},
      'application/json',
      ['bearerAuth'],
    );
  }

  Future<void> apiUsersUserIdPut({
    required String userId,
    required UserManagement userManagement,
    required String idempotencyKey,
  }) async {
    try {
      final response = await apiUsersUserIdPutWithHttpInfo(
        userId: userId,
        userManagement: userManagement,
        idempotencyKey: idempotencyKey,
      );
      debugPrint('Users userId put response status: ${response.statusCode}');
      debugPrint('Users userId put response body: ${response.body}');

      if (response.statusCode >= 400) {
        final errorMessage = _errorMessageOrUnknown(response);
        throw ApiException(response.statusCode, errorMessage);
      }
    } catch (e) {
      debugPrint('Users userId put error: $e');
      rethrow;
    }
  }

  // --- DELETE /api/users/username/{username} ---
  Future<http.Response> apiUsersUsernameUsernameDeleteWithHttpInfo({
    required String username,
  }) async {
    if (username.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('username'));
    }

    // removed endpoint
    throw ApiException(
      410,
      localizeRemovedEndpoint('DELETE /api/users/username/{username}'),
    );
  }

  Future<void> apiUsersUsernameUsernameDelete({
    required String username,
  }) async {
    // removed endpoint
    throw ApiException(
      410,
      localizeRemovedEndpoint('DELETE /api/users/username/{username}'),
    );
  }

  // --- GET /api/users/username/{username} ---
  Future<http.Response> apiUsersUsernameUsernameGetWithHttpInfo({
    required String username,
  }) async {
    if (username.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('username'));
    }

    // replaced by /api/users/search/username/{username}
    return await apiUsersSearchUsernameGetWithHttpInfo(username: username);
  }

  Future<UserManagement?> apiUsersUsernameUsernameGet({
    required String username,
  }) async {
    return await apiUsersSearchUsernameGet(username: username);
  }

  // --- GET /api/users/search/username/{username} ---
  Future<http.Response> apiUsersSearchUsernameGetWithHttpInfo({
    required String username,
  }) async {
    if (username.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('username'));
    }
    final path = "/api/users/search/username/${Uri.encodeComponent(username)}"
        .replaceAll("{format}", "json");
    final headerParams = await _getHeaders();
    return await apiClient.invokeAPI(
      path,
      'GET',
      [],
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
  }

  Future<UserManagement?> apiUsersSearchUsernameGet({
    required String username,
  }) async {
    try {
      final response =
          await apiUsersSearchUsernameGetWithHttpInfo(username: username);
      debugPrint(
          'Users search username response status: ${response.statusCode}');
      debugPrint('Users search username response body: ${response.body}');

      if (response.statusCode >= 400) {
        final errorMessage = _errorMessageOrUnknown(response);
        throw ApiException(response.statusCode, errorMessage);
      } else if (response.body.isNotEmpty) {
        return UserManagement.fromJson(jsonDecode(_decodeBodyBytes(response)));
      } else {
        return null;
      }
    } catch (e) {
      debugPrint('Users search username error: $e');
      rethrow;
    }
  }

  // --- GET /api/users/autocomplete/usernames ---
  Future<http.Response> apiUsersAutocompleteUsernamesGetWithHttpInfo({
    required String prefix,
  }) async {
    if (prefix.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('prefix'));
    }

    final path =
        "/api/users/autocomplete/usernames".replaceAll("{format}", "json");
    final queryParams = [QueryParam("prefix", prefix)];
    final headerParams = await _getHeaders();

    return await apiClient.invokeAPI(
      path,
      'GET',
      queryParams,
      null,
      headerParams,
      {},
      null,
      ['bearerAuth'],
    );
  }

  Future<List<String>> apiUsersAutocompleteUsernamesGet({
    required String prefix,
  }) async {
    try {
      final response =
          await apiUsersAutocompleteUsernamesGetWithHttpInfo(prefix: prefix);
      debugPrint(
          'Users autocomplete usernames response status: ${response.statusCode}');
      debugPrint(
          'Users autocomplete usernames response body: ${response.body}');

      if (response.statusCode >= 400) {
        final errorMessage = _errorMessageOrUnknown(response);
        throw ApiException(response.statusCode, errorMessage);
      } else if (response.body.isNotEmpty) {
        final List<dynamic> jsonList = jsonDecode(_decodeBodyBytes(response));
        return jsonList.cast<String>();
      } else {
        return [];
      }
    } catch (e) {
      debugPrint('Users autocomplete usernames error: $e');
      rethrow;
    }
  }

  // --- GET /api/users/autocomplete/statuses ---
  Future<http.Response> apiUsersAutocompleteStatusesGetWithHttpInfo({
    required String prefix,
  }) async {
    throw ApiException(
      410,
      localizeRemovedEndpoint('/api/users/autocomplete/statuses'),
    );
  }

  Future<List<String>> apiUsersAutocompleteStatusesGet({
    required String prefix,
  }) async {
    throw ApiException(
      410,
      localizeRemovedEndpoint('/api/users/autocomplete/statuses'),
    );
  }

  // --- GET /api/users/autocomplete/phone-numbers ---
  Future<http.Response> apiUsersAutocompletePhoneNumbersGetWithHttpInfo({
    required String prefix,
  }) async {
    throw ApiException(
      410,
      localizeRemovedEndpoint('/api/users/autocomplete/phone-numbers'),
    );
  }

  Future<List<String>> apiUsersAutocompletePhoneNumbersGet({
    required String prefix,
  }) async {
    throw ApiException(
      410,
      localizeRemovedEndpoint('/api/users/autocomplete/phone-numbers'),
    );
  }

}
