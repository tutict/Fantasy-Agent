part of 'ui_utils.dart';

class AppDialog {
  static String _resolveText(String value) {
    return value.contains('.') ? value.tr : value;
  }

  static Future<T?> showConfirmDialog<T>({
    required BuildContext context,
    required String title,
    required String message,
    String cancelText = 'common.cancel',
    String confirmText = 'common.confirm',
    VoidCallback? onConfirmed,
    VoidCallback? onCancelled,
    ThemeData? theme,
    Color? confirmColor,
    Color? cancelTextColor,
    IconData? leadingIcon,
  }) {
    final themeData = theme ?? Theme.of(context);
    return showDialog<T>(
      context: context,
      builder: (ctx) {
        final icon = leadingIcon ?? Icons.info_outline;
        final colorScheme = themeData.colorScheme;
        return Theme(
          data: themeData,
          child: AlertDialog(
            backgroundColor: colorScheme.surface,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(18),
            ),
            title: Row(
              children: [
                Icon(icon, color: colorScheme.primary),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    _resolveText(title),
                    style: themeData.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            content: Text(
              _resolveText(message),
              style: themeData.textTheme.bodyMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
            actionsPadding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            actions: [
              TextButton(
                onPressed: () {
                  Navigator.of(ctx).pop();
                  onCancelled?.call();
                },
                child: Text(
                  _resolveText(cancelText),
                  style: themeData.textTheme.labelLarge?.copyWith(
                    color: cancelTextColor ?? colorScheme.onSurfaceVariant,
                  ),
                ),
              ),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: confirmColor ?? colorScheme.primary,
                  foregroundColor: colorScheme.onPrimary,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
                onPressed: () {
                  Navigator.of(ctx).pop();
                  onConfirmed?.call();
                },
                child: Text(_resolveText(confirmText)),
              ),
            ],
          ),
        );
      },
    );
  }

  static Future<T?> showFormDialog<T>({
    required BuildContext context,
    required Widget formContent,
    String title = 'dialog.fillInfo',
    String confirmText = 'common.submit',
    String cancelText = 'common.cancel',
    VoidCallback? onSubmit,
    ThemeData? theme,
  }) {
    return showCustomDialog<T>(
      context: context,
      theme: theme,
      title: title,
      content: formContent,
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(_resolveText(cancelText)),
        ),
        ElevatedButton(
          onPressed: () {
            onSubmit?.call();
            Navigator.of(context).pop();
          },
          child: Text(_resolveText(confirmText)),
        ),
      ],
    );
  }

  static Future<T?> showCustomDialog<T>({
    required BuildContext context,
    required Widget content,
    String? title,
    List<Widget>? actions,
    ThemeData? theme,
  }) {
    final themeData = theme ?? Theme.of(context);
    return showDialog<T>(
      context: context,
      builder: (ctx) => Theme(
        data: themeData,
        child: AlertDialog(
          backgroundColor: themeData.colorScheme.surfaceContainerHighest,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
          title: title != null
              ? Text(
                  _resolveText(title),
                  style: themeData.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                )
              : null,
          content: content,
          actions: actions,
        ),
      ),
    );
  }
}
