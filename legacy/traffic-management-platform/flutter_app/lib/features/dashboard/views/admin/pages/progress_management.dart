import 'package:final_assignment_front/config/routes/app_routes.dart';
import 'package:final_assignment_front/features/dashboard/controllers/progress_controller.dart';
import 'package:final_assignment_front/features/dashboard/controllers/admin_dashboard_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/dashboard_page_template.dart';
import 'package:final_assignment_front/features/model/sys_request_history.dart';
import 'package:final_assignment_front/i18n/progress_localizers.dart';
import 'package:final_assignment_front/utils/ui/ui_utils.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class ProgressManagementPage extends StatefulWidget {
  const ProgressManagementPage({super.key});

  @override
  State<ProgressManagementPage> createState() => _ProgressManagementPageState();
}

class _ProgressManagementPageState extends State<ProgressManagementPage> {
  final TextEditingController _refundFineIdController = TextEditingController();
  final TextEditingController _refundPaymentIdController =
      TextEditingController();

  @override
  void dispose() {
    _refundFineIdController.dispose();
    _refundPaymentIdController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final DashboardController dashboardController =
        Get.find<DashboardController>();
    final ProgressController progressController =
        Get.find<ProgressController>();

    return Obx(() {
      final themeData = dashboardController.currentBodyTheme.value;
      return DashboardPageTemplate(
        theme: themeData,
        title: 'progress.pageTitle'.tr,
        pageType: DashboardPageType.admin,
        bodyIsScrollable: true,
        padding: EdgeInsets.zero,
        actions: const [],
        body: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            children: [
              _buildViewSwitcher(progressController, themeData),
              const SizedBox(height: 16),
              progressController.isRefundView
                  ? _buildRefundFilterControls(progressController, themeData)
                  : _buildFilterControls(
                      context, progressController, themeData),
              const SizedBox(height: 16),
              Expanded(
                child: progressController.isLoading.value
                    ? Center(
                        child: CircularProgressIndicator(
                          valueColor: AlwaysStoppedAnimation(
                              themeData.colorScheme.primary),
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
                        : !progressController.isAdmin
                            ? Center(
                                child: Text(
                                  'progress.error.adminOnly'.tr,
                                  style:
                                      themeData.textTheme.titleMedium?.copyWith(
                                    color:
                                        themeData.colorScheme.onSurfaceVariant,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              )
                            : progressController.isRefundView
                                ? _buildRefundAuditList(
                                    progressController, themeData)
                                : _buildProgressList(
                                    context, progressController, themeData),
              ),
            ],
          ),
        ),
      );
    });
  }

  Widget _buildViewSwitcher(
      ProgressController controller, ThemeData themeData) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          ChoiceChip(
            label: Text('progress.view.items'.tr),
            selected: controller.selectedView.value == progressViewItems,
            onSelected: (_) => controller.switchView(progressViewItems),
            selectedColor: themeData.colorScheme.primaryContainer,
            labelStyle: themeData.textTheme.bodyMedium?.copyWith(
              color: themeData.colorScheme.onSurface,
              fontWeight: FontWeight.w600,
            ),
          ),
          ChoiceChip(
            label: Text('progress.view.refunds'.tr),
            selected: controller.selectedView.value == progressViewRefunds,
            onSelected: (_) => controller.switchView(progressViewRefunds),
            selectedColor: themeData.colorScheme.primaryContainer,
            labelStyle: themeData.textTheme.bodyMedium?.copyWith(
              color: themeData.colorScheme.onSurface,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProgressList(BuildContext context, ProgressController controller,
      ThemeData themeData) {
    if (controller.filteredItems.isEmpty) {
      return Center(
        child: Text(
          'progress.empty'.tr,
          style: themeData.textTheme.titleMedium?.copyWith(
            color: themeData.colorScheme.onSurfaceVariant,
            fontWeight: FontWeight.w500,
          ),
        ),
      );
    }

    return ListView.builder(
      itemCount: controller.filteredItems.length,
      itemBuilder: (context, index) {
        final item = controller.filteredItems[index];
        return Card(
          elevation: 3,
          color: themeData.colorScheme.surfaceContainer,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          margin: const EdgeInsets.symmetric(vertical: 8),
          child: ListTile(
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            leading: CircleAvatar(
              backgroundColor: _getStatusColor(item.status, themeData),
              radius: 24,
              child: Text(
                item.title.isNotEmpty ? item.title[0].toUpperCase() : '?',
                style: themeData.textTheme.titleMedium?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            title: Text(
              item.title,
              style: themeData.textTheme.titleMedium?.copyWith(
                color: themeData.colorScheme.onSurface,
                fontWeight: FontWeight.w600,
              ),
            ),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 4),
                Text(
                  'progress.detail.status'.trParams({
                    'value': localizeProgressStatus(item.status),
                  }),
                  style: themeData.textTheme.bodyMedium?.copyWith(
                    color: _getStatusColor(item.status, themeData),
                    fontWeight: FontWeight.w500,
                  ),
                ),
                Text(
                  'progress.detail.submitTime'.trParams({
                    'value': formatProgressDateTime(item.submitTime),
                  }),
                  style: themeData.textTheme.bodyMedium?.copyWith(
                    color: themeData.colorScheme.onSurfaceVariant,
                  ),
                ),
                Text(
                  controller.getBusinessContext(item),
                  style: themeData.textTheme.bodySmall?.copyWith(
                    color: themeData.colorScheme.onSurfaceVariant
                        .withValues(alpha: 0.8),
                  ),
                ),
              ],
            ),
            trailing: Icon(
              Icons.chevron_right,
              color: themeData.colorScheme.onSurfaceVariant,
            ),
            onTap: () => Get.toNamed(Routes.progressDetailPage, arguments: item)
                ?.then((result) {
              if (result == true) {
                controller.fetchProgress();
              }
            }),
          ),
        );
      },
    );
  }

  Widget _buildRefundAuditList(
      ProgressController controller, ThemeData themeData) {
    if (controller.refundAudits.isEmpty) {
      return Center(
        child: Text(
          'progress.refund.empty'.tr,
          style: themeData.textTheme.titleMedium?.copyWith(
            color: themeData.colorScheme.onSurfaceVariant,
            fontWeight: FontWeight.w500,
          ),
        ),
      );
    }

    return ListView.builder(
      itemCount: controller.refundAudits.length,
      itemBuilder: (context, index) {
        final item = controller.refundAudits[index];
        return Card(
          elevation: 3,
          color: themeData.colorScheme.surfaceContainer,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          margin: const EdgeInsets.symmetric(vertical: 8),
          child: ListTile(
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            leading: CircleAvatar(
              backgroundColor:
                  refundAuditStatusColor(item.businessStatus, themeData),
              radius: 24,
              child: Icon(
                item.businessStatus == 'FAILED'
                    ? Icons.error_outline
                    : Icons.currency_exchange,
                color: Colors.white,
              ),
            ),
            title: Text(
              localizeRefundBusinessType(item.businessType),
              style: themeData.textTheme.titleMedium?.copyWith(
                color: themeData.colorScheme.onSurface,
                fontWeight: FontWeight.w600,
              ),
            ),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 4),
                Text(
                  'progress.detail.status'.trParams({
                    'value': localizeRefundAuditStatus(item.businessStatus),
                  }),
                  style: themeData.textTheme.bodyMedium?.copyWith(
                    color:
                        refundAuditStatusColor(item.businessStatus, themeData),
                    fontWeight: FontWeight.w500,
                  ),
                ),
                Text(
                  'progress.detail.submitTime'.trParams({
                    'value': formatProgressDateTime(item.createdTime),
                  }),
                  style: themeData.textTheme.bodyMedium?.copyWith(
                    color: themeData.colorScheme.onSurfaceVariant,
                  ),
                ),
                Text(
                  'progress.refund.detail.updatedTime'.trParams({
                    'value': formatProgressDateTime(item.modifiedTime),
                  }),
                  style: themeData.textTheme.bodyMedium?.copyWith(
                    color: themeData.colorScheme.onSurfaceVariant,
                  ),
                ),
                Text(
                  controller.refundAuditSummary(item),
                  style: themeData.textTheme.bodySmall?.copyWith(
                    color: themeData.colorScheme.onSurfaceVariant
                        .withValues(alpha: 0.85),
                  ),
                ),
                Text(
                  controller.refundAuditReason(item),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: themeData.textTheme.bodySmall?.copyWith(
                    color: themeData.colorScheme.onSurfaceVariant
                        .withValues(alpha: 0.85),
                  ),
                ),
              ],
            ),
            trailing: Icon(
              Icons.chevron_right,
              color: themeData.colorScheme.onSurfaceVariant,
            ),
            onTap: () => _showRefundAuditDetailDialog(
              context,
              controller,
              item,
              themeData,
            ),
          ),
        );
      },
    );
  }

  Widget _buildFilterControls(BuildContext context,
      ProgressController controller, ThemeData themeData) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: controller.statusCategories.map((status) {
            return Obx(() => FilterChip(
                  label: Text(localizeProgressStatus(status)),
                  selected: controller.filteredItems.any((item) =>
                      normalizeProgressStatusCode(item.status) ==
                      normalizeProgressStatusCode(status)),
                  onSelected: (selected) {
                    controller.filterByStatus(status);
                  },
                  selectedColor: themeData.colorScheme.primaryContainer,
                  checkmarkColor: themeData.colorScheme.onPrimaryContainer,
                  labelStyle: themeData.textTheme.bodyMedium?.copyWith(
                    color: themeData.colorScheme.onSurface,
                  ),
                ));
          }).toList(),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                icon: Icon(Icons.date_range,
                    color: themeData.colorScheme.primary),
                label: Text(
                  'progress.filter.selectTimeRange'.tr,
                  style: themeData.textTheme.bodyMedium
                      ?.copyWith(color: themeData.colorScheme.primary),
                ),
                onPressed: () => _showDateRangePicker(controller, themeData),
                style: OutlinedButton.styleFrom(
                  side: BorderSide(color: themeData.colorScheme.outline),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ),
            const SizedBox(width: 8),
            IconButton(
              icon: Icon(Icons.clear, color: themeData.colorScheme.error),
              onPressed: () {
                controller.clearTimeRangeFilter();
                controller.fetchProgress();
              },
              tooltip: 'progress.filter.clearTooltip'.tr,
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildRefundFilterControls(
      ProgressController controller, ThemeData themeData) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: controller.refundStatusCategories.map((status) {
            return ChoiceChip(
              label: Text(localizeRefundAuditStatus(status)),
              selected: controller.selectedRefundStatus.value == status,
              onSelected: (_) => controller.setRefundStatusFilter(status),
              selectedColor: themeData.colorScheme.primaryContainer,
              labelStyle: themeData.textTheme.bodyMedium?.copyWith(
                color: themeData.colorScheme.onSurface,
              ),
            );
          }).toList(),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            SizedBox(
              width: 220,
              child: TextField(
                controller: _refundFineIdController,
                keyboardType: TextInputType.number,
                onChanged: controller.setRefundFineIdFilter,
                decoration: InputDecoration(
                  labelText: 'progress.refund.filter.fineId'.tr,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
            ),
            SizedBox(
              width: 220,
              child: TextField(
                controller: _refundPaymentIdController,
                keyboardType: TextInputType.number,
                onChanged: controller.setRefundPaymentIdFilter,
                decoration: InputDecoration(
                  labelText: 'progress.refund.filter.paymentId'.tr,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
            ),
            FilledButton.icon(
              onPressed: controller.fetchRefundAudits,
              icon: const Icon(Icons.search),
              label: Text('common.search'.tr),
            ),
            OutlinedButton.icon(
              onPressed: () {
                _refundFineIdController.clear();
                _refundPaymentIdController.clear();
                controller.clearRefundFilters();
              },
              icon: Icon(Icons.clear, color: themeData.colorScheme.error),
              label: Text(
                'progress.filter.clear'.tr,
                style: themeData.textTheme.bodyMedium?.copyWith(
                  color: themeData.colorScheme.error,
                ),
              ),
              style: OutlinedButton.styleFrom(
                side: BorderSide(color: themeData.colorScheme.error),
              ),
            ),
          ],
        ),
      ],
    );
  }

  void _showRefundAuditDetailDialog(
    BuildContext context,
    ProgressController controller,
    SysRequestHistoryModel item,
    ThemeData themeData,
  ) {
    final params = controller.getRefundAuditParams(item);
    final detailLines = <String>[
      'progress.refund.detail.businessType'.trParams({
        'value': localizeRefundBusinessType(item.businessType),
      }),
      'progress.detail.status'.trParams({
        'value': localizeRefundAuditStatus(item.businessStatus),
      }),
      'progress.detail.submitTime'.trParams({
        'value': formatProgressDateTime(item.createdTime, includeSeconds: true),
      }),
      'progress.refund.detail.updatedTime'.trParams({
        'value':
            formatProgressDateTime(item.modifiedTime, includeSeconds: true),
      }),
      'progress.refund.detail.businessId'.trParams({
        'value': params['paymentId'] ??
            item.businessId?.toString() ??
            'common.notFilled'.tr,
      }),
      'progress.refund.detail.fineId'.trParams({
        'value': params['fineId'] ?? 'common.notFilled'.tr,
      }),
      'progress.refund.detail.refundAmount'.trParams({
        'value': params['refundAmount'] ?? 'common.notFilled'.tr,
      }),
      'progress.refund.detail.operator'.trParams({
        'value': controller.refundAuditOperator(item),
      }),
      'progress.refund.detail.reason'.trParams({
        'value': controller.refundAuditReason(item),
      }),
      'progress.refund.detail.requestIp'.trParams({
        'value': item.requestIp ?? 'common.notFilled'.tr,
      }),
      'progress.refund.detail.userId'.trParams({
        'value': item.userId?.toString() ?? 'common.notFilled'.tr,
      }),
      'progress.refund.detail.idempotencyKey'.trParams({
        'value': item.idempotencyKey ?? 'common.notFilled'.tr,
      }),
    ];

    final failure = controller.refundAuditFailure(item);
    if (failure != null) {
      detailLines.add(
        'progress.refund.detail.failure'.trParams({'value': failure}),
      );
    }

    AppDialog.showCustomDialog(
      context: context,
      theme: themeData,
      title: localizeRefundBusinessType(item.businessType),
      content: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: detailLines
                .map(
                  (line) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: SelectableText(
                      line,
                      style: themeData.textTheme.bodyMedium?.copyWith(
                        color: themeData.colorScheme.onSurface,
                      ),
                    ),
                  ),
                )
                .toList(),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text('common.close'.tr),
        ),
      ],
    );
  }

  void _showDateRangePicker(
      ProgressController controller, ThemeData themeData) async {
    final initialStartDate = DateTime.now().subtract(const Duration(days: 7));
    final initialEndDate = DateTime.now();

    final pickedRange = await showDateRangePicker(
      context: Get.context!,
      firstDate: DateTime(2000),
      lastDate: DateTime.now(),
      locale: Get.locale ?? const Locale('en', 'US'),
      initialDateRange: DateTimeRange(
        start: initialStartDate,
        end: initialEndDate,
      ),
      builder: (context, child) {
        return Theme(
          data: themeData.copyWith(
            colorScheme: themeData.colorScheme.copyWith(
              primary: themeData.colorScheme.primary,
              onPrimary: themeData.colorScheme.onPrimary,
              surface: themeData.colorScheme.surface,
            ),
            textButtonTheme: TextButtonThemeData(
              style: TextButton.styleFrom(
                foregroundColor: themeData.colorScheme.primary,
              ),
            ),
          ),
          child: child!,
        );
      },
    );

    if (pickedRange != null) {
      await controller.fetchProgressByTimeRange(
          pickedRange.start, pickedRange.end);
    }
  }

  Color _getStatusColor(String? status, ThemeData themeData) {
    return progressStatusColor(status, themeData);
  }
}
