import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:intl/intl.dart';

const Set<String> _successResultAliases = {
  'success',
  'succeeded',
  'successful',
  'successfully',
  'ok',
  'passed',
  '成功',
  '完成',
  '通过',
};

const Set<String> _failedResultAliases = {
  'failed',
  'failure',
  'error',
  'errored',
  'unsuccessful',
  'fail',
  '失败',
  '错误',
  '未通过',
};

String currentLocaleName() {
  final locale = Get.locale ?? Get.deviceLocale ?? const Locale('en', 'US');
  final countryCode = locale.countryCode;
  if (countryCode == null || countryCode.isEmpty) {
    return locale.languageCode;
  }
  return '${locale.languageCode}_$countryCode';
}

String formatLocalizedDate(
  DateTime? dateTime, {
  String emptyText = '',
  String? emptyKey,
}) {
  if (dateTime == null) {
    return emptyKey != null ? emptyKey.tr : emptyText;
  }

  return DateFormat.yMd(currentLocaleName()).format(dateTime);
}

String formatLocalizedDateTime(
  DateTime? dateTime, {
  bool includeSeconds = true,
  String emptyKey = 'common.notFilled',
}) {
  if (dateTime == null) return emptyKey.tr;

  final formatter = DateFormat.yMd(currentLocaleName());
  return includeSeconds
      ? formatter.add_Hms().format(dateTime)
      : formatter.add_Hm().format(dateTime);
}

String formatLocalizedPatternDate(
  DateTime dateTime,
  String pattern,
) {
  final locale = currentLocaleName();
  switch (pattern) {
    case 'Md':
      return DateFormat.Md(locale).format(dateTime);
    case 'yMMMd':
      return DateFormat.yMMMd(locale).format(dateTime);
    default:
      return DateFormat(pattern, locale).format(dateTime);
  }
}

String formatOptionalLocalizedPatternDate(
  DateTime? dateTime,
  String pattern, {
  String emptyKey = 'common.notFilled',
}) {
  if (dateTime == null) {
    return emptyKey.tr;
  }

  return formatLocalizedPatternDate(dateTime, pattern);
}

String displayLocalizedValue(
  String? value, {
  String emptyKey = 'common.notFilled',
}) {
  final normalized = value?.trim();
  if (normalized == null || normalized.isEmpty) {
    return emptyKey.tr;
  }
  return normalized;
}

String formatRequiredFieldLabel(
  String label, {
  bool required = false,
}) {
  return required ? '$label *' : label;
}

String formatRequiredFieldValidation(
  String validationKey,
  String fieldLabel,
) {
  return validationKey.trParams({'field': fieldLabel});
}

String? validateNonFutureDate(
  DateTime? selectedDate, {
  required String invalidKey,
  required String futureKey,
}) {
  if (selectedDate == null) {
    return invalidKey.tr;
  }

  final date = DateUtils.dateOnly(selectedDate);
  if (date.isAfter(DateTime.now())) {
    return futureKey.tr;
  }

  return null;
}

String? validatePointValue(
  String value, {
  required String invalidKey,
  required String negativeKey,
  required String tooLargeKey,
  int maxValue = 12,
}) {
  final points = int.tryParse(value);
  if (points == null) {
    return invalidKey.tr;
  }
  if (points < 0) {
    return negativeKey.tr;
  }
  if (points > maxValue) {
    return tooLargeKey.tr;
  }

  return null;
}

String? validateMoneyAmount(
  String value, {
  required String invalidKey,
  required String negativeKey,
  required String tooLargeKey,
  required String precisionKey,
  num maxValue = 99999999.99,
}) {
  final amount = num.tryParse(value);
  if (amount == null) {
    return invalidKey.tr;
  }
  if (amount < 0) {
    return negativeKey.tr;
  }
  if (amount > maxValue) {
    return tooLargeKey.tr;
  }
  if (!RegExp(r'^\d+(\.\d{1,2})?$').hasMatch(value)) {
    return precisionKey.tr;
  }

  return null;
}

String? validateMaxLength(
  String value, {
  required int maxLength,
  required String key,
}) {
  return value.length > maxLength ? key.tr : null;
}

String? validateMaxLengthWithField(
  String value, {
  required int maxLength,
  required String key,
  required String fieldLabel,
}) {
  return value.length > maxLength ? key.trParams({'field': fieldLabel}) : null;
}

String? validatePersonNameField(
  String value, {
  bool required = false,
  String? fieldLabel,
  int minLength = 2,
  int maxLength = 50,
  String requiredKey = 'driverAdmin.validation.required',
  String invalidKey = 'driverAdmin.validation.nameLength',
}) {
  final trimmedValue = value.trim();
  if (required && trimmedValue.isEmpty) {
    return formatRequiredFieldValidation(
      requiredKey,
      fieldLabel ?? '',
    );
  }
  if (trimmedValue.isEmpty) {
    return null;
  }
  if (trimmedValue.length < minLength || trimmedValue.length > maxLength) {
    return invalidKey.tr;
  }
  return null;
}

String? validateIdCardField(
  String value, {
  bool required = false,
  String? fieldLabel,
  bool allowLowercaseX = true,
  int? maxLength,
  String requiredKey = 'driverAdmin.validation.required',
  String invalidKey = 'driverAdmin.validation.idCardInvalid',
  String? tooLongKey,
}) {
  final trimmedValue = value.trim();
  if (required && trimmedValue.isEmpty) {
    return formatRequiredFieldValidation(
      requiredKey,
      fieldLabel ?? '',
    );
  }
  if (trimmedValue.isEmpty) {
    return null;
  }
  if (maxLength != null &&
      trimmedValue.length > maxLength &&
      tooLongKey != null) {
    return tooLongKey.tr;
  }
  if (!isChineseIdCardNumber(
    trimmedValue,
    allowLowercaseX: allowLowercaseX,
  )) {
    return invalidKey.tr;
  }
  return null;
}

String? validateContactNumberField(
  String value, {
  bool required = false,
  String? fieldLabel,
  bool strictPrefix = false,
  int? maxLength,
  String requiredKey = 'driverAdmin.validation.required',
  String invalidKey = 'driverAdmin.validation.contactInvalid',
  String? tooLongKey,
}) {
  final trimmedValue = value.trim();
  if (required && trimmedValue.isEmpty) {
    return formatRequiredFieldValidation(
      requiredKey,
      fieldLabel ?? '',
    );
  }
  if (trimmedValue.isEmpty) {
    return null;
  }
  if (maxLength != null &&
      trimmedValue.length > maxLength &&
      tooLongKey != null) {
    return tooLongKey.tr;
  }
  if (!isMainlandPhoneNumber(
    trimmedValue,
    strictPrefix: strictPrefix,
  )) {
    return invalidKey.tr;
  }
  return null;
}

String? validateExactDigitsFieldValue(
  String value, {
  bool required = false,
  String? fieldLabel,
  required int length,
  String requiredKey = 'driverAdmin.validation.required',
  String invalidKey = 'driverAdmin.validation.licenseInvalid',
}) {
  final trimmedValue = value.trim();
  if (required && trimmedValue.isEmpty) {
    return formatRequiredFieldValidation(
      requiredKey,
      fieldLabel ?? '',
    );
  }
  if (trimmedValue.isEmpty) {
    return null;
  }
  if (!isExactDigits(trimmedValue, length)) {
    return invalidKey.tr;
  }
  return null;
}

String? validateEmailFieldValue(
  String value, {
  bool required = false,
  String? fieldLabel,
  int maxLength = 100,
  String requiredKey = 'driverAdmin.validation.required',
  String tooLongKey = 'userAdmin.validation.emailTooLong',
  String invalidKey = 'auth.validation.emailInvalid',
}) {
  final trimmedValue = value.trim();
  if (required && trimmedValue.isEmpty) {
    return formatRequiredFieldValidation(
      requiredKey,
      fieldLabel ?? '',
    );
  }
  if (trimmedValue.isEmpty) {
    return null;
  }
  final emailLengthError = validateMaxLength(
    trimmedValue,
    maxLength: maxLength,
    key: tooLongKey,
  );
  if (emailLengthError != null) {
    return emailLengthError;
  }
  if (!RegExp(r'^[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}$').hasMatch(trimmedValue)) {
    return invalidKey.tr;
  }
  return null;
}

bool isCompactChineseLicensePlate(String value) {
  return RegExp(r'^[\u4e00-\u9fa5][A-Za-z0-9]{5,7}$').hasMatch(value);
}

bool isChineseIdCardNumber(
  String value, {
  bool allowLowercaseX = false,
}) {
  final suffix = allowLowercaseX ? r'[\dXx]' : r'[\dX]';
  return RegExp('^(\\d{17}$suffix|\\d{15})\$').hasMatch(value);
}

bool isMainlandPhoneNumber(
  String value, {
  bool strictPrefix = true,
}) {
  final pattern = strictPrefix ? r'^1[3-9]\d{9}$' : r'^1\d{10}$';
  return RegExp(pattern).hasMatch(value);
}

bool isExactDigits(String value, int length) {
  return RegExp('^\\d{$length}\$').hasMatch(value);
}

bool isLocalizedMessage(String message, String key) {
  return message == key.tr;
}

bool isAnyLocalizedMessage(String message, Iterable<String> keys) {
  for (final key in keys) {
    if (isLocalizedMessage(message, key)) {
      return true;
    }
  }
  return false;
}

bool hasLocalizedMessagePrefix(
  String message, {
  required String key,
  required String paramName,
  String marker = '__value__',
}) {
  final prefix = key.trParams({paramName: marker}).split(marker).first;
  return message.startsWith(prefix);
}

String localizeCommonResult(
  String? result, {
  String emptyKey = 'common.none',
}) {
  final normalized = result?.trim();
  if (normalized == null || normalized.isEmpty) {
    return emptyKey.tr;
  }

  final lowered = normalized.toLowerCase();
  if (_successResultAliases.contains(normalized) ||
      _successResultAliases.contains(lowered)) {
    return 'common.success'.tr;
  }

  if (_failedResultAliases.contains(normalized) ||
      _failedResultAliases.contains(lowered)) {
    return 'common.failed'.tr;
  }

  return 'common.unknown'.tr;
}
