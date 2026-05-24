import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/i18n/i18n_utils.dart';
import 'package:final_assignment_front/i18n/status_localizers.dart';
import 'package:get/get.dart';

const String kFineSearchTypePayee = 'payee';
const String kFineSearchTypeTimeRange = 'timeRange';

const String kFineFieldPlateNumber = 'plateNumber';
const String kFineFieldAmount = 'amount';
const String kFineFieldPayee = 'payee';
const String kFineFieldAccountNumber = 'accountNumber';
const String kFineFieldBank = 'bank';
const String kFineFieldReceiptNumber = 'receiptNumber';
const String kFineFieldRemarks = 'remarks';
const String kFineFieldFineDate = 'fineDate';

String formatFineAdminDate(
  DateTime? date, {
  String emptyKey = 'common.notFilled',
}) {
  return formatLocalizedDate(date, emptyKey: emptyKey);
}

String formatFineAdminDateTime(
  DateTime? date, {
  String emptyKey = 'common.notFilled',
}) {
  return formatLocalizedDateTime(
    date,
    includeSeconds: false,
    emptyKey: emptyKey,
  );
}

DateTime? resolveFineDisplayDate(DateTime? fineDate, String? fineTime) {
  return fineDate ?? (fineTime != null ? DateTime.tryParse(fineTime) : null);
}

DateTime comparableFineDisplayDate(DateTime? fineDate, String? fineTime) {
  return resolveFineDisplayDate(fineDate, fineTime) ??
      DateTime.fromMillisecondsSinceEpoch(0);
}

String formatFineAdminError(dynamic error) {
  return formatLocalizedApiError(
    error,
    requestKey: 'fineAdmin.error.request',
    forbiddenKey: 'fineAdmin.error.forbidden',
    notFoundKey: 'fineAdmin.error.notFound',
    duplicateKey: 'fineAdmin.error.duplicateRequest',
    serverKey: 'fineAdmin.error.server',
    fallbackKey: 'fineAdmin.error.operationFailed',
  );
}

String formatFineVisibleDate(
  DateTime? date, {
  String emptyKey = 'common.notFilled',
}) {
  return formatFineAdminDate(date, emptyKey: emptyKey);
}

String formatFineUserDateTime(
  DateTime? fineDate,
  String? fineTime, {
  String emptyKey = 'common.unknown',
}) {
  return formatLocalizedDateTime(
    resolveFineDisplayDate(fineDate, fineTime),
    includeSeconds: false,
    emptyKey: emptyKey,
  );
}

bool shouldShowFineAdminReloginAction(String message) {
  return isAnyLocalizedMessage(message, const [
    'fineAdmin.error.unauthorized',
    'fineAdmin.error.expired',
    'fineAdmin.error.refreshedExpired',
    'fineAdmin.error.invalidLogin',
    'fineAdmin.error.adminOnly',
  ]);
}

bool shouldShowFineDetailReloginAction(String message) {
  return isAnyLocalizedMessage(message, const [
    'fineAdmin.error.unauthorized',
    'fineAdmin.error.expired',
    'fineAdmin.error.invalidLogin',
  ]);
}

String localizeAdminFineStatus(
  String? status, {
  String emptyKey = 'common.notFilled',
}) {
  return localizeFineStatus(status, emptyKey: emptyKey);
}

@Deprecated('Use localizeAdminFineStatus instead.')
String localizeManagerFineStatus(
  String? status, {
  String emptyKey = 'common.notFilled',
}) {
  return localizeAdminFineStatus(status, emptyKey: emptyKey);
}

String fineSearchHintText(String searchType) {
  switch (searchType) {
    case kFineSearchTypeTimeRange:
      return 'fineAdmin.search.timeRangeSelected'.tr;
    case kFineSearchTypePayee:
    default:
      return 'fineAdmin.search.payee'.tr;
  }
}

String fineSearchTypeLabel(String searchType) {
  switch (searchType) {
    case kFineSearchTypeTimeRange:
      return 'fineAdmin.filter.byTimeRange'.tr;
    case kFineSearchTypePayee:
    default:
      return 'fineAdmin.filter.byPayee'.tr;
  }
}

String fineFieldLabel(String fieldKey) {
  switch (fieldKey) {
    case kFineFieldPlateNumber:
      return 'fineAdmin.form.plateNumber'.tr;
    case kFineFieldAmount:
      return 'fineAdmin.form.amount'.tr;
    case kFineFieldPayee:
      return 'fineAdmin.form.payee'.tr;
    case kFineFieldAccountNumber:
      return 'fineAdmin.form.accountNumber'.tr;
    case kFineFieldBank:
      return 'fineAdmin.form.bank'.tr;
    case kFineFieldReceiptNumber:
      return 'fineAdmin.form.receiptNumber'.tr;
    case kFineFieldRemarks:
      return 'fineAdmin.form.remarks'.tr;
    case kFineFieldFineDate:
      return 'fineAdmin.form.fineDate'.tr;
    default:
      return fieldKey;
  }
}

String? fineFieldHelperText(String fieldKey) {
  switch (fieldKey) {
    case kFineFieldPlateNumber:
      return 'fineAdmin.form.plateHelper'.tr;
    case kFineFieldAccountNumber:
      return 'fineAdmin.form.accountHelper'.tr;
    default:
      return null;
  }
}

String? validateFineOffenseSelection(int? offenseId) {
  return offenseId == null ? 'fineAdmin.error.selectValidOffense'.tr : null;
}

String? normalizeOptionalFineValue(String? value) {
  final trimmedValue = value?.trim() ?? '';
  return trimmedValue.isEmpty ? null : trimmedValue;
}

String? validateFineFormField(
  String fieldKey,
  String? value, {
  bool required = false,
  DateTime? selectedDate,
}) {
  final trimmedValue = value?.trim() ?? '';
  final fieldLabel = fineFieldLabel(fieldKey);

  if (required && trimmedValue.isEmpty) {
    return formatRequiredFieldValidation(
      'fineAdmin.validation.required',
      fieldLabel,
    );
  }

  if (trimmedValue.isEmpty) {
    return null;
  }

  switch (fieldKey) {
    case kFineFieldPlateNumber:
      if (trimmedValue.length > 20) {
        return 'fineAdmin.validation.plateTooLong'.tr;
      }
      if (!isCompactChineseLicensePlate(trimmedValue)) {
        return 'fineAdmin.validation.plateInvalid'.tr;
      }
      return null;
    case kFineFieldPayee:
      return validateMaxLength(
        trimmedValue,
        maxLength: 100,
        key: 'fineAdmin.validation.payeeTooLong',
      );
    case kFineFieldAmount:
      return validateMoneyAmount(
        trimmedValue,
        invalidKey: 'fineAdmin.validation.amountNumber',
        negativeKey: 'fineAdmin.validation.amountNegative',
        tooLargeKey: 'fineAdmin.validation.amountTooLarge',
        precisionKey: 'fineAdmin.validation.amountPrecision',
      );
    case kFineFieldAccountNumber:
      return validateMaxLength(
        trimmedValue,
        maxLength: 50,
        key: 'fineAdmin.validation.accountTooLong',
      );
    case kFineFieldBank:
      return validateMaxLength(
        trimmedValue,
        maxLength: 100,
        key: 'fineAdmin.validation.bankTooLong',
      );
    case kFineFieldReceiptNumber:
      return validateMaxLength(
        trimmedValue,
        maxLength: 50,
        key: 'fineAdmin.validation.receiptTooLong',
      );
    case kFineFieldRemarks:
      return validateMaxLength(
        trimmedValue,
        maxLength: 255,
        key: 'fineAdmin.validation.remarksTooLong',
      );
    case kFineFieldFineDate:
      return validateNonFutureDate(
        selectedDate,
        invalidKey: 'fineAdmin.validation.dateInvalid',
        futureKey: 'fineAdmin.validation.dateFuture',
      );
    default:
      return null;
  }
}
