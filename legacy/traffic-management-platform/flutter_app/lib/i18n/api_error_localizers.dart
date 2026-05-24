import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:get/get.dart';

String _resolveCommonApiMessage(String message) {
  final normalized = message.trim();
  if (normalized.isEmpty || normalized == 'null') {
    return localizeUnknownApiError();
  }

  const exceptionPrefix = 'Exception: ';
  final unwrapped = normalized.startsWith(exceptionPrefix)
      ? normalized.substring(exceptionPrefix.length).trim()
      : normalized;

  if (unwrapped.contains('.') && !unwrapped.contains(' ')) {
    return unwrapped.tr;
  }

  switch (unwrapped.toLowerCase()) {
    case 'invalid_jwt':
    case 'invalid jwt':
      return 'auth.error.invalidJwt'.tr;
    case 'not_authenticated':
    case 'not authenticated':
    case 'unauthorized':
      return 'api.error.notAuthenticated'.tr;
    case 'invalid request data':
      return 'api.error.invalidRequestData'.tr;
    default:
      return unwrapped;
  }
}

String localizeMissingRequiredParam(String param) {
  return 'api.error.missingRequiredParam'.trParams({'param': param});
}

String localizeMissingRequiredParams(Iterable<String> params) {
  return 'api.error.missingRequiredParams'.trParams({
    'params': params.join(', '),
  });
}

String localizeDuplicateRequest(String idempotencyKey) {
  return 'api.error.duplicateRequestIdempotency'.trParams({
    'key': idempotencyKey,
  });
}

String localizeRemovedEndpoint(String endpoint) {
  return 'api.error.endpointRemoved'.trParams({'endpoint': endpoint});
}

String localizeEntityNotFoundWithId(String entity, Object id) {
  return 'api.error.entityNotFoundWithId'.trParams({
    'entity': entity,
    'id': '$id',
  });
}

String localizeAdminOnlyDelete(String resource) {
  return 'api.error.adminOnlyDelete'.trParams({'resource': resource});
}

String localizeInvalidRequestData() {
  return 'api.error.invalidRequestData'.tr;
}

String localizeCannotDetermineUserRole() {
  return 'api.error.cannotDetermineUserRole'.tr;
}

String localizeApiErrorMessageOrUnknown(Object? error) {
  return _resolveCommonApiMessage('$error');
}

String localizeApiErrorDetail(Object? error) {
  if (error is ApiException) {
    return _resolveCommonApiMessage(error.message);
  }
  return _resolveCommonApiMessage('$error');
}

String localizeHttpStatusError(int statusCode) {
  return 'api.error.httpStatus'.trParams({'statusCode': '$statusCode'});
}

String localizeUnknownApiError() {
  return 'api.error.unknown'.tr;
}

String localizeEmptyResponseApiError() {
  return 'api.error.emptyResponse'.tr;
}

bool isDuplicateRequestApiError(Object? error) {
  final message = '$error'.toLowerCase();
  return message.contains('duplicate request') || message.contains('duplicate');
}

bool isNotFoundApiError(Object? error) {
  return '$error'.toLowerCase().contains('not found');
}

bool isUnauthorizedApiError(Object? error) {
  final message = '$error'.toLowerCase();
  return message.contains('unauthorized') ||
      message.contains('not authenticated') ||
      message.contains('not_authenticated');
}

String formatLocalizedApiError(
  dynamic error, {
  required String requestKey,
  required String forbiddenKey,
  required String notFoundKey,
  required String serverKey,
  required String fallbackKey,
  String? duplicateKey,
}) {
  if (error is ApiException) {
    final localizedMessage = localizeApiErrorDetail(error);
    switch (error.code) {
      case 400:
        return requestKey.trParams({'message': localizedMessage});
      case 403:
        return forbiddenKey.trParams({'message': localizedMessage});
      case 404:
        return notFoundKey.trParams({'message': localizedMessage});
      case 409:
        if (duplicateKey != null) {
          return duplicateKey.trParams({'message': localizedMessage});
        }
        return serverKey.trParams({'message': localizedMessage});
      default:
        return serverKey.trParams({'message': localizedMessage});
    }
  }

  return fallbackKey.trParams({
    'error': localizeApiErrorDetail(error),
  });
}
