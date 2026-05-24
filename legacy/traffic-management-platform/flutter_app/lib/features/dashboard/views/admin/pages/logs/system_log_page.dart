import 'dart:developer' as developer;

import 'package:final_assignment_front/config/routes/app_routes.dart';
import 'package:final_assignment_front/features/api/system_logs_controller_api.dart';
import 'package:final_assignment_front/features/dashboard/controllers/admin_dashboard_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/dashboard_page_template.dart';
import 'package:final_assignment_front/features/model/login_log.dart';
import 'package:final_assignment_front/features/model/operation_log.dart';
import 'package:final_assignment_front/i18n/system_log_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:final_assignment_front/utils/helpers/role_utils.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:final_assignment_front/utils/services/session_helper.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:jwt_decoder/jwt_decoder.dart';

class SystemLogPage extends StatefulWidget {
  const SystemLogPage({super.key});

  @override
  State<SystemLogPage> createState() => _SystemLogPageState();
}

class _SystemLogPageState extends State<SystemLogPage> {
  final SystemLogsControllerApi logApi = SystemLogsControllerApi();
  final ScrollController _scrollController = ScrollController();
  final DashboardController controller = Get.find<DashboardController>();
  final SessionHelper _sessionHelper = SessionHelper();

  Map<String, dynamic> _overviewData = {};
  List<LoginLog> _recentLoginLogs = [];
  List<OperationLog> _recentOperationLogs = [];
  bool _isLoading = false;
  bool _isAdmin = false;
  String _errorMessage = '';

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _setStateSafely(VoidCallback update) {
    if (!mounted) return;
    setState(update);
  }

  void _redirectToLogin() {
    if (!mounted) return;
    Get.offAllNamed(Routes.login);
  }

  Future<bool> _validateJwtToken() async {
    String? jwtToken = (await AuthTokenStore.instance.getJwtToken());
    if (jwtToken == null || jwtToken.isEmpty) {
      _setStateSafely(() => _errorMessage = 'systemLog.error.unauthorized'.tr);
      return false;
    }
    try {
      JwtDecoder.decode(jwtToken);
      if (JwtDecoder.isExpired(jwtToken)) {
        jwtToken = await _refreshJwtToken();
        if (!mounted) return false;
        if (jwtToken == null || JwtDecoder.isExpired(jwtToken)) {
          _setStateSafely(() => _errorMessage = 'systemLog.error.expired'.tr);
          return false;
        }
        await AuthTokenStore.instance.setJwtToken(jwtToken);
        await logApi.initializeWithJwt();
        if (!mounted) return false;
      }
      return true;
    } catch (_) {
      _setStateSafely(() => _errorMessage = 'systemLog.error.invalidLogin'.tr);
      return false;
    }
  }

  Future<String?> _refreshJwtToken() async {
    return await _sessionHelper.refreshJwtToken();
  }

  Future<void> _initialize() async {
    _setStateSafely(() {
      _isLoading = true;
      _errorMessage = '';
    });
    try {
      final isValid = await _validateJwtToken();
      if (!mounted) return;
      if (!isValid) {
        _redirectToLogin();
        return;
      }
      await logApi.initializeWithJwt();
      if (!mounted) return;
      await _checkUserRole();
      if (!mounted) return;
      if (_isAdmin) {
        await _fetchSystemLogData(showLoader: false);
      } else {
        _setStateSafely(() => _errorMessage = 'systemLog.error.adminOnly'.tr);
      }
    } catch (e) {
      _setStateSafely(() => _errorMessage = 'systemLog.error.initFailed'
          .trParams({'error': formatSystemLogError(e)}));
    } finally {
      _setStateSafely(() => _isLoading = false);
    }
  }

  Future<void> _checkUserRole() async {
    try {
      final isValid = await _validateJwtToken();
      if (!mounted) return;
      if (!isValid) {
        _redirectToLogin();
        return;
      }
      final roles = await _sessionHelper.fetchCurrentRoles();
      if (!mounted) return;
      _setStateSafely(() => _isAdmin = hasAnyRole(roles, const [
            'SUPER_ADMIN',
            'ADMIN',
          ]));
      if (!_isAdmin) {
        _setStateSafely(() => _errorMessage = 'systemLog.error.adminOnly'.tr);
      }
    } catch (e) {
      _setStateSafely(() => _errorMessage = 'systemLog.error.roleCheckFailed'
          .trParams({'error': formatSystemLogError(e)}));
      developer.log('Error checking user role: $e',
          stackTrace: StackTrace.current);
    }
  }

  Future<void> _fetchSystemLogData({bool showLoader = true}) async {
    if (!_isAdmin) return;
    if (showLoader) {
      _setStateSafely(() {
        _isLoading = true;
        _errorMessage = '';
      });
    }
    try {
      final isValid = await _validateJwtToken();
      if (!mounted) return;
      if (!isValid) {
        _redirectToLogin();
        return;
      }
      await logApi.initializeWithJwt();
      if (!mounted) return;
      final overview = await logApi.apiSystemLogsOverviewGet();
      if (!mounted) return;
      final loginLogs = await logApi.apiSystemLogsLoginRecentGet(limit: 20);
      if (!mounted) return;
      final operationLogs =
          await logApi.apiSystemLogsOperationRecentGet(limit: 20);
      if (!mounted) return;
      _setStateSafely(() {
        _overviewData = overview;
        _recentLoginLogs = loginLogs;
        _recentOperationLogs = operationLogs;
        _errorMessage = '';
      });
    } catch (e) {
      developer.log('Failed to fetch system logs: $e',
          stackTrace: StackTrace.current);
      if (e is ApiException && e.code == 403) {
        _setStateSafely(
            () => _errorMessage = 'systemLog.error.unauthorized'.tr);
        _redirectToLogin();
      } else {
        _setStateSafely(() {
          _errorMessage = 'systemLog.error.loadFailed'
              .trParams({'error': formatSystemLogError(e)});
        });
      }
    } finally {
      if (showLoader) {
        _setStateSafely(() => _isLoading = false);
      }
    }
  }

  Future<void> _handleRefresh() async {
    await _fetchSystemLogData(showLoader: false);
  }

  int _recentLoginFailures() {
    return _recentLoginLogs
        .where((log) =>
            localizeSystemLogResult(
                  log.loginResult,
                  emptyKey: 'common.unknown',
                ) !=
                'common.success'.tr &&
            (log.loginResult ?? '').trim().isNotEmpty)
        .length;
  }

  int _recentOperationAlerts() {
    return _recentOperationLogs
        .where((log) =>
            localizeSystemLogResult(
                  log.operationResult,
                  emptyKey: 'common.unknown',
                ) !=
                'common.success'.tr &&
            (log.operationResult ?? '').trim().isNotEmpty)
        .length;
  }

  Widget _buildHeroSection(ThemeData themeData) {
    final onHero = themeData.brightness == Brightness.dark
        ? Colors.white
        : const Color(0xFF102530);
    final muted = onHero.withValues(alpha: 0.72);
    final overviewCount = _overviewData.length;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: themeData.brightness == Brightness.dark
              ? const [
                  Color(0xFF07141D),
                  Color(0xFF0B202B),
                  Color(0xFF123848),
                ]
              : const [
                  Color(0xFFF5F9FC),
                  Color(0xFFE9F1F8),
                  Color(0xFFDCE8F0),
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
                  _SystemHeroBadge(
                    label: 'systemLog.workspace.eyebrow'.tr.toUpperCase(),
                    foregroundColor: onHero,
                  ),
                  _SystemHeroBadge(
                    label: 'common.adminConsole'.tr.toUpperCase(),
                    foregroundColor: Colors.white,
                    backgroundColor: const Color(0xFF2F6FD6),
                    filled: true,
                  ),
                ],
              ),
              const SizedBox(height: 18),
              Text(
                'systemLog.workspace.title'.tr,
                style: themeData.textTheme.headlineMedium?.copyWith(
                  color: onHero,
                  fontWeight: FontWeight.w800,
                  height: 1.05,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'systemLog.workspace.subtitle'.tr,
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
                  _SystemInlineSignal(
                    icon: Icons.login_rounded,
                    label: 'systemLog.workspace.signal.login'.trParams({
                      'count': '${_recentLoginLogs.length}',
                    }),
                    color: onHero,
                  ),
                  _SystemInlineSignal(
                    icon: Icons.fact_check_outlined,
                    label: 'systemLog.workspace.signal.operation'.trParams({
                      'count': '${_recentOperationLogs.length}',
                    }),
                    color: onHero,
                  ),
                  _SystemInlineSignal(
                    icon: Icons.refresh_rounded,
                    label: 'systemLog.workspace.signal.refresh'.tr,
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
              _SystemMetricTile(
                label: 'systemLog.workspace.metric.overview'.tr,
                value: '$overviewCount',
              ),
              _SystemMetricTile(
                label: 'systemLog.workspace.metric.login'.tr,
                value: '${_recentLoginLogs.length}',
              ),
              _SystemMetricTile(
                label: 'systemLog.workspace.metric.operation'.tr,
                value: '${_recentOperationLogs.length}',
              ),
              _SystemMetricTile(
                label: 'systemLog.workspace.metric.alert'.tr,
                value: '${_recentLoginFailures() + _recentOperationAlerts()}',
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

  Widget _buildWarningBanner(ThemeData themeData) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: themeData.colorScheme.errorContainer,
        borderRadius: BorderRadius.circular(22),
      ),
      child: Row(
        children: [
          Icon(
            CupertinoIcons.exclamationmark_triangle_fill,
            color: themeData.colorScheme.onErrorContainer,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              _errorMessage,
              style: themeData.textTheme.bodyMedium?.copyWith(
                color: themeData.colorScheme.onErrorContainer,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
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

  Widget _buildSurfacePanel(
    ThemeData themeData, {
    required Widget child,
  }) {
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
      child: child,
    );
  }

  Widget _buildEmptySection(ThemeData themeData, String message) {
    return Row(
      children: [
        Icon(
          CupertinoIcons.info,
          color: themeData.colorScheme.onSurfaceVariant,
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            message,
            style: themeData.textTheme.bodyMedium?.copyWith(
              color: themeData.colorScheme.onSurfaceVariant,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildOverviewSection(ThemeData themeData) {
    return _buildSurfacePanel(
      themeData,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSectionHeading(
            themeData,
            eyebrow: 'systemLog.section.overview'.tr,
            title: 'systemLog.section.overview'.tr,
            description: 'systemLog.workspace.overviewBody'.tr,
          ),
          const SizedBox(height: 18),
          if (_overviewData.isEmpty)
            _buildEmptySection(themeData, 'systemLog.empty.overview'.tr)
          else
            Wrap(
              spacing: 14,
              runSpacing: 14,
              children: _overviewData.entries.map((entry) {
                final value = entry.value;
                return _OverviewSignalTile(
                  label: formatSystemLogOverviewLabel(entry.key),
                  value: value?.toString() ?? '0',
                  themeData: themeData,
                );
              }).toList(),
            ),
        ],
      ),
    );
  }

  Widget _buildLoginLogsSection(ThemeData themeData) {
    return _buildSurfacePanel(
      themeData,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSectionHeading(
            themeData,
            eyebrow: 'systemLog.workspace.loginEyebrow'.tr,
            title: 'systemLog.section.recentLogin'.tr,
            description: 'systemLog.workspace.loginBody'.tr,
          ),
          const SizedBox(height: 18),
          if (_recentLoginLogs.isEmpty)
            _buildEmptySection(themeData, 'systemLog.empty.login'.tr)
          else
            ..._recentLoginLogs.asMap().entries.map((entry) {
              return Padding(
                padding: EdgeInsets.only(
                  bottom: entry.key == _recentLoginLogs.length - 1 ? 0 : 14,
                ),
                child: _buildLoginLogTile(entry.value, themeData),
              );
            }),
        ],
      ),
    );
  }

  Widget _buildLoginLogTile(LoginLog log, ThemeData themeData) {
    final result = localizeSystemLogResult(
      log.loginResult,
      emptyKey: 'common.unknown',
    );
    final isSuccess = result == 'common.success'.tr;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: themeData.colorScheme.surface,
        borderRadius: BorderRadius.circular(22),
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
                      log.username ?? 'systemLog.value.unknownUser'.tr,
                      style: themeData.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: [
                        _LogStatusBadge(
                          label: result,
                          color: isSuccess
                              ? const Color(0xFF1F9D68)
                              : const Color(0xFFC45A4E),
                        ),
                        _LogMetaChip(
                          icon: Icons.schedule_rounded,
                          label: formatSystemLogDateTime(log.loginTime),
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
              _LogMetaChip(
                icon: Icons.language_rounded,
                label: 'systemLog.detail.loginIp'
                    .trParams({'value': log.loginIp ?? 'common.unknown'.tr}),
              ),
              _LogMetaChip(
                icon: Icons.devices_outlined,
                label: 'systemLog.detail.loginDevice'
                    .trParams({'value': buildSystemLogDeviceInfo(log)}),
              ),
              if (log.loginLocation != null && log.loginLocation!.isNotEmpty)
                _LogMetaChip(
                  icon: Icons.place_outlined,
                  label: 'systemLog.detail.loginLocation'
                      .trParams({'value': log.loginLocation!}),
                ),
            ],
          ),
          if (log.remarks != null && log.remarks!.isNotEmpty) ...[
            const SizedBox(height: 14),
            Text(
              'systemLog.detail.remarks'.trParams({'value': log.remarks!}),
              style: themeData.textTheme.bodySmall?.copyWith(
                color: themeData.colorScheme.onSurfaceVariant,
                height: 1.45,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildOperationLogsSection(ThemeData themeData) {
    return _buildSurfacePanel(
      themeData,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSectionHeading(
            themeData,
            eyebrow: 'systemLog.workspace.operationEyebrow'.tr,
            title: 'systemLog.section.recentOperation'.tr,
            description: 'systemLog.workspace.operationBody'.tr,
          ),
          const SizedBox(height: 18),
          if (_recentOperationLogs.isEmpty)
            _buildEmptySection(themeData, 'systemLog.empty.operation'.tr)
          else
            ..._recentOperationLogs.asMap().entries.map((entry) {
              return Padding(
                padding: EdgeInsets.only(
                  bottom: entry.key == _recentOperationLogs.length - 1 ? 0 : 14,
                ),
                child: _buildOperationLogTile(entry.value, themeData),
              );
            }),
        ],
      ),
    );
  }

  Widget _buildOperationLogTile(OperationLog log, ThemeData themeData) {
    final userLabel = log.username ??
        log.realName ??
        log.userId?.toString() ??
        'systemLog.value.unknownUser'.tr;
    final result = localizeSystemLogResult(
      log.operationResult,
      emptyKey: 'common.unknown',
    );
    final isSuccess = result == 'common.success'.tr;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: themeData.colorScheme.surface,
        borderRadius: BorderRadius.circular(22),
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
                      log.operationModule ??
                          log.operationFunction ??
                          'systemLog.value.unknownModule'.tr,
                      style: themeData.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: [
                        _LogStatusBadge(
                          label: result,
                          color: isSuccess
                              ? const Color(0xFF1F9D68)
                              : const Color(0xFFC45A4E),
                        ),
                        _LogMetaChip(
                          icon: Icons.schedule_rounded,
                          label: formatSystemLogDateTime(log.operationTime),
                        ),
                        _LogMetaChip(
                          icon: Icons.person_outline_rounded,
                          label: 'systemLog.detail.user'.trParams({
                            'value': userLabel,
                          }),
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
              _LogMetaChip(
                icon: Icons.category_outlined,
                label: 'systemLog.detail.operationType'.trParams({
                  'value': log.operationType ?? 'common.unknown'.tr,
                }),
              ),
              _LogMetaChip(
                icon: Icons.language_rounded,
                label: 'systemLog.detail.requestIp'.trParams({
                  'value': log.requestIp ?? 'common.unknown'.tr,
                }),
              ),
            ],
          ),
          if (log.operationContent != null &&
              log.operationContent!.isNotEmpty) ...[
            const SizedBox(height: 14),
            Text(
              'systemLog.detail.operationContent'
                  .trParams({'value': log.operationContent!}),
              style: themeData.textTheme.bodySmall?.copyWith(
                color: themeData.colorScheme.onSurfaceVariant,
                height: 1.45,
              ),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
          ],
          if (log.remarks != null && log.remarks!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              'systemLog.detail.remarks'.trParams({'value': log.remarks!}),
              style: themeData.textTheme.bodySmall?.copyWith(
                color: themeData.colorScheme.onSurfaceVariant,
                height: 1.45,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildErrorView(ThemeData themeData) {
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
            Icon(
              CupertinoIcons.exclamationmark_triangle,
              color: themeData.colorScheme.error,
              size: 48,
            ),
            const SizedBox(height: 16),
            Text(
              'systemLog.workspace.errorTitle'.tr,
              style: themeData.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w700,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 10),
            Text(
              _errorMessage,
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
                  onPressed: _handleRefresh,
                  icon: const Icon(Icons.refresh_rounded),
                  label: Text('page.refreshList'.tr),
                ),
                FilledButton.icon(
                  onPressed: () => Get.offAllNamed(Routes.login),
                  icon: const Icon(Icons.login_rounded),
                  label: Text('systemLog.action.relogin'.tr),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  bool _hasData() {
    return _overviewData.isNotEmpty ||
        _recentLoginLogs.isNotEmpty ||
        _recentOperationLogs.isNotEmpty;
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final themeData = controller.currentBodyTheme.value;
      final showBlockingError = _errorMessage.isNotEmpty && !_hasData();
      return DashboardPageTemplate(
        theme: themeData,
        title: 'systemLog.page.title'.tr,
        pageType: DashboardPageType.admin,
        bodyIsScrollable: true,
        padding: EdgeInsets.zero,
        onRefresh: _fetchSystemLogData,
        onThemeToggle: controller.toggleBodyTheme,
        body: _isLoading
            ? Center(
                child: CupertinoActivityIndicator(
                  color: themeData.colorScheme.primary,
                  radius: 16.0,
                ),
              )
            : showBlockingError
                ? _buildErrorView(themeData)
                : RefreshIndicator(
                    onRefresh: _handleRefresh,
                    color: themeData.colorScheme.primary,
                    backgroundColor: themeData.colorScheme.surfaceContainer,
                    child: CupertinoScrollbar(
                      controller: _scrollController,
                      thumbVisibility: true,
                      thickness: 6.0,
                      thicknessWhileDragging: 10.0,
                      child: ListView(
                        controller: _scrollController,
                        padding: const EdgeInsets.all(20),
                        children: [
                          _buildHeroSection(themeData),
                          const SizedBox(height: 24),
                          if (_errorMessage.isNotEmpty && _hasData()) ...[
                            _buildWarningBanner(themeData),
                            const SizedBox(height: 24),
                          ],
                          _buildOverviewSection(themeData),
                          const SizedBox(height: 24),
                          LayoutBuilder(
                            builder: (context, constraints) {
                              final stacked = constraints.maxWidth < 1040;
                              if (stacked) {
                                return Column(
                                  children: [
                                    _buildLoginLogsSection(themeData),
                                    const SizedBox(height: 24),
                                    _buildOperationLogsSection(themeData),
                                  ],
                                );
                              }
                              return Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Expanded(
                                    child: _buildLoginLogsSection(themeData),
                                  ),
                                  const SizedBox(width: 24),
                                  Expanded(
                                    child:
                                        _buildOperationLogsSection(themeData),
                                  ),
                                ],
                              );
                            },
                          ),
                        ],
                      ),
                    ),
                  ),
      );
    });
  }
}

class _SystemHeroBadge extends StatelessWidget {
  const _SystemHeroBadge({
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

class _SystemInlineSignal extends StatelessWidget {
  const _SystemInlineSignal({
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

class _SystemMetricTile extends StatelessWidget {
  const _SystemMetricTile({
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

class _OverviewSignalTile extends StatelessWidget {
  const _OverviewSignalTile({
    required this.label,
    required this.value,
    required this.themeData,
  });

  final String label;
  final String value;
  final ThemeData themeData;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 160, maxWidth: 220),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: themeData.colorScheme.surface,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            value,
            style: themeData.textTheme.titleLarge?.copyWith(
              color: themeData.colorScheme.primary,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            label,
            style: themeData.textTheme.bodySmall?.copyWith(
              color: themeData.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}

class _LogStatusBadge extends StatelessWidget {
  const _LogStatusBadge({
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

class _LogMetaChip extends StatelessWidget {
  const _LogMetaChip({
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
