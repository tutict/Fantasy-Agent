import 'package:get/get.dart';

const String _accountStatusActive = 'Active';
const String _accountStatusInactive = 'Inactive';

const String _appealStatusPending = 'Pending';
const String _appealStatusApproved = 'Approved';
const String _appealStatusRejected = 'Rejected';
const String _appealStatusAccepted = 'Accepted';
const String _appealStatusNeedSupplement = 'Need_Supplement';
const String _appealStatusUnprocessed = 'Unprocessed';
const String _appealStatusUnderReview = 'Under_Review';
const String _appealStatusWithdrawn = 'Withdrawn';

const String _vehicleStatusActive = 'Active';
const String _vehicleStatusInactive = 'Inactive';
const String _vehicleStatusSuspended = 'Suspended';
const String _vehicleStatusArchived = 'Archived';

const String _fineStatusProcessing = 'Processing';
const String _fineStatusApproved = 'Approved';
const String _fineStatusRejected = 'Rejected';
const String _fineStatusPaid = 'Paid';
const String _fineStatusPending = 'Pending';

const String _offenseProcessPending = 'Pending';
const String _offenseProcessProcessing = 'Processing';
const String _offenseProcessCompleted = 'Completed';
const String _offenseProcessProcessed = 'Processed';
const String _offenseProcessApproved = 'Approved';
const String _offenseProcessRejected = 'Rejected';

const String _feedbackStatusPending = 'Pending';
const String _feedbackStatusApproved = 'Approved';
const String _feedbackStatusRejected = 'Rejected';

const String _backupRestoreStatusPending = 'PENDING';
const String _backupRestoreStatusRestored = 'RESTORED';
const String _backupRestoreStatusFailed = 'FAILED';

const String _paymentStatusUnpaid = 'Unpaid';
const String _paymentStatusPartial = 'Partial';
const String _paymentStatusPaid = 'Paid';
const String _paymentStatusOverdue = 'Overdue';
const String _paymentStatusWaived = 'Waived';

String normalizeAccountStatusCode(String? status) {
  final normalized = status?.trim();
  if (normalized == null || normalized.isEmpty) {
    return '';
  }

  switch (normalized.toLowerCase()) {
    case 'active':
    case 'enabled':
    case '启用':
    case '正常':
      return _accountStatusActive;
    case 'inactive':
    case 'disabled':
    case '禁用':
    case '停用':
      return _accountStatusInactive;
    default:
      return normalized;
  }
}

String localizeAccountStatus(
  String? status, {
  required String activeKey,
  required String inactiveKey,
  String unknownKey = 'common.unknown',
}) {
  switch (normalizeAccountStatusCode(status)) {
    case _accountStatusActive:
      return activeKey.tr;
    case _accountStatusInactive:
      return inactiveKey.tr;
    default:
      return unknownKey.tr;
  }
}

String normalizeAppealStatusCode(String? status) {
  final normalized = status?.trim();
  if (normalized == null || normalized.isEmpty) {
    return '';
  }

  switch (normalized.toLowerCase()) {
    case 'pending':
    case '待审批':
    case '待处理':
    case '待受理':
      return _appealStatusPending;
    case 'approved':
    case '已批准':
      return _appealStatusApproved;
    case 'rejected':
    case '已拒绝':
    case '已驳回':
    case '不予受理':
      return _appealStatusRejected;
    case 'accepted':
    case '已受理':
      return _appealStatusAccepted;
    case 'need_supplement':
    case 'need supplement':
    case '需补充材料':
      return _appealStatusNeedSupplement;
    case 'unprocessed':
    case '未处理':
      return _appealStatusUnprocessed;
    case 'under_review':
    case 'under review':
    case '审核中':
      return _appealStatusUnderReview;
    case 'withdrawn':
    case '已撤回':
      return _appealStatusWithdrawn;
    default:
      return normalized;
  }
}

String localizeAppealStatus(String? status) {
  switch (normalizeAppealStatusCode(status)) {
    case _appealStatusPending:
      return 'appeal.status.pending'.tr;
    case _appealStatusApproved:
      return 'appeal.status.approved'.tr;
    case _appealStatusRejected:
      return 'appeal.status.rejected'.tr;
    case _appealStatusAccepted:
      return 'lookup.appealAcceptanceStatus.accepted'.tr;
    case _appealStatusNeedSupplement:
      return 'lookup.appealAcceptanceStatus.needSupplement'.tr;
    case _appealStatusUnprocessed:
      return 'lookup.appealProcessStatus.unprocessed'.tr;
    case _appealStatusUnderReview:
      return 'lookup.appealProcessStatus.underReview'.tr;
    case _appealStatusWithdrawn:
      return 'lookup.appealProcessStatus.withdrawn'.tr;
    default:
      return 'common.unknown'.tr;
  }
}

String appealPendingStatusCode() => _appealStatusPending;

String appealApprovedStatusCode() => _appealStatusApproved;

String appealRejectedStatusCode() => _appealStatusRejected;

bool isPendingAppealStatus(String? status) {
  return normalizeAppealStatusCode(status) == _appealStatusPending;
}

bool isApprovedAppealStatus(String? status) {
  return normalizeAppealStatusCode(status) == _appealStatusApproved;
}

bool isRejectedAppealStatus(String? status) {
  return normalizeAppealStatusCode(status) == _appealStatusRejected;
}

String normalizeVehicleStatusCode(String? status) {
  final normalized = status?.trim();
  if (normalized == null || normalized.isEmpty) {
    return '';
  }

  switch (normalized.toLowerCase()) {
    case 'active':
    case 'enabled':
    case '启用':
    case '正常':
      return _vehicleStatusActive;
    case 'inactive':
    case 'disabled':
    case '禁用':
    case '停用':
      return _vehicleStatusInactive;
    case 'suspended':
    case '暂停':
      return _vehicleStatusSuspended;
    case 'archived':
    case '已归档':
      return _vehicleStatusArchived;
    default:
      return normalized;
  }
}

String localizeVehicleStatus(String? status) {
  switch (normalizeVehicleStatusCode(status)) {
    case _vehicleStatusActive:
      return 'vehicle.status.active'.tr;
    case _vehicleStatusInactive:
      return 'vehicle.status.inactive'.tr;
    case _vehicleStatusSuspended:
      return 'vehicle.status.suspended'.tr;
    case _vehicleStatusArchived:
      return 'vehicle.status.archived'.tr;
    default:
      return 'common.unknown'.tr;
  }
}

String normalizeFineStatusCode(String? status) {
  final normalized = status?.trim();
  if (normalized == null || normalized.isEmpty) {
    return '';
  }

  switch (normalized.toLowerCase()) {
    case 'approved':
    case '批准':
      return _fineStatusApproved;
    case 'rejected':
    case '驳回':
      return _fineStatusRejected;
    case 'paid':
    case '已缴纳':
      return _fineStatusPaid;
    case 'pending':
    case '待缴纳':
      return _fineStatusPending;
    case 'processing':
    case '处理中':
      return _fineStatusProcessing;
    default:
      return normalized;
  }
}

String localizeFineStatus(
  String? status, {
  String? emptyKey,
}) {
  final normalized = normalizeFineStatusCode(status);
  if (normalized.isEmpty) {
    return emptyKey != null ? emptyKey.tr : 'common.notFilled'.tr;
  }

  switch (normalized) {
    case _fineStatusApproved:
      return 'common.status.approved'.tr;
    case _fineStatusRejected:
      return 'common.status.rejected'.tr;
    case _fineStatusPaid:
      return 'fine.status.paid'.tr;
    case _fineStatusPending:
      return 'fine.status.pending'.tr;
    case _fineStatusProcessing:
      return 'common.status.processing'.tr;
    default:
      return 'common.unknown'.tr;
  }
}

String localizeFineDisplayStatus(
  String? status, {
  String emptyKey = 'common.unknown',
}) {
  final fineStatusLabel = localizeFineStatus(status, emptyKey: emptyKey);
  if (fineStatusLabel != emptyKey.tr) {
    return fineStatusLabel;
  }

  final paymentStatusLabel = localizePaymentStatus(status, emptyKey: emptyKey);
  if (paymentStatusLabel != emptyKey.tr) {
    return paymentStatusLabel;
  }

  return emptyKey.tr;
}

String fineApprovedStatusCode() => _fineStatusApproved;

String fineRejectedStatusCode() => _fineStatusRejected;

String fineProcessingStatusCode() => _fineStatusProcessing;

bool isProcessingFineStatus(String? status) {
  return normalizeFineStatusCode(status) == _fineStatusProcessing;
}

bool isPaidFineStatus(String? status) {
  return normalizeFineStatusCode(status) == _fineStatusPaid;
}

String normalizeOffenseProcessStatusCode(String? status) {
  final normalized = status?.trim();
  if (normalized == null || normalized.isEmpty) {
    return '';
  }

  switch (normalized.toLowerCase()) {
    case 'pending':
    case '待处理':
      return _offenseProcessPending;
    case 'processing':
    case '处理中':
      return _offenseProcessProcessing;
    case 'completed':
    case 'processed':
    case '已处理':
    case '已完成':
      return _offenseProcessCompleted;
    case 'approved':
    case '已批准':
      return _offenseProcessApproved;
    case 'rejected':
    case '已拒绝':
      return _offenseProcessRejected;
    default:
      return normalized;
  }
}

String localizeOffenseProcessStatus(
  String? status, {
  String emptyKey = 'common.none',
}) {
  final normalized = normalizeOffenseProcessStatusCode(status);
  if (normalized.isEmpty) {
    return emptyKey.tr;
  }

  switch (normalized) {
    case _offenseProcessPending:
      return 'common.status.pending'.tr;
    case _offenseProcessProcessing:
      return 'common.status.processing'.tr;
    case _offenseProcessCompleted:
    case _offenseProcessProcessed:
      return 'common.status.completed'.tr;
    case _offenseProcessApproved:
      return 'common.status.approved'.tr;
    case _offenseProcessRejected:
      return 'common.status.rejected'.tr;
    default:
      return 'common.unknown'.tr;
  }
}

String offensePendingProcessStatusCode() => _offenseProcessPending;

String normalizeFeedbackStatusCode(String? status) {
  final normalized = status?.trim();
  if (normalized == null || normalized.isEmpty) {
    return '';
  }

  switch (normalized.toLowerCase()) {
    case 'pending':
    case '待审核':
      return _feedbackStatusPending;
    case 'approved':
    case '已批准':
      return _feedbackStatusApproved;
    case 'rejected':
    case '已拒绝':
      return _feedbackStatusRejected;
    default:
      return normalized;
  }
}

String localizeFeedbackStatus(String? status) {
  switch (normalizeFeedbackStatusCode(status)) {
    case _feedbackStatusPending:
      return 'common.status.pending'.tr;
    case _feedbackStatusApproved:
      return 'common.status.approved'.tr;
    case _feedbackStatusRejected:
      return 'common.status.rejected'.tr;
    default:
      return 'common.unknown'.tr;
  }
}

String feedbackPendingStatusCode() => _feedbackStatusPending;

String feedbackApprovedStatusCode() => _feedbackStatusApproved;

String feedbackRejectedStatusCode() => _feedbackStatusRejected;

bool isPendingFeedbackStatus(String? status) {
  return normalizeFeedbackStatusCode(status) == _feedbackStatusPending;
}

String normalizeBackupRestoreStatusCode(String? status) {
  final normalized = status?.trim();
  if (normalized == null || normalized.isEmpty) {
    return '';
  }

  switch (normalized.toUpperCase()) {
    case 'PENDING':
    case '待处理':
      return _backupRestoreStatusPending;
    case 'RESTORED':
    case '已恢复':
      return _backupRestoreStatusRestored;
    case 'FAILED':
    case '失败':
      return _backupRestoreStatusFailed;
    default:
      return normalized;
  }
}

String localizeBackupRestoreStatus(String? status) {
  switch (normalizeBackupRestoreStatusCode(status)) {
    case '':
      return 'backupRestore.status.notRestored'.tr;
    case _backupRestoreStatusPending:
      return 'backupRestore.status.pending'.tr;
    case _backupRestoreStatusRestored:
      return 'backupRestore.status.restored'.tr;
    case _backupRestoreStatusFailed:
      return 'backupRestore.status.failed'.tr;
    default:
      return status?.trim().isNotEmpty == true
          ? status!.trim()
          : 'common.unknown'.tr;
  }
}

String normalizePaymentStatusCode(String? status) {
  final normalized = status?.trim();
  if (normalized == null || normalized.isEmpty) {
    return '';
  }

  switch (normalized.toLowerCase()) {
    case 'unpaid':
    case '未支付':
      return _paymentStatusUnpaid;
    case 'partial':
    case 'partially paid':
    case '部分支付':
      return _paymentStatusPartial;
    case 'paid':
    case '已支付':
    case '已缴纳':
      return _paymentStatusPaid;
    case 'overdue':
    case '已逾期':
      return _paymentStatusOverdue;
    case 'waived':
    case '已减免':
      return _paymentStatusWaived;
    default:
      return normalized;
  }
}

String localizePaymentStatus(
  String? status, {
  String emptyKey = 'common.unknown',
}) {
  switch (normalizePaymentStatusCode(status)) {
    case '':
      return emptyKey.tr;
    case _paymentStatusUnpaid:
      return 'lookup.paymentStatus.unpaid'.tr;
    case _paymentStatusPartial:
      return 'lookup.paymentStatus.partial'.tr;
    case _paymentStatusPaid:
      return 'lookup.paymentStatus.paid'.tr;
    case _paymentStatusOverdue:
      return 'lookup.paymentStatus.overdue'.tr;
    case _paymentStatusWaived:
      return 'lookup.paymentStatus.waived'.tr;
    default:
      return emptyKey.tr;
  }
}
