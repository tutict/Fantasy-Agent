import 'package:final_assignment_front/features/dashboard/controllers/admin_dashboard_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/admin/pages/logs/login_log_page.dart';
import 'package:final_assignment_front/features/dashboard/views/admin/pages/logs/operation_log_page.dart';
import 'package:final_assignment_front/features/dashboard/views/admin/pages/logs/system_log_page.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/dashboard_page_template.dart';
import 'package:final_assignment_front/utils/helpers/role_utils.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class LogManagement extends StatefulWidget {
  const LogManagement({super.key});

  @override
  State<LogManagement> createState() => _LogManagementState();
}

class _LogManagementState extends State<LogManagement> {
  late DashboardController controller;
  List<String> _currentRoles = [];
  bool _isLoadingRoles = true;

  @override
  void initState() {
    super.initState();
    try {
      controller = Get.find<DashboardController>();
    } catch (e) {
      debugPrint('DashboardController not found: $e');
      controller = Get.put(DashboardController());
    }
    _loadRoles();
  }

  final List<Map<String, dynamic>> logOptions = [
    {
      'titleKey': 'loginLog.page.title',
      'icon': Icons.login_rounded,
      'route': const LoginLogPage(),
    },
    {
      'titleKey': 'operationLog.page.title',
      'icon': Icons.history,
      'route': const OperationLogPage(),
    },
    {
      'titleKey': 'systemLog.page.title',
      'icon': Icons.book_outlined,
      'route': const SystemLogPage(),
    },
  ];

  void _navigateToLogPage(Widget route) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => route),
    );
  }

  Future<void> _loadRoles() async {
    try {
      await controller.refreshRoleState();
      if (!mounted) return;
      setState(() {
        _currentRoles = controller.currentRoles.toList();
        _isLoadingRoles = false;
      });
    } catch (e) {
      debugPrint('Failed to resolve log roles: $e');
      if (!mounted) return;
      setState(() => _isLoadingRoles = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Obx(
      () {
        final themeData = controller.currentBodyTheme.value;
        final colorScheme = themeData.colorScheme;
        final canManageLogs =
            hasAnyRole(_currentRoles, const ['SUPER_ADMIN', 'ADMIN']);
        return DashboardPageTemplate(
          theme: themeData,
          title: 'admin.logs.title'.tr,
          pageType: DashboardPageType.admin,
          bodyIsScrollable: true,
          padding: EdgeInsets.zero,
          onThemeToggle: controller.toggleBodyTheme,
          body: Padding(
            padding: const EdgeInsets.all(16.0),
            child: _isLoadingRoles
                ? Center(
                    child: CircularProgressIndicator(
                      color: colorScheme.primary,
                    ),
                  )
                : !canManageLogs
                    ? Center(
                        child: Text(
                          'common.noData'.tr,
                          style: themeData.textTheme.bodyLarge?.copyWith(
                            color: colorScheme.onSurfaceVariant,
                          ),
                          textAlign: TextAlign.center,
                        ),
                      )
                    : ListView.separated(
                        itemCount: logOptions.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 12),
                        itemBuilder: (context, index) {
                          final option = logOptions[index];
                          return Card(
                            elevation: 2,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16),
                            ),
                            color: colorScheme.surfaceContainer,
                            child: ListTile(
                              leading: CircleAvatar(
                                backgroundColor: colorScheme.primaryContainer,
                                child: Icon(
                                  option['icon'],
                                  color: colorScheme.onPrimaryContainer,
                                ),
                              ),
                              title: Text(
                                (option['titleKey'] as String).tr,
                                style:
                                    themeData.textTheme.titleMedium?.copyWith(
                                  color: colorScheme.onSurface,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              trailing: Icon(
                                Icons.arrow_forward_ios,
                                color: colorScheme.onSurfaceVariant,
                                size: 18,
                              ),
                              onTap: () => _navigateToLogPage(option['route']),
                            ),
                          );
                        },
                      ),
          ),
        );
      },
    );
  }
}
