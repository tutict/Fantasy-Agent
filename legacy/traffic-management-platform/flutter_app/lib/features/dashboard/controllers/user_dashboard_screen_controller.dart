import 'dart:developer' as developer;

import 'package:final_assignment_front/config/routes/app_routes.dart';
import 'package:final_assignment_front/config/themes/app_theme.dart';
import 'package:final_assignment_front/constants/app_constants.dart';
import 'package:final_assignment_front/features/api/driver_information_controller_api.dart';
import 'package:final_assignment_front/features/api/offense_information_controller_api.dart';
import 'package:final_assignment_front/features/api/role_management_controller_api.dart';
import 'package:final_assignment_front/features/api/user_management_controller_api.dart';
import 'package:final_assignment_front/features/dashboard/models/profile.dart';
import 'package:final_assignment_front/shared_components/case_card.dart';
import 'package:final_assignment_front/shared_components/project_card.dart';
import 'package:final_assignment_front/utils/helpers/app_helpers.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// UserDashboardController 管理用户主页的主线控制器，包含主要的进入流程、数据处理和界面的控制。

class UserDashboardController extends GetxController {
  final scaffoldKey = GlobalKey<ScaffoldState>();
  final caseCardDataList = <CaseCardData>[].obs;
  var selectedStyle = 'Basic'.obs;
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
  final RxBool _refreshPersonalPage = false.obs;
  final RxString currentDriverName = ''.obs;
  final RxString currentEmail = ''.obs;
  var driverLicenseNumber = RxString('');
  var idCardNumber = RxString('');
  final isLoadingUser = true.obs; // Loading state for user data
  final offenseApi = OffenseInformationControllerApi();
  final roleApi = RoleManagementControllerApi();
  Widget? Function(String routeName)? pageResolver;

  @override
  void onInit() {
    super.onInit();
    _initializeCaseCardData();
    _loadUserFromPrefs();
    loadCredentials();
    _loadTheme();
  }

  @override
  void onReady() {
    super.onReady();
    refreshUserData();
  }

  Future<void> _loadTheme() async {
    final prefs = await SharedPreferences.getInstance();
    final storedTheme = prefs.getString('userTheme_${selectedStyle.value}');
    if (storedTheme != null) {
      currentTheme.value = storedTheme;
      _applyTheme();
    } else {
      final brightness =
          WidgetsBinding.instance.platformDispatcher.platformBrightness;
      currentTheme.value = brightness == Brightness.dark ? 'Dark' : 'Light';
      _applyTheme();
      await prefs.setString(
          'userTheme_${selectedStyle.value}', currentTheme.value);
    }
  }

  Future<void> _loadUserFromPrefs() async {
    isLoadingUser.value = true;
    try {
      final prefs = await SharedPreferences.getInstance();
      final jwtToken = await AuthTokenStore.instance.getJwtToken();
      final userName = prefs.getString('userName');
      final displayName =
          prefs.getString('displayName') ?? prefs.getString('driverName');
      final userEmail = prefs.getString('userEmail');
      final resolvedDisplayName =
          (displayName != null && displayName.isNotEmpty)
              ? displayName
              : userName;

      if (jwtToken != null &&
          userName != null &&
          resolvedDisplayName != null &&
          userEmail != null) {
        currentUser.value = Profile(
          photo: const AssetImage(ImageRasterPath.avatar1),
          name: resolvedDisplayName,
          email: userEmail,
        );
        currentDriverName.value = resolvedDisplayName;
        currentEmail.value = userEmail;
        await offenseApi.initializeWithJwt();
        await roleApi.initializeWithJwt();
        await _fetchDriverData();
      } else {
        _showErrorSnackBar('auth.error.loginRequiredForReset'.tr);
        _redirectToLogin();
      }
    } catch (e) {
      developer.log('Error loading user from prefs: $e');
      _showErrorSnackBar('personal.error.loadUserFailed'.tr);
      _redirectToLogin();
    } finally {
      isLoadingUser.value = false;
    }
  }

  Future<void> _fetchDriverData() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final storedUsername = prefs.getString('userName');
      final userApi = UserManagementControllerApi();
      await userApi.initializeWithJwt();
      final user = await userApi.apiUsersMeGet();

      final driverApi = DriverInformationControllerApi();
      await driverApi.initializeWithJwt();
      final driver = await driverApi.apiDriversMeGet();
      final resolvedName = driver?.name ??
          prefs.getString('displayName') ??
          prefs.getString('driverName') ??
          user?.realName ??
          user?.username ??
          storedUsername ??
          currentDriverName.value;
      final resolvedEmail = user?.email ?? currentEmail.value;

      updateCurrentUser(
        resolvedName,
        resolvedEmail,
      );
      driverLicenseNumber.value = driver?.driverLicenseNumber ?? '';
      idCardNumber.value = driver?.idCardNumber ?? '';
      if (resolvedName.isNotEmpty) {
        await prefs.setString('displayName', resolvedName);
        await prefs.setString('driverName', resolvedName);
      }
      if (user?.userId != null) {
        await prefs.setString('userId', user!.userId.toString());
      }
      if (resolvedEmail.isNotEmpty) {
        await prefs.setString('userEmail', resolvedEmail);
      }
      developer.log(
          'Updated user info from API: name=$resolvedName, id=${user?.userId}');
    } catch (e) {
      developer.log('Failed to fetch driver data: $e');
      _showErrorSnackBar('offense.error.driverNameMissing'.tr);
    }
  }

  Future<void> refreshUserData() async {
    developer.log('Refreshing user data');
    await _loadUserFromPrefs();
  }

  void _redirectToLogin() {
    Get.offAllNamed(Routes.login);
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

  Future<void> loadCredentials() async {
    final prefs = await SharedPreferences.getInstance();
    driverLicenseNumber.value = prefs.getString('driverLicenseNumber') ?? '';
    idCardNumber.value = prefs.getString('idCardNumber') ?? '';
    developer.log(
        'Loaded credentials: driverLicense=${driverLicenseNumber.value}, idCard=${idCardNumber.value}');
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
    developer
        .log('UserDashboardController updated - Name: $name, Email: $email');
    _saveUserToPrefs(name, email);
  }

  Future<void> _saveUserToPrefs(String name, String email) async {
    final prefs = await SharedPreferences.getInstance();
    if (name.isNotEmpty) {
      await prefs.setString('displayName', name);
      await prefs.setString('driverName', name);
    }
    if (email.isNotEmpty) {
      await prefs.setString('userEmail', email);
    }
  }

  Profile get currentProfile =>
      currentUser.value ??
      Profile(
        photo: const AssetImage(ImageRasterPath.avatar1),
        name: 'personal.value.unknownUser'.tr,
        email: 'common.notFilled'.tr,
      );

  void toggleSidebar() {
    isSidebarOpen.value = !isSidebarOpen.value;
  }

  void toggleBodyTheme() {
    final newMode = currentTheme.value == 'Light' ? 'Dark' : 'Light';
    currentTheme.value = newMode;
    _applyTheme();
    SharedPreferences.getInstance().then((prefs) {
      prefs.setBool('isDarkMode', newMode == 'Dark');
      prefs.setString('userTheme_${selectedStyle.value}', newMode);
    });
  }

  void toggleChat() {
    isChatExpanded.value = !isChatExpanded.value;
  }

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
      prefs.setString('userTheme_${selectedStyle.value}', currentTheme.value);
    });
  }

  void triggerPersonalPageRefresh() {
    exitSidebarContent();
  }

  void openDrawer() => isDesktop.value
      ? isSidebarOpen.value = true
      : scaffoldKey.currentState?.openDrawer();

  void closeSidebar() => isDesktop.value ? isSidebarOpen.value = false : null;

  void onCaseTypeSelected(CaseType selectedType) =>
      selectedCaseType.value = selectedType;

  List<CaseCardData> getCaseByType(CaseType type) =>
      caseCardDataList.where((task) => task.type == type).toList();

  void navigateToPage(String routeName) {
    developer.log('Navigating to: $routeName');
    selectedPage.value = pageResolver?.call(routeName);
    isShowingSidebarContent.value = true;
  }

  void exitSidebarContent() {
    developer.log('Exiting sidebar content');
    isShowingSidebarContent.value = false;
    selectedPage.value = null;
  }

  Widget buildSelectedPageContent() {
    return Obx(() {
      final pageContent = selectedPage.value;
      return pageContent ?? const SizedBox.shrink();
    });
  }

  ProjectCardData getSelectedProject() => ProjectCardData(
        percent: .3,
        projectImage: const AssetImage(ImageRasterPath.logo4),
        projectName: 'dashboard.projectName',
        releaseTime: DateTime.now(),
      );

  List<ProjectCardData> getActiveProject() => [];

  List<ImageProvider> getMember() => const [
        AssetImage(ImageRasterPath.avatar1),
        AssetImage(ImageRasterPath.avatar2),
        AssetImage(ImageRasterPath.avatar3),
        AssetImage(ImageRasterPath.avatar4),
        AssetImage(ImageRasterPath.avatar5),
        AssetImage(ImageRasterPath.avatar6),
      ];

  void updateScrollDirection(ScrollController scrollController) {
    scrollController.addListener(() {
      isScrollingDown.value = scrollController.position.userScrollDirection ==
          ScrollDirection.reverse;
    });
  }

  void _initializeCaseCardData() {
    caseCardDataList.addAll([
      const CaseCardData(
        title: 'dashboard.task.todo1',
        dueDay: 5,
        totalComments: 10,
        totalContributors: 3,
        type: CaseType.caseManagement,
        profilContributors: [],
      ),
      const CaseCardData(
        title: 'dashboard.task.inProgress1',
        dueDay: 10,
        totalComments: 5,
        totalContributors: 2,
        type: CaseType.caseSearch,
        profilContributors: [],
      ),
      const CaseCardData(
        title: 'dashboard.task.done1',
        dueDay: -2,
        totalComments: 3,
        totalContributors: 1,
        type: CaseType.caseAppeal,
        profilContributors: [],
      ),
    ]);
  }

  void setSelectedStyle(String style) {
    selectedStyle.value = style;
    _loadTheme();
  }

  RxBool get refreshPersonalPage => _refreshPersonalPage;
}
