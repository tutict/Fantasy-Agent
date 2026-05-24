// ignore_for_file: use_build_context_synchronously
import 'package:final_assignment_front/features/api/driver_information_controller_api.dart';
import 'package:final_assignment_front/features/api/user_management_controller_api.dart';
import 'package:final_assignment_front/features/dashboard/controllers/user_dashboard_screen_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/user/widgets/user_page_app_bar.dart';
import 'package:final_assignment_front/features/model/driver_information.dart';
import 'package:final_assignment_front/features/model/user_management.dart';
import 'package:final_assignment_front/i18n/personal_field_localizers.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:final_assignment_front/utils/ui/ui_utils.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

String generateIdempotencyKey() =>
    DateTime.now().millisecondsSinceEpoch.toString();

class PersonalMainPage extends StatefulWidget {
  const PersonalMainPage({super.key});

  @override
  State<PersonalMainPage> createState() => _PersonalMainPageState();
}

class _PersonalMainPageState extends State<PersonalMainPage> {
  final UserDashboardController dashboardController =
      Get.find<UserDashboardController>();
  final DriverInformationControllerApi driverApi =
      DriverInformationControllerApi();
  final UserManagementControllerApi userApi = UserManagementControllerApi();

  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _contactNumberController =
      TextEditingController();
  final TextEditingController _idCardController = TextEditingController();
  final TextEditingController _licenseController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();

  final ScrollController _scrollController = ScrollController();

  Future<UserManagement?>? _userFuture;
  DriverInformation? _driverInfo;
  bool _isLoading = true;
  String _errorMessage = '';

  @override
  void initState() {
    super.initState();
    _loadCurrentUser();
    ever(dashboardController.refreshPersonalPage, (_) {
      if (dashboardController.refreshPersonalPage.value && mounted) {
        _loadCurrentUser();
      }
    });
  }

  @override
  void dispose() {
    _nameController.dispose();
    _contactNumberController.dispose();
    _idCardController.dispose();
    _licenseController.dispose();
    _emailController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadCurrentUser() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });
    try {
      final prefs = await SharedPreferences.getInstance();
      final jwtToken = await AuthTokenStore.instance.getJwtToken();
      if (jwtToken == null) {
        throw Exception('personal.error.notLoggedIn'.tr);
      }

      await driverApi.initializeWithJwt();
      await userApi.initializeWithJwt();

      final user = await userApi.apiUsersMeGet();
      if (user == null) {
        throw Exception('personal.error.loadUserFailed'.tr);
      }

      final driverInfo = await driverApi.apiDriversMeGet();

      setState(() {
        _driverInfo = driverInfo;
        _userFuture = Future.value(user);
        _nameController.text =
            driverInfo?.name ?? user.realName ?? user.username ?? '';
        _contactNumberController.text =
            driverInfo?.contactNumber ?? user.contactNumber ?? '';
        _idCardController.text =
            driverInfo?.idCardNumber ?? user.idCardNumber ?? '';
        _licenseController.text = driverInfo?.driverLicenseNumber ?? '';
        _emailController.text = user.email ?? driverInfo?.email ?? '';
        _isLoading = false;
      });

      if (_nameController.text.isNotEmpty) {
        await prefs.setString('driverName', _nameController.text);
        await prefs.setString('displayName', _nameController.text);
      }
      dashboardController.updateCurrentUser(
        _nameController.text,
        user.email ?? '',
      );
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = formatPersonalError(e);
      });
    }
  }

  Future<void> _updateField(String field, String value) async {
    setState(() => _isLoading = true);
    try {
      final user = await _userFuture;
      if (user == null) {
        throw Exception('personal.error.currentUserNotFound'.tr);
      }

      final validationError = _validateField(field, value);
      if (validationError != null) {
        throw Exception(validationError);
      }
      final normalizedValue = value.trim();
      switch (field) {
        case 'name':
        case 'contactNumber':
        case 'idCardNumber':
        case 'driverLicenseNumber':
        case 'email':
          await driverApi.apiDriversMePut(
            driverInformation: _buildDriverDraft(
              user,
              name: field == 'name' ? normalizedValue : null,
              contactNumber: field == 'contactNumber' ? normalizedValue : null,
              idCardNumber: field == 'idCardNumber' ? normalizedValue : null,
              driverLicenseNumber:
                  field == 'driverLicenseNumber' ? normalizedValue : null,
              email: field == 'email' ? normalizedValue : null,
            ),
          );
          break;
        default:
          throw Exception(
            'personal.error.unknownField'.trParams({'field': field}),
          );
      }

      await _loadCurrentUser();
      AppSnackbar.showSuccess(
        context,
        message: 'personal.success.fieldUpdated'.trParams(
          {'field': personalFieldLabel(field)},
        ),
      );
    } catch (e) {
      AppSnackbar.showError(context, message: formatPersonalError(e));
      setState(() => _isLoading = false);
    }
  }

  DriverInformation _buildDriverDraft(
    UserManagement user, {
    String? name,
    String? contactNumber,
    String? idCardNumber,
    String? driverLicenseNumber,
    String? email,
  }) {
    return (_driverInfo ?? const DriverInformation()).copyWith(
      name: name ?? _driverInfo?.name ?? user.realName ?? user.username,
      contactNumber:
          contactNumber ?? _driverInfo?.contactNumber ?? user.contactNumber,
      idCardNumber:
          idCardNumber ?? _driverInfo?.idCardNumber ?? user.idCardNumber,
      driverLicenseNumber:
          driverLicenseNumber ?? _driverInfo?.driverLicenseNumber,
      email: email ?? _driverInfo?.email ?? user.email,
      gender: _driverInfo?.gender ?? user.gender,
    );
  }

  Future<void> _updatePassword(
    String currentPassword,
    String newPassword,
  ) async {
    setState(() => _isLoading = true);
    try {
      final user = await _userFuture;
      if (user == null) {
        throw Exception('personal.error.currentUserNotFound'.tr);
      }

      final currentPasswordError = validatePersonalField(
        'password',
        value: currentPassword,
        required: true,
      );
      if (currentPasswordError != null) {
        throw Exception(currentPasswordError);
      }

      final newPasswordError = validatePersonalField(
        'password',
        value: newPassword,
        required: true,
      );
      if (newPasswordError != null) {
        throw Exception(newPasswordError);
      }

      await userApi.apiUsersMePasswordPut(
        currentPassword: currentPassword,
        newPassword: newPassword,
        idempotencyKey: generateIdempotencyKey(),
      );

      await _loadCurrentUser();
      AppSnackbar.showSuccess(
        context,
        message: 'personal.success.fieldUpdated'.trParams(
          {'field': personalFieldLabel('password')},
        ),
      );
    } catch (e) {
      AppSnackbar.showError(context, message: formatPersonalError(e));
      setState(() => _isLoading = false);
    }
  }

  String? _validateField(String field, String value) {
    return validatePersonalField(field, value: value, required: true);
  }

  TextInputType _keyboardTypeForField(String field) {
    switch (field) {
      case 'contactNumber':
        return TextInputType.phone;
      case 'idCardNumber':
      case 'driverLicenseNumber':
        return TextInputType.number;
      case 'email':
        return TextInputType.emailAddress;
      case 'password':
        return TextInputType.visiblePassword;
      default:
        return TextInputType.text;
    }
  }

  int? _maxLengthForField(String field) {
    switch (field) {
      case 'name':
        return 50;
      case 'contactNumber':
        return 20;
      case 'idCardNumber':
        return 18;
      case 'driverLicenseNumber':
        return 12;
      case 'email':
        return 254;
      default:
        return null;
    }
  }

  Future<void> _showPasswordEditDialog() async {
    final formKey = GlobalKey<FormState>();
    final currentPasswordController = TextEditingController();
    final newPasswordController = TextEditingController();
    final confirmPasswordController = TextEditingController();
    var autovalidateMode = AutovalidateMode.disabled;
    var obscureCurrentPassword = true;
    var obscureNewPassword = true;
    var obscureConfirmPassword = true;
    StateSetter? updateDialogState;

    try {
      final confirmed = await AppDialog.showCustomDialog<bool>(
        context: context,
        title: 'personal.editDialog.title'.trParams({
          'field': personalFieldLabel('password'),
        }),
        content: StatefulBuilder(
          builder: (context, dialogSetState) {
            updateDialogState = dialogSetState;
            return Form(
              key: formKey,
              autovalidateMode: autovalidateMode,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextFormField(
                    controller: currentPasswordController,
                    obscureText: obscureCurrentPassword,
                    autofocus: true,
                    decoration: InputDecoration(
                      labelText: 'auth.currentPassword'.tr,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
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
                    validator: (value) => validatePersonalField(
                      'password',
                      value: value ?? '',
                      required: true,
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: newPasswordController,
                    obscureText: obscureNewPassword,
                    decoration: InputDecoration(
                      labelText: 'auth.newPassword'.tr,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
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
                    validator: (value) => validatePersonalField(
                      'password',
                      value: value ?? '',
                      required: true,
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: confirmPasswordController,
                    obscureText: obscureConfirmPassword,
                    decoration: InputDecoration(
                      labelText: 'auth.confirmPassword'.tr,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
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
                    validator: (value) {
                      final confirmValue = value ?? '';
                      final confirmError = validatePersonalField(
                        'password',
                        value: confirmValue,
                        required: true,
                      );
                      if (confirmError != null) {
                        return confirmError;
                      }
                      if (confirmValue.trim() !=
                          newPasswordController.text.trim()) {
                        return 'auth.error.passwordMismatch'.tr;
                      }
                      return null;
                    },
                  ),
                ],
              ),
            );
          },
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text('common.cancel'.tr),
          ),
          ElevatedButton(
            onPressed: () {
              final isValid = formKey.currentState?.validate() ?? false;
              if (!isValid) {
                updateDialogState?.call(() {
                  autovalidateMode = AutovalidateMode.onUserInteraction;
                });
                return;
              }
              Navigator.of(context).pop(true);
            },
            child: Text('common.save'.tr),
          ),
        ],
      );

      if (confirmed == true) {
        await _updatePassword(
          currentPasswordController.text.trim(),
          newPasswordController.text.trim(),
        );
      }
    } finally {
      currentPasswordController.dispose();
      newPasswordController.dispose();
      confirmPasswordController.dispose();
    }
  }

  void _showEditDialog(
    String field,
    TextEditingController controller,
    VoidCallback onSave,
  ) {
    final label = personalFieldLabel(field);
    final formKey = GlobalKey<FormState>();
    var autovalidateMode = AutovalidateMode.disabled;
    StateSetter? updateDialogState;
    AppDialog.showCustomDialog(
      context: context,
      title: 'personal.editDialog.title'.trParams({'field': label}),
      content: StatefulBuilder(
        builder: (context, dialogSetState) {
          updateDialogState = dialogSetState;
          return Form(
            key: formKey,
            autovalidateMode: autovalidateMode,
            child: TextFormField(
              controller: controller,
              keyboardType: _keyboardTypeForField(field),
              obscureText: field == 'password',
              maxLength: _maxLengthForField(field),
              autofocus: true,
              decoration: InputDecoration(
                hintText: 'personal.editDialog.hint'.trParams({'field': label}),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              validator: (value) => _validateField(field, value ?? ''),
            ),
          );
        },
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text('common.cancel'.tr),
        ),
        ElevatedButton(
          onPressed: () {
            final isValid = formKey.currentState?.validate() ?? false;
            if (!isValid) {
              updateDialogState?.call(() {
                autovalidateMode = AutovalidateMode.onUserInteraction;
              });
              return;
            }
            Navigator.of(context).pop();
            onSave();
          },
          child: Text('common.save'.tr),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final themeData = dashboardController.currentBodyTheme.value;
      return Scaffold(
        backgroundColor: themeData.colorScheme.surface,
        appBar: UserPageAppBar(
          theme: themeData,
          title: 'personal.title'.tr,
          onThemeToggle: dashboardController.toggleBodyTheme,
        ),
        body: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _errorMessage.isNotEmpty
                ? Center(
                    child: Text(
                      _errorMessage,
                      style: themeData.textTheme.bodyLarge?.copyWith(
                        color: themeData.colorScheme.error,
                      ),
                    ),
                  )
                : FutureBuilder<UserManagement?>(
                    future: _userFuture,
                    builder: (context, snapshot) {
                      if (!snapshot.hasData) {
                        return const Center(child: CircularProgressIndicator());
                      }
                      final user = snapshot.data!;
                      return CupertinoScrollbar(
                        controller: _scrollController,
                        child: ListView(
                          controller: _scrollController,
                          padding: const EdgeInsets.all(16),
                          children: [
                            _buildEditableTile(
                              themeData,
                              title: personalFieldLabel('name'),
                              value: personalDisplayValue(
                                _driverInfo?.name ?? user.realName,
                              ),
                              onTap: () {
                                _nameController.text =
                                    _driverInfo?.name ?? user.realName ?? '';
                                _showEditDialog('name', _nameController, () {
                                  _updateField('name', _nameController.text);
                                });
                              },
                            ),
                            _buildEditableTile(
                              themeData,
                              title: personalFieldLabel('contactNumber'),
                              value: personalDisplayValue(
                                _driverInfo?.contactNumber ??
                                    user.contactNumber,
                              ),
                              onTap: () {
                                _contactNumberController.text =
                                    _driverInfo?.contactNumber ??
                                        user.contactNumber ??
                                        '';
                                _showEditDialog(
                                  'contactNumber',
                                  _contactNumberController,
                                  () => _updateField(
                                    'contactNumber',
                                    _contactNumberController.text,
                                  ),
                                );
                              },
                            ),
                            _buildEditableTile(
                              themeData,
                              title: personalFieldLabel('idCardNumber'),
                              value: personalDisplayValue(
                                _driverInfo?.idCardNumber ?? user.idCardNumber,
                              ),
                              onTap: () {
                                _idCardController.text =
                                    _driverInfo?.idCardNumber ??
                                        user.idCardNumber ??
                                        '';
                                _showEditDialog(
                                  'idCardNumber',
                                  _idCardController,
                                  () => _updateField(
                                    'idCardNumber',
                                    _idCardController.text,
                                  ),
                                );
                              },
                            ),
                            _buildEditableTile(
                              themeData,
                              title: personalFieldLabel('driverLicenseNumber'),
                              value: personalDisplayValue(
                                _driverInfo?.driverLicenseNumber,
                              ),
                              onTap: () {
                                _licenseController.text =
                                    _driverInfo?.driverLicenseNumber ?? '';
                                _showEditDialog(
                                  'driverLicenseNumber',
                                  _licenseController,
                                  () => _updateField(
                                    'driverLicenseNumber',
                                    _licenseController.text,
                                  ),
                                );
                              },
                            ),
                            _buildEditableTile(
                              themeData,
                              title: personalFieldLabel('password'),
                              value: 'personal.value.changePassword'.tr,
                              onTap: _showPasswordEditDialog,
                            ),
                            _buildEditableTile(
                              themeData,
                              title: personalFieldLabel('email'),
                              value: personalDisplayValue(
                                _driverInfo?.email ?? user.email,
                              ),
                              onTap: () {
                                _emailController.text =
                                    _driverInfo?.email ?? user.email ?? '';
                                _showEditDialog(
                                  'email',
                                  _emailController,
                                  () => _updateField(
                                    'email',
                                    _emailController.text,
                                  ),
                                );
                              },
                            ),
                            _buildDisplayTile(
                              themeData,
                              title: personalFieldLabel('status'),
                              value: localizePersonalAccountStatus(user.status),
                            ),
                            _buildDisplayTile(
                              themeData,
                              title: personalFieldLabel('createdTime'),
                              value: formatPersonalDateTime(user.createdTime),
                            ),
                            _buildDisplayTile(
                              themeData,
                              title: personalFieldLabel('modifiedTime'),
                              value: formatPersonalDateTime(user.modifiedTime),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
      );
    });
  }

  Widget _buildEditableTile(
    ThemeData theme, {
    required String title,
    required String value,
    VoidCallback? onTap,
  }) {
    return Card(
      elevation: 2,
      color: theme.colorScheme.surfaceContainer,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: ListTile(
        title: Text(
          title,
          style: theme.textTheme.bodyLarge?.copyWith(
            fontWeight: FontWeight.bold,
            color: theme.colorScheme.onSurface,
          ),
        ),
        subtitle: Text(
          value,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        trailing: onTap != null
            ? Icon(Icons.edit, color: theme.colorScheme.primary)
            : null,
        onTap: onTap,
      ),
    );
  }

  Widget _buildDisplayTile(
    ThemeData theme, {
    required String title,
    required String value,
  }) {
    return Card(
      elevation: 2,
      color: theme.colorScheme.surfaceContainer,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: ListTile(
        title: Text(
          title,
          style: theme.textTheme.bodyLarge?.copyWith(
            fontWeight: FontWeight.bold,
            color: theme.colorScheme.onSurface,
          ),
        ),
        subtitle: Text(
          value,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
      ),
    );
  }
}
