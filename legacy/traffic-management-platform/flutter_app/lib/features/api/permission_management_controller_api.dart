import 'package:final_assignment_front/features/model/permission_management.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:final_assignment_front/utils/services/api_client.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:final_assignment_front/utils/services/auth_token_store.dart';

/// Shared default ApiClient instance.

final ApiClient defaultApiClient = ApiClient();

class PermissionManagementControllerApi {
  final ApiClient apiClient;

  /// Allows injecting a custom ApiClient and otherwise uses the shared default instance.


  PermissionManagementControllerApi([ApiClient? apiClient])
      : apiClient = apiClient ?? defaultApiClient;

  /// Loads the JWT token from storage and applies it to the ApiClient.
  Future<void> initializeWithJwt() async {
    final jwtToken = (await AuthTokenStore.instance.getJwtToken());
    if (jwtToken == null) {
      throw Exception('api.error.notAuthenticated'.tr);
    }
    apiClient.setJwtToken(jwtToken);
  }

  /// Decodes the response body.
  String _decodeBodyBytes(http.Response response) => response.body;

  String _errorMessageOrHttpStatus(http.Response response) {
    return response.body.isNotEmpty
        ? _decodeBodyBytes(response)
        : localizeHttpStatusError(response.statusCode);
  }

  void _throwIfError(http.Response response) {
    if (response.statusCode >= 400) {
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
  }

  /// Builds query parameters for optional name filters.

  List<QueryParam> _addQueryParams({String? name}) {
    final queryParams = <QueryParam>[];
    if (name != null) queryParams.add(QueryParam('name', name));
    return queryParams;
  }

  /// GET /api/permissions - fetch all permissions.
  Future<List<PermissionManagement>> apiPermissionsGet({
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/permissions',
      'GET',
      [
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return PermissionManagement.listFromJson(data);
  }

  /// DELETE /api/permissions/name/{permissionName} - delete a permission by name (admin only).

  Future<void> apiPermissionsNamePermissionNameDelete(
      {required String permissionName}) async {
    if (permissionName.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('permissionName'));
    }
    final response = await apiClient.invokeAPI(
      '/api/permissions/name/$permissionName',
      'DELETE',
      [],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
  }

  /// GET /api/permissions/name/{permissionName} - fetch a permission by name.
  Future<PermissionManagement?> apiPermissionsNamePermissionNameGet(
      {required String permissionName}) async {
    if (permissionName.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('permissionName'));
    }
    final response = await apiClient.invokeAPI(
      '/api/permissions/name/$permissionName',
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
    return PermissionManagement.fromJson(data);
  }

  /// DELETE /api/permissions/{permissionId} - delete a permission by ID (admin only).

  Future<void> apiPermissionsPermissionIdDelete(
      {required String permissionId}) async {
    if (permissionId.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('permissionId'));
    }
    final response = await apiClient.invokeAPI(
      '/api/permissions/$permissionId',
      'DELETE',
      [],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
  }

  /// GET /api/permissions/{permissionId} - fetch a permission by ID.
  Future<PermissionManagement?> apiPermissionsPermissionIdGet(
      {required String permissionId}) async {
    if (permissionId.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('permissionId'));
    }
    final response = await apiClient.invokeAPI(
      '/api/permissions/$permissionId',
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
    return PermissionManagement.fromJson(data);
  }

  /// PUT /api/permissions/{permissionId} - update a permission (admin only).

  Future<PermissionManagement> apiPermissionsPermissionIdPut({
    required String permissionId,
    required PermissionManagement permissionManagement,
  }) async {
    if (permissionId.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('permissionId'));
    }
    final response = await apiClient.invokeAPI(
      '/api/permissions/$permissionId',
      'PUT',
      [],
      permissionManagement.toJson(),
      {},
      {},
      'application/json',
      ['bearerAuth'],
    );
    _throwIfError(response);
    final data = apiClient.deserialize(
        _decodeBodyBytes(response), 'Map<String, dynamic>');
    return PermissionManagement.fromJson(data);
  }

  /// POST /api/permissions - create a permission (admin only).

  Future<PermissionManagement> apiPermissionsPost(
      {required PermissionManagement permissionManagement}) async {
    final response = await apiClient.invokeAPI(
      '/api/permissions',
      'POST',
      [],
      permissionManagement.toJson(),
      {},
      {},
      'application/json',
      ['bearerAuth'],
    );
    _throwIfError(response);
    final data = apiClient.deserialize(
        _decodeBodyBytes(response), 'Map<String, dynamic>');
    return PermissionManagement.fromJson(data);
  }

  /// GET /api/permissions/search - search permissions by name.
  Future<List<PermissionManagement>> apiPermissionsSearchGet(
      {String? name}) async {
    final response = await apiClient.invokeAPI(
      '/api/permissions/search',
      'GET',
      _addQueryParams(name: name),
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return PermissionManagement.listFromJson(data);
  }

  // HTTP: GET /api/permissions/parent/{parentId} - fetch permissions by parent ID.
  Future<List<PermissionManagement>> apiPermissionsParentParentIdGet({
    required int parentId,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/permissions/parent/$parentId',
      'GET',
      [
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return PermissionManagement.listFromJson(data);
  }

  // HTTP: GET /api/permissions/search/code/prefix
  Future<List<PermissionManagement>> apiPermissionsSearchCodePrefixGet({
    required String permissionCode,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/permissions/search/code/prefix',
      'GET',
      [
        QueryParam('permissionCode', permissionCode),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return PermissionManagement.listFromJson(data);
  }

  // HTTP: GET /api/permissions/search/code/fuzzy
  Future<List<PermissionManagement>> apiPermissionsSearchCodeFuzzyGet({
    required String permissionCode,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/permissions/search/code/fuzzy',
      'GET',
      [
        QueryParam('permissionCode', permissionCode),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return PermissionManagement.listFromJson(data);
  }

  // HTTP: GET /api/permissions/search/name/prefix
  Future<List<PermissionManagement>> apiPermissionsSearchNamePrefixGet({
    required String permissionName,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/permissions/search/name/prefix',
      'GET',
      [
        QueryParam('permissionName', permissionName),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return PermissionManagement.listFromJson(data);
  }

  // HTTP: GET /api/permissions/search/name/fuzzy
  Future<List<PermissionManagement>> apiPermissionsSearchNameFuzzyGet({
    required String permissionName,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/permissions/search/name/fuzzy',
      'GET',
      [
        QueryParam('permissionName', permissionName),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return PermissionManagement.listFromJson(data);
  }

  // HTTP: GET /api/permissions/search/type
  Future<List<PermissionManagement>> apiPermissionsSearchTypeGet({
    required String permissionType,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/permissions/search/type',
      'GET',
      [
        QueryParam('permissionType', permissionType),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return PermissionManagement.listFromJson(data);
  }

  // HTTP: GET /api/permissions/search/api-path
  Future<List<PermissionManagement>> apiPermissionsSearchApiPathGet({
    required String apiPath,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/permissions/search/api-path',
      'GET',
      [
        QueryParam('apiPath', apiPath),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return PermissionManagement.listFromJson(data);
  }

  // HTTP: GET /api/permissions/search/menu-path
  Future<List<PermissionManagement>> apiPermissionsSearchMenuPathGet({
    required String menuPath,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/permissions/search/menu-path',
      'GET',
      [
        QueryParam('menuPath', menuPath),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return PermissionManagement.listFromJson(data);
  }

  // HTTP: GET /api/permissions/search/visible
  Future<List<PermissionManagement>> apiPermissionsSearchVisibleGet({
    required bool isVisible,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/permissions/search/visible',
      'GET',
      [
        QueryParam('isVisible', isVisible.toString()),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return PermissionManagement.listFromJson(data);
  }

  // HTTP: GET /api/permissions/search/external
  Future<List<PermissionManagement>> apiPermissionsSearchExternalGet({
    required bool isExternal,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/permissions/search/external',
      'GET',
      [
        QueryParam('isExternal', isExternal.toString()),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return PermissionManagement.listFromJson(data);
  }

  // HTTP: GET /api/permissions/search/status
  Future<List<PermissionManagement>> apiPermissionsSearchStatusGet({
    required String status,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/permissions/search/status',
      'GET',
      [
        QueryParam('status', status),
        QueryParam('page', '$page'),
        QueryParam('size', '$size'),
      ],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    _throwIfError(response);
    final List<dynamic> data =
        apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
    return PermissionManagement.listFromJson(data);
  }
}
