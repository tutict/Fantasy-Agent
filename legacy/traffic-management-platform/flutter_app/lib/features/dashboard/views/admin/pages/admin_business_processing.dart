import 'package:final_assignment_front/features/dashboard/controllers/admin_dashboard_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/admin/pages/main_process/appeal_management.dart';
import 'package:final_assignment_front/features/dashboard/views/admin/pages/main_process/deduction_management.dart';
import 'package:final_assignment_front/features/dashboard/views/admin/pages/main_process/driver_list.dart';
import 'package:final_assignment_front/features/dashboard/views/admin/pages/main_process/fine_list.dart';
import 'package:final_assignment_front/features/dashboard/views/admin/pages/main_process/offense_list.dart';
import 'package:final_assignment_front/features/dashboard/views/admin/pages/main_process/vehicle_list.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/dashboard_page_template.dart';
import 'package:final_assignment_front/utils/helpers/role_utils.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:jwt_decoder/jwt_decoder.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AdminBusinessProcessing extends StatefulWidget {
  const AdminBusinessProcessing({
    super.key,
    this.titleKey = 'admin.business.title',
    this.enterLabelKey = 'admin.business.enter',
    this.pageType = DashboardPageType.admin,
  });

  final String titleKey;
  final String enterLabelKey;
  final DashboardPageType pageType;

  @override
  State<AdminBusinessProcessing> createState() =>
      _AdminBusinessProcessingState();
}

class _AdminBusinessProcessingState extends State<AdminBusinessProcessing> {
  late DashboardController controller;
  List<String> _currentRoles = [];
  bool _isLoadingRoles = true;

  final List<Map<String, dynamic>> businessOptions = [
    {
      'titleKey': 'admin.business.appeal',
      'icon': Icons.gavel,
      'route': const AppealManagementAdmin(),
      'allowedRoles': const ['SUPER_ADMIN', 'ADMIN', 'APPEAL_REVIEWER'],
    },
    {
      'titleKey': 'admin.business.deduction',
      'icon': Icons.score,
      'route': const DeductionManagement(),
      'allowedRoles': const ['SUPER_ADMIN', 'ADMIN', 'TRAFFIC_POLICE'],
    },
    {
      'titleKey': 'admin.business.driver',
      'icon': Icons.person,
      'route': const DriverList(),
      'allowedRoles': const ['SUPER_ADMIN', 'ADMIN', 'TRAFFIC_POLICE'],
    },
    {
      'titleKey': 'admin.business.fine',
      'icon': Icons.payment,
      'route': const FineList(),
      'allowedRoles': const [
        'SUPER_ADMIN',
        'ADMIN',
        'TRAFFIC_POLICE',
        'FINANCE',
      ],
    },
    {
      'titleKey': 'admin.business.vehicle',
      'icon': Icons.directions_car,
      'route': const VehicleList(),
      'allowedRoles': const ['SUPER_ADMIN', 'ADMIN', 'TRAFFIC_POLICE'],
    },
    {
      'titleKey': 'admin.business.offense',
      'icon': Icons.warning,
      'route': const OffenseList(),
      'allowedRoles': const [
        'SUPER_ADMIN',
        'ADMIN',
        'TRAFFIC_POLICE',
        'APPEAL_REVIEWER',
      ],
    },
  ];

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

  Future<void> _loadRoles() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final storedRoles = prefs.getStringList('userRoles');
      final fallbackRole = prefs.getString('userRole');
      final jwtToken = await AuthTokenStore.instance.getJwtToken();
      final jwtRoles = jwtToken == null
          ? const []
          : normalizeRoleCodes(JwtDecoder.decode(jwtToken)['roles']);
      final effectiveRoles = storedRoles != null && storedRoles.isNotEmpty
          ? normalizeRoleCodes(storedRoles)
          : normalizeRoleCodes([
              if (fallbackRole != null && fallbackRole.isNotEmpty) fallbackRole,
              ...jwtRoles,
            ]);
      if (!mounted) return;
      setState(() {
        _currentRoles = effectiveRoles;
        _isLoadingRoles = false;
      });
    } catch (e) {
      debugPrint('Failed to resolve business roles: $e');
      if (!mounted) return;
      setState(() => _isLoadingRoles = false);
    }
  }

  void _navigateToBusiness(Widget route) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => route),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final themeData = controller.currentBodyTheme.value;
      final colorScheme = themeData.colorScheme;
      final visibleOptions = businessOptions.where((option) {
        final allowedRoles = option['allowedRoles'] as List<String>;
        return hasAnyRole(_currentRoles, allowedRoles);
      }).toList();

      return DashboardPageTemplate(
        theme: themeData,
        title: widget.titleKey.tr,
        pageType: widget.pageType,
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
              : visibleOptions.isEmpty
                  ? Center(
                      child: Text(
                        'common.noData'.tr,
                        style: themeData.textTheme.bodyLarge?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    )
                  : GridView.builder(
                      gridDelegate:
                          const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 2,
                        childAspectRatio: 4 / 3,
                        crossAxisSpacing: 16,
                        mainAxisSpacing: 16,
                      ),
                      itemCount: visibleOptions.length,
                      itemBuilder: (context, index) {
                        final option = visibleOptions[index];
                        return InkWell(
                          borderRadius: BorderRadius.circular(20),
                          onTap: () =>
                              _navigateToBusiness(option['route'] as Widget),
                          child: Ink(
                            decoration: BoxDecoration(
                              color: colorScheme.surfaceContainer,
                              borderRadius: BorderRadius.circular(20),
                              border:
                                  Border.all(color: colorScheme.outlineVariant),
                            ),
                            child: Padding(
                              padding: const EdgeInsets.all(16.0),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  CircleAvatar(
                                    backgroundColor: colorScheme
                                        .primaryContainer
                                        .withValues(alpha: 0.6),
                                    child: Icon(
                                      option['icon'] as IconData,
                                      color: colorScheme.onPrimaryContainer,
                                    ),
                                  ),
                                  const Spacer(),
                                  Text(
                                    (option['titleKey'] as String).tr,
                                    style: themeData.textTheme.titleMedium
                                        ?.copyWith(
                                      color: colorScheme.onSurface,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    widget.enterLabelKey.tr,
                                    style:
                                        themeData.textTheme.bodySmall?.copyWith(
                                      color: colorScheme.onSurfaceVariant,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        );
                      },
                    ),
        ),
      );
    });
  }
}
