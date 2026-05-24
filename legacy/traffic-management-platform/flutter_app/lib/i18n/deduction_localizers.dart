import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/i18n/i18n_utils.dart';
import 'package:get/get.dart';

const String kDeductionSearchTypeHandler = 'handler';
const String kDeductionSearchTypeTimeRange = 'timeRange';

const String kDeductionFieldOffenseRecord = 'offenseRecord';
const String kDeductionFieldDeductedPoints = 'deductedPoints';
const String kDeductionFieldHandler = 'handler';
const String kDeductionFieldApprover = 'approver';
const String kDeductionFieldRemarks = 'remarks';
const String kDeductionFieldDeductionTime = 'deductionTime';

String formatDeductionDate(DateTime? value) {
  return formatLocalizedDate(value);
}

String formatDeductionDateTime(DateTime? value) {
  return formatLocalizedDateTime(
    value,
    includeSeconds: false,
    emptyKey: 'common.notFilled',
  );
}

String formatDeductionAdminError(dynamic error) {
  return formatLocalizedApiError(
    error,
    requestKey: 'deductionAdmin.error.request',
    forbiddenKey: 'deductionAdmin.error.forbidden',
    notFoundKey: 'deductionAdmin.error.notFound',
    serverKey: 'deductionAdmin.error.server',
    fallbackKey: 'deductionAdmin.error.operationFailed',
    duplicateKey: 'deductionAdmin.error.duplicateRequest',
  );
}

String buildDeductionOffenseOptionText({
  required int? offenseId,
  required int points,
  required String timeText,
}) {
  return 'deductionAdmin.offense.option'.trParams({
    'id': '${offenseId ?? ''}',
    'points': '$points',
    'time': timeText,
  });
}

String deductionFieldTranslationKey(String fieldKey) {
  switch (fieldKey) {
    case kDeductionFieldOffenseRecord:
      return 'deductionAdmin.field.offenseRecord';
    case kDeductionFieldDeductedPoints:
      return 'deductionAdmin.field.deductedPoints';
    case kDeductionFieldHandler:
      return 'deductionAdmin.field.handler';
    case kDeductionFieldApprover:
      return 'deductionAdmin.field.approver';
    case kDeductionFieldRemarks:
      return 'deductionAdmin.field.remarks';
    case kDeductionFieldDeductionTime:
      return 'deductionAdmin.field.deductionTime';
    default:
      return fieldKey;
  }
}

String deductionFieldLabel(String fieldKey, {bool required = false}) {
  final label = deductionFieldTranslationKey(fieldKey).tr;
  return formatRequiredFieldLabel(label, required: required);
}

String? deductionFieldHelperText(String fieldKey) {
  switch (fieldKey) {
    case kDeductionFieldOffenseRecord:
      return 'deductionAdmin.helper.selectOffense'.tr;
    case kDeductionFieldDeductedPoints:
      return 'deductionAdmin.helper.points'.tr;
    case kDeductionFieldHandler:
    case kDeductionFieldApprover:
      return 'deductionAdmin.helper.nameOptional'.trParams({
        'field': deductionFieldLabel(fieldKey),
      });
    case kDeductionFieldDeductionTime:
      return 'deductionAdmin.helper.date'.tr;
    default:
      return null;
  }
}

String? validateDeductionField(
  String fieldKey,
  String? value, {
  bool required = false,
  DateTime? selectedDate,
}) {
  final trimmedValue = value?.trim() ?? '';
  final fieldLabel = deductionFieldLabel(fieldKey);

  if (required && trimmedValue.isEmpty) {
    return formatRequiredFieldValidation(
      'deductionAdmin.validation.required',
      fieldLabel,
    );
  }

  switch (fieldKey) {
    case kDeductionFieldDeductedPoints:
      if (trimmedValue.isEmpty) return null;
      return validatePointValue(
        trimmedValue,
        invalidKey: 'deductionAdmin.validation.pointsNumber',
        negativeKey: 'deductionAdmin.validation.pointsNegative',
        tooLargeKey: 'deductionAdmin.validation.pointsTooLarge',
      );
    case kDeductionFieldHandler:
    case kDeductionFieldApprover:
      return validateMaxLengthWithField(
        trimmedValue,
        maxLength: 100,
        key: 'deductionAdmin.validation.nameTooLong',
        fieldLabel: fieldLabel,
      );
    case kDeductionFieldRemarks:
      return validateMaxLength(
        trimmedValue,
        maxLength: 255,
        key: 'deductionAdmin.validation.remarksTooLong',
      );
    case kDeductionFieldDeductionTime:
      if (trimmedValue.isEmpty) return null;
      return validateNonFutureDate(
        selectedDate,
        invalidKey: 'deductionAdmin.validation.dateInvalid',
        futureKey: 'deductionAdmin.validation.dateFuture',
      );
    default:
      return null;
  }
}

String deductionSearchHintText(String searchType) {
  switch (searchType) {
    case kDeductionSearchTypeTimeRange:
      return 'deductionAdmin.filter.selectDateRange'.tr;
    case kDeductionSearchTypeHandler:
    default:
      return 'deductionAdmin.search.handler'.tr;
  }
}

String deductionSearchTypeLabel(String searchType) {
  switch (searchType) {
    case kDeductionSearchTypeTimeRange:
      return 'deductionAdmin.filter.byTimeRange'.tr;
    case kDeductionSearchTypeHandler:
    default:
      return 'deductionAdmin.filter.byHandler'.tr;
  }
}
