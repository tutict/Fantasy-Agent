// ignore_for_file: use_build_context_synchronously
import 'dart:async';

import 'package:final_assignment_front/features/api/offense_information_controller_api.dart';
import 'package:final_assignment_front/features/api/payment_record_controller_api.dart';
import 'package:final_assignment_front/features/api/vehicle_information_controller_api.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:flutter/material.dart';
import 'package:final_assignment_front/features/dashboard/controllers/admin_dashboard_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/dashboard_page_template.dart';
import 'package:final_assignment_front/config/routes/app_routes.dart';
import 'package:final_assignment_front/features/api/fine_information_controller_api.dart';
import 'package:final_assignment_front/features/model/fine_information.dart';
import 'package:final_assignment_front/features/model/payment_record.dart';
import 'package:final_assignment_front/i18n/fine_localizers.dart';
import 'package:final_assignment_front/i18n/status_localizers.dart';
import 'package:final_assignment_front/utils/helpers/payment_review_helper.dart';
import 'package:get/get.dart';
import 'package:jwt_decoder/jwt_decoder.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:final_assignment_front/utils/helpers/role_utils.dart';
import 'package:final_assignment_front/utils/services/session_helper.dart';

/// Generates a unique idempotency key.
String generateIdempotencyKey() {
  return DateTime.now().millisecondsSinceEpoch.toString();
}

/// Fine list page for privileged operators.
class FineList extends StatefulWidget {
  const FineList({super.key});

  @override
  State<FineList> createState() => _FineListState();
}

class _FineListState extends State<FineList> {
  static const Duration _reviewTaskOverdueThreshold = Duration(hours: 24);
  static const String _reviewQueueFilterAll = 'all';
  static const String _reviewQueueFilterOverdue = 'overdue';
  static const String _reviewQueueFilterMissingProof = 'missingProof';
  static const String _reviewQueueFilterNeedProof = 'needProof';
  static const String _reviewQueueSortPending = 'pending';
  static const String _reviewQueueSortAmount = 'amount';

  final FineInformationControllerApi fineApi = FineInformationControllerApi();
  final PaymentRecordControllerApi paymentApi = PaymentRecordControllerApi();
  final SessionHelper _sessionHelper = SessionHelper();
  final TextEditingController _searchController = TextEditingController();
  TextEditingController? _searchFieldController;
  final List<FineInformation> _fineList = [];
  List<PaymentRecordModel> _reviewTasks = [];
  final Set<int> _selectedReviewTaskIds = <int>{};
  List<FineInformation> _cachedFineList = [];
  List<FineInformation> _filteredFineList = [];
  String _searchType = kFineSearchTypePayee;
  String _reviewQueueFilter = _reviewQueueFilterAll;
  String _reviewQueueSort = _reviewQueueSortPending;
  String _activeQuery = '';
  int _currentPage = 1;
  final int _pageSize = 20;
  bool _hasMore = true;
  bool _isLoading = false;
  bool _isLoadingReviewTasks = false;
  bool _isSubmittingBatchReview = false;
  String _errorMessage = '';
  String _reviewTaskErrorMessage = '';
  bool _isAdmin = false;
  bool _canAccessPaymentReviewQueue = false;
  bool _needsRelogin = false;
  bool _hasRecoverableLoadError = false;
  DateTime? _startDate;
  DateTime? _endDate;
  Timer? _searchDebounce;
  final DashboardController controller = Get.find<DashboardController>();
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();
    _searchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<bool> _validateJwtToken() async {
    String? jwtToken = (await AuthTokenStore.instance.getJwtToken());
    if (jwtToken == null || jwtToken.isEmpty) {
      setState(() {
        _errorMessage = 'fineAdmin.error.unauthorized'.tr;
        _needsRelogin = true;
      });
      return false;
    }
    try {
      if (JwtDecoder.isExpired(jwtToken)) {
        jwtToken = await _refreshJwtToken();
        if (jwtToken == null) {
          setState(() {
            _errorMessage = 'fineAdmin.error.expired'.tr;
            _needsRelogin = true;
          });
          return false;
        }
        await AuthTokenStore.instance.setJwtToken(jwtToken);
        if (JwtDecoder.isExpired(jwtToken)) {
          setState(() {
            _errorMessage = 'fineAdmin.error.refreshedExpired'.tr;
            _needsRelogin = true;
          });
          return false;
        }
        await fineApi.initializeWithJwt();
      }
      if (_needsRelogin || _errorMessage == 'fineAdmin.error.invalidLogin'.tr) {
        setState(() => _needsRelogin = false);
      }
      return true;
    } catch (e) {
      setState(() {
        _errorMessage = 'fineAdmin.error.invalidLogin'.tr;
        _needsRelogin = true;
      });
      return false;
    }
  }

  Future<String?> _refreshJwtToken() async {
    return await _sessionHelper.refreshJwtToken();
  }

  Future<void> _initialize() async {
    setState(() => _isLoading = true);
    try {
      if (!await _validateJwtToken()) {
        Navigator.pushReplacementNamed(context, Routes.login);
        return;
      }
      await fineApi.initializeWithJwt();
      await paymentApi.initializeWithJwt();
      final jwtToken = (await AuthTokenStore.instance.getJwtToken())!;
      final decodedToken = JwtDecoder.decode(jwtToken);
      _isAdmin = hasAnyRole(decodedToken['roles'], const [
        'SUPER_ADMIN',
        'ADMIN',
        'TRAFFIC_POLICE',
        'FINANCE',
      ]);
      _canAccessPaymentReviewQueue = hasAnyRole(decodedToken['roles'], const [
        'SUPER_ADMIN',
        'ADMIN',
        'FINANCE',
      ]);
      if (!_isAdmin) {
        setState(() {
          _errorMessage = 'fineAdmin.error.adminOnly'.tr;
          _needsRelogin = true;
        });
        return;
      }
      if (_canAccessPaymentReviewQueue) {
        await _loadReviewTasks();
      }
      await _fetchFines(reset: true);
    } catch (e) {
      setState(() => _errorMessage = 'fineAdmin.error.initFailed'
          .trParams({'error': formatFineAdminError(e)}));
    } finally {
      setState(() => _isLoading = false);
    }
  }

  // ignore: unused_element
  Future<void> _checkUserRole() async {
    try {
      if (!await _validateJwtToken()) {
        Navigator.pushReplacementNamed(context, Routes.login);
        return;
      }
      final roles = await _sessionHelper.fetchCurrentRoles();
      setState(() => _isAdmin = hasAnyRole(roles, const [
            'SUPER_ADMIN',
            'ADMIN',
            'TRAFFIC_POLICE',
            'FINANCE',
          ]));
      if (!_isAdmin) {
        setState(() {
          _errorMessage = 'fineAdmin.error.adminOnly'.tr;
          _needsRelogin = true;
        });
      }
    } catch (e) {
      setState(() => _errorMessage = 'fineAdmin.error.roleCheckFailed'
          .trParams({'error': formatFineAdminError(e)}));
    }
  }

  Future<void> _fetchFines(
      {bool reset = false, String? query, int retries = 5}) async {
    if (!_isAdmin) return;

    if (reset) {
      _currentPage = 1;
      _hasMore = true;
      _activeQuery = (query ?? _searchController.text).trim();
      _cachedFineList = List<FineInformation>.from(_fineList);
      _fineList.clear();
      _filteredFineList.clear();
    }

    if (!_hasMore) return;

    setState(() {
      _isLoading = true;
      _errorMessage = '';
      _needsRelogin = false;
      _hasRecoverableLoadError = false;
    });

    try {
      if (!await _validateJwtToken()) {
        Navigator.pushReplacementNamed(context, Routes.login);
        return;
      }
      List<FineInformation> fines = [];
      for (int attempt = 1; attempt <= retries; attempt++) {
        try {
          fines = await _loadFinePage(
            page: _currentPage,
            query: _activeQuery,
          );
          break;
        } catch (e) {
          if (attempt == retries) {
            rethrow;
          }
          await Future.delayed(Duration(milliseconds: 1000 * attempt));
        }
      }

      setState(() {
        _fineList.addAll(fines);
        _hasMore = fines.length == _pageSize;
        _rebuildFilteredFineList();
        if (_filteredFineList.isEmpty) {
          _errorMessage = _hasActiveFilters
              ? 'fineAdmin.error.filteredEmpty'.tr
              : 'fineAdmin.empty.default'.tr;
        }
        _currentPage++;
        if (reset && _scrollController.hasClients) {
          _scrollController.animateTo(
            0,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeInOut,
          );
        }
      });
    } catch (e) {
      setState(() {
        if (e is ApiException && e.code == 403) {
          _errorMessage = 'fineAdmin.error.unauthorized'.tr;
          _needsRelogin = true;
          Navigator.pushReplacementNamed(context, Routes.login);
        } else if (e is ApiException && e.code == 404) {
          _errorMessage = 'fineAdmin.error.notFound'.tr;
          _hasMore = false;
        } else {
          _errorMessage = 'fineAdmin.error.loadFailed'.trParams({
            'error': '$e',
          });
          _hasRecoverableLoadError = true;
        }
        if (_cachedFineList.isNotEmpty) {
          _fineList.clear();
          _fineList.addAll(_cachedFineList);
          _rebuildFilteredFineList();
          _errorMessage = 'fineAdmin.error.loadLatestFallback'.tr;
          _hasRecoverableLoadError = true;
        }
      });
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<List<FineInformation>> _loadFinePage({
    required int page,
    required String query,
  }) async {
    if (_searchType == kFineSearchTypeTimeRange &&
        _startDate != null &&
        _endDate != null) {
      return fineApi.apiFinesTimeRangeGet(
        startDate: _startDate!.toIso8601String().split('T').first,
        endDate: _endDate!.toIso8601String().split('T').first,
        page: page,
        size: _pageSize,
      );
    }

    if (query.isNotEmpty) {
      return fineApi.apiFinesPayeePayeeGet(
        payee: query,
        mode: 'fuzzy',
        page: page,
        size: _pageSize,
      );
    }

    return fineApi.apiFinesGet(page: page, size: _pageSize);
  }

  Future<List<String>> _fetchAutocompleteSuggestions(String prefix) async {
    try {
      if (!await _validateJwtToken()) {
        Navigator.pushReplacementNamed(context, Routes.login);
        return [];
      }
      if (_searchType == kFineSearchTypePayee) {
        final fines = await fineApi.apiFinesPayeePayeeGet(
          payee: prefix.trim(),
          mode: 'prefix',
          page: 1,
          size: 5,
        );
        return fines
            .map((fine) => fine.payee ?? '')
            .where(
                (payee) => payee.toLowerCase().contains(prefix.toLowerCase()))
            .take(5)
            .toList();
      }
      return [];
    } catch (e) {
      setState(() => _errorMessage = 'fineAdmin.error.suggestionFailed'
          .trParams({'error': formatFineAdminError(e)}));
      return [];
    }
  }

  void _rebuildFilteredFineList() {
    final searchQuery = _activeQuery.trim().toLowerCase();
    _filteredFineList.clear();
    _filteredFineList = _fineList.where((fine) {
      final payee = (fine.payee ?? '').toLowerCase();
      final fineDate = resolveFineDisplayDate(fine.fineDate, fine.fineTime);

      bool matchesQuery = true;
      if (searchQuery.isNotEmpty && _searchType == kFineSearchTypePayee) {
        matchesQuery = payee.contains(searchQuery);
      }

      bool matchesDateRange = true;
      if (_startDate != null && _endDate != null) {
        if (fineDate == null) {
          matchesDateRange = false;
        } else {
          final inclusiveEnd = _endDate!.add(const Duration(days: 1));
          matchesDateRange = !fineDate.isBefore(_startDate!) &&
              fineDate.isBefore(inclusiveEnd);
        }
      }

      return matchesQuery && matchesDateRange;
    }).toList();

    if (_filteredFineList.isEmpty && _fineList.isNotEmpty) {
      _errorMessage = 'fineAdmin.error.filteredEmpty'.tr;
    } else {
      _errorMessage = _filteredFineList.isEmpty && _fineList.isEmpty
          ? 'fineAdmin.empty.default'.tr
          : '';
    }
  }

  // ignore: unused_element
  Future<void> _searchFines() async {
    await _refreshFines(query: _searchController.text.trim());
  }

  Future<void> _refreshFines({String? query}) async {
    _searchDebounce?.cancel();
    final effectiveQuery = (query ?? _searchController.text).trim();
    setState(() {
      _cachedFineList = List<FineInformation>.from(_fineList);
      _fineList.clear();
      _filteredFineList.clear();
      _currentPage = 1;
      _hasMore = true;
      _isLoading = true;
      _activeQuery = effectiveQuery;
      if (query == null) {
        _setSearchText('');
        _startDate = null;
        _endDate = null;
        _searchType = kFineSearchTypePayee;
      } else {
        _setSearchText(effectiveQuery);
      }
    });
    if (_canAccessPaymentReviewQueue) {
      await _loadReviewTasks();
    }
    await _fetchFines(reset: true, query: effectiveQuery);
    if (_errorMessage.isEmpty && _fineList.isNotEmpty) {
      _showSnackBar('fineAdmin.success.refreshed'.tr);
    }
  }

  Future<void> _loadMoreFines() async {
    if (!_isLoading && _hasMore) {
      await _fetchFines();
    }
  }

  bool get _hasActiveFilters =>
      _activeQuery.isNotEmpty || (_startDate != null && _endDate != null);

  void _setSearchText(String value) {
    final textValue = TextEditingValue(
      text: value,
      selection: TextSelection.collapsed(offset: value.length),
    );
    _searchController.value = textValue;
    _searchFieldController?.value = textValue;
  }

  void _scheduleSearchRefresh(String value) {
    _searchDebounce?.cancel();
    _searchDebounce = Timer(const Duration(milliseconds: 350), () {
      if (!mounted) return;
      _refreshFines(query: value);
    });
  }

  void _createFine() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => const AddFinePage()),
    ).then((value) {
      if (value == true) {
        _refreshFines();
      }
    });
  }

  void _goToDetailPage(FineInformation fine) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => FineDetailPage(fine: fine)),
    ).then((value) {
      if (value == true) {
        _refreshFines();
      }
      if (_canAccessPaymentReviewQueue) {
        _loadReviewTasks();
      }
    });
  }

  Future<void> _openFineFromReviewTask(PaymentRecordModel task) async {
    final fineId = task.fineId;
    if (fineId == null) {
      return;
    }
    try {
      final fine = await fineApi.apiFinesFineIdGet(fineId: fineId);
      if (!mounted) return;
      if (fine == null) {
        _showSnackBar(
          'fine.reviewQueue.openFailed'
              .trParams({'error': 'fineAdmin.error.notFound'.tr}),
          isError: true,
        );
        return;
      }
      _goToDetailPage(fine);
    } catch (e) {
      if (!mounted) return;
      _showSnackBar(
        'fine.reviewQueue.openFailed'
            .trParams({'error': formatFineAdminError(e)}),
        isError: true,
      );
    }
  }

  Future<void> _loadReviewTasks() async {
    if (!_canAccessPaymentReviewQueue) {
      return;
    }
    setState(() {
      _isLoadingReviewTasks = true;
      _reviewTaskErrorMessage = '';
    });
    try {
      final tasks = await paymentApi.apiPaymentsReviewTasksGet(size: 10);
      if (!mounted) return;
      setState(() {
        _reviewTasks = tasks;
        final visibleTaskIds = _buildVisibleReviewTasks(tasks: tasks)
            .map((task) => task.paymentId)
            .whereType<int>()
            .toSet();
        _selectedReviewTaskIds.removeWhere(
          (paymentId) => !visibleTaskIds.contains(paymentId),
        );
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _reviewTaskErrorMessage = 'fine.reviewQueue.loadFailed'
            .trParams({'error': formatFineAdminError(e)});
      });
    } finally {
      if (mounted) {
        setState(() => _isLoadingReviewTasks = false);
      }
    }
  }

  Widget _buildReviewTaskSection(ThemeData themeData) {
    if (!_canAccessPaymentReviewQueue) {
      return const SizedBox.shrink();
    }
    final visibleTasks = _buildVisibleReviewTasks();
    final selectableTaskIds =
        visibleTasks.map((task) => task.paymentId).whereType<int>().toSet();
    final hasSelection = _selectedReviewTaskIds.isNotEmpty;
    return Card(
      color: themeData.colorScheme.surfaceContainer,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'fine.reviewQueue.title'.tr,
                    style: themeData.textTheme.titleMedium?.copyWith(
                      color: themeData.colorScheme.onSurface,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                if (visibleTasks.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: Text(
                      'fine.reviewQueue.selectionHint'.trParams({
                        'count': '${_selectedReviewTaskIds.length}',
                      }),
                      style: themeData.textTheme.bodySmall?.copyWith(
                        color: themeData.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ),
                IconButton(
                  onPressed: _isLoadingReviewTasks ? null : _loadReviewTasks,
                  icon: Icon(
                    Icons.refresh,
                    color: themeData.colorScheme.primary,
                  ),
                  tooltip: 'fineAdmin.action.refresh'.tr,
                ),
              ],
            ),
            if (_reviewTasks.isNotEmpty) ...[
              Wrap(
                spacing: 8,
                runSpacing: 8,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  _buildReviewQueueFilterChip(
                    themeData,
                    value: _reviewQueueFilterAll,
                    labelKey: 'fine.reviewQueue.filter.all',
                  ),
                  _buildReviewQueueFilterChip(
                    themeData,
                    value: _reviewQueueFilterOverdue,
                    labelKey: 'fine.reviewQueue.filter.overdue',
                  ),
                  _buildReviewQueueFilterChip(
                    themeData,
                    value: _reviewQueueFilterMissingProof,
                    labelKey: 'fine.reviewQueue.filter.missingProof',
                  ),
                  _buildReviewQueueFilterChip(
                    themeData,
                    value: _reviewQueueFilterNeedProof,
                    labelKey: 'fine.reviewQueue.filter.needProof',
                  ),
                  SizedBox(
                    width: 170,
                    child: DropdownButtonFormField<String>(
                      initialValue: _reviewQueueSort,
                      decoration: InputDecoration(
                        isDense: true,
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 10,
                        ),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      items: [
                        DropdownMenuItem<String>(
                          value: _reviewQueueSortPending,
                          child: Text('fine.reviewQueue.sort.pending'.tr),
                        ),
                        DropdownMenuItem<String>(
                          value: _reviewQueueSortAmount,
                          child: Text('fine.reviewQueue.sort.amount'.tr),
                        ),
                      ],
                      onChanged: _isSubmittingBatchReview
                          ? null
                          : (value) {
                              if (value == null || value == _reviewQueueSort) {
                                return;
                              }
                              setState(() => _reviewQueueSort = value);
                            },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  OutlinedButton(
                    onPressed:
                        _isSubmittingBatchReview || selectableTaskIds.isEmpty
                            ? null
                            : () {
                                setState(() {
                                  _selectedReviewTaskIds
                                    ..clear()
                                    ..addAll(selectableTaskIds);
                                });
                              },
                    child: Text('fine.reviewQueue.selectAll'.tr),
                  ),
                  OutlinedButton(
                    onPressed: _isSubmittingBatchReview || !hasSelection
                        ? null
                        : () => setState(_selectedReviewTaskIds.clear),
                    child: Text('fine.reviewQueue.clearSelection'.tr),
                  ),
                  FilledButton.tonal(
                    onPressed: _isSubmittingBatchReview || !hasSelection
                        ? null
                        : _showBatchNeedProofDialog,
                    child: Text('fine.reviewQueue.batchNeedProof'.tr),
                  ),
                  FilledButton(
                    onPressed: _isSubmittingBatchReview || !hasSelection
                        ? null
                        : _submitBatchApproveReviewTasks,
                    child: Text('fine.reviewQueue.batchApprove'.tr),
                  ),
                ],
              ),
            ],
            if (_isLoadingReviewTasks)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 12),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_reviewTaskErrorMessage.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  _reviewTaskErrorMessage,
                  style: themeData.textTheme.bodyMedium?.copyWith(
                    color: themeData.colorScheme.error,
                  ),
                ),
              )
            else if (_reviewTasks.isEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  'fine.reviewQueue.empty'.tr,
                  style: themeData.textTheme.bodyMedium?.copyWith(
                    color: themeData.colorScheme.onSurfaceVariant,
                  ),
                ),
              )
            else if (visibleTasks.isEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  'fine.reviewQueue.filteredEmpty'.tr,
                  style: themeData.textTheme.bodyMedium?.copyWith(
                    color: themeData.colorScheme.onSurfaceVariant,
                  ),
                ),
              )
            else
              ...visibleTasks.map(
                (task) {
                  final taskId = task.paymentId;
                  final financeReview =
                      parseLatestFinancePaymentReview(task.remarks);
                  final taskAnchor =
                      _resolveReviewTaskAnchor(task, financeReview);
                  final isOverdue = _isReviewTaskOverdue(task, financeReview);
                  final isSelected =
                      taskId != null && _selectedReviewTaskIds.contains(taskId);
                  return Card(
                    margin: const EdgeInsets.only(top: 12),
                    color: isOverdue
                        ? themeData.colorScheme.errorContainer
                        : themeData.colorScheme.surfaceContainerLowest,
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Checkbox(
                                value: isSelected,
                                onChanged: taskId == null ||
                                        _isSubmittingBatchReview
                                    ? null
                                    : (selected) {
                                        setState(() {
                                          if (selected == true) {
                                            _selectedReviewTaskIds.add(taskId);
                                          } else {
                                            _selectedReviewTaskIds
                                                .remove(taskId);
                                          }
                                        });
                                      },
                              ),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      'fine.paymentHistory.recordTitle'
                                          .trParams({
                                        'amount': (task.paymentAmount ?? 0)
                                            .toStringAsFixed(2),
                                      }),
                                      style: themeData.textTheme.titleSmall
                                          ?.copyWith(
                                        fontWeight: FontWeight.w600,
                                        color: isOverdue
                                            ? themeData
                                                .colorScheme.onErrorContainer
                                            : themeData.colorScheme.onSurface,
                                      ),
                                    ),
                                    const SizedBox(height: 6),
                                    Wrap(
                                      spacing: 8,
                                      runSpacing: 8,
                                      crossAxisAlignment:
                                          WrapCrossAlignment.center,
                                      children: [
                                        Text(
                                          'fine.reviewQueue.recordSubtitle'
                                              .trParams({
                                            'fineId': '${task.fineId ?? '-'}',
                                            'status': localizePaymentStatus(
                                                task.paymentStatus),
                                            'channel': task.paymentChannel ??
                                                'common.none'.tr,
                                          }),
                                          style: themeData.textTheme.bodyMedium
                                              ?.copyWith(
                                            color: isOverdue
                                                ? themeData.colorScheme
                                                    .onErrorContainer
                                                : themeData.colorScheme
                                                    .onSurfaceVariant,
                                          ),
                                        ),
                                        if (isOverdue)
                                          Container(
                                            padding: const EdgeInsets.symmetric(
                                              horizontal: 8,
                                              vertical: 4,
                                            ),
                                            decoration: BoxDecoration(
                                              color: themeData.colorScheme.error
                                                  .withValues(alpha: 0.12),
                                              borderRadius:
                                                  BorderRadius.circular(999),
                                            ),
                                            child: Text(
                                              'fine.reviewQueue.overdueBadge'
                                                  .tr,
                                              style: themeData
                                                  .textTheme.bodySmall
                                                  ?.copyWith(
                                                color:
                                                    themeData.colorScheme.error,
                                                fontWeight: FontWeight.w700,
                                              ),
                                            ),
                                          ),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          if (taskAnchor != null)
                            Padding(
                              padding: const EdgeInsets.only(top: 4),
                              child: Text(
                                'fine.reviewQueue.pendingSince'.trParams({
                                  'time': _formatReviewTaskAge(taskAnchor),
                                }),
                                style: themeData.textTheme.bodySmall?.copyWith(
                                  color: isOverdue
                                      ? themeData.colorScheme.onErrorContainer
                                      : themeData.colorScheme.onSurfaceVariant,
                                ),
                              ),
                            ),
                          const SizedBox(height: 8),
                          if ((task.transactionId ?? '').trim().isNotEmpty)
                            Text(
                              'common.labelWithColon'.trParams({
                                    'label':
                                        'fine.paymentHistory.transactionId'.tr,
                                  }) +
                                  task.transactionId!,
                              style: themeData.textTheme.bodyMedium?.copyWith(
                                color: isOverdue
                                    ? themeData.colorScheme.onErrorContainer
                                    : themeData.colorScheme.onSurface,
                              ),
                            ),
                          if ((task.receiptUrl ?? '').trim().isNotEmpty)
                            Text(
                              'common.labelWithColon'.trParams({
                                    'label':
                                        'fine.paymentHistory.receiptUrl'.tr,
                                  }) +
                                  task.receiptUrl!,
                              style: themeData.textTheme.bodyMedium?.copyWith(
                                color: isOverdue
                                    ? themeData.colorScheme.onErrorContainer
                                    : themeData.colorScheme.onSurface,
                              ),
                            )
                          else
                            Padding(
                              padding: const EdgeInsets.only(top: 4),
                              child: Text(
                                'fine.paymentHistory.missingProofHint'.tr,
                                style: themeData.textTheme.bodyMedium?.copyWith(
                                  color: themeData.colorScheme.error,
                                ),
                              ),
                            ),
                          const SizedBox(height: 10),
                          Align(
                            alignment: Alignment.centerRight,
                            child: FilledButton(
                              onPressed: () => _openFineFromReviewTask(task),
                              child: Text('fine.reviewQueue.openFine'.tr),
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
          ],
        ),
      ),
    );
  }

  DateTime? _resolveReviewTaskAnchor(
    PaymentRecordModel task,
    FinancePaymentReview? review,
  ) {
    if (review?.reviewResult == 'NEED_PROOF' && review?.reviewTime != null) {
      return review!.reviewTime;
    }
    return task.updatedAt ?? task.paymentTime ?? task.createdAt;
  }

  List<PaymentRecordModel> _buildVisibleReviewTasks({
    List<PaymentRecordModel>? tasks,
    String? filter,
    String? sort,
  }) {
    final selectedFilter = filter ?? _reviewQueueFilter;
    final selectedSort = sort ?? _reviewQueueSort;
    final filteredTasks = (tasks ?? _reviewTasks).where((task) {
      final review = parseLatestFinancePaymentReview(task.remarks);
      switch (selectedFilter) {
        case _reviewQueueFilterOverdue:
          return _isReviewTaskOverdue(task, review);
        case _reviewQueueFilterMissingProof:
          return (task.receiptUrl ?? '').trim().isEmpty;
        case _reviewQueueFilterNeedProof:
          return review?.reviewResult == 'NEED_PROOF';
        case _reviewQueueFilterAll:
        default:
          return true;
      }
    }).toList();

    filteredTasks.sort((left, right) {
      if (selectedSort == _reviewQueueSortAmount) {
        final amountCompare =
            (right.paymentAmount ?? 0).compareTo(left.paymentAmount ?? 0);
        if (amountCompare != 0) {
          return amountCompare;
        }
      }
      final leftAnchor = _resolveReviewTaskAnchor(
        left,
        parseLatestFinancePaymentReview(left.remarks),
      );
      final rightAnchor = _resolveReviewTaskAnchor(
        right,
        parseLatestFinancePaymentReview(right.remarks),
      );
      if (leftAnchor == null && rightAnchor == null) {
        return 0;
      }
      if (leftAnchor == null) {
        return 1;
      }
      if (rightAnchor == null) {
        return -1;
      }
      return rightAnchor.compareTo(leftAnchor);
    });
    return filteredTasks;
  }

  Widget _buildReviewQueueFilterChip(
    ThemeData themeData, {
    required String value,
    required String labelKey,
  }) {
    return ChoiceChip(
      label: Text(labelKey.tr),
      selected: _reviewQueueFilter == value,
      onSelected: _isSubmittingBatchReview
          ? null
          : (selected) {
              if (!selected || value == _reviewQueueFilter) {
                return;
              }
              final visibleTaskIds = _buildVisibleReviewTasks(
                tasks: _reviewTasks,
                filter: value,
              ).map((task) => task.paymentId).whereType<int>().toSet();
              setState(() {
                _reviewQueueFilter = value;
                _selectedReviewTaskIds.removeWhere(
                  (paymentId) => !visibleTaskIds.contains(paymentId),
                );
              });
            },
      selectedColor: themeData.colorScheme.secondaryContainer,
      labelStyle: themeData.textTheme.bodyMedium?.copyWith(
        color: _reviewQueueFilter == value
            ? themeData.colorScheme.onSecondaryContainer
            : themeData.colorScheme.onSurfaceVariant,
      ),
      side: BorderSide(color: themeData.colorScheme.outlineVariant),
    );
  }

  bool _isReviewTaskOverdue(
    PaymentRecordModel task,
    FinancePaymentReview? review,
  ) {
    final anchor = _resolveReviewTaskAnchor(task, review);
    if (anchor == null) {
      return false;
    }
    return anchor
        .add(_reviewTaskOverdueThreshold)
        .isBefore(DateTime.now().toLocal());
  }

  String _formatReviewTaskAge(DateTime anchor) {
    final duration = DateTime.now().toLocal().difference(anchor);
    if (duration.inHours < 24) {
      final hours = duration.inHours <= 0 ? 1 : duration.inHours;
      return 'fine.reviewQueue.pendingHours'.trParams({
        'hours': '$hours',
      });
    }
    final days = duration.inDays <= 0 ? 1 : duration.inDays;
    return 'fine.reviewQueue.pendingDays'.trParams({
      'days': '$days',
    });
  }

  Future<void> _submitBatchApproveReviewTasks() async {
    final selectedIds = _selectedReviewTaskIds.toList(growable: false);
    if (selectedIds.isEmpty) {
      return;
    }
    setState(() => _isSubmittingBatchReview = true);
    try {
      for (final paymentId in selectedIds) {
        await paymentApi.apiPaymentsPaymentIdFinanceReviewPost(
          paymentId: paymentId,
          reviewResult: 'APPROVED',
          idempotencyKey: generateIdempotencyKey(),
        );
      }
      if (!mounted) return;
      setState(_selectedReviewTaskIds.clear);
      _showSnackBar(
        'fine.reviewQueue.batchApproveSuccess'.trParams({
          'count': '${selectedIds.length}',
        }),
      );
      await _loadReviewTasks();
    } catch (e) {
      if (!mounted) return;
      _showSnackBar(
        'fine.reviewQueue.batchApproveFailed'
            .trParams({'error': formatFineAdminError(e)}),
        isError: true,
      );
    } finally {
      if (mounted) {
        setState(() => _isSubmittingBatchReview = false);
      }
    }
  }

  Future<void> _showBatchNeedProofDialog() async {
    if (_selectedReviewTaskIds.isEmpty || _isSubmittingBatchReview) {
      return;
    }
    final opinionController = TextEditingController();
    try {
      final opinion = await showDialog<String>(
        context: context,
        builder: (dialogContext) {
          final themeData = controller.currentBodyTheme.value;
          return AlertDialog(
            title: Text('fine.paymentReview.dialog.needProofTitle'.tr),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'fine.paymentReview.dialog.needProofHint'.tr,
                  style: themeData.textTheme.bodyMedium,
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: opinionController,
                  maxLines: 3,
                  decoration: InputDecoration(
                    labelText: 'fine.paymentReview.opinion'.tr,
                    border: const OutlineInputBorder(),
                  ),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(dialogContext).pop(),
                child: Text('common.cancel'.tr),
              ),
              FilledButton(
                onPressed: () {
                  final normalized = opinionController.text.trim();
                  if (normalized.isEmpty) {
                    _showSnackBar(
                      'fine.paymentReview.validation.opinionRequired'.tr,
                      isError: true,
                    );
                    return;
                  }
                  Navigator.of(dialogContext).pop(normalized);
                },
                child: Text('common.submit'.tr),
              ),
            ],
          );
        },
      );
      if (opinion == null || opinion.trim().isEmpty) {
        return;
      }
      await _submitBatchNeedProofReviewTasks(opinion);
    } finally {
      opinionController.dispose();
    }
  }

  Future<void> _submitBatchNeedProofReviewTasks(String opinion) async {
    final selectedIds = _selectedReviewTaskIds.toList(growable: false);
    if (selectedIds.isEmpty) {
      return;
    }
    setState(() => _isSubmittingBatchReview = true);
    try {
      for (final paymentId in selectedIds) {
        await paymentApi.apiPaymentsPaymentIdFinanceReviewPost(
          paymentId: paymentId,
          reviewResult: 'NEED_PROOF',
          reviewOpinion: opinion,
          idempotencyKey: generateIdempotencyKey(),
        );
      }
      if (!mounted) return;
      setState(_selectedReviewTaskIds.clear);
      _showSnackBar(
        'fine.reviewQueue.batchNeedProofSuccess'.trParams({
          'count': '${selectedIds.length}',
        }),
      );
      await _loadReviewTasks();
    } catch (e) {
      if (!mounted) return;
      _showSnackBar(
        'fine.reviewQueue.batchNeedProofFailed'
            .trParams({'error': formatFineAdminError(e)}),
        isError: true,
      );
    } finally {
      if (mounted) {
        setState(() => _isSubmittingBatchReview = false);
      }
    }
  }

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

  Widget _buildSearchField(ThemeData themeData) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: Autocomplete<String>(
                  optionsBuilder: (TextEditingValue textEditingValue) async {
                    if (textEditingValue.text.isEmpty ||
                        _searchType != kFineSearchTypePayee) {
                      return const Iterable<String>.empty();
                    }
                    return await _fetchAutocompleteSuggestions(
                        textEditingValue.text);
                  },
                  onSelected: (String selection) {
                    _setSearchText(selection);
                    _refreshFines(query: selection);
                  },
                  fieldViewBuilder:
                      (context, controller, focusNode, onFieldSubmitted) {
                    _searchFieldController = controller;
                    if (controller.text != _searchController.text) {
                      controller.value = _searchController.value;
                    }
                    return TextField(
                      controller: controller,
                      focusNode: focusNode,
                      style: TextStyle(color: themeData.colorScheme.onSurface),
                      decoration: InputDecoration(
                        hintText: fineSearchHintText(_searchType),
                        hintStyle: TextStyle(
                            color: themeData.colorScheme.onSurface
                                .withValues(alpha: 0.6)),
                        prefixIcon: Icon(Icons.search,
                            color: themeData.colorScheme.primary),
                        suffixIcon: controller.text.isNotEmpty ||
                                (_startDate != null && _endDate != null)
                            ? IconButton(
                                icon: Icon(Icons.clear,
                                    color:
                                        themeData.colorScheme.onSurfaceVariant),
                                onPressed: () {
                                  setState(() {
                                    _startDate = null;
                                    _endDate = null;
                                    _searchType = kFineSearchTypePayee;
                                  });
                                  _setSearchText('');
                                  _refreshFines(query: '');
                                },
                              )
                            : null,
                        border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12.0)),
                        enabledBorder: OutlineInputBorder(
                          borderSide: BorderSide(
                              color: themeData.colorScheme.outline
                                  .withValues(alpha: 0.3)),
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderSide: BorderSide(
                              color: themeData.colorScheme.primary, width: 1.5),
                        ),
                        filled: true,
                        fillColor: themeData.colorScheme.surfaceContainerLowest,
                        contentPadding: const EdgeInsets.symmetric(
                            vertical: 12.0, horizontal: 16.0),
                      ),
                      onChanged: (value) {
                        _setSearchText(value);
                        _scheduleSearchRefresh(value);
                      },
                      onSubmitted: (value) {
                        _setSearchText(value);
                        _refreshFines(query: value);
                      },
                      enabled: _searchType == kFineSearchTypePayee,
                    );
                  },
                ),
              ),
              const SizedBox(width: 8),
              DropdownButton<String>(
                value: _searchType,
                onChanged: (String? newValue) {
                  setState(() {
                    _searchType = newValue!;
                    _startDate = null;
                    _endDate = null;
                  });
                  _setSearchText('');
                  _refreshFines(query: '');
                },
                items: <String>[
                  kFineSearchTypePayee,
                  kFineSearchTypeTimeRange,
                ].map<DropdownMenuItem<String>>((String value) {
                  return DropdownMenuItem<String>(
                    value: value,
                    child: Text(
                      fineSearchTypeLabel(value),
                      style: TextStyle(color: themeData.colorScheme.onSurface),
                    ),
                  );
                }).toList(),
                dropdownColor: themeData.colorScheme.surfaceContainer,
                icon: Icon(Icons.arrow_drop_down,
                    color: themeData.colorScheme.primary),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: Text(
                  _startDate != null && _endDate != null
                      ? 'fineAdmin.filter.dateRangeLabel'.trParams({
                          'start': formatFineVisibleDate(_startDate),
                          'end': formatFineVisibleDate(_endDate),
                        })
                      : 'fineAdmin.filter.selectDateRange'.tr,
                  style: themeData.textTheme.bodyMedium?.copyWith(
                    color: _startDate != null && _endDate != null
                        ? themeData.colorScheme.onSurface
                        : themeData.colorScheme.onSurfaceVariant,
                  ),
                ),
              ),
              IconButton(
                icon: Icon(Icons.date_range,
                    color: themeData.colorScheme.primary),
                tooltip: 'fineAdmin.filter.tooltip'.tr,
                onPressed: () async {
                  final range = await showDateRangePicker(
                    context: context,
                    firstDate: DateTime(1900),
                    lastDate: DateTime.now(),
                    locale: Get.locale ?? const Locale('en', 'US'),
                    helpText: 'fineAdmin.filter.selectDateRange'.tr,
                    cancelText: 'common.cancel'.tr,
                    confirmText: 'common.confirm'.tr,
                    fieldStartHintText: 'fineAdmin.filter.startDate'.tr,
                    fieldEndHintText: 'fineAdmin.filter.endDate'.tr,
                    builder: (BuildContext context, Widget? child) {
                      return Theme(
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
                      );
                    },
                  );
                  if (range != null) {
                    setState(() {
                      _startDate = range.start;
                      _endDate = range.end;
                      _searchType = kFineSearchTypeTimeRange;
                    });
                    _refreshFines(query: _searchController.text);
                  }
                },
              ),
              if (_startDate != null && _endDate != null)
                IconButton(
                  icon: Icon(Icons.clear,
                      color: themeData.colorScheme.onSurfaceVariant),
                  tooltip: 'fineAdmin.filter.clearDateRange'.tr,
                  onPressed: () {
                    setState(() {
                      _startDate = null;
                      _endDate = null;
                      _searchType = kFineSearchTypePayee;
                    });
                    _refreshFines(query: _searchController.text);
                  },
                ),
            ],
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
        title: 'fineAdmin.page.title'.tr,
        pageType: DashboardPageType.admin,
        bodyIsScrollable: true,
        padding: EdgeInsets.zero,
        actions: [
          if (_isAdmin) ...[
            DashboardPageBarAction(
              icon: Icons.add,
              onPressed: _createFine,
              tooltip: 'fineAdmin.action.add'.tr,
            ),
            DashboardPageBarAction(
              icon: Icons.refresh,
              onPressed: () => _refreshFines(),
              tooltip: 'fineAdmin.action.refresh'.tr,
            ),
          ],
        ],
        onThemeToggle: controller.toggleBodyTheme,
        body: RefreshIndicator(
          onRefresh: () => _refreshFines(),
          color: themeData.colorScheme.primary,
          backgroundColor: themeData.colorScheme.surfaceContainer,
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              children: [
                const SizedBox(height: 12),
                _buildSearchField(themeData),
                const SizedBox(height: 12),
                _buildReviewTaskSection(themeData),
                if (_canAccessPaymentReviewQueue) const SizedBox(height: 12),
                Expanded(
                  child: NotificationListener<ScrollNotification>(
                    onNotification: (scrollInfo) {
                      if (scrollInfo.metrics.pixels ==
                              scrollInfo.metrics.maxScrollExtent &&
                          _hasMore) {
                        _loadMoreFines();
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
                        : _errorMessage.isNotEmpty && _filteredFineList.isEmpty
                            ? Center(
                                child: Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Text(
                                      _errorMessage,
                                      style: themeData.textTheme.titleMedium
                                          ?.copyWith(
                                        color: themeData.colorScheme.error,
                                        fontWeight: FontWeight.w500,
                                      ),
                                      textAlign: TextAlign.center,
                                    ),
                                    if (_hasRecoverableLoadError)
                                      Padding(
                                        padding:
                                            const EdgeInsets.only(top: 16.0),
                                        child: ElevatedButton(
                                          onPressed: () => _refreshFines(),
                                          style: ElevatedButton.styleFrom(
                                            backgroundColor:
                                                themeData.colorScheme.primary,
                                            foregroundColor:
                                                themeData.colorScheme.onPrimary,
                                          ),
                                          child:
                                              Text('fineAdmin.action.retry'.tr),
                                        ),
                                      ),
                                    if (_hasRecoverableLoadError &&
                                        _cachedFineList.isNotEmpty)
                                      Padding(
                                        padding:
                                            const EdgeInsets.only(top: 16.0),
                                        child: ElevatedButton(
                                          onPressed: () {
                                            setState(() {
                                              _fineList.clear();
                                              _fineList.addAll(_cachedFineList);
                                              _rebuildFilteredFineList();
                                              _errorMessage = '';
                                            });
                                          },
                                          style: ElevatedButton.styleFrom(
                                            backgroundColor:
                                                themeData.colorScheme.secondary,
                                            foregroundColor: themeData
                                                .colorScheme.onSecondary,
                                          ),
                                          child: Text(
                                              'fineAdmin.action.restoreCache'
                                                  .tr),
                                        ),
                                      ),
                                    if (_needsRelogin ||
                                        shouldShowFineAdminReloginAction(
                                            _errorMessage))
                                      Padding(
                                        padding:
                                            const EdgeInsets.only(top: 16.0),
                                        child: ElevatedButton(
                                          onPressed: () =>
                                              Navigator.pushReplacementNamed(
                                                  context, Routes.login),
                                          style: ElevatedButton.styleFrom(
                                            backgroundColor:
                                                themeData.colorScheme.primary,
                                            foregroundColor:
                                                themeData.colorScheme.onPrimary,
                                          ),
                                          child: Text(
                                              'fineAdmin.action.relogin'.tr),
                                        ),
                                      ),
                                  ],
                                ),
                              )
                            : ListView.builder(
                                controller: _scrollController,
                                itemCount: _filteredFineList.length +
                                    (_hasMore ? 1 : 0),
                                itemBuilder: (context, index) {
                                  if (index == _filteredFineList.length &&
                                      _hasMore) {
                                    return const Padding(
                                      padding: EdgeInsets.all(8.0),
                                      child: Center(
                                          child: CircularProgressIndicator()),
                                    );
                                  }
                                  final fijne = _filteredFineList[index];
                                  return Card(
                                    margin: const EdgeInsets.symmetric(
                                        vertical: 8.0),
                                    elevation: 3,
                                    color:
                                        themeData.colorScheme.surfaceContainer,
                                    shape: RoundedRectangleBorder(
                                        borderRadius:
                                            BorderRadius.circular(16.0)),
                                    child: ListTile(
                                      contentPadding:
                                          const EdgeInsets.symmetric(
                                              horizontal: 16.0, vertical: 12.0),
                                      title: Text(
                                        'fineAdmin.card.amount'.trParams({
                                          'amount': '${fijne.fineAmount ?? 0}',
                                        }),
                                        style: themeData.textTheme.titleMedium
                                            ?.copyWith(
                                          color:
                                              themeData.colorScheme.onSurface,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                      subtitle: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          const SizedBox(height: 4),
                                          Text(
                                            'fineAdmin.card.payee'.trParams({
                                              'value': fijne.payee ??
                                                  'common.unknown'.tr,
                                            }),
                                            style: themeData
                                                .textTheme.bodyMedium
                                                ?.copyWith(
                                              color: themeData
                                                  .colorScheme.onSurfaceVariant,
                                            ),
                                          ),
                                          Text(
                                            'fineAdmin.card.time'.trParams({
                                              'value': formatFineVisibleDate(
                                                resolveFineDisplayDate(
                                                  fijne.fineDate,
                                                  fijne.fineTime,
                                                ),
                                              ),
                                            }),
                                            style: themeData
                                                .textTheme.bodyMedium
                                                ?.copyWith(
                                              color: themeData
                                                  .colorScheme.onSurfaceVariant,
                                            ),
                                          ),
                                          Text(
                                            'fineAdmin.card.status'.trParams({
                                              'value': localizeAdminFineStatus(
                                                fijne.status,
                                                emptyKey:
                                                    'common.status.processing',
                                              ),
                                            }),
                                            style: themeData
                                                .textTheme.bodyMedium
                                                ?.copyWith(
                                              color: themeData
                                                  .colorScheme.onSurfaceVariant,
                                            ),
                                          ),
                                        ],
                                      ),
                                      trailing: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Icon(
                                            Icons.arrow_forward_ios,
                                            color: themeData
                                                .colorScheme.onSurfaceVariant,
                                            size: 18,
                                          ),
                                        ],
                                      ),
                                      onTap: () => _goToDetailPage(fijne),
                                    ),
                                  );
                                },
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

class AddFinePage extends StatefulWidget {
  final FineInformation? fine;
  final bool isEditMode;

  const AddFinePage({super.key, this.fine, this.isEditMode = false});

  @override
  State<AddFinePage> createState() => _AddFinePageState();
}

class _AddFinePageState extends State<AddFinePage> {
  final FineInformationControllerApi fineApi = FineInformationControllerApi();
  final OffenseInformationControllerApi offenseApi =
      OffenseInformationControllerApi();
  final VehicleInformationControllerApi vehicleApi =
      VehicleInformationControllerApi();
  final _formKey = GlobalKey<FormState>();
  final _plateNumberController = TextEditingController();
  final _fineAmountController = TextEditingController();
  final _payeeController = TextEditingController();
  final _accountNumberController = TextEditingController();
  final _bankController = TextEditingController();
  final _receiptNumberController = TextEditingController();
  final _remarksController = TextEditingController();
  final _dateController = TextEditingController();
  bool _isLoading = false;
  final DashboardController controller = Get.find<DashboardController>();
  int? _selectedOffenseId;
  DateTime? _selectedFineDate;

  @override
  void initState() {
    super.initState();
    if (widget.isEditMode && widget.fine != null) {
      _prepopulateFields(widget.fine!);
    }
    _initialize();
  }

  void _prepopulateFields(FineInformation fine) {
    _plateNumberController.text =
        ''; // Plate number not stored in FineInformation
    _fineAmountController.text = fine.fineAmount?.toString() ?? '';
    _payeeController.text = fine.payee ?? '';
    _accountNumberController.text = fine.accountNumber ?? '';
    _bankController.text = fine.bank ?? '';
    _receiptNumberController.text = fine.receiptNumber ?? '';
    _remarksController.text = fine.remarks ?? '';
    _setFineDate(resolveFineDisplayDate(fine.fineDate, fine.fineTime));
    _selectedOffenseId = fine.offenseId;
  }

  void _setFineDate(DateTime? value) {
    _selectedFineDate = value == null ? null : DateUtils.dateOnly(value);
    _dateController.text =
        _selectedFineDate == null ? '' : formatFineAdminDate(_selectedFineDate);
  }

  Future<bool> _validateJwtToken() async {
    final jwtToken = (await AuthTokenStore.instance.getJwtToken());
    if (jwtToken == null || jwtToken.isEmpty) {
      _showSnackBar('fineAdmin.error.unauthorized'.tr, isError: true);
      return false;
    }
    try {
      if (JwtDecoder.isExpired(jwtToken)) {
        _showSnackBar('fineAdmin.error.expired'.tr, isError: true);
        return false;
      }
      return true;
    } catch (e) {
      _showSnackBar('fineAdmin.error.invalidLogin'.tr, isError: true);
      return false;
    }
  }

  Future<void> _initialize() async {
    setState(() => _isLoading = true);
    try {
      if (!await _validateJwtToken()) {
        Navigator.pushReplacementNamed(context, Routes.login);
        return;
      }
      await fineApi.initializeWithJwt();
      await offenseApi.initializeWithJwt();
      await vehicleApi.initializeWithJwt();
    } catch (e) {
      _showSnackBar(
        'fineAdmin.error.initFailed'
            .trParams({'error': formatFineAdminError(e)}),
        isError: true,
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  void dispose() {
    _plateNumberController.dispose();
    _fineAmountController.dispose();
    _payeeController.dispose();
    _accountNumberController.dispose();
    _bankController.dispose();
    _receiptNumberController.dispose();
    _remarksController.dispose();
    _dateController.dispose();
    super.dispose();
  }

  Future<List<String>> _fetchLicensePlateSuggestions(String prefix) async {
    try {
      if (!await _validateJwtToken()) {
        Navigator.pushReplacementNamed(context, Routes.login);
        return [];
      }
      return await vehicleApi.apiVehiclesSearchLicenseGlobalGet(
        prefix: prefix,
        size: 10,
      );
    } catch (e) {
      _showSnackBar(
        'fineAdmin.error.fetchPlateSuggestionsFailed'
            .trParams({'error': formatFineAdminError(e)}),
        isError: true,
      );
      return [];
    }
  }

  Future<List<Map<String, dynamic>>> _fetchPayeeSuggestions(
      String prefix) async {
    try {
      if (!await _validateJwtToken()) {
        Navigator.pushReplacementNamed(context, Routes.login);
        return [];
      }
      if (prefix.trim().isEmpty) return [];
      final offenses = await offenseApi.apiOffensesByDriverNameGet(
        query: prefix.trim(),
        page: 1,
        size: 10,
      );
      return offenses
          .where((o) => o.driverName != null && o.driverName!.isNotEmpty)
          .map((o) => {
                'payee': o.driverName!,
                'offenseId': o.offenseId ?? 0,
                'fineAmount': o.fineAmount ?? 0.0,
                'licensePlate': o.licensePlate ?? '',
              })
          .where(
              (item) => item['payee'].toString().contains(prefix.toLowerCase()))
          .toList();
    } catch (e) {
      if (e is ApiException && e.code == 400 && prefix.trim().isEmpty) {
        return [];
      }
      _showSnackBar(
        'fineAdmin.error.fetchPayeeSuggestionsFailed'
            .trParams({'error': formatFineAdminError(e)}),
        isError: true,
      );
      return [];
    }
  }

  Future<void> _onLicensePlateSelected(String licensePlate) async {
    try {
      if (!await _validateJwtToken()) {
        Navigator.pushReplacementNamed(context, Routes.login);
        return;
      }
      final offenses = await offenseApi.apiOffensesByLicensePlateGet(
        query: licensePlate,
        page: 1,
        size: 10,
      );
      if (offenses.isNotEmpty) {
        final latestOffense = offenses.first;
        setState(() {
          _selectedOffenseId = latestOffense.offenseId;
          _payeeController.text = latestOffense.driverName ?? '';
          _fineAmountController.text =
              latestOffense.fineAmount?.toString() ?? '';
        });
      } else {
        _showSnackBar('fineAdmin.error.offenseNotFoundByPlate'.tr,
            isError: true);
        setState(() {
          _selectedOffenseId = null;
          _payeeController.clear();
          _fineAmountController.clear();
        });
      }
    } catch (e) {
      _showSnackBar(
        'fineAdmin.error.fetchOffenseFailed'
            .trParams({'error': formatFineAdminError(e)}),
        isError: true,
      );
    }
  }

  Future<void> _onPayeeSelected(Map<String, dynamic> payeeData) async {
    try {
      if (!await _validateJwtToken()) {
        Navigator.pushReplacementNamed(context, Routes.login);
        return;
      }
      if (payeeData['offenseId'] == 0) {
        _showSnackBar('fineAdmin.error.invalidOffense'.tr, isError: true);
        return;
      }
      setState(() {
        _payeeController.text = payeeData['payee'];
        _selectedOffenseId = payeeData['offenseId'];
        _fineAmountController.text = payeeData['fineAmount']?.toString() ?? '';
        _plateNumberController.text = payeeData['licensePlate'].isNotEmpty
            ? payeeData['licensePlate']
            : _plateNumberController.text;
      });
    } catch (e) {
      _showSnackBar(
        'fineAdmin.error.loadPayeeFailed'
            .trParams({'error': formatFineAdminError(e)}),
        isError: true,
      );
    }
  }

  Future<void> _submitFine() async {
    if (!_formKey.currentState!.validate()) return;
    final selectedOffenseId = _selectedOffenseId;
    final offenseValidationError = validateFineOffenseSelection(
      selectedOffenseId,
    );
    if (offenseValidationError != null) {
      _showSnackBar(offenseValidationError, isError: true);
      return;
    }
    if (!await _validateJwtToken()) {
      Navigator.pushReplacementNamed(context, Routes.login);
      return;
    }
    setState(() => _isLoading = true);
    try {
      if (widget.isEditMode) {
        _showSnackBar('fineAdmin.error.updateFailed'.tr, isError: true);
        return;
      }
      final idempotencyKey = generateIdempotencyKey();
      final fineAmount = double.parse(_fineAmountController.text.trim());
      final finePayload = FineInformation(
        fineId: null,
        offenseId: selectedOffenseId!,
        fineAmount: fineAmount,
        payee: _payeeController.text.trim(),
        accountNumber:
            normalizeOptionalFineValue(_accountNumberController.text),
        bank: normalizeOptionalFineValue(_bankController.text),
        receiptNumber:
            normalizeOptionalFineValue(_receiptNumberController.text),
        remarks: normalizeOptionalFineValue(_remarksController.text),
        fineTime: _selectedFineDate?.toIso8601String(),
        idempotencyKey: idempotencyKey,
      );
      await fineApi.apiFinesPost(
        fineInformation: finePayload,
        idempotencyKey: idempotencyKey,
      );
      _showSnackBar('fineAdmin.success.created'.tr);
      if (mounted) Navigator.pop(context, true);
    } on ApiException catch (e) {
      _showSnackBar(
        'fineAdmin.error.createFailed'
            .trParams({'error': formatFineAdminError(e)}),
        isError: true,
      );
    } catch (e) {
      _showSnackBar(
        (widget.isEditMode
                ? 'fineAdmin.error.updateFailed'
                : 'fineAdmin.error.createFailed')
            .trParams({'error': formatFineAdminError(e)}),
        isError: true,
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

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

  Future<void> _pickDate() async {
    final pickedDate = await showDatePicker(
      context: context,
      initialDate: _selectedFineDate ??
          (widget.fine != null
              ? resolveFineDisplayDate(
                  widget.fine!.fineDate,
                  widget.fine!.fineTime,
                )
              : null) ??
          DateTime.now(),
      firstDate: DateTime(1900),
      lastDate: DateTime.now(),
      builder: (context, child) => Theme(
        data: controller.currentBodyTheme.value.copyWith(
          colorScheme: controller.currentBodyTheme.value.colorScheme.copyWith(
            primary: controller.currentBodyTheme.value.colorScheme.primary,
            onPrimary: controller.currentBodyTheme.value.colorScheme.onPrimary,
          ),
        ),
        child: child!,
      ),
    );
    if (pickedDate != null && mounted) {
      setState(() => _setFineDate(pickedDate));
    }
  }

  Widget _buildFormField(
    String fieldKey,
    TextEditingController controller,
    ThemeData themeData, {
    TextInputType? keyboardType,
    bool readOnly = false,
    VoidCallback? onTap,
    bool required = false,
    int? maxLength,
    String? Function(String?)? validator,
  }) {
    final label = fineFieldLabel(fieldKey);
    final helperText = fineFieldHelperText(fieldKey);
    final isAutocompleteField =
        fieldKey == kFineFieldPlateNumber || fieldKey == kFineFieldPayee;

    InputDecoration buildDecoration({Widget? suffixIcon}) {
      return InputDecoration(
        labelText: label,
        labelStyle: TextStyle(color: themeData.colorScheme.onSurfaceVariant),
        helperText: helperText,
        helperStyle: TextStyle(
          color: themeData.colorScheme.onSurfaceVariant.withValues(alpha: 0.6),
        ),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12.0)),
        enabledBorder: OutlineInputBorder(
          borderSide: BorderSide(
            color: themeData.colorScheme.outline.withValues(alpha: 0.3),
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderSide:
              BorderSide(color: themeData.colorScheme.primary, width: 1.5),
        ),
        filled: true,
        fillColor: readOnly
            ? themeData.colorScheme.surfaceContainerHighest
                .withValues(alpha: 0.5)
            : themeData.colorScheme.surfaceContainerLowest,
        suffixIcon: suffixIcon ??
            (readOnly
                ? Icon(
                    Icons.calendar_today,
                    size: 18,
                    color: themeData.colorScheme.primary,
                  )
                : null),
      );
    }

    if (isAutocompleteField) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 6.0),
        child: Autocomplete<Map<String, dynamic>>(
          optionsBuilder: (TextEditingValue textEditingValue) async {
            if (textEditingValue.text.trim().isEmpty) {
              return const Iterable<Map<String, dynamic>>.empty();
            }
            if (fieldKey == kFineFieldPlateNumber) {
              final suggestions =
                  await _fetchLicensePlateSuggestions(textEditingValue.text);
              return suggestions.map((item) => {'value': item}).toList();
            }
            return await _fetchPayeeSuggestions(textEditingValue.text);
          },
          displayStringForOption: (Map<String, dynamic> option) =>
              fieldKey == kFineFieldPlateNumber
                  ? option['value']
                  : option['payee'],
          onSelected: (Map<String, dynamic> selection) async {
            if (fieldKey == kFineFieldPlateNumber) {
              controller.text = selection['value'];
              await _onLicensePlateSelected(selection['value']);
              return;
            }
            await _onPayeeSelected(selection);
          },
          fieldViewBuilder:
              (context, textEditingController, focusNode, onFieldSubmitted) {
            if (textEditingController.text != controller.text) {
              textEditingController.value = TextEditingValue(
                text: controller.text,
                selection:
                    TextSelection.collapsed(offset: controller.text.length),
              );
            }

            return TextFormField(
              controller: textEditingController,
              focusNode: focusNode,
              style: TextStyle(color: themeData.colorScheme.onSurface),
              decoration: buildDecoration(
                suffixIcon: textEditingController.text.isNotEmpty
                    ? IconButton(
                        icon: Icon(
                          Icons.clear,
                          color: themeData.colorScheme.onSurfaceVariant,
                        ),
                        onPressed: () {
                          textEditingController.clear();
                          controller.clear();
                          setState(() {
                            _selectedOffenseId = null;
                            if (fieldKey == kFineFieldPlateNumber) {
                              _payeeController.clear();
                              _fineAmountController.clear();
                            }
                          });
                        },
                      )
                    : null,
              ),
              keyboardType: keyboardType,
              maxLength: maxLength,
              validator: validator ??
                  (value) => validateFineFormField(
                        fieldKey,
                        value,
                        required: required,
                        selectedDate: fieldKey == kFineFieldFineDate
                            ? _selectedFineDate
                            : null,
                      ),
              onChanged: (value) {
                controller.text = value;
              },
            );
          },
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6.0),
      child: TextFormField(
        controller: controller,
        style: TextStyle(color: themeData.colorScheme.onSurface),
        decoration: buildDecoration(),
        keyboardType: keyboardType,
        readOnly: readOnly,
        onTap: onTap,
        maxLength: maxLength,
        validator: validator ??
            (value) => validateFineFormField(
                  fieldKey,
                  value,
                  required: required,
                  selectedDate:
                      fieldKey == kFineFieldFineDate ? _selectedFineDate : null,
                ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final themeData = controller.currentBodyTheme.value;
      return DashboardPageTemplate(
        theme: themeData,
        title: widget.isEditMode
            ? 'fineAdmin.form.editTitle'.tr
            : 'fineAdmin.form.addTitle'.tr,
        pageType: DashboardPageType.admin,
        bodyIsScrollable: true,
        padding: EdgeInsets.zero,
        body: Padding(
          padding: const EdgeInsets.all(16.0),
          child: _isLoading
              ? const Center(child: CircularProgressIndicator())
              : Form(
                  key: _formKey,
                  child: SingleChildScrollView(
                    child: Column(
                      children: [
                        Card(
                          elevation: 3,
                          color: themeData.colorScheme.surfaceContainer,
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16.0)),
                          child: Padding(
                            padding: const EdgeInsets.all(16.0),
                            child: Column(
                              children: [
                                _buildFormField(kFineFieldPlateNumber,
                                    _plateNumberController, themeData,
                                    required: true, maxLength: 20),
                                _buildFormField(kFineFieldAmount,
                                    _fineAmountController, themeData,
                                    keyboardType:
                                        const TextInputType.numberWithOptions(
                                            decimal: true),
                                    required: true),
                                _buildFormField(kFineFieldPayee,
                                    _payeeController, themeData,
                                    required: true, maxLength: 100),
                                _buildFormField(kFineFieldAccountNumber,
                                    _accountNumberController, themeData,
                                    maxLength: 50),
                                _buildFormField(
                                    kFineFieldBank, _bankController, themeData,
                                    maxLength: 100),
                                _buildFormField(kFineFieldReceiptNumber,
                                    _receiptNumberController, themeData,
                                    maxLength: 50),
                                _buildFormField(kFineFieldRemarks,
                                    _remarksController, themeData,
                                    maxLength: 255),
                                _buildFormField(kFineFieldFineDate,
                                    _dateController, themeData,
                                    readOnly: true,
                                    onTap: _pickDate,
                                    required: true),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 20),
                        ElevatedButton(
                          onPressed: _submitFine,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: themeData.colorScheme.primary,
                            foregroundColor: themeData.colorScheme.onPrimary,
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12.0)),
                            padding: const EdgeInsets.symmetric(
                                vertical: 14.0, horizontal: 20.0),
                            textStyle: themeData.textTheme.labelLarge
                                ?.copyWith(fontWeight: FontWeight.bold),
                          ),
                          child: Text(
                            widget.isEditMode
                                ? 'common.save'.tr
                                : 'common.submit'.tr,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
        ),
      );
    });
  }
}

class FineDetailPage extends StatefulWidget {
  final FineInformation fine;

  const FineDetailPage({super.key, required this.fine});

  @override
  State<FineDetailPage> createState() => _FineDetailPageState();
}

class _FineDetailPageState extends State<FineDetailPage> {
  final FineInformationControllerApi fineApi = FineInformationControllerApi();
  final PaymentRecordControllerApi paymentApi = PaymentRecordControllerApi();
  bool _isLoading = false;
  bool _isPaymentLoading = false;
  bool _isSubmittingPaymentReview = false;
  String _errorMessage = '';
  String _paymentErrorMessage = '';
  final DashboardController controller = Get.find<DashboardController>();
  late FineInformation _currentFine;
  List<PaymentRecordModel> _paymentRecords = [];

  @override
  void initState() {
    super.initState();
    _currentFine = widget.fine;
    _initialize();
  }

  Future<bool> _validateJwtToken() async {
    final jwtToken = (await AuthTokenStore.instance.getJwtToken());
    if (jwtToken == null || jwtToken.isEmpty) {
      setState(() => _errorMessage = 'fineAdmin.error.unauthorized'.tr);
      return false;
    }
    try {
      if (JwtDecoder.isExpired(jwtToken)) {
        setState(() => _errorMessage = 'fineAdmin.error.expired'.tr);
        return false;
      }
      return true;
    } catch (e) {
      setState(() => _errorMessage = 'fineAdmin.error.invalidLogin'.tr);
      return false;
    }
  }

  Future<void> _initialize() async {
    setState(() => _isLoading = true);
    try {
      if (!await _validateJwtToken()) {
        Navigator.pushReplacementNamed(context, Routes.login);
        return;
      }
      await fineApi.initializeWithJwt();
      await paymentApi.initializeWithJwt();
      await _loadPaymentHistory();
    } catch (e) {
      setState(() => _errorMessage = 'fineAdmin.error.initFailed'
          .trParams({'error': formatFineAdminError(e)}));
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _loadPaymentHistory() async {
    final fineId = _currentFine.fineId;
    if (fineId == null) {
      setState(() {
        _paymentRecords = const [];
        _paymentErrorMessage = '';
      });
      return;
    }

    setState(() {
      _isPaymentLoading = true;
      _paymentErrorMessage = '';
    });

    try {
      final payments =
          await paymentApi.apiPaymentsFineFineIdGet(fineId: fineId, size: 50);
      payments.sort((left, right) {
        final rightTime = right.paymentTime ?? right.createdAt;
        final leftTime = left.paymentTime ?? left.createdAt;
        final rightValue = rightTime?.millisecondsSinceEpoch ?? 0;
        final leftValue = leftTime?.millisecondsSinceEpoch ?? 0;
        return rightValue.compareTo(leftValue);
      });
      if (!mounted) return;
      setState(() => _paymentRecords = payments);
    } catch (e) {
      if (!mounted) return;
      if (e is ApiException && e.code == 404) {
        setState(() {
          _paymentRecords = const [];
          _paymentErrorMessage = '';
        });
      } else {
        setState(() {
          _paymentErrorMessage = 'fine.paymentHistory.loadFailed'
              .trParams({'error': formatFineAdminError(e)});
        });
      }
    } finally {
      if (mounted) {
        setState(() => _isPaymentLoading = false);
      }
    }
  }

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

  String _displayText(String? value, {String emptyKey = 'common.none'}) {
    final trimmed = value?.trim();
    return trimmed == null || trimmed.isEmpty ? emptyKey.tr : trimmed;
  }

  String _formatPaymentDateTime(DateTime? dateTime) {
    return formatFineAdminDateTime(dateTime, emptyKey: 'common.none');
  }

  void _showFeedbackMessage(String message, {bool isError = false}) {
    if (!mounted) return;
    final themeData = controller.currentBodyTheme.value;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          message,
          style: themeData.textTheme.bodyMedium?.copyWith(
            color: themeData.colorScheme.onInverseSurface,
          ),
        ),
        backgroundColor: isError
            ? themeData.colorScheme.error
            : themeData.colorScheme.inverseSurface,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  String _maskIdCard(String? idCard) {
    final trimmed = idCard?.trim();
    if (trimmed == null || trimmed.isEmpty) {
      return 'common.none'.tr;
    }
    if (trimmed.length <= 8) {
      return trimmed;
    }
    return '${trimmed.substring(0, 4)}****${trimmed.substring(trimmed.length - 4)}';
  }

  bool _isSelfServicePayment(PaymentRecordModel payment) {
    final paymentChannel = (payment.paymentChannel ?? '').trim().toUpperCase();
    return paymentChannel == 'APP' || paymentChannel == 'USER_SELF_SERVICE';
  }

  bool _needsManualProofReview(PaymentRecordModel payment) {
    final normalizedStatus = normalizePaymentStatusCode(payment.paymentStatus);
    final isConfirmedPayment =
        normalizedStatus == 'paid' || normalizedStatus == 'partial';
    final hasReceiptUrl = (payment.receiptUrl ?? '').trim().isNotEmpty;
    return _isSelfServicePayment(payment) &&
        isConfirmedPayment &&
        !hasReceiptUrl;
  }

  bool _isFinanceReviewablePayment(PaymentRecordModel payment) {
    final normalizedStatus = normalizePaymentStatusCode(payment.paymentStatus);
    return _isSelfServicePayment(payment) &&
        (normalizedStatus == 'paid' || normalizedStatus == 'partial');
  }

  String _localizeFinanceReviewResult(String reviewResult) {
    switch (reviewResult.trim().toUpperCase()) {
      case 'APPROVED':
        return 'fine.paymentReview.result.approved'.tr;
      case 'NEED_PROOF':
        return 'fine.paymentReview.result.needProof'.tr;
      default:
        return reviewResult;
    }
  }

  Future<void> _submitFinanceReview(
    PaymentRecordModel payment, {
    required String reviewResult,
    String? reviewOpinion,
  }) async {
    final paymentId = payment.paymentId;
    if (paymentId == null || _isSubmittingPaymentReview) {
      return;
    }
    setState(() => _isSubmittingPaymentReview = true);
    try {
      await paymentApi.apiPaymentsPaymentIdFinanceReviewPost(
        paymentId: paymentId,
        reviewResult: reviewResult,
        reviewOpinion: reviewOpinion,
        idempotencyKey: generateIdempotencyKey(),
      );
      if (!mounted) return;
      _showFeedbackMessage(
        reviewResult == 'APPROVED'
            ? 'fine.paymentReview.success.approved'.tr
            : 'fine.paymentReview.success.needProof'.tr,
      );
      await _loadPaymentHistory();
    } catch (e) {
      if (!mounted) return;
      _showFeedbackMessage(
        'fine.paymentReview.failed'
            .trParams({'error': formatFineAdminError(e)}),
        isError: true,
      );
    } finally {
      if (mounted) {
        setState(() => _isSubmittingPaymentReview = false);
      }
    }
  }

  Future<void> _showNeedProofDialog(PaymentRecordModel payment) async {
    final opinionController = TextEditingController();
    try {
      final opinion = await showDialog<String>(
        context: context,
        builder: (dialogContext) {
          final themeData = controller.currentBodyTheme.value;
          return AlertDialog(
            title: Text('fine.paymentReview.dialog.needProofTitle'.tr),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'fine.paymentReview.dialog.needProofHint'.tr,
                  style: themeData.textTheme.bodyMedium,
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: opinionController,
                  maxLines: 3,
                  decoration: InputDecoration(
                    labelText: 'fine.paymentReview.opinion'.tr,
                    border: const OutlineInputBorder(),
                  ),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(dialogContext).pop(),
                child: Text('common.cancel'.tr),
              ),
              FilledButton(
                onPressed: () {
                  final normalized = opinionController.text.trim();
                  if (normalized.isEmpty) {
                    _showFeedbackMessage(
                      'fine.paymentReview.validation.opinionRequired'.tr,
                      isError: true,
                    );
                    return;
                  }
                  Navigator.of(dialogContext).pop(normalized);
                },
                child: Text('common.submit'.tr),
              ),
            ],
          );
        },
      );
      if (opinion == null || opinion.trim().isEmpty) {
        return;
      }
      await _submitFinanceReview(
        payment,
        reviewResult: 'NEED_PROOF',
        reviewOpinion: opinion,
      );
    } finally {
      opinionController.dispose();
    }
  }

  Widget _buildFinanceReviewSummary(
    FinancePaymentReview review,
    ThemeData themeData,
  ) {
    final needsProof = review.reviewResult == 'NEED_PROOF';
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: needsProof
            ? themeData.colorScheme.errorContainer
            : themeData.colorScheme.secondaryContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'fine.paymentReview.latest'.tr,
            style: themeData.textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w700,
              color: needsProof
                  ? themeData.colorScheme.onErrorContainer
                  : themeData.colorScheme.onSecondaryContainer,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'common.labelWithColon'.trParams(
                  {'label': 'fine.paymentReview.result'.tr},
                ) +
                _localizeFinanceReviewResult(review.reviewResult),
            style: themeData.textTheme.bodyMedium?.copyWith(
              color: needsProof
                  ? themeData.colorScheme.onErrorContainer
                  : themeData.colorScheme.onSecondaryContainer,
            ),
          ),
          if (review.reviewTime != null)
            Text(
              'common.labelWithColon'.trParams(
                    {'label': 'fine.paymentReview.time'.tr},
                  ) +
                  _formatPaymentDateTime(review.reviewTime),
              style: themeData.textTheme.bodyMedium?.copyWith(
                color: needsProof
                    ? themeData.colorScheme.onErrorContainer
                    : themeData.colorScheme.onSecondaryContainer,
              ),
            ),
          if ((review.reviewer ?? '').trim().isNotEmpty)
            Text(
              'common.labelWithColon'.trParams(
                    {'label': 'fine.paymentReview.reviewer'.tr},
                  ) +
                  review.reviewer!,
              style: themeData.textTheme.bodyMedium?.copyWith(
                color: needsProof
                    ? themeData.colorScheme.onErrorContainer
                    : themeData.colorScheme.onSecondaryContainer,
              ),
            ),
          if ((review.reviewOpinion ?? '').trim().isNotEmpty)
            Text(
              'common.labelWithColon'.trParams(
                    {'label': 'fine.paymentReview.opinion'.tr},
                  ) +
                  review.reviewOpinion!,
              style: themeData.textTheme.bodyMedium?.copyWith(
                color: needsProof
                    ? themeData.colorScheme.onErrorContainer
                    : themeData.colorScheme.onSecondaryContainer,
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildPaymentReviewActions(
    PaymentRecordModel payment,
    ThemeData themeData,
  ) {
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Wrap(
        spacing: 10,
        runSpacing: 10,
        children: [
          FilledButton(
            onPressed: _isSubmittingPaymentReview
                ? null
                : () => _submitFinanceReview(
                      payment,
                      reviewResult: 'APPROVED',
                    ),
            child: Text('fine.paymentReview.action.approve'.tr),
          ),
          OutlinedButton(
            onPressed: _isSubmittingPaymentReview
                ? null
                : () => _showNeedProofDialog(payment),
            child: Text('fine.paymentReview.action.needProof'.tr),
          ),
        ],
      ),
    );
  }

  Widget _buildPaymentHistorySection(ThemeData themeData) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 24),
        Divider(color: themeData.colorScheme.outlineVariant),
        const SizedBox(height: 16),
        Text(
          'fine.paymentHistory.title'.tr,
          style: themeData.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
            color: themeData.colorScheme.onSurface,
          ),
        ),
        const SizedBox(height: 12),
        if (_isPaymentLoading)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Row(
              children: [
                SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor: AlwaysStoppedAnimation(
                      themeData.colorScheme.primary,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Text(
                  'common.loading'.tr,
                  style: themeData.textTheme.bodyMedium?.copyWith(
                    color: themeData.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          )
        else if (_paymentErrorMessage.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              _paymentErrorMessage,
              style: themeData.textTheme.bodyMedium?.copyWith(
                color: themeData.colorScheme.error,
              ),
            ),
          )
        else if (_paymentRecords.isEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              'fine.paymentHistory.empty'.tr,
              style: themeData.textTheme.bodyMedium?.copyWith(
                color: themeData.colorScheme.onSurfaceVariant,
              ),
            ),
          )
        else
          ..._paymentRecords.map(
            (payment) {
              final financeReview =
                  parseLatestFinancePaymentReview(payment.remarks);
              final plainRemarks = stripFinancePaymentReviews(payment.remarks);
              return Card(
                margin: const EdgeInsets.only(top: 12),
                color: themeData.colorScheme.surfaceContainerLowest,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'fine.paymentHistory.recordTitle'.trParams({
                          'amount':
                              (payment.paymentAmount ?? 0).toStringAsFixed(2),
                        }),
                        style: themeData.textTheme.titleSmall?.copyWith(
                          color: themeData.colorScheme.onSurface,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      if (_needsManualProofReview(payment)) ...[
                        const SizedBox(height: 10),
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: themeData.colorScheme.errorContainer,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(
                            'fine.paymentHistory.missingProofHint'.tr,
                            style: themeData.textTheme.bodyMedium?.copyWith(
                              color: themeData.colorScheme.onErrorContainer,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ],
                      if (financeReview != null)
                        _buildFinanceReviewSummary(financeReview, themeData),
                      const SizedBox(height: 8),
                      _buildDetailRow(
                        'fine.paymentHistory.status'.tr,
                        localizePaymentStatus(payment.paymentStatus),
                        themeData,
                      ),
                      _buildDetailRow(
                        'fine.paymentHistory.time'.tr,
                        _formatPaymentDateTime(
                          payment.paymentTime ?? payment.createdAt,
                        ),
                        themeData,
                      ),
                      _buildDetailRow(
                        'fine.paymentHistory.method'.tr,
                        _displayText(payment.paymentMethod),
                        themeData,
                      ),
                      _buildDetailRow(
                        'fine.paymentHistory.channel'.tr,
                        _displayText(payment.paymentChannel),
                        themeData,
                      ),
                      _buildDetailRow(
                        'fine.paymentHistory.paymentNumber'.tr,
                        _displayText(payment.paymentNumber),
                        themeData,
                      ),
                      _buildDetailRow(
                        'fine.paymentHistory.transactionId'.tr,
                        _displayText(payment.transactionId),
                        themeData,
                      ),
                      _buildDetailRow(
                        'fine.paymentHistory.receiptNumber'.tr,
                        _displayText(payment.receiptNumber),
                        themeData,
                      ),
                      _buildDetailRow(
                        'fine.paymentHistory.receiptUrl'.tr,
                        _displayText(payment.receiptUrl),
                        themeData,
                      ),
                      _buildDetailRow(
                        'fine.paymentHistory.payerName'.tr,
                        _displayText(payment.payerName,
                            emptyKey: 'common.unknown'),
                        themeData,
                      ),
                      _buildDetailRow(
                        'fine.paymentHistory.payerIdCard'.tr,
                        _maskIdCard(payment.payerIdCard),
                        themeData,
                      ),
                      _buildDetailRow(
                        'fine.paymentHistory.payerContact'.tr,
                        _displayText(payment.payerContact),
                        themeData,
                      ),
                      _buildDetailRow(
                        'fine.paymentHistory.bankName'.tr,
                        _displayText(payment.bankName),
                        themeData,
                      ),
                      _buildDetailRow(
                        'fine.paymentHistory.bankAccount'.tr,
                        _displayText(payment.bankAccount),
                        themeData,
                      ),
                      if (payment.refundAmount != null &&
                          payment.refundAmount! > 0)
                        _buildDetailRow(
                          'fine.paymentHistory.refund'.tr,
                          'fine.paymentHistory.refundValue'.trParams({
                            'amount': payment.refundAmount!.toStringAsFixed(2),
                            'time': _formatPaymentDateTime(payment.refundTime),
                          }),
                          themeData,
                        ),
                      _buildDetailRow(
                        'fine.detail.remarks'.tr,
                        _displayText(plainRemarks),
                        themeData,
                      ),
                      if (_isFinanceReviewablePayment(payment))
                        _buildPaymentReviewActions(payment, themeData),
                    ],
                  ),
                ),
              );
            },
          ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final themeData = controller.currentBodyTheme.value;
      if (_errorMessage.isNotEmpty) {
        return DashboardPageTemplate(
          theme: themeData,
          title: 'fineAdmin.detail.title'.tr,
          pageType: DashboardPageType.admin,
          bodyIsScrollable: true,
          padding: EdgeInsets.zero,
          body: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  _errorMessage,
                  style: themeData.textTheme.titleMedium?.copyWith(
                    color: themeData.colorScheme.error,
                    fontWeight: FontWeight.w500,
                  ),
                  textAlign: TextAlign.center,
                ),
                if (shouldShowFineDetailReloginAction(_errorMessage))
                  Padding(
                    padding: const EdgeInsets.only(top: 16.0),
                    child: ElevatedButton(
                      onPressed: () =>
                          Navigator.pushReplacementNamed(context, Routes.login),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: themeData.colorScheme.primary,
                        foregroundColor: themeData.colorScheme.onPrimary,
                      ),
                      child: Text('fineAdmin.action.relogin'.tr),
                    ),
                  ),
              ],
            ),
          ),
        );
      }

      return DashboardPageTemplate(
        theme: themeData,
        title: 'fineAdmin.detail.title'.tr,
        pageType: DashboardPageType.admin,
        bodyIsScrollable: true,
        padding: EdgeInsets.zero,
        actions: const [],
        body: _isLoading
            ? Center(
                child: CircularProgressIndicator(
                  valueColor:
                      AlwaysStoppedAnimation(themeData.colorScheme.primary),
                ),
              )
            : Padding(
                padding: const EdgeInsets.all(16.0),
                child: Card(
                  elevation: 3,
                  color: themeData.colorScheme.surfaceContainer,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16.0),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: SingleChildScrollView(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _buildDetailRow(
                            'fine.detail.amount'.tr,
                            '${_currentFine.fineAmount ?? 0}',
                            themeData,
                          ),
                          _buildDetailRow(
                            'fine.detail.payee'.tr,
                            _currentFine.payee ?? 'common.unknown'.tr,
                            themeData,
                          ),
                          _buildDetailRow(
                            'fine.detail.time'.tr,
                            formatFineAdminDateTime(
                              resolveFineDisplayDate(
                                _currentFine.fineDate,
                                _currentFine.fineTime,
                              ),
                            ),
                            themeData,
                          ),
                          _buildDetailRow(
                            'fine.detail.status'.tr,
                            localizeAdminFineStatus(_currentFine.status),
                            themeData,
                          ),
                          _buildDetailRow(
                            'fine.detail.account'.tr,
                            _currentFine.accountNumber ?? 'common.none'.tr,
                            themeData,
                          ),
                          _buildDetailRow(
                            'fine.detail.bank'.tr,
                            _currentFine.bank ?? 'common.none'.tr,
                            themeData,
                          ),
                          _buildDetailRow(
                            'fine.detail.receipt'.tr,
                            _currentFine.receiptNumber ?? 'common.none'.tr,
                            themeData,
                          ),
                          _buildDetailRow(
                            'fine.detail.remarks'.tr,
                            _currentFine.remarks ?? 'common.none'.tr,
                            themeData,
                          ),
                          _buildPaymentHistorySection(themeData),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
      );
    });
  }
}
