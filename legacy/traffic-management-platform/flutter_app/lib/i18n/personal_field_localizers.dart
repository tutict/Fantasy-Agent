import 'package:final_assignment_front/i18n/i18n_utils.dart';
import 'package:final_assignment_front/i18n/status_localizers.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:get/get.dart';

String personalFieldLabel(String field) {
  switch (field) {
    case 'name':
      return 'personal.field.name'.tr;
    case 'contactNumber':
      return 'personal.field.contactNumber'.tr;
    case 'idCardNumber':
      return 'personal.field.idCardNumber'.tr;
    case 'driverLicenseNumber':
      return 'personal.field.driverLicenseNumber'.tr;
    case 'password':
      return 'personal.field.password'.tr;
    case 'email':
      return 'personal.field.email'.tr;
    case 'status':
      return 'personal.field.status'.tr;
    case 'createdTime':
      return 'personal.field.createdTime'.tr;
    case 'modifiedTime':
      return 'personal.field.modifiedTime'.tr;
    default:
      return field;
  }
}

String adminPersonalFieldLabel(String field) {
  switch (field) {
    case 'email':
      return 'admin.personal.field.emailAddress'.tr;
    case 'remarks':
      return 'admin.personal.field.remarks'.tr;
    case 'username':
      return 'admin.personal.field.username'.tr;
    default:
      return personalFieldLabel(field);
  }
}

@Deprecated('Use adminPersonalFieldLabel instead.')
String managerPersonalFieldLabel(String field) {
  return adminPersonalFieldLabel(field);
}

String localizePersonalAccountStatus(String? status) {
  return localizeAccountStatus(
    status,
    activeKey: 'personal.status.active',
    inactiveKey: 'personal.status.inactive',
  );
}

String localizeAdminPersonalAccountStatus(String? status) {
  return localizeAccountStatus(
    status,
    activeKey: 'admin.personal.status.active',
    inactiveKey: 'admin.personal.status.inactive',
  );
}

@Deprecated('Use localizeAdminPersonalAccountStatus instead.')
String localizeManagerPersonalAccountStatus(String? status) {
  return localizeAdminPersonalAccountStatus(status);
}

String personalDisplayValue(
  String? value, {
  String emptyKey = 'common.notFilled',
}) {
  return displayLocalizedValue(value, emptyKey: emptyKey);
}

String formatPersonalDateTime(
  DateTime? dateTime, {
  String emptyKey = 'common.notFilled',
}) {
  return formatLocalizedDateTime(
    dateTime,
    includeSeconds: false,
    emptyKey: emptyKey,
  );
}

String formatPersonalError(dynamic error) {
  if (error is ApiException) {
    return 'personal.error.requestFailed'.trParams({
      'code': '${error.code}',
      'message': localizeApiErrorDetail(error),
    });
  }

  return localizeApiErrorDetail(error);
}

String? validatePersonalField(
  String field, {
  required String value,
  bool required = false,
}) {
  final trimmedValue = value.trim();
  final fieldLabel = personalFieldLabel(field);

  if (required && trimmedValue.isEmpty) {
    return formatRequiredFieldValidation(
      'driverAdmin.validation.required',
      fieldLabel,
    );
  }

  if (trimmedValue.isEmpty) {
    return null;
  }

  switch (field) {
    case 'name':
      return validatePersonNameField(
        trimmedValue,
        required: required,
        fieldLabel: fieldLabel,
      );
    case 'contactNumber':
      return validateContactNumberField(
        trimmedValue,
        required: required,
        fieldLabel: fieldLabel,
        strictPrefix: false,
      );
    case 'idCardNumber':
      return validateIdCardField(
        trimmedValue,
        required: required,
        fieldLabel: fieldLabel,
        allowLowercaseX: true,
      );
    case 'driverLicenseNumber':
      return validateExactDigitsFieldValue(
        trimmedValue,
        required: required,
        fieldLabel: fieldLabel,
        length: 12,
      );
    case 'email':
      return validateEmailFieldValue(
        trimmedValue,
        required: required,
        fieldLabel: fieldLabel,
      );
    case 'password':
      if (trimmedValue.length < 5) {
        return 'auth.validation.passwordShort'.tr;
      }
      return null;
    default:
      return null;
  }
}
