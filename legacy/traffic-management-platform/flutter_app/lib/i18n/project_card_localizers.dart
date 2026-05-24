import 'package:final_assignment_front/i18n/i18n_utils.dart';
import 'package:intl/intl.dart';

String formatProjectCardTime(DateTime date) {
  return DateFormat.Hms(currentLocaleName()).format(date);
}
