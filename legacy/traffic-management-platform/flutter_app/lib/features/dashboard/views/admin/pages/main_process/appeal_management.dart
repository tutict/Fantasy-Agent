// ignore_for_file: use_build_context_synchronously
import 'dart:async';
import 'dart:developer' as developer;

import 'package:final_assignment_front/config/routes/app_routes.dart';
import 'package:final_assignment_front/features/api/appeal_management_controller_api.dart';
import 'package:final_assignment_front/features/dashboard/controllers/admin_dashboard_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/dashboard_page_template.dart';
import 'package:final_assignment_front/features/model/appeal_record.dart';
import 'package:final_assignment_front/features/model/appeal_review.dart';
import 'package:final_assignment_front/i18n/appeal_localizers.dart';
import 'package:final_assignment_front/i18n/status_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:final_assignment_front/utils/helpers/role_utils.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:final_assignment_front/utils/services/session_helper.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:jwt_decoder/jwt_decoder.dart';
import 'package:uuid/uuid.dart';

String generateIdempotencyKey() {
  return const Uuid().v4();
}

class AppealManagementAdmin extends StatefulWidget {
  const AppealManagementAdmin({super.key});

  @override
  State<AppealManagementAdmin> createState() => _AppealManagementAdminState();
}

class _AppealManagementAdminState extends State<AppealManagementAdmin> {
  static const int _appealPageSize = 50;
  static const int _reviewPageSize = 50;
  static const String _viewAppeals = 'appeals';
  static const String _viewReviews = 'reviews';
  static const String _reviewLevelPrimary = 'primary';
  static const String _reviewLevelSecondary = 'secondary';
  static const String _reviewLevelFinal = 'final';

  final AppealManagementControllerApi appealApi =
      AppealManagementControllerApi();
  final SessionHelper _sessionHelper = SessionHelper();
  final TextEditingController _searchController = TextEditingController();
  final TextEditingController _reviewSearchController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<AppealRecordModel> _appeals = [];
  final List<AppealReviewModel> _reviews = [];
  List<AppealRecordModel> _filteredAppeals = [];
  List<AppealReviewModel> _filteredReviews = [];
  String _currentView = _viewAppeals;
  String _searchType = kAppealSearchTypeAppealReason;
  String _reviewSearchType = kAppealReviewSearchTypeReviewer;
  String _activeQuery = '';
  String _activeReviewQuery = '';
  DateTime? _startTime;
  DateTime? _endTime;
  DateTime? _reviewStartTime;
  DateTime? _reviewEndTime;
  int _currentPage = 1;
  int _currentReviewPage = 1;
  bool _hasMore = true;
  bool _hasMoreReviews = true;
  bool _isLoading = false;
  bool _isAdmin = false;
  String _errorMessage = '';
  String _reviewErrorMessage = '';
  bool _isReviewWorkbenchLoading = false;
  String _reviewWorkbenchError = '';
  Map<String, int> _reviewLevelCounts = {
    _reviewLevelPrimary: 0,
    _reviewLevelSecondary: 0,
    _reviewLevelFinal: 0,
  };
  Timer? _searchDebounce;
  Timer? _reviewSearchDebounce;
  final DashboardController controller = Get.find<DashboardController>();

  @override
  void initState() {
    super.initState();
    _initialize();
    _scrollController.addListener(() {
      if (_scrollController.position.pixels >=
              _scrollController.position.maxScrollExtent - 200 &&
          ((_currentView == _viewAppeals && _hasMore) ||
              (_currentView == _viewReviews && _hasMoreReviews)) &&
          !_isLoading) {
        if (_currentView == _viewAppeals) {
          _loadAppeals();
        } else {
          _loadReviews();
        }
      }
    });
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();
    _reviewSearchDebounce?.cancel();
    _searchController.dispose();
    _reviewSearchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<bool> _validateJwtToken() async {
    String? jwtToken = (await AuthTokenStore.instance.getJwtToken());
    if (jwtToken == null || jwtToken.isEmpty) {
      setState(
          () => _errorMessage = 'appealAdmin.error.unauthorizedMissing'.tr);
      return false;
    }
    try {
      final decodedToken = JwtDecoder.decode(jwtToken);
      if (JwtDecoder.isExpired(jwtToken)) {
        jwtToken = await _refreshJwtToken();
        if (jwtToken == null) {
          setState(() => _errorMessage = 'appealAdmin.error.expired'.tr);
          return false;
        }
        await AuthTokenStore.instance.setJwtToken(jwtToken);
        if (JwtDecoder.isExpired(jwtToken)) {
          setState(
              () => _errorMessage = 'appealAdmin.error.refreshedExpired'.tr);
          return false;
        }
        await appealApi.initializeWithJwt();
      }
      developer
          .log('JWT Token validated successfully: sub=${decodedToken['sub']}');
      return true;
    } catch (e) {
      setState(() => _errorMessage = 'appealAdmin.error.invalidLogin'.trParams({
            'error': formatAppealErrorDetail(e),
          }));
      developer.log('JWT validation failed: $e',
          stackTrace: StackTrace.current);
      return false;
    }
  }

  Future<String?> _refreshJwtToken() async {
    final newJwt = await _sessionHelper.refreshJwtToken();
    if (newJwt != null) {
      developer.log('JWT token refreshed successfully');
    } else {
      developer.log('Failed to refresh JWT token');
    }
    return newJwt;
  }

  Future<void> _initialize() async {
    setState(() => _isLoading = true);
    try {
      if (!await _validateJwtToken()) {
        Get.offAllNamed(Routes.login);
        return;
      }
      await appealApi.initializeWithJwt();
      await _checkUserRole();
      if (_isAdmin) {
        await _loadAppeals(reset: true);
      } else {
        setState(() => _errorMessage = 'appealAdmin.error.adminOnly'.tr);
      }
    } catch (e) {
      setState(() => _errorMessage = 'appealAdmin.error.initFailed'.trParams({
            'error': formatAppealErrorDetail(e),
          }));
      developer.log('Initialization failed: $e',
          stackTrace: StackTrace.current);
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
      final roles = await _sessionHelper.fetchCurrentRoles();
      final hasAdminAccess = hasAnyRole(roles, const [
        'SUPER_ADMIN',
        'ADMIN',
        'APPEAL_REVIEWER',
      ]);
      setState(() {
        _isAdmin = hasAdminAccess;
        if (!hasAdminAccess) {
          _errorMessage = 'appealAdmin.error.adminOnly'.tr;
        }
      });
    } catch (e) {
      setState(
          () => _errorMessage = 'appealAdmin.error.roleCheckFailed'.trParams({
                'error': formatAppealErrorDetail(e),
              }));
      developer.log('Role check failed: $e', stackTrace: StackTrace.current);
    }
  }

  Future<List<String>> _fetchAutocompleteSuggestions(String prefix) async {
    if (prefix.isEmpty) return [];
    final normalized = prefix.toLowerCase();
    Iterable<String> values = const Iterable.empty();
    switch (_searchType) {
      case kAppealSearchTypeAppealReason:
        values = _appeals.map((appeal) => appeal.appealReason ?? '');
        break;
      case kAppealSearchTypeAppellantName:
        values = _appeals.map((appeal) => appeal.appellantName ?? '');
        break;
      case kAppealSearchTypeProcessStatus:
        values = _appeals
            .map((appeal) => localizeAppealStatus(appeal.processStatus));
        break;
      default:
        return [];
    }
    return values
        .where((value) => value.isNotEmpty)
        .where((value) => value.toLowerCase().contains(normalized))
        .toSet()
        .take(5)
        .toList();
  }

  Future<List<String>> _fetchReviewAutocompleteSuggestions(
      String prefix) async {
    if (prefix.isEmpty) return [];
    final normalized = prefix.toLowerCase();
    Iterable<String> values = const Iterable.empty();
    switch (_reviewSearchType) {
      case kAppealReviewSearchTypeReviewer:
        values = _reviews.map((review) => review.reviewer ?? '');
        break;
      case kAppealReviewSearchTypeReviewerDept:
        values = _reviews.map((review) => review.reviewerDept ?? '');
        break;
      default:
        return [];
    }
    return values
        .where((value) => value.isNotEmpty)
        .where((value) => value.toLowerCase().contains(normalized))
        .toSet()
        .take(5)
        .toList();
  }

  Future<void> _loadAppeals({bool reset = false, String? query}) async {
    if (!_isAdmin) return;

    if (reset) {
      _currentPage = 1;
      _hasMore = true;
      _activeQuery = (query ?? _searchController.text).trim();
      _appeals.clear();
      _filteredAppeals.clear();
    }
    if (!reset && (_isLoading || !_hasMore)) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    try {
      if (!await _validateJwtToken()) {
        Get.offAllNamed(Routes.login);
        return;
      }
      await appealApi.initializeWithJwt();
      final appeals =
          await _loadAppealPage(page: _currentPage, query: _activeQuery);
      setState(() {
        _appeals.addAll(appeals);
        _rebuildVisibleAppeals();
        _hasMore = appeals.length == _appealPageSize;
        _currentPage++;
      });
      developer.log('Loaded appeals: ${_appeals.length}');
    } catch (e) {
      developer.log('Error fetching appeals: $e',
          stackTrace: StackTrace.current);
      setState(() {
        _appeals.clear();
        _filteredAppeals.clear();
        if (e is ApiException && e.code == 403) {
          _errorMessage = 'appealAdmin.error.unauthorized'.tr;
          Get.offAllNamed(Routes.login);
        } else {
          _errorMessage = 'appealAdmin.error.loadFailed'
              .trParams({'error': formatAppealAdminError(e)});
        }
      });
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _loadReviews({bool reset = false, String? query}) async {
    if (!_isAdmin) return;

    if (reset) {
      _currentReviewPage = 1;
      _hasMoreReviews = true;
      _activeReviewQuery = (query ?? _reviewSearchController.text).trim();
      _reviews.clear();
      _filteredReviews.clear();
    }
    if (!reset && (_isLoading || !_hasMoreReviews)) {
      return;
    }

    setState(() {
      _isLoading = true;
      _reviewErrorMessage = '';
    });

    try {
      if (!await _validateJwtToken()) {
        Get.offAllNamed(Routes.login);
        return;
      }
      await appealApi.initializeWithJwt();
      final reviews = await _loadReviewPage(
          page: _currentReviewPage, query: _activeReviewQuery);
      setState(() {
        _reviews.addAll(reviews);
        _rebuildVisibleReviews();
        _hasMoreReviews = reviews.length == _reviewPageSize;
        _currentReviewPage++;
      });
    } catch (e) {
      developer.log('Error fetching appeal reviews: $e',
          stackTrace: StackTrace.current);
      setState(() {
        _reviews.clear();
        _filteredReviews.clear();
        if (e is ApiException && e.code == 403) {
          _reviewErrorMessage = 'appealAdmin.error.unauthorized'.tr;
          Get.offAllNamed(Routes.login);
        } else {
          _reviewErrorMessage = 'appealAdmin.review.loadFailed'
              .trParams({'error': formatAppealAdminError(e)});
        }
      });
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<List<AppealRecordModel>> _loadAppealPage({
    required int page,
    required String query,
  }) {
    if (_searchType == kAppealSearchTypeTimeRange &&
        _startTime != null &&
        _endTime != null) {
      return appealApi.apiAppealsSearchTimeRangeGet(
        startTime: _startTime!.toIso8601String(),
        endTime: _endTime!.add(const Duration(days: 1)).toIso8601String(),
        page: page,
        size: _appealPageSize,
      );
    }
    if (query.isEmpty) {
      return appealApi.apiAppealsGet(page: page, size: _appealPageSize);
    }
    switch (_searchType) {
      case kAppealSearchTypeAppellantName:
        return appealApi.apiAppealsSearchAppellantNameFuzzyGet(
          appellantName: query,
          page: page,
          size: _appealPageSize,
        );
      case kAppealSearchTypeProcessStatus:
        return appealApi.apiAppealsSearchProcessStatusGet(
          processStatus: normalizeAppealStatusCode(query),
          page: page,
          size: _appealPageSize,
        );
      case kAppealSearchTypeAppealReason:
      default:
        return appealApi.apiAppealsSearchReasonFuzzyGet(
          appealReason: query,
          page: page,
          size: _appealPageSize,
        );
    }
  }

  Future<List<AppealReviewModel>> _loadReviewPage({
    required int page,
    required String query,
  }) {
    if (_reviewSearchType == kAppealReviewSearchTypeTimeRange &&
        _reviewStartTime != null &&
        _reviewEndTime != null) {
      return appealApi.apiAppealsReviewsSearchTimeRangeGet(
        startTime: _reviewStartTime!.toIso8601String(),
        endTime: _reviewEndTime!.add(const Duration(days: 1)).toIso8601String(),
        page: page,
        size: _reviewPageSize,
      );
    }
    if (query.isEmpty) {
      return appealApi.apiAppealsReviewsGet(page: page, size: _reviewPageSize);
    }
    switch (_reviewSearchType) {
      case kAppealReviewSearchTypeReviewerDept:
        return appealApi.apiAppealsReviewsSearchReviewerDeptGet(
          reviewerDept: query,
          page: page,
          size: _reviewPageSize,
        );
      case kAppealReviewSearchTypeReviewer:
      default:
        return appealApi.apiAppealsReviewsSearchReviewerGet(
          reviewer: query,
          page: page,
          size: _reviewPageSize,
        );
    }
  }

  void _rebuildVisibleAppeals() {
    _filteredAppeals = List<AppealRecordModel>.from(_appeals);
    if (_filteredAppeals.isEmpty) {
      _errorMessage =
          _activeQuery.isNotEmpty || (_startTime != null && _endTime != null)
              ? 'appeal.empty.filtered'.tr
              : 'appeal.empty'.tr;
    } else {
      _errorMessage = '';
    }
  }

  void _rebuildVisibleReviews() {
    _filteredReviews = List<AppealReviewModel>.from(_reviews);
    if (_filteredReviews.isEmpty) {
      _reviewErrorMessage = _activeReviewQuery.isNotEmpty ||
              (_reviewStartTime != null && _reviewEndTime != null)
          ? 'appealAdmin.review.empty.filtered'.tr
          : 'appealAdmin.review.empty'.tr;
    } else {
      _reviewErrorMessage = '';
    }
  }

  Future<void> _refreshAppeals({String? query}) async {
    _searchDebounce?.cancel();
    final effectiveQuery = (query ?? _searchController.text).trim();
    setState(() {
      _appeals.clear();
      _filteredAppeals.clear();
      _currentPage = 1;
      _hasMore = true;
      _isLoading = true;
      _searchController.value = TextEditingValue(
        text: effectiveQuery,
        selection: TextSelection.collapsed(offset: effectiveQuery.length),
      );
    });
    await _loadAppeals(reset: true, query: effectiveQuery);
  }

  Future<void> _refreshReviews({String? query}) async {
    _reviewSearchDebounce?.cancel();
    final effectiveQuery = (query ?? _reviewSearchController.text).trim();
    setState(() {
      _reviews.clear();
      _filteredReviews.clear();
      _currentReviewPage = 1;
      _hasMoreReviews = true;
      _isLoading = true;
      _reviewSearchController.value = TextEditingValue(
        text: effectiveQuery,
        selection: TextSelection.collapsed(offset: effectiveQuery.length),
      );
    });
    await _loadReviews(reset: true, query: effectiveQuery);
  }

  Future<void> _refreshCurrentView() async {
    if (_currentView == _viewAppeals) {
      await _refreshAppeals();
      return;
    }
    await _refreshReviews();
    await _refreshAppeals(query: _activeQuery);
    await _loadReviewWorkbenchSummary(showLoading: false);
  }

  void _scheduleSearchRefresh(String value) {
    _searchDebounce?.cancel();
    _searchDebounce = Timer(const Duration(milliseconds: 350), () {
      if (!mounted) {
        return;
      }
      _refreshAppeals(query: value);
    });
  }

  void _scheduleReviewSearchRefresh(String value) {
    _reviewSearchDebounce?.cancel();
    _reviewSearchDebounce = Timer(const Duration(milliseconds: 350), () {
      if (!mounted) {
        return;
      }
      _refreshReviews(query: value);
    });
  }

  Future<void> _switchView(String view) async {
    if (_currentView == view) return;
    setState(() {
      _currentView = view;
    });
    if (view == _viewReviews) {
      if (_reviews.isEmpty) {
        await _loadReviews(reset: true);
      }
      if (_reviewLevelCounts.values.every((count) => count == 0)) {
        await _loadReviewWorkbenchSummary();
      }
    }
  }

  void _goToDetailPage(AppealRecordModel appeal) {
    Get.to(() => AppealDetailPage(
          appeal: appeal,
          onAppealUpdated: (updatedAppeal) {
            setState(() {
              final index = _appeals
                  .indexWhere((a) => a.appealId == updatedAppeal.appealId);
              if (index != -1) {
                _appeals[index] = updatedAppeal;
              }
              final visibleIndex = _filteredAppeals
                  .indexWhere((a) => a.appealId == updatedAppeal.appealId);
              if (visibleIndex != -1) {
                _filteredAppeals[visibleIndex] = updatedAppeal;
              }
              _rebuildVisibleAppeals();
            });
          },
        ))?.then((value) {
      if (value == true && mounted) {
        _refreshAppeals().then((_) async {
          if (!mounted) {
            return;
          }
          await _loadReviewWorkbenchSummary(showLoading: false);
          if (!mounted || _currentView != _viewReviews) {
            return;
          }
          await _refreshReviews();
        });
      }
    });
  }

  Future<void> _openAppealFromReview(AppealReviewModel review) async {
    final appealId = review.appealId;
    if (appealId == null) {
      _showSnackBar('appealAdmin.error.invalidAppealId'.tr, isError: true);
      return;
    }
    try {
      if (!await _validateJwtToken()) {
        Get.offAllNamed(Routes.login);
        return;
      }
      await appealApi.initializeWithJwt();
      final appeal = await appealApi.apiAppealsAppealIdGet(appealId: appealId);
      if (appeal == null) {
        _showSnackBar(
            'appealAdmin.error.notFound'.trParams({'message': '$appealId'}),
            isError: true);
        return;
      }
      _goToDetailPage(appeal);
    } catch (e) {
      _showSnackBar(formatAppealAdminError(e), isError: true);
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

  Widget _buildSearchBar(ThemeData themeData) {
    return Card(
      elevation: 4,
      color: themeData.colorScheme.surfaceContainerLowest,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16.0)),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Autocomplete<String>(
                    optionsBuilder: (TextEditingValue textEditingValue) async {
                      if (textEditingValue.text.isEmpty ||
                          _searchType == kAppealSearchTypeTimeRange) {
                        return const Iterable<String>.empty();
                      }
                      return await _fetchAutocompleteSuggestions(
                          textEditingValue.text);
                    },
                    onSelected: (String selection) {
                      _searchController.text = selection;
                      _refreshAppeals(query: selection);
                    },
                    fieldViewBuilder:
                        (context, controller, focusNode, onFieldSubmitted) {
                      return TextField(
                        controller: _searchController,
                        focusNode: focusNode,
                        style: themeData.textTheme.bodyMedium
                            ?.copyWith(color: themeData.colorScheme.onSurface),
                        decoration: InputDecoration(
                          hintText: appealAdminSearchHintText(_searchType),
                          hintStyle: themeData.textTheme.bodyMedium?.copyWith(
                            color: themeData.colorScheme.onSurface
                                .withValues(alpha: 0.6),
                          ),
                          prefixIcon: Icon(Icons.search,
                              color: themeData.colorScheme.primary),
                          suffixIcon: _searchController.text.isNotEmpty ||
                                  (_startTime != null && _endTime != null)
                              ? IconButton(
                                  icon: Icon(Icons.clear,
                                      color: themeData
                                          .colorScheme.onSurfaceVariant),
                                  onPressed: () {
                                    _searchController.clear();
                                    setState(() {
                                      _startTime = null;
                                      _endTime = null;
                                      _searchType =
                                          kAppealSearchTypeAppealReason;
                                    });
                                    _refreshAppeals(query: '');
                                  },
                                )
                              : null,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12.0),
                            borderSide: BorderSide.none,
                          ),
                          filled: true,
                          fillColor: themeData.colorScheme.surfaceContainer,
                          contentPadding: const EdgeInsets.symmetric(
                              vertical: 14.0, horizontal: 16.0),
                        ),
                        onChanged: (value) {
                          setState(() {});
                          _scheduleSearchRefresh(value);
                        },
                        onSubmitted: (value) => _refreshAppeals(query: value),
                        enabled: _searchType != kAppealSearchTypeTimeRange,
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
                      _searchController.clear();
                      _startTime = null;
                      _endTime = null;
                    });
                    _refreshAppeals(query: '');
                  },
                  items: <String>[
                    kAppealSearchTypeAppealReason,
                    kAppealSearchTypeAppellantName,
                    kAppealSearchTypeProcessStatus,
                    kAppealSearchTypeTimeRange,
                  ].map<DropdownMenuItem<String>>((String value) {
                    return DropdownMenuItem<String>(
                      value: value,
                      child: Text(
                        appealAdminSearchTypeLabel(value),
                        style:
                            TextStyle(color: themeData.colorScheme.onSurface),
                      ),
                    );
                  }).toList(),
                  dropdownColor: themeData.colorScheme.surfaceContainer,
                  icon: Icon(Icons.arrow_drop_down,
                      color: themeData.colorScheme.primary),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Text(
                    _startTime != null && _endTime != null
                        ? 'appeal.filter.rangeLabel'.trParams({
                            'start': formatAppealDateTime(_startTime),
                            'end': formatAppealDateTime(_endTime),
                          })
                        : 'appeal.filter.select'.tr,
                    style: themeData.textTheme.bodyMedium?.copyWith(
                      color: _startTime != null && _endTime != null
                          ? themeData.colorScheme.onSurface
                          : themeData.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ),
                IconButton(
                  icon: Icon(Icons.date_range,
                      color: themeData.colorScheme.primary),
                  tooltip: 'appeal.filter.tooltip'.tr,
                  onPressed: () async {
                    final range = await showDateRangePicker(
                      context: context,
                      firstDate: DateTime(2000),
                      lastDate: DateTime.now(),
                      locale: Get.locale ?? const Locale('en', 'US'),
                      helpText: 'appeal.filter.select'.tr,
                      cancelText: 'common.cancel'.tr,
                      confirmText: 'common.confirm'.tr,
                      fieldStartHintText: 'appeal.filter.startDate'.tr,
                      fieldEndHintText: 'appeal.filter.endDate'.tr,
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
                        _startTime = range.start;
                        _endTime = range.end;
                        _searchType = kAppealSearchTypeTimeRange;
                        _searchController.clear();
                      });
                      _refreshAppeals(query: '');
                    }
                  },
                ),
                if (_startTime != null && _endTime != null)
                  IconButton(
                    icon: Icon(Icons.clear,
                        color: themeData.colorScheme.onSurfaceVariant),
                    tooltip: 'appeal.filter.clear'.tr,
                    onPressed: () {
                      setState(() {
                        _startTime = null;
                        _endTime = null;
                        _searchType = kAppealSearchTypeAppealReason;
                        _searchController.clear();
                      });
                      _refreshAppeals(query: '');
                    },
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildViewToggle(ThemeData themeData) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Wrap(
        spacing: 8.0,
        runSpacing: 8.0,
        children: [
          ChoiceChip(
            label: Text('appealAdmin.view.appeals'.tr),
            selected: _currentView == _viewAppeals,
            onSelected: (_) => _switchView(_viewAppeals),
            selectedColor: themeData.colorScheme.primaryContainer,
          ),
          ChoiceChip(
            label: Text('appealAdmin.view.reviews'.tr),
            selected: _currentView == _viewReviews,
            onSelected: (_) => _switchView(_viewReviews),
            selectedColor: themeData.colorScheme.primaryContainer,
          ),
        ],
      ),
    );
  }

  int _reviewLevelCount(String level) => _reviewLevelCounts[level] ?? 0;

  bool _isAppealAwaitingReviewStart(AppealRecordModel appeal) {
    return normalizeAppealStatusCode(appeal.acceptanceStatus) == 'Accepted' &&
        normalizeAppealStatusCode(appeal.processStatus) == 'Unprocessed';
  }

  bool _isAppealUnderReview(AppealRecordModel appeal) {
    return normalizeAppealStatusCode(appeal.acceptanceStatus) == 'Accepted' &&
        normalizeAppealStatusCode(appeal.processStatus) == 'Under_Review';
  }

  bool _isSameDay(DateTime? left, DateTime right) {
    return left != null &&
        left.year == right.year &&
        left.month == right.month &&
        left.day == right.day;
  }

  List<AppealRecordModel> get _appealsAwaitingReviewStart {
    final items = _appeals.where(_isAppealAwaitingReviewStart).toList();
    items.sort((left, right) {
      final leftTime =
          left.appealTime ?? DateTime.fromMillisecondsSinceEpoch(0);
      final rightTime =
          right.appealTime ?? DateTime.fromMillisecondsSinceEpoch(0);
      return leftTime.compareTo(rightTime);
    });
    return items;
  }

  List<AppealRecordModel> get _appealsUnderReview {
    final items = _appeals.where(_isAppealUnderReview).toList();
    items.sort((left, right) {
      final leftTime = left.processTime ??
          left.appealTime ??
          DateTime.fromMillisecondsSinceEpoch(0);
      final rightTime = right.processTime ??
          right.appealTime ??
          DateTime.fromMillisecondsSinceEpoch(0);
      return rightTime.compareTo(leftTime);
    });
    return items;
  }

  int get _todayReviewCount {
    final now = DateTime.now();
    return _reviews
        .where((review) => _isSameDay(review.reviewTime, now))
        .length;
  }

  int get _approvedReviewCount {
    return _reviews
        .where((review) =>
            (review.reviewResult ?? '').trim().toLowerCase() == 'approved')
        .length;
  }

  int get _rejectedReviewCount {
    return _reviews
        .where((review) =>
            (review.reviewResult ?? '').trim().toLowerCase() == 'rejected')
        .length;
  }

  Future<void> _loadReviewWorkbenchSummary({bool showLoading = true}) async {
    if (!_isAdmin) {
      return;
    }
    if (showLoading) {
      setState(() {
        _isReviewWorkbenchLoading = true;
        _reviewWorkbenchError = '';
      });
    } else {
      setState(() {
        _reviewWorkbenchError = '';
      });
    }

    try {
      if (!await _validateJwtToken()) {
        Get.offAllNamed(Routes.login);
        return;
      }
      await appealApi.initializeWithJwt();
      final counts = await Future.wait<int>([
        appealApi.apiAppealsReviewsCountGet(reviewLevel: _reviewLevelPrimary),
        appealApi.apiAppealsReviewsCountGet(reviewLevel: _reviewLevelSecondary),
        appealApi.apiAppealsReviewsCountGet(reviewLevel: _reviewLevelFinal),
      ]);
      if (!mounted) {
        return;
      }
      setState(() {
        _reviewLevelCounts = {
          _reviewLevelPrimary: counts[0],
          _reviewLevelSecondary: counts[1],
          _reviewLevelFinal: counts[2],
        };
      });
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _reviewWorkbenchError = 'appealAdmin.review.workbench.loadFailed'
            .trParams({'error': formatAppealAdminError(e)});
      });
    } finally {
      if (mounted && showLoading) {
        setState(() => _isReviewWorkbenchLoading = false);
      }
    }
  }

  Future<void> _openAppealsByProcessStatus(String status) async {
    final normalizedStatus = normalizeAppealStatusCode(status);
    setState(() {
      _currentView = _viewAppeals;
      _searchType = kAppealSearchTypeProcessStatus;
      _startTime = null;
      _endTime = null;
      _searchController.value = TextEditingValue(
        text: normalizedStatus,
        selection: TextSelection.collapsed(offset: normalizedStatus.length),
      );
    });
    await _refreshAppeals(query: normalizedStatus);
  }

  Future<void> _showTodayReviews() async {
    final now = DateTime.now();
    setState(() {
      _currentView = _viewReviews;
      _reviewSearchType = kAppealReviewSearchTypeTimeRange;
      _reviewStartTime = DateTime(now.year, now.month, now.day);
      _reviewEndTime = DateTime(now.year, now.month, now.day);
      _reviewSearchController.clear();
    });
    await _refreshReviews(query: '');
    await _loadReviewWorkbenchSummary(showLoading: false);
  }

  Widget _buildReviewWorkbenchMetricCard({
    required ThemeData themeData,
    required String label,
    required String value,
    required IconData icon,
    Color? accentColor,
    String? helperText,
    VoidCallback? onTap,
  }) {
    final effectiveAccent = accentColor ?? themeData.colorScheme.primary;
    return SizedBox(
      width: 212,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16.0),
        child: Container(
          padding: const EdgeInsets.all(16.0),
          decoration: BoxDecoration(
            color: themeData.colorScheme.surfaceContainer,
            borderRadius: BorderRadius.circular(16.0),
            border: Border.all(
              color: effectiveAccent.withValues(alpha: 0.24),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(icon, color: effectiveAccent, size: 20),
                  const Spacer(),
                  if (onTap != null)
                    Icon(
                      CupertinoIcons.chevron_right,
                      size: 14,
                      color: themeData.colorScheme.onSurfaceVariant,
                    ),
                ],
              ),
              const SizedBox(height: 16),
              Text(
                value,
                style: themeData.textTheme.headlineSmall?.copyWith(
                  color: themeData.colorScheme.onSurface,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                label,
                style: themeData.textTheme.titleSmall?.copyWith(
                  color: themeData.colorScheme.onSurface,
                  fontWeight: FontWeight.w600,
                ),
              ),
              if (helperText != null) ...[
                const SizedBox(height: 4),
                Text(
                  helperText,
                  style: themeData.textTheme.bodySmall?.copyWith(
                    color: themeData.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildReviewWorkbenchActionChip({
    required ThemeData themeData,
    required String label,
    required IconData icon,
    required VoidCallback onPressed,
  }) {
    return ActionChip(
      avatar: Icon(icon, size: 18, color: themeData.colorScheme.primary),
      label: Text(label),
      onPressed: onPressed,
      backgroundColor: themeData.colorScheme.surfaceContainer,
      side: BorderSide(color: themeData.colorScheme.outlineVariant),
      labelStyle: themeData.textTheme.bodyMedium?.copyWith(
        color: themeData.colorScheme.onSurface,
      ),
    );
  }

  Widget _buildReviewWorkbenchQueueItem(
    AppealRecordModel appeal,
    ThemeData themeData,
  ) {
    final status = localizeAppealStatus(appeal.processStatus);
    final time = formatAppealDateTime(appeal.processTime ?? appeal.appealTime);
    return InkWell(
      onTap: () => _goToDetailPage(appeal),
      borderRadius: BorderRadius.circular(12.0),
      child: Container(
        width: double.infinity,
        margin: const EdgeInsets.only(bottom: 10.0),
        padding: const EdgeInsets.all(14.0),
        decoration: BoxDecoration(
          color: themeData.colorScheme.surfaceContainer,
          borderRadius: BorderRadius.circular(12.0),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'appeal.card.title'.trParams({
                'name': appeal.appellantName ?? 'common.unknown'.tr,
                'id': '${appeal.appealId ?? 'common.none'.tr}',
              }),
              style: themeData.textTheme.titleSmall?.copyWith(
                color: themeData.colorScheme.onSurface,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'appealAdmin.review.queue.reason'.trParams({
                'value': appeal.appealReason ?? 'common.notFilled'.tr,
              }),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: themeData.textTheme.bodyMedium?.copyWith(
                color: themeData.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'appealAdmin.review.queue.status'.trParams({'value': status}),
              style: themeData.textTheme.bodyMedium?.copyWith(
                color: themeData.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'appealAdmin.review.queue.time'.trParams({'value': time}),
              style: themeData.textTheme.bodyMedium?.copyWith(
                color: themeData.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildReviewWorkbench(ThemeData themeData) {
    final pendingStartAppeals = _appealsAwaitingReviewStart;
    final underReviewAppeals = _appealsUnderReview;
    final queueItems = [
      ...pendingStartAppeals.take(3),
      ...underReviewAppeals
          .where((appeal) => !pendingStartAppeals
              .any((item) => item.appealId == appeal.appealId))
          .take(3),
    ];

    return Card(
      elevation: 4,
      color: themeData.colorScheme.surfaceContainerLowest,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16.0)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
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
                        'appealAdmin.review.workbench.title'.tr,
                        style: themeData.textTheme.titleLarge?.copyWith(
                          color: themeData.colorScheme.onSurface,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'appealAdmin.review.workbench.subtitle'.tr,
                        style: themeData.textTheme.bodyMedium?.copyWith(
                          color: themeData.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  tooltip: 'appealAdmin.review.quick.refreshWorkbench'.tr,
                  onPressed: () async {
                    await _refreshAppeals(query: _activeQuery);
                    if (!mounted) {
                      return;
                    }
                    await _loadReviewWorkbenchSummary();
                    if (!mounted) {
                      return;
                    }
                    await _refreshReviews(query: _activeReviewQuery);
                  },
                  icon: Icon(Icons.sync, color: themeData.colorScheme.primary),
                ),
              ],
            ),
            const SizedBox(height: 16.0),
            if (_isReviewWorkbenchLoading)
              Center(
                child: CupertinoActivityIndicator(
                  color: themeData.colorScheme.primary,
                  radius: 14.0,
                ),
              )
            else ...[
              if (_reviewWorkbenchError.isNotEmpty) ...[
                Container(
                  width: double.infinity,
                  margin: const EdgeInsets.only(bottom: 12.0),
                  padding: const EdgeInsets.all(12.0),
                  decoration: BoxDecoration(
                    color: themeData.colorScheme.errorContainer,
                    borderRadius: BorderRadius.circular(12.0),
                  ),
                  child: Text(
                    _reviewWorkbenchError,
                    style: themeData.textTheme.bodyMedium?.copyWith(
                      color: themeData.colorScheme.onErrorContainer,
                    ),
                  ),
                ),
              ],
              Wrap(
                spacing: 12.0,
                runSpacing: 12.0,
                children: [
                  _buildReviewWorkbenchMetricCard(
                    themeData: themeData,
                    label: 'appealAdmin.review.metric.primary'.tr,
                    value: '${_reviewLevelCount(_reviewLevelPrimary)}',
                    icon: CupertinoIcons.layers_alt,
                    helperText: 'appealAdmin.review.metric.primary.helper'.tr,
                  ),
                  _buildReviewWorkbenchMetricCard(
                    themeData: themeData,
                    label: 'appealAdmin.review.metric.secondary'.tr,
                    value: '${_reviewLevelCount(_reviewLevelSecondary)}',
                    icon: CupertinoIcons.square_grid_2x2,
                    helperText: 'appealAdmin.review.metric.secondary.helper'.tr,
                  ),
                  _buildReviewWorkbenchMetricCard(
                    themeData: themeData,
                    label: 'appealAdmin.review.metric.final'.tr,
                    value: '${_reviewLevelCount(_reviewLevelFinal)}',
                    icon: CupertinoIcons.check_mark_circled_solid,
                    helperText: 'appealAdmin.review.metric.final.helper'.tr,
                  ),
                  _buildReviewWorkbenchMetricCard(
                    themeData: themeData,
                    label: 'appealAdmin.review.metric.today'.tr,
                    value: '$_todayReviewCount',
                    icon: CupertinoIcons.calendar_today,
                    accentColor: Colors.teal,
                    helperText: 'appealAdmin.review.metric.today.helper'.tr,
                    onTap: () {
                      _showTodayReviews();
                    },
                  ),
                  _buildReviewWorkbenchMetricCard(
                    themeData: themeData,
                    label: 'appealAdmin.review.metric.pendingStart'.tr,
                    value: '${pendingStartAppeals.length}',
                    icon: CupertinoIcons.play_circle,
                    accentColor: Colors.orange,
                    helperText:
                        'appealAdmin.review.metric.pendingStart.helper'.tr,
                    onTap: () {
                      _openAppealsByProcessStatus('Unprocessed');
                    },
                  ),
                  _buildReviewWorkbenchMetricCard(
                    themeData: themeData,
                    label: 'appealAdmin.review.metric.inProgress'.tr,
                    value: '${underReviewAppeals.length}',
                    icon: CupertinoIcons.time,
                    accentColor: Colors.indigo,
                    helperText:
                        'appealAdmin.review.metric.inProgress.helper'.tr,
                    onTap: () {
                      _openAppealsByProcessStatus('Under_Review');
                    },
                  ),
                ],
              ),
              const SizedBox(height: 16.0),
              Wrap(
                spacing: 8.0,
                runSpacing: 8.0,
                children: [
                  _buildReviewWorkbenchActionChip(
                    themeData: themeData,
                    label: 'appealAdmin.review.quick.today'.tr,
                    icon: CupertinoIcons.calendar,
                    onPressed: () {
                      _showTodayReviews();
                    },
                  ),
                  _buildReviewWorkbenchActionChip(
                    themeData: themeData,
                    label: 'appealAdmin.review.quick.pendingStart'.tr,
                    icon: CupertinoIcons.play_arrow_solid,
                    onPressed: () {
                      _openAppealsByProcessStatus('Unprocessed');
                    },
                  ),
                  _buildReviewWorkbenchActionChip(
                    themeData: themeData,
                    label: 'appealAdmin.review.quick.inProgress'.tr,
                    icon: CupertinoIcons.clock,
                    onPressed: () {
                      _openAppealsByProcessStatus('Under_Review');
                    },
                  ),
                ],
              ),
              const SizedBox(height: 16.0),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14.0),
                decoration: BoxDecoration(
                  color: themeData.colorScheme.surfaceContainer,
                  borderRadius: BorderRadius.circular(14.0),
                ),
                child: Wrap(
                  spacing: 16.0,
                  runSpacing: 8.0,
                  children: [
                    Text(
                      'appealAdmin.review.metric.visibleTotal'
                          .trParams({'count': '${_reviews.length}'}),
                      style: themeData.textTheme.bodyMedium?.copyWith(
                        color: themeData.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    Text(
                      'appealAdmin.review.metric.visibleApproved'
                          .trParams({'count': '$_approvedReviewCount'}),
                      style: themeData.textTheme.bodyMedium?.copyWith(
                        color: Colors.green,
                      ),
                    ),
                    Text(
                      'appealAdmin.review.metric.visibleRejected'
                          .trParams({'count': '$_rejectedReviewCount'}),
                      style: themeData.textTheme.bodyMedium?.copyWith(
                        color: Colors.red,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16.0),
              Text(
                'appealAdmin.review.queue.title'.tr,
                style: themeData.textTheme.titleMedium?.copyWith(
                  color: themeData.colorScheme.onSurface,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 10.0),
              if (queueItems.isEmpty)
                Text(
                  'appealAdmin.review.queue.empty'.tr,
                  style: themeData.textTheme.bodyMedium?.copyWith(
                    color: themeData.colorScheme.onSurfaceVariant,
                  ),
                )
              else
                Column(
                  children: queueItems
                      .map((appeal) =>
                          _buildReviewWorkbenchQueueItem(appeal, themeData))
                      .toList(),
                ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildReviewSearchBar(ThemeData themeData) {
    return Card(
      elevation: 4,
      color: themeData.colorScheme.surfaceContainerLowest,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16.0)),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Autocomplete<String>(
                    optionsBuilder: (TextEditingValue textEditingValue) async {
                      if (textEditingValue.text.isEmpty ||
                          _reviewSearchType ==
                              kAppealReviewSearchTypeTimeRange) {
                        return const Iterable<String>.empty();
                      }
                      return _fetchReviewAutocompleteSuggestions(
                        textEditingValue.text,
                      );
                    },
                    onSelected: (String selection) {
                      _reviewSearchController.text = selection;
                      _refreshReviews(query: selection);
                    },
                    fieldViewBuilder:
                        (context, textController, focusNode, onFieldSubmitted) {
                      return TextField(
                        controller: _reviewSearchController,
                        focusNode: focusNode,
                        style: themeData.textTheme.bodyMedium
                            ?.copyWith(color: themeData.colorScheme.onSurface),
                        decoration: InputDecoration(
                          hintText:
                              appealReviewSearchHintText(_reviewSearchType),
                          hintStyle: themeData.textTheme.bodyMedium?.copyWith(
                            color: themeData.colorScheme.onSurface
                                .withValues(alpha: 0.6),
                          ),
                          prefixIcon: Icon(
                            Icons.search,
                            color: themeData.colorScheme.primary,
                          ),
                          suffixIcon: _reviewSearchController.text.isNotEmpty ||
                                  (_reviewStartTime != null &&
                                      _reviewEndTime != null)
                              ? IconButton(
                                  icon: Icon(
                                    Icons.clear,
                                    color:
                                        themeData.colorScheme.onSurfaceVariant,
                                  ),
                                  onPressed: () {
                                    _reviewSearchController.clear();
                                    setState(() {
                                      _reviewStartTime = null;
                                      _reviewEndTime = null;
                                      _reviewSearchType =
                                          kAppealReviewSearchTypeReviewer;
                                    });
                                    _refreshReviews(query: '');
                                  },
                                )
                              : null,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12.0),
                            borderSide: BorderSide.none,
                          ),
                          filled: true,
                          fillColor: themeData.colorScheme.surfaceContainer,
                          contentPadding: const EdgeInsets.symmetric(
                            vertical: 14.0,
                            horizontal: 16.0,
                          ),
                        ),
                        onChanged: (value) {
                          setState(() {});
                          _scheduleReviewSearchRefresh(value);
                        },
                        onSubmitted: (value) => _refreshReviews(query: value),
                        enabled: _reviewSearchType !=
                            kAppealReviewSearchTypeTimeRange,
                      );
                    },
                  ),
                ),
                const SizedBox(width: 8),
                DropdownButton<String>(
                  value: _reviewSearchType,
                  onChanged: (String? newValue) {
                    setState(() {
                      _reviewSearchType = newValue!;
                      _reviewSearchController.clear();
                      _reviewStartTime = null;
                      _reviewEndTime = null;
                    });
                    _refreshReviews(query: '');
                  },
                  items: <String>[
                    kAppealReviewSearchTypeReviewer,
                    kAppealReviewSearchTypeReviewerDept,
                    kAppealReviewSearchTypeTimeRange,
                  ].map<DropdownMenuItem<String>>((String value) {
                    return DropdownMenuItem<String>(
                      value: value,
                      child: Text(
                        appealReviewSearchTypeLabel(value),
                        style:
                            TextStyle(color: themeData.colorScheme.onSurface),
                      ),
                    );
                  }).toList(),
                  dropdownColor: themeData.colorScheme.surfaceContainer,
                  icon: Icon(Icons.arrow_drop_down,
                      color: themeData.colorScheme.primary),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Text(
                    _reviewStartTime != null && _reviewEndTime != null
                        ? 'appeal.filter.rangeLabel'.trParams({
                            'start': formatAppealDateTime(_reviewStartTime),
                            'end': formatAppealDateTime(_reviewEndTime),
                          })
                        : 'appeal.filter.select'.tr,
                    style: themeData.textTheme.bodyMedium?.copyWith(
                      color: _reviewStartTime != null && _reviewEndTime != null
                          ? themeData.colorScheme.onSurface
                          : themeData.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ),
                IconButton(
                  icon: Icon(Icons.date_range,
                      color: themeData.colorScheme.primary),
                  tooltip: 'appeal.filter.tooltip'.tr,
                  onPressed: () async {
                    final range = await showDateRangePicker(
                      context: context,
                      firstDate: DateTime(2000),
                      lastDate: DateTime.now(),
                      locale: Get.locale ?? const Locale('en', 'US'),
                      helpText: 'appeal.filter.select'.tr,
                      cancelText: 'common.cancel'.tr,
                      confirmText: 'common.confirm'.tr,
                      fieldStartHintText: 'appeal.filter.startDate'.tr,
                      fieldEndHintText: 'appeal.filter.endDate'.tr,
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
                        _reviewStartTime = range.start;
                        _reviewEndTime = range.end;
                        _reviewSearchType = kAppealReviewSearchTypeTimeRange;
                        _reviewSearchController.clear();
                      });
                      _refreshReviews(query: '');
                    }
                  },
                ),
                if (_reviewStartTime != null && _reviewEndTime != null)
                  IconButton(
                    icon: Icon(Icons.clear,
                        color: themeData.colorScheme.onSurfaceVariant),
                    tooltip: 'appeal.filter.clear'.tr,
                    onPressed: () {
                      setState(() {
                        _reviewStartTime = null;
                        _reviewEndTime = null;
                        _reviewSearchType = kAppealReviewSearchTypeReviewer;
                        _reviewSearchController.clear();
                      });
                      _refreshReviews(query: '');
                    },
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAppealCard(AppealRecordModel appeal, ThemeData themeData) {
    final acceptance = normalizeAppealStatusCode(appeal.acceptanceStatus);
    final displayStatus = acceptance == appealPendingStatusCode() ||
            acceptance == appealRejectedStatusCode() ||
            acceptance == 'Need_Supplement'
        ? localizeAppealStatus(appeal.acceptanceStatus)
        : localizeAppealStatus(appeal.processStatus);
    final isRejected = isRejectedAppealStatus(appeal.acceptanceStatus) ||
        isRejectedAppealStatus(appeal.processStatus);
    return Card(
      elevation: 4,
      color: themeData.colorScheme.surfaceContainerLowest,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16.0)),
      margin: const EdgeInsets.symmetric(vertical: 8.0),
      child: ListTile(
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
        title: Text(
          'appeal.card.title'.trParams({
            'name': appeal.appellantName ?? 'common.unknown'.tr,
            'id': '${appeal.appealId ?? 'common.none'.tr}',
          }),
          style: themeData.textTheme.titleMedium?.copyWith(
            color: themeData.colorScheme.onSurface,
            fontWeight: FontWeight.bold,
          ),
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 4.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'appealAdmin.card.reason'.trParams({
                  'value': appeal.appealReason ?? 'common.none'.tr,
                }),
                style: themeData.textTheme.bodyMedium?.copyWith(
                  color: themeData.colorScheme.onSurfaceVariant,
                ),
              ),
              Text(
                'appealAdmin.card.status'.trParams({
                  'value': displayStatus,
                }),
                style: themeData.textTheme.bodyMedium?.copyWith(
                  color: isApprovedAppealStatus(appeal.processStatus)
                      ? Colors.green
                      : isRejected
                          ? Colors.red
                          : themeData.colorScheme.onSurfaceVariant,
                ),
              ),
              Text(
                'appealAdmin.card.time'.trParams({
                  'value': formatAppealDateTime(appeal.appealTime),
                }),
                style: themeData.textTheme.bodyMedium?.copyWith(
                  color: themeData.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
        trailing: Icon(
          CupertinoIcons.forward,
          color: themeData.colorScheme.primary,
          size: 18,
        ),
        onTap: () => _goToDetailPage(appeal),
      ),
    );
  }

  Widget _buildReviewCard(AppealReviewModel review, ThemeData themeData) {
    final reviewResult = localizeAppealReviewResult(review.reviewResult);
    final resultColor = (review.reviewResult ?? '').toLowerCase() == 'approved'
        ? Colors.green
        : (review.reviewResult ?? '').toLowerCase() == 'rejected'
            ? Colors.red
            : themeData.colorScheme.onSurfaceVariant;
    return Card(
      elevation: 4,
      color: themeData.colorScheme.surfaceContainerLowest,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16.0)),
      margin: const EdgeInsets.symmetric(vertical: 8.0),
      child: ListTile(
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
        title: Text(
          'appealAdmin.review.card.title'.trParams({
            'appealId': '${review.appealId ?? 'common.none'.tr}',
            'level': localizeAppealReviewLevel(review.reviewLevel),
          }),
          style: themeData.textTheme.titleMedium?.copyWith(
            color: themeData.colorScheme.onSurface,
            fontWeight: FontWeight.bold,
          ),
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 4.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'appealAdmin.review.card.result'.trParams({
                  'value': reviewResult,
                }),
                style: themeData.textTheme.bodyMedium?.copyWith(
                  color: resultColor,
                  fontWeight: FontWeight.w600,
                ),
              ),
              Text(
                'appealAdmin.review.card.reviewer'.trParams({
                  'value': review.reviewer ?? 'common.notFilled'.tr,
                }),
                style: themeData.textTheme.bodyMedium?.copyWith(
                  color: themeData.colorScheme.onSurfaceVariant,
                ),
              ),
              Text(
                'appealAdmin.review.card.reviewerDept'.trParams({
                  'value': review.reviewerDept ?? 'common.notFilled'.tr,
                }),
                style: themeData.textTheme.bodyMedium?.copyWith(
                  color: themeData.colorScheme.onSurfaceVariant,
                ),
              ),
              Text(
                'appealAdmin.review.card.time'.trParams({
                  'value': formatAppealDateTime(review.reviewTime),
                }),
                style: themeData.textTheme.bodyMedium?.copyWith(
                  color: themeData.colorScheme.onSurfaceVariant,
                ),
              ),
              Text(
                'appealAdmin.review.card.opinion'.trParams({
                  'value': review.reviewOpinion ?? 'common.notFilled'.tr,
                }),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: themeData.textTheme.bodyMedium?.copyWith(
                  color: themeData.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
        trailing: Icon(
          CupertinoIcons.forward,
          color: themeData.colorScheme.primary,
          size: 18,
        ),
        onTap: () => _openAppealFromReview(review),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final themeData = controller.currentBodyTheme.value;
      final activeErrorMessage =
          _currentView == _viewAppeals ? _errorMessage : _reviewErrorMessage;
      final isCurrentListEmpty = _currentView == _viewAppeals
          ? _filteredAppeals.isEmpty
          : _filteredReviews.isEmpty;
      final hasLoadingTail = _isLoading &&
          ((_currentView == _viewAppeals && _appeals.isNotEmpty) ||
              (_currentView == _viewReviews && _reviews.isNotEmpty));
      final currentItemCount = (_currentView == _viewAppeals
              ? _filteredAppeals.length
              : _filteredReviews.length) +
          (hasLoadingTail ? 1 : 0);
      final showBlockingError = activeErrorMessage.isNotEmpty &&
          activeErrorMessage != 'appeal.empty'.tr &&
          activeErrorMessage != 'appeal.empty.filtered'.tr &&
          activeErrorMessage != 'appealAdmin.review.empty'.tr &&
          activeErrorMessage != 'appealAdmin.review.empty.filtered'.tr;

      return DashboardPageTemplate(
        theme: themeData,
        title: 'appealAdmin.page.title'.tr,
        pageType: DashboardPageType.admin,
        bodyIsScrollable: true,
        padding: EdgeInsets.zero,
        actions: [
          DashboardPageBarAction(
            icon: Icons.refresh,
            onPressed: _refreshCurrentView,
            tooltip: 'page.refreshList'.tr,
          ),
        ],
        onThemeToggle: controller.toggleBodyTheme,
        body: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _buildViewToggle(themeData),
              const SizedBox(height: 12),
              if (_currentView == _viewReviews) ...[
                _buildReviewWorkbench(themeData),
                const SizedBox(height: 12),
              ],
              _currentView == _viewAppeals
                  ? _buildSearchBar(themeData)
                  : _buildReviewSearchBar(themeData),
              const SizedBox(height: 20),
              Expanded(
                child: _isLoading &&
                        ((_currentView == _viewAppeals && _appeals.isEmpty) ||
                            (_currentView == _viewReviews && _reviews.isEmpty))
                    ? Center(
                        child: CupertinoActivityIndicator(
                          color: themeData.colorScheme.primary,
                          radius: 16.0,
                        ),
                      )
                    : showBlockingError
                        ? Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(
                                  CupertinoIcons.exclamationmark_triangle,
                                  color: themeData.colorScheme.error,
                                  size: 48,
                                ),
                                const SizedBox(height: 16),
                                Text(
                                  activeErrorMessage,
                                  style:
                                      themeData.textTheme.titleMedium?.copyWith(
                                    color: themeData.colorScheme.error,
                                    fontWeight: FontWeight.w500,
                                  ),
                                  textAlign: TextAlign.center,
                                ),
                                if (shouldShowAppealAdminReloginAction(
                                    activeErrorMessage))
                                  Padding(
                                    padding: const EdgeInsets.only(top: 20.0),
                                    child: ElevatedButton(
                                      onPressed: () =>
                                          Get.offAllNamed(Routes.login),
                                      style: ElevatedButton.styleFrom(
                                        backgroundColor:
                                            themeData.colorScheme.primary,
                                        foregroundColor:
                                            themeData.colorScheme.onPrimary,
                                        shape: RoundedRectangleBorder(
                                            borderRadius:
                                                BorderRadius.circular(12.0)),
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 24.0, vertical: 12.0),
                                      ),
                                      child:
                                          Text('appealAdmin.action.relogin'.tr),
                                    ),
                                  ),
                              ],
                            ),
                          )
                        : isCurrentListEmpty
                            ? Center(
                                child: Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(
                                      CupertinoIcons.doc,
                                      color: themeData
                                          .colorScheme.onSurfaceVariant,
                                      size: 48,
                                    ),
                                    const SizedBox(height: 16),
                                    Text(
                                      activeErrorMessage.isNotEmpty
                                          ? activeErrorMessage
                                          : _currentView == _viewAppeals
                                              ? 'appeal.empty'.tr
                                              : 'appealAdmin.review.empty'.tr,
                                      style: themeData.textTheme.titleMedium
                                          ?.copyWith(
                                        color: themeData
                                            .colorScheme.onSurfaceVariant,
                                        fontWeight: FontWeight.w500,
                                      ),
                                      textAlign: TextAlign.center,
                                    ),
                                  ],
                                ),
                              )
                            : CupertinoScrollbar(
                                controller: _scrollController,
                                thumbVisibility: true,
                                thickness: 6.0,
                                thicknessWhileDragging: 10.0,
                                child: RefreshIndicator(
                                  onRefresh: _refreshCurrentView,
                                  color: themeData.colorScheme.primary,
                                  backgroundColor:
                                      themeData.colorScheme.surfaceContainer,
                                  child: ListView.builder(
                                    controller: _scrollController,
                                    itemCount: currentItemCount,
                                    itemBuilder: (context, index) {
                                      final currentItemsLength =
                                          _currentView == _viewAppeals
                                              ? _filteredAppeals.length
                                              : _filteredReviews.length;
                                      if (hasLoadingTail &&
                                          index >= currentItemsLength) {
                                        return const Padding(
                                          padding: EdgeInsets.all(8.0),
                                          child: Center(
                                            child: CupertinoActivityIndicator(),
                                          ),
                                        );
                                      }
                                      if (_currentView == _viewAppeals) {
                                        final appeal = _filteredAppeals[index];
                                        return _buildAppealCard(
                                            appeal, themeData);
                                      }
                                      final review = _filteredReviews[index];
                                      return _buildReviewCard(
                                          review, themeData);
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

class AppealDetailPage extends StatefulWidget {
  final AppealRecordModel appeal;
  final Function(AppealRecordModel)? onAppealUpdated;

  const AppealDetailPage(
      {super.key, required this.appeal, this.onAppealUpdated});

  @override
  State<AppealDetailPage> createState() => _AppealDetailPageState();
}

class _AppealDetailPageState extends State<AppealDetailPage> {
  static const int _detailReviewPageSize = 50;

  final AppealManagementControllerApi appealApi =
      AppealManagementControllerApi();
  final SessionHelper _sessionHelper = SessionHelper();
  final TextEditingController _rejectionReasonController =
      TextEditingController();
  final List<AppealReviewModel> _reviewHistory = [];
  bool _isLoading = false;
  bool _isReviewHistoryLoading = false;
  bool _isAdmin = false;
  String _errorMessage = '';
  String _reviewHistoryError = '';
  final DashboardController controller = Get.find<DashboardController>();

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  @override
  void dispose() {
    _rejectionReasonController.dispose();
    super.dispose();
  }

  Future<bool> _validateJwtToken() async {
    String? jwtToken = (await AuthTokenStore.instance.getJwtToken());
    if (jwtToken == null || jwtToken.isEmpty) {
      setState(
          () => _errorMessage = 'appealAdmin.error.unauthorizedMissing'.tr);
      return false;
    }
    try {
      final decodedToken = JwtDecoder.decode(jwtToken);
      if (JwtDecoder.isExpired(jwtToken)) {
        jwtToken = await _refreshJwtToken();
        if (jwtToken == null) {
          setState(() => _errorMessage = 'appealAdmin.error.expired'.tr);
          return false;
        }
        await AuthTokenStore.instance.setJwtToken(jwtToken);
        if (JwtDecoder.isExpired(jwtToken)) {
          setState(
              () => _errorMessage = 'appealAdmin.error.refreshedExpired'.tr);
          return false;
        }
        await appealApi.initializeWithJwt();
      }
      developer
          .log('JWT Token validated successfully: sub=${decodedToken['sub']}');
      return true;
    } catch (e) {
      setState(() => _errorMessage = 'appealAdmin.error.invalidLogin'.trParams({
            'error': formatAppealErrorDetail(e),
          }));
      developer.log('JWT validation failed: $e',
          stackTrace: StackTrace.current);
      return false;
    }
  }

  Future<String?> _refreshJwtToken() async {
    final newJwt = await _sessionHelper.refreshJwtToken();
    if (newJwt != null) {
      developer.log('JWT token refreshed successfully');
    } else {
      developer.log('Failed to refresh JWT token');
    }
    return newJwt;
  }

  Future<void> _initialize() async {
    setState(() => _isLoading = true);
    try {
      if (!await _validateJwtToken()) {
        Get.offAllNamed(Routes.login);
        return;
      }
      await appealApi.initializeWithJwt();
      await _checkUserRole();
      if (_isAdmin) {
        await _loadReviewHistory();
      }
    } catch (e) {
      setState(() => _errorMessage = 'appealAdmin.error.initFailed'.trParams({
            'error': formatAppealErrorDetail(e),
          }));
      developer.log('Initialization failed: $e',
          stackTrace: StackTrace.current);
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _loadReviewHistory() async {
    final appealId = widget.appeal.appealId;
    if (appealId == null) {
      setState(() => _reviewHistoryError = 'appeal.detail.reviewEmpty'.tr);
      return;
    }
    setState(() {
      _isReviewHistoryLoading = true;
      _reviewHistoryError = '';
      _reviewHistory.clear();
    });
    try {
      final reviews = await appealApi.apiAppealsAppealIdReviewsGet(
        appealId: appealId,
        page: 1,
        size: _detailReviewPageSize,
      );
      setState(() {
        _reviewHistory.addAll(reviews);
        if (_reviewHistory.isEmpty) {
          _reviewHistoryError = 'appeal.detail.reviewEmpty'.tr;
        }
      });
    } catch (e) {
      setState(() {
        _reviewHistoryError = 'appealAdmin.review.loadFailed'
            .trParams({'error': formatAppealAdminError(e)});
      });
    } finally {
      if (mounted) {
        setState(() => _isReviewHistoryLoading = false);
      }
    }
  }

  Future<void> _checkUserRole() async {
    try {
      if (!await _validateJwtToken()) {
        Get.offAllNamed(Routes.login);
        return;
      }
      final roles = await _sessionHelper.fetchCurrentRoles();
      final hasAdminAccess = hasAnyRole(roles, const [
        'SUPER_ADMIN',
        'ADMIN',
        'APPEAL_REVIEWER',
      ]);
      setState(() {
        _isAdmin = hasAdminAccess;
        if (!hasAdminAccess) {
          _errorMessage = 'appealAdmin.error.adminOnly'.tr;
        }
      });
    } catch (e) {
      setState(
          () => _errorMessage = 'appealAdmin.error.roleCheckFailed'.trParams({
                'error': formatAppealErrorDetail(e),
              }));
      developer.log('Role check failed: $e', stackTrace: StackTrace.current);
    }
  }

  Future<void> _approveAppeal(int appealId) async {
    await _submitFinalReview(
      appealId: appealId,
      reviewResult: 'Approved',
      successMessage: 'appealAdmin.success.approved'.tr,
    );
  }

  Future<void> _acceptAppeal(int appealId) async {
    await _triggerAcceptanceEvent(
      appealId: appealId,
      event: 'ACCEPT',
      successMessage: 'lookup.appealAcceptanceEventType.accept'.tr,
    );
  }

  Future<void> _requestSupplement(int appealId) async {
    await _showAcceptanceReasonDialog(
      appealId: appealId,
      titleKey: 'appealAdmin.dialog.requestSupplementTitle',
      fieldLabelKey: 'appealAdmin.field.supplementReason',
      validationMessageKey: 'appealAdmin.validation.supplementReasonRequired',
      confirmLabelKey: 'appealAdmin.action.confirmRequestSupplement',
      event: 'REQUEST_SUPPLEMENT',
      successMessage: 'appealAdmin.success.supplementRequested'.tr,
    );
  }

  Future<void> _startReview(int appealId) async {
    await _triggerProcessEvent(
      appealId: appealId,
      event: 'START_REVIEW',
      successMessage: 'lookup.appealProcessEventType.startReview'.tr,
    );
  }

  Future<void> _rejectAcceptedAppeal(int appealId) async {
    await _showAcceptanceReasonDialog(
      appealId: appealId,
      titleKey: 'appealAdmin.dialog.rejectTitle',
      fieldLabelKey: 'appealAdmin.field.rejectionReason',
      validationMessageKey: 'appealAdmin.validation.rejectionReasonRequired',
      confirmLabelKey: 'appealAdmin.action.confirmReject',
      event: 'REJECT',
      successMessage: 'appealAdmin.success.acceptanceRejected'.tr,
      useErrorStyle: true,
    );
  }

  Future<void> _showAcceptanceReasonDialog({
    required int appealId,
    required String titleKey,
    required String fieldLabelKey,
    required String validationMessageKey,
    required String confirmLabelKey,
    required String event,
    required String successMessage,
    bool useErrorStyle = false,
  }) async {
    final themeData = controller.currentBodyTheme.value;
    _rejectionReasonController.clear();
    showDialog(
      context: context,
      builder: (ctx) => Theme(
        data: themeData,
        child: Dialog(
          backgroundColor: themeData.colorScheme.surfaceContainerLowest,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(16.0)),
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  titleKey.tr,
                  style: themeData.textTheme.titleLarge?.copyWith(
                    color: themeData.colorScheme.onSurface,
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16.0),
                TextField(
                  controller: _rejectionReasonController,
                  decoration: InputDecoration(
                    labelText: fieldLabelKey.tr,
                    labelStyle: themeData.textTheme.bodyMedium?.copyWith(
                      color: themeData.colorScheme.onSurfaceVariant,
                    ),
                    filled: true,
                    fillColor: themeData.colorScheme.surfaceContainer,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12.0),
                      borderSide: BorderSide.none,
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12.0),
                      borderSide: BorderSide(
                        color: themeData.colorScheme.primary,
                        width: 2.0,
                      ),
                    ),
                  ),
                  maxLines: 3,
                  style: themeData.textTheme.bodyMedium?.copyWith(
                    color: themeData.colorScheme.onSurface,
                  ),
                ),
                const SizedBox(height: 20.0),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    TextButton(
                      onPressed: () => Navigator.pop(ctx),
                      child: Text(
                        'common.cancel'.tr,
                        style: themeData.textTheme.labelLarge?.copyWith(
                          color: themeData.colorScheme.onSurfaceVariant,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    ElevatedButton(
                      onPressed: () async {
                        final reason = _rejectionReasonController.text.trim();
                        if (reason.isEmpty) {
                          _showSnackBar(
                            validationMessageKey.tr,
                            isError: true,
                          );
                          return;
                        }
                        if (widget.appeal.appealId == null) {
                          _showSnackBar(
                            'appealAdmin.error.invalidAppealId'.tr,
                            isError: true,
                          );
                          Navigator.pop(ctx);
                          return;
                        }
                        final didUpdate = await _triggerAcceptanceEvent(
                          appealId: appealId,
                          event: event,
                          rejectionReason: reason,
                          successMessage: successMessage,
                          closePage: false,
                        );
                        if (didUpdate && mounted) {
                          Navigator.pop(ctx);
                          Navigator.pop(context, true);
                        }
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: useErrorStyle
                            ? themeData.colorScheme.error
                            : themeData.colorScheme.primary,
                        foregroundColor: useErrorStyle
                            ? themeData.colorScheme.onError
                            : themeData.colorScheme.onPrimary,
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12.0)),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 20.0, vertical: 12.0),
                      ),
                      child: Text(
                        confirmLabelKey.tr,
                        style: themeData.textTheme.labelLarge?.copyWith(
                          color: useErrorStyle
                              ? themeData.colorScheme.onError
                              : themeData.colorScheme.onPrimary,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _rejectReviewedAppeal(int appealId) async {
    final confirmed = await _showConfirmationDialog(
      title: 'lookup.appealProcessEventType.reject'.tr,
      content: 'lookup.appealProcessEventType.reject'.tr,
      confirmLabel: 'lookup.appealProcessEventType.reject'.tr,
      useErrorStyle: true,
    );
    if (confirmed == true) {
      await _submitFinalReview(
        appealId: appealId,
        reviewResult: 'Rejected',
        successMessage: 'appealAdmin.success.finalRejected'.tr,
      );
    }
  }

  Future<bool?> _showConfirmationDialog({
    required String title,
    required String content,
    required String confirmLabel,
    bool useErrorStyle = false,
  }) {
    final themeData = controller.currentBodyTheme.value;
    return showDialog<bool>(
      context: context,
      builder: (ctx) => Theme(
        data: themeData,
        child: AlertDialog(
          backgroundColor: themeData.colorScheme.surfaceContainerLowest,
          title: Text(title),
          content: Text(content),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: Text('common.cancel'.tr),
            ),
            ElevatedButton(
              onPressed: () => Navigator.pop(ctx, true),
              style: ElevatedButton.styleFrom(
                backgroundColor: useErrorStyle
                    ? themeData.colorScheme.error
                    : themeData.colorScheme.primary,
                foregroundColor: useErrorStyle
                    ? themeData.colorScheme.onError
                    : themeData.colorScheme.onPrimary,
              ),
              child: Text(confirmLabel),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _submitFinalReview({
    required int appealId,
    required String reviewResult,
    required String successMessage,
    String? reviewOpinion,
  }) async {
    if (widget.appeal.appealId == null) {
      _showSnackBar('appealAdmin.error.invalidAppealId'.tr, isError: true);
      return;
    }
    setState(() => _isLoading = true);
    try {
      final review = AppealReviewModel(
        appealId: appealId,
        reviewLevel: 'Final',
        reviewResult: reviewResult,
        reviewOpinion: reviewOpinion == null || reviewOpinion.trim().isEmpty
            ? null
            : reviewOpinion.trim(),
      );
      await appealApi
          .apiAppealsAppealIdReviewsPost(
            appealId: appealId,
            review: review,
            idempotencyKey: generateIdempotencyKey(),
          )
          .timeout(const Duration(seconds: 5));
      final refreshedAppeal =
          await appealApi.apiAppealsAppealIdGet(appealId: appealId);
      _showSnackBar(successMessage);
      if (refreshedAppeal != null) {
        widget.onAppealUpdated?.call(refreshedAppeal);
      }
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      developer.log('Error submitting final appeal review $reviewResult: $e',
          stackTrace: StackTrace.current);
      _showSnackBar(formatAppealAdminError(e), isError: true);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<bool> _triggerAcceptanceEvent({
    required int appealId,
    required String event,
    required String successMessage,
    String? rejectionReason,
    bool closePage = true,
  }) async {
    if (widget.appeal.appealId == null) {
      _showSnackBar('appealAdmin.error.invalidAppealId'.tr, isError: true);
      return false;
    }
    setState(() => _isLoading = true);
    try {
      final updatedAppeal = await appealApi
          .apiWorkflowAppealsAppealIdAcceptanceEventsEventPost(
            appealId: appealId,
            event: event,
            rejectionReason: rejectionReason,
            idempotencyKey: generateIdempotencyKey(),
          )
          .timeout(const Duration(seconds: 5));
      _showSnackBar(successMessage);
      widget.onAppealUpdated?.call(updatedAppeal);
      if (closePage && mounted) {
        Navigator.pop(context, true);
      }
      return true;
    } catch (e) {
      developer.log('Error triggering appeal acceptance event $event: $e',
          stackTrace: StackTrace.current);
      _showSnackBar(formatAppealAdminError(e), isError: true);
      return false;
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _triggerProcessEvent({
    required int appealId,
    required String event,
    required String successMessage,
  }) async {
    if (widget.appeal.appealId == null) {
      _showSnackBar('appealAdmin.error.invalidAppealId'.tr, isError: true);
      return;
    }
    setState(() => _isLoading = true);
    try {
      final updatedAppeal = await appealApi
          .apiWorkflowAppealsAppealIdEventsEventPost(
            appealId: appealId,
            event: event,
            idempotencyKey: generateIdempotencyKey(),
          )
          .timeout(const Duration(seconds: 5));
      _showSnackBar(successMessage);
      widget.onAppealUpdated?.call(updatedAppeal);
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      developer.log('Error triggering appeal process event $event: $e',
          stackTrace: StackTrace.current);
      _showSnackBar(formatAppealAdminError(e), isError: true);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  bool _isAcceptancePending() {
    return normalizeAppealStatusCode(widget.appeal.acceptanceStatus) ==
        appealPendingStatusCode();
  }

  bool _isAcceptanceAccepted() {
    return normalizeAppealStatusCode(widget.appeal.acceptanceStatus) ==
        'Accepted';
  }

  bool _isAcceptanceRejected() {
    return normalizeAppealStatusCode(widget.appeal.acceptanceStatus) ==
        appealRejectedStatusCode();
  }

  bool _isAcceptanceNeedSupplement() {
    return normalizeAppealStatusCode(widget.appeal.acceptanceStatus) ==
        'Need_Supplement';
  }

  bool _isProcessUnprocessed() {
    return normalizeAppealStatusCode(widget.appeal.processStatus) ==
        'Unprocessed';
  }

  bool _isProcessUnderReview() {
    return normalizeAppealStatusCode(widget.appeal.processStatus) ==
        'Under_Review';
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

  Widget _buildDetailRow(String label, String value, ThemeData themeData,
      {Color? valueColor}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'common.labelWithColon'.trParams({'label': label}),
            style: themeData.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
              color: themeData.colorScheme.onSurface,
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: themeData.textTheme.bodyLarge?.copyWith(
                color: valueColor ?? themeData.colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildReviewHistorySection(ThemeData themeData) {
    return Card(
      elevation: 4,
      color: themeData.colorScheme.surfaceContainerLowest,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16.0)),
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'appeal.detail.reviewHistory'.tr,
                    style: themeData.textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: themeData.colorScheme.onSurface,
                    ),
                  ),
                ),
                if (_reviewHistory.isNotEmpty)
                  Text(
                    'appeal.detail.reviewCount'
                        .trParams({'count': '${_reviewHistory.length}'}),
                    style: themeData.textTheme.bodyMedium?.copyWith(
                      color: themeData.colorScheme.onSurfaceVariant,
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 16.0),
            if (_isReviewHistoryLoading)
              Center(
                child: CupertinoActivityIndicator(
                  color: themeData.colorScheme.primary,
                  radius: 14.0,
                ),
              )
            else if (_reviewHistory.isEmpty)
              Text(
                _reviewHistoryError.isNotEmpty
                    ? _reviewHistoryError
                    : 'appeal.detail.reviewEmpty'.tr,
                style: themeData.textTheme.bodyMedium?.copyWith(
                  color: themeData.colorScheme.onSurfaceVariant,
                ),
              )
            else
              Column(
                children: _reviewHistory.map((review) {
                  final result =
                      localizeAppealReviewResult(review.reviewResult);
                  final resultColor = (review.reviewResult ?? '')
                              .toLowerCase() ==
                          'approved'
                      ? Colors.green
                      : (review.reviewResult ?? '').toLowerCase() == 'rejected'
                          ? Colors.red
                          : themeData.colorScheme.onSurfaceVariant;
                  return Container(
                    width: double.infinity,
                    margin: const EdgeInsets.only(bottom: 12.0),
                    padding: const EdgeInsets.all(14.0),
                    decoration: BoxDecoration(
                      color: themeData.colorScheme.surfaceContainer,
                      borderRadius: BorderRadius.circular(12.0),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildDetailRow(
                          'appeal.detail.reviewLevel'.tr,
                          localizeAppealReviewLevel(review.reviewLevel),
                          themeData,
                        ),
                        _buildDetailRow(
                          'appeal.detail.reviewResult'.tr,
                          result,
                          themeData,
                          valueColor: resultColor,
                        ),
                        _buildDetailRow(
                          'appeal.detail.reviewReviewer'.tr,
                          review.reviewer ?? 'common.notFilled'.tr,
                          themeData,
                        ),
                        _buildDetailRow(
                          'appeal.detail.reviewReviewerDept'.tr,
                          review.reviewerDept ?? 'common.notFilled'.tr,
                          themeData,
                        ),
                        _buildDetailRow(
                          'appeal.detail.reviewTime'.tr,
                          formatAppealDateTime(review.reviewTime),
                          themeData,
                        ),
                        _buildDetailRow(
                          'appeal.detail.reviewOpinion'.tr,
                          review.reviewOpinion ?? 'common.notFilled'.tr,
                          themeData,
                        ),
                      ],
                    ),
                  );
                }).toList(),
              ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final themeData = controller.currentBodyTheme.value;
      final appealId =
          widget.appeal.appealId?.toString() ?? 'common.notFilled'.tr;
      final offenseId =
          widget.appeal.offenseId?.toString() ?? 'common.notFilled'.tr;
      final name = widget.appeal.appellantName ?? 'common.notFilled'.tr;
      final idCard = widget.appeal.appellantIdCard ?? 'common.notFilled'.tr;
      final contact = widget.appeal.appellantContact ?? 'common.notFilled'.tr;
      final reason = widget.appeal.appealReason ?? 'common.notFilled'.tr;
      final time = formatAppealDateTime(widget.appeal.appealTime);
      final acceptanceStatus =
          localizeAppealStatus(widget.appeal.acceptanceStatus);
      final processStatus = localizeAppealStatus(widget.appeal.processStatus);
      final result = widget.appeal.processResult ??
          widget.appeal.rejectionReason ??
          'common.notFilled'.tr;

      return DashboardPageTemplate(
        theme: themeData,
        title: 'appeal.detail.title'.tr,
        pageType: DashboardPageType.admin,
        bodyIsScrollable: true,
        padding: EdgeInsets.zero,
        body: Padding(
          padding: const EdgeInsets.all(16.0),
          child: _isLoading
              ? Center(
                  child: CupertinoActivityIndicator(
                    color: themeData.colorScheme.primary,
                    radius: 16.0,
                  ),
                )
              : _errorMessage.isNotEmpty
                  ? Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          CupertinoIcons.exclamationmark_triangle,
                          color: themeData.colorScheme.error,
                          size: 48,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          _errorMessage,
                          style: themeData.textTheme.titleMedium?.copyWith(
                            color: themeData.colorScheme.error,
                            fontWeight: FontWeight.w500,
                          ),
                          textAlign: TextAlign.center,
                        ),
                        if (shouldShowAppealAdminReloginAction(_errorMessage))
                          Padding(
                            padding: const EdgeInsets.only(top: 20.0),
                            child: ElevatedButton(
                              onPressed: () => Get.offAllNamed(Routes.login),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: themeData.colorScheme.primary,
                                foregroundColor:
                                    themeData.colorScheme.onPrimary,
                                shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(12.0)),
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 24.0, vertical: 12.0),
                              ),
                              child: Text('appealAdmin.action.relogin'.tr),
                            ),
                          ),
                      ],
                    )
                  : CupertinoScrollbar(
                      controller: ScrollController(),
                      thumbVisibility: true,
                      thickness: 6.0,
                      thicknessWhileDragging: 10.0,
                      child: SingleChildScrollView(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Card(
                              elevation: 4,
                              color:
                                  themeData.colorScheme.surfaceContainerLowest,
                              shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(16.0)),
                              child: Padding(
                                padding: const EdgeInsets.all(20.0),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    _buildDetailRow(
                                      'appeal.detail.appealId'.tr,
                                      appealId,
                                      themeData,
                                    ),
                                    _buildDetailRow(
                                      'appeal.detail.offenseId'.tr,
                                      offenseId,
                                      themeData,
                                    ),
                                    _buildDetailRow(
                                      'appeal.detail.appellant'.tr,
                                      name,
                                      themeData,
                                    ),
                                    _buildDetailRow(
                                      'appeal.detail.idCard'.tr,
                                      idCard,
                                      themeData,
                                    ),
                                    _buildDetailRow(
                                      'appeal.detail.contact'.tr,
                                      contact,
                                      themeData,
                                    ),
                                    _buildDetailRow(
                                      'appeal.detail.reason'.tr,
                                      reason,
                                      themeData,
                                    ),
                                    _buildDetailRow(
                                      'appeal.detail.time'.tr,
                                      time,
                                      themeData,
                                    ),
                                    _buildDetailRow(
                                      'appeal.detail.acceptanceStatus'.tr,
                                      acceptanceStatus,
                                      themeData,
                                      valueColor: isRejectedAppealStatus(
                                              widget.appeal.acceptanceStatus)
                                          ? Colors.red
                                          : themeData
                                              .colorScheme.onSurfaceVariant,
                                    ),
                                    _buildDetailRow('appeal.detail.status'.tr,
                                        processStatus, themeData,
                                        valueColor: isApprovedAppealStatus(
                                                widget.appeal.processStatus)
                                            ? Colors.green
                                            : isRejectedAppealStatus(
                                                    widget.appeal.processStatus)
                                                ? Colors.red
                                                : themeData.colorScheme
                                                    .onSurfaceVariant),
                                    _buildDetailRow(
                                      'appeal.detail.result'.tr,
                                      result,
                                      themeData,
                                    ),
                                  ],
                                ),
                              ),
                            ),
                            const SizedBox(height: 16),
                            _buildReviewHistorySection(themeData),
                            const SizedBox(height: 24),
                            if (_isAdmin && _isAcceptancePending()) ...[
                              Wrap(
                                alignment: WrapAlignment.center,
                                spacing: 12.0,
                                runSpacing: 12.0,
                                children: [
                                  ElevatedButton.icon(
                                    onPressed: () => _acceptAppeal(
                                        widget.appeal.appealId ?? 0),
                                    icon: const Icon(CupertinoIcons.checkmark,
                                        size: 20),
                                    label: Text(
                                        'lookup.appealAcceptanceEventType.accept'
                                            .tr),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: Colors.green,
                                      foregroundColor: Colors.white,
                                      shape: RoundedRectangleBorder(
                                          borderRadius:
                                              BorderRadius.circular(12.0)),
                                      padding: const EdgeInsets.symmetric(
                                          horizontal: 20.0, vertical: 12.0),
                                      elevation: 2,
                                    ),
                                  ),
                                  ElevatedButton.icon(
                                    onPressed: () => _requestSupplement(
                                        widget.appeal.appealId ?? 0),
                                    icon: const Icon(CupertinoIcons.doc_text,
                                        size: 20),
                                    label: Text(
                                        'lookup.appealAcceptanceEventType.requestSupplement'
                                            .tr),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: Colors.orange,
                                      foregroundColor: Colors.white,
                                      shape: RoundedRectangleBorder(
                                          borderRadius:
                                              BorderRadius.circular(12.0)),
                                      padding: const EdgeInsets.symmetric(
                                          horizontal: 20.0, vertical: 12.0),
                                      elevation: 2,
                                    ),
                                  ),
                                  ElevatedButton.icon(
                                    onPressed: () => _rejectAcceptedAppeal(
                                        widget.appeal.appealId ?? 0),
                                    icon: const Icon(CupertinoIcons.xmark,
                                        size: 20),
                                    label: Text(
                                        'lookup.appealAcceptanceEventType.reject'
                                            .tr),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor:
                                          themeData.colorScheme.error,
                                      foregroundColor:
                                          themeData.colorScheme.onError,
                                      shape: RoundedRectangleBorder(
                                          borderRadius:
                                              BorderRadius.circular(12.0)),
                                      padding: const EdgeInsets.symmetric(
                                          horizontal: 20.0, vertical: 12.0),
                                      elevation: 2,
                                    ),
                                  ),
                                ],
                              ),
                            ] else if (_isAdmin &&
                                _isAcceptanceNeedSupplement()) ...[
                              Center(
                                child: Text(
                                  'appealAdmin.note.awaitingApplicantSupplement'
                                      .tr,
                                  style:
                                      themeData.textTheme.bodyMedium?.copyWith(
                                    color:
                                        themeData.colorScheme.onSurfaceVariant,
                                  ),
                                ),
                              ),
                            ] else if (_isAdmin && _isAcceptanceRejected()) ...[
                              Center(
                                child: Text(
                                  'appealAdmin.note.awaitingApplicantResubmission'
                                      .tr,
                                  style:
                                      themeData.textTheme.bodyMedium?.copyWith(
                                    color:
                                        themeData.colorScheme.onSurfaceVariant,
                                  ),
                                ),
                              ),
                            ] else if (_isAdmin &&
                                _isAcceptanceAccepted() &&
                                _isProcessUnprocessed()) ...[
                              Center(
                                child: ElevatedButton.icon(
                                  onPressed: () =>
                                      _startReview(widget.appeal.appealId ?? 0),
                                  icon: const Icon(CupertinoIcons.play_arrow,
                                      size: 20),
                                  label: Text(
                                      'lookup.appealProcessEventType.startReview'
                                          .tr),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor:
                                        themeData.colorScheme.primary,
                                    foregroundColor:
                                        themeData.colorScheme.onPrimary,
                                  ),
                                ),
                              ),
                            ] else if (_isAdmin && _isProcessUnderReview()) ...[
                              Wrap(
                                alignment: WrapAlignment.center,
                                spacing: 12.0,
                                runSpacing: 12.0,
                                children: [
                                  ElevatedButton.icon(
                                    onPressed: () => _approveAppeal(
                                        widget.appeal.appealId ?? 0),
                                    icon: const Icon(CupertinoIcons.checkmark,
                                        size: 20),
                                    label: Text(
                                        'lookup.appealProcessEventType.approve'
                                            .tr),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: Colors.green,
                                      foregroundColor: Colors.white,
                                    ),
                                  ),
                                  ElevatedButton.icon(
                                    onPressed: () => _rejectReviewedAppeal(
                                        widget.appeal.appealId ?? 0),
                                    icon: const Icon(CupertinoIcons.xmark,
                                        size: 20),
                                    label: Text(
                                        'lookup.appealProcessEventType.reject'
                                            .tr),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor:
                                          themeData.colorScheme.error,
                                      foregroundColor:
                                          themeData.colorScheme.onError,
                                    ),
                                  ),
                                ],
                              ),
                            ] else
                              Center(
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                      vertical: 12.0, horizontal: 20.0),
                                  decoration: BoxDecoration(
                                    color:
                                        themeData.colorScheme.surfaceContainer,
                                    borderRadius: BorderRadius.circular(12.0),
                                  ),
                                  child: Text(
                                    _isAdmin
                                        ? 'appealAdmin.note.alreadyProcessed'.tr
                                        : 'appealAdmin.note.adminApprovalOnly'
                                            .tr,
                                    style:
                                        themeData.textTheme.bodyLarge?.copyWith(
                                      color: themeData
                                          .colorScheme.onSurfaceVariant,
                                      fontStyle: FontStyle.italic,
                                    ),
                                  ),
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
