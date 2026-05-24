import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/i18n/i18n_utils.dart';
import 'package:final_assignment_front/i18n/status_localizers.dart';
import 'package:final_assignment_front/utils/helpers/app_helpers.dart';
import 'package:get/get.dart';

const String kOffenseSearchTypeDriverName = 'driverName';
const String kOffenseSearchTypeLicensePlate = 'licensePlate';
const String kOffenseSearchTypeOffenseType = 'offenseType';

const String kOffenseFieldDriverName = 'driverName';
const String kOffenseFieldLicensePlate = 'licensePlate';
const String kOffenseFieldOffenseType = 'offenseType';
const String kOffenseFieldOffenseCode = 'offenseCode';
const String kOffenseFieldOffenseLocation = 'offenseLocation';
const String kOffenseFieldOffenseTime = 'offenseTime';
const String kOffenseFieldDeductedPoints = 'deductedPoints';
const String kOffenseFieldFineAmount = 'fineAmount';
const String kOffenseFieldProcessStatus = 'processStatus';
const String kOffenseFieldProcessResult = 'processResult';

String formatOffenseDate(
  DateTime? date, {
  String emptyKey = 'common.notFilled',
}) {
  return formatLocalizedDate(date, emptyKey: emptyKey);
}

String formatOffensePoints(int? points) {
  return 'offense.value.points'.trParams({'value': '${points ?? 0}'});
}

String formatOffenseAmount(num? amount) {
  return 'offense.value.amount'.trParams({'value': '${amount ?? 0}'});
}

String formatOffenseAdminError(dynamic error) {
  return formatLocalizedApiError(
    error,
    requestKey: 'offenseAdmin.error.request',
    forbiddenKey: 'offenseAdmin.error.forbidden',
    notFoundKey: 'offenseAdmin.error.notFound',
    duplicateKey: 'offenseAdmin.error.duplicateRequest',
    serverKey: 'offenseAdmin.error.server',
    fallbackKey: 'offenseAdmin.error.operationFailed',
  );
}

bool shouldShowOffenseAdminReloginAction(String message) {
  return isAnyLocalizedMessage(message, const [
    'offenseAdmin.error.unauthorized',
    'offenseAdmin.error.expired',
    'offenseAdmin.error.refreshedExpired',
    'offenseAdmin.error.invalidLogin',
  ]);
}

bool shouldShowUserOffenseReloginAction(String message) {
  return isAnyLocalizedMessage(message, const [
    'offense.error.unauthorized',
    'offense.error.loginExpired',
    'offense.error.invalidLogin',
    'offense.error.driverNameMissing',
  ]);
}

String formatUserOffenseError(dynamic error) {
  return formatLocalizedApiError(
    error,
    requestKey: 'offense.error.badRequest',
    forbiddenKey: 'offense.error.forbidden',
    notFoundKey: 'offense.error.notFoundMessage',
    serverKey: 'offense.error.server',
    fallbackKey: 'offense.error.operationFailed',
    duplicateKey: 'offense.error.duplicateRequest',
  );
}

String formatUserOffenseErrorDetail(Object? error) {
  return localizeApiErrorDetail(error);
}

String formatUserOffenseProcessStatus(
  String? status, {
  String emptyKey = 'common.unknown',
}) {
  final localized = localizeOffenseProcessStatus(status, emptyKey: emptyKey);
  if (localized != emptyKey.tr) {
    return localized;
  }

  final normalized = status?.trim();
  return StringHelper.labelFromCode(
    OffenseProcessStatus.values,
    normalized,
    codeSelector: (value) => value.code,
    labelSelector: (value) => value.label,
    placeholder: emptyKey,
  );
}

String offenseSearchHintText(String searchType) {
  switch (searchType) {
    case kOffenseSearchTypeDriverName:
      return 'offenseAdmin.search.driverName'.tr;
    case kOffenseSearchTypeLicensePlate:
      return 'offenseAdmin.search.licensePlate'.tr;
    default:
      return 'offenseAdmin.search.offenseType'.tr;
  }
}

String offenseSearchTypeLabel(String searchType) {
  switch (searchType) {
    case kOffenseSearchTypeDriverName:
      return 'offenseAdmin.filter.byDriverName'.tr;
    case kOffenseSearchTypeLicensePlate:
      return 'offenseAdmin.filter.byLicensePlate'.tr;
    default:
      return 'offenseAdmin.filter.byOffenseType'.tr;
  }
}

String offenseFieldLabel(String fieldKey) {
  switch (fieldKey) {
    case kOffenseFieldDriverName:
      return 'offenseAdmin.form.driverName'.tr;
    case kOffenseFieldLicensePlate:
      return 'offenseAdmin.form.licensePlate'.tr;
    case kOffenseFieldOffenseType:
      return 'offenseAdmin.form.offenseType'.tr;
    case kOffenseFieldOffenseCode:
      return 'offenseAdmin.form.offenseCode'.tr;
    case kOffenseFieldOffenseLocation:
      return 'offenseAdmin.form.offenseLocation'.tr;
    case kOffenseFieldOffenseTime:
      return 'offenseAdmin.form.offenseTime'.tr;
    case kOffenseFieldDeductedPoints:
      return 'offenseAdmin.form.deductedPoints'.tr;
    case kOffenseFieldFineAmount:
      return 'offenseAdmin.form.fineAmount'.tr;
    case kOffenseFieldProcessStatus:
      return 'offenseAdmin.form.processStatus'.tr;
    case kOffenseFieldProcessResult:
      return 'offenseAdmin.form.processResult'.tr;
    default:
      return fieldKey;
  }
}

String? offenseFieldHelperText(String fieldKey) {
  switch (fieldKey) {
    case kOffenseFieldLicensePlate:
      return 'offenseAdmin.form.plateHelper'.tr;
    case kOffenseFieldOffenseLocation:
      return 'offenseAdmin.form.locationHelper'.tr;
    default:
      return null;
  }
}

String? validateOffenseFormField(
  String fieldKey,
  String? value, {
  bool required = false,
  DateTime? selectedDate,
}) {
  final trimmedValue = value?.trim() ?? '';
  final fieldLabel = offenseFieldLabel(fieldKey);

  if (required && trimmedValue.isEmpty) {
    return formatRequiredFieldValidation(
      'offenseAdmin.validation.required',
      fieldLabel,
    );
  }

  if (trimmedValue.isEmpty) {
    return null;
  }

  switch (fieldKey) {
    case kOffenseFieldDriverName:
      return validateMaxLength(
        trimmedValue,
        maxLength: 100,
        key: 'offenseAdmin.validation.driverNameTooLong',
      );
    case kOffenseFieldLicensePlate:
      if (trimmedValue.length > 20) {
        return 'offenseAdmin.validation.plateTooLong'.tr;
      }
      if (!isCompactChineseLicensePlate(trimmedValue)) {
        return 'offenseAdmin.validation.plateInvalid'.tr;
      }
      return null;
    case kOffenseFieldOffenseType:
      return validateMaxLength(
        trimmedValue,
        maxLength: 100,
        key: 'offenseAdmin.validation.typeTooLong',
      );
    case kOffenseFieldOffenseCode:
      return validateMaxLength(
        trimmedValue,
        maxLength: 50,
        key: 'offenseAdmin.validation.codeTooLong',
      );
    case kOffenseFieldOffenseLocation:
      return validateMaxLength(
        trimmedValue,
        maxLength: 100,
        key: 'offenseAdmin.validation.locationTooLong',
      );
    case kOffenseFieldOffenseTime:
      return validateNonFutureDate(
        selectedDate,
        invalidKey: 'offenseAdmin.validation.timeInvalid',
        futureKey: 'offenseAdmin.validation.timeFuture',
      );
    case kOffenseFieldDeductedPoints:
      return validatePointValue(
        trimmedValue,
        invalidKey: 'offenseAdmin.validation.pointsInteger',
        negativeKey: 'offenseAdmin.validation.pointsNegative',
        tooLargeKey: 'offenseAdmin.validation.pointsTooLarge',
      );
    case kOffenseFieldFineAmount:
      return validateMoneyAmount(
        trimmedValue,
        invalidKey: 'offenseAdmin.validation.amountNumber',
        negativeKey: 'offenseAdmin.validation.amountNegative',
        tooLargeKey: 'offenseAdmin.validation.amountTooLarge',
        precisionKey: 'offenseAdmin.validation.amountPrecision',
      );
    case kOffenseFieldProcessStatus:
      return validateMaxLength(
        trimmedValue,
        maxLength: 50,
        key: 'offenseAdmin.validation.statusTooLong',
      );
    case kOffenseFieldProcessResult:
      return validateMaxLength(
        trimmedValue,
        maxLength: 255,
        key: 'offenseAdmin.validation.resultTooLong',
      );
    default:
      return null;
  }
}
