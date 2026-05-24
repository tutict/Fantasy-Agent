import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/i18n/i18n_utils.dart';
import 'package:get/get.dart';

const String kLogSearchTypeTimeRange = 'timeRange';

const String kLoginLogSearchTypeUsername = 'username';
const String kLoginLogSearchTypeLoginResult = 'loginResult';

const String kOperationLogSearchTypeUserId = 'userId';
const String kOperationLogSearchTypeOperationResult = 'operationResult';

String formatLogDateTime(
  DateTime? value, {
  String emptyKey = 'common.notFilled',
}) {
  return formatLocalizedDateTime(value, emptyKey: emptyKey);
}

String localizeLoginLogResult(
  String? result, {
  String emptyKey = 'common.unknown',
}) {
  return localizeCommonResult(result, emptyKey: emptyKey);
}

String formatLoginLogError(dynamic error) {
  return formatLocalizedApiError(
    error,
    requestKey: 'loginLog.error.request',
    forbiddenKey: 'loginLog.error.forbidden',
    notFoundKey: 'loginLog.error.notFound',
    duplicateKey: 'loginLog.error.duplicateRequest',
    serverKey: 'loginLog.error.server',
    fallbackKey: 'loginLog.error.operationFailed',
  );
}

String loginLogSearchHintText(String searchType) {
  switch (searchType) {
    case kLoginLogSearchTypeUsername:
      return 'loginLog.search.username'.tr;
    case kLoginLogSearchTypeLoginResult:
      return 'loginLog.search.loginResult'.tr;
    case kLogSearchTypeTimeRange:
    default:
      return 'loginLog.search.timeRangeSelected'.tr;
  }
}

String loginLogSearchTypeLabel(String searchType) {
  switch (searchType) {
    case kLoginLogSearchTypeUsername:
      return 'loginLog.filter.byUsername'.tr;
    case kLoginLogSearchTypeLoginResult:
      return 'loginLog.filter.byLoginResult'.tr;
    case kLogSearchTypeTimeRange:
    default:
      return 'loginLog.search.timeRangeSelected'.tr;
  }
}

bool shouldShowLoginLogReloginAction(String message) {
  return isAnyLocalizedMessage(message, const [
    'loginLog.error.unauthorized',
    'loginLog.error.expired',
    'loginLog.error.invalidLogin',
    'loginLog.error.adminOnly',
  ]);
}

String? validateLoginLogField(
  String field, {
  String? value,
  bool required = false,
}) {
  final trimmedValue = value?.trim() ?? '';
  String fieldLabel;
  int? maxLength;
  String? requiredKey;
  String? tooLongKey;

  switch (field) {
    case 'username':
      fieldLabel = 'loginLog.field.username'.tr;
      maxLength = 100;
      requiredKey = 'loginLog.validation.usernameRequired';
      tooLongKey = 'loginLog.validation.usernameTooLong';
      break;
    case 'loginIp':
      fieldLabel = 'loginLog.field.loginIp'.tr;
      maxLength = 50;
      requiredKey = 'loginLog.validation.loginIpRequired';
      tooLongKey = 'loginLog.validation.loginIpTooLong';
      break;
    case 'loginResult':
      fieldLabel = 'loginLog.field.loginResult'.tr;
      maxLength = 50;
      requiredKey = 'loginLog.validation.loginResultRequired';
      tooLongKey = 'loginLog.validation.loginResultTooLong';
      break;
    case 'browserType':
      fieldLabel = 'loginLog.field.browserType'.tr;
      maxLength = 100;
      tooLongKey = 'loginLog.validation.browserTypeTooLong';
      break;
    case 'osVersion':
      fieldLabel = 'loginLog.field.osVersion'.tr;
      maxLength = 100;
      tooLongKey = 'loginLog.validation.osVersionTooLong';
      break;
    case 'remarks':
      fieldLabel = 'loginLog.field.remarks'.tr;
      maxLength = 500;
      tooLongKey = 'loginLog.validation.remarksTooLong';
      break;
    default:
      return null;
  }

  if (required && trimmedValue.isEmpty) {
    return requiredKey != null
        ? requiredKey.tr
        : formatRequiredFieldValidation('loginLog.validation.required', fieldLabel);
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

String localizeOperationLogResult(
  String? result, {
  String emptyKey = 'common.unknown',
}) {
  return localizeLoginLogResult(result, emptyKey: emptyKey);
}

String formatOperationLogError(dynamic error) {
  return formatLocalizedApiError(
    error,
    requestKey: 'operationLog.error.request',
    forbiddenKey: 'operationLog.error.forbidden',
    notFoundKey: 'operationLog.error.notFound',
    duplicateKey: 'operationLog.error.duplicateRequest',
    serverKey: 'operationLog.error.server',
    fallbackKey: 'operationLog.error.operationFailed',
  );
}

String operationLogSearchHintText(String searchType) {
  switch (searchType) {
    case kOperationLogSearchTypeUserId:
      return 'operationLog.search.userId'.tr;
    case kOperationLogSearchTypeOperationResult:
      return 'operationLog.search.operationResult'.tr;
    case kLogSearchTypeTimeRange:
    default:
      return 'operationLog.search.timeRangeSelected'.tr;
  }
}

String operationLogSearchTypeLabel(String searchType) {
  switch (searchType) {
    case kOperationLogSearchTypeUserId:
      return 'operationLog.filter.byUserId'.tr;
    case kOperationLogSearchTypeOperationResult:
      return 'operationLog.filter.byOperationResult'.tr;
    case kLogSearchTypeTimeRange:
    default:
      return 'operationLog.search.timeRangeSelected'.tr;
  }
}

String? validateOperationLogField(
  String field, {
  String? value,
  bool required = false,
}) {
  final trimmedValue = value?.trim() ?? '';
  int? maxLength;
  String? requiredKey;
  String? tooLongKey;

  switch (field) {
    case 'userId':
      requiredKey = 'operationLog.validation.userIdRequired';
      if (required && trimmedValue.isEmpty) {
        return requiredKey.tr;
      }
      if (trimmedValue.isEmpty) {
        return null;
      }
      if (trimmedValue.length > 20) {
        return 'operationLog.validation.userIdTooLong'.tr;
      }
      return int.tryParse(trimmedValue) == null
          ? 'operationLog.validation.userIdNumeric'.tr
          : null;
    case 'operationContent':
      maxLength = 500;
      requiredKey = 'operationLog.validation.operationContentRequired';
      tooLongKey = 'operationLog.validation.operationContentTooLong';
      break;
    case 'operationResult':
      maxLength = 100;
      requiredKey = 'operationLog.validation.operationResultRequired';
      tooLongKey = 'operationLog.validation.operationResultTooLong';
      break;
    case 'remarks':
      maxLength = 500;
      tooLongKey = 'operationLog.validation.remarksTooLong';
      break;
    default:
      return null;
  }

  if (required && trimmedValue.isEmpty) {
    return requiredKey!.tr;
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

bool shouldShowOperationLogReloginAction(String message) {
  return isAnyLocalizedMessage(message, const [
    'operationLog.error.unauthorized',
    'operationLog.error.expired',
    'operationLog.error.invalidLogin',
    'operationLog.error.adminOnly',
  ]);
}
