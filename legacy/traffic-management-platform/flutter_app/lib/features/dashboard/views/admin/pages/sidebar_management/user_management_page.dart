import 'dart:async';

import 'package:final_assignment_front/config/routes/app_routes.dart';
import 'package:final_assignment_front/features/api/role_management_controller_api.dart';
import 'package:final_assignment_front/features/api/user_management_controller_api.dart';
import 'package:final_assignment_front/features/dashboard/controllers/admin_dashboard_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/dashboard_page_template.dart';
import 'package:final_assignment_front/features/model/role_management.dart';
import 'package:final_assignment_front/features/model/user_management.dart';
import 'package:final_assignment_front/i18n/status_localizers.dart';
import 'package:final_assignment_front/i18n/user_admin_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:final_assignment_front/utils/helpers/role_utils.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:jwt_decoder/jwt_decoder.dart';
import 'package:uuid/uuid.dart';

String generateIdempotencyKey() => const Uuid().v4();

class UserManagementPage extends StatefulWidget {
  const UserManagementPage({super.key});

  @override
  State<UserManagementPage> createState() => _UserManagementPageState();
}

class _UserManagementPageState extends State<UserManagementPage> {
  static const int _pageSize = 20;
  static const int _rolePageSize = 100;

  final DashboardController controller = Get.find<DashboardController>();
  final UserManagementControllerApi userApi = UserManagementControllerApi();
  final RoleManagementControllerApi roleApi = RoleManagementControllerApi();
  final TextEditingController _searchController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  final List<UserManagement> _allUsers = [];
  List<UserManagement> _filteredUsers = [];

  String _activeQuery = '';
  int _currentPage = 1;
  bool _hasMore = true;
  bool _isLoading = false;
  bool _isAdmin = false;
  bool _showReloginAction = false;
  String _statusMessage = '';
  String _searchType = kUserAdminSearchTypeUsername;
  String? _currentUsername;
  Timer? _searchDebounce;

  @override
  void initState() {
    super.initState();
    _initialize();
    _scrollController.addListener(_handleScroll);
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();
    _searchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<bool> _validateJwtToken() async {
    final jwtToken = await AuthTokenStore.instance.getJwtToken();
    if (jwtToken == null || jwtToken.isEmpty) {
      if (mounted) {
        setState(() {
          _statusMessage = 'userAdmin.error.unauthorized'.tr;
          _showReloginAction = true;
        });
      }
      return false;
    }

    try {
      if (JwtDecoder.isExpired(jwtToken)) {
        if (mounted) {
          setState(() {
            _statusMessage = 'userAdmin.error.expired'.tr;
            _showReloginAction = true;
          });
        }
        return false;
      }

      final decodedToken = JwtDecoder.decode(jwtToken);
      _currentUsername = decodedToken['sub']?.toString();
      return true;
    } catch (e) {
      if (mounted) {
        setState(() {
          _statusMessage = 'userAdmin.error.invalidLogin'.trParams({
            'error': formatUserAdminError(e),
          });
          _showReloginAction = true;
        });
      }
      return false;
    }
  }

  Future<void> _initialize() async {
    if (mounted) {
      setState(() {
        _isLoading = true;
        _statusMessage = '';
        _showReloginAction = false;
      });
    }

    try {
      if (!await _validateJwtToken()) {
        return;
      }

      await userApi.initializeWithJwt();
      final jwtToken = await AuthTokenStore.instance.getJwtToken();
      final decodedToken = JwtDecoder.decode(jwtToken!);
      final roles = decodedToken['roles'];

      if (!hasAnyRole(roles, const ['SUPER_ADMIN', 'ADMIN'])) {
        if (mounted) {
          setState(() {
            _isAdmin = false;
            _statusMessage = 'userAdmin.error.adminOnly'.tr;
          });
        }
        return;
      }

      _isAdmin = true;
      await _loadUsers(reset: true);
    } catch (e) {
      if (mounted) {
        setState(() {
          _statusMessage = 'userAdmin.error.initFailed'.trParams({
            'error': formatUserAdminError(e),
          });
        });
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _loadUsers({bool reset = false, String? query}) async {
    if (!_isAdmin) return;
    if (reset) {
      _currentPage = 1;
      _hasMore = true;
      _activeQuery = (query ?? _searchController.text).trim();
      _allUsers.clear();
      _filteredUsers.clear();
    }
    if (!reset && (_isLoading || !_hasMore)) {
      return;
    }

    if (mounted) {
      setState(() {
        _isLoading = true;
        _statusMessage = '';
        _showReloginAction = false;
      });
    }

    try {
      if (!await _validateJwtToken()) {
        return;
      }

      await userApi.initializeWithJwt();
      final users =
          await _loadUserPage(page: _currentPage, query: _activeQuery);
      final visibleUsers = users
          .where((user) =>
              user.username != null && user.username != _currentUsername)
          .toList()
        ..sort((left, right) {
          final leftName = left.username?.toLowerCase() ?? '';
          final rightName = right.username?.toLowerCase() ?? '';
          return leftName.compareTo(rightName);
        });

      if (!mounted) return;
      setState(() {
        _allUsers.addAll(visibleUsers);
        _rebuildVisibleUsers();
        _hasMore = users.length == _pageSize;
        _currentPage++;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _allUsers.clear();
        _filteredUsers = [];
        _statusMessage = 'userAdmin.error.loadFailed'.trParams({
          'error': formatUserAdminError(e),
        });
        _showReloginAction = e is ApiException && e.code == 403;
      });
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _refreshUsers() async {
    await _refreshUsersWithQuery();
  }

  Future<List<UserManagement>> _loadUserPage({
    required int page,
    required String query,
  }) {
    if (query.isEmpty) {
      return userApi.apiUsersGet(page: page, size: _pageSize);
    }

    switch (_searchType) {
      case kUserAdminSearchTypeStatus:
        return userApi.apiUsersSearchStatusGet(
          status: query,
          page: page,
          size: _pageSize,
        );
      case kUserAdminSearchTypeDepartment:
        return userApi.apiUsersSearchDepartmentPrefixGet(
          department: query,
          page: page,
          size: _pageSize,
        );
      case kUserAdminSearchTypeContactNumber:
        return userApi.apiUsersSearchContactGet(
          contactNumber: query,
          page: page,
          size: _pageSize,
        );
      case kUserAdminSearchTypeEmail:
        return userApi.apiUsersSearchEmailGet(
          email: query,
          page: page,
          size: _pageSize,
        );
      case kUserAdminSearchTypeUsername:
      default:
        return userApi.apiUsersSearchUsernameFuzzyGet(
          username: query,
          page: page,
          size: _pageSize,
        );
    }
  }

  void _rebuildVisibleUsers() {
    _filteredUsers = List<UserManagement>.from(_allUsers);
    if (_filteredUsers.isEmpty) {
      _statusMessage = _activeQuery.isEmpty
          ? 'userAdmin.empty.default'.tr
          : 'userAdmin.empty.filtered'.tr;
    } else {
      _statusMessage = '';
    }
  }

  void _handleScroll() {
    if (!_scrollController.hasClients || _isLoading || !_hasMore) {
      return;
    }
    final position = _scrollController.position;
    if (position.pixels >= position.maxScrollExtent - 200) {
      _loadUsers();
    }
  }

  Future<void> _refreshUsersWithQuery({String? query}) async {
    _searchDebounce?.cancel();
    final effectiveQuery = (query ?? _searchController.text).trim();
    _searchController.value = TextEditingValue(
      text: effectiveQuery,
      selection: TextSelection.collapsed(offset: effectiveQuery.length),
    );
    await _loadUsers(reset: true, query: effectiveQuery);
  }

  void _scheduleSearchRefresh(String value) {
    _searchDebounce?.cancel();
    _searchDebounce = Timer(const Duration(milliseconds: 350), () {
      if (!mounted) {
        return;
      }
      _refreshUsersWithQuery(query: value);
    });
  }

  Future<bool> _checkUsernameAvailability(String username) async {
    try {
      await userApi.apiUsersUsernameUsernameGet(username: username);
      return false;
    } catch (e) {
      if (e is ApiException && e.code == 404) {
        return true;
      }
      rethrow;
    }
  }

  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;
    final themeData = controller.currentBodyTheme.value;
    ScaffoldMessenger.of(context).clearSnackBars();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          message,
          style: TextStyle(
            color: isError
                ? themeData.colorScheme.onError
                : themeData.colorScheme.onPrimary,
          ),
        ),
        backgroundColor: isError
            ? themeData.colorScheme.error
            : themeData.colorScheme.primary,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  bool get _hasActiveFilters =>
      _searchController.text.trim().isNotEmpty ||
      _searchType != kUserAdminSearchTypeUsername;

  int _activeUserCount() {
    return _filteredUsers
        .where((user) =>
            normalizeAccountStatusCode(user.status) == kUserAdminStatusActive)
        .length;
  }

  int _inactiveUserCount() {
    return _filteredUsers
        .where((user) =>
            normalizeAccountStatusCode(user.status) == kUserAdminStatusInactive)
        .length;
  }

  int _departmentCount() {
    return _filteredUsers
        .map((user) => user.department?.trim() ?? '')
        .where((department) => department.isNotEmpty)
        .toSet()
        .length;
  }

  Widget _buildHeroSection(ThemeData themeData) {
    final onHero = themeData.brightness == Brightness.dark
        ? Colors.white
        : const Color(0xFF102530);
    final muted = onHero.withValues(alpha: 0.72);
    final queryLabel = _searchController.text.trim().isNotEmpty
        ? 'userAdmin.workspace.signal.query'.trParams({
            'value': _searchController.text.trim(),
          })
        : 'userAdmin.workspace.signal.queryIdle'.tr;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: themeData.brightness == Brightness.dark
              ? const [
                  Color(0xFF08161E),
                  Color(0xFF0F2530),
                  Color(0xFF174557),
                ]
              : const [
                  Color(0xFFF6FAFC),
                  Color(0xFFEAF2F7),
                  Color(0xFFDDE8EF),
                ],
        ),
        borderRadius: BorderRadius.circular(30),
        border: Border.all(
          color: themeData.colorScheme.outline.withValues(alpha: 0.12),
        ),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final stacked = constraints.maxWidth < 940;
          final lead = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  _UserHeroBadge(
                    label: 'userAdmin.workspace.eyebrow'.tr.toUpperCase(),
                    foregroundColor: onHero,
                  ),
                  _UserHeroBadge(
                    label: userAdminSearchTypeLabelKey(_searchType)
                        .tr
                        .toUpperCase(),
                    foregroundColor: Colors.white,
                    backgroundColor: _hasActiveFilters
                        ? const Color(0xFF1F9D68)
                        : const Color(0xFF2F6FD6),
                    filled: true,
                  ),
                ],
              ),
              const SizedBox(height: 18),
              Text(
                'userAdmin.workspace.title'.tr,
                style: themeData.textTheme.headlineMedium?.copyWith(
                  color: onHero,
                  fontWeight: FontWeight.w800,
                  height: 1.05,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'userAdmin.workspace.subtitle'.tr,
                style: themeData.textTheme.bodyLarge?.copyWith(
                  color: muted,
                  height: 1.55,
                ),
              ),
              const SizedBox(height: 18),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  _UserInlineSignal(
                    icon: Icons.search_rounded,
                    label: queryLabel,
                    color: onHero,
                  ),
                  _UserInlineSignal(
                    icon: Icons.tune_rounded,
                    label: 'userAdmin.workspace.signal.mode'.trParams({
                      'value': userAdminSearchTypeLabelKey(_searchType).tr,
                    }),
                    color: onHero,
                  ),
                ],
              ),
            ],
          );
          final metrics = Wrap(
            spacing: 14,
            runSpacing: 14,
            children: [
              _UserMetricTile(
                label: 'userAdmin.workspace.metric.loaded'.tr,
                value: '${_allUsers.length}',
              ),
              _UserMetricTile(
                label: 'userAdmin.workspace.metric.visible'.tr,
                value: '${_filteredUsers.length}',
              ),
              _UserMetricTile(
                label: 'userAdmin.workspace.metric.active'.tr,
                value: '${_activeUserCount()}',
              ),
              _UserMetricTile(
                label: 'userAdmin.workspace.metric.inactive'.tr,
                value: '${_inactiveUserCount()}',
              ),
              _UserMetricTile(
                label: 'userAdmin.workspace.metric.department'.tr,
                value: '${_departmentCount()}',
              ),
            ],
          );

          if (stacked) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                lead,
                const SizedBox(height: 22),
                metrics,
              ],
            );
          }

          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(flex: 6, child: lead),
              const SizedBox(width: 24),
              Expanded(
                flex: 4,
                child: Align(alignment: Alignment.topRight, child: metrics),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildSectionHeading(
    ThemeData themeData, {
    required String eyebrow,
    required String title,
    required String description,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          eyebrow.toUpperCase(),
          style: themeData.textTheme.labelMedium?.copyWith(
            color: themeData.colorScheme.primary,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.3,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          title,
          style: themeData.textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.w800,
            height: 1.1,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          description,
          style: themeData.textTheme.bodyMedium?.copyWith(
            color: themeData.colorScheme.onSurfaceVariant,
            height: 1.5,
          ),
        ),
      ],
    );
  }

  Future<void> _showCreateUserDialog() async {
    final usernameController = TextEditingController();
    final passwordController = TextEditingController();
    final contactNumberController = TextEditingController();
    final emailController = TextEditingController();
    final departmentController = TextEditingController();
    final remarksController = TextEditingController();
    String selectedStatus = kUserAdminStatusActive;
    final formKey = GlobalKey<FormState>();

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        final themeData = controller.currentBodyTheme.value;
        return Theme(
          data: themeData,
          child: AlertDialog(
            title: Text('userAdmin.dialog.createTitle'.tr),
            backgroundColor: themeData.colorScheme.surfaceContainerLowest,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16.0),
            ),
            content: SizedBox(
              width: 480,
              child: Form(
                key: formKey,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      _buildTextField(
                        controller: usernameController,
                        themeData: themeData,
                        fieldKey: kUserAdminFieldUsername,
                        isRequired: true,
                      ),
                      const SizedBox(height: 12),
                      _buildTextField(
                        controller: passwordController,
                        themeData: themeData,
                        fieldKey: kUserAdminFieldPassword,
                        isRequired: true,
                        obscureText: true,
                      ),
                      const SizedBox(height: 12),
                      _buildTextField(
                        controller: contactNumberController,
                        themeData: themeData,
                        fieldKey: kUserAdminFieldContactNumber,
                        keyboardType: TextInputType.phone,
                      ),
                      const SizedBox(height: 12),
                      _buildTextField(
                        controller: emailController,
                        themeData: themeData,
                        fieldKey: kUserAdminFieldEmail,
                        keyboardType: TextInputType.emailAddress,
                      ),
                      const SizedBox(height: 12),
                      _buildTextField(
                        controller: departmentController,
                        themeData: themeData,
                        fieldKey: kUserAdminFieldDepartment,
                      ),
                      const SizedBox(height: 12),
                      _buildStatusField(
                        themeData: themeData,
                        initialValue: selectedStatus,
                        onChanged: (value) {
                          if (value != null) {
                            selectedStatus = value;
                          }
                        },
                      ),
                      const SizedBox(height: 12),
                      _buildTextField(
                        controller: remarksController,
                        themeData: themeData,
                        fieldKey: kUserAdminFieldRemarks,
                        maxLines: 3,
                      ),
                    ],
                  ),
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(dialogContext).pop(),
                child: Text('common.cancel'.tr),
              ),
              ElevatedButton(
                onPressed: () async {
                  if (!formKey.currentState!.validate()) return;
                  if (!await _validateJwtToken()) return;

                  final username = usernameController.text.trim();

                  try {
                    await userApi.initializeWithJwt();
                    final isAvailable =
                        await _checkUsernameAvailability(username);
                    if (!isAvailable) {
                      _showSnackBar(
                        'userAdmin.validation.usernameExists'.tr,
                        isError: true,
                      );
                      return;
                    }

                    final newUser = UserManagement(
                      username: username,
                      password: passwordController.text.trim(),
                      contactNumber: _emptyToNull(contactNumberController.text),
                      email: _emptyToNull(emailController.text),
                      department: _emptyToNull(departmentController.text),
                      status: selectedStatus,
                      remarks: _emptyToNull(remarksController.text),
                    );

                    await userApi.apiUsersPost(
                      userManagement: newUser,
                      idempotencyKey: generateIdempotencyKey(),
                    );

                    if (!mounted || !dialogContext.mounted) return;
                    Navigator.of(dialogContext).pop();
                    _showSnackBar('userAdmin.success.created'.tr);
                    await _refreshUsers();
                  } catch (e) {
                    _showSnackBar(
                      'userAdmin.error.createFailed'.trParams({
                        'error': formatUserAdminError(e),
                      }),
                      isError: true,
                    );
                  }
                },
                child: Text('userAdmin.action.create'.tr),
              ),
            ],
          ),
        );
      },
    );

    usernameController.dispose();
    passwordController.dispose();
    contactNumberController.dispose();
    emailController.dispose();
    departmentController.dispose();
    remarksController.dispose();
  }

  Future<void> _showEditUserDialog(UserManagement user) async {
    final usernameController = TextEditingController(text: user.username ?? '');
    final passwordController = TextEditingController();
    final contactNumberController =
        TextEditingController(text: user.contactNumber ?? '');
    final emailController = TextEditingController(text: user.email ?? '');
    final departmentController =
        TextEditingController(text: user.department ?? '');
    final remarksController = TextEditingController(text: user.remarks ?? '');
    String selectedStatus = normalizeAccountStatusCode(user.status);
    if (selectedStatus.isEmpty) {
      selectedStatus = kUserAdminStatusActive;
    }
    final formKey = GlobalKey<FormState>();

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        final themeData = controller.currentBodyTheme.value;
        return Theme(
          data: themeData,
          child: AlertDialog(
            title: Text('userAdmin.dialog.editTitle'.tr),
            backgroundColor: themeData.colorScheme.surfaceContainerLowest,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16.0),
            ),
            content: SizedBox(
              width: 480,
              child: Form(
                key: formKey,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      _buildTextField(
                        controller: usernameController,
                        themeData: themeData,
                        fieldKey: kUserAdminFieldUsername,
                        isRequired: true,
                      ),
                      const SizedBox(height: 12),
                      _buildTextField(
                        controller: passwordController,
                        themeData: themeData,
                        fieldKey: kUserAdminFieldNewPassword,
                        obscureText: true,
                        helperText: 'userAdmin.helper.passwordOptional'.tr,
                      ),
                      const SizedBox(height: 12),
                      _buildTextField(
                        controller: contactNumberController,
                        themeData: themeData,
                        fieldKey: kUserAdminFieldContactNumber,
                        keyboardType: TextInputType.phone,
                      ),
                      const SizedBox(height: 12),
                      _buildTextField(
                        controller: emailController,
                        themeData: themeData,
                        fieldKey: kUserAdminFieldEmail,
                        keyboardType: TextInputType.emailAddress,
                      ),
                      const SizedBox(height: 12),
                      _buildTextField(
                        controller: departmentController,
                        themeData: themeData,
                        fieldKey: kUserAdminFieldDepartment,
                      ),
                      const SizedBox(height: 12),
                      _buildStatusField(
                        themeData: themeData,
                        initialValue: selectedStatus,
                        onChanged: (value) {
                          if (value != null) {
                            selectedStatus = value;
                          }
                        },
                      ),
                      const SizedBox(height: 12),
                      _buildTextField(
                        controller: remarksController,
                        themeData: themeData,
                        fieldKey: kUserAdminFieldRemarks,
                        maxLines: 3,
                      ),
                    ],
                  ),
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(dialogContext).pop(),
                child: Text('common.cancel'.tr),
              ),
              ElevatedButton(
                onPressed: () async {
                  if (!formKey.currentState!.validate()) return;
                  if (!await _validateJwtToken()) return;

                  final nextUsername = usernameController.text.trim();

                  try {
                    await userApi.initializeWithJwt();
                    if (nextUsername != (user.username ?? '')) {
                      final isAvailable =
                          await _checkUsernameAvailability(nextUsername);
                      if (!isAvailable) {
                        _showSnackBar(
                          'userAdmin.validation.usernameExists'.tr,
                          isError: true,
                        );
                        return;
                      }
                    }

                    final updatedUser = user.copyWith(
                      username: nextUsername,
                      password: passwordController.text.trim().isEmpty
                          ? user.password
                          : passwordController.text.trim(),
                      contactNumber: _emptyToNull(contactNumberController.text),
                      email: _emptyToNull(emailController.text),
                      department: _emptyToNull(departmentController.text),
                      status: selectedStatus,
                      remarks: _emptyToNull(remarksController.text),
                    );

                    await userApi.apiUsersUserIdPut(
                      userId: '${user.userId}',
                      userManagement: updatedUser,
                      idempotencyKey: generateIdempotencyKey(),
                    );

                    if (!mounted || !dialogContext.mounted) return;
                    Navigator.of(dialogContext).pop();
                    _showSnackBar('userAdmin.success.updated'.tr);
                    await _refreshUsers();
                  } catch (e) {
                    _showSnackBar(
                      'userAdmin.error.updateFailed'.trParams({
                        'error': formatUserAdminError(e),
                      }),
                      isError: true,
                    );
                  }
                },
                child: Text('common.save'.tr),
              ),
            ],
          ),
        );
      },
    );

    usernameController.dispose();
    passwordController.dispose();
    contactNumberController.dispose();
    emailController.dispose();
    departmentController.dispose();
    remarksController.dispose();
  }

  Future<void> _deleteUser(UserManagement user) async {
    final themeData = controller.currentBodyTheme.value;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return Theme(
          data: themeData,
          child: AlertDialog(
            title: Text('userAdmin.delete.confirmTitle'.tr),
            content: Text('userAdmin.delete.confirmBody'.tr),
            backgroundColor: themeData.colorScheme.surfaceContainerLowest,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16.0),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(dialogContext).pop(false),
                child: Text('common.cancel'.tr),
              ),
              ElevatedButton(
                onPressed: () => Navigator.of(dialogContext).pop(true),
                style: ElevatedButton.styleFrom(
                  backgroundColor: themeData.colorScheme.error,
                  foregroundColor: themeData.colorScheme.onError,
                ),
                child: Text('userAdmin.action.delete'.tr),
              ),
            ],
          ),
        );
      },
    );

    if (confirmed != true) return;
    if (!await _validateJwtToken()) return;

    try {
      await userApi.initializeWithJwt();
      await userApi.apiUsersUserIdDelete(userId: '${user.userId}');
      _showSnackBar('userAdmin.success.deleted'.tr);
      await _refreshUsers();
    } catch (e) {
      _showSnackBar(
        'userAdmin.error.deleteFailed'.trParams({
          'error': formatUserAdminError(e),
        }),
        isError: true,
      );
    }
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required ThemeData themeData,
    required String fieldKey,
    bool isRequired = false,
    bool obscureText = false,
    int maxLines = 1,
    TextInputType? keyboardType,
    String? helperText,
  }) {
    return TextFormField(
      controller: controller,
      decoration: InputDecoration(
        labelText: userAdminFieldLabel(fieldKey, required: isRequired),
        helperText: helperText,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12.0),
        ),
        filled: true,
        fillColor: themeData.colorScheme.surfaceContainer,
      ),
      obscureText: obscureText,
      maxLines: obscureText ? 1 : maxLines,
      keyboardType: keyboardType,
      validator: (value) => validateUserAdminField(
        fieldKey,
        value,
        required: isRequired,
      ),
    );
  }

  Widget _buildStatusField({
    required ThemeData themeData,
    required String initialValue,
    required ValueChanged<String?> onChanged,
  }) {
    return DropdownButtonFormField<String>(
      initialValue: initialValue,
      decoration: InputDecoration(
        labelText: userAdminFieldLabel(kUserAdminFieldStatus, required: true),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12.0),
        ),
        filled: true,
        fillColor: themeData.colorScheme.surfaceContainer,
      ),
      items: const [kUserAdminStatusActive, kUserAdminStatusInactive]
          .map(
            (status) => DropdownMenuItem<String>(
              value: status,
              child: Text(userAdminStatusKey(status).tr),
            ),
          )
          .toList(),
      onChanged: onChanged,
      validator: (value) {
        if (value == null || value.isEmpty) {
          return 'userAdmin.validation.statusRequired'.tr;
        }
        return null;
      },
    );
  }

  Widget _buildSearchCard(ThemeData themeData) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: themeData.colorScheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(26),
        border: Border.all(
          color: themeData.colorScheme.outline.withValues(alpha: 0.12),
        ),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final stacked = constraints.maxWidth < 880;
          final searchField = TextField(
            controller: _searchController,
            decoration: InputDecoration(
              labelText: 'userAdmin.workspace.filterTitle'.tr,
              hintText: userAdminSearchHintKey(_searchType).tr,
              prefixIcon: const Icon(Icons.search_rounded),
              suffixIcon: _searchController.text.trim().isEmpty
                  ? null
                  : IconButton(
                      onPressed: () {
                        _searchController.clear();
                        setState(() {});
                        _refreshUsersWithQuery(query: '');
                      },
                      icon: const Icon(Icons.clear_rounded),
                    ),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(18.0),
                borderSide: BorderSide.none,
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(18.0),
                borderSide: BorderSide(
                  color: themeData.colorScheme.outline.withValues(alpha: 0.14),
                ),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(18.0),
                borderSide: BorderSide(
                  color: themeData.colorScheme.primary,
                  width: 1.4,
                ),
              ),
              filled: true,
              fillColor: themeData.colorScheme.surface,
            ),
            onChanged: (value) {
              setState(() {});
              _scheduleSearchRefresh(value);
            },
            onSubmitted: (value) => _refreshUsersWithQuery(query: value),
          );
          final modePicker = DropdownButtonFormField<String>(
            initialValue: _searchType,
            decoration: InputDecoration(
              labelText: 'userAdmin.workspace.filterMode'.tr,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(18.0),
                borderSide: BorderSide.none,
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(18.0),
                borderSide: BorderSide(
                  color: themeData.colorScheme.outline.withValues(alpha: 0.14),
                ),
              ),
              filled: true,
              fillColor: themeData.colorScheme.surface,
            ),
            items: const [
              kUserAdminSearchTypeUsername,
              kUserAdminSearchTypeStatus,
              kUserAdminSearchTypeDepartment,
              kUserAdminSearchTypeContactNumber,
              kUserAdminSearchTypeEmail,
            ]
                .map(
                  (type) => DropdownMenuItem<String>(
                    value: type,
                    child: Text(userAdminSearchTypeLabelKey(type).tr),
                  ),
                )
                .toList(),
            onChanged: (value) {
              if (value == null) return;
              setState(() {
                _searchType = value;
              });
              _refreshUsersWithQuery(query: _searchController.text);
            },
          );
          final actions = Wrap(
            spacing: 12,
            runSpacing: 12,
            alignment: stacked ? WrapAlignment.start : WrapAlignment.end,
            children: [
              if (_hasActiveFilters)
                OutlinedButton.icon(
                  onPressed: () {
                    _searchController.clear();
                    setState(() {
                      _searchType = kUserAdminSearchTypeUsername;
                    });
                    _refreshUsersWithQuery(query: '');
                  },
                  icon: const Icon(Icons.layers_clear_outlined),
                  label: Text('userAdmin.workspace.filterReset'.tr),
                ),
              FilledButton.tonalIcon(
                onPressed: _refreshUsers,
                icon: const Icon(Icons.refresh_rounded),
                label: Text('userAdmin.workspace.filterRefresh'.tr),
              ),
            ],
          );

          if (stacked) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                searchField,
                const SizedBox(height: 16),
                modePicker,
                const SizedBox(height: 16),
                actions,
              ],
            );
          }

          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(flex: 5, child: searchField),
              const SizedBox(width: 16),
              Expanded(flex: 3, child: modePicker),
              const SizedBox(width: 16),
              Expanded(flex: 2, child: actions),
            ],
          );
        },
      ),
    );
  }

  Widget _buildStateView(
    ThemeData themeData, {
    required IconData icon,
    required Color color,
    required String title,
    required String message,
    bool showReloginAction = false,
  }) {
    return Center(
      child: Container(
        constraints: const BoxConstraints(maxWidth: 460),
        padding: const EdgeInsets.all(28),
        decoration: BoxDecoration(
          color: themeData.colorScheme.surfaceContainer,
          borderRadius: BorderRadius.circular(28),
          border: Border.all(
            color: themeData.colorScheme.outline.withValues(alpha: 0.12),
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 48, color: color),
            const SizedBox(height: 16),
            Text(
              title,
              style: themeData.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w700,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 10),
            Text(
              message,
              style: themeData.textTheme.bodyMedium?.copyWith(
                color: themeData.colorScheme.onSurfaceVariant,
                height: 1.5,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 18),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              alignment: WrapAlignment.center,
              children: [
                FilledButton.tonalIcon(
                  onPressed: _refreshUsers,
                  icon: const Icon(Icons.refresh_rounded),
                  label: Text('userAdmin.workspace.filterRefresh'.tr),
                ),
                if (showReloginAction)
                  FilledButton.icon(
                    onPressed: () => Get.offAllNamed(Routes.login),
                    icon: const Icon(Icons.login_rounded),
                    label: Text('userAdmin.action.relogin'.tr),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildUserList(ThemeData themeData) {
    return RefreshIndicator(
      onRefresh: _refreshUsers,
      color: themeData.colorScheme.primary,
      backgroundColor: themeData.colorScheme.surfaceContainer,
      child: ListView.separated(
        controller: _scrollController,
        physics: const AlwaysScrollableScrollPhysics(),
        itemCount: _filteredUsers.length +
            ((_isLoading && _allUsers.isNotEmpty) ? 1 : 0),
        separatorBuilder: (_, index) => index >= _filteredUsers.length - 1
            ? const SizedBox.shrink()
            : const SizedBox(height: 12),
        itemBuilder: (context, index) {
          if (index >= _filteredUsers.length) {
            return const Padding(
              padding: EdgeInsets.symmetric(vertical: 16),
              child: Center(
                child: CupertinoActivityIndicator(radius: 12),
              ),
            );
          }
          final user = _filteredUsers[index];
          final isActive =
              normalizeAccountStatusCode(user.status) == kUserAdminStatusActive;
          final accent =
              isActive ? const Color(0xFF1F9D68) : const Color(0xFFC45A4E);
          return Container(
            width: double.infinity,
            padding: const EdgeInsets.all(22),
            decoration: BoxDecoration(
              color: themeData.colorScheme.surfaceContainerLowest,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(
                color: themeData.colorScheme.outline.withValues(alpha: 0.12),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            user.username?.trim().isNotEmpty == true
                                ? user.username!
                                : 'userAdmin.value.unknownUser'.tr,
                            style: themeData.textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 10),
                          Wrap(
                            spacing: 12,
                            runSpacing: 12,
                            children: [
                              _UserStatusBadge(
                                label: userAdminStatusKey(user.status).tr,
                                color: accent,
                              ),
                              _UserMetaChip(
                                icon: Icons.badge_outlined,
                                label: user.realName?.trim().isNotEmpty == true
                                    ? user.realName!
                                    : 'common.notFilled'.tr,
                              ),
                              _UserMetaChip(
                                icon: Icons.schedule_rounded,
                                label: formatUserAdminDateTime(
                                  user.modifiedTime,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 16,
                  runSpacing: 12,
                  children: [
                    _UserMetaChip(
                      icon: Icons.apartment_outlined,
                      label: userAdminDisplayValue(user.department),
                    ),
                    _UserMetaChip(
                      icon: Icons.call_outlined,
                      label: userAdminDisplayValue(user.contactNumber),
                    ),
                    _UserMetaChip(
                      icon: Icons.mail_outline_rounded,
                      label: userAdminDisplayValue(user.email),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(18),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        userAdminFieldTranslationKey(kUserAdminFieldRemarks).tr,
                        style: themeData.textTheme.labelLarge?.copyWith(
                          color: themeData.colorScheme.onSurfaceVariant,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        userAdminDisplayValue(user.remarks),
                        style: themeData.textTheme.bodyMedium?.copyWith(
                          height: 1.45,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 14),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    IconButton(
                      tooltip: 'userAdmin.action.manageRoles'.tr,
                      onPressed: () => _showManageRolesDialog(user),
                      icon: Icon(
                        Icons.admin_panel_settings_outlined,
                        color: themeData.colorScheme.secondary,
                      ),
                    ),
                    IconButton(
                      tooltip: 'userAdmin.action.edit'.tr,
                      onPressed: () => _showEditUserDialog(user),
                      icon: Icon(
                        Icons.edit_outlined,
                        color: themeData.colorScheme.primary,
                      ),
                    ),
                    IconButton(
                      tooltip: 'userAdmin.action.delete'.tr,
                      onPressed: () => _deleteUser(user),
                      icon: Icon(
                        Icons.delete_outline,
                        color: themeData.colorScheme.error,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  String? _emptyToNull(String value) {
    final trimmed = value.trim();
    return trimmed.isEmpty ? null : trimmed;
  }

  bool _isRoleActive(RoleManagement role) {
    final status = normalizeAccountStatusCode(role.status);
    return status.isEmpty || status == kUserAdminStatusActive;
  }

  int? _readInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse(value?.toString() ?? '');
  }

  Set<int> _boundRoleIds(List<Map<String, dynamic>> bindings) {
    return bindings
        .map((binding) => _readInt(binding['roleId']))
        .whereType<int>()
        .toSet();
  }

  String _roleLabel(RoleManagement? role, int? roleId) {
    if (role == null) {
      return roleId == null ? 'common.none'.tr : 'ROLE#$roleId';
    }
    if (role.roleName?.trim().isNotEmpty == true &&
        role.roleCode?.trim().isNotEmpty == true) {
      return '${role.roleName} (${role.roleCode})';
    }
    if (role.roleName?.trim().isNotEmpty == true) {
      return role.roleName!;
    }
    if (role.roleCode?.trim().isNotEmpty == true) {
      return role.roleCode!;
    }
    return 'ROLE#${role.roleId}';
  }

  Future<List<RoleManagement>> _fetchAllRoles() async {
    final roles = <RoleManagement>[];
    var page = 1;
    while (true) {
      final pageRoles = await roleApi.apiRolesGet(
        page: page,
        size: _rolePageSize,
      );
      roles.addAll(pageRoles);
      if (pageRoles.length < _rolePageSize) {
        break;
      }
      page++;
    }
    return roles;
  }

  Future<void> _showManageRolesDialog(UserManagement user) async {
    if (user.userId == null) {
      _showSnackBar(
        'userAdmin.error.notFound'.trParams({'message': 'userId'}),
        isError: true,
      );
      return;
    }
    if (!await _validateJwtToken()) return;

    try {
      await userApi.initializeWithJwt();
      await roleApi.initializeWithJwt();

      final allRoles = await _fetchAllRoles();
      final availableRoles = allRoles
          .where((role) => role.roleId != null && _isRoleActive(role))
          .toList();
      final roleById = <int, RoleManagement>{
        for (final role in availableRoles) role.roleId!: role,
      };

      var bindings = await userApi.apiUsersUserIdRolesGet(userId: user.userId!);
      var dialogBusy = false;

      int? firstAvailableRoleId() {
        final assigned = _boundRoleIds(bindings);
        for (final role in availableRoles) {
          final roleId = role.roleId;
          if (roleId != null && !assigned.contains(roleId)) {
            return roleId;
          }
        }
        return null;
      }

      int? selectedRoleId = firstAvailableRoleId();

      if (!mounted) return;

      await showDialog<void>(
        context: context,
        builder: (dialogContext) {
          final themeData = controller.currentBodyTheme.value;
          return StatefulBuilder(
            builder: (context, setDialogState) {
              final assignedRoleIds = _boundRoleIds(bindings);
              final selectableRoles = availableRoles
                  .where((role) => !assignedRoleIds.contains(role.roleId))
                  .toList();

              if (selectedRoleId != null &&
                  selectableRoles
                      .every((role) => role.roleId != selectedRoleId)) {
                selectedRoleId = selectableRoles.isNotEmpty
                    ? selectableRoles.first.roleId
                    : null;
              }

              Future<void> reloadBindings() async {
                bindings =
                    await userApi.apiUsersUserIdRolesGet(userId: user.userId!);
                selectedRoleId = firstAvailableRoleId();
              }

              Future<void> addRole() async {
                if (selectedRoleId == null) {
                  _showSnackBar(
                    'userAdmin.validation.roleRequired'.tr,
                    isError: true,
                  );
                  return;
                }
                setDialogState(() => dialogBusy = true);
                try {
                  await userApi.apiUsersUserIdRolesPost(
                    userId: user.userId!,
                    body: {
                      'userId': user.userId,
                      'roleId': selectedRoleId,
                    },
                    idempotencyKey: generateIdempotencyKey(),
                  );
                  await reloadBindings();
                  if (mounted) {
                    _showSnackBar('userAdmin.success.roleAdded'.tr);
                  }
                  setDialogState(() {});
                } catch (e) {
                  if (mounted) {
                    _showSnackBar(
                      'userAdmin.error.roleLoadFailed'
                          .trParams({'error': formatUserAdminError(e)}),
                      isError: true,
                    );
                  }
                } finally {
                  if (dialogContext.mounted) {
                    setDialogState(() => dialogBusy = false);
                  }
                }
              }

              Future<void> removeRole(int relationId) async {
                setDialogState(() => dialogBusy = true);
                try {
                  await userApi.apiUsersRolesRelationIdDelete(
                    relationId: relationId,
                  );
                  await reloadBindings();
                  if (mounted) {
                    _showSnackBar('userAdmin.success.roleRemoved'.tr);
                  }
                  setDialogState(() {});
                } catch (e) {
                  if (mounted) {
                    _showSnackBar(
                      'userAdmin.error.roleLoadFailed'
                          .trParams({'error': formatUserAdminError(e)}),
                      isError: true,
                    );
                  }
                } finally {
                  if (dialogContext.mounted) {
                    setDialogState(() => dialogBusy = false);
                  }
                }
              }

              return Theme(
                data: themeData,
                child: AlertDialog(
                  title: Text(
                    'userAdmin.dialog.manageRolesTitle'.trParams(
                        {'username': user.username ?? '${user.userId}'}),
                  ),
                  backgroundColor: themeData.colorScheme.surfaceContainerLowest,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16.0),
                  ),
                  content: SizedBox(
                    width: 480,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'userAdmin.action.manageRoles'.tr,
                          style: themeData.textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 12),
                        if (bindings.isEmpty)
                          Text(
                            'userAdmin.empty.roles'.tr,
                            style: themeData.textTheme.bodyMedium,
                          )
                        else
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: bindings.map((binding) {
                              final relationId = _readInt(binding['id']);
                              final roleId = _readInt(binding['roleId']);
                              return InputChip(
                                label:
                                    Text(_roleLabel(roleById[roleId], roleId)),
                                onDeleted: dialogBusy || relationId == null
                                    ? null
                                    : () => removeRole(relationId),
                              );
                            }).toList(),
                          ),
                        const SizedBox(height: 20),
                        DropdownButtonFormField<int>(
                          initialValue: selectedRoleId,
                          decoration: InputDecoration(
                            labelText: 'userAdmin.hint.selectRole'.tr,
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12.0),
                            ),
                            filled: true,
                            fillColor: themeData.colorScheme.surfaceContainer,
                          ),
                          items: selectableRoles
                              .map(
                                (role) => DropdownMenuItem<int>(
                                  value: role.roleId,
                                  child: Text(_roleLabel(role, role.roleId)),
                                ),
                              )
                              .toList(),
                          onChanged: dialogBusy
                              ? null
                              : (value) {
                                  setDialogState(() => selectedRoleId = value);
                                },
                        ),
                      ],
                    ),
                  ),
                  actions: [
                    TextButton(
                      onPressed: dialogBusy
                          ? null
                          : () => Navigator.of(dialogContext).pop(),
                      child: Text('common.cancel'.tr),
                    ),
                    ElevatedButton(
                      onPressed: dialogBusy || selectableRoles.isEmpty
                          ? null
                          : addRole,
                      child: Text('common.add'.tr),
                    ),
                  ],
                ),
              );
            },
          );
        },
      );
    } catch (e) {
      _showSnackBar(
        'userAdmin.error.roleLoadFailed'
            .trParams({'error': formatUserAdminError(e)}),
        isError: true,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final themeData = controller.currentBodyTheme.value;

      return DashboardPageTemplate(
        theme: themeData,
        title: 'userAdmin.page.title'.tr,
        pageType: DashboardPageType.admin,
        bodyIsScrollable: true,
        padding: EdgeInsets.zero,
        onThemeToggle: controller.toggleBodyTheme,
        actions: [
          if (_isAdmin)
            DashboardPageBarAction(
              icon: Icons.person_add_alt_1_outlined,
              onPressed: () => _showCreateUserDialog(),
              tooltip: 'userAdmin.action.create'.tr,
            ),
          DashboardPageBarAction(
            icon: Icons.refresh,
            onPressed: () => _refreshUsers(),
            tooltip: 'userAdmin.action.refresh'.tr,
          ),
        ],
        body: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_isAdmin) ...[
                _buildHeroSection(themeData),
                const SizedBox(height: 24),
                _buildSectionHeading(
                  themeData,
                  eyebrow: 'userAdmin.workspace.filterEyebrow'.tr,
                  title: 'userAdmin.workspace.filterTitle'.tr,
                  description: 'userAdmin.workspace.filterBody'.tr,
                ),
                const SizedBox(height: 18),
                _buildSearchCard(themeData),
                const SizedBox(height: 24),
                _buildSectionHeading(
                  themeData,
                  eyebrow: 'userAdmin.workspace.listEyebrow'.tr,
                  title: 'userAdmin.workspace.listTitle'.tr,
                  description: 'userAdmin.workspace.listBody'.tr,
                ),
                const SizedBox(height: 18),
              ],
              Expanded(
                child: _isLoading && _allUsers.isEmpty
                    ? Center(
                        child: CupertinoActivityIndicator(
                          color: themeData.colorScheme.primary,
                          radius: 16,
                        ),
                      )
                    : _statusMessage.isNotEmpty && _filteredUsers.isEmpty
                        ? _buildStateView(
                            themeData,
                            icon: CupertinoIcons.exclamationmark_triangle,
                            color: themeData.colorScheme.error,
                            title: 'userAdmin.workspace.errorTitle'.tr,
                            message: _statusMessage,
                            showReloginAction: _showReloginAction,
                          )
                        : _filteredUsers.isEmpty
                            ? _buildStateView(
                                themeData,
                                icon: CupertinoIcons.person_2,
                                color: themeData.colorScheme.onSurfaceVariant,
                                title: 'userAdmin.workspace.emptyTitle'.tr,
                                message: _searchController.text.trim().isEmpty
                                    ? 'userAdmin.empty.default'.tr
                                    : 'userAdmin.empty.filtered'.tr,
                              )
                            : _buildUserList(themeData),
              ),
            ],
          ),
        ),
      );
    });
  }
}

class _UserHeroBadge extends StatelessWidget {
  const _UserHeroBadge({
    required this.label,
    required this.foregroundColor,
    this.backgroundColor,
    this.filled = false,
  });

  final String label;
  final Color foregroundColor;
  final Color? backgroundColor;
  final bool filled;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color:
            filled ? backgroundColor : foregroundColor.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: filled
              ? backgroundColor!.withValues(alpha: 0.24)
              : foregroundColor.withValues(alpha: 0.14),
        ),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: filled ? Colors.white : foregroundColor,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.6,
            ),
      ),
    );
  }
}

class _UserInlineSignal extends StatelessWidget {
  const _UserInlineSignal({
    required this.icon,
    required this.label,
    required this.color,
  });

  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: 8),
          Text(
            label,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: color.withValues(alpha: 0.86),
                ),
          ),
        ],
      ),
    );
  }
}

class _UserMetricTile extends StatelessWidget {
  const _UserMetricTile({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final themeData = Theme.of(context);
    return Container(
      constraints: const BoxConstraints(minWidth: 132),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: themeData.brightness == Brightness.dark
            ? Colors.white.withValues(alpha: 0.08)
            : const Color(0xFFF8FBFB),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            value,
            style: themeData.textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: themeData.textTheme.bodySmall?.copyWith(
              color: themeData.colorScheme.onSurface.withValues(alpha: 0.7),
            ),
          ),
        ],
      ),
    );
  }
}

class _UserStatusBadge extends StatelessWidget {
  const _UserStatusBadge({
    required this.label,
    required this.color,
  });

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: color,
              fontWeight: FontWeight.w700,
            ),
      ),
    );
  }
}

class _UserMetaChip extends StatelessWidget {
  const _UserMetaChip({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    final themeData = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: themeData.colorScheme.surfaceContainerHighest
            .withValues(alpha: 0.45),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: themeData.colorScheme.primary),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              label,
              style: themeData.textTheme.bodySmall?.copyWith(
                color: themeData.colorScheme.onSurfaceVariant,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}
