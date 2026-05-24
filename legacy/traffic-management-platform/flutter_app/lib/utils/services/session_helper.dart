import 'package:final_assignment_front/features/api/auth_controller_api.dart';
import 'package:final_assignment_front/features/api/user_management_controller_api.dart';
import 'package:final_assignment_front/features/model/user_management.dart';
import 'package:final_assignment_front/utils/helpers/role_utils.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:jwt_decoder/jwt_decoder.dart';

class SessionHelper {
  SessionHelper({
    AuthControllerApi? authApi,
    UserManagementControllerApi? userApi,
  })  : _authApi = authApi ?? AuthControllerApi(),
        _userApi = userApi ?? UserManagementControllerApi();

  final AuthControllerApi _authApi;
  final UserManagementControllerApi _userApi;

  Future<String?> refreshJwtToken() async {
    final refreshToken = await AuthTokenStore.instance.getRefreshToken();
    if (refreshToken == null || refreshToken.trim().isEmpty) {
      return null;
    }
    try {
      final payload =
          await _authApi.apiAuthRefreshPost(refreshToken: refreshToken);
      final newJwt = payload['jwtToken']?.toString();
      if (newJwt == null || newJwt.isEmpty) {
        return null;
      }
      final refreshedToken = payload['refreshToken']?.toString();
      await AuthTokenStore.instance.setJwtToken(newJwt);
      if (refreshedToken != null && refreshedToken.isNotEmpty) {
        await AuthTokenStore.instance.setRefreshToken(refreshedToken);
      }
      return newJwt;
    } catch (_) {
      return null;
    }
  }

  Future<UserManagement?> fetchCurrentUser() async {
    await _userApi.initializeWithJwt();
    return await _userApi.apiUsersMeGet();
  }

  Future<List<String>> fetchCurrentRoles() async {
    try {
      final user = await fetchCurrentUser();
      final userRoles = normalizeRoleCodes(user?.roles);
      if (userRoles.isNotEmpty) {
        return userRoles;
      }
    } catch (_) {}

    final jwtToken = await AuthTokenStore.instance.getJwtToken();
    if (jwtToken == null || jwtToken.isEmpty) {
      return const [];
    }
    try {
      final decoded = JwtDecoder.decode(jwtToken);
      return normalizeRoleCodes(decoded['roles']);
    } catch (_) {
      return const [];
    }
  }
}
