import 'package:final_assignment_front/i18n/i18n_utils.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:get/get.dart';

const String kDriverGenderMale = 'Male';
const String kDriverGenderFemale = 'Female';
const List<String> kDriverGenderValues = [
  kDriverGenderMale,
  kDriverGenderFemale,
];

String normalizeDriverGenderCode(String? gender) {
  final normalized = gender?.trim();
  if (normalized == null || normalized.isEmpty) {
    return '';
  }

  switch (normalized.toLowerCase()) {
    case 'male':
    case '\u7537':
      return kDriverGenderMale;
    case 'female':
    case '\u5973':
      return kDriverGenderFemale;
    default:
      return normalized;
  }
}

String driverFieldTranslationKey(String fieldKey) {
  switch (fieldKey) {
    case 'name':
      return 'driverAdmin.field.name';
    case 'idCardNumber':
      return 'driverAdmin.field.idCardNumber';
    case 'contactNumber':
      return 'driverAdmin.field.contactNumber';
    case 'driverLicenseNumber':
      return 'driverAdmin.field.driverLicenseNumber';
    case 'gender':
      return 'driverAdmin.field.gender';
    case 'birthdate':
      return 'driverAdmin.field.birthdate';
    case 'firstLicenseDate':
      return 'driverAdmin.field.firstLicenseDate';
    case 'allowedVehicleType':
      return 'driverAdmin.field.allowedVehicleType';
    case 'issueDate':
      return 'driverAdmin.field.issueDate';
    case 'expiryDate':
      return 'driverAdmin.field.expiryDate';
    default:
      return fieldKey;
  }
}

String driverFieldLabel(String fieldKey, {bool required = false}) {
  final label = driverFieldTranslationKey(fieldKey).tr;
  return formatRequiredFieldLabel(label, required: required);
}

String localizeDriverGender(String? gender) {
  switch (normalizeDriverGenderCode(gender)) {
    case kDriverGenderMale:
      return 'driverAdmin.gender.male'.tr;
    case kDriverGenderFemale:
      return 'driverAdmin.gender.female'.tr;
    default:
      return 'driverAdmin.gender.unknown'.tr;
  }
}

String formatDriverDate(DateTime? value) {
  return formatLocalizedDate(
    value?.toLocal(),
    emptyKey: 'common.notFilled',
  );
}

String driverDisplayValue(String? value) {
  return displayLocalizedValue(value);
}

String formatDriverAdminError(dynamic error) {
  return formatLocalizedApiError(
    error,
    requestKey: 'driverAdmin.error.request',
    forbiddenKey: 'driverAdmin.error.forbidden',
    notFoundKey: 'driverAdmin.error.notFound',
    serverKey: 'driverAdmin.error.server',
    fallbackKey: 'driverAdmin.error.operationFailed',
    duplicateKey: 'driverAdmin.error.duplicateRequest',
  );
}

String? driverGenderToBackend(String? value) {
  switch (normalizeDriverGenderCode(value)) {
    case kDriverGenderMale:
      return kDriverGenderMale;
    case kDriverGenderFemale:
      return kDriverGenderFemale;
    default:
      return null;
  }
}

String? validateDriverField(
  String fieldKey,
  String? value, {
  bool required = false,
}) {
  final trimmedValue = value?.trim() ?? '';
  final fieldLabel = driverFieldLabel(fieldKey);

  if (required && trimmedValue.isEmpty) {
    return formatRequiredFieldValidation(
      'driverAdmin.validation.required',
      fieldLabel,
    );
  }

  switch (fieldKey) {
    case 'name':
      return validatePersonNameField(
        trimmedValue,
        required: required,
        fieldLabel: fieldLabel,
      );
    case 'idCardNumber':
      return validateIdCardField(
        trimmedValue,
        required: required,
        fieldLabel: fieldLabel,
        allowLowercaseX: true,
      );
    case 'contactNumber':
      return validateContactNumberField(
        trimmedValue,
        required: required,
        fieldLabel: fieldLabel,
        strictPrefix: false,
      );
    case 'driverLicenseNumber':
      return validateExactDigitsFieldValue(
        trimmedValue,
        required: required,
        fieldLabel: fieldLabel,
        length: 12,
      );
    case 'allowedVehicleType':
      return validateMaxLength(
        trimmedValue,
        maxLength: 50,
        key: 'driverAdmin.validation.allowedVehicleTypeTooLong',
      );
    default:
      return null;
  }
}
