// ignore_for_file: use_build_context_synchronously
import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:final_assignment_front/constants/app_constants.dart';
import 'package:final_assignment_front/config/routes/app_routes.dart';
import 'package:final_assignment_front/config/themes/app_theme.dart';
import 'package:final_assignment_front/features/api/auth_controller_api.dart';
import 'package:final_assignment_front/features/api/driver_information_controller_api.dart';
import 'package:final_assignment_front/features/api/user_management_controller_api.dart';
import 'package:final_assignment_front/features/dashboard/controllers/chat_controller.dart';
import 'package:final_assignment_front/i18n/auth_localizers.dart';
import 'package:final_assignment_front/features/model/login_request.dart';
import 'package:final_assignment_front/features/model/register_request.dart';
import 'package:final_assignment_front/shared_components/local_captcha_main.dart';
import 'package:final_assignment_front/shared_components/responsive_builder.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:final_assignment_front/utils/helpers/role_utils.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';

String generateIdempotencyKey() =>
    DateTime.now().millisecondsSinceEpoch.toString();

mixin ValidatorMixin {
  String? validateEmail(String? value) {
    if (value == null || value.isEmpty) {
      return 'auth.validation.emailRequired'.tr;
    }
    final emailRegex =
        RegExp(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$');
    if (!emailRegex.hasMatch(value)) {
      return 'auth.validation.emailInvalid'.tr;
    }
    return null;
  }

  String? validatePassword(String? value) {
    if (value == null || value.isEmpty) {
      return 'auth.validation.passwordRequired'.tr;
    }
    if (value.length < 5) {
      return 'auth.validation.passwordShort'.tr;
    }
    return null;
  }
}

enum _AuthMode { login, register }

class LoginScreen extends StatefulWidget with ValidatorMixin {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> with ValidatorMixin {
  late final AuthControllerApi authApi;
  late final DriverInformationControllerApi driverApi;

  final _loginFormKey = GlobalKey<FormState>();
  final _registerFormKey = GlobalKey<FormState>();
  final _loginEmailController = TextEditingController();
  final _loginPasswordController = TextEditingController();
  final _registerEmailController = TextEditingController();
  final _registerPasswordController = TextEditingController();
  final _registerConfirmController = TextEditingController();

  bool _isDarkMode = false;
  bool _isSubmitting = false;
  bool _hasSentRegisterRequest = false;
  bool _obscureLoginPassword = true;
  bool _obscureRegisterPassword = true;
  bool _obscureConfirmPassword = true;
  _AuthMode _mode = _AuthMode.login;
  String? _userRole;

  ThemeData get _pageTheme =>
      _isDarkMode ? AppTheme.basicDark : AppTheme.basicLight;

  String get _landingRoute {
    switch (_userRole) {
      case 'ADMIN':
        return Routes.dashboard;
      case 'MANAGER':
        return Routes.managerDashboard;
      default:
        return Routes.userDashboard;
    }
  }

  void setMode(_AuthMode mode) {
    setState(() => _mode = mode);
  }

  void toggleLoginPasswordVisibility() {
    setState(() => _obscureLoginPassword = !_obscureLoginPassword);
  }

  void toggleRegisterPasswordVisibility() {
    setState(() => _obscureRegisterPassword = !_obscureRegisterPassword);
  }

  void toggleConfirmPasswordVisibility() {
    setState(() => _obscureConfirmPassword = !_obscureConfirmPassword);
  }

  @override
  void initState() {
    super.initState();
    authApi = AuthControllerApi();
    driverApi = DriverInformationControllerApi();
    if (!Get.isRegistered<ChatController>()) {
      Get.lazyPut(() => ChatController());
    }
    _loadTheme();
  }

  @override
  void dispose() {
    _loginEmailController.dispose();
    _loginPasswordController.dispose();
    _registerEmailController.dispose();
    _registerPasswordController.dispose();
    _registerConfirmController.dispose();
    super.dispose();
  }

  Future<void> _loadTheme() async {
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) return;
    setState(() => _isDarkMode = prefs.getBool('isDarkMode') ?? false);
  }

  Future<void> _toggleTheme() async {
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) return;
    setState(() => _isDarkMode = !_isDarkMode);
    await prefs.setBool('isDarkMode', _isDarkMode);
  }

  Map<String, dynamic> _decodeJwt(String token) {
    final parts = token.split('.');
    if (parts.length != 3) throw const FormatException('invalid_jwt');
    final payload = base64Url.decode(base64Url.normalize(parts[1]));
    return jsonDecode(utf8.decode(payload));
  }

  Future<void> _handleLogin() async {
    if (!_loginFormKey.currentState!.validate()) return;
    setState(() => _isSubmitting = true);
    final error = await _authenticateUser(
      _loginEmailController.text.trim(),
      _loginPasswordController.text.trim(),
    );
    if (mounted) setState(() => _isSubmitting = false);
    if (error == null) {
      Get.offAllNamed(_landingRoute);
      return;
    }
    _showMessage(error, isError: true);
  }

  Future<void> _handleRegister() async {
    if (!_registerFormKey.currentState!.validate()) return;
    if (_registerPasswordController.text != _registerConfirmController.text) {
      _showMessage('auth.error.passwordMismatch'.tr, isError: true);
      return;
    }
    if (_hasSentRegisterRequest) {
      _showMessage('auth.error.registering'.tr, isError: true);
      return;
    }
    final isCaptchaValid = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (context) => const LocalCaptchaMain(),
    );
    if (isCaptchaValid != true) {
      _showMessage('auth.error.registerCancelled'.tr, isError: true);
      return;
    }
    setState(() => _isSubmitting = true);
    final error = await _registerUser(
      _registerEmailController.text.trim(),
      _registerPasswordController.text.trim(),
    );
    if (mounted) setState(() => _isSubmitting = false);
    if (error == null) {
      Get.offAllNamed(_landingRoute);
      return;
    }
    _showMessage(error, isError: true);
  }

  Future<String?> _authenticateUser(String username, String password) async {
    try {
      final result = await authApi.apiAuthLoginPost(
        loginRequest: LoginRequest(username: username, password: password),
      );
      if (!result.containsKey('jwtToken')) {
        return result['message'] ?? 'auth.error.loginFailed'.tr;
      }

      final jwtToken = result['jwtToken'];
      final decodedJwt = _decodeJwt(jwtToken);
      final roleCodes = normalizeRoleCodes(decodedJwt['roles']);
      _userRole = resolveWorkspaceRole(roleCodes);

      final prefs = await SharedPreferences.getInstance();
      await AuthTokenStore.instance.setJwtToken(jwtToken);
      final refreshToken = result['refreshToken']?.toString();
      await AuthTokenStore.instance.setRefreshToken(refreshToken);
      await prefs.setString('userRole', _userRole!);
      await prefs.setStringList('userRoles', roleCodes);
      await prefs.setString('userName', username);

      final userData = result['user'] ?? {};
      final int? userIdFromLogin = userData['userId'];
      String resolvedName = userData['realName'] ??
          userData['username'] ??
          username.split('@').first;
      String resolvedEmail = userData['email'] ?? username;

      await driverApi.initializeWithJwt();
      final userManagementApi = UserManagementControllerApi();
      await userManagementApi.initializeWithJwt();

      int? userId = userIdFromLogin;
      try {
        final userInfo = await userManagementApi.apiUsersMeGet();
        if (userInfo != null) {
          userId = userInfo.userId ?? userId;
          resolvedName = userInfo.realName ?? userInfo.username ?? resolvedName;
          resolvedEmail = userInfo.email ?? resolvedEmail;
        }
      } catch (_) {}

      String driverName = resolvedName;
      try {
        final driverInfo = await driverApi.apiDriversMeGet();
        if (driverInfo?.name != null && driverInfo!.name!.isNotEmpty) {
          driverName = driverInfo.name!;
        }
      } catch (error) {
        if (error is! ApiException || error.code != 404) {
          rethrow;
        }
      }

      await prefs.setString('displayName', driverName);
      await prefs.setString('driverName', driverName);
      await prefs.setString('userEmail', resolvedEmail);
      if (userId != null) {
        await prefs.setString('userId', userId.toString());
      }

      Get.find<ChatController>().setUserRole(_userRole!);
      return null;
    } on FormatException {
      return 'auth.error.invalidJwt'.tr;
    } on ApiException catch (error) {
      return formatAuthApiError(error, 'auth.error.loginFailed'.tr);
    } catch (error) {
      return 'auth.error.loginError'.trParams({
        'error': formatAuthErrorDetail(error),
      });
    }
  }

  Future<String?> _registerUser(String username, String password) async {
    try {
      final registerResult = await authApi.apiAuthRegisterPost(
        registerRequest: RegisterRequest(
          username: username,
          password: password,
          idempotencyKey: generateIdempotencyKey(),
        ),
      );
      if (registerResult['status'] != 'CREATED') {
        return registerResult['error'] ?? 'auth.error.registerFailed'.tr;
      }
      _hasSentRegisterRequest = true;
      return _authenticateUser(username, password);
    } on ApiException catch (error) {
      return formatAuthApiError(error, 'auth.error.registerFailed'.tr);
    } catch (error) {
      return 'auth.error.registerError'.trParams({
        'error': formatAuthErrorDetail(error),
      });
    }
  }

  Future<void> _showResetPasswordDialog() async {
    final formKey = GlobalKey<FormState>();
    final currentPasswordController = TextEditingController();
    final newPasswordController = TextEditingController();
    final confirmPasswordController = TextEditingController();
    bool obscureCurrentPassword = true;
    bool obscureNewPassword = true;
    bool obscureConfirmPassword = true;

    try {
      final result = await showDialog<bool>(
        context: context,
        builder: (context) => Theme(
          data: _pageTheme,
          child: StatefulBuilder(
            builder: (context, dialogSetState) => AlertDialog(
              title: Text('auth.resetPassword'.tr),
              content: Form(
                key: formKey,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextFormField(
                      controller: currentPasswordController,
                      validator: validatePassword,
                      obscureText: obscureCurrentPassword,
                      decoration: InputDecoration(
                        labelText: 'auth.currentPassword'.tr,
                        suffixIcon: IconButton(
                          onPressed: () {
                            dialogSetState(() {
                              obscureCurrentPassword = !obscureCurrentPassword;
                            });
                          },
                          icon: Icon(
                            obscureCurrentPassword
                                ? Icons.visibility_outlined
                                : Icons.visibility_off_outlined,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: newPasswordController,
                      validator: validatePassword,
                      obscureText: obscureNewPassword,
                      decoration: InputDecoration(
                        labelText: 'auth.newPassword'.tr,
                        suffixIcon: IconButton(
                          onPressed: () {
                            dialogSetState(() {
                              obscureNewPassword = !obscureNewPassword;
                            });
                          },
                          icon: Icon(
                            obscureNewPassword
                                ? Icons.visibility_outlined
                                : Icons.visibility_off_outlined,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: confirmPasswordController,
                      validator: (value) {
                        final passwordError = validatePassword(value);
                        if (passwordError != null) {
                          return passwordError;
                        }
                        if (value!.trim() !=
                            newPasswordController.text.trim()) {
                          return 'auth.error.passwordMismatch'.tr;
                        }
                        return null;
                      },
                      obscureText: obscureConfirmPassword,
                      decoration: InputDecoration(
                        labelText: 'auth.confirmPassword'.tr,
                        suffixIcon: IconButton(
                          onPressed: () {
                            dialogSetState(() {
                              obscureConfirmPassword = !obscureConfirmPassword;
                            });
                          },
                          icon: Icon(
                            obscureConfirmPassword
                                ? Icons.visibility_outlined
                                : Icons.visibility_off_outlined,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context, false),
                  child: Text('common.cancel'.tr),
                ),
                FilledButton(
                  onPressed: () {
                    if (formKey.currentState?.validate() != true) {
                      return;
                    }
                    Navigator.pop(context, true);
                  },
                  child: Text('common.continue'.tr),
                ),
              ],
            ),
          ),
        ),
      );

      if (result != true) return;
      final isCaptchaValid = await showDialog<bool>(
        context: context,
        barrierDismissible: false,
        builder: (context) => const LocalCaptchaMain(),
      );
      if (isCaptchaValid != true) {
        _showMessage('auth.error.passwordResetCancelled'.tr, isError: true);
        return;
      }

      final jwtToken = await AuthTokenStore.instance.getJwtToken();
      if (jwtToken == null) {
        _showMessage('auth.error.loginRequiredForReset'.tr, isError: true);
        return;
      }

      try {
        final userManagementApi = UserManagementControllerApi();
        await userManagementApi.apiUsersMePasswordPut(
          currentPassword: currentPasswordController.text.trim(),
          newPassword: newPasswordController.text.trim(),
          idempotencyKey: generateIdempotencyKey(),
        );
        _showMessage('auth.success.passwordUpdated'.tr);
      } on ApiException catch (error) {
        _showMessage(
          formatAuthApiError(
            error,
            'auth.error.passwordResetFailed'.trParams(
              {'code': '${error.code}'},
            ),
          ),
          isError: true,
        );
      } catch (error) {
        _showMessage(
          'auth.error.passwordResetError'.trParams({
            'error': formatAuthErrorDetail(error),
          }),
          isError: true,
        );
      }
    } finally {
      currentPasswordController.dispose();
      newPasswordController.dispose();
      confirmPasswordController.dispose();
    }
  }

  void _showMessage(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor:
            isError ? Colors.red.shade700 : _pageTheme.colorScheme.primary,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = _pageTheme;
    final metrics = ResponsiveMetrics.of(context);

    return Theme(
      data: theme,
      child: Scaffold(
        backgroundColor: theme.scaffoldBackgroundColor,
        body: Stack(
          children: [
            const _LoginBackdrop(),
            SafeArea(
              child: LayoutBuilder(
                builder: (context, constraints) {
                  if (metrics.isDesktop || metrics.isWide) {
                    final authWidth = math.min(
                      constraints.maxWidth * 0.34,
                      430.0,
                    );

                    return Stack(
                      children: [
                        Positioned.fill(
                          child: _RevealIn(
                            delay: const Duration(milliseconds: 60),
                            child: _BrandPanel(
                              theme: theme,
                              darkMode: _isDarkMode,
                              fullBleed: true,
                            ),
                          ),
                        ),
                        Positioned(
                          top: 20,
                          left: 20,
                          right: 20,
                          child: Row(
                            children: [
                              Text(
                                'app.name'.tr,
                                style: theme.textTheme.titleLarge?.copyWith(
                                  color: Colors.white,
                                ),
                              ),
                              const Spacer(),
                              IconButton.filledTonal(
                                onPressed: _toggleTheme,
                                icon: const Icon(Icons.contrast_rounded),
                                tooltip: 'common.toggleTheme'.tr,
                              ),
                            ],
                          ),
                        ),
                        Positioned(
                          top: 88,
                          right: 32,
                          bottom: 32,
                          child: SizedBox(
                            width: authWidth,
                            child: Align(
                              alignment: Alignment.centerRight,
                              child: SingleChildScrollView(
                                padding: EdgeInsets.zero,
                                child: _RevealIn(
                                  delay: const Duration(milliseconds: 180),
                                  child: _AuthPanel(state: this, theme: theme),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    );
                  }

                  if (metrics.isTablet) {
                    final splitLayout = constraints.maxWidth >= 900 &&
                        constraints.maxWidth > constraints.maxHeight;

                    if (splitLayout) {
                      return Padding(
                        padding: EdgeInsets.all(metrics.pagePadding),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Expanded(
                              flex: 6,
                              child: _RevealIn(
                                delay: const Duration(milliseconds: 80),
                                child: SingleChildScrollView(
                                  child: _BrandPanel(
                                    theme: theme,
                                    darkMode: _isDarkMode,
                                    compact: true,
                                  ),
                                ),
                              ),
                            ),
                            SizedBox(width: metrics.sectionGap),
                            SizedBox(
                              width: math.min(
                                constraints.maxWidth * 0.36,
                                400.0,
                              ),
                              child: Column(
                                children: [
                                  Row(
                                    children: [
                                      Expanded(
                                        child: Text(
                                          'app.name'.tr,
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: theme.textTheme.titleLarge,
                                        ),
                                      ),
                                      IconButton.filledTonal(
                                        onPressed: _toggleTheme,
                                        icon:
                                            const Icon(Icons.contrast_rounded),
                                        tooltip: 'common.toggleTheme'.tr,
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 12),
                                  Expanded(
                                    child: Align(
                                      alignment: Alignment.center,
                                      child: SingleChildScrollView(
                                        child: _RevealIn(
                                          delay:
                                              const Duration(milliseconds: 180),
                                          child: _AuthPanel(
                                            state: this,
                                            theme: theme,
                                          ),
                                        ),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      );
                    }

                    return SingleChildScrollView(
                      padding: EdgeInsets.all(metrics.pagePadding),
                      child: Center(
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 900),
                          child: Column(
                            children: [
                              Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      'app.name'.tr,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: theme.textTheme.titleLarge,
                                    ),
                                  ),
                                  IconButton.filledTonal(
                                    onPressed: _toggleTheme,
                                    icon: const Icon(Icons.contrast_rounded),
                                    tooltip: 'common.toggleTheme'.tr,
                                  ),
                                ],
                              ),
                              SizedBox(height: metrics.sectionGap),
                              _RevealIn(
                                delay: const Duration(milliseconds: 80),
                                child: _BrandPanel(
                                  theme: theme,
                                  darkMode: _isDarkMode,
                                  compact: true,
                                ),
                              ),
                              SizedBox(height: metrics.sectionGap),
                              ConstrainedBox(
                                constraints:
                                    const BoxConstraints(maxWidth: 520),
                                child: _RevealIn(
                                  delay: const Duration(milliseconds: 180),
                                  child: _AuthPanel(state: this, theme: theme),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    );
                  }

                  return SingleChildScrollView(
                    padding: EdgeInsets.all(metrics.pagePadding),
                    child: Column(
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                'app.name'.tr,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: theme.textTheme.titleLarge,
                              ),
                            ),
                            IconButton(
                              onPressed: _toggleTheme,
                              icon: const Icon(Icons.contrast_rounded),
                              tooltip: 'common.toggleTheme'.tr,
                            ),
                          ],
                        ),
                        SizedBox(height: metrics.sectionGap),
                        _RevealIn(
                          delay: const Duration(milliseconds: 80),
                          child: _BrandPanel(
                            theme: theme,
                            darkMode: _isDarkMode,
                            compact: true,
                            fullBleed: true,
                          ),
                        ),
                        SizedBox(height: metrics.sectionGap),
                        _RevealIn(
                          delay: const Duration(milliseconds: 180),
                          child: _AuthPanel(state: this, theme: theme),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AuthPanel extends StatelessWidget {
  const _AuthPanel({
    required this.state,
    required this.theme,
  });

  final _LoginScreenState state;
  final ThemeData theme;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final narrow = constraints.maxWidth < 360;

        return _SurfaceFrame(
          padding: EdgeInsets.all(narrow ? 18 : 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  _PanelTag(label: 'common.workspace'.tr),
                  const Spacer(),
                  _ModePill(
                    label: state._mode == _AuthMode.login
                        ? 'common.login'.tr
                        : 'common.register'.tr,
                  ),
                ],
              ),
              const SizedBox(height: 18),
              Text(
                'auth.enterWorkspace'.tr,
                style: theme.textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text(
                'auth.enterWorkspaceBody'.tr,
                style: theme.textTheme.bodyMedium,
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  _StatusTile(
                    icon: Icons.radio_button_checked_rounded,
                    label: 'common.workspace'.tr,
                    value: 'common.online'.tr,
                    color: const Color(0xFF1F9D68),
                  ),
                  _StatusTile(
                    icon: Icons.route_rounded,
                    label: 'auth.metric.flow'.tr,
                    value: 'auth.metric.flowValue'.tr,
                    color: theme.colorScheme.primary,
                  ),
                  _StatusTile(
                    icon: Icons.bolt_rounded,
                    label: 'common.agent'.tr,
                    value: 'auth.metric.agentValue'.tr,
                    color: theme.colorScheme.tertiary,
                  ),
                ],
              ),
              const SizedBox(height: 18),
              Container(
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(
                  color: theme.colorScheme.surfaceContainerHighest
                      .withValues(alpha: 0.65),
                  borderRadius: BorderRadius.circular(22),
                  border: Border.all(
                    color: theme.colorScheme.outlineVariant
                        .withValues(alpha: 0.36),
                  ),
                ),
                child: SegmentedButton<_AuthMode>(
                  showSelectedIcon: false,
                  style: ButtonStyle(
                    visualDensity: VisualDensity.compact,
                    padding: WidgetStateProperty.all(
                      const EdgeInsets.symmetric(vertical: 14),
                    ),
                  ),
                  segments: [
                    ButtonSegment(
                      value: _AuthMode.login,
                      label: Text('common.login'.tr),
                    ),
                    ButtonSegment(
                      value: _AuthMode.register,
                      label: Text('common.register'.tr),
                    ),
                  ],
                  selected: {state._mode},
                  onSelectionChanged: (selection) {
                    state.setMode(selection.first);
                  },
                ),
              ),
              const SizedBox(height: 22),
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 320),
                switchInCurve: Curves.easeOutCubic,
                switchOutCurve: Curves.easeInCubic,
                transitionBuilder: (child, animation) {
                  final offset = Tween<Offset>(
                    begin: const Offset(0.04, 0),
                    end: Offset.zero,
                  ).animate(animation);
                  return FadeTransition(
                    opacity: animation,
                    child: SlideTransition(
                      position: offset,
                      child: child,
                    ),
                  );
                },
                child: state._mode == _AuthMode.login
                    ? _LoginForm(state: state)
                    : _RegisterForm(state: state),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _LoginForm extends StatelessWidget {
  const _LoginForm({required this.state});

  final _LoginScreenState state;

  @override
  Widget build(BuildContext context) {
    return Form(
      key: state._loginFormKey,
      child: Column(
        key: const ValueKey('login-form'),
        children: [
          TextFormField(
            controller: state._loginEmailController,
            validator: state.validateEmail,
            decoration: InputDecoration(
              labelText: 'auth.email'.tr,
              prefixIcon: const Icon(Icons.mail_outline_rounded),
            ),
          ),
          const SizedBox(height: 14),
          TextFormField(
            controller: state._loginPasswordController,
            validator: state.validatePassword,
            obscureText: state._obscureLoginPassword,
            decoration: InputDecoration(
              labelText: 'auth.password'.tr,
              prefixIcon: const Icon(Icons.lock_outline_rounded),
              suffixIcon: IconButton(
                onPressed: () {
                  state.toggleLoginPasswordVisibility();
                },
                icon: Icon(
                  state._obscureLoginPassword
                      ? Icons.visibility_outlined
                      : Icons.visibility_off_outlined,
                ),
              ),
            ),
          ),
          const SizedBox(height: 18),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: state._isSubmitting ? null : state._handleLogin,
              icon: const Icon(Icons.arrow_forward_rounded),
              label: Text(
                state._isSubmitting ? 'auth.signingIn'.tr : 'common.login'.tr,
              ),
            ),
          ),
          const SizedBox(height: 12),
          LayoutBuilder(
            builder: (context, constraints) {
              final compactActions = constraints.maxWidth < 360;

              if (compactActions) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    TextButton(
                      onPressed: state._isSubmitting
                          ? null
                          : state._showResetPasswordDialog,
                      child: Text('auth.resetPassword'.tr),
                    ),
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton(
                        onPressed: state._isSubmitting
                            ? null
                            : () => state.setMode(_AuthMode.register),
                        child: Text('auth.createAccount'.tr),
                      ),
                    ),
                  ],
                );
              }

              return Row(
                children: [
                  TextButton(
                    onPressed: state._isSubmitting
                        ? null
                        : state._showResetPasswordDialog,
                    child: Text('auth.resetPassword'.tr),
                  ),
                  const Spacer(),
                  TextButton(
                    onPressed: state._isSubmitting
                        ? null
                        : () => state.setMode(_AuthMode.register),
                    child: Text('auth.createAccount'.tr),
                  ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}

class _RegisterForm extends StatelessWidget {
  const _RegisterForm({required this.state});

  final _LoginScreenState state;

  @override
  Widget build(BuildContext context) {
    return Form(
      key: state._registerFormKey,
      child: Column(
        key: const ValueKey('register-form'),
        children: [
          TextFormField(
            controller: state._registerEmailController,
            validator: state.validateEmail,
            decoration: InputDecoration(
              labelText: 'auth.email'.tr,
              prefixIcon: const Icon(Icons.mail_outline_rounded),
            ),
          ),
          const SizedBox(height: 14),
          TextFormField(
            controller: state._registerPasswordController,
            validator: state.validatePassword,
            obscureText: state._obscureRegisterPassword,
            decoration: InputDecoration(
              labelText: 'auth.password'.tr,
              prefixIcon: const Icon(Icons.lock_outline_rounded),
              suffixIcon: IconButton(
                onPressed: () {
                  state.toggleRegisterPasswordVisibility();
                },
                icon: Icon(
                  state._obscureRegisterPassword
                      ? Icons.visibility_outlined
                      : Icons.visibility_off_outlined,
                ),
              ),
            ),
          ),
          const SizedBox(height: 14),
          TextFormField(
            controller: state._registerConfirmController,
            validator: state.validatePassword,
            obscureText: state._obscureConfirmPassword,
            decoration: InputDecoration(
              labelText: 'auth.confirmPassword'.tr,
              prefixIcon: const Icon(Icons.verified_user_outlined),
              suffixIcon: IconButton(
                onPressed: () {
                  state.toggleConfirmPasswordVisibility();
                },
                icon: Icon(
                  state._obscureConfirmPassword
                      ? Icons.visibility_outlined
                      : Icons.visibility_off_outlined,
                ),
              ),
            ),
          ),
          const SizedBox(height: 18),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: state._isSubmitting ? null : state._handleRegister,
              icon: const Icon(Icons.person_add_alt_1_rounded),
              label: Text(
                state._isSubmitting ? 'auth.creating'.tr : 'common.register'.tr,
              ),
            ),
          ),
          const SizedBox(height: 12),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: state._isSubmitting
                  ? null
                  : () => state.setMode(_AuthMode.login),
              child: Text('auth.backToLogin'.tr),
            ),
          ),
        ],
      ),
    );
  }
}

class _BrandPanel extends StatelessWidget {
  const _BrandPanel({
    required this.theme,
    required this.darkMode,
    this.compact = false,
    this.fullBleed = false,
  });

  final ThemeData theme;
  final bool darkMode;
  final bool compact;
  final bool fullBleed;

  @override
  Widget build(BuildContext context) {
    final content = LayoutBuilder(
      builder: (context, constraints) {
        final stacked = compact || constraints.maxWidth < 760;
        final hero = _BrandHero(
          theme: theme,
          compact: compact,
          fullBleed: fullBleed,
        );
        final rails = [
          _MetricRail(
            label: 'auth.metric.mode'.tr,
            value: darkMode ? 'common.dark'.tr : 'common.light'.tr,
          ),
          _MetricRail(
            label: 'auth.metric.flow'.tr,
            value: 'auth.metric.flowValue'.tr,
          ),
          _MetricRail(
            label: 'auth.metric.agent'.tr,
            value: 'auth.metric.agentValue'.tr,
          ),
        ];

        if (stacked) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              hero,
              const SizedBox(height: 20),
              ...rails
                  .expand((rail) => [rail, const SizedBox(height: 12)])
                  .toList()
                ..removeLast(),
            ],
          );
        }

        return Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(flex: 8, child: hero),
            const SizedBox(width: 24),
            Expanded(
              flex: 3,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (var i = 0; i < rails.length; i++) ...[
                    rails[i],
                    if (i != rails.length - 1) const SizedBox(height: 18),
                  ],
                ],
              ),
            ),
          ],
        );
      },
    );

    if (fullBleed) {
      return content;
    }

    return _SurfaceFrame(
      padding: EdgeInsets.all(compact ? 20 : 28),
      child: content,
    );
  }
}

class _BrandHero extends StatelessWidget {
  const _BrandHero({
    required this.theme,
    required this.compact,
    required this.fullBleed,
  });

  final ThemeData theme;
  final bool compact;
  final bool fullBleed;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final narrow = constraints.maxWidth < 360;
        final contentPadding = fullBleed
            ? EdgeInsets.fromLTRB(
                compact ? (narrow ? 18 : 24) : 44,
                compact ? (narrow ? 22 : 28) : 48,
                compact ? (narrow ? 18 : 24) : 40,
                compact ? (narrow ? 24 : 28) : 42,
              )
            : EdgeInsets.all(compact ? 18 : 24);

        return Container(
          constraints: BoxConstraints(minHeight: compact ? 360 : 560),
          padding: contentPadding,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(fullBleed ? 0 : 28),
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Color(0xFF061722),
                Color(0xFF0B3142),
                Color(0xFF145C65),
              ],
              stops: [0.08, 0.52, 1],
            ),
          ),
          child: Stack(
            children: [
              Positioned(
                top: -40,
                right: -40,
                child: _FloatDrift(
                  offset: const Offset(-12, 12),
                  duration: const Duration(milliseconds: 5200),
                  child: Container(
                    width: compact ? (narrow ? 140 : 180) : 260,
                    height: compact ? (narrow ? 140 : 180) : 260,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(
                        colors: [
                          Colors.white.withValues(alpha: 0.22),
                          Colors.white.withValues(alpha: 0.02),
                          Colors.transparent,
                        ],
                      ),
                    ),
                  ),
                ),
              ),
              Positioned(
                left: compact ? -80 : -20,
                bottom: compact ? (narrow ? 104 : 84) : 118,
                child: _FloatDrift(
                  offset: const Offset(14, -10),
                  duration: const Duration(milliseconds: 4800),
                  child: Container(
                    width: compact ? (narrow ? 140 : 180) : 260,
                    height: compact ? (narrow ? 140 : 180) : 260,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(
                        colors: [
                          theme.colorScheme.tertiary.withValues(alpha: 0.16),
                          Colors.transparent,
                        ],
                      ),
                    ),
                  ),
                ),
              ),
              Positioned(
                right: compact ? (narrow ? -28 : -18) : 24,
                bottom: compact ? (narrow ? 6 : -6) : 0,
                child: IgnorePointer(
                  child: _FloatDrift(
                    offset: const Offset(0, -10),
                    duration: const Duration(milliseconds: 4200),
                    child: Opacity(
                      opacity: 0.84,
                      child: SizedBox(
                        width: compact ? (narrow ? 148 : 200) : 360,
                        height: compact ? (narrow ? 112 : 150) : 260,
                        child: SvgPicture.asset(
                          ImageVectorPath.wavyBus,
                          fit: BoxFit.contain,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
              ConstrainedBox(
                constraints: BoxConstraints(
                  maxWidth: compact ? double.infinity : 560,
                ),
                child: Column(
                  mainAxisSize: compact ? MainAxisSize.min : MainAxisSize.max,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _RevealIn(
                      delay: const Duration(milliseconds: 80),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 8,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.10),
                          borderRadius: BorderRadius.circular(999),
                          border: Border.all(
                            color: Colors.white.withValues(alpha: 0.12),
                          ),
                        ),
                        child: Text(
                          'auth.brandBadge'.tr,
                          style: theme.textTheme.labelLarge?.copyWith(
                            color: Colors.white,
                          ),
                        ),
                      ),
                    ),
                    SizedBox(height: compact ? (narrow ? 18 : 22) : 30),
                    _RevealIn(
                      delay: const Duration(milliseconds: 140),
                      child: Text(
                        'app.name'.tr,
                        style: theme.textTheme.labelLarge?.copyWith(
                          color: Colors.white.withValues(alpha: 0.72),
                          letterSpacing: 1.6,
                        ),
                      ),
                    ),
                    const SizedBox(height: 10),
                    _RevealIn(
                      delay: const Duration(milliseconds: 180),
                      distance: 26,
                      child: Text(
                        'auth.brandTitle'.tr,
                        style: (compact
                                ? (narrow
                                    ? theme.textTheme.headlineLarge
                                    : theme.textTheme.displaySmall)
                                : theme.textTheme.displayLarge)
                            ?.copyWith(
                          color: Colors.white,
                          height: 0.94,
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),
                    _RevealIn(
                      delay: const Duration(milliseconds: 220),
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 460),
                        child: Text(
                          'auth.brandBody'.tr,
                          style: theme.textTheme.bodyLarge?.copyWith(
                            color: Colors.white.withValues(alpha: 0.80),
                            height: 1.45,
                          ),
                        ),
                      ),
                    ),
                    SizedBox(height: compact ? (narrow ? 18 : 22) : 28),
                    _RevealIn(
                      delay: const Duration(milliseconds: 260),
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 430),
                        child: _CommandCard(
                          theme: theme,
                          lines: [
                            'auth.promptLine1'.tr,
                            'auth.promptLine2'.tr,
                          ],
                          darkSurface: true,
                        ),
                      ),
                    ),
                    if (compact)
                      SizedBox(height: narrow ? 20 : 28)
                    else
                      const Spacer(),
                    _RevealIn(
                      delay: const Duration(milliseconds: 320),
                      child: const _HeroSignalBand(),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _MetricRail extends StatelessWidget {
  const _MetricRail({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 14),
      decoration: BoxDecoration(
        border: Border(
          top: BorderSide(
            color: Colors.white.withValues(alpha: 0.18),
          ),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: theme.textTheme.labelMedium?.copyWith(
              color: Colors.white.withValues(alpha: 0.66),
              letterSpacing: 0.6,
            ),
          ),
          const SizedBox(height: 10),
          Container(
            width: 28,
            height: 2,
            color: Colors.white.withValues(alpha: 0.42),
          ),
          const SizedBox(height: 10),
          Text(
            value,
            style: theme.textTheme.headlineSmall?.copyWith(
              color: Colors.white,
              height: 1,
            ),
          ),
        ],
      ),
    );
  }
}

class _CommandCard extends StatelessWidget {
  const _CommandCard({
    required this.theme,
    required this.lines,
    this.darkSurface = false,
  });

  final ThemeData theme;
  final List<String> lines;
  final bool darkSurface;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: darkSurface
            ? Colors.white.withValues(alpha: 0.08)
            : theme.colorScheme.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: darkSurface
              ? Colors.white.withValues(alpha: 0.10)
              : theme.colorScheme.outlineVariant.withValues(alpha: 0.40),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'auth.promptIdeas'.tr,
            style: theme.textTheme.titleMedium?.copyWith(
              color: darkSurface ? Colors.white : null,
            ),
          ),
          const SizedBox(height: 12),
          ...lines.map(
            (line) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(
                '> $line',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: darkSurface
                      ? Colors.white.withValues(alpha: 0.78)
                      : theme.textTheme.bodyMedium?.color,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PanelTag extends StatelessWidget {
  const _PanelTag({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: theme.colorScheme.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: theme.colorScheme.primary.withValues(alpha: 0.18),
        ),
      ),
      child: Text(
        label,
        style: theme.textTheme.labelMedium?.copyWith(
          color: theme.colorScheme.primary,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _ModePill extends StatelessWidget {
  const _ModePill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: theme.textTheme.labelMedium?.copyWith(
          color: theme.colorScheme.onSurface,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _StatusTile extends StatelessWidget {
  const _StatusTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      constraints: const BoxConstraints(minWidth: 112),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHigh.withValues(alpha: 0.82),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: theme.colorScheme.outlineVariant.withValues(alpha: 0.32),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: theme.textTheme.labelSmall),
              const SizedBox(height: 2),
              Text(
                value,
                style: theme.textTheme.labelMedium?.copyWith(
                  color: theme.colorScheme.onSurface,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HeroSignalBand extends StatelessWidget {
  const _HeroSignalBand();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.18),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.10),
        ),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 420;
          final items = const [
            ('common.workspace', 'common.online'),
            ('common.focus', 'auth.metric.flowValue'),
            ('common.agent', 'auth.metric.agentValue'),
          ];

          if (compact) {
            return Column(
              children: [
                for (var i = 0; i < items.length; i++) ...[
                  _HeroSignalItem(
                    titleKey: items[i].$1,
                    valueKey: items[i].$2,
                  ),
                  if (i != items.length - 1)
                    Divider(
                      color: Colors.white.withValues(alpha: 0.10),
                      height: 22,
                    ),
                ],
              ],
            );
          }

          return Row(
            children: [
              for (var i = 0; i < items.length; i++) ...[
                Expanded(
                  child: _HeroSignalItem(
                    titleKey: items[i].$1,
                    valueKey: items[i].$2,
                  ),
                ),
                if (i != items.length - 1)
                  Container(
                    width: 1,
                    height: 34,
                    color: Colors.white.withValues(alpha: 0.10),
                    margin: const EdgeInsets.symmetric(horizontal: 14),
                  ),
              ],
            ],
          );
        },
      ),
    );
  }
}

class _HeroSignalItem extends StatelessWidget {
  const _HeroSignalItem({
    required this.titleKey,
    required this.valueKey,
  });

  final String titleKey;
  final String valueKey;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          titleKey.tr,
          style: theme.textTheme.labelMedium?.copyWith(
            color: Colors.white.withValues(alpha: 0.62),
            letterSpacing: 0.3,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          valueKey.tr,
          style: theme.textTheme.titleMedium?.copyWith(
            color: Colors.white,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}

class _LoginBackdrop extends StatelessWidget {
  const _LoginBackdrop();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Stack(
      children: [
        Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  theme.scaffoldBackgroundColor,
                  theme.colorScheme.surfaceContainer.withValues(alpha: 0.82),
                  theme.scaffoldBackgroundColor,
                ],
              ),
            ),
          ),
        ),
        const Positioned.fill(child: _BackdropGrid()),
        Positioned(
          top: -140,
          left: -90,
          child: _FloatDrift(
            offset: const Offset(10, 8),
            duration: const Duration(milliseconds: 5200),
            child: _Blob(
              size: 320,
              color: theme.colorScheme.primary.withValues(alpha: 0.14),
            ),
          ),
        ),
        Positioned(
          right: -80,
          top: 120,
          child: _FloatDrift(
            offset: const Offset(-12, 12),
            duration: const Duration(milliseconds: 5800),
            child: _Blob(
              size: 260,
              color: theme.colorScheme.primaryContainer.withValues(alpha: 0.18),
            ),
          ),
        ),
        Positioned(
          bottom: -120,
          right: 120,
          child: _FloatDrift(
            offset: const Offset(14, -10),
            duration: const Duration(milliseconds: 5400),
            child: _Blob(
              size: 360,
              color: theme.colorScheme.tertiary.withValues(alpha: 0.12),
            ),
          ),
        ),
      ],
    );
  }
}

class _Blob extends StatelessWidget {
  const _Blob({
    required this.size,
    required this.color,
  });

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [color, color.withValues(alpha: 0)],
        ),
      ),
    );
  }
}

class _SurfaceFrame extends StatelessWidget {
  const _SurfaceFrame({
    required this.child,
    this.padding = const EdgeInsets.all(20),
  });

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      padding: padding,
      decoration: BoxDecoration(
        color: theme.colorScheme.surface.withValues(alpha: 0.88),
        borderRadius: BorderRadius.circular(30),
        border: Border.all(
          color: theme.colorScheme.outlineVariant.withValues(alpha: 0.46),
        ),
        boxShadow: [
          BoxShadow(
            color: theme.colorScheme.shadow.withValues(alpha: 0.08),
            blurRadius: 30,
            offset: const Offset(0, 18),
          ),
        ],
      ),
      child: child,
    );
  }
}

class _RevealIn extends StatelessWidget {
  const _RevealIn({
    required this.child,
    this.delay = Duration.zero,
    this.distance = 18,
  });

  final Widget child;
  final Duration delay;
  final double distance;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      duration: const Duration(milliseconds: 420) + delay,
      curve: Curves.easeOutCubic,
      tween: Tween(begin: 0, end: 1),
      builder: (context, value, widget) {
        final delayedValue = delay == Duration.zero
            ? value
            : ((value * (420 + delay.inMilliseconds) - delay.inMilliseconds) /
                    420)
                .clamp(0.0, 1.0);
        return Opacity(
          opacity: delayedValue,
          child: Transform.translate(
            offset: Offset(0, (1 - delayedValue) * distance),
            child: widget,
          ),
        );
      },
      child: child,
    );
  }
}

class _FloatDrift extends StatefulWidget {
  const _FloatDrift({
    required this.child,
    required this.offset,
    required this.duration,
  });

  final Widget child;
  final Offset offset;
  final Duration duration;

  @override
  State<_FloatDrift> createState() => _FloatDriftState();
}

class _FloatDriftState extends State<_FloatDrift>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: widget.duration,
  )..repeat(reverse: true);

  late final Animation<double> _animation = CurvedAnimation(
    parent: _controller,
    curve: Curves.easeInOut,
  );

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animation,
      child: widget.child,
      builder: (context, child) {
        final dx = widget.offset.dx * _animation.value;
        final dy = widget.offset.dy * _animation.value;
        return Transform.translate(
          offset: Offset(dx, dy),
          child: child,
        );
      },
    );
  }
}

class _BackdropGrid extends StatelessWidget {
  const _BackdropGrid();

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: CustomPaint(
        painter: _BackdropGridPainter(
          color: Theme.of(context)
              .colorScheme
              .outlineVariant
              .withValues(alpha: 0.12),
        ),
        child: const SizedBox.expand(),
      ),
    );
  }
}

class _BackdropGridPainter extends CustomPainter {
  const _BackdropGridPainter({required this.color});

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 1;

    const gap = 52.0;

    for (double x = 0; x < size.width; x += gap) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }
    for (double y = 0; y < size.height; y += gap) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(covariant _BackdropGridPainter oldDelegate) {
    return oldDelegate.color != color;
  }
}
