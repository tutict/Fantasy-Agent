import 'package:final_assignment_front/features/model/role_management.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:final_assignment_front/utils/services/api_client.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;

/// Shared default ApiClient instance.

final ApiClient defaultApiClient = ApiClient();

class RoleManagementControllerApi {
  final ApiClient apiClient;

  /// Allows injecting a custom ApiClient and otherwise uses the shared default instance.


  RoleManagementControllerApi([ApiClient? apiClient])
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

  /// Builds common request headers.

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

  List<QueryParam> _addQueryParams({String? name}) {
    final queryParams = <QueryParam>[];
    if (name != null) {
      queryParams.add(QueryParam('name', name));
    }
    return queryParams;
  }

  /// POST /api/roles - create a role (admin only).
  Future<RoleManagement> createRole(
      RoleManagement role, String idempotencyKey) async {
    final response = await apiClient.invokeAPI(
      '/api/roles',
      'POST',
      [],
      role.toJson(),
      await _getHeaders(idempotencyKey: idempotencyKey),
      {},
      'application/json',
      ['bearerAuth'],
    );
    if (response.statusCode != 201) {
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
    final data = apiClient.deserialize(
        _decodeBodyBytes(response), 'Map<String, dynamic>');
    return RoleManagement.fromJson(data);
  }

  /// GET /api/roles/{roleId} - fetch a role by ID.
  Future<RoleManagement?> apiRolesRoleIdGet(int roleId) async {
    final response = await apiClient.invokeAPI(
      '/api/roles/$roleId',
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
    return RoleManagement.fromJson(data);
  }

  /// GET /api/roles - fetch all roles.
  Future<List<RoleManagement>> apiRolesGet({
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/roles',
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
    return RoleManagement.listFromJson(data);
  }

  /// GET /api/roles/name/{roleName} - fetch a role by name.
  Future<RoleManagement?> apiRolesNameRoleNameGet(String roleName) async {
    if (roleName.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('roleName'));
    }
    final response = await apiClient.invokeAPI(
      '/api/roles/name/$roleName',
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
    return RoleManagement.fromJson(data);
  }

  /// GET /api/roles/search - search roles by name.

  Future<List<RoleManagement>> apiRolesSearchGet({String? name}) async {
    final response = await apiClient.invokeAPI(
      '/api/roles/search',
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
    return RoleManagement.listFromJson(data);
  }

  /// PUT /api/roles/{roleId} - update a role (admin only).
  Future<RoleManagement> apiRolesRoleIdPut(
      int roleId, RoleManagement updatedRole, String idempotencyKey) async {
    final response = await apiClient.invokeAPI(
      '/api/roles/$roleId',
      'PUT',
      [],
      updatedRole.toJson(),
      await _getHeaders(idempotencyKey: idempotencyKey),
      {},
      'application/json',
      ['bearerAuth'],
    );
    _throwIfError(response);
    final data = apiClient.deserialize(
        _decodeBodyBytes(response), 'Map<String, dynamic>');
    return RoleManagement.fromJson(data);
  }

  /// DELETE /api/roles/{roleId} - delete a role (admin only).
  Future<void> apiRolesRoleIdDelete(int roleId) async {
    final response = await apiClient.invokeAPI(
      '/api/roles/$roleId',
      'DELETE',
      [],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode != 204) {
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
  }

  /// DELETE /api/roles/name/{roleName} - delete a role by name (admin only).
  Future<void> apiRolesNameRoleNameDelete(String roleName) async {
    if (roleName.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('roleName'));
    }
    final response = await apiClient.invokeAPI(
      '/api/roles/name/$roleName',
      'DELETE',
      [],
      '',
      {},
      {},
      null,
      ['bearerAuth'],
    );
    if (response.statusCode != 204) {
      throw ApiException(
          response.statusCode, _errorMessageOrHttpStatus(response));
    }
  }

  /// Determines the current user role from the fetched role list.
  Future<String> getCurrentUserRole() async {
    final roles = await apiRolesGet();
    for (var role in roles) {
      if (role.roleName != null && role.roleName!.isNotEmpty) {
        return role
            .roleName!; // Returns the first non-empty role name.
      }
    }
    throw ApiException(403, localizeCannotDetermineUserRole());
  }

  // HTTP: GET /api/roles/by-code/{roleCode} - fetch a role by code.
  Future<RoleManagement?> apiRolesByCodeRoleCodeGet(String roleCode) async {
    if (roleCode.isEmpty) {
      throw ApiException(400, localizeMissingRequiredParam('roleCode'));
    }
    final response = await apiClient.invokeAPI(
      '/api/roles/by-code/$roleCode',
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
    return RoleManagement.fromJson(data);
  }

  // HTTP: GET /api/roles/search/code/prefix?roleCode=&page=&size=
  Future<List<RoleManagement>> apiRolesSearchCodePrefixGet({
    required String roleCode,
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/roles/search/code/prefix',
      'GET',
      [
        QueryParam('roleCode', roleCode),
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
    return RoleManagement.listFromJson(data);
  }

  // HTTP: GET /api/roles/search/code/fuzzy?roleCode=&page=&size=
  Future<List<RoleManagement>> apiRolesSearchCodeFuzzyGet({
    required String roleCode,
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/roles/search/code/fuzzy',
      'GET',
      [
        QueryParam('roleCode', roleCode),
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
    return RoleManagement.listFromJson(data);
  }

  // HTTP: GET /api/roles/search/name/prefix?roleName=&page=&size=
  Future<List<RoleManagement>> apiRolesSearchNamePrefixGet({
    required String roleName,
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/roles/search/name/prefix',
      'GET',
      [
        QueryParam('roleName', roleName),
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
    return RoleManagement.listFromJson(data);
  }

  // HTTP: GET /api/roles/search/name/fuzzy?roleName=&page=&size=
  Future<List<RoleManagement>> apiRolesSearchNameFuzzyGet({
    required String roleName,
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/roles/search/name/fuzzy',
      'GET',
      [
        QueryParam('roleName', roleName),
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
    return RoleManagement.listFromJson(data);
  }

  // HTTP: GET /api/roles/search/type?roleType=&page=&size=
  Future<List<RoleManagement>> apiRolesSearchTypeGet({
    required String roleType,
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/roles/search/type',
      'GET',
      [
        QueryParam('roleType', roleType),
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
    return RoleManagement.listFromJson(data);
  }

  // HTTP: GET /api/roles/search/data-scope?dataScope=&page=&size=
  Future<List<RoleManagement>> apiRolesSearchDataScopeGet({
    required String dataScope,
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/roles/search/data-scope',
      'GET',
      [
        QueryParam('dataScope', dataScope),
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
    return RoleManagement.listFromJson(data);
  }

  // HTTP: GET /api/roles/search/status?status=&page=&size=
  Future<List<RoleManagement>> apiRolesSearchStatusGet({
    required String status,
    int page = 1,
    int size = 20,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/roles/search/status',
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
    return RoleManagement.listFromJson(data);
  }

  // HTTP: GET /api/roles/{roleId}/permissions - fetch permissions assigned to a role.
  Future<List<dynamic>> apiRolesRoleIdPermissionsGet({
    required int roleId,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/roles/$roleId/permissions',
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
    return apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
  }

  // HTTP: GET /api/roles/permissions/search?roleId=&permissionId=&page=&size=
  Future<List<dynamic>> apiRolesPermissionsSearchGet({
    required int roleId,
    required int permissionId,
    int page = 1,
    int size = 50,
  }) async {
    final response = await apiClient.invokeAPI(
      '/api/roles/permissions/search',
      'GET',
      [
        QueryParam('roleId', '$roleId'),
        QueryParam('permissionId', '$permissionId'),
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
    return apiClient.deserialize(_decodeBodyBytes(response), 'List<dynamic>');
  }
}
