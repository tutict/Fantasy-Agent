// ignore_for_file: use_build_context_synchronously
import 'dart:async';
import 'dart:developer' as developer;

import 'package:final_assignment_front/config/routes/app_routes.dart';
import 'package:final_assignment_front/features/api/operation_log_controller_api.dart';
import 'package:final_assignment_front/features/dashboard/controllers/admin_dashboard_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/dashboard_page_template.dart';
import 'package:final_assignment_front/features/model/operation_log.dart';
import 'package:final_assignment_front/i18n/log_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:final_assignment_front/utils/helpers/role_utils.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:jwt_decoder/jwt_decoder.dart';

class OperationLogPage extends StatefulWidget {
  const OperationLogPage({super.key});

  @override
  State<OperationLogPage> createState() => _OperationLogPageState();
}

class _OperationLogPageState extends State<OperationLogPage> {
  final OperationLogControllerApi logApi = OperationLogControllerApi();
  final TextEditingController _searchController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final DashboardController controller = Get.find<DashboardController>();
  final List<OperationLog> _logs = [];
  List<OperationLog> _filteredLogs = [];
  String _searchType = kOperationLogSearchTypeUserId;
  String _activeQuery = '';
  DateTime? _startTime;
  DateTime? _endTime;
  int _currentPage = 1;
  final int _pageSize = 20;
  bool _hasMore = true;
  bool _isLoading = false;
  bool _isAdmin = false;
  String _errorMessage = '';
  Timer? _searchDebounce;

  @override
  void initState() {
    super.initState();
    _initialize();
    _scrollController.addListener(() {
      if (_scrollController.position.pixels >=
              _scrollController.position.maxScrollExtent - 200 &&
          _hasMore &&
          !_isLoading) {
        _loadMoreLogs();
      }
    });
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();
    _searchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<bool> _validateJwtToken() async {
    final jwtToken = await AuthTokenStore.instance.getJwtToken();
    if (jwtToken == null || jwtToken.isEmpty) {
      setState(() => _errorMessage = 'operationLog.error.unauthorized'.tr);
      return false;
    }
    try {
      if (JwtDecoder.isExpired(jwtToken)) {
        setState(() => _errorMessage = 'operationLog.error.expired'.tr);
        return false;
      }
      await logApi.initializeWithJwt();
      return true;
    } catch (e) {
      setState(() => _errorMessage = 'operationLog.error.invalidLogin'.tr);
      return false;
    }
  }

  Future<void> _initialize() async {
    setState(() => _isLoading = true);
    try {
      if (!await _validateJwtToken()) {
        Get.offAllNamed(Routes.login);
        return;
      }
      await _checkUserRole();
      if (_isAdmin) {
        await _fetchLogs(reset: true);
      } else {
        setState(() => _errorMessage = 'operationLog.error.adminOnly'.tr);
      }
    } catch (e) {
      setState(() => _errorMessage = 'operationLog.error.initFailed'
          .trParams({'error': formatOperationLogError(e)}));
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _checkUserRole() async {
    try {
      if (!await _validateJwtToken()) {
        Get.offAllNamed(Routes.login);
        return;
      }
      final jwtToken = (await AuthTokenStore.instance.getJwtToken())!;
      final decodedToken = JwtDecoder.decode(jwtToken);
      final roles = decodedToken['roles'];
      setState(() => _isAdmin = hasAnyRole(roles, const [
            'SUPER_ADMIN',
            'ADMIN',
          ]));
      if (!_isAdmin) {
        setState(() => _errorMessage = 'operationLog.error.adminOnly'.tr);
      }
      developer.log('User roles from JWT: $roles');
    } catch (e) {
      setState(() => _errorMessage = 'operationLog.error.roleCheckFailed'
          .trParams({'error': formatOperationLogError(e)}));
      developer.log('Error checking user role: $e',
          stackTrace: StackTrace.current);
    }
  }

  Future<void> _fetchLogs({bool reset = false, String? query}) async {
    if (reset) {
      _currentPage = 1;
      _hasMore = true;
      _activeQuery = (query ?? _searchController.text).trim();
      _logs.clear();
      _filteredLogs.clear();
    }
    if (!_isAdmin || (!reset && (_isLoading || !_hasMore))) return;

    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    try {
      if (!await _validateJwtToken()) {
        Get.offAllNamed(Routes.login);
        return;
      }
      final logs = await _loadLogPage(page: _currentPage, query: _activeQuery);

      setState(() {
        _logs.addAll(logs);
        _rebuildVisibleLogs();
        _hasMore = logs.length == _pageSize;
        _currentPage++;
      });
      developer.log('Loaded logs: ${_logs.length}');
    } catch (e) {
      developer.log('Error fetching logs: $e', stackTrace: StackTrace.current);
      setState(() {
        if (e is ApiException && e.code == 404) {
          _logs.clear();
          _filteredLogs.clear();
          _errorMessage = 'operationLog.empty.filtered'.tr;
          _hasMore = false;
        } else if (e is ApiException && e.code == 403) {
          _errorMessage = 'operationLog.error.unauthorized'.tr;
          Get.offAllNamed(Routes.login);
        } else {
          _errorMessage = 'operationLog.error.loadFailed'
              .trParams({'error': formatOperationLogError(e)});
        }
      });
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<List<OperationLog>> _loadLogPage({
    required int page,
    required String query,
  }) {
    if (_searchType == kLogSearchTypeTimeRange &&
        _startTime != null &&
        _endTime != null) {
      return logApi.apiLogsOperationSearchTimeRangeGet(
        startTime: _startTime!.toIso8601String(),
        endTime: _endTime!.add(const Duration(days: 1)).toIso8601String(),
        page: page,
        size: _pageSize,
      );
    }
    if (query.isEmpty) {
      return logApi.apiLogsOperationGet(page: page, size: _pageSize);
    }
    if (_searchType == kOperationLogSearchTypeOperationResult) {
      return logApi.apiLogsOperationSearchResultGet(
        operationResult: _normalizeResultQuery(query),
        page: page,
        size: _pageSize,
      );
    }
    final userId = int.tryParse(query);
    if (userId == null) {
      return Future.value(const <OperationLog>[]);
    }
    return logApi.apiLogsOperationSearchUserUserIdGet(
      userId: userId,
      page: page,
      size: _pageSize,
    );
  }

  void _rebuildVisibleLogs() {
    _filteredLogs = List<OperationLog>.from(_logs);
    if (_filteredLogs.isEmpty) {
      _errorMessage =
          _activeQuery.isNotEmpty || (_startTime != null && _endTime != null)
              ? 'operationLog.empty.filtered'.tr
              : 'operationLog.empty.default'.tr;
    } else {
      _errorMessage = '';
    }
  }

  String _normalizeResultQuery(String query) {
    final normalized = query.trim();
    if (normalized.isEmpty) {
      return normalized;
    }
    final lowered = normalized.toLowerCase();
    final successAliases = <String>{
      'success',
      'succeeded',
      'successful',
      'ok',
      'passed',
      'common.success'.tr.toLowerCase(),
    };
    final failedAliases = <String>{
      'failed',
      'failure',
      'error',
      'errored',
      'fail',
      'common.failed'.tr.toLowerCase(),
    };
    if (successAliases.any((alias) =>
        alias.contains(lowered) || lowered.contains(alias.toLowerCase()))) {
      return 'SUCCESS';
    }
    if (failedAliases.any((alias) =>
        alias.contains(lowered) || lowered.contains(alias.toLowerCase()))) {
      return 'FAILED';
    }
    return normalized;
  }

  Future<List<String>> _fetchAutocompleteSuggestions(String prefix) async {
    if (prefix.isEmpty || _searchType == kLogSearchTypeTimeRange) {
      return [];
    }
    final normalized = prefix.toLowerCase();
    final values = _searchType == kOperationLogSearchTypeUserId
        ? _logs.map((log) => log.userId?.toString() ?? '')
        : _logs.map((log) => localizeOperationLogResult(log.operationResult));
    return values
        .where((value) => value.isNotEmpty)
        .where((value) => value.toLowerCase().contains(normalized))
        .toSet()
        .take(5)
        .toList();
  }

  Future<void> _loadMoreLogs() async {
    if (!_isLoading && _hasMore) {
      await _fetchLogs();
    }
  }

  Future<void> _refreshLogs({String? query}) async {
    _searchDebounce?.cancel();
    final effectiveQuery = (query ?? _searchController.text).trim();
    setState(() {
      _logs.clear();
      _filteredLogs.clear();
      _currentPage = 1;
      _hasMore = true;
      _isLoading = true;
      _searchController.value = TextEditingValue(
        text: effectiveQuery,
        selection: TextSelection.collapsed(offset: effectiveQuery.length),
      );
    });
    await _fetchLogs(reset: true, query: effectiveQuery);
  }

  void _scheduleSearchRefresh(String value) {
    _searchDebounce?.cancel();
    _searchDebounce = Timer(const Duration(milliseconds: 350), () {
      if (!mounted) {
        return;
      }
      _refreshLogs(query: value);
    });
  }

  void _resetFilters() {
    _searchDebounce?.cancel();
    _searchController.clear();
    setState(() {
      _startTime = null;
      _endTime = null;
      _searchType = kOperationLogSearchTypeUserId;
    });
    _refreshLogs(query: '');
  }

  // ignore: unused_element
  Future<void> _showCreateLogDialog() async {
    return;
  }

  // ignore: unused_element
  Future<void> _showEditLogDialog(OperationLog log) async {
    return;
  }

  // ignore: unused_element
  Future<void> _deleteLog(int logId) async {
    return;
  }

  // ignore: unused_element
  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;
    final themeData = controller.currentBodyTheme.value;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          message,
          style: TextStyle(
            color: isError
                ? themeData.colorScheme.onError
                : themeData.colorScheme.onPrimary,
          ),
        ),
        backgroundColor: isError
            ? themeData.colorScheme.error
            : themeData.colorScheme.primary,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8.0)),
        margin: const EdgeInsets.all(10.0),
      ),
    );
  }

  bool get _hasActiveFilters =>
      _searchController.text.trim().isNotEmpty ||
      (_startTime != null && _endTime != null) ||
      _searchType != kOperationLogSearchTypeUserId;

  int _successCount() {
    return _filteredLogs
        .where((log) =>
            localizeOperationLogResult(log.operationResult) ==
            'common.success'.tr)
        .length;
  }

  int _failedCount() {
    return _filteredLogs
        .where((log) =>
            localizeOperationLogResult(log.operationResult) ==
            'common.failed'.tr)
        .length;
  }

  Widget _buildHeroSection(ThemeData themeData) {
    final onHero = themeData.brightness == Brightness.dark
        ? Colors.white
        : const Color(0xFF102530);
    final muted = onHero.withValues(alpha: 0.72);
    final queryLabel = _searchController.text.trim().isNotEmpty
        ? 'operationLog.workspace.signal.query'.trParams({
            'value': _searchController.text.trim(),
          })
        : 'operationLog.workspace.signal.queryIdle'.tr;
    final rangeLabel = _startTime != null && _endTime != null
        ? 'operationLog.filter.dateRangeLabel'.trParams({
            'start': formatLogDateTime(_startTime),
            'end': formatLogDateTime(_endTime),
          })
        : 'operationLog.workspace.signal.rangeIdle'.tr;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: themeData.brightness == Brightness.dark
              ? const [
                  Color(0xFF0A151D),
                  Color(0xFF102430),
                  Color(0xFF174255),
                ]
              : const [
                  Color(0xFFF7FAFC),
                  Color(0xFFE9F1F7),
                  Color(0xFFDDE8F0),
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
                  _OperationHeroBadge(
                    label: 'operationLog.workspace.eyebrow'.tr.toUpperCase(),
                    foregroundColor: onHero,
                  ),
                  _OperationHeroBadge(
                    label:
                        operationLogSearchTypeLabel(_searchType).toUpperCase(),
                    foregroundColor: Colors.white,
                    backgroundColor: _hasActiveFilters
                        ? const Color(0xFF1F9D68)
                        : const Color(0xFF2F6FD6),
                    filled: true,
                  ),
                ],
              ),
              const SizedBox(height: 18),
              Text(
                'operationLog.workspace.title'.tr,
                style: themeData.textTheme.headlineMedium?.copyWith(
                  color: onHero,
                  fontWeight: FontWeight.w800,
                  height: 1.05,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'operationLog.workspace.subtitle'.tr,
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
                  _OperationInlineSignal(
                    icon: Icons.search_rounded,
                    label: queryLabel,
                    color: onHero,
                  ),
                  _OperationInlineSignal(
                    icon: Icons.date_range_rounded,
                    label: rangeLabel,
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
              _OperationMetricTile(
                label: 'operationLog.workspace.metric.loaded'.tr,
                value: '${_logs.length}',
              ),
              _OperationMetricTile(
                label: 'operationLog.workspace.metric.visible'.tr,
                value: '${_filteredLogs.length}',
              ),
              _OperationMetricTile(
                label: 'operationLog.workspace.metric.success'.tr,
                value: '${_successCount()}',
              ),
              _OperationMetricTile(
                label: 'operationLog.workspace.metric.failed'.tr,
                value: '${_failedCount()}',
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

  Widget _buildStatePanel(
    ThemeData themeData, {
    required IconData icon,
    required String title,
    required String message,
    bool showRelogin = false,
  }) {
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
            Icon(icon, size: 40, color: themeData.colorScheme.primary),
            const SizedBox(height: 16),
            Text(
              title,
              style: themeData.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w700,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 10),
            Text(
              message,
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
                  onPressed: () => _refreshLogs(),
                  icon: const Icon(Icons.refresh_rounded),
                  label: Text('operationLog.workspace.filterRefresh'.tr),
                ),
                if (showRelogin)
                  FilledButton.icon(
                    onPressed: () => Get.offAllNamed(Routes.login),
                    icon: const Icon(Icons.login_rounded),
                    label: Text('operationLog.action.relogin'.tr),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSearchBar(ThemeData themeData) {
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
      child: Padding(
        padding: EdgeInsets.zero,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            LayoutBuilder(
              builder: (context, constraints) {
                final stacked = constraints.maxWidth < 880;
                final search = Autocomplete<String>(
                  optionsBuilder: (TextEditingValue textEditingValue) async {
                    if (textEditingValue.text.isEmpty ||
                        _searchType == kLogSearchTypeTimeRange) {
                      return const Iterable<String>.empty();
                    }
                    return await _fetchAutocompleteSuggestions(
                        textEditingValue.text);
                  },
                  onSelected: (String selection) {
                    _searchController.text = selection;
                    _refreshLogs(query: selection);
                  },
                  fieldViewBuilder:
                      (context, controller, focusNode, onFieldSubmitted) {
                    return TextField(
                      controller: _searchController,
                      focusNode: focusNode,
                      decoration: InputDecoration(
                        labelText: 'operationLog.workspace.filterTitle'.tr,
                        hintText: operationLogSearchHintText(_searchType),
                        hintStyle: themeData.textTheme.bodyMedium?.copyWith(
                          color: themeData.colorScheme.onSurface
                              .withValues(alpha: 0.6),
                        ),
                        prefixIcon: Icon(
                          Icons.search_rounded,
                          color: themeData.colorScheme.primary,
                        ),
                        suffixIcon: _searchController.text.isNotEmpty ||
                                (_startTime != null && _endTime != null)
                            ? IconButton(
                                icon: Icon(
                                  Icons.clear_rounded,
                                  color: themeData.colorScheme.onSurfaceVariant,
                                ),
                                onPressed: () {
                                  _resetFilters();
                                },
                              )
                            : null,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(18.0),
                          borderSide: BorderSide.none,
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(18.0),
                          borderSide: BorderSide(
                            color: themeData.colorScheme.outline
                                .withValues(alpha: 0.14),
                          ),
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(18.0),
                          borderSide: BorderSide(
                            color: themeData.colorScheme.primary,
                            width: 1.4,
                          ),
                        ),
                        filled: true,
                        fillColor: themeData.colorScheme.surface,
                        contentPadding: const EdgeInsets.symmetric(
                          vertical: 14.0,
                          horizontal: 16.0,
                        ),
                      ),
                      onChanged: (value) {
                        setState(() {});
                        _scheduleSearchRefresh(value);
                      },
                      onSubmitted: (value) => _refreshLogs(query: value),
                      enabled: _searchType != kLogSearchTypeTimeRange,
                    );
                  },
                );
                final modePicker = DropdownButtonFormField<String>(
                  initialValue: _searchType,
                  onChanged: (String? newValue) {
                    setState(() {
                      _searchType = newValue!;
                      _searchController.clear();
                      _startTime = null;
                      _endTime = null;
                    });
                    _refreshLogs(query: '');
                  },
                  decoration: InputDecoration(
                    labelText: 'operationLog.workspace.filterMode'.tr,
                    filled: true,
                    fillColor: themeData.colorScheme.surface,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(18),
                      borderSide: BorderSide.none,
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(18),
                      borderSide: BorderSide(
                        color: themeData.colorScheme.outline
                            .withValues(alpha: 0.14),
                      ),
                    ),
                  ),
                  items: <String>[
                    kOperationLogSearchTypeUserId,
                    kOperationLogSearchTypeOperationResult,
                    kLogSearchTypeTimeRange,
                  ].map<DropdownMenuItem<String>>((String value) {
                    return DropdownMenuItem<String>(
                      value: value,
                      child: Text(
                        operationLogSearchTypeLabel(value),
                        style:
                            TextStyle(color: themeData.colorScheme.onSurface),
                      ),
                    );
                  }).toList(),
                  dropdownColor: themeData.colorScheme.surface,
                  icon: Icon(
                    Icons.arrow_drop_down_rounded,
                    color: themeData.colorScheme.primary,
                  ),
                );
                final actions = Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  alignment: stacked ? WrapAlignment.start : WrapAlignment.end,
                  children: [
                    if (_hasActiveFilters)
                      OutlinedButton.icon(
                        onPressed: _resetFilters,
                        icon: const Icon(Icons.layers_clear_outlined),
                        label: Text('operationLog.workspace.filterReset'.tr),
                      ),
                    FilledButton.tonalIcon(
                      onPressed: () => _refreshLogs(),
                      icon: const Icon(Icons.refresh_rounded),
                      label: Text('operationLog.workspace.filterRefresh'.tr),
                    ),
                  ],
                );

                if (stacked) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      search,
                      const SizedBox(height: 16),
                      modePicker,
                      const SizedBox(height: 16),
                      actions,
                    ],
                  );
                }

                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(flex: 5, child: search),
                    const SizedBox(width: 16),
                    Expanded(flex: 3, child: modePicker),
                    const SizedBox(width: 16),
                    Expanded(flex: 2, child: actions),
                  ],
                );
              },
            ),
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: themeData.colorScheme.surface,
                borderRadius: BorderRadius.circular(18),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      _startTime != null && _endTime != null
                          ? 'operationLog.filter.dateRangeLabel'.trParams({
                              'start': formatLogDateTime(_startTime),
                              'end': formatLogDateTime(_endTime),
                            })
                          : 'operationLog.filter.selectDateRange'.tr,
                      style: themeData.textTheme.bodyMedium?.copyWith(
                        color: _startTime != null && _endTime != null
                            ? themeData.colorScheme.onSurface
                            : themeData.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    icon: Icon(Icons.date_range_rounded,
                        color: themeData.colorScheme.primary),
                    tooltip: 'operationLog.filter.tooltip'.tr,
                    onPressed: () async {
                      final range = await showDateRangePicker(
                        context: context,
                        firstDate: DateTime(2000),
                        lastDate: DateTime.now(),
                        locale: Get.locale ?? const Locale('en', 'US'),
                        helpText: 'operationLog.filter.selectDateRange'.tr,
                        cancelText: 'common.cancel'.tr,
                        confirmText: 'common.confirm'.tr,
                        fieldStartHintText: 'operationLog.filter.startDate'.tr,
                        fieldEndHintText: 'operationLog.filter.endDate'.tr,
                        builder: (BuildContext context, Widget? child) {
                          return Theme(
                            data: themeData.copyWith(
                              colorScheme: themeData.colorScheme.copyWith(
                                primary: themeData.colorScheme.primary,
                                onPrimary: themeData.colorScheme.onPrimary,
                              ),
                              textButtonTheme: TextButtonThemeData(
                                style: TextButton.styleFrom(
                                  foregroundColor:
                                      themeData.colorScheme.primary,
                                ),
                              ),
                            ),
                            child: child!,
                          );
                        },
                      );
                      if (range != null) {
                        setState(() {
                          _startTime = range.start;
                          _endTime = range.end;
                          _searchType = kLogSearchTypeTimeRange;
                          _searchController.clear();
                        });
                        _refreshLogs(query: '');
                      }
                    },
                  ),
                  if (_startTime != null && _endTime != null)
                    IconButton(
                      icon: Icon(Icons.clear_rounded,
                          color: themeData.colorScheme.onSurfaceVariant),
                      tooltip: 'operationLog.filter.clearDateRange'.tr,
                      onPressed: () {
                        setState(() {
                          _startTime = null;
                          _endTime = null;
                          _searchType = kOperationLogSearchTypeUserId;
                          _searchController.clear();
                        });
                        _refreshLogs(query: '');
                      },
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLogCard(OperationLog log, ThemeData themeData) {
    final result = localizeOperationLogResult(log.operationResult);
    final userLabel = log.username ??
        log.realName ??
        log.userId?.toString() ??
        'common.unknown'.tr;
    final accent = result == 'common.success'.tr
        ? const Color(0xFF1F9D68)
        : result == 'common.failed'.tr
            ? const Color(0xFFC45A4E)
            : const Color(0xFF2F6FD6);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: themeData.colorScheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: themeData.colorScheme.outline.withValues(alpha: 0.12),
        ),
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
                      'operationLog.detail.id'.trParams(
                          {'value': '${log.logId ?? 'common.unknown'.tr}'}),
                      style: themeData.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: [
                        _OperationStatusBadge(
                          label: result,
                          color: accent,
                        ),
                        _OperationMetaChip(
                          icon: Icons.person_outline_rounded,
                          label: 'operationLog.detail.userId'.trParams({
                            'value': '${log.userId ?? userLabel}',
                          }),
                        ),
                        _OperationMetaChip(
                          icon: Icons.schedule_rounded,
                          label: formatLogDateTime(log.operationTime),
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
              _OperationMetaChip(
                icon: Icons.category_outlined,
                label: log.operationType ?? 'common.unknown'.tr,
              ),
              _OperationMetaChip(
                icon: Icons.language_rounded,
                label: log.requestIp ?? 'common.none'.tr,
              ),
            ],
          ),
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(18),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'operationLog.field.operationContent'.tr,
                  style: themeData.textTheme.labelLarge?.copyWith(
                    color: themeData.colorScheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  log.operationContent ?? 'common.none'.tr,
                  style: themeData.textTheme.bodyMedium?.copyWith(
                    height: 1.45,
                  ),
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 10),
                Text(
                  'operationLog.detail.remarks'
                      .trParams({'value': log.remarks ?? 'common.none'.tr}),
                  style: themeData.textTheme.bodySmall?.copyWith(
                    color: themeData.colorScheme.onSurfaceVariant,
                    height: 1.45,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final themeData = controller.currentBodyTheme.value;
      return DashboardPageTemplate(
        theme: themeData,
        title: 'operationLog.page.title'.tr,
        pageType: DashboardPageType.admin,
        bodyIsScrollable: true,
        padding: EdgeInsets.zero,
        onRefresh: _refreshLogs,
        onThemeToggle: controller.toggleBodyTheme,
        body: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_isAdmin) ...[
                _buildHeroSection(themeData),
                const SizedBox(height: 24),
                _buildSectionHeading(
                  themeData,
                  eyebrow: 'operationLog.workspace.filterEyebrow'.tr,
                  title: 'operationLog.workspace.filterTitle'.tr,
                  description: 'operationLog.workspace.filterBody'.tr,
                ),
                const SizedBox(height: 18),
                _buildSearchBar(themeData),
                const SizedBox(height: 24),
                _buildSectionHeading(
                  themeData,
                  eyebrow: 'operationLog.workspace.listEyebrow'.tr,
                  title: 'operationLog.workspace.listTitle'.tr,
                  description: 'operationLog.workspace.listBody'.tr,
                ),
                const SizedBox(height: 18),
              ],
              Expanded(
                child: _isLoading && _logs.isEmpty
                    ? Center(
                        child: CupertinoActivityIndicator(
                          color: themeData.colorScheme.primary,
                          radius: 16.0,
                        ),
                      )
                    : _errorMessage.isNotEmpty && !_isLoading
                        ? _buildStatePanel(
                            themeData,
                            icon: CupertinoIcons.exclamationmark_triangle,
                            title: 'operationLog.workspace.errorTitle'.tr,
                            message: _errorMessage,
                            showRelogin: shouldShowOperationLogReloginAction(
                              _errorMessage,
                            ),
                          )
                        : _filteredLogs.isEmpty
                            ? _buildStatePanel(
                                themeData,
                                icon: CupertinoIcons.doc,
                                title: 'operationLog.workspace.emptyTitle'.tr,
                                message: _errorMessage.isNotEmpty
                                    ? _errorMessage
                                    : 'operationLog.empty.default'.tr,
                              )
                            : CupertinoScrollbar(
                                controller: _scrollController,
                                thumbVisibility: true,
                                thickness: 6.0,
                                thicknessWhileDragging: 10.0,
                                child: RefreshIndicator(
                                  onRefresh: () => _refreshLogs(),
                                  color: themeData.colorScheme.primary,
                                  backgroundColor:
                                      themeData.colorScheme.surfaceContainer,
                                  child: ListView.builder(
                                    controller: _scrollController,
                                    itemCount: _filteredLogs.length +
                                        ((_isLoading && _logs.isNotEmpty)
                                            ? 1
                                            : 0),
                                    itemBuilder: (context, index) {
                                      if (index == _filteredLogs.length) {
                                        return const Padding(
                                          padding: EdgeInsets.symmetric(
                                            vertical: 12,
                                          ),
                                          child: Center(
                                              child:
                                                  CupertinoActivityIndicator()),
                                        );
                                      }
                                      final log = _filteredLogs[index];
                                      return Padding(
                                        padding: EdgeInsets.only(
                                          bottom:
                                              index == _filteredLogs.length - 1
                                                  ? 0
                                                  : 14,
                                        ),
                                        child: _buildLogCard(log, themeData),
                                      );
                                    },
                                  ),
                                ),
                              ),
              ),
            ],
          ),
        ),
      );
    });
  }
}

class _OperationHeroBadge extends StatelessWidget {
  const _OperationHeroBadge({
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

class _OperationInlineSignal extends StatelessWidget {
  const _OperationInlineSignal({
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

class _OperationMetricTile extends StatelessWidget {
  const _OperationMetricTile({
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

class _OperationStatusBadge extends StatelessWidget {
  const _OperationStatusBadge({
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

class _OperationMetaChip extends StatelessWidget {
  const _OperationMetaChip({
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
