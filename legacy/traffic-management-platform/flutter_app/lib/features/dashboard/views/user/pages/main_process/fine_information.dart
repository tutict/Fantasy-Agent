import 'package:final_assignment_front/features/api/fine_information_controller_api.dart';
import 'package:final_assignment_front/features/api/payment_record_controller_api.dart';
import 'package:final_assignment_front/features/api/driver_information_controller_api.dart';
import 'package:final_assignment_front/features/api/user_management_controller_api.dart';
import 'package:final_assignment_front/features/dashboard/controllers/user_dashboard_screen_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/dashboard_page_template.dart';
import 'package:final_assignment_front/features/model/fine_information.dart';
import 'package:final_assignment_front/features/model/payment_record.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/i18n/fine_localizers.dart';
import 'package:final_assignment_front/i18n/i18n_utils.dart';
import 'package:final_assignment_front/i18n/status_localizers.dart';
import 'package:final_assignment_front/utils/helpers/payment_review_helper.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'dart:developer' as developer;
import 'package:shared_preferences/shared_preferences.dart';

class FineInformationPage extends StatefulWidget {
  const FineInformationPage({super.key});

  @override
  State<FineInformationPage> createState() => _FineInformationPageState();
}

class _FineInformationPageState extends State<FineInformationPage> {
  static const int _pageSize = 100;
  static const Duration _pendingPaymentConfirmWindow = Duration(minutes: 15);

  late FineInformationControllerApi fineApi;
  late PaymentRecordControllerApi paymentApi;
  late Future<List<FineInformation>> _finesFuture;
  final UserDashboardController controller =
      Get.find<UserDashboardController>();
  final DriverInformationControllerApi driverApi =
      DriverInformationControllerApi();
  final UserManagementControllerApi userApi = UserManagementControllerApi();
  bool _isLoading = true;
  String _errorMessage = '';
  String? _currentDriverName;

  @override
  void initState() {
    super.initState();
    fineApi = FineInformationControllerApi();
    paymentApi = PaymentRecordControllerApi();
    _initializeFines();
  }

  Future<void> _initializeFines() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });
    try {
      final prefs = await SharedPreferences.getInstance();
      final jwtToken = await AuthTokenStore.instance.getJwtToken();
      if (jwtToken == null) {
        throw Exception('fine.error.missingLoginOrDriver'.tr);
      }
      await fineApi.initializeWithJwt();
      await paymentApi.initializeWithJwt();
      await driverApi.initializeWithJwt();
      await userApi.initializeWithJwt();
      _currentDriverName = await _fetchDriverName();
      if (_currentDriverName != null && _currentDriverName!.isNotEmpty) {
        await prefs.setString('driverName', _currentDriverName!);
        await prefs.setString('displayName', _currentDriverName!);
      } else {
        _currentDriverName = prefs.getString('driverName') ??
            prefs.getString('displayName') ??
            prefs.getString('userName') ??
            'common.unknown'.tr;
      }
      developer.log('Current Driver Name: $_currentDriverName');
      _finesFuture = _loadUserFines();
      final fines = await _finesFuture;
      developer.log('Loaded Fines: $fines');
    } catch (e) {
      developer.log('Initialization error: $e');
      setState(() {
        _isLoading = false;
        _errorMessage = 'fine.error.initializeFailed'
            .trParams({'error': localizeApiErrorDetail(e)});
      });
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<String?> _fetchDriverName() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final user = await userApi.apiUsersMeGet();
      final driverInfo = await driverApi.apiDriversMeGet();
      final driverName = driverInfo?.name ??
          prefs.getString('displayName') ??
          prefs.getString('driverName') ??
          user?.realName ??
          user?.username;
      developer.log('Driver name from API: $driverName');
      return driverName;
    } catch (e) {
      developer.log('Error fetching driver name: $e');
      return null;
    }
  }

  Future<List<FineInformation>> _loadUserFines() async {
    try {
      final fines = <FineInformation>[];
      var page = 1;
      while (true) {
        final pageItems = await fineApi.apiFinesMeGet(
          page: page,
          size: _pageSize,
        );
        fines.addAll(pageItems);
        if (pageItems.length < _pageSize) {
          break;
        }
        page++;
      }
      developer.log('Loaded fines for current user: $fines');
      return fines;
    } catch (e) {
      developer.log('Error loading fines: $e');
      setState(() {
        _isLoading = false;
        _errorMessage = 'fine.error.loadFailed'
            .trParams({'error': localizeApiErrorDetail(e)});
      });
      return [];
    } finally {
      setState(() => _isLoading = false);
    }
  }

  String _generateIdempotencyKey() {
    return DateTime.now().microsecondsSinceEpoch.toString();
  }

  double _resolveOutstandingAmount(FineInformation fine) {
    final totalAmount =
        fine.totalAmount ?? ((fine.fineAmount ?? 0) + (fine.lateFee ?? 0));
    final paidAmount = fine.paidAmount ?? 0;
    final outstandingAmount = fine.unpaidAmount ?? (totalAmount - paidAmount);
    return outstandingAmount > 0 ? outstandingAmount : 0;
  }

  bool _canSubmitPayment(FineInformation fine) {
    final rawStatus =
        (fine.paymentStatus ?? fine.status ?? '').trim().toLowerCase();
    if (rawStatus == 'waived') {
      return false;
    }
    return _resolveOutstandingAmount(fine) > 0;
  }

  bool _isPendingSelfServicePayment(PaymentRecordModel payment) {
    final paymentStatus = (payment.paymentStatus ?? '').trim().toUpperCase();
    final paymentChannel = (payment.paymentChannel ?? '').trim().toUpperCase();
    return paymentStatus == 'UNPAID' &&
        (paymentChannel == 'APP' || paymentChannel == 'USER_SELF_SERVICE');
  }

  DateTime? _resolvePendingSince(PaymentRecordModel payment) {
    return payment.createdAt ?? payment.paymentTime ?? payment.updatedAt;
  }

  bool _isExpiredPendingSelfServicePayment(PaymentRecordModel payment) {
    if (!_isPendingSelfServicePayment(payment)) {
      return false;
    }
    final pendingSince = _resolvePendingSince(payment);
    if (pendingSince == null) {
      return false;
    }
    return pendingSince
        .add(_pendingPaymentConfirmWindow)
        .isBefore(DateTime.now().toLocal());
  }

  bool _isActivePendingSelfServicePayment(PaymentRecordModel payment) {
    return _isPendingSelfServicePayment(payment) &&
        !_isExpiredPendingSelfServicePayment(payment);
  }

  bool _hasPendingSelfServicePayment(List<PaymentRecordModel> payments) {
    return payments.any(_isActivePendingSelfServicePayment);
  }

  String? _normalizeOptionalPaymentText(String value) {
    final normalized = value.trim();
    return normalized.isEmpty ? null : normalized;
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

  bool _canUploadPaymentProof(
    PaymentRecordModel payment,
    FinancePaymentReview? review,
  ) {
    final normalizedStatus = normalizePaymentStatusCode(payment.paymentStatus);
    final isConfirmed =
        normalizedStatus == 'paid' || normalizedStatus == 'partial';
    final isSelfService =
        (payment.paymentChannel ?? '').trim().toUpperCase() == 'APP' ||
            (payment.paymentChannel ?? '').trim().toUpperCase() ==
                'USER_SELF_SERVICE';
    return isConfirmed &&
        isSelfService &&
        (review?.reviewResult == 'NEED_PROOF' ||
            (payment.receiptUrl ?? '').trim().isEmpty);
  }

  Future<void> _updatePaymentProof(
    int paymentId,
    String receiptUrl,
  ) async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });
    try {
      await paymentApi.apiPaymentsMePaymentIdProofPost(
        paymentId: paymentId,
        receiptUrl: receiptUrl,
        idempotencyKey: _generateIdempotencyKey(),
      );
      if (!mounted) return;
      Get.snackbar(
        'common.success'.tr,
        'fine.payment.proof.success'.tr,
        snackPosition: SnackPosition.TOP,
      );
      _finesFuture = _loadUserFines();
      setState(() {});
    } catch (e) {
      if (!mounted) return;
      Get.snackbar(
        'common.error'.tr,
        'fine.payment.proof.failed'
            .trParams({'error': localizeApiErrorDetail(e)}),
        snackPosition: SnackPosition.TOP,
      );
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _showUpdateProofDialog(PaymentRecordModel payment) async {
    final paymentId = payment.paymentId;
    if (paymentId == null) {
      return;
    }
    final receiptUrlController = TextEditingController(
      text: payment.receiptUrl ?? '',
    );
    try {
      final receiptUrl = await showDialog<String>(
        context: context,
        builder: (dialogContext) {
          return AlertDialog(
            title: Text('fine.payment.proofDialog.title'.tr),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'fine.payment.proofDialog.hint'.tr,
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: receiptUrlController,
                  decoration: InputDecoration(
                    labelText: 'fine.payment.form.receiptUrl'.tr,
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
                  final normalized = _normalizeOptionalPaymentText(
                    receiptUrlController.text,
                  );
                  if (normalized == null) {
                    Get.snackbar(
                      'common.error'.tr,
                      'fine.payment.proof.validation.receiptUrlRequired'.tr,
                      snackPosition: SnackPosition.TOP,
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
      if (receiptUrl == null || receiptUrl.trim().isEmpty) {
        return;
      }
      await _updatePaymentProof(paymentId, receiptUrl);
    } finally {
      receiptUrlController.dispose();
    }
  }

  Future<void> _submitPayment(FineInformation fine) async {
    final outstandingAmount = _resolveOutstandingAmount(fine);
    if (fine.fineId == null || outstandingAmount <= 0) {
      Get.snackbar(
        'common.error'.tr,
        'fine.payment.unavailable'.tr,
        snackPosition: SnackPosition.TOP,
      );
      return;
    }
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });
    try {
      await paymentApi.apiPaymentsMePost(
        paymentRecord: PaymentRecordModel(
          fineId: fine.fineId,
          paymentAmount: outstandingAmount,
          paymentMethod: 'WeChat',
          paymentChannel: 'APP',
          remarks: 'Current user self-service payment',
        ),
        idempotencyKey: _generateIdempotencyKey(),
      );
      Get.snackbar(
        'common.confirm'.tr,
        'fine.payment.orderCreated'.trParams({
          'amount': outstandingAmount.toStringAsFixed(2),
        }),
        snackPosition: SnackPosition.TOP,
      );
      await _refreshFines();
    } catch (e) {
      developer.log('Error submitting fine payment: $e');
      Get.snackbar(
        'common.error'.tr,
        'fine.payment.failed'.trParams({
          'error': localizeApiErrorDetail(e),
        }),
        snackPosition: SnackPosition.TOP,
      );
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _confirmPayment(
    PaymentRecordModel payment, {
    required String transactionId,
    String? receiptUrl,
  }) async {
    final paymentId = payment.paymentId;
    final paymentAmount = payment.paymentAmount ?? 0;
    if (paymentId == null || paymentAmount <= 0) {
      Get.snackbar(
        'common.error'.tr,
        'fine.payment.unavailable'.tr,
        snackPosition: SnackPosition.TOP,
      );
      return;
    }
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });
    try {
      await paymentApi.apiPaymentsMePaymentIdConfirmPost(
        paymentId: paymentId,
        paymentRecord: PaymentRecordModel(
          transactionId: transactionId,
          receiptUrl: receiptUrl,
        ),
        idempotencyKey: _generateIdempotencyKey(),
      );
      Get.snackbar(
        'common.confirm'.tr,
        'fine.payment.confirmSuccess'.trParams({
          'amount': paymentAmount.toStringAsFixed(2),
        }),
        snackPosition: SnackPosition.TOP,
      );
      await _refreshFines();
    } catch (e) {
      developer.log('Error confirming fine payment: $e');
      Get.snackbar(
        'common.error'.tr,
        'fine.payment.confirmFailed'.trParams({
          'error': localizeApiErrorDetail(e),
        }),
        snackPosition: SnackPosition.TOP,
      );
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  void _showConfirmPaymentDialog(PaymentRecordModel payment) {
    final themeData = controller.currentBodyTheme.value;
    final transactionIdController = TextEditingController();
    final receiptUrlController = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: themeData.colorScheme.surfaceContainer,
        title: Text(
          'fine.payment.confirmDialog.title'.tr,
          style: themeData.textTheme.titleLarge?.copyWith(
            color: themeData.colorScheme.onSurface,
          ),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'fine.payment.confirmDialog.hint'.tr,
              style: themeData.textTheme.bodyMedium?.copyWith(
                color: themeData.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: transactionIdController,
              decoration: InputDecoration(
                labelText: 'fine.payment.form.transactionId'.tr,
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: receiptUrlController,
              decoration: InputDecoration(
                labelText: 'fine.payment.form.receiptUrl'.tr,
                border: const OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text('common.cancel'.tr),
          ),
          FilledButton(
            onPressed: () {
              final transactionId =
                  _normalizeOptionalPaymentText(transactionIdController.text);
              if (transactionId == null) {
                Get.snackbar(
                  'common.error'.tr,
                  'fine.payment.validation.transactionIdRequired'.tr,
                  snackPosition: SnackPosition.TOP,
                );
                return;
              }
              Navigator.pop(ctx);
              _confirmPayment(
                payment,
                transactionId: transactionId,
                receiptUrl:
                    _normalizeOptionalPaymentText(receiptUrlController.text),
              );
            },
            child: Text('fine.payment.confirmAction'.tr),
          ),
        ],
      ),
    ).whenComplete(() {
      transactionIdController.dispose();
      receiptUrlController.dispose();
    });
  }

  Future<void> _refreshFines() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });
    try {
      _finesFuture = _loadUserFines();
      final fines = await _finesFuture;
      developer.log('Refreshed Fines: $fines');
    } catch (e) {
      developer.log('Error refreshing fines: $e');
      setState(() {
        _errorMessage = 'fine.error.refreshFailed'
            .trParams({'error': localizeApiErrorDetail(e)});
      });
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<List<PaymentRecordModel>> _loadPaymentHistory(int? fineId) async {
    if (fineId == null) {
      return const [];
    }
    try {
      final payments = <PaymentRecordModel>[];
      var page = 1;
      while (true) {
        final pageItems = await paymentApi.apiPaymentsMeGet(
          fineId: fineId,
          page: page,
          size: _pageSize,
        );
        payments.addAll(pageItems);
        if (pageItems.length < _pageSize) {
          break;
        }
        page++;
      }
      return payments;
    } catch (e) {
      developer.log('Error loading payment history for fine $fineId: $e');
      rethrow;
    }
  }

  String _formatPaymentDateTime(DateTime? value) {
    return formatLocalizedDateTime(
      value,
      includeSeconds: false,
      emptyKey: 'common.none',
    );
  }

  Widget _buildPayNowButton(
    FineInformation fine,
    BuildContext dialogContext,
  ) {
    final outstandingAmount = _resolveOutstandingAmount(fine);
    return SizedBox(
      width: double.infinity,
      child: FilledButton.icon(
        onPressed: () {
          Navigator.pop(dialogContext);
          _submitPayment(fine);
        },
        icon: const Icon(Icons.payment),
        label: Text(
          'fine.action.payNow'.trParams({
            'amount': outstandingAmount.toStringAsFixed(2),
          }),
        ),
      ),
    );
  }

  Widget _buildConfirmPaymentButton(
    PaymentRecordModel payment,
    BuildContext dialogContext,
  ) {
    return SizedBox(
      width: double.infinity,
      child: OutlinedButton.icon(
        onPressed: payment.paymentId == null
            ? null
            : () {
                Navigator.pop(dialogContext);
                _showConfirmPaymentDialog(payment);
              },
        icon: const Icon(Icons.verified),
        label: Text('fine.payment.confirmAction'.tr),
      ),
    );
  }

  Widget _buildPaymentSection(
    ThemeData themeData,
    FineInformation fine,
    Future<List<PaymentRecordModel>> paymentHistoryFuture,
    BuildContext dialogContext,
  ) {
    return FutureBuilder<List<PaymentRecordModel>>(
      future: paymentHistoryFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Padding(
            padding: EdgeInsets.symmetric(vertical: 12),
            child: Center(child: CircularProgressIndicator()),
          );
        }

        final payments = snapshot.data ?? const <PaymentRecordModel>[];
        final hasPendingSelfServicePayment =
            _hasPendingSelfServicePayment(payments);

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (snapshot.hasError)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  'fine.paymentHistory.loadFailed'.trParams({
                    'error': localizeApiErrorDetail(snapshot.error),
                  }),
                  style: themeData.textTheme.bodyMedium?.copyWith(
                    color: themeData.colorScheme.error,
                  ),
                ),
              )
            else if (payments.isEmpty)
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
              ...payments.map(
                (payment) {
                  final financeReview =
                      parseLatestFinancePaymentReview(payment.remarks);
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
                              'amount': (payment.paymentAmount ?? 0)
                                  .toStringAsFixed(2),
                            }),
                            style: themeData.textTheme.titleSmall?.copyWith(
                              color: themeData.colorScheme.onSurface,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          if (financeReview != null)
                            _buildFinanceReviewSummary(
                                financeReview, themeData),
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
                            payment.paymentMethod ?? 'common.none'.tr,
                            themeData,
                          ),
                          _buildDetailRow(
                            'fine.paymentHistory.channel'.tr,
                            payment.paymentChannel ?? 'common.none'.tr,
                            themeData,
                          ),
                          _buildDetailRow(
                            'fine.paymentHistory.paymentNumber'.tr,
                            payment.paymentNumber ?? 'common.none'.tr,
                            themeData,
                          ),
                          _buildDetailRow(
                            'fine.paymentHistory.transactionId'.tr,
                            payment.transactionId ?? 'common.none'.tr,
                            themeData,
                          ),
                          if ((payment.receiptUrl ?? '').trim().isNotEmpty)
                            _buildDetailRow(
                              'fine.paymentHistory.receiptUrl'.tr,
                              payment.receiptUrl!,
                              themeData,
                            ),
                          if (payment.refundAmount != null &&
                              payment.refundAmount! > 0)
                            _buildDetailRow(
                              'fine.paymentHistory.refund'.tr,
                              'fine.paymentHistory.refundValue'.trParams({
                                'amount':
                                    payment.refundAmount!.toStringAsFixed(2),
                                'time':
                                    _formatPaymentDateTime(payment.refundTime),
                              }),
                              themeData,
                            ),
                          if (_canUploadPaymentProof(
                              payment, financeReview)) ...[
                            const SizedBox(height: 12),
                            OutlinedButton(
                              onPressed: () => _showUpdateProofDialog(payment),
                              child: Text('fine.payment.action.uploadProof'.tr),
                            ),
                          ],
                          if (_isPendingSelfServicePayment(payment)) ...[
                            const SizedBox(height: 8),
                            Text(
                              _isExpiredPendingSelfServicePayment(payment)
                                  ? 'fine.payment.expiredHint'.tr
                                  : 'fine.payment.pendingHint'.tr,
                              style: themeData.textTheme.bodyMedium?.copyWith(
                                color: themeData.colorScheme.onSurfaceVariant,
                              ),
                            ),
                            if (_isActivePendingSelfServicePayment(
                                payment)) ...[
                              const SizedBox(height: 12),
                              _buildConfirmPaymentButton(
                                  payment, dialogContext),
                            ],
                          ],
                        ],
                      ),
                    ),
                  );
                },
              ),
            if (hasPendingSelfServicePayment) ...[
              const SizedBox(height: 12),
              Text(
                'fine.payment.pendingExistsInline'.tr,
                style: themeData.textTheme.bodyMedium?.copyWith(
                  color: themeData.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
            if (_canSubmitPayment(fine) && !hasPendingSelfServicePayment) ...[
              const SizedBox(height: 16),
              _buildPayNowButton(fine, dialogContext),
            ],
          ],
        );
      },
    );
  }

  void _showFineDetailsDialog(FineInformation fine) {
    final themeData = controller.currentBodyTheme.value;
    final outstandingAmount = _resolveOutstandingAmount(fine);
    final paymentHistoryFuture = _loadPaymentHistory(fine.fineId);

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: themeData.colorScheme.surfaceContainer,
        title: Text(
          'fine.detail.title'.tr,
          style: themeData.textTheme.titleLarge?.copyWith(
            color: themeData.colorScheme.onSurface,
          ),
        ),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildDetailRow(
                  'fine.detail.amount'.tr,
                  '\$${fine.fineAmount?.toStringAsFixed(2) ?? "0.00"}',
                  themeData),
              _buildDetailRow(
                  'fine.detail.payee'.tr,
                  fine.payee ?? _currentDriverName ?? 'common.unknown'.tr,
                  themeData),
              _buildDetailRow('fine.detail.account'.tr,
                  fine.accountNumber ?? 'common.unknown'.tr, themeData),
              _buildDetailRow('fine.detail.bank'.tr,
                  fine.bank ?? 'common.unknown'.tr, themeData),
              _buildDetailRow('fine.detail.receipt'.tr,
                  fine.receiptNumber ?? 'common.unknown'.tr, themeData),
              _buildDetailRow(
                  'fine.detail.time'.tr,
                  formatFineUserDateTime(fine.fineDate, fine.fineTime),
                  themeData),
              _buildDetailRow('fine.detail.status'.tr,
                  localizeFineDisplayStatus(fine.status), themeData),
              _buildDetailRow('fine.detail.outstanding'.tr,
                  '\$${outstandingAmount.toStringAsFixed(2)}', themeData),
              _buildDetailRow('fine.detail.remarks'.tr,
                  fine.remarks ?? 'common.none'.tr, themeData),
              const SizedBox(height: 16),
              Text(
                'fine.paymentHistory.title'.tr,
                style: themeData.textTheme.titleMedium?.copyWith(
                  color: themeData.colorScheme.onSurface,
                  fontWeight: FontWeight.w600,
                ),
              ),
              _buildPaymentSection(
                themeData,
                fine,
                paymentHistoryFuture,
                ctx,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(
              'fine.action.close'.tr,
              style: themeData.textTheme.labelMedium?.copyWith(
                color: themeData.colorScheme.onSurface,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailRow(String label, String value, ThemeData themeData) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
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
    final themeData = controller.currentBodyTheme.value;

    return DashboardPageTemplate(
      theme: themeData,
      title: 'fine.page.title'.tr,
      pageType: DashboardPageType.user,
      onThemeToggle: controller.toggleBodyTheme,
      bodyIsScrollable: true,
      actions: [
        DashboardPageBarAction(
          icon: Icons.refresh,
          onPressed: _refreshFines,
          tooltip: 'fine.action.refresh'.tr,
        ),
      ],
      isLoading: _isLoading,
      errorMessage: _errorMessage.isNotEmpty ? _errorMessage : null,
      floatingActionButton: FloatingActionButton(
        onPressed: _refreshFines,
        backgroundColor: themeData.colorScheme.primary,
        foregroundColor: themeData.colorScheme.onPrimary,
        tooltip: 'fine.action.refresh'.tr,
        child: const Icon(Icons.refresh),
      ),
      body: Column(
        children: [
          Expanded(
            child: FutureBuilder<List<FineInformation>>(
              future: _finesFuture,
              builder: (context, snapshot) {
                developer.log(
                    'FutureBuilder state: ${snapshot.connectionState}, data: ${snapshot.data}, error: ${snapshot.error}');
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return Center(
                    child: CircularProgressIndicator(
                      valueColor: AlwaysStoppedAnimation<Color>(
                          themeData.colorScheme.primary),
                    ),
                  );
                } else if (snapshot.hasError) {
                  return Center(
                    child: Text(
                      'fine.error.loadFailed'.trParams(
                          {'error': localizeApiErrorDetail(snapshot.error)}),
                      style: themeData.textTheme.bodyLarge?.copyWith(
                        color: themeData.colorScheme.onSurface,
                      ),
                    ),
                  );
                } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
                  return Center(
                    child: Text(
                      _currentDriverName != null
                          ? 'fine.empty.byDriver'.trParams(
                              {'driver': _currentDriverName!},
                            )
                          : 'fine.error.driverNotFoundRelogin'.tr,
                      style: themeData.textTheme.bodyLarge?.copyWith(
                        color: themeData.colorScheme.onSurface,
                      ),
                    ),
                  );
                } else {
                  final fines = snapshot.data!;
                  return RefreshIndicator(
                    onRefresh: _refreshFines,
                    child: ListView.builder(
                      itemCount: fines.length,
                      itemBuilder: (context, index) {
                        final record = fines[index];
                        final amount = record.fineAmount ?? 0.0;
                        final payee = record.payee ??
                            _currentDriverName ??
                            'common.unknown'.tr;
                        final date = formatFineUserDateTime(
                          record.fineDate,
                          record.fineTime,
                        );
                        final status = localizeFineDisplayStatus(record.status);
                        final isPaid = isPaidFineStatus(record.status);
                        return Card(
                          elevation: 2,
                          margin: const EdgeInsets.symmetric(vertical: 8.0),
                          color: themeData.colorScheme.surfaceContainer,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12.0),
                          ),
                          child: ListTile(
                            title: Text(
                              'fine.card.amount'.trParams(
                                  {'amount': amount.toStringAsFixed(2)}),
                              style: themeData.textTheme.bodyLarge?.copyWith(
                                color: themeData.colorScheme.onSurface,
                              ),
                            ),
                            subtitle: Text(
                              'fine.card.summary'.trParams({
                                'payee': payee,
                                'time': date,
                                'status': status,
                              }),
                              style: themeData.textTheme.bodyMedium?.copyWith(
                                color: themeData.colorScheme.onSurfaceVariant,
                              ),
                            ),
                            trailing: Icon(
                              isPaid ? Icons.check_circle : Icons.payment,
                              color: isPaid
                                  ? Colors.green
                                  : themeData.colorScheme.onSurfaceVariant,
                            ),
                            onTap: () {
                              _showFineDetailsDialog(record);
                            },
                          ),
                        );
                      },
                    ),
                  );
                }
              },
            ),
          ),
        ],
      ),
    );
  }
}
