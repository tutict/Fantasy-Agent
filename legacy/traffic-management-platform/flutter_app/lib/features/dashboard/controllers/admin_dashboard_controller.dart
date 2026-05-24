import 'package:final_assignment_front/config/routes/app_routes.dart';
import 'package:final_assignment_front/config/themes/app_theme.dart';
import 'package:final_assignment_front/constants/app_constants.dart';
import 'package:final_assignment_front/features/api/offense_information_controller_api.dart';
import 'package:final_assignment_front/features/api/role_management_controller_api.dart';
import 'package:final_assignment_front/features/dashboard/models/profile.dart';
import 'package:final_assignment_front/features/model/offense_information.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/shared_components/case_card.dart';
import 'package:final_assignment_front/shared_components/project_card.dart';
import 'package:final_assignment_front/utils/helpers/app_helpers.dart';
import 'package:final_assignment_front/utils/helpers/role_utils.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

class DashboardController extends GetxController {
  final scaffoldKey = GlobalKey<ScaffoldState>();
  final caseCardDataList = <CaseCardData>[].obs;
  final selectedStyle = 'Basic'.obs;
  final currentTheme = 'Light'.obs;
  final Rx<ThemeData> currentBodyTheme = AppTheme.basicLight.obs;
  final selectedCaseType = CaseType.caseManagement.obs;
  final isShowingSidebarContent = false.obs;
  final isScrollingDown = false.obs;
  final isDesktop = false.obs;
  final isSidebarOpen = false.obs;
  final selectedPage = Rx<Widget?>(null);
  final isChatExpanded = false.obs;
  final Rx<Profile?> currentUser = Rx<Profile?>(null);
  final RxList<String> currentRoles = <String>[].obs;
  late Rx<Future<List<OffenseInformation>>> offensesFuture;
  final RxString currentDriverName = ''.obs;
  final RxString currentEmail = ''.obs;
  final RxBool _refreshPersonalPage = false.obs;
  final offenseApi = OffenseInformationControllerApi();
  final roleApi = RoleManagementControllerApi();
  Widget? Function(String routeName)? pageResolver;

  @override
  void onInit() {
    super.onInit();
    _initializeCaseCardData();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadUserFromPrefs();
      _loadTheme();
    });
  }

  Future<void> _loadTheme() async {
    final prefs = await SharedPreferences.getInstance();
    final themeKey = 'dashboardTheme_${selectedStyle.value}';
    final storedTheme = prefs.getString(themeKey);
    if (storedTheme != null) {
      currentTheme.value = storedTheme;
      _applyTheme();
    } else {
      final systemBrightness =
          WidgetsBinding.instance.platformDispatcher.platformBrightness;
      currentTheme.value =
          systemBrightness == Brightness.dark ? 'Dark' : 'Light';
      _applyTheme();
      await prefs.setString(themeKey, currentTheme.value);
    }
  }

  void loadAdminData() {
    offensesFuture = Rx<Future<List<OffenseInformation>>>(_fetchAllOffenses());
  }

  Future<void> refreshRoleState() async {
    final prefs = await SharedPreferences.getInstance();
    final storedRoles = prefs.getStringList('userRoles');
    final fallbackRole = prefs.getString('userRole');
    final effectiveRoles = storedRoles != null && storedRoles.isNotEmpty
        ? normalizeRoleCodes(storedRoles)
        : <String>[
            if (fallbackRole != null && fallbackRole.isNotEmpty)
              ...normalizeRoleCodes([fallbackRole]),
          ];
    currentRoles
      ..clear()
      ..addAll(effectiveRoles);
  }

  Future<void> _loadUserFromPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    final jwtToken = await AuthTokenStore.instance.getJwtToken();
    final userName = prefs.getString('userName');
    final displayName =
        prefs.getString('displayName') ?? prefs.getString('driverName');
    final userEmail = prefs.getString('userEmail');
    final userRole = prefs.getString('userRole');
    final resolvedDisplayName = (displayName != null && displayName.isNotEmpty)
        ? displayName
        : userName;

    if (jwtToken != null &&
        resolvedDisplayName != null &&
        userEmail != null &&
        userRole != null) {
      currentUser.value = Profile(
        photo: const AssetImage(ImageRasterPath.avatar1),
        name: resolvedDisplayName,
        email: userEmail,
      );
      currentDriverName.value = resolvedDisplayName;
      currentEmail.value = userEmail;
      await refreshRoleState();
      await offenseApi.initializeWithJwt();
      await roleApi.initializeWithJwt();
    } else {
      _showErrorSnackBar('auth.error.loginRequiredForReset'.tr);
      _redirectToLogin();
    }
  }

  Future<void> _validateTokenAndRole() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final storedRoles = prefs.getStringList('userRoles');
      final fallbackRole = prefs.getString('userRole');
      final effectiveRoles = storedRoles != null && storedRoles.isNotEmpty
          ? storedRoles
          : <String>[
              if (fallbackRole != null && fallbackRole.isNotEmpty) fallbackRole,
            ];
      if (!hasManagementAccess(effectiveRoles)) {
        throw Exception('dashboard.error.adminOnlyFunction'.tr);
      }
    } catch (e) {
      _showErrorSnackBar(_formatDashboardError(e));
      _redirectToLogin();
      rethrow;
    }
  }

  void updateCurrentUser(String name, String email) {
    currentDriverName.value = name;
    currentEmail.value = email;
    currentUser.value = Profile(
      photo:
          currentUser.value?.photo ?? const AssetImage(ImageRasterPath.avatar1),
      name: name,
      email: email,
    );
    debugPrint('DashboardController updated - Name: $name, Email: $email');
    _saveUserToPrefs(name, email);
  }

  Future<void> _saveUserToPrefs(String name, String email) async {
    final prefs = await SharedPreferences.getInstance();
    if (name.isNotEmpty) {
      await prefs.setString('displayName', name);
    }
    if (email.isNotEmpty) {
      await prefs.setString('userEmail', email);
    }
    final existingRole = prefs.getString('userRole');
    final resolvedRole = existingRole ?? resolveStoredUserRole(currentRoles);
    if (resolvedRole.isNotEmpty) {
      await prefs.setString('userRole', resolvedRole);
    }
  }

  Profile get currentProfile =>
      currentUser.value ??
      Profile(
        photo: const AssetImage(ImageRasterPath.avatar1),
        name: 'personal.value.unknownUser'.tr,
        email: 'common.notFilled'.tr,
      );

  void toggleSidebar() => isSidebarOpen.value = !isSidebarOpen.value;

  void toggleBodyTheme() {
    final newMode = currentTheme.value == 'Light' ? 'Dark' : 'Light';
    currentTheme.value = newMode;
    _applyTheme();
    SharedPreferences.getInstance().then((prefs) {
      prefs.setBool('isDarkMode', newMode == 'Dark');
      prefs.setString('dashboardTheme_${selectedStyle.value}', newMode);
    });
  }

  void toggleChat() => isChatExpanded.value = !isChatExpanded.value;

  void _applyTheme() {
    currentBodyTheme.value = AppTheme.resolveDashboardTheme(
      style: selectedStyle.value,
      mode: currentTheme.value,
    );

    Get.changeTheme(currentBodyTheme.value);
    _persistThemeSelection();
  }

  void _persistThemeSelection() {
    SharedPreferences.getInstance().then((prefs) {
      prefs.setString(
        'dashboardTheme_${selectedStyle.value}',
        currentTheme.value,
      );
    });
  }

  void triggerPersonalPageRefresh() {
    exitSidebarContent();
  }

  void openDrawer() => isDesktop.value
      ? isSidebarOpen.value = true
      : scaffoldKey.currentState?.openDrawer();

  void closeSidebar() => isDesktop.value ? isSidebarOpen.value = false : null;

  void onCaseTypeSelected(CaseType selectedType) {
    selectedCaseType.value = selectedType;
  }

  List<CaseCardData> getCaseByType(CaseType type) =>
      caseCardDataList.where((task) => task.type == type).toList();

  void navigateToPage(String routeName) {
    debugPrint('Navigate to route: $routeName');
    selectedPage.value = pageResolver?.call(routeName);
    isShowingSidebarContent.value = true;
  }

  void exitSidebarContent() {
    debugPrint('Exit sidebar content');
    isShowingSidebarContent.value = false;
    selectedPage.value = null;
  }

  Widget buildSelectedPageContent() =>
      Obx(() => selectedPage.value ?? const SizedBox.shrink());

  ProjectCardData getSelectedProject() => ProjectCardData(
        percent: .3,
        projectImage: const AssetImage(ImageRasterPath.logo4),
        projectName: 'dashboard.projectName',
        releaseTime: DateTime.now(),
      );

  List<ProjectCardData> getActiveProject() => [];

  List<ImageProvider<Object>> getMember() => const [
        AssetImage(ImageRasterPath.avatar1),
        AssetImage(ImageRasterPath.avatar2),
        AssetImage(ImageRasterPath.avatar3),
        AssetImage(ImageRasterPath.avatar4),
        AssetImage(ImageRasterPath.avatar5),
        AssetImage(ImageRasterPath.avatar6),
      ];

  Future<Map<String, int>> getOffenseTypeDistribution() async {
    try {
      final offenses = await offensesFuture.value;
      final Map<String, int> typeCountMap = {};
      for (final o in offenses) {
        final type = o.offenseType ?? 'dashboard.offense.unknownType'.tr;
        typeCountMap[type] = (typeCountMap[type] ?? 0) + 1;
      }
      return typeCountMap;
    } catch (e) {
      debugPrint('Error fetching offense distribution: $e');
      return {};
    }
  }

  Future<List<OffenseInformation>> _fetchAllOffenses() async {
    try {
      await _validateTokenAndRole();
      const pageSize = 100;
      final List<OffenseInformation> allOffenses = [];
      var page = 1;
      while (true) {
        final offenses =
            await offenseApi.apiOffensesGet(page: page, size: pageSize);
        if (offenses.isEmpty) {
          break;
        }
        allOffenses.addAll(offenses);
        if (offenses.length < pageSize) {
          break;
        }
        page++;
      }
      return allOffenses;
    } catch (e) {
      debugPrint('Failed to fetch offense information: $e');
      _showErrorSnackBar(
        'offense.error.loadFailed'
            .trParams({'error': _formatDashboardError(e)}),
      );
      return [];
    }
  }

  String _formatDashboardError(Object error) {
    return localizeApiErrorDetail(error);
  }

  void _showErrorSnackBar(String message) {
    Get.snackbar(
      'dashboard.error.title'.tr,
      message,
      snackPosition: SnackPosition.BOTTOM,
      backgroundColor: Colors.red.withValues(alpha: 0.9),
      colorText: Colors.white,
      duration: const Duration(seconds: 3),
    );
  }

  void _redirectToLogin() {
    Get.offAllNamed(Routes.login);
  }

  void updateScrollDirection(ScrollController scrollController) {
    scrollController.addListener(() {
      isScrollingDown.value = scrollController.position.userScrollDirection ==
          ScrollDirection.reverse;
    });
  }

  void _initializeCaseCardData() {
    caseCardDataList.addAll([
      CaseCardData(
        title: 'dashboard.task.todo1',
        dueDay: 5,
        totalComments: 10,
        totalContributors: 3,
        type: CaseType.caseManagement,
        profilContributors: const [],
      ),
      CaseCardData(
        title: 'dashboard.task.inProgress1',
        dueDay: 10,
        totalComments: 5,
        totalContributors: 2,
        type: CaseType.caseSearch,
        profilContributors: const [],
      ),
      CaseCardData(
        title: 'dashboard.task.done1',
        dueDay: -2,
        totalComments: 3,
        totalContributors: 1,
        type: CaseType.caseAppeal,
        profilContributors: const [],
      ),
    ]);
  }

  void setSelectedStyle(String style) {
    selectedStyle.value = style;
    _loadTheme();
  }

  RxBool get refreshPersonalPage => _refreshPersonalPage;
}
