import 'dart:convert';

import 'package:final_assignment_front/features/model/progress_item.dart';
import 'package:final_assignment_front/features/model/sys_request_history.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/i18n/progress_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:final_assignment_front/utils/helpers/role_utils.dart';
import 'package:final_assignment_front/utils/services/api_client.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:final_assignment_front/utils/ui/ui_utils.dart';
import 'package:get/get.dart';
import 'package:jwt_decoder/jwt_decoder.dart';

class ProgressController extends GetxController {
  static const int _progressPageSize = 100;
  static const int _refundAuditPageSize = 100;

  final ApiClient apiClient = ApiClient();
  final RxList<ProgressItem> progressItems = <ProgressItem>[].obs;
  final RxList<ProgressItem> filteredItems = <ProgressItem>[].obs;
  final RxList<SysRequestHistoryModel> refundAudits =
      <SysRequestHistoryModel>[].obs;
  final RxList<String> statusCategories =
      List<String>.from(kProgressStatusCategories).obs;
  final RxList<String> refundStatusCategories =
      List<String>.from(kRefundAuditStatusCategories).obs;
  final RxBool isLoading = false.obs;
  final RxString errorMessage = ''.obs;
  final RxString selectedView = progressViewItems.obs;
  final RxString selectedRefundStatus = refundAuditStatusAll.obs;
  final RxString refundFineIdFilter = ''.obs;
  final RxString refundPaymentIdFilter = ''.obs;
  final RxBool _isAdmin = false.obs;

  String _errorMessageOrHttpStatus(String body, int statusCode) {
    return body.isNotEmpty ? body : localizeHttpStatusError(statusCode);
  }

  void _showSnackbar(String title, String message, {bool isError = false}) {
    final ctx = Get.context;
    if (ctx != null) {
      if (isError) {
        AppSnackbar.showError(ctx, message: message);
      } else {
        AppSnackbar.showSuccess(ctx, message: message);
      }
    } else {
      Get.snackbar(
        title,
        message,
        snackPosition: SnackPosition.TOP,
        backgroundColor: isError ? Get.theme.colorScheme.error : null,
        colorText: isError ? Get.theme.colorScheme.onError : null,
      );
    }
  }

  @override
  void onInit() {
    super.onInit();
    _initialize();
  }

  bool get isAdmin => _isAdmin.value;
  bool get isRefundView => selectedView.value == progressViewRefunds;

  Future<void> _initialize() async {
    await _loadUserRole();
    await fetchProgress();
  }

  Future<void> _loadUserRole() async {
    final token = await AuthTokenStore.instance.getJwtToken();
    if (token == null || token.isEmpty) {
      _isAdmin.value = false;
      return;
    }
    try {
      final decoded = JwtDecoder.decode(token);
      _isAdmin.value = hasManagementAccess(decoded['roles']);
    } catch (_) {
      _isAdmin.value = false;
    }
  }

  Future<void> fetchProgress() async {
    isLoading.value = true;
    errorMessage.value = '';
    try {
      final jwtToken = await _requireJwtToken();

      final path = isAdmin ? '/api/progress' : '/api/progress/me';
      final items = await _fetchAllProgressItems(path, jwtToken);
      progressItems.value = items;
      filteredItems.value = List<ProgressItem>.from(items);
    } catch (e) {
      errorMessage.value = formatProgressError(e);
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> switchView(String view) async {
    if (selectedView.value == view) {
      return;
    }
    selectedView.value = view;
    errorMessage.value = '';
    if (view == progressViewRefunds && refundAudits.isEmpty) {
      await fetchRefundAudits();
    }
  }

  Future<void> fetchRefundAudits() async {
    isLoading.value = true;
    errorMessage.value = '';
    try {
      if (!isAdmin) {
        refundAudits.clear();
        return;
      }
      final jwtToken = await _requireJwtToken();

      final queryParams = <QueryParam>[];
      final statusCode =
          normalizeRefundAuditStatusCode(selectedRefundStatus.value);
      final fineId = _parseOptionalPositiveInt(refundFineIdFilter.value);
      final paymentId = _parseOptionalPositiveInt(refundPaymentIdFilter.value);
      if (statusCode.isNotEmpty && statusCode != refundAuditStatusAll) {
        queryParams.add(QueryParam('status', statusCode));
      }
      if (fineId != null) {
        queryParams.add(QueryParam('fineId', '$fineId'));
      }
      if (paymentId != null) {
        queryParams.add(QueryParam('paymentId', '$paymentId'));
      }

      refundAudits.value = await _fetchAllRefundAudits(
        jwtToken: jwtToken,
        baseQueryParams: queryParams,
      );
    } catch (e) {
      errorMessage.value = formatProgressError(e);
      _showSnackbar('common.error'.tr, errorMessage.value, isError: true);
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> clearRefundFilters() async {
    selectedRefundStatus.value = refundAuditStatusAll;
    refundFineIdFilter.value = '';
    refundPaymentIdFilter.value = '';
    await fetchRefundAudits();
  }

  void filterByStatus(String status) {
    final targetStatus = normalizeProgressStatusCode(status);
    filteredItems.value = progressItems
        .where(
            (item) => normalizeProgressStatusCode(item.status) == targetStatus)
        .toList();
  }

  Future<void> fetchProgressByTimeRange(DateTime start, DateTime end) async {
    final startAt = start.isBefore(end) ? start : end;
    final endAt = end.isAfter(start) ? end : start;
    filteredItems.value = progressItems.where((item) {
      final submitTime = item.submitTime;
      return !submitTime.isBefore(startAt) && !submitTime.isAfter(endAt);
    }).toList();
  }

  void clearTimeRangeFilter() {
    filteredItems.value = progressItems;
  }

  void setRefundStatusFilter(String status) {
    selectedRefundStatus.value = status;
  }

  void setRefundFineIdFilter(String value) {
    refundFineIdFilter.value = value.trim();
  }

  void setRefundPaymentIdFilter(String value) {
    refundPaymentIdFilter.value = value.trim();
  }

  String getBusinessContext(ProgressItem item) {
    final contexts = <String>[];
    if (item.appealId != null) {
      contexts.add(
        'progress.context.appealId'.trParams({'id': '${item.appealId}'}),
      );
    }
    if (item.deductionId != null) {
      contexts.add(
        'progress.context.deductionId'.trParams({'id': '${item.deductionId}'}),
      );
    }
    if (item.driverId != null) {
      contexts.add(
        'progress.context.driverId'.trParams({'id': '${item.driverId}'}),
      );
    }
    if (item.fineId != null) {
      contexts.add(
        'progress.context.fineId'.trParams({'id': '${item.fineId}'}),
      );
    }
    if (item.vehicleId != null) {
      contexts.add(
        'progress.context.vehicleId'.trParams({'id': '${item.vehicleId}'}),
      );
    }
    if (item.offenseId != null) {
      contexts.add(
        'progress.context.offenseId'.trParams({'id': '${item.offenseId}'}),
      );
    }
    if (item.businessType?.trim().isNotEmpty == true) {
      contexts.add(item.businessType!.trim());
    }
    if (item.businessId != null) {
      contexts.add('ID: ${item.businessId}');
    }
    if (item.requestUrl?.trim().isNotEmpty == true) {
      contexts.add(item.requestUrl!.trim());
    }
    return contexts.isNotEmpty
        ? contexts.join(', ')
        : 'progress.context.noRelatedBusiness'.tr;
  }

  Map<String, String> getRefundAuditParams(SysRequestHistoryModel item) {
    final params = <String, String>{};
    final raw = item.requestParams?.trim();
    if (raw == null || raw.isEmpty) {
      return params;
    }
    for (final segment in raw.split(',')) {
      final trimmed = segment.trim();
      if (trimmed.isEmpty) {
        continue;
      }
      final separatorIndex = trimmed.indexOf('=');
      if (separatorIndex <= 0 || separatorIndex == trimmed.length - 1) {
        continue;
      }
      params[trimmed.substring(0, separatorIndex)] =
          trimmed.substring(separatorIndex + 1).trim();
    }
    return params;
  }

  String refundAuditSummary(SysRequestHistoryModel item) {
    final params = getRefundAuditParams(item);
    final contexts = <String>[];
    final fineId = params['fineId'];
    final paymentId = params['paymentId'] ?? item.businessId?.toString();
    final refundAmount = params['refundAmount'];
    if (fineId != null && fineId.isNotEmpty && fineId != 'null') {
      contexts.add(
        'progress.refund.detail.fineId'.trParams({'value': fineId}),
      );
    }
    if (paymentId != null && paymentId.isNotEmpty && paymentId != 'null') {
      contexts.add(
        'progress.refund.detail.businessId'.trParams({'value': paymentId}),
      );
    }
    if (refundAmount != null &&
        refundAmount.isNotEmpty &&
        refundAmount != 'null') {
      contexts.add(
        'progress.refund.detail.refundAmount'.trParams({'value': refundAmount}),
      );
    }
    return contexts.isNotEmpty
        ? contexts.join(' | ')
        : 'progress.context.noRelatedBusiness'.tr;
  }

  String refundAuditReason(SysRequestHistoryModel item) {
    final params = getRefundAuditParams(item);
    final reason = params['reason'];
    if (reason == null || reason.isEmpty || reason == 'null') {
      return 'progress.refund.detail.noReason'.tr;
    }
    return reason;
  }

  String? refundAuditFailure(SysRequestHistoryModel item) {
    final params = getRefundAuditParams(item);
    final failure = params['failure'];
    if (failure == null || failure.isEmpty || failure == 'null') {
      return null;
    }
    return failure;
  }

  String refundAuditOperator(SysRequestHistoryModel item) {
    final params = getRefundAuditParams(item);
    final operator = params['operator'];
    if (operator == null || operator.isEmpty || operator == 'null') {
      return 'common.notFilled'.tr;
    }
    return operator;
  }

  int? _parseOptionalPositiveInt(String value) {
    final trimmed = value.trim();
    if (trimmed.isEmpty) {
      return null;
    }
    final parsed = int.tryParse(trimmed);
    if (parsed == null || parsed <= 0) {
      throw Exception('progress.error.operationFailed'
          .trParams({'error': 'ID must be a positive integer'}));
    }
    return parsed;
  }

  Future<String> _requireJwtToken() async {
    final jwtToken = await AuthTokenStore.instance.getJwtToken();
    if (jwtToken == null || jwtToken.isEmpty) {
      throw Exception('auth.error.loginRequiredForReset'.tr);
    }
    return jwtToken;
  }

  Future<List<ProgressItem>> _fetchAllProgressItems(
    String path,
    String jwtToken,
  ) async {
    final items = <ProgressItem>[];
    var page = 1;
    while (true) {
      final response = await apiClient.invokeAPI(
        path,
        'GET',
        [
          QueryParam('page', '$page'),
          QueryParam('size', '$_progressPageSize'),
        ],
        null,
        {'Authorization': 'Bearer $jwtToken'},
        {},
        'application/json',
        ['bearerAuth'],
      );

      if (response.statusCode != 200) {
        throw ApiException(
          response.statusCode,
          _errorMessageOrHttpStatus(response.body, response.statusCode),
        );
      }

      final pageItems = response.body.isEmpty
          ? <ProgressItem>[]
          : (jsonDecode(response.body) as List<dynamic>)
              .map(
                  (json) => ProgressItem.fromJson(json as Map<String, dynamic>))
              .toList();
      items.addAll(pageItems);
      if (pageItems.length < _progressPageSize) {
        break;
      }
      page++;
    }
    return items;
  }

  Future<List<SysRequestHistoryModel>> _fetchAllRefundAudits({
    required String jwtToken,
    required List<QueryParam> baseQueryParams,
  }) async {
    final items = <SysRequestHistoryModel>[];
    var page = 1;
    while (true) {
      final response = await apiClient.invokeAPI(
        '/api/progress/refunds',
        'GET',
        [
          ...baseQueryParams,
          QueryParam('page', '$page'),
          QueryParam('size', '$_refundAuditPageSize'),
        ],
        null,
        {'Authorization': 'Bearer $jwtToken'},
        {},
        'application/json',
        ['bearerAuth'],
      );

      if (response.statusCode != 200) {
        throw ApiException(
          response.statusCode,
          _errorMessageOrHttpStatus(response.body, response.statusCode),
        );
      }

      final pageItems = response.body.isEmpty
          ? <SysRequestHistoryModel>[]
          : (jsonDecode(response.body) as List<dynamic>)
              .map((json) =>
                  SysRequestHistoryModel.fromJson(json as Map<String, dynamic>))
              .toList();
      items.addAll(pageItems);
      if (pageItems.length < _refundAuditPageSize) {
        break;
      }
      page++;
    }
    return items;
  }
}
