import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/i18n/i18n_utils.dart';
import 'package:get/get.dart';

const String kVehiclePlatePrefix = '\u9ed1A';
const String kVehicleSearchTypeLicensePlate = 'licensePlate';
const String kVehicleSearchTypeVehicleType = 'vehicleType';

const String kVehicleFieldLicensePlate = 'vehicle.field.licensePlate';
const String kVehicleFieldType = 'vehicle.field.vehicleType';
const String kVehicleFieldOwnerName = 'vehicle.field.ownerName';
const String kVehicleFieldIdCard = 'vehicle.field.idCardNumber';
const String kVehicleFieldContact = 'vehicle.field.contactNumber';
const String kVehicleFieldEngineNumber = 'vehicle.field.engineNumber';
const String kVehicleFieldFrameNumber = 'vehicle.field.frameNumber';
const String kVehicleFieldColor = 'vehicle.field.vehicleColor';
const String kVehicleFieldFirstRegistrationDate =
    'vehicle.field.firstRegistrationDate';
const String kVehicleFieldCurrentStatus = 'vehicle.field.currentStatus';

bool isValidLicensePlate(String value) {
  final regex = RegExp(r'^[\u4e00-\u9fa5][A-Za-z][A-Za-z0-9]{5,6}$');
  return regex.hasMatch(value);
}

String formatVehicleDate(
  DateTime? date, {
  String emptyKey = 'common.notFilled',
}) {
  return formatLocalizedDate(date, emptyKey: emptyKey);
}

bool shouldShowVehicleUserReloginAction(String message) {
  return isAnyLocalizedMessage(message, const [
    'vehicle.error.unauthorized',
    'vehicle.error.jwtMissingRelogin',
    'vehicle.error.usernameMissingInJwt',
  ]);
}

bool shouldShowVehicleAdminReloginAction(String message) {
  return isAnyLocalizedMessage(message, const [
    'vehicle.error.unauthorized',
    'vehicle.error.expired',
    'vehicle.error.refreshedExpired',
    'vehicle.error.invalidLogin',
  ]);
}

String formatVehicleError(Object? error) {
  return localizeApiErrorDetail(error);
}

String vehicleSearchHintText(String searchType) {
  switch (searchType) {
    case kVehicleSearchTypeVehicleType:
      return 'vehicle.search.byType'.tr;
    case kVehicleSearchTypeLicensePlate:
    default:
      return 'vehicle.search.byPlate'.tr;
  }
}

String vehicleSearchTypeLabel(String searchType) {
  return vehicleSearchHintText(searchType);
}

String vehicleSearchFieldLabel(String searchType) {
  switch (searchType) {
    case kVehicleSearchTypeVehicleType:
      return 'vehicle.field.vehicleType'.tr;
    case kVehicleSearchTypeLicensePlate:
    default:
      return 'vehicle.field.licensePlate'.tr;
  }
}

String vehicleFieldTranslationKey(String fieldKey) {
  switch (fieldKey) {
    case 'licensePlate':
    case kVehicleFieldLicensePlate:
      return kVehicleFieldLicensePlate;
    case 'vehicleType':
    case kVehicleFieldType:
      return kVehicleFieldType;
    case 'ownerName':
    case kVehicleFieldOwnerName:
      return kVehicleFieldOwnerName;
    case 'idCardNumber':
    case kVehicleFieldIdCard:
      return kVehicleFieldIdCard;
    case 'contactNumber':
    case kVehicleFieldContact:
      return kVehicleFieldContact;
    case 'engineNumber':
    case kVehicleFieldEngineNumber:
      return kVehicleFieldEngineNumber;
    case 'frameNumber':
    case kVehicleFieldFrameNumber:
      return kVehicleFieldFrameNumber;
    case 'vehicleColor':
    case kVehicleFieldColor:
      return kVehicleFieldColor;
    case 'firstRegistrationDate':
    case kVehicleFieldFirstRegistrationDate:
      return kVehicleFieldFirstRegistrationDate;
    case 'currentStatus':
    case kVehicleFieldCurrentStatus:
      return kVehicleFieldCurrentStatus;
    default:
      return fieldKey;
  }
}

bool isVehicleField(String fieldKey, String expectedTranslationKey) {
  return vehicleFieldTranslationKey(fieldKey) == expectedTranslationKey;
}

String vehicleFieldLabel(String fieldKey) {
  return vehicleFieldTranslationKey(fieldKey).tr;
}

String? vehicleFieldHelperKey(String fieldKey) {
  switch (vehicleFieldTranslationKey(fieldKey)) {
    case kVehicleFieldLicensePlate:
      return 'vehicle.helper.plateSuffix';
    case kVehicleFieldIdCard:
      return 'vehicle.helper.idCard';
    case kVehicleFieldContact:
      return 'vehicle.helper.contact';
    default:
      return null;
  }
}

String? vehicleFieldHelperText(String fieldKey) {
  return vehicleFieldHelperKey(fieldKey)?.tr;
}

String? vehicleFieldHintKey(String fieldKey, {bool readOnly = false}) {
  if (readOnly && isVehicleField(fieldKey, kVehicleFieldIdCard)) {
    return 'vehicle.hint.modifyIdCardInProfile';
  }
  return null;
}

String? vehicleFieldHintText(String fieldKey, {bool readOnly = false}) {
  return vehicleFieldHintKey(fieldKey, readOnly: readOnly)?.tr;
}

String? validateVehicleField(
  String fieldKey,
  String? value, {
  bool required = false,
  DateTime? selectedDate,
}) {
  final trimmedValue = value?.trim() ?? '';
  final translationKey = vehicleFieldTranslationKey(fieldKey);

  if (required && trimmedValue.isEmpty) {
    return formatRequiredFieldValidation(
      'vehicle.validation.required',
      translationKey.tr,
    );
  }

  if (trimmedValue.isEmpty) {
    return null;
  }

  switch (translationKey) {
    case kVehicleFieldLicensePlate:
      final fullPlate = '$kVehiclePlatePrefix$trimmedValue';
      if (fullPlate.length > 20) {
        return 'vehicle.validation.licensePlateTooLong'.tr;
      }
      if (!isValidLicensePlate(fullPlate)) {
        return 'vehicle.validation.licensePlateInvalid'.tr;
      }
      return null;
    case kVehicleFieldType:
      return validateMaxLength(
        trimmedValue,
        maxLength: 50,
        key: 'vehicle.validation.vehicleTypeTooLong',
      );
    case kVehicleFieldOwnerName:
      return validateMaxLength(
        trimmedValue,
        maxLength: 100,
        key: 'vehicle.validation.ownerNameTooLong',
      );
    case kVehicleFieldIdCard:
      return validateIdCardField(
        trimmedValue,
        required: required,
        fieldLabel: translationKey.tr,
        allowLowercaseX: true,
        maxLength: 18,
        invalidKey: 'vehicle.validation.idCardInvalid',
        tooLongKey: 'vehicle.validation.idCardTooLong',
      );
    case kVehicleFieldContact:
      return validateContactNumberField(
        trimmedValue,
        required: required,
        fieldLabel: translationKey.tr,
        strictPrefix: false,
        maxLength: 20,
        invalidKey: 'vehicle.validation.contactInvalid',
        tooLongKey: 'vehicle.validation.contactTooLong',
      );
    case kVehicleFieldEngineNumber:
      return validateMaxLength(
        trimmedValue,
        maxLength: 50,
        key: 'vehicle.validation.engineTooLong',
      );
    case kVehicleFieldFrameNumber:
      return validateMaxLength(
        trimmedValue,
        maxLength: 50,
        key: 'vehicle.validation.frameTooLong',
      );
    case kVehicleFieldColor:
      return validateMaxLength(
        trimmedValue,
        maxLength: 50,
        key: 'vehicle.validation.colorTooLong',
      );
    case kVehicleFieldFirstRegistrationDate:
      return validateNonFutureDate(
        selectedDate,
        invalidKey: 'vehicle.validation.dateInvalid',
        futureKey: 'vehicle.validation.dateFuture',
      );
    case kVehicleFieldCurrentStatus:
      return validateMaxLength(
        trimmedValue,
        maxLength: 50,
        key: 'vehicle.validation.statusTooLong',
      );
    default:
      return null;
  }
}
