import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/i18n/i18n_utils.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:get/get.dart';

String formatBackupDate(DateTime? dateTime) {
  return formatLocalizedDate(dateTime?.toLocal());
}

String formatBackupDateTime(DateTime? dateTime) {
  return formatLocalizedDateTime(
    dateTime?.toLocal(),
    emptyKey: 'common.none',
  );
}

String backupDisplayValue(String? value) {
  return displayLocalizedValue(value, emptyKey: 'common.none');
}

String localizeBackupType(String? type) {
  final normalized = type?.trim();
  if (normalized == null || normalized.isEmpty) {
    return 'common.none'.tr;
  }

  switch (normalized.toUpperCase()) {
    case 'FULL':
      return 'backupRestore.type.full'.tr;
    case 'INCREMENTAL':
      return 'backupRestore.type.incremental'.tr;
    case 'DIFFERENTIAL':
      return 'backupRestore.type.differential'.tr;
    case 'MANUAL':
      return 'backupRestore.type.manual'.tr;
    case 'AUTO':
    case 'AUTOMATIC':
      return 'backupRestore.type.auto'.tr;
    default:
      return normalized;
  }
}

String? validateBackupRestoreField(
  String field, {
  String? value,
  bool required = false,
}) {
  final trimmedValue = value?.trim() ?? '';
  String fieldLabel;
  int? maxLength;
  String? tooLongKey;

  switch (field) {
    case 'fileName':
      fieldLabel = 'backupRestore.field.fileName'.tr;
      maxLength = 255;
      tooLongKey = 'backupRestore.validation.fileNameTooLong';
      break;
    case 'remarks':
      fieldLabel = 'backupRestore.field.remarks'.tr;
      maxLength = 500;
      tooLongKey = 'backupRestore.validation.remarksTooLong';
      break;
    default:
      return null;
  }

  if (required && trimmedValue.isEmpty) {
    return formatRequiredFieldValidation(
      'backupRestore.validation.required',
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

String formatBackupRestoreError(dynamic error) {
  if (error is ApiException) {
    final message = error.message.isNotEmpty
        ? localizeApiErrorDetail(error)
        : 'backupRestore.error.server'.tr;
    return '$message (HTTP ${error.code})';
  }
  return localizeApiErrorDetail(error);
}
