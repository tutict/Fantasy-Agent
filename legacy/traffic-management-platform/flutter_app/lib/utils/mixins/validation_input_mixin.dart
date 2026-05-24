part of 'app_mixins.dart';

mixin ValidatorMixin {
  String? validateTextFieldIsRequired(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'validation.required'.tr;
    }
    return null;
  }
}

mixin ValidationInputMixin {
  bool validateEmail(String email) {
    final emailRegex =
        RegExp(r'^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$');
    return emailRegex.hasMatch(email);
  }
}
