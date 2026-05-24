// ignore_for_file: use_build_context_synchronously
import 'dart:convert';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:final_assignment_front/features/model/appeal_record.dart';
import 'package:final_assignment_front/features/api/appeal_management_controller_api.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/components/progress_detail.dart';
import 'package:final_assignment_front/features/api/driver_information_controller_api.dart';
import 'package:final_assignment_front/features/api/offense_information_controller_api.dart';
import 'package:final_assignment_front/features/api/user_management_controller_api.dart';
import 'package:final_assignment_front/features/model/driver_information.dart';
import 'package:final_assignment_front/features/model/offense_information.dart';
import 'package:final_assignment_front/features/model/progress_item.dart';
import 'package:final_assignment_front/features/model/user_management.dart';
import 'package:final_assignment_front/i18n/appeal_localizers.dart';
import 'package:final_assignment_front/i18n/progress_localizers.dart';
import 'package:final_assignment_front/i18n/status_localizers.dart';
import 'package:final_assignment_front/utils/helpers/role_utils.dart';
import 'package:final_assignment_front/utils/services/api_client.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:get/get.dart';
import 'package:final_assignment_front/features/dashboard/controllers/user_dashboard_screen_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/dashboard_page_template.dart';
import 'dart:developer' as developer;

String generateIdempotencyKey() {
  return DateTime.now().millisecondsSinceEpoch.toString();
}

class UserAppealPage extends StatefulWidget {
  const UserAppealPage({super.key});

  @override
  State<UserAppealPage> createState() => _UserAppealPageState();
}

class _UserAppealPageState extends State<UserAppealPage> {
  static const int _pageSize = 100;

  late AppealManagementControllerApi appealApi;
  late DriverInformationControllerApi driverApi;
  final OffenseInformationControllerApi offenseApi =
      OffenseInformationControllerApi();
  final UserManagementControllerApi userApi = UserManagementControllerApi();
  final TextEditingController _searchController = TextEditingController();
  List<AppealRecordModel> _appeals = [];
  bool _isLoading = true;
  bool _isUser = false;
  String _errorMessage = '';
  late ScrollController _scrollController;
  List<OffenseInformation> _offenseCache = [];
  String? _currentDriverName;

  DateTime? _startTime;
  DateTime? _endTime;

  final UserDashboardController? controller =
      Get.isRegistered<UserDashboardController>()
          ? Get.find<UserDashboardController>()
          : null;

  @override
  void initState() {
    super.initState();
    appealApi = AppealManagementControllerApi();
    driverApi = DriverInformationControllerApi();
    _scrollController = ScrollController();
    _loadAppealsAndCheckRole();
  }

  @override
  void dispose() {
    _searchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadAppealsAndCheckRole() async {
    setState(() => _isLoading = true);
    try {
      final prefs = await SharedPreferences.getInstance();
      final jwtToken = await AuthTokenStore.instance.getJwtToken();
      if (jwtToken == null) {
        throw Exception('appeal.error.notLoggedIn'.tr);
      }
      await appealApi.initializeWithJwt();
      await driverApi.initializeWithJwt();
      await offenseApi.initializeWithJwt();
      await userApi.initializeWithJwt();

      _currentDriverName = await _fetchDriverName();
      if (_currentDriverName != null && _currentDriverName!.isNotEmpty) {
        await prefs.setString('driverName', _currentDriverName!);
        await prefs.setString('displayName', _currentDriverName!);
        developer.log('Fetched and stored driver name: $_currentDriverName');
      } else {
        _currentDriverName = prefs.getString('driverName') ??
            prefs.getString('displayName') ??
            prefs.getString('userName');
      }
      developer.log('Current Driver Name: $_currentDriverName');

      final decodedJwt = _decodeJwt(jwtToken);
      _isUser = hasAnyRole(decodedJwt['roles'], const ['USER']);
      if (!_isUser) {
        throw Exception('appeal.error.userOnly'.tr);
      }

      await _checkUserOffenses();
      await _fetchUserAppeals();
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'appeal.error.loadFailed'
            .trParams({'error': formatUserAppealError(e)});
      });
    }
  }

  Map<String, dynamic> _decodeJwt(String token) {
    try {
      final parts = token.split('.');
      if (parts.length != 3) throw Exception('appeal.error.invalidJwt'.tr);
      final payload = base64Url.decode(base64Url.normalize(parts[1]));
      return jsonDecode(utf8.decode(payload)) as Map<String, dynamic>;
    } catch (e) {
      developer.log('JWT decode error: $e');
      return {};
    }
  }

  Future<String?> _fetchDriverName() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final userData = await userApi.apiUsersMeGet();
      final driverInfo = await driverApi.apiDriversMeGet();
      final driverName = driverInfo?.name ??
          prefs.getString('displayName') ??
          prefs.getString('driverName') ??
          userData?.realName ??
          userData?.username;
      developer.log('Driver name from API: $driverName');
      return driverName;
    } catch (e) {
      developer.log('Error fetching driver name: $e');
      return null;
    }
  }

  Future<void> _checkUserOffenses() async {
    try {
      final offenses = await _fetchAllUserOffenses();
      developer.log('Fetched offenses: ${offenses.length}');
      setState(() {
        _offenseCache = offenses;
      });
    } catch (e) {
      developer.log('Error checking user offenses: $e');
      setState(() {
        _errorMessage = 'appeal.error.checkOffenseFailed'
            .trParams({'error': formatUserAppealError(e)});
      });
    }
  }

  Future<List<OffenseInformation>> _fetchUserOffenses() async {
    try {
      if (_offenseCache.isNotEmpty) {
        return _offenseCache;
      }
      _offenseCache = await _fetchAllUserOffenses();
      developer.log('Fetched offenses for dialog: $_offenseCache');
      return _offenseCache;
    } catch (e) {
      developer.log('Error fetching user offenses: $e');
      return const [];
    }
  }

  Future<UserManagement?> _fetchUserManagement() async {
    try {
      return await userApi.apiUsersMeGet();
    } catch (e) {
      developer.log('Failed to fetch user info: $e');
      return null;
    }
  }

  Future<DriverInformation?> _fetchDriverInformation() async {
    try {
      return await driverApi.apiDriversMeGet();
    } catch (e) {
      developer.log('Failed to fetch driver info: $e');
      return null;
    }
  }

  Future<void> _fetchUserAppeals({bool resetFilters = false}) async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });
    try {
      if (resetFilters) {
        _startTime = null;
        _endTime = null;
        _searchController.clear();
      }

      final offenseIds =
          _offenseCache.map((o) => o.offenseId).whereType<int>().toSet();
      if (offenseIds.isEmpty) {
        setState(() {
          _appeals = [];
          _isLoading = false;
          _errorMessage = 'appeal.empty'.tr;
        });
        return;
      }
      final fetched = await _fetchAllUserAppeals();

      final searchText = _searchController.text.trim().toLowerCase();
      final filtered = fetched.where((appeal) {
        final matchesOffense =
            appeal.offenseId != null && offenseIds.contains(appeal.offenseId);
        final matchesSearch = searchText.isEmpty
            ? true
            : (appeal.appealReason ?? '').toLowerCase().contains(searchText);
        bool matchesRange = true;
        if (_startTime != null && _endTime != null) {
          final time = appeal.appealTime;
          matchesRange = time != null &&
              !time.isBefore(_startTime!) &&
              !time.isAfter(_endTime!);
        }
        return matchesOffense && matchesSearch && matchesRange;
      }).toList();

      setState(() {
        _appeals = filtered;
        _isLoading = false;
        if (_appeals.isEmpty) {
          _errorMessage = _searchController.text.isNotEmpty ||
                  (_startTime != null && _endTime != null)
              ? 'appeal.empty.filtered'.tr
              : 'appeal.empty'.tr;
        }
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'appeal.error.loadRecordsFailed'
            .trParams({'error': formatUserAppealError(e)});
      });
    }
  }

  Future<List<OffenseInformation>> _fetchAllUserOffenses() async {
    final offenses = <OffenseInformation>[];
    var page = 1;
    while (true) {
      final pageItems = await offenseApi.apiOffensesMeGet(
        page: page,
        size: _pageSize,
      );
      offenses.addAll(pageItems);
      if (pageItems.length < _pageSize) {
        break;
      }
      page++;
    }
    return offenses;
  }

  Future<List<AppealRecordModel>> _fetchAllUserAppeals() async {
    final appeals = <AppealRecordModel>[];
    var page = 1;
    while (true) {
      final pageItems = await appealApi.apiAppealsMeGet(
        page: page,
        size: _pageSize,
      );
      appeals.addAll(pageItems);
      if (pageItems.length < _pageSize) {
        break;
      }
      page++;
    }
    return appeals;
  }

  Future<List<String>> _fetchAutocompleteSuggestions(String prefix) async {
    final lowerPrefix = prefix.toLowerCase();
    return _appeals
        .map((appeal) => appeal.appealReason ?? '')
        .where((reason) => reason.toLowerCase().contains(lowerPrefix))
        .toList();
  }

  String _resolveDisplayStatus(AppealRecordModel appeal) {
    final acceptance = normalizeAppealStatusCode(appeal.acceptanceStatus);
    if (acceptance == appealPendingStatusCode() ||
        acceptance == appealRejectedStatusCode() ||
        acceptance == 'Need_Supplement') {
      return localizeAppealStatus(appeal.acceptanceStatus);
    }
    return localizeAppealStatus(appeal.processStatus);
  }

  Future<void> _submitAppeal(
      AppealRecordModel appeal, String idempotencyKey) async {
    try {
      developer.log('Submitting appeal with idempotencyKey: $idempotencyKey');
      await appealApi.apiAppealsMePost(
          appealRecord: appeal, idempotencyKey: idempotencyKey);
      developer.log('Appeal submitted successfully: ${appeal.toJson()}');
      _showSnackBar('appeal.success.submitted'.tr);
      await _fetchUserAppeals();
    } catch (e) {
      developer.log('Appeal submission failed: $e');
      _showSnackBar(
        'appeal.error.submitFailed'
            .trParams({'error': formatUserAppealError(e)}),
        isError: true,
      );
    }
  }

  String? _normalizeOptionalAppealText(String value) {
    final trimmed = value.trim();
    return trimmed.isEmpty ? null : trimmed;
  }

  void _showSubmitAppealDialog() async {
    final user = await _fetchUserManagement();
    final driverInfo = await _fetchDriverInformation();
    final profileName = (driverInfo?.name ??
            _currentDriverName ??
            user?.realName ??
            user?.username ??
            '')
        .trim();
    final profileIdCard =
        (driverInfo?.idCardNumber ?? user?.idCardNumber ?? '').trim();
    final profileContact =
        (driverInfo?.contactNumber ?? user?.contactNumber ?? '').trim();

    if (profileName.isEmpty ||
        profileIdCard.isEmpty ||
        profileContact.isEmpty) {
      _showSnackBar(
        'appeal.error.completeProfileBeforeSubmit'.tr,
        isError: true,
      );
      return;
    }

    final TextEditingController reasonController = TextEditingController();
    final TextEditingController evidenceDescriptionController =
        TextEditingController();
    final TextEditingController evidenceUrlsController =
        TextEditingController();
    final formKey = GlobalKey<FormState>();
    int? selectedOffenseId;
    bool isSubmitting = false;
    AutovalidateMode autovalidateMode = AutovalidateMode.disabled;

    final offenses = await _fetchUserOffenses();
    if (offenses.isEmpty) {
      _showSnackBar('appeal.error.noOffenseToSubmit'.tr, isError: true);
      return;
    }

    showDialog(
      context: context,
      builder: (ctx) => Obx(() {
        final themeData =
            controller?.currentBodyTheme.value ?? Theme.of(context);
        return StatefulBuilder(
          builder: (context, dialogSetState) => Dialog(
            backgroundColor: themeData.colorScheme.surfaceContainer,
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16.0)),
            child: ConstrainedBox(
              constraints:
                  const BoxConstraints(maxWidth: 300.0, minHeight: 200.0),
              child: Padding(
                padding: const EdgeInsets.all(12.0),
                child: Form(
                  key: formKey,
                  autovalidateMode: autovalidateMode,
                  child: SingleChildScrollView(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text(
                          'appeal.dialog.submitTitle'.tr,
                          style: themeData.textTheme.titleMedium?.copyWith(
                            color: themeData.colorScheme.onSurface,
                            fontWeight: FontWeight.bold,
                          ),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 12.0),
                        DropdownButtonFormField<int>(
                          initialValue: selectedOffenseId,
                          decoration: InputDecoration(
                            labelText: 'appeal.form.offense'.tr,
                            labelStyle: TextStyle(
                                color: themeData.colorScheme.onSurfaceVariant),
                            filled: true,
                            fillColor:
                                themeData.colorScheme.surfaceContainerLowest,
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8.0),
                              borderSide: BorderSide(
                                  color: themeData.colorScheme.outline
                                      .withValues(alpha: 0.3)),
                            ),
                          ),
                          items: offenses.map((offense) {
                            return DropdownMenuItem<int>(
                              value: offense.offenseId,
                              child: Text('appeal.form.offenseOption'.trParams({
                                'id': '${offense.offenseId}',
                                'type': offense.offenseType ??
                                    'appeal.value.noDescription'.tr,
                              })),
                            );
                          }).toList(),
                          onChanged: (value) {
                            dialogSetState(() => selectedOffenseId = value);
                          },
                          validator: (value) => value == null
                              ? 'appeal.validation.offenseRequired'.tr
                              : null,
                        ),
                        const SizedBox(height: 12.0),
                        TextFormField(
                          initialValue: profileName,
                          readOnly: true,
                          decoration: InputDecoration(
                            labelText: 'appeal.form.appellantName'.tr,
                            labelStyle: TextStyle(
                                color: themeData.colorScheme.onSurfaceVariant),
                            filled: true,
                            fillColor: themeData
                                .colorScheme.surfaceContainerHighest
                                .withValues(alpha: 0.5),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8.0),
                              borderSide: BorderSide(
                                  color: themeData.colorScheme.outline
                                      .withValues(alpha: 0.3)),
                            ),
                            helperText: 'appeal.form.identityFromProfile'.tr,
                            suffixIcon: Icon(Icons.lock,
                                size: 18, color: themeData.colorScheme.primary),
                          ),
                          style:
                              TextStyle(color: themeData.colorScheme.onSurface),
                        ),
                        const SizedBox(height: 12.0),
                        TextFormField(
                          initialValue: profileIdCard,
                          readOnly: true,
                          decoration: InputDecoration(
                            labelText: 'appeal.form.idCard'.tr,
                            labelStyle: TextStyle(
                                color: themeData.colorScheme.onSurfaceVariant),
                            filled: true,
                            fillColor: themeData
                                .colorScheme.surfaceContainerHighest
                                .withValues(alpha: 0.5),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8.0),
                              borderSide: BorderSide(
                                  color: themeData.colorScheme.outline
                                      .withValues(alpha: 0.3)),
                            ),
                            suffixIcon: Icon(Icons.lock,
                                size: 18, color: themeData.colorScheme.primary),
                          ),
                          style:
                              TextStyle(color: themeData.colorScheme.onSurface),
                        ),
                        const SizedBox(height: 12.0),
                        TextFormField(
                          initialValue: profileContact,
                          readOnly: true,
                          decoration: InputDecoration(
                            labelText: 'appeal.form.contact'.tr,
                            labelStyle: TextStyle(
                                color: themeData.colorScheme.onSurfaceVariant),
                            filled: true,
                            fillColor: themeData
                                .colorScheme.surfaceContainerHighest
                                .withValues(alpha: 0.5),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8.0),
                              borderSide: BorderSide(
                                  color: themeData.colorScheme.outline
                                      .withValues(alpha: 0.3)),
                            ),
                            suffixIcon: Icon(Icons.lock,
                                size: 18, color: themeData.colorScheme.primary),
                          ),
                          style:
                              TextStyle(color: themeData.colorScheme.onSurface),
                        ),
                        const SizedBox(height: 12.0),
                        TextFormField(
                          controller: reasonController,
                          decoration: InputDecoration(
                            labelText: 'appeal.form.reason'.tr,
                            labelStyle: TextStyle(
                                color: themeData.colorScheme.onSurfaceVariant),
                            filled: true,
                            fillColor:
                                themeData.colorScheme.surfaceContainerLowest,
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8.0),
                              borderSide: BorderSide(
                                  color: themeData.colorScheme.outline
                                      .withValues(alpha: 0.3)),
                            ),
                          ),
                          maxLength: 500,
                          maxLines: 3,
                          validator: (value) =>
                              validateAppealReasonField(value, required: true),
                          style:
                              TextStyle(color: themeData.colorScheme.onSurface),
                        ),
                        const SizedBox(height: 12.0),
                        TextFormField(
                          controller: evidenceDescriptionController,
                          decoration: InputDecoration(
                            labelText:
                                'appeal.form.initialEvidenceDescription'.tr,
                            labelStyle: TextStyle(
                                color: themeData.colorScheme.onSurfaceVariant),
                            filled: true,
                            fillColor:
                                themeData.colorScheme.surfaceContainerLowest,
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8.0),
                              borderSide: BorderSide(
                                  color: themeData.colorScheme.outline
                                      .withValues(alpha: 0.3)),
                            ),
                          ),
                          maxLength: 500,
                          maxLines: 3,
                          style:
                              TextStyle(color: themeData.colorScheme.onSurface),
                        ),
                        const SizedBox(height: 12.0),
                        TextFormField(
                          controller: evidenceUrlsController,
                          decoration: InputDecoration(
                            labelText: 'appeal.form.initialEvidenceUrls'.tr,
                            hintText: 'appeal.form.evidenceUrlsHint'.tr,
                            labelStyle: TextStyle(
                                color: themeData.colorScheme.onSurfaceVariant),
                            filled: true,
                            fillColor:
                                themeData.colorScheme.surfaceContainerLowest,
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8.0),
                              borderSide: BorderSide(
                                  color: themeData.colorScheme.outline
                                      .withValues(alpha: 0.3)),
                            ),
                          ),
                          maxLength: 1000,
                          maxLines: 3,
                          style:
                              TextStyle(color: themeData.colorScheme.onSurface),
                        ),
                        const SizedBox(height: 16.0),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                          children: [
                            TextButton(
                              onPressed: () => Navigator.pop(ctx),
                              child: Text(
                                'common.cancel'.tr,
                                style:
                                    themeData.textTheme.labelMedium?.copyWith(
                                  color: themeData.colorScheme.onSurface,
                                ),
                              ),
                            ),
                            ElevatedButton(
                              onPressed: isSubmitting
                                  ? null
                                  : () async {
                                      final currentForm = formKey.currentState;
                                      final isValid =
                                          currentForm?.validate() ?? false;
                                      if (!isValid) {
                                        dialogSetState(() {
                                          autovalidateMode = AutovalidateMode
                                              .onUserInteraction;
                                        });
                                        return;
                                      }

                                      dialogSetState(() => isSubmitting = true);
                                      final newAppeal = AppealRecordModel(
                                        offenseId: selectedOffenseId,
                                        appealReason:
                                            reasonController.text.trim(),
                                        evidenceDescription:
                                            _normalizeOptionalAppealText(
                                          evidenceDescriptionController.text,
                                        ),
                                        evidenceUrls:
                                            _normalizeOptionalAppealText(
                                          evidenceUrlsController.text,
                                        ),
                                        appealTime: DateTime.now(),
                                      );
                                      final idempotencyKey =
                                          generateIdempotencyKey();
                                      developer.log(
                                          'Preparing to submit appeal with key: $idempotencyKey');
                                      await _submitAppeal(
                                          newAppeal, idempotencyKey);
                                      dialogSetState(
                                          () => isSubmitting = false);
                                      if (mounted) Navigator.pop(ctx);
                                    },
                              style:
                                  themeData.elevatedButtonTheme.style?.copyWith(
                                backgroundColor: WidgetStateProperty.all(
                                    themeData.colorScheme.primary),
                                foregroundColor: WidgetStateProperty.all(
                                    themeData.colorScheme.onPrimary),
                              ),
                              child: isSubmitting
                                  ? const SizedBox(
                                      width: 20,
                                      height: 20,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        valueColor:
                                            AlwaysStoppedAnimation<Color>(
                                                Colors.white),
                                      ),
                                    )
                                  : Text('common.submit'.tr),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        );
      }),
    ).whenComplete(() {
      reasonController.dispose();
      evidenceDescriptionController.dispose();
      evidenceUrlsController.dispose();
    });
  }

  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message, style: const TextStyle(color: Colors.white)),
        backgroundColor: isError ? Colors.red : Colors.green,
      ),
    );
  }

  Widget _buildSearchBar(ThemeData themeData) {
    return Card(
      elevation: 2,
      color: themeData.colorScheme.surfaceContainer,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12.0)),
      child: Padding(
        padding: const EdgeInsets.all(8.0),
        child: Column(
          children: [
            Row(
              children: [
                Expanded(
                  child: Autocomplete<String>(
                    optionsBuilder: (TextEditingValue textEditingValue) async {
                      if (textEditingValue.text.isEmpty) {
                        return const Iterable<String>.empty();
                      }
                      return await _fetchAutocompleteSuggestions(
                          textEditingValue.text);
                    },
                    onSelected: (String selection) {
                      _searchController.text = selection;
                      _fetchUserAppeals();
                    },
                    fieldViewBuilder:
                        (context, controller, focusNode, onFieldSubmitted) {
                      _searchController.text = controller.text;
                      return TextField(
                        controller: controller,
                        focusNode: focusNode,
                        style:
                            TextStyle(color: themeData.colorScheme.onSurface),
                        decoration: InputDecoration(
                          hintText: 'appeal.search.hint'.tr,
                          hintStyle: TextStyle(
                              color: themeData.colorScheme.onSurface
                                  .withValues(alpha: 0.6)),
                          prefixIcon: Icon(Icons.search,
                              color: themeData.colorScheme.primary),
                          suffixIcon: controller.text.isNotEmpty
                              ? IconButton(
                                  icon: Icon(Icons.clear,
                                      color: themeData
                                          .colorScheme.onSurfaceVariant),
                                  onPressed: () {
                                    controller.clear();
                                    _searchController.clear();
                                    _fetchUserAppeals(resetFilters: true);
                                  },
                                )
                              : null,
                          border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8.0)),
                          enabledBorder: OutlineInputBorder(
                            borderSide: BorderSide(
                                color: themeData.colorScheme.outline
                                    .withValues(alpha: 0.3)),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderSide: BorderSide(
                                color: themeData.colorScheme.primary,
                                width: 1.5),
                          ),
                          filled: true,
                          fillColor:
                              themeData.colorScheme.surfaceContainerLowest,
                          contentPadding: const EdgeInsets.symmetric(
                              vertical: 12.0, horizontal: 16.0),
                        ),
                        onChanged: (value) {
                          if (value.isEmpty) {
                            _fetchUserAppeals(resetFilters: true);
                          }
                        },
                        onSubmitted: (value) => _fetchUserAppeals(),
                      );
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: Text(
                    _startTime != null && _endTime != null
                        ? 'appeal.filter.rangeLabel'.trParams({
                            'start': formatAppealDateTime(_startTime),
                            'end': formatAppealDateTime(_endTime),
                          })
                        : 'appeal.filter.select'.tr,
                    style: TextStyle(
                      color: _startTime != null && _endTime != null
                          ? themeData.colorScheme.onSurface
                          : themeData.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ),
                IconButton(
                  icon: Icon(Icons.date_range,
                      color: themeData.colorScheme.primary),
                  tooltip: 'appeal.filter.tooltip'.tr,
                  onPressed: () async {
                    final range = await showDateRangePicker(
                      context: context,
                      firstDate: DateTime(2000),
                      lastDate: DateTime.now(),
                      locale: Get.locale ?? const Locale('en', 'US'),
                      helpText: 'appeal.filter.select'.tr,
                      cancelText: 'common.cancel'.tr,
                      confirmText: 'common.confirm'.tr,
                      fieldStartHintText: 'appeal.filter.startDate'.tr,
                      fieldEndHintText: 'appeal.filter.endDate'.tr,
                      builder: (BuildContext context, Widget? child) {
                        return Theme(
                          data: Theme.of(context),
                          child: child!,
                        );
                      },
                    );
                    if (range != null) {
                      setState(() {
                        _startTime = range.start;
                        _endTime = range.end;
                      });
                      _fetchUserAppeals();
                    }
                  },
                ),
                if (_startTime != null && _endTime != null)
                  IconButton(
                    icon: Icon(Icons.clear,
                        color: themeData.colorScheme.onSurfaceVariant),
                    tooltip: 'appeal.filter.clear'.tr,
                    onPressed: () {
                      setState(() {
                        _startTime = null;
                        _endTime = null;
                      });
                      _fetchUserAppeals();
                    },
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final themeData = controller?.currentBodyTheme.value ?? Theme.of(context);
      if (!_isUser) {
        return DashboardPageTemplate(
          theme: themeData,
          title: 'appeal.page.title'.tr,
          pageType: DashboardPageType.custom,
          body: Center(
            child: Text(
              _errorMessage,
              style: themeData.textTheme.bodyLarge?.copyWith(
                color: themeData.colorScheme.error,
              ),
            ),
          ),
        );
      }

      return DashboardPageTemplate(
        theme: themeData,
        title: 'appeal.page.title'.tr,
        pageType: DashboardPageType.user,
        onThemeToggle: controller?.toggleBodyTheme,
        bodyIsScrollable: true,
        padding: EdgeInsets.zero,
        floatingActionButton: FloatingActionButton(
          onPressed: _showSubmitAppealDialog,
          backgroundColor: themeData.colorScheme.primary,
          foregroundColor: themeData.colorScheme.onPrimary,
          tooltip: 'appeal.action.submit'.tr,
          child: const Icon(Icons.add),
        ),
        body: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            children: [
              _buildSearchBar(themeData),
              const SizedBox(height: 16),
              Expanded(
                child: _isLoading
                    ? Center(
                        child: CircularProgressIndicator(
                          valueColor: AlwaysStoppedAnimation<Color>(
                              themeData.colorScheme.primary),
                        ),
                      )
                    : _errorMessage.isNotEmpty
                        ? Center(
                            child: Text(
                              _errorMessage,
                              style: themeData.textTheme.bodyLarge?.copyWith(
                                color: themeData.colorScheme.error,
                              ),
                            ),
                          )
                        : _appeals.isEmpty
                            ? Center(
                                child: Text(
                                  _currentDriverName != null
                                      ? 'appeal.empty.byAppellant'.trParams({
                                          'name': _currentDriverName!,
                                        })
                                      : 'appeal.error.driverNameMissingRelogin'
                                          .tr,
                                  style:
                                      themeData.textTheme.bodyLarge?.copyWith(
                                    color:
                                        themeData.colorScheme.onSurfaceVariant,
                                  ),
                                ),
                              )
                            : CupertinoScrollbar(
                                controller: _scrollController,
                                thumbVisibility: true,
                                child: RefreshIndicator(
                                  onRefresh: () => _fetchUserAppeals(),
                                  color: themeData.colorScheme.primary,
                                  child: ListView.builder(
                                    controller: _scrollController,
                                    itemCount: _appeals.length,
                                    itemBuilder: (context, index) {
                                      final appeal = _appeals[index];
                                      return Card(
                                        elevation: 3,
                                        color: themeData
                                            .colorScheme.surfaceContainer,
                                        shape: RoundedRectangleBorder(
                                            borderRadius:
                                                BorderRadius.circular(12.0)),
                                        margin: const EdgeInsets.symmetric(
                                            vertical: 6.0),
                                        child: ListTile(
                                          title: Text(
                                            'appeal.card.title'.trParams({
                                              'name': appeal.appellantName ??
                                                  'common.unknown'.tr,
                                              'id':
                                                  '${appeal.appealId ?? 'common.none'.tr}',
                                            }),
                                            style: themeData.textTheme.bodyLarge
                                                ?.copyWith(
                                              color: themeData
                                                  .colorScheme.onSurface,
                                              fontWeight: FontWeight.w600,
                                            ),
                                          ),
                                          subtitle: Text(
                                            'appeal.card.summary'.trParams({
                                              'reason': appeal.appealReason ??
                                                  'common.none'.tr,
                                              'status':
                                                  _resolveDisplayStatus(appeal),
                                              'time': formatAppealDateTime(
                                                appeal.appealTime,
                                              ),
                                            }),
                                            style: themeData
                                                .textTheme.bodyMedium
                                                ?.copyWith(
                                              color: themeData
                                                  .colorScheme.onSurfaceVariant,
                                            ),
                                          ),
                                          onTap: () {
                                            Navigator.push<bool>(
                                              context,
                                              MaterialPageRoute(
                                                builder: (context) =>
                                                    UserAppealDetailPage(
                                                        appeal: appeal),
                                              ),
                                            ).then((_) {
                                              _fetchUserAppeals();
                                            });
                                          },
                                        ),
                                      );
                                    },
                                  ),
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

class UserAppealDetailPage extends StatefulWidget {
  final AppealRecordModel appeal;

  const UserAppealDetailPage({super.key, required this.appeal});

  @override
  State<UserAppealDetailPage> createState() => _UserAppealDetailPageState();
}

class _UserAppealDetailPageState extends State<UserAppealDetailPage> {
  static const int _relatedProgressPageSize = 100;

  final AppealManagementControllerApi _appealApi =
      AppealManagementControllerApi();
  final ApiClient _progressApiClient = ApiClient();
  final UserDashboardController? controller =
      Get.isRegistered<UserDashboardController>()
          ? Get.find<UserDashboardController>()
          : null;
  final GlobalKey<FormState> _supplementFormKey = GlobalKey<FormState>();
  final TextEditingController _reasonController = TextEditingController();
  final TextEditingController _evidenceDescriptionController =
      TextEditingController();
  final TextEditingController _evidenceUrlsController = TextEditingController();
  List<ProgressItem> _relatedProgressItems = const [];
  late AppealRecordModel _appeal;
  bool _isLoadingRelatedProgress = false;
  bool _isSubmittingAction = false;
  String _relatedProgressError = '';

  @override
  void initState() {
    super.initState();
    _appeal = widget.appeal;
    _syncSupplementDraft(_appeal);
    _initializeApi();
    _loadRelatedProgress();
  }

  @override
  void dispose() {
    _reasonController.dispose();
    _evidenceDescriptionController.dispose();
    _evidenceUrlsController.dispose();
    super.dispose();
  }

  Future<void> _initializeApi() async {
    try {
      await _appealApi.initializeWithJwt();
    } catch (e) {
      developer.log('Failed to initialize appeal API for detail page: $e');
    }
  }

  Widget _buildDetailRow(String label, String value, ThemeData themeData,
      {Color? valueColor}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'common.labelWithColon'.trParams({'label': label}),
            style: themeData.textTheme.bodyLarge?.copyWith(
              fontWeight: FontWeight.bold,
              color: themeData.colorScheme.onSurface,
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: themeData.textTheme.bodyMedium?.copyWith(
                color: valueColor ?? themeData.colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        ],
      ),
    );
  }

  bool _isAcceptanceRejected() {
    return normalizeAppealStatusCode(_appeal.acceptanceStatus) ==
        appealRejectedStatusCode();
  }

  bool _isAcceptanceNeedSupplement() {
    return normalizeAppealStatusCode(_appeal.acceptanceStatus) ==
        'Need_Supplement';
  }

  bool _isAwaitingUserAction() {
    return _isAcceptanceNeedSupplement() || _isAcceptanceRejected();
  }

  bool _canWithdrawAppeal() {
    final processStatus = normalizeAppealStatusCode(_appeal.processStatus);
    return processStatus == 'Unprocessed' || processStatus == 'Under_Review';
  }

  bool _shouldShowActionCard() {
    return _isAwaitingUserAction() || _canWithdrawAppeal();
  }

  Future<void> _loadRelatedProgress() async {
    final appealId = _appeal.appealId;
    if (appealId == null) {
      setState(() {
        _relatedProgressItems = const [];
        _relatedProgressError = '';
        _isLoadingRelatedProgress = false;
      });
      return;
    }

    setState(() {
      _isLoadingRelatedProgress = true;
      _relatedProgressError = '';
    });
    try {
      final related = await _fetchRelatedProgressItems(appealId);
      if (!mounted) {
        return;
      }
      setState(() {
        _relatedProgressItems = related;
      });
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _relatedProgressError = 'progress.error.fetchFailed'.tr;
      });
      developer.log('Failed to load related progress: $e');
    } finally {
      if (mounted) {
        setState(() => _isLoadingRelatedProgress = false);
      }
    }
  }

  Future<List<ProgressItem>> _fetchRelatedProgressItems(int appealId) async {
    final items = <ProgressItem>[];
    var page = 1;
    while (true) {
      final response = await _progressApiClient.invokeAPI(
        '/api/progress/me',
        'GET',
        [
          QueryParam('appealId', '$appealId'),
          QueryParam('page', '$page'),
          QueryParam('size', '$_relatedProgressPageSize'),
        ],
        null,
        {},
        {},
        'application/json',
        ['bearerAuth'],
      );
      if (response.statusCode != 200) {
        final message = response.bodyBytes.isEmpty
            ? 'HTTP ${response.statusCode}'
            : utf8.decode(response.bodyBytes);
        throw Exception(message);
      }
      final pageItems = response.bodyBytes.isEmpty
          ? const <ProgressItem>[]
          : (jsonDecode(utf8.decode(response.bodyBytes)) as List<dynamic>)
              .map(
                  (json) => ProgressItem.fromJson(json as Map<String, dynamic>))
              .toList(growable: false);
      items.addAll(pageItems);
      if (pageItems.length < _relatedProgressPageSize) {
        break;
      }
      page++;
    }
    return items;
  }

  void _syncSupplementDraft(AppealRecordModel appeal) {
    _reasonController.text = appeal.appealReason ?? '';
    _evidenceDescriptionController.text = appeal.evidenceDescription ?? '';
    _evidenceUrlsController.text = appeal.evidenceUrls ?? '';
  }

  String? _normalizeOptionalText(String value) {
    final trimmed = value.trim();
    return trimmed.isEmpty ? null : trimmed;
  }

  AppealRecordModel _buildSupplementPayload() {
    return AppealRecordModel(
      appealReason: _normalizeOptionalText(_reasonController.text),
      evidenceDescription:
          _normalizeOptionalText(_evidenceDescriptionController.text),
      evidenceUrls: _normalizeOptionalText(_evidenceUrlsController.text),
    );
  }

  Widget _buildSupplementField({
    required ThemeData themeData,
    required TextEditingController controller,
    required String label,
    String? hint,
    int maxLines = 1,
    String? Function(String?)? validator,
  }) {
    return TextFormField(
      controller: controller,
      enabled: !_isSubmittingAction,
      maxLines: maxLines,
      validator: validator,
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        alignLabelWithHint: maxLines > 1,
        filled: true,
        fillColor: themeData.colorScheme.surfaceContainerLowest,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
        ),
      ),
    );
  }

  Future<bool?> _showActionConfirmDialog(
      ThemeData themeData, String title, String confirmLabel) {
    return showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: themeData.colorScheme.surfaceContainer,
        title: Text(title),
        content: Text(title),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text('common.cancel'.tr),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(confirmLabel),
          ),
        ],
      ),
    );
  }

  Future<void> _triggerCurrentUserAcceptanceEvent({
    required String event,
    required String successMessage,
  }) async {
    final appealId = _appeal.appealId;
    if (appealId == null) {
      _showSnackBar(
          'appeal.error.submitFailed'.trParams({'error': 'Invalid appeal ID'}),
          isError: true);
      return;
    }
    final requiresSupplementPayload = _isAwaitingUserAction();
    if (requiresSupplementPayload &&
        !(_supplementFormKey.currentState?.validate() ?? false)) {
      return;
    }
    setState(() => _isSubmittingAction = true);
    try {
      await _appealApi.initializeWithJwt();
      final updated = await _appealApi
          .apiAppealsMeAppealIdAcceptanceEventsEventPost(
            appealId: appealId,
            event: event,
            appealRecord:
                requiresSupplementPayload ? _buildSupplementPayload() : null,
            idempotencyKey: generateIdempotencyKey(),
          )
          .timeout(const Duration(seconds: 5));
      setState(() {
        _appeal = updated;
        _syncSupplementDraft(updated);
      });
      await _loadRelatedProgress();
      _showSnackBar(successMessage);
    } catch (e) {
      _showSnackBar(
        'appeal.error.submitFailed'
            .trParams({'error': formatUserAppealError(e)}),
        isError: true,
      );
    } finally {
      if (mounted) {
        setState(() => _isSubmittingAction = false);
      }
    }
  }

  Future<void> _triggerCurrentUserProcessEvent({
    required String event,
    required String successMessage,
  }) async {
    final appealId = _appeal.appealId;
    if (appealId == null) {
      _showSnackBar(
        'appeal.error.submitFailed'.trParams({'error': 'Invalid appeal ID'}),
        isError: true,
      );
      return;
    }
    setState(() => _isSubmittingAction = true);
    try {
      await _appealApi.initializeWithJwt();
      final updated = await _appealApi
          .apiAppealsMeAppealIdProcessEventsEventPost(
            appealId: appealId,
            event: event,
            idempotencyKey: generateIdempotencyKey(),
          )
          .timeout(const Duration(seconds: 5));
      setState(() {
        _appeal = updated;
        _syncSupplementDraft(updated);
      });
      await _loadRelatedProgress();
      _showSnackBar(successMessage);
    } catch (e) {
      _showSnackBar(
        'appeal.error.submitFailed'
            .trParams({'error': formatUserAppealError(e)}),
        isError: true,
      );
    } finally {
      if (mounted) {
        setState(() => _isSubmittingAction = false);
      }
    }
  }

  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) {
      return;
    }
    final themeData = controller?.currentBodyTheme.value ?? Theme.of(context);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError
            ? themeData.colorScheme.error
            : themeData.colorScheme.primary,
      ),
    );
  }

  Widget _buildRelatedProgressSection(ThemeData themeData) {
    if (_isLoadingRelatedProgress) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 24.0),
        child: Center(child: CupertinoActivityIndicator()),
      );
    }
    if (_relatedProgressError.isNotEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 12.0),
        child: Text(
          _relatedProgressError,
          style: themeData.textTheme.bodyMedium?.copyWith(
            color: themeData.colorScheme.error,
          ),
        ),
      );
    }
    if (_relatedProgressItems.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 12.0),
        child: Text(
          'appeal.progress.empty'.tr,
          style: themeData.textTheme.bodyMedium?.copyWith(
            color: themeData.colorScheme.onSurfaceVariant,
          ),
        ),
      );
    }
    return Column(
      children: _relatedProgressItems
          .map(
            (item) => Card(
              margin: const EdgeInsets.only(top: 12),
              color: themeData.colorScheme.surfaceContainerLowest,
              child: ListTile(
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 8,
                ),
                title: Text(
                  item.title,
                  style: themeData.textTheme.titleSmall?.copyWith(
                    color: themeData.colorScheme.onSurface,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                subtitle: Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'appeal.progress.summary'.trParams({
                          'status': localizeProgressStatus(item.status),
                          'time': formatProgressDateTime(item.submitTime),
                        }),
                        style: themeData.textTheme.bodySmall?.copyWith(
                          color: themeData.colorScheme.onSurfaceVariant,
                        ),
                      ),
                      if ((item.details ?? '').trim().isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Text(
                          item.details!.trim(),
                          style: themeData.textTheme.bodySmall?.copyWith(
                            color: themeData.colorScheme.onSurfaceVariant,
                          ),
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ],
                  ),
                ),
                trailing: Icon(
                  Icons.chevron_right,
                  color: themeData.colorScheme.onSurfaceVariant,
                ),
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => ProgressDetailPage(item: item),
                    ),
                  );
                },
              ),
            ),
          )
          .toList(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final themeData = controller?.currentBodyTheme.value ?? Theme.of(context);
      return DashboardPageTemplate(
        theme: themeData,
        title: 'appeal.detail.title'.tr,
        pageType: DashboardPageType.user,
        onThemeToggle: controller?.toggleBodyTheme,
        bodyIsScrollable: true,
        padding: EdgeInsets.zero,
        body: Padding(
          padding: const EdgeInsets.all(16.0),
          child: CupertinoScrollbar(
            thumbVisibility: true,
            child: ListView(
              children: [
                Card(
                  elevation: 2,
                  color: themeData.colorScheme.surfaceContainer,
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildDetailRow(
                            'appeal.detail.appealId'.tr,
                            _appeal.appealId?.toString() ?? 'common.none'.tr,
                            themeData),
                        _buildDetailRow(
                            'appeal.detail.offenseId'.tr,
                            _appeal.offenseId?.toString() ?? 'common.none'.tr,
                            themeData),
                        _buildDetailRow(
                            'appeal.detail.appellant'.tr,
                            _appeal.appellantName ?? 'common.none'.tr,
                            themeData),
                        _buildDetailRow(
                            'appeal.detail.idCard'.tr,
                            _appeal.appellantIdCard ?? 'common.none'.tr,
                            themeData),
                        _buildDetailRow(
                            'appeal.detail.contact'.tr,
                            _appeal.appellantContact ?? 'common.none'.tr,
                            themeData),
                        _buildDetailRow(
                            'appeal.detail.reason'.tr,
                            _appeal.appealReason ?? 'common.none'.tr,
                            themeData),
                        _buildDetailRow(
                            'appeal.detail.evidenceDescription'.tr,
                            _appeal.evidenceDescription ?? 'common.none'.tr,
                            themeData),
                        _buildDetailRow(
                            'appeal.detail.evidenceUrls'.tr,
                            _appeal.evidenceUrls ?? 'common.none'.tr,
                            themeData),
                        _buildDetailRow(
                            'appeal.detail.time'.tr,
                            formatAppealDateTime(_appeal.appealTime),
                            themeData),
                        _buildDetailRow(
                          'appeal.detail.acceptanceStatus'.tr,
                          localizeAppealStatus(_appeal.acceptanceStatus),
                          themeData,
                          valueColor:
                              isRejectedAppealStatus(_appeal.acceptanceStatus)
                                  ? themeData.colorScheme.error
                                  : themeData.colorScheme.onSurfaceVariant,
                        ),
                        _buildDetailRow(
                            'appeal.detail.status'.tr,
                            localizeAppealStatus(_appeal.processStatus),
                            themeData,
                            valueColor: isApprovedAppealStatus(
                                    _appeal.processStatus)
                                ? Colors.green
                                : isRejectedAppealStatus(_appeal.processStatus)
                                    ? themeData.colorScheme.error
                                    : themeData.colorScheme.onSurfaceVariant),
                        _buildDetailRow(
                            'appeal.detail.result'.tr,
                            _appeal.processResult ??
                                _appeal.rejectionReason ??
                                'common.none'.tr,
                            themeData),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                if (_shouldShowActionCard())
                  Card(
                    elevation: 2,
                    color: themeData.colorScheme.surfaceContainer,
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12)),
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Form(
                        key: _supplementFormKey,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            if (_isAwaitingUserAction()) ...[
                              Text(
                                'appeal.form.supplementTitle'.tr,
                                style:
                                    themeData.textTheme.titleMedium?.copyWith(
                                  color: themeData.colorScheme.onSurface,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                'appeal.form.supplementHint'.tr,
                                style: themeData.textTheme.bodyMedium?.copyWith(
                                  color: themeData.colorScheme.onSurfaceVariant,
                                ),
                              ),
                              const SizedBox(height: 12),
                              _buildSupplementField(
                                themeData: themeData,
                                controller: _reasonController,
                                label: 'appeal.form.reason'.tr,
                                maxLines: 3,
                                validator: (value) {
                                  if ((value ?? '').trim().isEmpty) {
                                    return 'appeal.validation.required'
                                        .trParams({
                                      'field': 'appeal.form.reason'.tr,
                                    });
                                  }
                                  return null;
                                },
                              ),
                              const SizedBox(height: 12),
                              _buildSupplementField(
                                themeData: themeData,
                                controller: _evidenceDescriptionController,
                                label: 'appeal.form.evidenceDescription'.tr,
                                maxLines: 3,
                              ),
                              const SizedBox(height: 12),
                              _buildSupplementField(
                                themeData: themeData,
                                controller: _evidenceUrlsController,
                                label: 'appeal.form.evidenceUrls'.tr,
                                hint: 'appeal.form.evidenceUrlsHint'.tr,
                                maxLines: 3,
                              ),
                              const SizedBox(height: 12),
                            ],
                            if (_isSubmittingAction)
                              const Center(child: CupertinoActivityIndicator())
                            else ...[
                              if (_isAcceptanceNeedSupplement())
                                ElevatedButton.icon(
                                  onPressed: () async {
                                    final confirmed =
                                        await _showActionConfirmDialog(
                                      themeData,
                                      'appeal.action.supplementComplete'.tr,
                                      'appeal.action.supplementComplete'.tr,
                                    );
                                    if (confirmed == true) {
                                      await _triggerCurrentUserAcceptanceEvent(
                                        event: 'SUPPLEMENT_COMPLETE',
                                        successMessage:
                                            'appeal.success.supplementCompleted'
                                                .tr,
                                      );
                                    }
                                  },
                                  icon: const Icon(CupertinoIcons.doc_text),
                                  label: Text(
                                    'appeal.action.supplementComplete'.tr,
                                  ),
                                )
                              else if (_isAcceptanceRejected())
                                ElevatedButton.icon(
                                  onPressed: () async {
                                    final confirmed =
                                        await _showActionConfirmDialog(
                                      themeData,
                                      'appeal.action.resubmit'.tr,
                                      'appeal.action.resubmit'.tr,
                                    );
                                    if (confirmed == true) {
                                      await _triggerCurrentUserAcceptanceEvent(
                                        event: 'RESUBMIT',
                                        successMessage:
                                            'appeal.success.resubmitted'.tr,
                                      );
                                    }
                                  },
                                  icon: const Icon(CupertinoIcons.refresh),
                                  label: Text('appeal.action.resubmit'.tr),
                                ),
                              if (_canWithdrawAppeal()) ...[
                                if (_isAwaitingUserAction())
                                  const SizedBox(height: 12),
                                OutlinedButton.icon(
                                  onPressed: () async {
                                    final confirmed =
                                        await _showActionConfirmDialog(
                                      themeData,
                                      'appeal.action.withdraw'.tr,
                                      'appeal.action.withdraw'.tr,
                                    );
                                    if (confirmed == true) {
                                      await _triggerCurrentUserProcessEvent(
                                        event: 'WITHDRAW',
                                        successMessage:
                                            'appeal.success.withdrawn'.tr,
                                      );
                                    }
                                  },
                                  icon:
                                      const Icon(CupertinoIcons.clear_circled),
                                  label: Text('appeal.action.withdraw'.tr),
                                ),
                              ],
                            ],
                          ],
                        ),
                      ),
                    ),
                  ),
                const SizedBox(height: 20),
                Card(
                  elevation: 2,
                  color: themeData.colorScheme.surfaceContainer,
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'appeal.progress.related'.tr,
                          style: themeData.textTheme.titleLarge?.copyWith(
                            color: themeData.colorScheme.onSurface,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        _buildRelatedProgressSection(themeData),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16.0),
                  child: Text(
                    _isAwaitingUserAction()
                        ? 'appeal.note.awaitingUserAction'.tr
                        : _canWithdrawAppeal()
                            ? 'appeal.note.withdrawable'.tr
                            : 'appeal.note.readonly'.tr,
                    style: themeData.textTheme.bodyMedium?.copyWith(
                      color: _isAwaitingUserAction() || _canWithdrawAppeal()
                          ? themeData.colorScheme.primary
                          : themeData.colorScheme.error,
                      fontStyle: FontStyle.italic,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    });
  }
}
