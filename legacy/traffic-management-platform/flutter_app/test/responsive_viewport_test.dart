// ignore_for_file: must_call_super

import 'dart:convert';

import 'package:final_assignment_front/config/themes/app_theme.dart';
import 'package:final_assignment_front/features/dashboard/controllers/admin_dashboard_controller.dart';
import 'package:final_assignment_front/features/dashboard/controllers/chat_controller.dart';
import 'package:final_assignment_front/features/dashboard/controllers/progress_controller.dart';
import 'package:final_assignment_front/features/dashboard/controllers/user_dashboard_screen_controller.dart';
import 'package:final_assignment_front/features/dashboard/models/profile.dart';
import 'package:final_assignment_front/features/dashboard/views/admin/admin_dashboard_screen.dart';
import 'package:final_assignment_front/features/dashboard/views/admin/pages/admin_business_processing.dart';
import 'package:final_assignment_front/features/dashboard/views/admin/pages/admin_setting_page.dart';
import 'package:final_assignment_front/features/dashboard/views/admin/pages/progress_management.dart';
import 'package:final_assignment_front/features/dashboard/views/admin/pages/sidebar_management/log_management.dart';
import 'package:final_assignment_front/features/dashboard/views/admin/pages/sidebar_management/user_management_page.dart';
import 'package:final_assignment_front/features/dashboard/views/manager/manager_dashboard_screen.dart';
import 'package:final_assignment_front/features/dashboard/views/manager/pages/manager_personal_page.dart';
import 'package:final_assignment_front/features/dashboard/views/manager/pages/manager_setting.dart';
import 'package:final_assignment_front/features/dashboard/views/manager/pages/sidebar_management/manager_business_processing.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/agent_dashboard_shell.dart';
import 'package:final_assignment_front/features/dashboard/views/user/pages/main_process/business_progress.dart';
import 'package:final_assignment_front/features/dashboard/views/user/pages/main_process/online_processing_progress.dart';
import 'package:final_assignment_front/features/dashboard/views/user/user_dashboard.dart';
import 'package:final_assignment_front/features/dashboard/views/user/widgets/news_page_layout.dart';
import 'package:final_assignment_front/features/login_screen/login.dart';
import 'package:final_assignment_front/features/model/progress_item.dart';
import 'package:final_assignment_front/i18n/app_translations.dart';
import 'package:final_assignment_front/i18n/locale_controller.dart';
import 'package:final_assignment_front/i18n/progress_localizers.dart';
import 'package:final_assignment_front/shared_components/responsive_builder.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() async {
    await initializeDateFormatting('zh_CN');
    await initializeDateFormatting('en_US');
  });

  const viewports = <({String label, Size size, ResponsiveTier tier})>[
    (label: 'phone', size: Size(390, 844), tier: ResponsiveTier.phone),
    (
      label: 'tablet-portrait',
      size: Size(768, 1024),
      tier: ResponsiveTier.tablet,
    ),
    (
      label: 'tablet-landscape',
      size: Size(1024, 768),
      tier: ResponsiveTier.tablet,
    ),
    (label: 'wide-desktop', size: Size(1440, 960), tier: ResponsiveTier.wide),
  ];

  final transparentAvatar = MemoryImage(
    base64Decode(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO3Zk2QAAAAASUVORK5CYII=',
    ),
  );

  setUp(() async {
    Get.testMode = true;
    Get.reset();
    SharedPreferences.setMockInitialValues({
      'app.languageCode': 'zh',
      'app.countryCode': 'CN',
      'isDarkMode': false,
    });
    Get.put(LocaleController(const Locale('zh', 'CN')));
  });

  tearDown(Get.reset);

  test('responsive metrics map widths to tiers', () {
    expect(ResponsiveMetrics.fromWidth(390).tier, ResponsiveTier.phone);
    expect(ResponsiveMetrics.fromWidth(768).tier, ResponsiveTier.tablet);
    expect(ResponsiveMetrics.fromWidth(1200).tier, ResponsiveTier.desktop);
    expect(ResponsiveMetrics.fromWidth(1440).tier, ResponsiveTier.wide);
  });

  group('viewport smoke tests', () {
    for (final viewport in viewports) {
      testWidgets(
        'LoginScreen renders without layout errors on ${viewport.label}',
        (tester) async {
          await _setViewport(tester, viewport.size);

          await tester.pumpWidget(_buildHarness(const LoginScreen()));
          await _pumpSmokeFrame(tester);

          expect(find.byType(LoginScreen), findsOneWidget);
          _expectNoFlutterErrors(tester);
        },
      );

      testWidgets(
        'AgentDashboardShell renders without layout errors on ${viewport.label}',
        (tester) async {
          await _setViewport(tester, viewport.size);
          Get.put<ChatController>(_FakeChatController());

          await tester.pumpWidget(
            _buildHarness(
              AgentDashboardShell(
                scaffoldKey: GlobalKey<ScaffoldState>(),
                theme: AppTheme.basicLight,
                title: 'Traffic Agent',
                subtitle: 'Workspace verification',
                profile: Profile(
                  photo: transparentAvatar,
                  name: 'Operator',
                  email: 'operator@example.com',
                ),
                navigationItems: [
                  AgentDashboardNavItem(
                    label: 'Home',
                    icon: Icons.home_rounded,
                    active: true,
                    onTap: () {},
                  ),
                  AgentDashboardNavItem(
                    label: 'Progress',
                    icon: Icons.timeline_rounded,
                    onTap: () {},
                  ),
                  AgentDashboardNavItem(
                    label: 'Settings',
                    icon: Icons.tune_rounded,
                    onTap: () {},
                  ),
                ],
                body: const _ViewportBody(),
                chatPanel: const _ViewportChatPanel(),
              ),
            ),
          );
          await _pumpSmokeFrame(tester);

          expect(find.byType(AgentDashboardShell), findsOneWidget);
          _expectNoFlutterErrors(tester);
        },
      );

      testWidgets(
        'UserDashboard home renders without layout errors on ${viewport.label}',
        (tester) async {
          await _setViewport(tester, viewport.size);
          Get.put<ChatController>(_FakeChatController());
          Get.put<UserDashboardController>(
            _FakeUserDashboardController(transparentAvatar),
          );

          await tester.pumpWidget(_buildHarness(const UserDashboard()));
          await _pumpSmokeFrame(tester);

          expect(find.byType(UserDashboard), findsOneWidget);
          _expectNoFlutterErrors(tester);
        },
      );

      testWidgets(
        'UserDashboard selected page renders without layout errors on ${viewport.label}',
        (tester) async {
          await _setViewport(tester, viewport.size);
          Get.put<ChatController>(_FakeChatController());
          Get.put<UserDashboardController>(
            _FakeUserDashboardController(
              transparentAvatar,
              showSelectedPage: true,
            ),
          );

          await tester.pumpWidget(_buildHarness(const UserDashboard()));
          await _pumpSmokeFrame(tester);

          expect(find.byType(UserDashboard), findsOneWidget);
          expect(find.byType(_SelectedViewportPage), findsOneWidget);
          _expectNoFlutterErrors(tester);
        },
      );

      testWidgets(
        'AdminDashboardScreen home renders without layout errors on ${viewport.label}',
        (tester) async {
          await _setViewport(tester, viewport.size);
          Get.put<ChatController>(_FakeChatController());
          Get.put<DashboardController>(
            _FakeAdminDashboardController(transparentAvatar),
          );

          await tester.pumpWidget(_buildHarness(const AdminDashboardScreen()));
          await _pumpSmokeFrame(tester);

          expect(find.byType(AdminDashboardScreen), findsOneWidget);
          _expectNoFlutterErrors(tester);
        },
      );

      testWidgets(
        'AdminDashboardScreen selected page renders without layout errors on ${viewport.label}',
        (tester) async {
          await _setViewport(tester, viewport.size);
          Get.put<ChatController>(_FakeChatController());
          Get.put<DashboardController>(
            _FakeAdminDashboardController(
              transparentAvatar,
              showSelectedPage: true,
            ),
          );

          await tester.pumpWidget(_buildHarness(const AdminDashboardScreen()));
          await _pumpSmokeFrame(tester);

          expect(find.byType(AdminDashboardScreen), findsOneWidget);
          expect(find.byType(_SelectedViewportPage), findsOneWidget);
          _expectNoFlutterErrors(tester);
        },
      );

      testWidgets(
        'ManagerDashboardScreen home renders without layout errors on ${viewport.label}',
        (tester) async {
          await _setViewport(tester, viewport.size);
          Get.put<ChatController>(_FakeChatController());
          Get.put<DashboardController>(
            _FakeAdminDashboardController(
              transparentAvatar,
              roles: const ['TRAFFIC_POLICE'],
            ),
          );

          await tester
              .pumpWidget(_buildHarness(const ManagerDashboardScreen()));
          await _pumpSmokeFrame(tester);

          expect(find.byType(ManagerDashboardScreen), findsOneWidget);
          _expectNoFlutterErrors(tester);
        },
      );

      testWidgets(
        'ManagerDashboardScreen selected page renders without layout errors on ${viewport.label}',
        (tester) async {
          await _setViewport(tester, viewport.size);
          Get.put<ChatController>(_FakeChatController());
          Get.put<DashboardController>(
            _FakeAdminDashboardController(
              transparentAvatar,
              showSelectedPage: true,
              roles: const ['TRAFFIC_POLICE'],
            ),
          );

          await tester
              .pumpWidget(_buildHarness(const ManagerDashboardScreen()));
          await _pumpSmokeFrame(tester);

          expect(find.byType(ManagerDashboardScreen), findsOneWidget);
          expect(find.byType(_SelectedViewportPage), findsOneWidget);
          _expectNoFlutterErrors(tester);
        },
      );

      testWidgets(
        'BusinessProgressPage renders without layout errors on ${viewport.label}',
        (tester) async {
          await _setViewport(tester, viewport.size);
          Get.put<UserDashboardController>(
            _FakeUserDashboardController(transparentAvatar),
          );

          await tester.pumpWidget(_buildHarness(const BusinessProgressPage()));
          await _pumpSmokeFrame(tester);

          expect(find.byType(BusinessProgressPage), findsOneWidget);
          _expectNoFlutterErrors(tester);
        },
      );

      testWidgets(
        'OnlineProcessingProgress renders without layout errors on ${viewport.label}',
        (tester) async {
          await _setViewport(tester, viewport.size);
          Get.put<UserDashboardController>(
            _FakeUserDashboardController(transparentAvatar),
          );
          Get.put<ProgressController>(_FakeProgressController());

          await tester.pumpWidget(
            _buildHarness(const OnlineProcessingProgress()),
          );
          await _pumpSmokeFrame(tester);

          expect(find.byType(OnlineProcessingProgress), findsOneWidget);
          _expectNoFlutterErrors(tester);
        },
      );

      testWidgets(
        'AdminBusinessProcessing renders without layout errors on ${viewport.label}',
        (tester) async {
          await _setViewport(tester, viewport.size);
          SharedPreferences.setMockInitialValues({
            'app.languageCode': 'zh',
            'app.countryCode': 'CN',
            'isDarkMode': false,
            'userRoles': ['ADMIN'],
          });
          Get.put<DashboardController>(
            _FakeAdminDashboardController(transparentAvatar),
          );

          await tester.pumpWidget(
            _buildHarness(const AdminBusinessProcessing()),
          );
          await _pumpSmokeFrame(tester);

          expect(find.byType(AdminBusinessProcessing), findsOneWidget);
          _expectNoFlutterErrors(tester);
        },
      );

      testWidgets(
        'AdminSettingPage renders without layout errors on ${viewport.label}',
        (tester) async {
          await _setViewport(tester, viewport.size);
          Get.put<DashboardController>(
            _FakeAdminDashboardController(transparentAvatar),
          );

          await tester.pumpWidget(_buildHarness(const AdminSettingPage()));
          await _pumpSmokeFrame(tester);

          expect(find.byType(AdminSettingPage), findsOneWidget);
          _expectNoFlutterErrors(tester);
        },
      );

      testWidgets(
        'ProgressManagementPage renders without layout errors on ${viewport.label}',
        (tester) async {
          await _setViewport(tester, viewport.size);
          Get.put<DashboardController>(
            _FakeAdminDashboardController(transparentAvatar),
          );
          Get.put<ProgressController>(
            _FakeProgressController(hasAdminAccess: true),
          );

          await tester
              .pumpWidget(_buildHarness(const ProgressManagementPage()));
          await _pumpSmokeFrame(tester);

          expect(find.byType(ProgressManagementPage), findsOneWidget);
          _expectNoFlutterErrors(tester);
        },
      );

      testWidgets(
        'LogManagement renders without layout errors on ${viewport.label}',
        (tester) async {
          await _setViewport(tester, viewport.size);
          Get.put<DashboardController>(
            _FakeAdminDashboardController(transparentAvatar),
          );

          await tester.pumpWidget(_buildHarness(const LogManagement()));
          await _pumpSmokeFrame(tester);

          expect(find.byType(LogManagement), findsOneWidget);
          _expectNoFlutterErrors(tester);
        },
      );

      testWidgets(
        'UserManagementPage unauthorized state renders without layout errors on ${viewport.label}',
        (tester) async {
          await _setViewport(tester, viewport.size);
          Get.put<DashboardController>(
            _FakeAdminDashboardController(transparentAvatar),
          );

          await tester.pumpWidget(_buildHarness(const UserManagementPage()));
          await _pumpSmokeFrame(tester);

          expect(find.byType(UserManagementPage), findsOneWidget);
          _expectNoFlutterErrors(tester);
        },
      );

      testWidgets(
        'ManagerBusinessProcessing renders without layout errors on ${viewport.label}',
        (tester) async {
          await _setViewport(tester, viewport.size);
          SharedPreferences.setMockInitialValues({
            'app.languageCode': 'zh',
            'app.countryCode': 'CN',
            'isDarkMode': false,
            'userRoles': ['TRAFFIC_POLICE'],
          });
          Get.put<DashboardController>(
            _FakeAdminDashboardController(
              transparentAvatar,
              roles: const ['TRAFFIC_POLICE'],
            ),
          );

          await tester.pumpWidget(
            _buildHarness(const ManagerBusinessProcessing()),
          );
          await _pumpSmokeFrame(tester);

          expect(find.byType(ManagerBusinessProcessing), findsOneWidget);
          _expectNoFlutterErrors(tester);
        },
      );

      testWidgets(
        'ManagerSetting renders without layout errors on ${viewport.label}',
        (tester) async {
          await _setViewport(tester, viewport.size);
          Get.put<DashboardController>(
            _FakeAdminDashboardController(
              transparentAvatar,
              roles: const ['TRAFFIC_POLICE'],
            ),
          );

          await tester.pumpWidget(_buildHarness(const ManagerSetting()));
          await _pumpSmokeFrame(tester);

          expect(find.byType(ManagerSetting), findsOneWidget);
          _expectNoFlutterErrors(tester);
        },
      );

      testWidgets(
        'ManagerPersonalPage renders without layout errors on ${viewport.label}',
        (tester) async {
          await _setViewport(tester, viewport.size);
          Get.put<DashboardController>(
            _FakeAdminDashboardController(
              transparentAvatar,
              roles: const ['TRAFFIC_POLICE'],
            ),
          );

          await tester.pumpWidget(_buildHarness(const ManagerPersonalPage()));
          await _pumpSmokeFrame(tester);

          expect(find.byType(ManagerPersonalPage), findsOneWidget);
          _expectNoFlutterErrors(tester);
        },
      );

      testWidgets(
        'NewsPageLayout header adapts without layout errors on ${viewport.label}',
        (tester) async {
          await _setViewport(tester, viewport.size);

          await tester.pumpWidget(
            _buildHarness(
              NewsPageLayout(
                title: 'Traffic processing updates and evidence guide',
                trailing: const [
                  Icon(Icons.share_outlined, color: Colors.white),
                  Icon(Icons.bookmark_outline, color: Colors.white),
                ],
                contentBuilder: _buildNewsViewportBody,
              ),
            ),
          );
          await _pumpSmokeFrame(tester);

          expect(find.byType(NewsPageLayout), findsOneWidget);
          _expectNoFlutterErrors(tester);
        },
      );
    }
  });
}

Widget _buildHarness(Widget child) {
  return GetMaterialApp(
    debugShowCheckedModeBanner: false,
    translations: AppTranslations(),
    locale: const Locale('zh', 'CN'),
    fallbackLocale: AppTranslations.fallbackLocale,
    theme: AppTheme.basicLight,
    home: child,
  );
}

Future<void> _setViewport(WidgetTester tester, Size size) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = size;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

Future<void> _pumpSmokeFrame(WidgetTester tester) async {
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 250));
  await tester.pump(const Duration(milliseconds: 350));
}

void _expectNoFlutterErrors(WidgetTester tester) {
  final errors = <Object>[];
  Object? exception;
  while ((exception = tester.takeException()) != null) {
    errors.add(exception!);
  }
  expect(errors, isEmpty);
}

class _ViewportBody extends StatelessWidget {
  const _ViewportBody();

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: List.generate(
          8,
          (index) => Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: Text(
              'Section ${index + 1}',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
          ),
        ),
      ),
    );
  }
}

Widget _buildNewsViewportBody(BuildContext context, ThemeData theme) {
  return Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: List.generate(
      6,
      (index) => Padding(
        padding: const EdgeInsets.only(bottom: 16),
        child: Text(
          'News content section ${index + 1}',
          style: theme.textTheme.titleMedium,
        ),
      ),
    ),
  );
}

class _ViewportChatPanel extends StatelessWidget {
  const _ViewportChatPanel();

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(color: Color(0xFF10151C)),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: List.generate(
          6,
          (index) => Container(
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.06),
              borderRadius: BorderRadius.circular(18),
            ),
            child: Text(
              'Chat block ${index + 1}',
              style: const TextStyle(color: Colors.white),
            ),
          ),
        ),
      ),
    );
  }
}

class _SelectedViewportPage extends StatelessWidget {
  const _SelectedViewportPage();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(24),
      children: List.generate(
        12,
        (index) => Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surfaceContainerLowest,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: Theme.of(context)
                  .colorScheme
                  .outlineVariant
                  .withValues(alpha: 0.4),
            ),
          ),
          child: Text('Selected content row ${index + 1}'),
        ),
      ),
    );
  }
}

class _FakeChatController extends ChatController {
  @override
  void onInit() {}
}

class _FakeUserDashboardController extends UserDashboardController {
  _FakeUserDashboardController(
    ImageProvider avatar, {
    this.showSelectedPage = false,
  }) {
    currentUser.value = Profile(
      photo: avatar,
      name: 'Driver User',
      email: 'driver@example.com',
    );
    currentDriverName.value = 'Driver User';
    currentEmail.value = 'driver@example.com';
    currentTheme.value = 'Light';
    currentBodyTheme.value = AppTheme.basicLight;
    driverLicenseNumber.value = '1234567890';
    idCardNumber.value = 'ID-320101';
    isLoadingUser.value = false;
    pageResolver = (_) => const SizedBox.shrink();
    if (showSelectedPage) {
      isShowingSidebarContent.value = true;
      selectedPage.value = const _SelectedViewportPage();
    }
  }

  final bool showSelectedPage;

  @override
  void onInit() {}

  @override
  void onReady() {}
}

class _FakeProgressController extends ProgressController {
  _FakeProgressController({this.hasAdminAccess = false}) {
    progressItems.assignAll(_sampleProgressItems());
    filteredItems.assignAll(progressItems);
    isLoading.value = false;
    errorMessage.value = '';
  }

  final bool hasAdminAccess;

  @override
  void onInit() {}

  @override
  bool get isAdmin => hasAdminAccess;

  @override
  Future<void> fetchProgress() async {
    isLoading.value = false;
    errorMessage.value = '';
    filteredItems.assignAll(progressItems);
  }

  @override
  Future<void> fetchRefundAudits() async {
    isLoading.value = false;
    errorMessage.value = '';
  }

  List<ProgressItem> _sampleProgressItems() {
    return [
      ProgressItem(
        id: 1,
        title: 'Appeal review',
        status: progressStatusPending,
        submitTime: DateTime(2026, 1, 8, 9, 30),
        username: 'operator',
        businessType: 'APPEAL',
        appealId: 42,
      ),
      ProgressItem(
        id: 2,
        title: 'Fine payment',
        status: progressStatusCompleted,
        submitTime: DateTime(2026, 1, 9, 10, 15),
        username: 'driver',
        businessType: 'FINE',
        fineId: 73,
      ),
    ];
  }
}

class _FakeAdminDashboardController extends DashboardController {
  _FakeAdminDashboardController(
    ImageProvider avatar, {
    this.showSelectedPage = false,
    this.roles = const ['ADMIN'],
  }) {
    currentUser.value = Profile(
      photo: avatar,
      name: 'Admin User',
      email: 'admin@example.com',
    );
    currentDriverName.value = 'Admin User';
    currentEmail.value = 'admin@example.com';
    currentTheme.value = 'Light';
    currentBodyTheme.value = AppTheme.basicLight;
    currentRoles.assignAll(roles);
    pageResolver = (_) => const SizedBox.shrink();
    if (showSelectedPage) {
      isShowingSidebarContent.value = true;
      selectedPage.value = const _SelectedViewportPage();
    }
  }

  final bool showSelectedPage;
  final List<String> roles;

  @override
  void onInit() {}

  @override
  Future<void> refreshRoleState() async {
    currentRoles.assignAll(roles);
  }
}
