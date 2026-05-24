// ignore_for_file: use_build_context_synchronously
import 'dart:convert';

import 'package:final_assignment_front/features/dashboard/controllers/progress_controller.dart';
import 'package:final_assignment_front/features/dashboard/controllers/user_dashboard_screen_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/user/widgets/user_page_app_bar.dart';
import 'package:final_assignment_front/i18n/api_error_localizers.dart';
import 'package:final_assignment_front/i18n/status_localizers.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:final_assignment_front/utils/ui/ui_utils.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

String _feedbackHttpError(int statusCode) {
  return 'feedback.error.httpStatus'.trParams({
    'statusCode': '$statusCode',
  });
}

class Feedback {
  final int feedbackId;
  final String username;
  final String feedback;
  final String status;
  final String timestamp;

  Feedback({
    required this.feedbackId,
    required this.username,
    required this.feedback,
    required this.status,
    required this.timestamp,
  });

  factory Feedback.fromJson(Map<String, dynamic> json) {
    return Feedback(
      feedbackId: json['feedbackId'] ?? 0,
      username: json['username'] ?? '',
      feedback: json['feedback'] ?? '',
      status: json['status'] ?? feedbackPendingStatusCode(),
      timestamp: json['timestamp'] ?? DateTime.now().toIso8601String(),
    );
  }

  Map<String, dynamic> toJson() => {
        'feedbackId': feedbackId,
        'username': username,
        'feedback': feedback,
        'status': status,
        'timestamp': timestamp,
      };
}

class ConsultationFeedback extends StatefulWidget {
  const ConsultationFeedback({super.key});

  @override
  State<ConsultationFeedback> createState() => _ConsultationFeedbackState();
}

class _ConsultationFeedbackState extends State<ConsultationFeedback> {
  final TextEditingController _feedbackController = TextEditingController();
  final UserDashboardController _dashboardController =
      Get.find<UserDashboardController>();
  bool _isLoading = false;

  @override
  void dispose() {
    _feedbackController.dispose();
    super.dispose();
  }

  Future<void> _submitFeedback() async {
    final feedbackText = _feedbackController.text.trim();
    if (feedbackText.isEmpty) {
      AppSnackbar.showError(context, message: 'feedback.empty'.tr);
      return;
    }

    setState(() => _isLoading = true);

    try {
      final prefs = await SharedPreferences.getInstance();
      final jwtToken = await AuthTokenStore.instance.getJwtToken();
      final username = prefs.getString('userName');
      if (jwtToken == null || username == null) {
        throw Exception('feedback.error.notLoggedIn'.tr);
      }

      final apiClient = Get.find<ProgressController>().apiClient;
      final feedbackData = Feedback(
        feedbackId: 0,
        username: username,
        feedback: feedbackText,
        status: feedbackPendingStatusCode(),
        timestamp: DateTime.now().toIso8601String(),
      );

      final response = await apiClient.invokeAPI(
        '/api/feedback',
        'POST',
        const [],
        feedbackData.toJson(),
        {
          'Authorization': 'Bearer $jwtToken',
          'Content-Type': 'application/json',
        },
        const {},
        'application/json',
        const [],
      );

      if (response.statusCode == 201) {
        AppDialog.showConfirmDialog(
          context: context,
          title: 'feedback.successTitle',
          message: 'feedback.successMessage',
          confirmText: 'feedback.successConfirm',
        );
        _feedbackController.clear();
      } else {
        throw Exception(_feedbackHttpError(response.statusCode));
      }
    } catch (e) {
      AppSnackbar.showError(
        context,
        message: 'feedback.error.submitFailed'
            .trParams({'error': localizeApiErrorDetail(e)}),
      );
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final themeData = _dashboardController.currentBodyTheme.value;
      return Scaffold(
        backgroundColor: themeData.colorScheme.surface,
        appBar: UserPageAppBar(
          theme: themeData,
          title: 'feedback.title'.tr,
          onThemeToggle: _dashboardController.toggleBodyTheme,
        ),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'feedback.label'.tr,
                style: themeData.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: themeData.colorScheme.onSurface,
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _feedbackController,
                maxLines: 5,
                decoration: InputDecoration(
                  hintText: 'feedback.hint'.tr,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  filled: true,
                  fillColor: themeData.colorScheme.surfaceContainer,
                ),
                style: themeData.textTheme.bodyMedium?.copyWith(
                  color: themeData.colorScheme.onSurface,
                ),
              ),
              const SizedBox(height: 20),
              _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: _submitFeedback,
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 32,
                            vertical: 14,
                          ),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                        child: Text(
                          'feedback.submit'.tr,
                          style: const TextStyle(fontSize: 16),
                        ),
                      ),
                    ),
            ],
          ),
        ),
      );
    });
  }
}

class FeedbackApprovalPage extends StatefulWidget {
  const FeedbackApprovalPage({super.key});

  @override
  State<FeedbackApprovalPage> createState() => _FeedbackApprovalPageState();
}

class _FeedbackApprovalPageState extends State<FeedbackApprovalPage> {
  final List<Feedback> _feedbackRequests = [];
  final UserDashboardController dashboardController =
      Get.find<UserDashboardController>();
  bool _isLoading = true;
  String _errorMessage = '';

  @override
  void initState() {
    super.initState();
    _fetchFeedbackRequests();
  }

  Future<void> _fetchFeedbackRequests() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    try {
      final jwtToken = await AuthTokenStore.instance.getJwtToken();
      if (jwtToken == null) {
        throw Exception('feedback.error.notLoggedIn'.tr);
      }

      final apiClient = Get.find<ProgressController>().apiClient;
      final response = await apiClient.invokeAPI(
        '/api/feedback',
        'GET',
        const [],
        null,
        {
          'Authorization': 'Bearer $jwtToken',
          'Content-Type': 'application/json',
        },
        const {},
        null,
        const [],
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        setState(() {
          _feedbackRequests
            ..clear()
            ..addAll(data.map((json) => Feedback.fromJson(json)));
          _isLoading = false;
        });
      } else {
        throw Exception(_feedbackHttpError(response.statusCode));
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'feedback.error.loadFailed'
            .trParams({'error': localizeApiErrorDetail(e)});
      });
    }
  }

  Future<void> _updateFeedbackRequest(int feedbackId, String status) async {
    setState(() => _isLoading = true);
    try {
      final jwtToken = await AuthTokenStore.instance.getJwtToken();
      if (jwtToken == null) {
        throw Exception('feedback.error.notLoggedIn'.tr);
      }

      final apiClient = Get.find<ProgressController>().apiClient;
      final response = await apiClient.invokeAPI(
        '/api/feedback/$feedbackId',
        'PUT',
        const [],
        {
          'status': status,
          'timestamp': DateTime.now().toIso8601String(),
        },
        {
          'Authorization': 'Bearer $jwtToken',
          'Content-Type': 'application/json',
        },
        const {},
        'application/json',
        const [],
      );

      if (response.statusCode == 200) {
        await _fetchFeedbackRequests();
        AppSnackbar.showSuccess(
          context,
          message: 'feedback.approvalUpdated'.trParams(
            {'status': localizeFeedbackStatus(status)},
          ),
        );
      } else {
        throw Exception(_feedbackHttpError(response.statusCode));
      }
    } catch (e) {
      AppSnackbar.showError(
        context,
        message: 'feedback.error.updateFailed'
            .trParams({'error': localizeApiErrorDetail(e)}),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
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
          title: 'feedback.approvalTitle'.tr,
          onThemeToggle: dashboardController.toggleBodyTheme,
          onRefresh: _fetchFeedbackRequests,
        ),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: _isLoading
              ? const Center(child: CircularProgressIndicator())
              : _errorMessage.isNotEmpty
                  ? Center(
                      child: Text(
                        _errorMessage,
                        style: themeData.textTheme.bodyLarge?.copyWith(
                          color: themeData.colorScheme.error,
                        ),
                      ),
                    )
                  : _feedbackRequests.isEmpty
                      ? Center(
                          child: Text(
                            'feedback.approvalEmpty'.tr,
                            style: themeData.textTheme.bodyLarge?.copyWith(
                              color: themeData.colorScheme.onSurfaceVariant,
                            ),
                          ),
                        )
                      : ListView.builder(
                          itemCount: _feedbackRequests.length,
                          itemBuilder: (context, index) {
                            final feedback = _feedbackRequests[index];
                            return Card(
                              elevation: 3,
                              color: themeData.colorScheme.surfaceContainer,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: ListTile(
                                title: Text(
                                  'feedback.approvalUser'.trParams(
                                    {'user': feedback.username},
                                  ),
                                  style:
                                      themeData.textTheme.titleMedium?.copyWith(
                                    color: themeData.colorScheme.onSurface,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                subtitle: Text(
                                  'feedback.approvalDetail'.trParams({
                                    'feedback': feedback.feedback,
                                    'status':
                                        localizeFeedbackStatus(feedback.status),
                                  }),
                                  style:
                                      themeData.textTheme.bodyMedium?.copyWith(
                                    color:
                                        themeData.colorScheme.onSurfaceVariant,
                                  ),
                                ),
                                trailing: isPendingFeedbackStatus(
                                  feedback.status,
                                )
                                    ? Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          IconButton(
                                            icon: Icon(
                                              Icons.check,
                                              color:
                                                  themeData.colorScheme.primary,
                                            ),
                                            onPressed: () {
                                              if (feedback.feedbackId != 0) {
                                                _updateFeedbackRequest(
                                                  feedback.feedbackId,
                                                  feedbackApprovedStatusCode(),
                                                );
                                              } else {
                                                AppSnackbar.showError(
                                                  context,
                                                  message:
                                                      'feedback.approvalInvalidId'
                                                          .tr,
                                                );
                                              }
                                            },
                                            tooltip:
                                                'feedback.approvalApprove'.tr,
                                          ),
                                          IconButton(
                                            icon: Icon(
                                              Icons.close,
                                              color:
                                                  themeData.colorScheme.error,
                                            ),
                                            onPressed: () {
                                              if (feedback.feedbackId != 0) {
                                                _updateFeedbackRequest(
                                                  feedback.feedbackId,
                                                  feedbackRejectedStatusCode(),
                                                );
                                              } else {
                                                AppSnackbar.showError(
                                                  context,
                                                  message:
                                                      'feedback.approvalInvalidId'
                                                          .tr,
                                                );
                                              }
                                            },
                                            tooltip:
                                                'feedback.approvalReject'.tr,
                                          ),
                                        ],
                                      )
                                    : null,
                              ),
                            );
                          },
                        ),
        ),
      );
    });
  }
}
