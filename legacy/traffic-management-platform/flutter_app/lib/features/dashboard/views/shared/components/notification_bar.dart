import 'dart:developer' as developer;

import 'package:eva_icons_flutter/eva_icons_flutter.dart';
import 'package:final_assignment_front/config/routes/app_routes.dart';
import 'package:final_assignment_front/constants/app_constants.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class NotificationBarData {
  final String message;
  final IconData icon;
  final String actionText;
  final String routeName;

  const NotificationBarData({
    required this.message,
    required this.icon,
    required this.actionText,
    required this.routeName,
  });
}

String _resolveNotificationText(String value) {
  return value.contains('.') ? value.tr : value;
}

void navigateToPage(String routeName) {
  developer.log('Navigating to route: $routeName');
  try {
    Get.toNamed(routeName);
  } catch (e) {
    developer.log('Navigation error: $e', stackTrace: StackTrace.current);
    Get.snackbar(
      'common.unknown'.tr,
      'shared.notificationBar.navigationError'.tr,
    );
  }
}

class NotificationBar extends StatelessWidget {
  const NotificationBar({
    super.key,
    this.data = const NotificationBarData(
      message: 'shared.notificationBar.defaultMessage',
      icon: EvaIcons.alertCircleOutline,
      actionText: 'shared.notificationBar.defaultAction',
      routeName: Routes.personalMain,
    ),
    this.onPressedAction,
  });

  final NotificationBarData data;
  final VoidCallback? onPressedAction;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final bool isLight = theme.brightness == Brightness.light;
    final Color shadowColor =
        Colors.black.withValues(alpha: isLight ? 0.1 : 0.15);
    final Color textColor =
        isLight ? Colors.black87 : theme.colorScheme.onSurface;
    final Color iconColor = isLight
        ? theme.colorScheme.onSurfaceVariant
        : theme.colorScheme.onSurface.withValues(alpha: 0.7);
    final Color arrowColor = isLight
        ? theme.colorScheme.primary
        : theme.colorScheme.primary.withValues(alpha: 0.9);

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(kBorderRadius),
        border: Border.all(
          color: theme.colorScheme.outline.withValues(alpha: 0.2),
          width: 1,
        ),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: isLight
              ? [Colors.white, Colors.grey[50]!]
              : [
                  theme.colorScheme.surface,
                  theme.colorScheme.surfaceContainerHighest.withValues(
                    alpha: 0.8,
                  ),
                ],
        ),
        boxShadow: [
          BoxShadow(
            color: shadowColor,
            offset: const Offset(0, 3),
            blurRadius: 8,
            spreadRadius: 1,
          ),
        ],
      ),
      child: InkWell(
        onTap: onPressedAction ?? () => navigateToPage(data.routeName),
        borderRadius: BorderRadius.circular(kBorderRadius),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
          child: Row(
            children: [
              Icon(data.icon, size: 24, color: iconColor),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  _resolveNotificationText(data.message),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.bodyLarge!.copyWith(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: textColor,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              IconButton(
                onPressed:
                    onPressedAction ?? () => navigateToPage(data.routeName),
                icon: Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: arrowColor.withValues(alpha: 0.1),
                  ),
                  child: Icon(
                    EvaIcons.arrowForwardOutline,
                    size: 24,
                    color: arrowColor,
                  ),
                ),
                tooltip: _resolveNotificationText(data.actionText),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
