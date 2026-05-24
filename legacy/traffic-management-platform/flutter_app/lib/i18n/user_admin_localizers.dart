import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/i18n/i18n_utils.dart';
import 'package:final_assignment_front/i18n/status_localizers.dart';
import 'package:get/get.dart';

const String kUserAdminSearchTypeUsername = 'username';
const String kUserAdminSearchTypeStatus = 'status';
const String kUserAdminSearchTypeDepartment = 'department';
const String kUserAdminSearchTypeContactNumber = 'contactNumber';
const String kUserAdminSearchTypeEmail = 'email';

const String kUserAdminFieldUsername = 'username';
const String kUserAdminFieldPassword = 'password';
const String kUserAdminFieldNewPassword = 'newPassword';
const String kUserAdminFieldContactNumber = 'contactNumber';
const String kUserAdminFieldEmail = 'email';
const String kUserAdminFieldDepartment = 'department';
const String kUserAdminFieldStatus = 'status';
const String kUserAdminFieldRemarks = 'remarks';
const String kUserAdminFieldCreatedTime = 'createdTime';
const String kUserAdminFieldModifiedTime = 'modifiedTime';

const String kUserAdminStatusActive = 'Active';
const String kUserAdminStatusInactive = 'Inactive';

String formatUserAdminError(dynamic error) {
  return formatLocalizedApiError(
    error,
    requestKey: 'userAdmin.error.request',
    forbiddenKey: 'userAdmin.error.forbidden',
    notFoundKey: 'userAdmin.error.notFound',
    duplicateKey: 'userAdmin.error.duplicateRequest',
    serverKey: 'userAdmin.error.server',
    fallbackKey: 'userAdmin.error.operationFailed',
  );
}

String formatUserAdminDateTime(DateTime? value) {
  return formatLocalizedDateTime(
    value?.toLocal(),
    emptyKey: 'common.notFilled',
  );
}

String userAdminDisplayValue(String? value) {
  return displayLocalizedValue(value);
}

String userAdminStatusKey(String? status) {
  switch (normalizeAccountStatusCode(status)) {
    case kUserAdminStatusActive:
      return 'userAdmin.status.active';
    case kUserAdminStatusInactive:
      return 'userAdmin.status.inactive';
    default:
      return 'common.unknown';
  }
}

String userAdminFieldTranslationKey(String fieldKey) {
  switch (fieldKey) {
    case kUserAdminFieldUsername:
      return 'userAdmin.field.username';
    case kUserAdminFieldPassword:
      return 'userAdmin.field.password';
    case kUserAdminFieldNewPassword:
      return 'userAdmin.field.newPassword';
    case kUserAdminFieldContactNumber:
      return 'userAdmin.field.contactNumber';
    case kUserAdminFieldEmail:
      return 'userAdmin.field.email';
    case kUserAdminFieldDepartment:
      return 'userAdmin.field.department';
    case kUserAdminFieldStatus:
      return 'userAdmin.field.status';
    case kUserAdminFieldRemarks:
      return 'userAdmin.field.remarks';
    case kUserAdminFieldCreatedTime:
      return 'userAdmin.field.createdTime';
    case kUserAdminFieldModifiedTime:
      return 'userAdmin.field.modifiedTime';
    default:
      return fieldKey;
  }
}

String userAdminFieldLabel(String fieldKey, {bool required = false}) {
  final label = userAdminFieldTranslationKey(fieldKey).tr;
  return formatRequiredFieldLabel(label, required: required);
}

String userAdminSearchHintKey(String searchType) {
  switch (searchType) {
    case kUserAdminSearchTypeStatus:
      return 'userAdmin.search.status';
    case kUserAdminSearchTypeDepartment:
      return 'userAdmin.search.department';
    case kUserAdminSearchTypeContactNumber:
      return 'userAdmin.search.contactNumber';
    case kUserAdminSearchTypeEmail:
      return 'userAdmin.search.email';
    case kUserAdminSearchTypeUsername:
    default:
      return 'userAdmin.search.username';
  }
}

String userAdminSearchTypeLabelKey(String searchType) {
  switch (searchType) {
    case kUserAdminSearchTypeStatus:
      return 'userAdmin.filter.byStatus';
    case kUserAdminSearchTypeDepartment:
      return 'userAdmin.filter.byDepartment';
    case kUserAdminSearchTypeContactNumber:
      return 'userAdmin.filter.byContactNumber';
    case kUserAdminSearchTypeEmail:
      return 'userAdmin.filter.byEmail';
    case kUserAdminSearchTypeUsername:
    default:
      return 'userAdmin.filter.byUsername';
  }
}

String? validateUserAdminField(
  String fieldKey,
  String? value, {
  bool required = false,
}) {
  final trimmedValue = value?.trim() ?? '';
  final fieldLabel = userAdminFieldLabel(fieldKey);

  if (required && trimmedValue.isEmpty) {
    return formatRequiredFieldValidation(
      'userAdmin.validation.required',
      fieldLabel,
    );
  }

  switch (fieldKey) {
    case kUserAdminFieldUsername:
      return validateMaxLength(
        trimmedValue,
        maxLength: 50,
        key: 'userAdmin.validation.usernameTooLong',
      );
    case kUserAdminFieldPassword:
    case kUserAdminFieldNewPassword:
      return validateMaxLength(
        trimmedValue,
        maxLength: 255,
        key: 'userAdmin.validation.passwordTooLong',
      );
    case kUserAdminFieldContactNumber:
      return validateMaxLength(
        trimmedValue,
        maxLength: 20,
        key: 'userAdmin.validation.contactNumberTooLong',
      );
    case kUserAdminFieldEmail:
      if (trimmedValue.isEmpty) return null;
      final emailLengthError = validateMaxLength(
        trimmedValue,
        maxLength: 100,
        key: 'userAdmin.validation.emailTooLong',
      );
      if (emailLengthError != null) return emailLengthError;
      final emailPattern = RegExp(r'^[\w-.]+@([\w-]+\.)+[\w-]{2,4}$');
      if (!emailPattern.hasMatch(trimmedValue)) {
        return 'userAdmin.validation.emailInvalid'.tr;
      }
      return null;
    case kUserAdminFieldDepartment:
      return validateMaxLength(
        trimmedValue,
        maxLength: 100,
        key: 'userAdmin.validation.departmentTooLong',
      );
    case kUserAdminFieldRemarks:
      return validateMaxLength(
        trimmedValue,
        maxLength: 255,
        key: 'userAdmin.validation.remarksTooLong',
      );
    default:
      return null;
  }
}
