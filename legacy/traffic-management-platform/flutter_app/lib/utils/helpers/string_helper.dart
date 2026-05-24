part of 'app_helpers.dart';

typedef CodeSelector<T extends Enum> = String Function(T value);

class StringHelper {
  const StringHelper._();

  static bool isNullOrBlank(String? value) =>
      value == null || value.trim().isEmpty;

  static String orDefault(
    String? value, {
    String placeholder = 'common.unknown',
  }) {
    return isNullOrBlank(value)
        ? _resolvePlaceholder(placeholder)
        : value!.trim();
  }

  static T? enumFromCode<T extends Enum>(
    Iterable<T> values,
    String? code,
    CodeSelector<T> codeSelector,
  ) {
    if (isNullOrBlank(code)) {
      return null;
    }
    final normalized = code!.trim().toLowerCase();
    for (final value in values) {
      final candidate = codeSelector(value).toLowerCase();
      if (candidate == normalized) {
        return value;
      }
    }
    return null;
  }

  static String labelFromCode<T extends Enum>(
    Iterable<T> values,
    String? code, {
    required CodeSelector<T> codeSelector,
    required String Function(T value) labelSelector,
    String placeholder = 'common.unknown',
  }) {
    final match = enumFromCode(values, code, codeSelector);
    return match == null
        ? _resolvePlaceholder(placeholder)
        : _resolvePlaceholder(labelSelector(match));
  }

  static String _resolvePlaceholder(String value) {
    return value.contains('.') ? value.tr.trim() : value.trim();
  }
}
