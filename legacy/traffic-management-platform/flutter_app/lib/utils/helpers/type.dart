part of 'app_helpers.dart';

enum TaskType {
  todo,
  inProgress,
  done,
}

enum CaseType {
  caseAppeal,
  caseSearch,
  caseManagement,
}

enum PaymentStatus {
  unpaid(code: 'Unpaid', label: 'lookup.paymentStatus.unpaid'),
  partial(code: 'Partial', label: 'lookup.paymentStatus.partial'),
  paid(code: 'Paid', label: 'lookup.paymentStatus.paid'),
  overdue(code: 'Overdue', label: 'lookup.paymentStatus.overdue'),
  waived(code: 'Waived', label: 'lookup.paymentStatus.waived');

  final String code;
  final String label;

  const PaymentStatus({required this.code, required this.label});

  static PaymentStatus? fromCode(String? code) =>
      StringHelper.enumFromCode(values, code, (value) => value.code);
}

enum OffenseProcessStatus {
  unprocessed(
    code: 'Unprocessed',
    label: 'lookup.offenseProcessStatus.unprocessed',
  ),
  processing(
      code: 'Processing', label: 'lookup.offenseProcessStatus.processing'),
  processed(code: 'Processed', label: 'lookup.offenseProcessStatus.processed'),
  appealing(code: 'Appealing', label: 'lookup.offenseProcessStatus.appealing'),
  appealApproved(
    code: 'Appeal_Approved',
    label: 'lookup.offenseProcessStatus.appealApproved',
  ),
  appealRejected(
    code: 'Appeal_Rejected',
    label: 'lookup.offenseProcessStatus.appealRejected',
  ),
  cancelled(code: 'Cancelled', label: 'lookup.offenseProcessStatus.cancelled');

  final String code;
  final String label;

  const OffenseProcessStatus({required this.code, required this.label});

  static OffenseProcessStatus? fromCode(String? code) =>
      StringHelper.enumFromCode(values, code, (value) => value.code);
}

enum DeductionStatus {
  effective(code: 'Effective', label: 'lookup.deductionStatus.effective'),
  cancelled(code: 'Cancelled', label: 'lookup.deductionStatus.cancelled'),
  restored(code: 'Restored', label: 'lookup.deductionStatus.restored');

  final String code;
  final String label;

  const DeductionStatus({required this.code, required this.label});

  static DeductionStatus? fromCode(String? code) =>
      StringHelper.enumFromCode(values, code, (value) => value.code);
}

enum AppealAcceptanceStatus {
  pending(code: 'Pending', label: 'lookup.appealAcceptanceStatus.pending'),
  accepted(code: 'Accepted', label: 'lookup.appealAcceptanceStatus.accepted'),
  rejected(code: 'Rejected', label: 'lookup.appealAcceptanceStatus.rejected'),
  needSupplement(
    code: 'Need_Supplement',
    label: 'lookup.appealAcceptanceStatus.needSupplement',
  );

  final String code;
  final String label;

  const AppealAcceptanceStatus({required this.code, required this.label});

  static AppealAcceptanceStatus? fromCode(String? code) =>
      StringHelper.enumFromCode(values, code, (value) => value.code);
}

enum AppealProcessStatus {
  unprocessed(
    code: 'Unprocessed',
    label: 'lookup.appealProcessStatus.unprocessed',
  ),
  underReview(
    code: 'Under_Review',
    label: 'lookup.appealProcessStatus.underReview',
  ),
  approved(code: 'Approved', label: 'lookup.appealProcessStatus.approved'),
  rejected(code: 'Rejected', label: 'lookup.appealProcessStatus.rejected'),
  withdrawn(code: 'Withdrawn', label: 'lookup.appealProcessStatus.withdrawn');

  final String code;
  final String label;

  const AppealProcessStatus({required this.code, required this.label});

  static AppealProcessStatus? fromCode(String? code) =>
      StringHelper.enumFromCode(values, code, (value) => value.code);
}

enum PaymentEventType {
  partialPay(code: 'PARTIAL_PAY', label: 'lookup.paymentEventType.partialPay'),
  completePayment(
    code: 'COMPLETE_PAYMENT',
    label: 'lookup.paymentEventType.completePayment',
  ),
  markOverdue(
    code: 'MARK_OVERDUE',
    label: 'lookup.paymentEventType.markOverdue',
  ),
  waiveFine(code: 'WAIVE_FINE', label: 'lookup.paymentEventType.waiveFine'),
  continuePayment(
    code: 'CONTINUE_PAYMENT',
    label: 'lookup.paymentEventType.continuePayment',
  );

  final String code;
  final String label;

  const PaymentEventType({required this.code, required this.label});

  static PaymentEventType? fromCode(String? code) =>
      StringHelper.enumFromCode(values, code, (value) => value.code);
}

enum DeductionEventType {
  cancel(code: 'CANCEL', label: 'lookup.deductionEventType.cancel'),
  restore(code: 'RESTORE', label: 'lookup.deductionEventType.restore'),
  reactivate(code: 'REACTIVATE', label: 'lookup.deductionEventType.reactivate');

  final String code;
  final String label;

  const DeductionEventType({required this.code, required this.label});

  static DeductionEventType? fromCode(String? code) =>
      StringHelper.enumFromCode(values, code, (value) => value.code);
}

enum OffenseProcessEventType {
  startProcessing(
    code: 'START_PROCESSING',
    label: 'lookup.offenseProcessEventType.startProcessing',
  ),
  completeProcessing(
    code: 'COMPLETE_PROCESSING',
    label: 'lookup.offenseProcessEventType.completeProcessing',
  ),
  submitAppeal(
    code: 'SUBMIT_APPEAL',
    label: 'lookup.offenseProcessEventType.submitAppeal',
  ),
  approveAppeal(
    code: 'APPROVE_APPEAL',
    label: 'lookup.offenseProcessEventType.approveAppeal',
  ),
  rejectAppeal(
    code: 'REJECT_APPEAL',
    label: 'lookup.offenseProcessEventType.rejectAppeal',
  ),
  cancel(code: 'CANCEL', label: 'lookup.offenseProcessEventType.cancel'),
  withdrawAppeal(
    code: 'WITHDRAW_APPEAL',
    label: 'lookup.offenseProcessEventType.withdrawAppeal',
  );

  final String code;
  final String label;

  const OffenseProcessEventType({required this.code, required this.label});

  static OffenseProcessEventType? fromCode(String? code) =>
      StringHelper.enumFromCode(values, code, (value) => value.code);
}

enum AppealAcceptanceEventType {
  accept(code: 'ACCEPT', label: 'lookup.appealAcceptanceEventType.accept'),
  reject(code: 'REJECT', label: 'lookup.appealAcceptanceEventType.reject'),
  requestSupplement(
    code: 'REQUEST_SUPPLEMENT',
    label: 'lookup.appealAcceptanceEventType.requestSupplement',
  ),
  supplementComplete(
    code: 'SUPPLEMENT_COMPLETE',
    label: 'lookup.appealAcceptanceEventType.supplementComplete',
  ),
  resubmit(
      code: 'RESUBMIT', label: 'lookup.appealAcceptanceEventType.resubmit');

  final String code;
  final String label;

  const AppealAcceptanceEventType({required this.code, required this.label});

  static AppealAcceptanceEventType? fromCode(String? code) =>
      StringHelper.enumFromCode(values, code, (value) => value.code);
}

enum AppealProcessEventType {
  startReview(
    code: 'START_REVIEW',
    label: 'lookup.appealProcessEventType.startReview',
  ),
  approve(code: 'APPROVE', label: 'lookup.appealProcessEventType.approve'),
  reject(code: 'REJECT', label: 'lookup.appealProcessEventType.reject'),
  withdraw(code: 'WITHDRAW', label: 'lookup.appealProcessEventType.withdraw'),
  reopenReview(
    code: 'REOPEN_REVIEW',
    label: 'lookup.appealProcessEventType.reopenReview',
  );

  final String code;
  final String label;

  const AppealProcessEventType({required this.code, required this.label});

  static AppealProcessEventType? fromCode(String? code) =>
      StringHelper.enumFromCode(values, code, (value) => value.code);
}
