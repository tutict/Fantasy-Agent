import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/i18n/i18n_utils.dart';
import 'package:get/get.dart';

const String kAppealSearchTypeAppealReason = 'appealReason';
const String kAppealSearchTypeAppellantName = 'appellantName';
const String kAppealSearchTypeProcessStatus = 'processStatus';
const String kAppealSearchTypeTimeRange = 'timeRange';
const String kAppealReviewSearchTypeReviewer = 'reviewer';
const String kAppealReviewSearchTypeReviewerDept = 'reviewerDept';
const String kAppealReviewSearchTypeTimeRange = 'reviewTimeRange';
const String kAppealFieldReason = 'appeal.form.reason';

String formatAppealDateTime(
  DateTime? value, {
  String emptyKey = 'common.notFilled',
}) {
  return formatLocalizedDateTime(
    value,
    includeSeconds: false,
    emptyKey: emptyKey,
  );
}

String formatAppealAdminError(dynamic error) {
  return formatLocalizedApiError(
    error,
    requestKey: 'appealAdmin.error.request',
    forbiddenKey: 'appealAdmin.error.forbidden',
    notFoundKey: 'appealAdmin.error.notFound',
    duplicateKey: 'appealAdmin.error.duplicateRequest',
    serverKey: 'appealAdmin.error.server',
    fallbackKey: 'appealAdmin.error.operationFailed',
  );
}

String formatAppealErrorDetail(Object? error) {
  return localizeApiErrorDetail(error);
}

String formatUserAppealError(Object? error) {
  return formatAppealErrorDetail(error);
}

String? validateAppealReasonField(
  String? value, {
  bool required = false,
  int maxLength = 500,
}) {
  final trimmedValue = value?.trim() ?? '';
  if (required && trimmedValue.isEmpty) {
    return formatRequiredFieldValidation(
      'appeal.validation.required',
      kAppealFieldReason.tr,
    );
  }
  if (trimmedValue.isEmpty) {
    return null;
  }

  return validateMaxLength(
    trimmedValue,
    maxLength: maxLength,
    key: 'appeal.validation.reasonTooLong',
  );
}

String appealAdminSearchHintText(String searchType) {
  switch (searchType) {
    case kAppealSearchTypeAppealReason:
      return 'appealAdmin.search.appealReason'.tr;
    case kAppealSearchTypeAppellantName:
      return 'appealAdmin.search.appellantName'.tr;
    case kAppealSearchTypeProcessStatus:
      return 'appealAdmin.search.processStatus'.tr;
    case kAppealSearchTypeTimeRange:
    default:
      return 'appealAdmin.search.timeRangeSelected'.tr;
  }
}

String appealAdminSearchTypeLabel(String searchType) {
  switch (searchType) {
    case kAppealSearchTypeAppealReason:
      return 'appealAdmin.filter.byAppealReason'.tr;
    case kAppealSearchTypeAppellantName:
      return 'appealAdmin.filter.byAppellantName'.tr;
    case kAppealSearchTypeProcessStatus:
      return 'appealAdmin.filter.byProcessStatus'.tr;
    case kAppealSearchTypeTimeRange:
    default:
      return 'appealAdmin.filter.byTimeRange'.tr;
  }
}

String appealReviewSearchHintText(String searchType) {
  switch (searchType) {
    case kAppealReviewSearchTypeReviewer:
      return 'appealAdmin.review.search.reviewer'.tr;
    case kAppealReviewSearchTypeReviewerDept:
      return 'appealAdmin.review.search.reviewerDept'.tr;
    case kAppealReviewSearchTypeTimeRange:
    default:
      return 'appealAdmin.review.search.timeRangeSelected'.tr;
  }
}

String appealReviewSearchTypeLabel(String searchType) {
  switch (searchType) {
    case kAppealReviewSearchTypeReviewer:
      return 'appealAdmin.review.filter.byReviewer'.tr;
    case kAppealReviewSearchTypeReviewerDept:
      return 'appealAdmin.review.filter.byReviewerDept'.tr;
    case kAppealReviewSearchTypeTimeRange:
    default:
      return 'appealAdmin.review.filter.byTimeRange'.tr;
  }
}

String localizeAppealReviewResult(String? result) {
  final normalized = result?.trim().toLowerCase() ?? '';
  switch (normalized) {
    case 'approved':
      return 'appealAdmin.review.result.approved'.tr;
    case 'rejected':
      return 'appealAdmin.review.result.rejected'.tr;
    case 'need_resubmit':
    case 'need resubmit':
      return 'appealAdmin.review.result.needResubmit'.tr;
    case 'transfer':
      return 'appealAdmin.review.result.transfer'.tr;
    default:
      return result?.trim().isNotEmpty == true
          ? result!.trim()
          : 'common.notFilled'.tr;
  }
}

String localizeAppealReviewLevel(String? level) {
  final normalized = level?.trim().toLowerCase() ?? '';
  switch (normalized) {
    case 'primary':
      return 'appealAdmin.review.level.primary'.tr;
    case 'secondary':
      return 'appealAdmin.review.level.secondary'.tr;
    case 'final':
      return 'appealAdmin.review.level.final'.tr;
    default:
      return level?.trim().isNotEmpty == true
          ? level!.trim()
          : 'common.notFilled'.tr;
  }
}

bool shouldShowAppealAdminReloginAction(String message) {
  return isAnyLocalizedMessage(message, const [
        'appealAdmin.error.unauthorizedMissing',
        'appealAdmin.error.expired',
        'appealAdmin.error.refreshedExpired',
      ]) ||
      hasLocalizedMessagePrefix(
        message,
        key: 'appealAdmin.error.invalidLogin',
        paramName: 'error',
        marker: '__error__',
      );
}
