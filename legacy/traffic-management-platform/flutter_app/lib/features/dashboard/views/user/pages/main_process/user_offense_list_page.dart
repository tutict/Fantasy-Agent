// user_offense_list_page.dart
import 'dart:developer' as developer;

import 'package:final_assignment_front/config/routes/app_routes.dart';
import 'package:final_assignment_front/features/api/driver_information_controller_api.dart';
import 'package:final_assignment_front/features/api/offense_information_controller_api.dart';
import 'package:final_assignment_front/features/api/user_management_controller_api.dart';
import 'package:final_assignment_front/features/dashboard/controllers/user_dashboard_screen_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/dashboard_page_template.dart';
import 'package:final_assignment_front/features/model/offense_information.dart';
import 'package:final_assignment_front/i18n/offense_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:final_assignment_front/utils/helpers/role_utils.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:jwt_decoder/jwt_decoder.dart';
import 'package:shared_preferences/shared_preferences.dart';

class UserOffenseListPage extends StatefulWidget {
  const UserOffenseListPage({super.key});

  @override
  State<UserOffenseListPage> createState() => _UserOffenseListPageState();
}

class _UserOffenseListPageState extends State<UserOffenseListPage> {
  final OffenseInformationControllerApi offenseApi =
      OffenseInformationControllerApi();
  final DriverInformationControllerApi driverApi =
      DriverInformationControllerApi();
  final UserManagementControllerApi userApi = UserManagementControllerApi();
  final List<OffenseInformation> _offenses = [];
  List<OffenseInformation> _filteredOffenses = [];
  final TextEditingController _searchController = TextEditingController();
  String _driverName = '';
  int _currentPage = 1;
  final int _pageSize = 20;
  bool _hasMore = true;
  bool _isLoading = false;
  bool _isUser = false;
  String _errorMessage = '';
  DateTime? _startTime;
  DateTime? _endTime;
  late ScrollController _scrollController;

  final UserDashboardController? dashboardController =
      Get.isRegistered<UserDashboardController>()
          ? Get.find<UserDashboardController>()
          : null;

  @override
  void initState() {
    super.initState();
    _scrollController = ScrollController();
    _initialize();
  }

  @override
  void dispose() {
    _searchController.dispose();
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

  List<OffenseInformation> _buildFilteredOffenses(
    Iterable<OffenseInformation> offenses,
  ) {
    final searchText = _searchController.text.trim().toLowerCase();

    return offenses.where((offense) {
      final offenseTime = offense.offenseTime;
      var matchesDateRange = true;

      if (_startTime != null && _endTime != null && offenseTime != null) {
        matchesDateRange = offenseTime.isAfter(_startTime!) &&
            offenseTime.isBefore(_endTime!.add(const Duration(days: 1)));
      } else if (_startTime != null &&
          _endTime != null &&
          offenseTime == null) {
        matchesDateRange = false;
      }

      var matchesSearch = true;
      if (searchText.isNotEmpty) {
        matchesSearch = (offense.offenseType
                    ?.toLowerCase()
                    .contains(searchText) ??
                false) ||
            (offense.offenseCode?.toLowerCase().contains(searchText) ?? false);
      }

      return matchesDateRange && matchesSearch;
    }).toList();
  }

  String _resolveFilterErrorMessage(List<OffenseInformation> filteredOffenses) {
    if (filteredOffenses.isNotEmpty) return '';
    if (_offenses.isEmpty) return 'offense.error.empty'.tr;
    if (_startTime != null && _endTime != null) {
      return 'offense.error.noRecordsInRange'.tr;
    }
    if (_searchController.text.trim().isNotEmpty) {
      return 'offense.error.noRecordsBySearch'.tr;
    }
    return 'offense.error.empty'.tr;
  }

  Future<bool> _validateJwtToken() async {
    final prefs = await SharedPreferences.getInstance();
    final jwtToken = await AuthTokenStore.instance.getJwtToken();
    if (jwtToken == null || jwtToken.isEmpty) {
      _setStateSafely(() {
        _isUser = false;
        _errorMessage = 'offense.error.unauthorized'.tr;
      });
      return false;
    }
    try {
      final decodedToken = JwtDecoder.decode(jwtToken);
      final isUser = hasAnyRole(decodedToken['roles'], const ['USER']);
      _setStateSafely(() {
        _isUser = isUser;
      });
      if (!isUser) {
        _setStateSafely(() => _errorMessage = 'offense.error.userOnly'.tr);
        return false;
      }
      if (JwtDecoder.isExpired(jwtToken)) {
        _setStateSafely(() {
          _isUser = false;
          _errorMessage = 'offense.error.loginExpired'.tr;
        });
        return false;
      }
      await userApi.initializeWithJwt();
      if (!mounted) return false;
      await driverApi.initializeWithJwt();
      if (!mounted) return false;
      _driverName = prefs.getString('driverName') ?? '';
      if (_driverName.isEmpty) {
        _driverName = await _fetchDriverName() ?? '';
        if (!mounted) return false;
      }
      if (_driverName.isNotEmpty) {
        await prefs.setString('driverName', _driverName);
        await prefs.setString('displayName', _driverName);
        developer.log('Stored driverName: $_driverName');
      }
      return true;
    } catch (e) {
      developer.log('JWT validation error: $e');
      _setStateSafely(() {
        _isUser = false;
        _errorMessage = 'offense.error.invalidLogin'.tr;
      });
      return false;
    }
  }

  Future<String?> _fetchDriverName() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final user = await userApi.apiUsersMeGet();
      final driverInfo = await driverApi.apiDriversMeGet();
      final driverName = driverInfo?.name ??
          prefs.getString('displayName') ??
          user?.realName ??
          user?.username ??
          prefs.getString('userName') ??
          '';
      developer.log('Driver name from API: $driverName');
      return driverName;
    } catch (e) {
      developer.log('Error fetching driver name: $e');
      return null;
    }
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
      await offenseApi.initializeWithJwt();
      if (!mounted) return;
      await _loadOffenses(reset: true);
    } catch (e) {
      developer.log('Initialization error: $e');
      _setStateSafely(
        () => _errorMessage = 'offense.error.initializeFailed'.trParams({
          'error': formatUserOffenseErrorDetail(e),
        }),
      );
    } finally {
      _setStateSafely(() => _isLoading = false);
    }
  }

  Future<void> _loadOffenses({bool reset = false}) async {
    if (!reset && (!_hasMore || _isLoading)) return;

    if (reset) {
      _currentPage = 1;
      _hasMore = true;
      _offenses.clear();
      _filteredOffenses.clear();
      _searchController.clear();
    }

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
      final offenses = await offenseApi.apiOffensesMeGet(
        page: _currentPage,
        size: _pageSize,
      );
      if (!mounted) return;
      final updatedOffenses = <OffenseInformation>[
        ..._offenses,
        ...offenses,
      ];
      final filteredOffenses = _buildFilteredOffenses(updatedOffenses);

      _setStateSafely(() {
        _offenses
          ..clear()
          ..addAll(updatedOffenses);
        _hasMore = offenses.length == _pageSize;
        _filteredOffenses = filteredOffenses;
        _errorMessage = _resolveFilterErrorMessage(filteredOffenses);
        _currentPage++;
      });
      developer.log('Loaded offenses: ${updatedOffenses.length}');
    } catch (e) {
      developer.log('Error fetching offenses: $e',
          stackTrace: StackTrace.current);
      if (e is ApiException && e.code == 204) {
        _setStateSafely(() {
          _offenses.clear();
          _filteredOffenses.clear();
          _errorMessage = 'offense.error.notFound'.tr;
          _hasMore = false;
        });
      } else if (e is ApiException && e.code == 403) {
        _setStateSafely(() {
          _errorMessage = 'offense.error.unauthorized'.tr;
        });
        _redirectToLogin();
      } else {
        _setStateSafely(() {
          _errorMessage = 'offense.error.loadFailed'
              .trParams({'error': formatUserOffenseError(e)});
        });
      }
    } finally {
      _setStateSafely(() => _isLoading = false);
    }
  }

  void _applyFilters() {
    final filteredOffenses = _buildFilteredOffenses(_offenses);
    _setStateSafely(() {
      _filteredOffenses = filteredOffenses;
      _errorMessage = _resolveFilterErrorMessage(filteredOffenses);
    });
  }

  Future<List<String>> _fetchAutocompleteSuggestions(String prefix) async {
    try {
      final offenses = _offenses.isNotEmpty
          ? _offenses
          : await offenseApi.apiOffensesMeGet(
              page: 1,
              size: 50,
            );
      final suggestions = <String>{};
      for (var offense in offenses) {
        if (offense.offenseType != null &&
            offense.offenseType!.toLowerCase().contains(prefix.toLowerCase())) {
          suggestions.add(offense.offenseType!);
        }
        if (offense.offenseCode != null &&
            offense.offenseCode!.toLowerCase().contains(prefix.toLowerCase())) {
          suggestions.add(offense.offenseCode!);
        }
      }
      return suggestions.toList();
    } catch (e) {
      developer.log('Failed to fetch autocomplete suggestions: $e');
      return [];
    }
  }

  Future<void> _loadMoreOffenses() async {
    if (!_isLoading && _hasMore) {
      await _loadOffenses();
    }
  }

  Future<void> _refreshOffenses() async {
    _setStateSafely(() {
      _offenses.clear();
      _filteredOffenses.clear();
      _currentPage = 1;
      _hasMore = true;
      _isLoading = true;
      _startTime = null;
      _endTime = null;
      _searchController.clear();
    });
    await _loadOffenses(reset: true);
  }

  void _goToDetailPage(OffenseInformation offense) {
    Get.to(() => UserOffenseDetailPage(offense: offense));
  }

  void _clearFilters() {
    _setStateSafely(() {
      _searchController.clear();
      _startTime = null;
      _endTime = null;
    });
    _applyFilters();
  }

  bool _isResolvedStatus(String? status) {
    final normalized = status?.trim().toLowerCase() ?? '';
    if (normalized.isEmpty) return false;
    return normalized.contains('processed') ||
        normalized.contains('completed') ||
        normalized.contains('approved') ||
        normalized.contains('success') ||
        normalized.contains('done');
  }

  int _visiblePoints() {
    return _filteredOffenses.fold<int>(
      0,
      (sum, offense) => sum + (offense.deductedPoints ?? 0),
    );
  }

  double _visibleFines() {
    return _filteredOffenses.fold<double>(
      0,
      (sum, offense) => sum + (offense.fineAmount ?? 0),
    );
  }

  int _pendingCount() {
    return _filteredOffenses
        .where((offense) => !_isResolvedStatus(offense.processStatus))
        .length;
  }

  Widget _buildWorkspaceHero(ThemeData themeData) {
    final displayName =
        _driverName.isNotEmpty ? _driverName : 'common.userWorkspace'.tr;
    final searchActive = _searchController.text.trim().isNotEmpty;
    final rangeActive = _startTime != null && _endTime != null;
    final onHero = themeData.brightness == Brightness.dark
        ? Colors.white
        : const Color(0xFF11242E);
    final muted = onHero.withValues(alpha: 0.74);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: themeData.brightness == Brightness.dark
              ? const [
                  Color(0xFF081720),
                  Color(0xFF0D2833),
                  Color(0xFF12424B),
                ]
              : const [
                  Color(0xFFF4FAFA),
                  Color(0xFFE7F3F4),
                  Color(0xFFDCECEE),
                ],
        ),
        borderRadius: BorderRadius.circular(30),
        border: Border.all(
          color: themeData.colorScheme.outline.withValues(alpha: 0.12),
        ),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final stacked = constraints.maxWidth < 920;
          final lead = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  _HeroBadge(
                    label: 'offense.workspace.eyebrow'.tr.toUpperCase(),
                    foregroundColor: onHero,
                  ),
                  _HeroBadge(
                    label: (searchActive || rangeActive
                            ? 'offense.workspace.filtered'
                            : 'offense.workspace.live')
                        .tr
                        .toUpperCase(),
                    foregroundColor: Colors.white,
                    backgroundColor: searchActive || rangeActive
                        ? const Color(0xFF1F9D68)
                        : const Color(0xFF2F6FD6),
                    filled: true,
                  ),
                ],
              ),
              const SizedBox(height: 18),
              Text(
                'offense.workspace.title'.trParams({'name': displayName}),
                style: themeData.textTheme.headlineMedium?.copyWith(
                  color: onHero,
                  fontWeight: FontWeight.w800,
                  height: 1.06,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'offense.workspace.subtitle'.tr,
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
                  _HeroInlineStat(
                    icon: Icons.search_rounded,
                    color: onHero,
                    label: searchActive
                        ? 'offense.workspace.searchActive'.trParams({
                            'value': _searchController.text.trim(),
                          })
                        : 'offense.workspace.searchIdle'.tr,
                  ),
                  _HeroInlineStat(
                    icon: Icons.date_range_rounded,
                    color: onHero,
                    label: rangeActive
                        ? 'offense.filter.rangeLabel'.trParams({
                            'start': formatOffenseDate(
                              _startTime,
                              emptyKey: 'common.notFilled',
                            ),
                            'end': formatOffenseDate(
                              _endTime,
                              emptyKey: 'common.notFilled',
                            ),
                          })
                        : 'offense.workspace.rangeIdle'.tr,
                  ),
                ],
              ),
            ],
          );
          final metrics = Wrap(
            spacing: 14,
            runSpacing: 14,
            children: [
              _WorkspaceMetric(
                label: 'offense.workspace.metric.loaded'.tr,
                value: '${_offenses.length}',
              ),
              _WorkspaceMetric(
                label: 'offense.workspace.metric.visible'.tr,
                value: '${_filteredOffenses.length}',
              ),
              _WorkspaceMetric(
                label: 'offense.workspace.metric.pending'.tr,
                value: '${_pendingCount()}',
              ),
              _WorkspaceMetric(
                label: 'offense.workspace.metric.points'.tr,
                value: '${_visiblePoints()}',
              ),
              _WorkspaceMetric(
                label: 'offense.workspace.metric.fine'.tr,
                value: formatOffenseAmount(_visibleFines()),
              ),
            ],
          );

          if (stacked) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                lead,
                const SizedBox(height: 24),
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
                flex: 5,
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
                  onPressed: _refreshOffenses,
                  icon: const Icon(Icons.refresh_rounded),
                  label: Text('offense.workspace.filterRefresh'.tr),
                ),
                if (showRelogin)
                  FilledButton.icon(
                    onPressed: () => Get.offAllNamed(Routes.login),
                    icon: const Icon(Icons.login_rounded),
                    label: Text('offense.action.relogin'.tr),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildOffenseListItem(
      ThemeData themeData, OffenseInformation offense) {
    final resolved = _isResolvedStatus(offense.processStatus);
    final normalized = offense.processStatus?.trim().toLowerCase() ?? '';
    final accent = normalized.contains('reject') || normalized.contains('fail')
        ? const Color(0xFFC45A4E)
        : resolved
            ? const Color(0xFF1F9D68)
            : normalized.contains('review') || normalized.contains('appeal')
                ? const Color(0xFFC28B2C)
                : const Color(0xFF2F6FD6);

    return Material(
      color: themeData.colorScheme.surfaceContainerLowest,
      borderRadius: BorderRadius.circular(24),
      child: InkWell(
        borderRadius: BorderRadius.circular(24),
        onTap: () => _goToDetailPage(offense),
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            border: Border.all(
              color: themeData.colorScheme.outline.withValues(alpha: 0.12),
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.all(22),
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
                          _PlateBadge(
                            label: offense.licensePlate ?? 'common.none'.tr,
                          ),
                          const SizedBox(height: 14),
                          Text(
                            offense.offenseType ?? 'common.unknown'.tr,
                            style: themeData.textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 14),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        _StatusBadge(
                          label: formatUserOffenseProcessStatus(
                            offense.processStatus,
                          ),
                          color: accent,
                        ),
                        const SizedBox(height: 18),
                        Icon(
                          Icons.arrow_outward_rounded,
                          size: 20,
                          color: themeData.colorScheme.onSurfaceVariant,
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 18,
                  runSpacing: 14,
                  children: [
                    _RecordMeta(
                      icon: Icons.qr_code_rounded,
                      label: 'offense.detail.code'.tr,
                      value: offense.offenseCode ?? 'common.none'.tr,
                    ),
                    _RecordMeta(
                      icon: Icons.schedule_rounded,
                      label: 'offense.detail.time'.tr,
                      value: formatOffenseDate(
                        offense.offenseTime,
                        emptyKey: 'common.notFilled',
                      ),
                    ),
                    _RecordMeta(
                      icon: Icons.scoreboard_outlined,
                      label: 'offense.detail.points'.tr,
                      value: formatOffensePoints(offense.deductedPoints),
                    ),
                    _RecordMeta(
                      icon: Icons.payments_outlined,
                      label: 'offense.detail.amount'.tr,
                      value: formatOffenseAmount(offense.fineAmount),
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
                        'offense.detail.location'.tr,
                        style: themeData.textTheme.labelLarge?.copyWith(
                          color: themeData.colorScheme.onSurfaceVariant,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        offense.offenseLocation ?? 'common.notFilled'.tr,
                        style: themeData.textTheme.bodyMedium?.copyWith(
                          height: 1.45,
                        ),
                      ),
                      if ((offense.processResult ?? '').trim().isNotEmpty) ...[
                        const SizedBox(height: 12),
                        Text(
                          offense.processResult!,
                          style: themeData.textTheme.bodySmall?.copyWith(
                            color: themeData.colorScheme.onSurfaceVariant,
                            height: 1.45,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
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
                final stacked = constraints.maxWidth < 840;
                final search = Autocomplete<String>(
                  optionsBuilder: (TextEditingValue textEditingValue) async {
                    if (textEditingValue.text.isEmpty) {
                      return const Iterable<String>.empty();
                    }
                    return await _fetchAutocompleteSuggestions(
                        textEditingValue.text);
                  },
                  onSelected: (String selection) {
                    _searchController.text = selection;
                    _applyFilters();
                  },
                  fieldViewBuilder:
                      (context, controller, focusNode, onFieldSubmitted) {
                    _searchController.text = controller.text;
                    return TextField(
                      controller: controller,
                      focusNode: focusNode,
                      decoration: InputDecoration(
                        labelText: 'offense.workspace.filterTitle'.tr,
                        hintText: 'offense.search.hint'.tr,
                        prefixIcon: Icon(
                          Icons.search_rounded,
                          color: themeData.colorScheme.primary,
                        ),
                        suffixIcon: controller.text.isNotEmpty
                            ? IconButton(
                                icon: Icon(
                                  Icons.clear_rounded,
                                  color: themeData.colorScheme.onSurfaceVariant,
                                ),
                                onPressed: () {
                                  controller.clear();
                                  _searchController.clear();
                                  _setStateSafely(() {});
                                  _applyFilters();
                                },
                              )
                            : null,
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
                        focusedBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(18),
                          borderSide: BorderSide(
                            color: themeData.colorScheme.primary,
                            width: 1.4,
                          ),
                        ),
                        filled: true,
                        fillColor: themeData.colorScheme.surface,
                        contentPadding: const EdgeInsets.symmetric(
                          vertical: 14,
                          horizontal: 18,
                        ),
                      ),
                      onChanged: (value) {
                        _setStateSafely(() {});
                        if (value.isEmpty) {
                          _applyFilters();
                        }
                      },
                      onSubmitted: (value) => _applyFilters(),
                    );
                  },
                );
                final actions = Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  alignment: stacked ? WrapAlignment.start : WrapAlignment.end,
                  children: [
                    if (_searchController.text.trim().isNotEmpty ||
                        (_startTime != null && _endTime != null))
                      OutlinedButton.icon(
                        onPressed: _clearFilters,
                        icon: const Icon(Icons.layers_clear_outlined),
                        label: Text('offense.workspace.filterReset'.tr),
                      ),
                    FilledButton.tonalIcon(
                      onPressed: _refreshOffenses,
                      icon: const Icon(Icons.refresh_rounded),
                      label: Text('offense.workspace.filterRefresh'.tr),
                    ),
                  ],
                );

                if (stacked) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      search,
                      const SizedBox(height: 16),
                      actions,
                    ],
                  );
                }

                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(flex: 5, child: search),
                    const SizedBox(width: 18),
                    Expanded(flex: 3, child: actions),
                  ],
                );
              },
            ),
            const SizedBox(height: 16),
            _buildTimeRangeFilter(themeData),
          ],
        ),
      ),
    );
  }

  Widget _buildTimeRangeFilter(ThemeData themeData) {
    return Container(
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
                  ? 'offense.filter.rangeLabel'.trParams({
                      'start': formatOffenseDate(
                        _startTime,
                        emptyKey: 'common.notFilled',
                      ),
                      'end': formatOffenseDate(
                        _endTime,
                        emptyKey: 'common.notFilled',
                      ),
                    })
                  : 'offense.filter.select'.tr,
              style: TextStyle(
                color: _startTime != null && _endTime != null
                    ? themeData.colorScheme.onSurface
                    : themeData.colorScheme.onSurfaceVariant,
                fontWeight: _startTime != null && _endTime != null
                    ? FontWeight.w600
                    : null,
              ),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            icon: Icon(Icons.date_range_rounded,
                color: themeData.colorScheme.primary),
            tooltip: 'offense.filter.tooltip'.tr,
            onPressed: () async {
              final range = await showDateRangePicker(
                context: context,
                firstDate: DateTime(2000),
                lastDate: DateTime.now(),
                locale: Get.locale ?? const Locale('en', 'US'),
                helpText: 'offense.filter.select'.tr,
                cancelText: 'common.cancel'.tr,
                confirmText: 'common.confirm'.tr,
                fieldStartHintText: 'offense.filter.startDate'.tr,
                fieldEndHintText: 'offense.filter.endDate'.tr,
                builder: (context, child) => Theme(
                  data: themeData.copyWith(
                    colorScheme: themeData.colorScheme.copyWith(
                      primary: themeData.colorScheme.primary,
                      onPrimary: themeData.colorScheme.onPrimary,
                    ),
                    textButtonTheme: TextButtonThemeData(
                      style: TextButton.styleFrom(
                        foregroundColor: themeData.colorScheme.primary,
                      ),
                    ),
                  ),
                  child: child!,
                ),
              );
              if (!mounted || range == null) return;
              _setStateSafely(() {
                _startTime = range.start;
                _endTime = range.end;
              });
              _applyFilters();
            },
          ),
          if (_startTime != null && _endTime != null)
            IconButton(
              icon: Icon(
                Icons.clear_rounded,
                color: themeData.colorScheme.onSurfaceVariant,
              ),
              tooltip: 'offense.filter.clear'.tr,
              onPressed: () {
                _setStateSafely(() {
                  _startTime = null;
                  _endTime = null;
                });
                _applyFilters();
              },
            ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final themeData = dashboardController != null
          ? dashboardController!.currentBodyTheme.value
          : Theme.of(context);
      if (!_isUser) {
        return DashboardPageTemplate(
          theme: themeData,
          title: 'offense.page.title'.tr,
          pageType: DashboardPageType.custom,
          body: _buildStatePanel(
            themeData,
            icon: Icons.lock_clock_outlined,
            title: 'offense.workspace.errorTitle'.tr,
            message: _errorMessage,
            showRelogin: true,
          ),
        );
      }

      return DashboardPageTemplate(
        theme: themeData,
        title: 'offense.page.title'.tr,
        pageType: DashboardPageType.user,
        onThemeToggle: dashboardController?.toggleBodyTheme,
        bodyIsScrollable: true,
        padding: EdgeInsets.zero,
        body: RefreshIndicator(
          onRefresh: _refreshOffenses,
          color: themeData.colorScheme.primary,
          backgroundColor: themeData.colorScheme.surfaceContainer,
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildWorkspaceHero(themeData),
                const SizedBox(height: 24),
                _buildSectionHeading(
                  themeData,
                  eyebrow: 'offense.workspace.filterEyebrow'.tr,
                  title: 'offense.workspace.filterTitle'.tr,
                  description: 'offense.workspace.filterBody'.tr,
                ),
                const SizedBox(height: 18),
                _buildSearchBar(themeData),
                const SizedBox(height: 24),
                _buildSectionHeading(
                  themeData,
                  eyebrow: 'offense.workspace.listEyebrow'.tr,
                  title: 'offense.workspace.listTitle'.tr,
                  description: 'offense.workspace.listBody'.tr,
                ),
                const SizedBox(height: 18),
                Expanded(
                  child: NotificationListener<ScrollNotification>(
                    onNotification: (scrollInfo) {
                      if (scrollInfo.metrics.pixels >=
                              scrollInfo.metrics.maxScrollExtent - 120 &&
                          _hasMore) {
                        _loadMoreOffenses();
                      }
                      return false;
                    },
                    child: _isLoading && _currentPage == 1
                        ? Center(
                            child: CircularProgressIndicator(
                              valueColor: AlwaysStoppedAnimation(
                                  themeData.colorScheme.primary),
                            ),
                          )
                        : _errorMessage.isNotEmpty && _filteredOffenses.isEmpty
                            ? _buildStatePanel(
                                themeData,
                                icon: Icons.info_outline_rounded,
                                title: 'offense.workspace.errorTitle'.tr,
                                message: _errorMessage,
                                showRelogin: shouldShowUserOffenseReloginAction(
                                  _errorMessage,
                                ),
                              )
                            : _filteredOffenses.isEmpty
                                ? _buildStatePanel(
                                    themeData,
                                    icon: Icons.fact_check_outlined,
                                    title: 'offense.workspace.emptyTitle'.tr,
                                    message: _errorMessage.isNotEmpty
                                        ? _errorMessage
                                        : 'offense.workspace.emptyBody'.tr,
                                  )
                                : CupertinoScrollbar(
                                    controller: _scrollController,
                                    thumbVisibility: true,
                                    child: ListView.builder(
                                      controller: _scrollController,
                                      itemCount: _filteredOffenses.length +
                                          (_hasMore ? 1 : 0),
                                      itemBuilder: (context, index) {
                                        if (index == _filteredOffenses.length &&
                                            _hasMore) {
                                          return const Padding(
                                            padding: EdgeInsets.symmetric(
                                              vertical: 12,
                                            ),
                                            child: Center(
                                              child:
                                                  CircularProgressIndicator(),
                                            ),
                                          );
                                        }
                                        final offense =
                                            _filteredOffenses[index];
                                        return Padding(
                                          padding: EdgeInsets.only(
                                            bottom: index ==
                                                    _filteredOffenses.length - 1
                                                ? 0
                                                : 14,
                                          ),
                                          child: _buildOffenseListItem(
                                            themeData,
                                            offense,
                                          ),
                                        );
                                      },
                                    ),
                                  ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    });
  }
}

class _HeroBadge extends StatelessWidget {
  const _HeroBadge({
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

class _HeroInlineStat extends StatelessWidget {
  const _HeroInlineStat({
    required this.icon,
    required this.color,
    required this.label,
  });

  final IconData icon;
  final Color color;
  final String label;

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

class _WorkspaceMetric extends StatelessWidget {
  const _WorkspaceMetric({
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

class _PlateBadge extends StatelessWidget {
  const _PlateBadge({
    required this.label,
  });

  final String label;

  @override
  Widget build(BuildContext context) {
    final themeData = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFF1E4F8A).withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: themeData.textTheme.labelLarge?.copyWith(
          fontWeight: FontWeight.w700,
          color: themeData.colorScheme.onSurface,
        ),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({
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

class _RecordMeta extends StatelessWidget {
  const _RecordMeta({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final themeData = Theme.of(context);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 18, color: themeData.colorScheme.primary),
        const SizedBox(width: 8),
        RichText(
          text: TextSpan(
            style: themeData.textTheme.bodyMedium?.copyWith(
              color: themeData.colorScheme.onSurfaceVariant,
            ),
            children: [
              TextSpan(
                text: '$label ',
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              TextSpan(text: value),
            ],
          ),
        ),
      ],
    );
  }
}

class UserOffenseDetailPage extends StatelessWidget {
  final OffenseInformation offense;
  final UserDashboardController? dashboardController;

  UserOffenseDetailPage({super.key, required this.offense})
      : dashboardController = Get.isRegistered<UserDashboardController>()
            ? Get.find<UserDashboardController>()
            : null;

  Widget _buildDetailRow(String label, String value, ThemeData themeData) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'common.labelWithColon'.trParams({'label': label}),
            style: themeData.textTheme.bodyLarge?.copyWith(
              fontWeight: FontWeight.bold,
              color: themeData.colorScheme.onSurface,
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: themeData.textTheme.bodyMedium?.copyWith(
                color: themeData.colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final themeData = dashboardController != null
          ? dashboardController!.currentBodyTheme.value
          : Theme.of(context);
      return DashboardPageTemplate(
        theme: themeData,
        title: 'offense.detail.title'.tr,
        pageType: DashboardPageType.user,
        onThemeToggle: dashboardController?.toggleBodyTheme,
        body: Card(
          elevation: 3,
          color: themeData.colorScheme.surfaceContainer,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(16.0)),
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildDetailRow(
                    'offense.detail.id'.tr,
                    offense.offenseId?.toString() ?? 'common.notFilled'.tr,
                    themeData),
                _buildDetailRow('offense.detail.licensePlate'.tr,
                    offense.licensePlate ?? 'common.none'.tr, themeData),
                _buildDetailRow('offense.detail.driverName'.tr,
                    offense.driverName ?? 'common.none'.tr, themeData),
                _buildDetailRow('offense.detail.type'.tr,
                    offense.offenseType ?? 'common.unknown'.tr, themeData),
                _buildDetailRow('offense.detail.code'.tr,
                    offense.offenseCode ?? 'common.none'.tr, themeData),
                _buildDetailRow('offense.detail.points'.tr,
                    formatOffensePoints(offense.deductedPoints), themeData),
                _buildDetailRow('offense.detail.amount'.tr,
                    formatOffenseAmount(offense.fineAmount), themeData),
                _buildDetailRow(
                    'offense.detail.time'.tr,
                    formatOffenseDate(
                      offense.offenseTime,
                      emptyKey: 'common.notFilled',
                    ),
                    themeData),
                _buildDetailRow(
                    'offense.detail.location'.tr,
                    offense.offenseLocation ?? 'common.notFilled'.tr,
                    themeData),
                _buildDetailRow(
                    'offense.detail.processStatus'.tr,
                    formatUserOffenseProcessStatus(offense.processStatus),
                    themeData),
                _buildDetailRow('offense.detail.processResult'.tr,
                    offense.processResult ?? 'common.none'.tr, themeData),
              ],
            ),
          ),
        ),
      );
    });
  }
}
