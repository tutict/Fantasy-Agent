import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/i18n/i18n_utils.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

const String progressStatusPending = 'Pending';
const String progressStatusProcessing = 'Processing';
const String progressStatusCompleted = 'Completed';
const String progressStatusArchived = 'Archived';
const String progressViewItems = 'items';
const String progressViewRefunds = 'refunds';
const String refundAuditStatusAll = 'ALL';

const List<String> kProgressStatusCategories = [
  progressStatusPending,
  progressStatusProcessing,
  progressStatusCompleted,
  progressStatusArchived,
];

const List<String> kRefundAuditStatusCategories = [
  refundAuditStatusAll,
  'SUCCESS',
  'FAILED',
];

String? validateProgressField(
  String field, {
  String? value,
  bool required = false,
}) {
  final trimmedValue = value?.trim() ?? '';
  String fieldLabel;
  int? maxLength;
  String tooLongKey;

  switch (field) {
    case 'title':
      fieldLabel = 'progress.field.title'.tr;
      maxLength = 100;
      tooLongKey = 'progress.validation.titleTooLong';
      break;
    case 'details':
      fieldLabel = 'progress.field.detailsOptional'.tr;
      maxLength = 500;
      tooLongKey = 'progress.validation.detailsTooLong';
      break;
    default:
      return null;
  }

  if (required && trimmedValue.isEmpty) {
    return formatRequiredFieldValidation(
      'progress.validation.required',
      fieldLabel,
    );
  }
  if (trimmedValue.isEmpty) {
    return null;
  }

  return validateMaxLength(
    trimmedValue,
    maxLength: maxLength,
    key: tooLongKey,
  );
}

String formatProgressDateTime(
  DateTime? value, {
  bool includeSeconds = false,
  String emptyKey = 'common.notFilled',
}) {
  final pattern = includeSeconds ? 'yyyy-MM-dd HH:mm:ss' : 'yyyy-MM-dd HH:mm';
  return formatOptionalLocalizedPatternDate(
    value,
    pattern,
    emptyKey: emptyKey,
  );
}

String formatProgressError(dynamic error) {
  return formatLocalizedApiError(
    error,
    requestKey: 'progress.error.request',
    forbiddenKey: 'progress.error.permission',
    notFoundKey: 'progress.error.notFound',
    serverKey: 'progress.error.server',
    fallbackKey: 'progress.error.operationFailed',
  );
}

String normalizeProgressStatusCode(String? status) {
  final normalized = status?.trim();
  if (normalized == null || normalized.isEmpty) {
    return '';
  }

  switch (normalized.toLowerCase()) {
    case 'pending':
    case '\u5f85\u5904\u7406':
      return progressStatusPending;
    case 'processing':
    case '\u5904\u7406\u4e2d':
      return progressStatusProcessing;
    case 'completed':
    case '\u5df2\u5b8c\u6210':
      return progressStatusCompleted;
    case 'archived':
    case '\u5df2\u5f52\u6863':
      return progressStatusArchived;
    default:
      return normalized;
  }
}

String localizeProgressStatus(String? status) {
  switch (normalizeProgressStatusCode(status)) {
    case progressStatusPending:
      return 'progress.status.pending'.tr;
    case progressStatusProcessing:
      return 'progress.status.processing'.tr;
    case progressStatusCompleted:
      return 'progress.status.completed'.tr;
    case progressStatusArchived:
      return 'progress.status.archived'.tr;
    default:
      return 'common.unknown'.tr;
  }
}

Color progressStatusColor(String? status, ThemeData themeData) {
  switch (normalizeProgressStatusCode(status)) {
    case progressStatusPending:
      return themeData.colorScheme.secondary;
    case progressStatusProcessing:
      return themeData.colorScheme.primary;
    case progressStatusCompleted:
      return themeData.colorScheme.tertiary;
    case progressStatusArchived:
      return themeData.colorScheme.outline;
    default:
      return themeData.colorScheme.outlineVariant;
  }
}

String normalizeRefundAuditStatusCode(String? status) {
  final normalized = status?.trim();
  if (normalized == null || normalized.isEmpty) {
    return '';
  }

  switch (normalized.toUpperCase()) {
    case 'SUCCESS':
      return 'SUCCESS';
    case 'FAILED':
      return 'FAILED';
    case 'ALL':
      return refundAuditStatusAll;
    default:
      return normalized.toUpperCase();
  }
}

String localizeRefundAuditStatus(String? status) {
  switch (normalizeRefundAuditStatusCode(status)) {
    case refundAuditStatusAll:
      return 'progress.refund.status.all'.tr;
    case 'SUCCESS':
      return 'common.success'.tr;
    case 'FAILED':
      return 'common.failed'.tr;
    default:
      return 'common.unknown'.tr;
  }
}

String localizeRefundBusinessType(String? businessType) {
  switch ((businessType ?? '').trim().toUpperCase()) {
    case 'PARTIAL_REFUND':
      return 'progress.refund.type.partial'.tr;
    case 'WAIVE_AND_REFUND':
      return 'progress.refund.type.waive'.tr;
    case 'PARTIAL_REFUND_FAILED':
      return 'progress.refund.type.partialFailed'.tr;
    case 'WAIVE_AND_REFUND_FAILED':
      return 'progress.refund.type.waiveFailed'.tr;
    default:
      return businessType?.trim().isNotEmpty == true
          ? businessType!.trim()
          : 'common.unknown'.tr;
  }
}

Color refundAuditStatusColor(String? status, ThemeData themeData) {
  switch (normalizeRefundAuditStatusCode(status)) {
    case 'SUCCESS':
      return themeData.colorScheme.tertiary;
    case 'FAILED':
      return themeData.colorScheme.error;
    default:
      return themeData.colorScheme.outline;
  }
}
