import 'dart:io';

import 'package:final_assignment_front/config/routes/app_routes.dart';
import 'package:final_assignment_front/features/dashboard/controllers/chat_controller.dart';
import 'package:final_assignment_front/features/dashboard/controllers/user_dashboard_screen_controller.dart';
import 'package:final_assignment_front/i18n/app_translations.dart';
import 'package:final_assignment_front/i18n/locale_controller.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:flutter/material.dart';
import 'package:flutter_cache_manager/flutter_cache_manager.dart';
import 'package:get/get.dart';
import 'package:path_provider/path_provider.dart';

class SettingPage extends StatefulWidget {
  const SettingPage({super.key});

  @override
  State<SettingPage> createState() => _SettingPageState();
}

class _SettingPageState extends State<SettingPage> {
  double _cacheSize = -1.0;
  final UserDashboardController controller =
      Get.find<UserDashboardController>();
  final LocaleController localeController = Get.find<LocaleController>();

  @override
  void initState() {
    super.initState();
    _calculateCacheSize();
  }

  Future<void> _calculateCacheSize() async {
    try {
      final cacheDir = await getTemporaryDirectory();
      final totalSize = await _getTotalSizeOfFilesInDir(cacheDir);
      if (mounted) {
        setState(() {
          _cacheSize = totalSize;
        });
      }
    } catch (e) {
      debugPrint('Failed to calculate cache size: $e');
    }
  }

  Future<double> _getTotalSizeOfFilesInDir(Directory directory) async {
    double totalSize = 0;
    try {
      if (directory.existsSync()) {
        final files = directory.listSync(recursive: true);
        for (final file in files) {
          if (file is File) {
            totalSize += await file.length() / (1024 * 1024);
          }
        }
      }
    } catch (e) {
      debugPrint('Error getting size of files in directory: $e');
    }
    return totalSize;
  }

  Future<void> _clearCache() async {
    await DefaultCacheManager().emptyCache();
    await _calculateCacheSize();
    _showSuccessDialog('settings.cacheCleared'.tr);
  }

  Future<void> _logout() async {
    await AuthTokenStore.instance.clearJwtToken();
    if (Get.isRegistered<ChatController>()) {
      final chatController = Get.find<ChatController>();
      chatController.clearMessages();
    }
    Get.offAllNamed(Routes.login);
  }

  void _showSuccessDialog(String message) {
    if (!mounted) return;
    showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: Text('settings.successTitle'.tr),
          content: Text(
            [
              message,
              'settings.summary.darkMode'.trParams({
                'value': controller.currentTheme.value == 'Dark'
                    ? 'settings.themeMode.enabled'.tr
                    : 'settings.themeMode.disabled'.tr,
              }),
              'settings.summary.currentTheme'.trParams({
                'value': _selectedThemeLabel,
              }),
              'settings.summary.cacheSize'.trParams({
                'value': _cacheSize >= 0
                    ? _cacheSize.toStringAsFixed(2)
                    : 'common.calculating'.tr,
              }),
            ].join('\n'),
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(dialogContext).pop();
                controller.exitSidebarContent();
              },
              child: Text('common.ok'.tr),
            ),
          ],
        );
      },
    );
  }

  void _saveSettings() {
    _showSuccessDialog('settings.saved'.tr);
  }

  String get _selectedThemeLabel {
    final style = controller.selectedStyle.value.toLowerCase();
    final mode = controller.currentTheme.value == 'Dark' ? 'Dark' : 'Light';
    return 'settings.theme.$style$mode'.tr;
  }

  String get _currentLanguageLabel {
    return localeController.isChinese
        ? 'common.language.zh'.tr
        : 'common.language.en'.tr;
  }

  void _applyThemeSelection({
    required String style,
    required bool darkMode,
  }) {
    controller.setSelectedStyle(style);
    final shouldToggle = (controller.currentTheme.value == 'Dark') != darkMode;
    if (shouldToggle) {
      controller.toggleBodyTheme();
    }
    setState(() {});
    Navigator.of(context).pop();
  }

  void _showThemeDialog() {
    showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: Text('settings.themeDialogTitle'.tr),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                ListTile(
                  title: Text('settings.theme.materialLight'.tr),
                  onTap: () => _applyThemeSelection(
                    style: 'Material',
                    darkMode: false,
                  ),
                ),
                ListTile(
                  title: Text('settings.theme.materialDark'.tr),
                  onTap: () => _applyThemeSelection(
                    style: 'Material',
                    darkMode: true,
                  ),
                ),
                ListTile(
                  title: Text('settings.theme.ionicLight'.tr),
                  onTap: () => _applyThemeSelection(
                    style: 'Ionic',
                    darkMode: false,
                  ),
                ),
                ListTile(
                  title: Text('settings.theme.ionicDark'.tr),
                  onTap: () => _applyThemeSelection(
                    style: 'Ionic',
                    darkMode: true,
                  ),
                ),
                ListTile(
                  title: Text('settings.theme.basicLight'.tr),
                  onTap: () => _applyThemeSelection(
                    style: 'Basic',
                    darkMode: false,
                  ),
                ),
                ListTile(
                  title: Text('settings.theme.basicDark'.tr),
                  onTap: () => _applyThemeSelection(
                    style: 'Basic',
                    darkMode: true,
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: Text('common.cancel'.tr),
            ),
          ],
        );
      },
    );
  }

  Future<void> _showLanguageDialog() async {
    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: Text('common.language'.tr),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: AppTranslations.supportedLocales
                .map(
                  (locale) => ListTile(
                    title: Text(
                      locale.languageCode == 'zh'
                          ? 'common.language.zh'.tr
                          : 'common.language.en'.tr,
                    ),
                    onTap: () async {
                      await localeController.updateLocale(locale);
                      if (dialogContext.mounted) {
                        Navigator.of(dialogContext).pop();
                      }
                      if (mounted) {
                        setState(() {});
                      }
                    },
                  ),
                )
                .toList(),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: Text('common.cancel'.tr),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('settings.title'.tr),
      ),
      body: Obx(
        () => Theme(
          data: controller.currentBodyTheme.value,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: ListView(
              children: [
                ListTile(
                  leading: const Icon(Icons.palette, color: Colors.blue),
                  title: Text(
                    'settings.theme'.tr,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.onSurface,
                    ),
                  ),
                  subtitle: Text(
                    _selectedThemeLabel,
                    style: TextStyle(
                      color: Theme.of(context)
                          .colorScheme
                          .onSurface
                          .withValues(alpha: 0.7),
                    ),
                  ),
                  trailing:
                      const Icon(Icons.arrow_forward_ios, color: Colors.grey),
                  onTap: _showThemeDialog,
                ),
                const SizedBox(height: 16),
                ListTile(
                  leading: const Icon(Icons.language, color: Colors.blue),
                  title: Text(
                    'common.language'.tr,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.onSurface,
                    ),
                  ),
                  subtitle: Text(
                    _currentLanguageLabel,
                    style: TextStyle(
                      color: Theme.of(context)
                          .colorScheme
                          .onSurface
                          .withValues(alpha: 0.7),
                    ),
                  ),
                  trailing:
                      const Icon(Icons.arrow_forward_ios, color: Colors.grey),
                  onTap: _showLanguageDialog,
                ),
                const SizedBox(height: 16),
                ListTile(
                  leading: const Icon(Icons.storage, color: Colors.blue),
                  title: Text(
                    'settings.cache'.tr,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.onSurface,
                    ),
                  ),
                  subtitle: Text(
                    '${_cacheSize >= 0 ? _cacheSize.toStringAsFixed(2) : 'common.calculating'.tr} MB',
                    style: TextStyle(
                      color: Theme.of(context)
                          .colorScheme
                          .onSurface
                          .withValues(alpha: 0.7),
                    ),
                  ),
                  trailing:
                      const Icon(Icons.arrow_forward_ios, color: Colors.grey),
                  onTap: _clearCache,
                ),
                const SizedBox(height: 16),
                ListTile(
                  leading: const Icon(Icons.save, color: Colors.blue),
                  title: Text(
                    'settings.saveSettings'.tr,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.onSurface,
                    ),
                  ),
                  trailing:
                      const Icon(Icons.arrow_forward_ios, color: Colors.grey),
                  onTap: _saveSettings,
                ),
                const SizedBox(height: 16),
                ListTile(
                  leading: const Icon(Icons.home, color: Colors.blue),
                  title: Text(
                    'common.backHome'.tr,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.onSurface,
                    ),
                  ),
                  trailing:
                      const Icon(Icons.arrow_forward_ios, color: Colors.grey),
                  onTap: controller.exitSidebarContent,
                ),
                const SizedBox(height: 16),
                ListTile(
                  leading:
                      const Icon(Icons.feedback_outlined, color: Colors.blue),
                  title: Text(
                    'common.feedback'.tr,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.onSurface,
                    ),
                  ),
                  trailing:
                      const Icon(Icons.arrow_forward_ios, color: Colors.grey),
                  onTap: () => controller.navigateToPage(Routes.consultation),
                ),
                const SizedBox(height: 16),
                ListTile(
                  leading: const Icon(Icons.logout, color: Colors.blue),
                  title: Text(
                    'common.logout'.tr,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.onSurface,
                    ),
                  ),
                  trailing:
                      const Icon(Icons.arrow_forward_ios, color: Colors.grey),
                  onTap: () {
                    Get.dialog<void>(
                      AlertDialog(
                        title: Text('settings.confirmLogoutTitle'.tr),
                        content: Text('settings.confirmLogoutMessage'.tr),
                        actions: [
                          TextButton(
                            onPressed: Get.back,
                            child: Text('common.cancel'.tr),
                          ),
                          TextButton(
                            onPressed: () {
                              Get.back<void>();
                              _logout();
                            },
                            child: Text('common.confirm'.tr),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
