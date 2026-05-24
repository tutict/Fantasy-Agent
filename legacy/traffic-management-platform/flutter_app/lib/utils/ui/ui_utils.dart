import 'package:flutter/material.dart';
import 'package:get/get.dart';

part 'app_bottomshet.dart';
part 'app_dialog.dart';
part 'app_snackbar.dart';

class UiUtils {}

extension TextStyleExtension on TextStyle {
  TextStyle inputHeader(Color color) {
    return copyWith(
      fontWeight: FontWeight.bold,
      fontSize: 16,
      color: color,
    );
  }
}
