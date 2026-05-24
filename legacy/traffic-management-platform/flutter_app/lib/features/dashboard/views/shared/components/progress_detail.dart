// ignore_for_file: use_build_context_synchronously
import 'package:final_assignment_front/features/dashboard/controllers/progress_controller.dart';
import 'package:final_assignment_front/features/dashboard/controllers/user_dashboard_screen_controller.dart';
import 'package:final_assignment_front/features/model/progress_item.dart';
import 'package:final_assignment_front/i18n/progress_localizers.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class ProgressDetailPage extends StatefulWidget {
  final ProgressItem item;

  const ProgressDetailPage({super.key, required this.item});

  @override
  State<ProgressDetailPage> createState() => _ProgressDetailPageState();
}

class _ProgressDetailPageState extends State<ProgressDetailPage> {
  final ProgressController progressController = Get.find<ProgressController>();
  final UserDashboardController? dashboardController =
      Get.isRegistered<UserDashboardController>()
          ? Get.find<UserDashboardController>()
          : null;

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final themeData =
          dashboardController?.currentBodyTheme.value ?? ThemeData.light();
      return Scaffold(
        backgroundColor: themeData.colorScheme.surface,
        appBar: AppBar(
          title: Text('progress.detail.title'.tr),
          backgroundColor: themeData.colorScheme.primary,
          foregroundColor: themeData.colorScheme.onPrimary,
        ),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: ListView(
            children: [
              _buildDetailRow(
                'progress.detail.id'.tr,
                widget.item.id?.toString() ?? 'common.unknown'.tr,
                themeData,
              ),
              _buildDetailRow(
                  'progress.field.title'.tr, widget.item.title, themeData),
              _buildDetailRow(
                'progress.status'.tr,
                localizeProgressStatus(widget.item.status),
                themeData,
              ),
              _buildDetailRow(
                'progress.submitTime'.tr,
                formatProgressDateTime(
                  widget.item.submitTime,
                  includeSeconds: true,
                ),
                themeData,
              ),
              _buildDetailRow(
                'progress.detail.user'.tr,
                widget.item.username.isNotEmpty
                    ? widget.item.username
                    : (widget.item.userId?.toString() ?? 'common.notFilled'.tr),
                themeData,
              ),
              _buildDetailRow(
                'progress.field.details'.tr,
                widget.item.details ?? 'common.noData'.tr,
                themeData,
              ),
              _buildDetailRow(
                'progress.detail.relatedBusiness'.tr,
                progressController.getBusinessContext(widget.item),
                themeData,
              ),
            ],
          ),
        ),
      );
    });
  }

  Widget _buildDetailRow(String label, String? value, ThemeData themeData) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('common.labelWithColon'.trParams({'label': label}),
              style: themeData.textTheme.bodyLarge?.copyWith(
                fontWeight: FontWeight.bold,
                color: themeData.colorScheme.onSurface,
              )),
          Expanded(
            child: Text(
              value ?? 'common.unknown'.tr,
              style: themeData.textTheme.bodyMedium?.copyWith(
                color: themeData.colorScheme.onSurface,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
