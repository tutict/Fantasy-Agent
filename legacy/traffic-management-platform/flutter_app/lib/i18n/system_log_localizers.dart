import 'package:final_assignment_front/features/model/login_log.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/i18n/i18n_utils.dart';
import 'package:get/get.dart';

String formatSystemLogOverviewLabel(String key) {
  final translationKey = 'systemLog.overview.$key';
  final translated = translationKey.tr;
  if (translated != translationKey) {
    return translated;
  }

  final snake = key.replaceAll('_', ' ');
  return snake.replaceAllMapped(
    RegExp('(?<=[a-z])([A-Z])'),
    (match) => ' ${match.group(1)}',
  );
}

String buildSystemLogDeviceInfo(LoginLog log) {
  final parts = <String>[];
  if (log.browserType != null && log.browserType!.isNotEmpty) {
    parts.add(log.browserType!);
  }
  if (log.osType != null && log.osType!.isNotEmpty) {
    parts.add(log.osType!);
  }
  if (log.deviceType != null && log.deviceType!.isNotEmpty) {
    parts.add(log.deviceType!);
  }
  return parts.isEmpty ? 'common.unknown'.tr : parts.join(' / ');
}

String formatSystemLogError(dynamic error) {
  return formatLocalizedApiError(
    error,
    requestKey: 'systemLog.error.request',
    forbiddenKey: 'systemLog.error.forbidden',
    notFoundKey: 'systemLog.error.notFound',
    duplicateKey: 'systemLog.error.duplicateRequest',
    serverKey: 'systemLog.error.server',
    fallbackKey: 'systemLog.error.operationFailed',
  );
}

String formatSystemLogDateTime(DateTime? dateTime) {
  return formatLocalizedDateTime(
    dateTime,
    emptyKey: 'common.notFilled',
  );
}

String localizeSystemLogResult(
  String? result, {
  String emptyKey = 'common.unknown',
}) {
  return localizeCommonResult(result, emptyKey: emptyKey);
}
