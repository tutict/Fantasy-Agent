import 'dart:convert';
import 'package:final_assignment_front/features/model/login_request.dart';
import 'package:final_assignment_front/features/model/register_request.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http; // Used for Response and MultipartRequest
import 'package:final_assignment_front/utils/services/api_client.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';

// Shared default ApiClient instance.

final ApiClient defaultApiClient = ApiClient();

class AuthControllerApi {
  final ApiClient apiClient;

  // Allows injecting a custom ApiClient and otherwise uses the shared default instance.
  AuthControllerApi([ApiClient? apiClient])
      : apiClient = apiClient ?? defaultApiClient;

  // Decodes the response body.

  String _decodeBodyBytes(http.Response response) => response.body;

  // Builds common headers and adds the JWT token when available.

  Future<Map<String, String>> _getHeaders() async {
    final token = (await AuthTokenStore.instance.getJwtToken()) ?? '';
    return {
      'Content-Type': 'application/json; charset=utf-8',
      if (token.isNotEmpty) 'Authorization': 'Bearer $token',
    };
  }

  /// Sends the HTTP login request.
  Future<http.Response> apiAuthLoginPostWithHttpInfo(
      {required LoginRequest loginRequest}) async {
    Object postBody = loginRequest;

    String path = "/api/auth/login".replaceAll("{format}", "json");

    List<QueryParam> queryParams = [];
    Map<String, String> headerParams = await _getHeaders();
    Map<String, String> formParams = {};

    List<String> contentTypes = ["application/json"];
    String? nullableContentType =
        contentTypes.isNotEmpty ? contentTypes[0] : null;
    List<String> authNames = [];

    var response = await apiClient.invokeAPI(path, 'POST', queryParams,
        postBody, headerParams, formParams, nullableContentType, authNames);
    return response;
  }

  /// Logs in with username and password.
  Future<Map<String, dynamic>> apiAuthLoginPost(
      {required LoginRequest loginRequest}) async {
    try {
      http.Response response =
          await apiAuthLoginPostWithHttpInfo(loginRequest: loginRequest);
      debugPrint('Login response status: ${response.statusCode}');

      if (response.statusCode >= 400) {
        String errorMessage = response.body.isNotEmpty
            ? _decodeBodyBytes(response)
            : localizeUnknownApiError();
        throw ApiException(response.statusCode, errorMessage);
      } else if (response.body.isNotEmpty) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      } else {
        return {};
      }
    } catch (e) {
      debugPrint('Login error: $e');
      rethrow;
    }
  }

  /// Sends the HTTP refresh-token request.
  Future<Map<String, dynamic>> apiAuthRefreshPost({
    required String refreshToken,
  }) async {
    if (refreshToken.trim().isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('refreshToken'));
    }

    final response = await apiClient.invokeAPI(
      '/api/auth/refresh',
      'POST',
      const [],
      {
        'refreshToken': refreshToken.trim(),
      },
      {
        'Content-Type': 'application/json; charset=utf-8',
      },
      const {},
      'application/json',
      const [],
    );

    if (response.statusCode >= 400) {
      final errorMessage = response.body.isNotEmpty
          ? _decodeBodyBytes(response)
          : localizeHttpStatusError(response.statusCode);
      throw ApiException(response.statusCode, errorMessage);
    }
    if (response.body.isEmpty) {
      return {};
    }
    return jsonDecode(_decodeBodyBytes(response)) as Map<String, dynamic>;
  }

  Future<http.Response> apiAuthRegisterPostWithHttpInfo(
      {required RegisterRequest registerRequest}) async {
    Object postBody = registerRequest;

    String path = "/api/auth/register".replaceAll("{format}", "json");

    List<QueryParam> queryParams = [];
    Map<String, String> headerParams = await _getHeaders();
    Map<String, String> formParams = {};

    List<String> contentTypes = ["application/json"];
    String? nullableContentType =
        contentTypes.isNotEmpty ? contentTypes[0] : null;
    List<String> authNames = [];

    var response = await apiClient.invokeAPI(path, 'POST', queryParams,
        postBody, headerParams, formParams, nullableContentType, authNames);
    return response;
  }

  /// Registers a new user.
  Future<Map<String, dynamic>> apiAuthRegisterPost(
      {required RegisterRequest registerRequest}) async {
    try {
      http.Response response = await apiAuthRegisterPostWithHttpInfo(
          registerRequest: registerRequest);
      debugPrint('Register response status: ${response.statusCode}');

      if (response.statusCode >= 400) {
        String errorMessage = response.body.isNotEmpty
            ? _decodeBodyBytes(response)
            : localizeUnknownApiError();
        throw ApiException(response.statusCode, errorMessage);
      } else if (response.body.isNotEmpty) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      } else if (response.statusCode == 201) {
        return {'status': 'CREATED'};
      } else {
        throw ApiException(
            response.statusCode, localizeEmptyResponseApiError());
      }
    } catch (e) {
      debugPrint('Register error: $e');
      rethrow;
    }
  }

  /// Sends the HTTP request that fetches a page of users.
  Future<http.Response> apiAuthUsersGetWithHttpInfo({
    int page = 1,
    int size = 100,
  }) async {
    String path = "/api/auth/users".replaceAll("{format}", "json");

    List<QueryParam> queryParams = [
      QueryParam('page', page.toString()),
      QueryParam('size', size.toString()),
    ];
    Map<String, String> headerParams = await _getHeaders();
    Map<String, String> formParams = {};

    List<String> contentTypes = [];
    String? nullableContentType =
        contentTypes.isNotEmpty ? contentTypes[0] : null;
    List<String> authNames = [];

    var response = await apiClient.invokeAPI(path, 'GET', queryParams, null,
        headerParams, formParams, nullableContentType, authNames);
    return response;
  }

  /// Fetches a page of users.
  Future<List<dynamic>> apiAuthUsersGet({
    int page = 1,
    int size = 100,
  }) async {
    try {
      http.Response response = await apiAuthUsersGetWithHttpInfo(
        page: page,
        size: size,
      );
      debugPrint('Users get response status: ${response.statusCode}');
      debugPrint('Users get response body: ${response.body}');

      if (response.statusCode >= 400) {
        String errorMessage = response.body.isNotEmpty
            ? _decodeBodyBytes(response)
            : localizeUnknownApiError();
        throw ApiException(response.statusCode, errorMessage);
      } else if (response.body.isNotEmpty) {
        return jsonDecode(response.body) as List<dynamic>;
      } else {
        return const [];
      }
    } catch (e) {
      debugPrint('Users get error: $e');
      rethrow;
    }
  }

  /// Sends the HTTP request that fetches all roles.
  Future<http.Response> apiRolesGetWithHttpInfo() async {
    String path = "/api/roles".replaceAll("{format}", "json");

    List<QueryParam> queryParams = [];
    Map<String, String> headerParams = await _getHeaders();
    Map<String, String> formParams = {};

    List<String> contentTypes = [];
    String? nullableContentType =
        contentTypes.isNotEmpty ? contentTypes[0] : null;
    List<String> authNames = [];

    var response = await apiClient.invokeAPI(path, 'GET', queryParams, null,
        headerParams, formParams, nullableContentType, authNames);
    return response;
  }

  /// Fetches all roles.
  Future<Map<String, dynamic>> apiRolesGet() async {
    try {
      http.Response response = await apiRolesGetWithHttpInfo();
      debugPrint('Roles get response status: ${response.statusCode}');
      debugPrint('Roles get response body: ${response.body}');

      if (response.statusCode >= 400) {
        String errorMessage = response.body.isNotEmpty
            ? _decodeBodyBytes(response)
            : localizeUnknownApiError();
        throw ApiException(response.statusCode, errorMessage);
      } else if (response.body.isNotEmpty) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      } else {
        return {};
      }
    } catch (e) {
      debugPrint('Roles get error: $e');
      rethrow;
    }
  }

}
