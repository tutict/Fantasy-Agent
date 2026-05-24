// ignore_for_file: use_build_context_synchronously

import 'package:final_assignment_front/config/routes/app_routes.dart';
import 'package:final_assignment_front/features/dashboard/controllers/progress_controller.dart';
import 'package:final_assignment_front/features/dashboard/controllers/user_dashboard_screen_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/dashboard_page_template.dart';
import 'package:final_assignment_front/i18n/progress_localizers.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class OnlineProcessingProgress extends StatelessWidget {
  const OnlineProcessingProgress({super.key});

  @override
  Widget build(BuildContext context) {
    final UserDashboardController dashboardController =
        Get.find<UserDashboardController>();

    ProgressController progressController;
    try {
      progressController = Get.find<ProgressController>();
    } catch (e) {
      progressController = Get.put(ProgressController());
      debugPrint('ProgressController was not found; registered locally: $e');
    }

    return Obx(() {
      final themeData = dashboardController.currentBodyTheme.value;
      return DashboardPageTemplate(
        theme: themeData,
        title: 'progress.pageTitle'.tr,
        pageType: DashboardPageType.user,
        onThemeToggle: dashboardController.toggleBodyTheme,
        onRefresh: () => progressController.fetchProgress(),
        bodyIsScrollable: true,
        padding: EdgeInsets.zero,
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              _buildFilterControls(progressController, themeData),
              const SizedBox(height: 16),
              Expanded(
                child: progressController.isLoading.value
                    ? Center(
                        child: CircularProgressIndicator(
                          valueColor: AlwaysStoppedAnimation(
                            themeData.colorScheme.primary,
                          ),
                        ),
                      )
                    : progressController.errorMessage.isNotEmpty
                        ? Center(
                            child: Text(
                              progressController.errorMessage.value,
                              style: themeData.textTheme.bodyLarge?.copyWith(
                                color: themeData.colorScheme.error,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          )
                        : progressController.filteredItems.isEmpty
                            ? Center(
                                child: Text(
                                  'progress.empty'.tr,
                                  style:
                                      themeData.textTheme.titleMedium?.copyWith(
                                    color:
                                        themeData.colorScheme.onSurfaceVariant,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              )
                            : ListView.builder(
                                itemCount:
                                    progressController.filteredItems.length,
                                itemBuilder: (context, index) {
                                  final item =
                                      progressController.filteredItems[index];
                                  return Card(
                                    elevation: 3,
                                    color:
                                        themeData.colorScheme.surfaceContainer,
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(16),
                                    ),
                                    margin:
                                        const EdgeInsets.symmetric(vertical: 8),
                                    child: ListTile(
                                      contentPadding:
                                          const EdgeInsets.symmetric(
                                        horizontal: 16,
                                        vertical: 12,
                                      ),
                                      leading: CircleAvatar(
                                        backgroundColor: _getStatusColor(
                                          item.status,
                                          themeData,
                                        ),
                                        radius: 24,
                                        child: Text(
                                          item.title.isNotEmpty
                                              ? item.title[0].toUpperCase()
                                              : '?',
                                          style: themeData.textTheme.titleMedium
                                              ?.copyWith(
                                            color: Colors.white,
                                            fontWeight: FontWeight.bold,
                                          ),
                                        ),
                                      ),
                                      title: Text(
                                        item.title,
                                        style: themeData.textTheme.titleMedium
                                            ?.copyWith(
                                          color:
                                              themeData.colorScheme.onSurface,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                      subtitle: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          const SizedBox(height: 4),
                                          Text(
                                            '${'progress.status'.tr}: ${localizeProgressStatus(item.status)}',
                                            style: themeData
                                                .textTheme.bodyMedium
                                                ?.copyWith(
                                              color: _getStatusColor(
                                                item.status,
                                                themeData,
                                              ),
                                              fontWeight: FontWeight.w500,
                                            ),
                                          ),
                                          Text(
                                            '${'progress.submitTime'.tr}: ${formatProgressDateTime(item.submitTime)}',
                                            style: themeData
                                                .textTheme.bodyMedium
                                                ?.copyWith(
                                              color: themeData
                                                  .colorScheme.onSurfaceVariant,
                                            ),
                                          ),
                                          Text(
                                            progressController
                                                .getBusinessContext(item),
                                            style: themeData.textTheme.bodySmall
                                                ?.copyWith(
                                              color: themeData
                                                  .colorScheme.onSurfaceVariant
                                                  .withValues(alpha: 0.8),
                                            ),
                                          ),
                                        ],
                                      ),
                                      trailing: Icon(
                                        Icons.chevron_right,
                                        color: themeData
                                            .colorScheme.onSurfaceVariant,
                                      ),
                                      onTap: () => Get.toNamed(
                                        Routes.progressDetailPage,
                                        arguments: item,
                                      )?.then((result) {
                                        if (result == true) {
                                          progressController.fetchProgress();
                                        }
                                      }),
                                    ),
                                  );
                                },
                              ),
              ),
            ],
          ),
        ),
      );
    });
  }

  Widget _buildFilterControls(
    ProgressController controller,
    ThemeData themeData,
  ) {
    return Row(
      children: [
        Expanded(
          child: DropdownButtonFormField<String>(
            initialValue: controller.statusCategories.isNotEmpty
                ? controller.statusCategories.first
                : null,
            decoration: InputDecoration(
              labelText: 'progress.filter.status'.tr,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              filled: true,
              fillColor: themeData.colorScheme.surfaceContainer,
            ),
            items: controller.statusCategories
                .map(
                  (status) => DropdownMenuItem<String>(
                    value: status,
                    child: Text(localizeProgressStatus(status)),
                  ),
                )
                .toList(),
            onChanged: (value) {
              if (value != null) {
                controller.filterByStatus(value);
              }
            },
          ),
        ),
        const SizedBox(width: 16),
        IconButton(
          icon: Icon(Icons.date_range, color: themeData.colorScheme.primary),
          onPressed: () => _showDateRangePicker(controller, themeData),
          tooltip: 'progress.filter.timeRange'.tr,
        ),
        IconButton(
          icon: Icon(Icons.clear, color: themeData.colorScheme.error),
          onPressed: () {
            controller.clearTimeRangeFilter();
            controller.fetchProgress();
          },
          tooltip: 'progress.filter.clear'.tr,
        ),
      ],
    );
  }

  void _showDateRangePicker(
    ProgressController controller,
    ThemeData themeData,
  ) async {
    final pickedRange = await showDateRangePicker(
      context: Get.context!,
      firstDate: DateTime(2000),
      lastDate: DateTime.now(),
      locale: Get.locale ?? const Locale('en', 'US'),
      initialDateRange: DateTimeRange(
        start: DateTime.now().subtract(const Duration(days: 7)),
        end: DateTime.now(),
      ),
    );

    if (pickedRange != null) {
      await controller.fetchProgressByTimeRange(
        pickedRange.start,
        pickedRange.end,
      );
    }
  }

  Color _getStatusColor(String? status, ThemeData themeData) {
    return progressStatusColor(status, themeData);
  }
}
