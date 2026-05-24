import 'package:final_assignment_front/i18n/i18n_utils.dart';

String formatNewsDate(DateTime date) {
  return formatLocalizedPatternDate(date, 'yMMMd');
}
