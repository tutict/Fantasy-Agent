import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:get/get.dart';

String _resolveAuthErrorMessage(String message) {
  final normalized = message.trim();
  if (normalized.isEmpty) {
    return '';
  }

  if (normalized.contains('.') && !normalized.contains(' ')) {
    return normalized.tr;
  }

  switch (normalized.toLowerCase()) {
    case 'invalid_jwt':
    case 'invalid jwt':
      return 'auth.error.invalidJwt'.tr;
    case 'not_authenticated':
    case 'not authenticated':
    case 'unauthorized':
      return 'api.error.notAuthenticated'.tr;
    default:
      return normalized;
  }
}

String formatAuthApiError(ApiException error, String fallback) {
  final resolvedMessage = _resolveAuthErrorMessage(error.message);
  if (resolvedMessage.isEmpty || resolvedMessage == fallback) {
    return fallback;
  }
  return '$fallback: $resolvedMessage';
}

String formatAuthErrorDetail(Object? error) {
  if (error is ApiException) {
    final resolvedMessage = _resolveAuthErrorMessage(error.message);
    if (resolvedMessage.isNotEmpty) {
      return resolvedMessage;
    }
  }

  return localizeApiErrorDetail(error);
}
