import 'package:final_assignment_front/features/dashboard/controllers/user_dashboard_screen_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/user/widgets/user_page_app_bar.dart';
import 'package:final_assignment_front/features/model/fine_information.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/i18n/status_localizers.dart';
import 'package:final_assignment_front/utils/ui/ui_utils.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:qr_flutter/qr_flutter.dart';

class MainScan extends StatefulWidget {
  final FineInformation? fine;

  const MainScan({super.key, this.fine});

  @override
  State<MainScan> createState() => _MainScanState();
}

class _MainScanState extends State<MainScan> {
  final UserDashboardController dashboardController =
      Get.find<UserDashboardController>();

  bool _isGenerating = false;
  String? _lastGeneratedData;

  String _buildQrData(FineInformation fine) {
    return [
      '${'scan.field.fineId'.tr}: ${fine.fineId ?? 'common.none'.tr}',
      '${'scan.field.fineAmount'.tr}: ${'fine.value.amount'.trParams({
            'value': '${fine.fineAmount ?? 0}'
          })}',
      '${'scan.field.payee'.tr}: ${fine.payee ?? 'common.notFilled'.tr}',
    ].join('\n');
  }

  @override
  void initState() {
    super.initState();
    if (widget.fine != null) {
      _generateCode();
    }
  }

  Future<void> _generateCode() async {
    if (_isGenerating) return;
    final qrData =
        widget.fine != null ? _buildQrData(widget.fine!) : 'app.name'.tr;

    setState(() {
      _isGenerating = true;
    });

    try {
      final qrWidget = QrImageView(
        data: qrData,
        version: QrVersions.auto,
        size: 280,
        backgroundColor: Colors.white,
        eyeStyle: QrEyeStyle(
          color: dashboardController.currentBodyTheme.value.colorScheme.primary,
        ),
        dataModuleStyle: QrDataModuleStyle(
          color: dashboardController.currentBodyTheme.value.colorScheme.primary,
        ),
        embeddedImage: const AssetImage('assets/images/ic_logo.jpg'),
        embeddedImageStyle: const QrEmbeddedImageStyle(size: Size(48, 48)),
      );

      if (!mounted) return;
      setState(() {
        _lastGeneratedData = qrData;
        _isGenerating = false;
      });

      AppDialog.showCustomDialog(
        context: context,
        title: widget.fine != null
            ? 'scan.dialog.fineQr'.tr
            : 'scan.dialog.genericQr'.tr,
        content: SizedBox(width: 280, height: 280, child: qrWidget),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text('common.close'.tr),
          ),
        ],
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _isGenerating = false);
      AppSnackbar.showError(
        context,
        message: 'scan.error.generateFailed'
            .trParams({'error': localizeApiErrorDetail(e)}),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final themeData = dashboardController.currentBodyTheme.value;
      return Scaffold(
        backgroundColor: themeData.colorScheme.surface,
        appBar: UserPageAppBar(
          theme: themeData,
          title: 'scan.pageTitle'.tr,
          onThemeToggle: dashboardController.toggleBodyTheme,
        ),
        body: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (widget.fine != null) _buildFineCard(themeData, widget.fine!),
              const SizedBox(height: 16),
              _buildQrPreview(themeData),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: _isGenerating ? null : _generateCode,
                icon: const Icon(Icons.qr_code),
                label: Text(
                  _lastGeneratedData == null
                      ? 'scan.action.generate'.tr
                      : 'scan.action.regenerate'.tr,
                ),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
            ],
          ),
        ),
      );
    });
  }

  Widget _buildFineCard(ThemeData theme, FineInformation fine) {
    return Card(
      elevation: 3,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      color: theme.colorScheme.surfaceContainer,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'scan.fineDetail.title'.tr,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: theme.colorScheme.onSurface,
              ),
            ),
            const Divider(),
            _buildDetailRow(theme, 'scan.field.fineId'.tr,
                fine.fineId?.toString() ?? 'common.none'.tr),
            _buildDetailRow(
              theme,
              'scan.field.fineAmount'.tr,
              'fine.value.amount'
                  .trParams({'value': '${fine.fineAmount ?? 0}'}),
            ),
            _buildDetailRow(theme, 'scan.field.payee'.tr,
                fine.payee ?? 'common.notFilled'.tr),
            _buildDetailRow(
              theme,
              'scan.field.paymentStatus'.tr,
              localizePaymentStatus(fine.paymentStatus),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQrPreview(ThemeData theme) {
    final colorScheme = theme.colorScheme;
    final qrText = _lastGeneratedData ?? 'scan.status.notGenerated'.tr;
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      color: colorScheme.surfaceContainer,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Text(
              _lastGeneratedData != null
                  ? 'scan.status.generated'.tr
                  : 'scan.status.waiting'.tr,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: colorScheme.onSurface,
              ),
            ),
            const SizedBox(height: 12),
            if (_lastGeneratedData == null)
              Text(
                qrText,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
                textAlign: TextAlign.center,
              ),
            if (_lastGeneratedData != null)
              Container(
                constraints:
                    const BoxConstraints(maxWidth: 260, maxHeight: 260),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  border: Border.all(
                      color: colorScheme.primary.withValues(alpha: 0.2)),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: QrImageView(
                  data: _lastGeneratedData!,
                  version: QrVersions.auto,
                  size: 240,
                  backgroundColor: Colors.white,
                  eyeStyle: QrEyeStyle(color: colorScheme.primary),
                  dataModuleStyle:
                      QrDataModuleStyle(color: colorScheme.primary),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildDetailRow(ThemeData theme, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          Text(
            value,
            style: theme.textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
