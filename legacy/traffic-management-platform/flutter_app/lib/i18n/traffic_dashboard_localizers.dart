import 'package:final_assignment_front/i18n/i18n_utils.dart';

String formatTrafficDashboardDate(
  DateTime? date, {
  String emptyKey = 'common.notFilled',
}) {
  return formatLocalizedDate(date, emptyKey: emptyKey);
}

String formatTrafficDashboardAxisDate(DateTime date) {
  return formatLocalizedPatternDate(date, 'Md');
}
