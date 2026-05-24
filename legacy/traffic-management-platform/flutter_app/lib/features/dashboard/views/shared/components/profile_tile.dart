import 'package:eva_icons_flutter/eva_icons_flutter.dart';
import 'package:final_assignment_front/features/dashboard/controllers/admin_dashboard_controller.dart';
import 'package:final_assignment_front/features/dashboard/controllers/user_dashboard_screen_controller.dart';
import 'package:final_assignment_front/features/dashboard/models/profile.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ProfilTile extends StatelessWidget {
  final Profile data;
  final VoidCallback onPressedNotification;
  final dynamic controller;

  const ProfilTile({
    super.key,
    required this.data,
    required this.onPressedNotification,
    required this.controller,
  });

  Future<String> _getUserRole() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('userRole') ?? 'USER';
  }

  @override
  Widget build(BuildContext context) {
    final bool isLight = Theme.of(context).brightness == Brightness.light;
    final Color backgroundColor = isLight
        ? Colors.white
        : Theme.of(context).cardColor.withValues(alpha: 0.9);
    final Color shadowColor =
        Colors.black.withValues(alpha: isLight ? 0.1 : 0.2);
    final Color defaultTextColor = isLight ? Colors.black87 : Colors.white;
    final Color subtitleTextColor =
        isLight ? Colors.grey.shade600 : Colors.white70;
    final Color iconColor = isLight ? Colors.grey.shade700 : Colors.white70;

    return FutureBuilder<String>(
      future: _getUserRole(),
      builder: (context, roleSnapshot) {
        if (roleSnapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }

        final String userRole = roleSnapshot.data ?? 'USER';

        return Obx(() {
          String displayName;
          String displayEmail;
          String displayPost;

          if (userRole == 'USER' && controller is UserDashboardController) {
            displayName = controller.currentDriverName.value.isNotEmpty
                ? controller.currentDriverName.value
                : data.name;
            displayEmail = controller.currentEmail.value.isNotEmpty
                ? controller.currentEmail.value
                : data.email;
            displayPost = 'shared.profileTile.role.userWelcome'.tr;
          } else if (userRole == 'ADMIN' && controller is DashboardController) {
            displayName = controller.currentDriverName.value.isNotEmpty
                ? controller.currentDriverName.value
                : data.name;
            displayEmail = controller.currentEmail.value.isNotEmpty
                ? controller.currentEmail.value
                : data.email;
            displayPost = 'shared.profileTile.role.adminWelcome'.tr;
          } else {
            displayName = data.name;
            displayEmail = data.email;
            displayPost = 'shared.profileTile.role.defaultWelcome'.tr;
          }

          return AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 12),
            decoration: BoxDecoration(
              color: backgroundColor,
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: shadowColor,
                  offset: const Offset(0, 3),
                  blurRadius: 8,
                  spreadRadius: 1,
                ),
              ],
            ),
            child: ListTile(
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              leading: CircleAvatar(
                backgroundImage: data.photo,
                radius: 28,
                backgroundColor:
                    isLight ? Colors.grey.shade200 : Colors.grey.shade800,
              ),
              title: Row(
                children: [
                  Flexible(
                    child: Text(
                      displayName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleLarge!.copyWith(
                            fontSize: 20,
                            fontWeight: FontWeight.w700,
                            color: defaultTextColor,
                          ),
                    ),
                  ),
                  const SizedBox(width: 60),
                  Expanded(
                    child: Text(
                      displayPost,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodyMedium!.copyWith(
                            fontSize: 16,
                            color: subtitleTextColor,
                          ),
                    ),
                  ),
                ],
              ),
              subtitle: Text(
                displayEmail,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.bodyMedium!.copyWith(
                      fontSize: 16,
                      color: subtitleTextColor,
                    ),
              ),
              trailing: IconButton(
                onPressed: onPressedNotification,
                icon: Icon(EvaIcons.bellOutline, size: 26, color: iconColor),
                tooltip: 'settings.notifications'.tr,
              ),
            ),
          );
        });
      },
    );
  }
}

