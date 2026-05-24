import 'package:final_assignment_front/config/routes/app_routes.dart';
import 'package:final_assignment_front/features/api/system_settings_controller_api.dart';
import 'package:final_assignment_front/features/dashboard/controllers/admin_dashboard_controller.dart';
import 'package:final_assignment_front/features/dashboard/controllers/chat_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/dashboard_page_template.dart';
import 'package:final_assignment_front/features/model/system_settings.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AdminSettingPage extends StatefulWidget {
  const AdminSettingPage({
    super.key,
    this.titleKey = 'settings.title',
    this.pageType = DashboardPageType.admin,
  });

  final String titleKey;
  final DashboardPageType pageType;

  @override
  State<AdminSettingPage> createState() => _AdminSettingPageState();
}

class _AdminSettingPageState extends State<AdminSettingPage> {
  static const _allCategories = '__all__';
  static const _notificationsPrefKey = 'adminSettings.notificationsEnabled';

  final DashboardController controller = Get.find<DashboardController>();
  final SystemSettingsControllerApi _settingsApi =
      SystemSettingsControllerApi();
  final TextEditingController _searchController = TextEditingController();
  final TextEditingController _themeController = TextEditingController();

  List<SystemSettings> _settings = const [];
  bool _notificationEnabled = true;
  bool _isLoading = true;
  bool _isSavingLocal = false;
  String _selectedCategory = _allCategories;
  String? _errorMessage;
  DateTime? _lastSyncedAt;

  @override
  void initState() {
    super.initState();
    _searchController.addListener(_handleSearchChanged);
    _themeController.text = _selectedThemeLabel;
    _initializePage();
  }

  @override
  void dispose() {
    _searchController.removeListener(_handleSearchChanged);
    _searchController.dispose();
    _themeController.dispose();
    super.dispose();
  }

  Future<void> _initializePage() async {
    await _loadLocalPreferences();
    await _loadRemoteSettings();
  }

  Future<void> _loadLocalPreferences() async {
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) {
      return;
    }
    setState(() {
      _notificationEnabled = prefs.getBool(_notificationsPrefKey) ?? true;
      _themeController.text = _selectedThemeLabel;
    });
  }

  Future<void> _loadRemoteSettings() async {
    if (mounted) {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });
    }

    try {
      await _settingsApi.initializeWithJwt();
      final settings = await _settingsApi.apiSystemSettingsListGet(size: 200);
      if (!mounted) {
        return;
      }

      final sorted = [...settings]..sort((left, right) {
          final leftCategory = _normalizedCategory(left.category);
          final rightCategory = _normalizedCategory(right.category);
          final categoryCompare = leftCategory.compareTo(rightCategory);
          if (categoryCompare != 0) {
            return categoryCompare;
          }
          final leftSort = left.sortOrder ?? 999999;
          final rightSort = right.sortOrder ?? 999999;
          final sortCompare = leftSort.compareTo(rightSort);
          if (sortCompare != 0) {
            return sortCompare;
          }
          return (left.settingKey ?? '').compareTo(right.settingKey ?? '');
        });

      setState(() {
        _settings = sorted;
        _lastSyncedAt = DateTime.now();
        _isLoading = false;
        if (!_categoryOptions.contains(_selectedCategory)) {
          _selectedCategory = _allCategories;
        }
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _errorMessage = 'settings.message.loadFailed'.trParams({
          'error': localizeApiErrorDetail(error),
        });
        _isLoading = false;
      });
    }
  }

  Future<void> _saveLocalPreferences() async {
    setState(() => _isSavingLocal = true);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_notificationsPrefKey, _notificationEnabled);
    await prefs.setString(
      'dashboardTheme_${controller.selectedStyle.value}',
      controller.currentTheme.value,
    );
    await prefs.setBool('isDarkMode', controller.currentTheme.value == 'Dark');

    if (!mounted) {
      return;
    }
    setState(() => _isSavingLocal = false);
    _showSnackBar('settings.message.localSaved'.tr);
  }

  void _handleSearchChanged() {
    if (!mounted) {
      return;
    }
    setState(() {});
  }

  Future<void> _logout() async {
    await AuthTokenStore.instance.clearJwtToken();
    if (Get.isRegistered<ChatController>()) {
      Get.find<ChatController>().clearMessages();
    }
    if (!mounted) {
      return;
    }
    Get.offAllNamed(Routes.login);
  }

  Future<void> _confirmLogout() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text('settings.confirmLogoutTitle'.tr),
        content: Text('settings.confirmLogoutMessage'.tr),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: Text('common.cancel'.tr),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: Text('common.confirm'.tr),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await _logout();
    }
  }

  Future<void> _showThemeDialog() async {
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text('settings.themeDialogTitle'.tr),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              _ThemeOptionTile(
                label: 'settings.theme.materialLight'.tr,
                onTap: () => _applyThemeSelection(
                  context: dialogContext,
                  style: 'Material',
                  darkMode: false,
                ),
              ),
              _ThemeOptionTile(
                label: 'settings.theme.materialDark'.tr,
                onTap: () => _applyThemeSelection(
                  context: dialogContext,
                  style: 'Material',
                  darkMode: true,
                ),
              ),
              _ThemeOptionTile(
                label: 'settings.theme.ionicLight'.tr,
                onTap: () => _applyThemeSelection(
                  context: dialogContext,
                  style: 'Ionic',
                  darkMode: false,
                ),
              ),
              _ThemeOptionTile(
                label: 'settings.theme.ionicDark'.tr,
                onTap: () => _applyThemeSelection(
                  context: dialogContext,
                  style: 'Ionic',
                  darkMode: true,
                ),
              ),
              _ThemeOptionTile(
                label: 'settings.theme.basicLight'.tr,
                onTap: () => _applyThemeSelection(
                  context: dialogContext,
                  style: 'Basic',
                  darkMode: false,
                ),
              ),
              _ThemeOptionTile(
                label: 'settings.theme.basicDark'.tr,
                onTap: () => _applyThemeSelection(
                  context: dialogContext,
                  style: 'Basic',
                  darkMode: true,
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: Text('common.cancel'.tr),
          ),
        ],
      ),
    );
  }

  void _applyThemeSelection({
    required BuildContext context,
    required String style,
    required bool darkMode,
  }) {
    controller.setSelectedStyle(style);
    final shouldToggle = (controller.currentTheme.value == 'Dark') != darkMode;
    if (shouldToggle) {
      controller.toggleBodyTheme();
    }

    if (!mounted) {
      return;
    }
    setState(() {
      _themeController.text = _selectedThemeLabel;
    });
    Navigator.pop(context);
  }

  Future<void> _openSettingEditor({SystemSettings? current}) async {
    if (current != null && current.isEditable == false) {
      _showSnackBar(
        'settings.message.notEditable'.tr,
        isError: true,
      );
      return;
    }

    final keyController =
        TextEditingController(text: current?.settingKey ?? '');
    final valueController =
        TextEditingController(text: current?.settingValue ?? '');
    final categoryController = TextEditingController(
      text: current?.category ?? '',
    );
    final descriptionController = TextEditingController(
      text: current?.description ?? '',
    );
    final remarksController = TextEditingController(
      text: current?.remarks ?? '',
    );
    final sortOrderController = TextEditingController(
      text: current?.sortOrder?.toString() ?? '',
    );
    final formKey = GlobalKey<FormState>();
    var selectedType = current?.settingType ?? 'String';
    var isEditable = current?.isEditable ?? true;
    var isEncrypted = current?.isEncrypted ?? false;

    try {
      final shouldSubmit = await showDialog<bool>(
        context: context,
        builder: (dialogContext) {
          return AlertDialog(
            title: Text(
              current == null
                  ? 'settings.form.createTitle'.tr
                  : 'settings.form.editTitle'.tr,
            ),
            content: StatefulBuilder(
              builder: (context, setDialogState) {
                return SizedBox(
                  width: 560,
                  child: Form(
                    key: formKey,
                    child: SingleChildScrollView(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          TextFormField(
                            controller: keyController,
                            decoration: InputDecoration(
                              labelText: 'settings.form.key'.tr,
                            ),
                            validator: (value) {
                              if (value == null || value.trim().isEmpty) {
                                return 'settings.form.keyRequired'.tr;
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 12),
                          TextFormField(
                            controller: valueController,
                            minLines: 3,
                            maxLines: 5,
                            decoration: InputDecoration(
                              labelText: 'settings.form.value'.tr,
                            ),
                            validator: (value) {
                              if (value == null || value.trim().isEmpty) {
                                return 'settings.form.valueRequired'.tr;
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 12),
                          DropdownButtonFormField<String>(
                            initialValue: selectedType,
                            decoration: InputDecoration(
                              labelText: 'settings.form.type'.tr,
                            ),
                            items: const [
                              DropdownMenuItem(
                                value: 'String',
                                child: Text('String'),
                              ),
                              DropdownMenuItem(
                                value: 'Number',
                                child: Text('Number'),
                              ),
                              DropdownMenuItem(
                                value: 'Boolean',
                                child: Text('Boolean'),
                              ),
                              DropdownMenuItem(
                                value: 'JSON',
                                child: Text('JSON'),
                              ),
                            ],
                            onChanged: (value) {
                              if (value == null) {
                                return;
                              }
                              setDialogState(() => selectedType = value);
                            },
                          ),
                          const SizedBox(height: 12),
                          TextFormField(
                            controller: categoryController,
                            decoration: InputDecoration(
                              labelText: 'settings.form.category'.tr,
                            ),
                          ),
                          const SizedBox(height: 12),
                          TextFormField(
                            controller: descriptionController,
                            minLines: 2,
                            maxLines: 4,
                            decoration: InputDecoration(
                              labelText: 'settings.form.description'.tr,
                            ),
                          ),
                          const SizedBox(height: 12),
                          TextFormField(
                            controller: remarksController,
                            minLines: 2,
                            maxLines: 4,
                            decoration: InputDecoration(
                              labelText: 'settings.form.remarks'.tr,
                            ),
                          ),
                          const SizedBox(height: 12),
                          TextFormField(
                            controller: sortOrderController,
                            keyboardType: TextInputType.number,
                            decoration: InputDecoration(
                              labelText: 'settings.form.sortOrder'.tr,
                            ),
                          ),
                          const SizedBox(height: 12),
                          SwitchListTile.adaptive(
                            value: isEditable,
                            contentPadding: EdgeInsets.zero,
                            title: Text('settings.form.isEditable'.tr),
                            onChanged: (value) {
                              setDialogState(() => isEditable = value);
                            },
                          ),
                          SwitchListTile.adaptive(
                            value: isEncrypted,
                            contentPadding: EdgeInsets.zero,
                            title: Text('settings.form.isEncrypted'.tr),
                            onChanged: (value) {
                              setDialogState(() => isEncrypted = value);
                            },
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              },
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, false),
                child: Text('common.cancel'.tr),
              ),
              FilledButton(
                onPressed: () {
                  if (formKey.currentState?.validate() != true) {
                    return;
                  }
                  Navigator.pop(dialogContext, true);
                },
                child: Text(
                  current == null ? 'common.create'.tr : 'common.save'.tr,
                ),
              ),
            ],
          );
        },
      );

      if (shouldSubmit != true) {
        return;
      }

      final payload = SystemSettings(
        settingId: current?.settingId,
        settingKey: keyController.text.trim(),
        settingValue: valueController.text.trim(),
        settingType: selectedType,
        category: categoryController.text.trim().isEmpty
            ? 'general'
            : categoryController.text.trim(),
        description: descriptionController.text.trim().isEmpty
            ? null
            : descriptionController.text.trim(),
        remarks: remarksController.text.trim().isEmpty
            ? null
            : remarksController.text.trim(),
        isEditable: isEditable,
        isEncrypted: isEncrypted,
        sortOrder: int.tryParse(sortOrderController.text.trim()),
      );

      if (current?.settingId != null) {
        await _settingsApi.apiSystemSettingsSettingIdPut(
          settingId: current!.settingId!,
          systemSettings: payload,
          idempotencyKey: _generateIdempotencyKey(),
        );
        _showSnackBar('settings.message.updateSuccess'.tr);
      } else {
        await _settingsApi.apiSystemSettingsPost(
          systemSettings: payload,
          idempotencyKey: _generateIdempotencyKey(),
        );
        _showSnackBar('settings.message.createSuccess'.tr);
      }

      await _loadRemoteSettings();
    } catch (error) {
      _showSnackBar(
        localizeApiErrorDetail(error),
        isError: true,
      );
    } finally {
      keyController.dispose();
      valueController.dispose();
      categoryController.dispose();
      descriptionController.dispose();
      remarksController.dispose();
      sortOrderController.dispose();
    }
  }

  void _showSnackBar(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError
            ? Colors.red.shade700
            : Theme.of(context).colorScheme.primary,
      ),
    );
  }

  String _generateIdempotencyKey() {
    return 'settings-${DateTime.now().microsecondsSinceEpoch}';
  }

  String _normalizedCategory(String? category) {
    final value = category?.trim();
    if (value == null || value.isEmpty) {
      return 'general';
    }
    return value;
  }

  String _displayCategory(String? category) {
    final normalized = _normalizedCategory(category);
    return normalized
        .split(RegExp(r'[_\-\s]+'))
        .where((segment) => segment.isNotEmpty)
        .map(
          (segment) => '${segment[0].toUpperCase()}${segment.substring(1)}',
        )
        .join(' ');
  }

  String _valuePreview(SystemSettings setting) {
    if (setting.isEncrypted == true) {
      return 'settings.value.encrypted'.tr;
    }
    final value = setting.settingValue?.trim();
    if (value == null || value.isEmpty) {
      return 'settings.value.notConfigured'.tr;
    }
    if (value.length <= 140) {
      return value;
    }
    return '${value.substring(0, 140)}...';
  }

  String _formatTimestamp(DateTime? value) {
    if (value == null) {
      return 'settings.metric.neverSynced'.tr;
    }
    final month = value.month.toString().padLeft(2, '0');
    final day = value.day.toString().padLeft(2, '0');
    final hour = value.hour.toString().padLeft(2, '0');
    final minute = value.minute.toString().padLeft(2, '0');
    return '$month-$day $hour:$minute';
  }

  List<String> get _categoryOptions {
    final categories = _settings
        .map((setting) => _normalizedCategory(setting.category))
        .toSet()
        .toList()
      ..sort();
    return [_allCategories, ...categories];
  }

  List<SystemSettings> get _filteredSettings {
    final query = _searchController.text.trim().toLowerCase();
    return _settings.where((setting) {
      final category = _normalizedCategory(setting.category);
      final categoryMatched =
          _selectedCategory == _allCategories || category == _selectedCategory;
      if (!categoryMatched) {
        return false;
      }
      if (query.isEmpty) {
        return true;
      }

      final haystack = [
        setting.settingKey,
        setting.settingValue,
        setting.settingType,
        setting.category,
        setting.description,
        setting.remarks,
      ].whereType<String>().join(' ').toLowerCase();
      return haystack.contains(query);
    }).toList();
  }

  int get _editableCount =>
      _settings.where((setting) => setting.isEditable == true).length;

  int get _encryptedCount =>
      _settings.where((setting) => setting.isEncrypted == true).length;

  String get _selectedThemeLabel {
    final style = controller.selectedStyle.value.toLowerCase();
    final mode = controller.currentTheme.value == 'Dark' ? 'Dark' : 'Light';
    return 'settings.theme.$style$mode'.tr;
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final theme = controller.currentBodyTheme.value;
      if (_themeController.text != _selectedThemeLabel) {
        _themeController.text = _selectedThemeLabel;
      }

      return DashboardPageTemplate(
        theme: theme,
        title: widget.titleKey.tr,
        pageType: widget.pageType,
        onRefresh: _loadRemoteSettings,
        onThemeToggle: controller.toggleBodyTheme,
        body: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildOverviewSurface(theme),
              const SizedBox(height: 20),
              _buildPreferenceSurface(theme),
              const SizedBox(height: 20),
              _buildRegistrySurface(theme),
            ],
          ),
        ),
      );
    });
  }

  Widget _buildOverviewSurface(ThemeData theme) {
    final metrics = [
      _SettingMetric(
        label: 'settings.metric.total'.tr,
        value: _settings.length.toString(),
      ),
      _SettingMetric(
        label: 'settings.metric.editable'.tr,
        value: _editableCount.toString(),
      ),
      _SettingMetric(
        label: 'settings.metric.encrypted'.tr,
        value: _encryptedCount.toString(),
      ),
      _SettingMetric(
        label: 'settings.metric.categories'.tr,
        value: (_categoryOptions.length - 1).clamp(0, 999).toString(),
      ),
      _SettingMetric(
        label: 'settings.metric.lastSync'.tr,
        value: _formatTimestamp(_lastSyncedAt),
      ),
    ];

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(
          color: theme.colorScheme.outlineVariant.withValues(alpha: 0.32),
        ),
        boxShadow: [
          BoxShadow(
            color: theme.colorScheme.shadow.withValues(alpha: 0.06),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          LayoutBuilder(
            builder: (context, constraints) {
              final stacked = constraints.maxWidth < 860;
              final headline = Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'settings.controlTitle'.tr,
                    style: theme.textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'settings.controlBody'.tr,
                    style: theme.textTheme.bodyMedium,
                  ),
                ],
              );
              final actions = Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  FilledButton.icon(
                    onPressed: _isLoading ? null : () => _openSettingEditor(),
                    icon: const Icon(Icons.add_rounded),
                    label: Text('settings.action.newSetting'.tr),
                  ),
                  OutlinedButton.icon(
                    onPressed: _loadRemoteSettings,
                    icon: const Icon(Icons.refresh_rounded),
                    label: Text('settings.action.reload'.tr),
                  ),
                ],
              );

              if (stacked) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    headline,
                    const SizedBox(height: 16),
                    actions,
                  ],
                );
              }

              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(flex: 3, child: headline),
                  const SizedBox(width: 16),
                  actions,
                ],
              );
            },
          ),
          const SizedBox(height: 24),
          Wrap(
            spacing: 14,
            runSpacing: 14,
            children: metrics
                .map((metric) => _MetricTile(metric: metric))
                .toList(growable: false),
          ),
        ],
      ),
    );
  }

  Widget _buildPreferenceSurface(ThemeData theme) {
    final sectionTitle = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'settings.workspaceTitle'.tr,
          style: theme.textTheme.titleLarge,
        ),
        const SizedBox(height: 6),
        Text(
          'settings.workspaceBody'.tr,
          style: theme.textTheme.bodyMedium,
        ),
      ],
    );

    final preferenceItems = Column(
      children: [
        _PreferenceTile(
          icon: Icons.notifications_active_outlined,
          title: 'settings.notificationsEnabled'.tr,
          body: 'settings.preference.notificationsBody'.tr,
          trailing: Switch.adaptive(
            value: _notificationEnabled,
            onChanged: (value) {
              setState(() => _notificationEnabled = value);
            },
          ),
        ),
        Divider(
          height: 1,
          color: theme.colorScheme.outlineVariant.withValues(alpha: 0.28),
        ),
        _PreferenceTile(
          icon: Icons.palette_outlined,
          title: 'settings.theme'.tr,
          body: 'settings.preference.themeBody'.trParams({
            'value': _selectedThemeLabel,
          }),
          trailing: OutlinedButton(
            onPressed: _showThemeDialog,
            child: Text('settings.preference.themeChange'.tr),
          ),
        ),
        Divider(
          height: 1,
          color: theme.colorScheme.outlineVariant.withValues(alpha: 0.28),
        ),
        _PreferenceTile(
          icon: Icons.save_outlined,
          title: 'common.save'.tr,
          body: 'settings.preference.localSaveBody'.tr,
          trailing: FilledButton(
            onPressed: _isSavingLocal ? null : _saveLocalPreferences,
            child: Text(
              _isSavingLocal
                  ? 'common.loading'.tr
                  : 'settings.action.saveLocal'.tr,
            ),
          ),
        ),
        Divider(
          height: 1,
          color: theme.colorScheme.outlineVariant.withValues(alpha: 0.28),
        ),
        _PreferenceTile(
          icon: Icons.logout_rounded,
          title: 'common.logout'.tr,
          body: 'settings.preference.logoutBody'.tr,
          trailing: TextButton(
            onPressed: _confirmLogout,
            child: Text('common.logout'.tr),
          ),
        ),
      ],
    );

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(
          color: theme.colorScheme.outlineVariant.withValues(alpha: 0.28),
        ),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final stacked = constraints.maxWidth < 880;
          if (stacked) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                sectionTitle,
                const SizedBox(height: 20),
                preferenceItems,
              ],
            );
          }

          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(flex: 2, child: sectionTitle),
              const SizedBox(width: 24),
              Expanded(flex: 3, child: preferenceItems),
            ],
          );
        },
      ),
    );
  }

  Widget _buildRegistrySurface(ThemeData theme) {
    final filteredSettings = _filteredSettings;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(
          color: theme.colorScheme.outlineVariant.withValues(alpha: 0.28),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'settings.registryTitle'.tr,
            style: theme.textTheme.titleLarge,
          ),
          const SizedBox(height: 6),
          Text(
            'settings.registryBody'.tr,
            style: theme.textTheme.bodyMedium,
          ),
          const SizedBox(height: 18),
          TextField(
            controller: _searchController,
            decoration: InputDecoration(
              hintText: 'settings.searchHint'.tr,
              prefixIcon: const Icon(Icons.search_rounded),
              suffixIcon: _searchController.text.isEmpty
                  ? null
                  : IconButton(
                      onPressed: () => _searchController.clear(),
                      icon: const Icon(Icons.close_rounded),
                    ),
            ),
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: _categoryOptions.map((category) {
              final isAll = category == _allCategories;
              final label =
                  isAll ? 'settings.filter.all'.tr : _displayCategory(category);
              return ChoiceChip(
                label: Text(label),
                selected: _selectedCategory == category,
                onSelected: (_) {
                  setState(() => _selectedCategory = category);
                },
              );
            }).toList(growable: false),
          ),
          if (_errorMessage != null) ...[
            const SizedBox(height: 16),
            _InlineStateBanner(
              icon: Icons.error_outline_rounded,
              message: _errorMessage!,
              isError: true,
            ),
          ],
          const SizedBox(height: 18),
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 220),
            child: _buildRegistryBody(theme, filteredSettings),
          ),
        ],
      ),
    );
  }

  Widget _buildRegistryBody(
    ThemeData theme,
    List<SystemSettings> filteredSettings,
  ) {
    if (_isLoading) {
      return Container(
        key: const ValueKey('loading'),
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 56),
        alignment: Alignment.center,
        child: CircularProgressIndicator(
          valueColor: AlwaysStoppedAnimation<Color>(
            theme.colorScheme.primary,
          ),
        ),
      );
    }

    if (filteredSettings.isEmpty) {
      return _EmptyRegistryState(
        key: const ValueKey('empty'),
        title: 'settings.state.emptyTitle'.tr,
        body: 'settings.state.emptyBody'.tr,
      );
    }

    return Container(
      key: const ValueKey('list'),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: theme.colorScheme.outlineVariant.withValues(alpha: 0.24),
        ),
      ),
      child: Column(
        children: [
          for (var index = 0; index < filteredSettings.length; index++) ...[
            _SettingRow(
              setting: filteredSettings[index],
              onEdit: () =>
                  _openSettingEditor(current: filteredSettings[index]),
              categoryLabel: _displayCategory(filteredSettings[index].category),
              valuePreview: _valuePreview(filteredSettings[index]),
              updatedAtLabel: _formatTimestamp(
                filteredSettings[index].modifiedTime ??
                    filteredSettings[index].createdTime,
              ),
            ),
            if (index != filteredSettings.length - 1)
              Divider(
                height: 1,
                color: theme.colorScheme.outlineVariant.withValues(alpha: 0.24),
              ),
          ],
        ],
      ),
    );
  }
}

class _SettingMetric {
  const _SettingMetric({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;
}

class _MetricTile extends StatelessWidget {
  const _MetricTile({
    required this.metric,
  });

  final _SettingMetric metric;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      width: 160,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            metric.label,
            style: theme.textTheme.labelMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            metric.value,
            style: theme.textTheme.titleLarge,
          ),
        ],
      ),
    );
  }
}

class _PreferenceTile extends StatelessWidget {
  const _PreferenceTile({
    required this.icon,
    required this.title,
    required this.body,
    required this.trailing,
  });

  final IconData icon;
  final String title;
  final String body;
  final Widget trailing;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: theme.colorScheme.primary.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, color: theme.colorScheme.primary),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: theme.textTheme.titleMedium),
                const SizedBox(height: 6),
                Text(body, style: theme.textTheme.bodyMedium),
              ],
            ),
          ),
          const SizedBox(width: 16),
          trailing,
        ],
      ),
    );
  }
}

class _SettingRow extends StatelessWidget {
  const _SettingRow({
    required this.setting,
    required this.onEdit,
    required this.categoryLabel,
    required this.valuePreview,
    required this.updatedAtLabel,
  });

  final SystemSettings setting;
  final VoidCallback onEdit;
  final String categoryLabel;
  final String valuePreview;
  final String updatedAtLabel;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return InkWell(
      onTap: setting.isEditable == false ? null : onEdit,
      borderRadius: BorderRadius.circular(24),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final stacked = constraints.maxWidth < 860;
            final content = Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(
                      setting.settingKey?.trim().isNotEmpty == true
                          ? setting.settingKey!
                          : 'settings.value.none'.tr,
                      style: theme.textTheme.titleMedium,
                    ),
                    _MiniBadge(label: categoryLabel),
                    _MiniBadge(
                      label: setting.settingType ?? 'String',
                      emphasized: true,
                    ),
                    _MiniBadge(
                      label: setting.isEditable == false
                          ? 'settings.value.readOnly'.tr
                          : 'settings.value.editable'.tr,
                    ),
                    _MiniBadge(
                      label: setting.isEncrypted == true
                          ? 'settings.value.encrypted'.tr
                          : 'settings.value.plaintext'.tr,
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  setting.description?.trim().isNotEmpty == true
                      ? setting.description!
                      : 'settings.value.none'.tr,
                  style: theme.textTheme.bodyMedium,
                ),
                const SizedBox(height: 12),
                Text(
                  valuePreview,
                  style: theme.textTheme.bodyLarge,
                ),
                const SizedBox(height: 14),
                Wrap(
                  spacing: 18,
                  runSpacing: 8,
                  children: [
                    Text(
                      'settings.label.updatedBy'.trParams({
                        'value': setting.updatedBy?.trim().isNotEmpty == true
                            ? setting.updatedBy!
                            : 'settings.value.none'.tr,
                      }),
                      style: theme.textTheme.labelMedium?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    Text(
                      'settings.label.updatedAt'.trParams({
                        'value': updatedAtLabel,
                      }),
                      style: theme.textTheme.labelMedium?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ],
            );

            final action = FilledButton.tonalIcon(
              onPressed: setting.isEditable == false ? null : onEdit,
              icon: const Icon(Icons.edit_outlined),
              label: Text('settings.action.editSetting'.tr),
            );

            if (stacked) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  content,
                  const SizedBox(height: 14),
                  action,
                ],
              );
            }

            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(child: content),
                const SizedBox(width: 18),
                action,
              ],
            );
          },
        ),
      ),
    );
  }
}

class _MiniBadge extends StatelessWidget {
  const _MiniBadge({
    required this.label,
    this.emphasized = false,
  });

  final String label;
  final bool emphasized;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final background = emphasized
        ? theme.colorScheme.primary.withValues(alpha: 0.10)
        : theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.72);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: theme.textTheme.labelMedium?.copyWith(
          color: emphasized
              ? theme.colorScheme.primary
              : theme.colorScheme.onSurfaceVariant,
        ),
      ),
    );
  }
}

class _InlineStateBanner extends StatelessWidget {
  const _InlineStateBanner({
    required this.icon,
    required this.message,
    this.isError = false,
  });

  final IconData icon;
  final String message;
  final bool isError;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = isError ? theme.colorScheme.error : theme.colorScheme.primary;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: color.withValues(alpha: 0.18)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              message,
              style: theme.textTheme.bodyMedium?.copyWith(color: color),
            ),
          ),
        ],
      ),
    );
  }
}

class _EmptyRegistryState extends StatelessWidget {
  const _EmptyRegistryState({
    super.key,
    required this.title,
    required this.body,
  });

  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 48),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        children: [
          Icon(
            Icons.tune_rounded,
            size: 36,
            color: theme.colorScheme.onSurfaceVariant,
          ),
          const SizedBox(height: 14),
          Text(title, style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          Text(
            body,
            textAlign: TextAlign.center,
            style: theme.textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }
}

class _ThemeOptionTile extends StatelessWidget {
  const _ThemeOptionTile({
    required this.label,
    required this.onTap,
  });

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      title: Text(label),
      trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 14),
      onTap: onTap,
    );
  }
}
