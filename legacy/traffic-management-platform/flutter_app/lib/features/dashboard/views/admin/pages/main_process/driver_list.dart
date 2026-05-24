import 'dart:async';

import 'package:final_assignment_front/features/api/driver_information_controller_api.dart';
import 'package:final_assignment_front/features/dashboard/controllers/admin_dashboard_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/dashboard_page_template.dart';
import 'package:final_assignment_front/features/model/driver_information.dart';
import 'package:final_assignment_front/i18n/driver_localizers.dart';
import 'package:final_assignment_front/utils/helpers/role_utils.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:jwt_decoder/jwt_decoder.dart';
import 'package:shared_preferences/shared_preferences.dart';

String generateIdempotencyKey() =>
    DateTime.now().millisecondsSinceEpoch.toString();

const String _fieldName = 'name';
const String _fieldIdCardNumber = 'idCardNumber';
const String _fieldContactNumber = 'contactNumber';
const String _fieldDriverLicenseNumber = 'driverLicenseNumber';
const String _fieldGender = 'gender';
const String _fieldBirthdate = 'birthdate';
const String _fieldFirstLicenseDate = 'firstLicenseDate';
const String _fieldAllowedVehicleType = 'allowedVehicleType';
const String _fieldIssueDate = 'issueDate';
const String _fieldExpiryDate = 'expiryDate';
const List<String> _driverManagementRoles = [
  'SUPER_ADMIN',
  'ADMIN',
  'TRAFFIC_POLICE',
];

Future<List<String>> _resolveDriverManagementRoles() async {
  final prefs = await SharedPreferences.getInstance();
  final storedRoles = prefs.getStringList('userRoles');
  if (storedRoles != null && storedRoles.isNotEmpty) {
    return normalizeRoleCodes(storedRoles);
  }

  final fallbackRole = prefs.getString('userRole');
  final jwtToken = await AuthTokenStore.instance.getJwtToken();
  final jwtRoles = jwtToken == null
      ? const []
      : normalizeRoleCodes(JwtDecoder.decode(jwtToken)['roles']);
  return normalizeRoleCodes([
    if (fallbackRole != null && fallbackRole.isNotEmpty) fallbackRole,
    ...jwtRoles,
  ]);
}

class _DriverFormControllers {
  final name = TextEditingController();
  final idCardNumber = TextEditingController();
  final contactNumber = TextEditingController();
  final driverLicenseNumber = TextEditingController();
  final birthdate = TextEditingController();
  final firstLicenseDate = TextEditingController();
  final allowedVehicleType = TextEditingController();
  final issueDate = TextEditingController();
  final expiryDate = TextEditingController();
  DateTime? birthdateValue;
  DateTime? firstLicenseDateValue;
  DateTime? issueDateValue;
  DateTime? expiryDateValue;

  void setDateValue(String fieldKey, DateTime? value) {
    final normalizedValue = value == null ? null : DateUtils.dateOnly(value);
    switch (fieldKey) {
      case _fieldBirthdate:
        birthdateValue = normalizedValue;
        birthdate.text =
            normalizedValue == null ? '' : formatDriverDate(normalizedValue);
        return;
      case _fieldFirstLicenseDate:
        firstLicenseDateValue = normalizedValue;
        firstLicenseDate.text =
            normalizedValue == null ? '' : formatDriverDate(normalizedValue);
        return;
      case _fieldIssueDate:
        issueDateValue = normalizedValue;
        issueDate.text =
            normalizedValue == null ? '' : formatDriverDate(normalizedValue);
        return;
      case _fieldExpiryDate:
        expiryDateValue = normalizedValue;
        expiryDate.text =
            normalizedValue == null ? '' : formatDriverDate(normalizedValue);
        return;
    }
  }

  DateTime? dateValueFor(String fieldKey) {
    switch (fieldKey) {
      case _fieldBirthdate:
        return birthdateValue;
      case _fieldFirstLicenseDate:
        return firstLicenseDateValue;
      case _fieldIssueDate:
        return issueDateValue;
      case _fieldExpiryDate:
        return expiryDateValue;
      default:
        return null;
    }
  }

  void dispose() {
    name.dispose();
    idCardNumber.dispose();
    contactNumber.dispose();
    driverLicenseNumber.dispose();
    birthdate.dispose();
    firstLicenseDate.dispose();
    allowedVehicleType.dispose();
    issueDate.dispose();
    expiryDate.dispose();
  }
}

class DriverList extends StatefulWidget {
  const DriverList({super.key});

  @override
  State<DriverList> createState() => _DriverListState();
}

class _DriverListState extends State<DriverList> {
  static const int _pageSize = 20;

  final DriverInformationControllerApi driverApi =
      DriverInformationControllerApi();
  final DashboardController controller = Get.find<DashboardController>();
  final TextEditingController _searchController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  final List<DriverInformation> _drivers = [];
  List<DriverInformation> _filteredDrivers = [];

  String _activeQuery = '';
  int _currentPage = 1;
  bool _hasMore = true;
  bool _isLoading = false;
  bool _canManageDrivers = false;
  String _statusMessage = '';
  Timer? _searchDebounce;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_handleScroll);
    _initialize();
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();
    _searchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _initialize() async {
    if (mounted) {
      setState(() {
        _isLoading = true;
        _statusMessage = '';
      });
    }

    try {
      final roles = await _resolveDriverManagementRoles();
      final canManage = hasAnyRole(roles, _driverManagementRoles);
      if (!mounted) return;
      setState(() {
        _canManageDrivers = canManage;
        if (!canManage) {
          _statusMessage = 'driverAdmin.error.adminOnly'.tr;
        }
      });
      if (!canManage) {
        return;
      }
      await _loadDrivers(reset: true);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _statusMessage = 'driverAdmin.error.loadFailed'.trParams({
          'error': formatDriverAdminError(e),
        });
      });
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _loadDrivers({bool reset = false, String? query}) async {
    if (!_canManageDrivers) {
      return;
    }
    if (reset) {
      _currentPage = 1;
      _hasMore = true;
      _activeQuery = (query ?? _searchController.text).trim();
      _drivers.clear();
      _filteredDrivers.clear();
    }
    if (!reset && (_isLoading || !_hasMore)) {
      return;
    }

    if (mounted) {
      setState(() {
        _isLoading = true;
        _statusMessage = '';
      });
    }

    try {
      await driverApi.initializeWithJwt();
      final drivers = _activeQuery.isEmpty
          ? await driverApi.apiDriversGet(page: _currentPage, size: _pageSize)
          : await driverApi.apiDriversSearchGet(
              query: _activeQuery,
              page: _currentPage,
              size: _pageSize,
            );
      drivers.sort((left, right) {
        final leftName = left.name?.toLowerCase() ?? '';
        final rightName = right.name?.toLowerCase() ?? '';
        return leftName.compareTo(rightName);
      });

      if (!mounted) return;
      setState(() {
        _drivers.addAll(drivers);
        _rebuildVisibleDrivers();
        _hasMore = drivers.length == _pageSize;
        _currentPage++;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _drivers.clear();
        _filteredDrivers = [];
        _statusMessage = 'driverAdmin.error.loadFailed'.trParams({
          'error': formatDriverAdminError(e),
        });
      });
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  void _rebuildVisibleDrivers() {
    _filteredDrivers = List<DriverInformation>.from(_drivers);
    if (_filteredDrivers.isEmpty) {
      _statusMessage = _activeQuery.isEmpty
          ? 'driverAdmin.empty.default'.tr
          : 'driverAdmin.empty.filtered'.tr;
    } else {
      _statusMessage = '';
    }
  }

  void _handleScroll() {
    if (!_scrollController.hasClients || _isLoading || !_hasMore) {
      return;
    }
    final position = _scrollController.position;
    if (position.pixels >= position.maxScrollExtent - 200) {
      _loadDrivers();
    }
  }

  Future<void> _refreshDrivers({String? query}) async {
    _searchDebounce?.cancel();
    final effectiveQuery = (query ?? _searchController.text).trim();
    _searchController.value = TextEditingValue(
      text: effectiveQuery,
      selection: TextSelection.collapsed(offset: effectiveQuery.length),
    );
    await _loadDrivers(reset: true, query: effectiveQuery);
  }

  void _scheduleSearchRefresh(String value) {
    _searchDebounce?.cancel();
    _searchDebounce = Timer(const Duration(milliseconds: 350), () {
      if (!mounted) {
        return;
      }
      _refreshDrivers(query: value);
    });
  }

  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;
    final themeData = controller.currentBodyTheme.value;
    ScaffoldMessenger.of(context).clearSnackBars();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          message,
          style: TextStyle(
            color: isError
                ? themeData.colorScheme.onError
                : themeData.colorScheme.onPrimary,
          ),
        ),
        backgroundColor: isError
            ? themeData.colorScheme.error
            : themeData.colorScheme.primary,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  Future<void> _openAddPage() async {
    final created = await Get.to<bool>(() => const AddDriverPage());
    if (!mounted) return;
    if (created == true) {
      await _refreshDrivers();
      _showSnackBar('driverAdmin.success.created'.tr);
    }
  }

  Future<void> _openDetailPage(DriverInformation driver) async {
    final updated = await Get.to<bool>(() => DriverDetailPage(driver: driver));
    if (!mounted) return;
    if (updated == true) {
      await _refreshDrivers();
    }
  }

  Widget _buildInfoLine(
    ThemeData themeData,
    String label,
    String value,
  ) {
    return Padding(
      padding: const EdgeInsets.only(top: 6.0),
      child: RichText(
        text: TextSpan(
          style: themeData.textTheme.bodyMedium?.copyWith(
            color: themeData.colorScheme.onSurfaceVariant,
          ),
          children: [
            TextSpan(
              text: 'common.labelWithColon'.trParams({'label': label}),
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            TextSpan(text: value),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final themeData = controller.currentBodyTheme.value;

      return DashboardPageTemplate(
        theme: themeData,
        title: 'driverAdmin.page.listTitle'.tr,
        pageType: DashboardPageType.admin,
        bodyIsScrollable: true,
        padding: EdgeInsets.zero,
        onThemeToggle: controller.toggleBodyTheme,
        actions: [
          if (_canManageDrivers)
            DashboardPageBarAction(
              icon: Icons.person_add_alt_1_outlined,
              onPressed: () => _openAddPage(),
              tooltip: 'driverAdmin.action.add'.tr,
            ),
          if (_canManageDrivers)
            DashboardPageBarAction(
              icon: Icons.refresh,
              onPressed: () => _refreshDrivers(),
              tooltip: 'driverAdmin.action.refresh'.tr,
            ),
        ],
        body: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            children: [
              Card(
                elevation: 2,
                color: themeData.colorScheme.surfaceContainerLowest,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16.0),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(12.0),
                  child: TextField(
                    controller: _searchController,
                    decoration: InputDecoration(
                      hintText: 'driverAdmin.search.hint'.tr,
                      prefixIcon: const Icon(Icons.search),
                      suffixIcon: _searchController.text.trim().isEmpty
                          ? null
                          : IconButton(
                              onPressed: () {
                                _searchController.clear();
                                setState(() {});
                                _refreshDrivers(query: '');
                              },
                              icon: const Icon(Icons.clear),
                            ),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12.0),
                        borderSide: BorderSide.none,
                      ),
                      filled: true,
                      fillColor: themeData.colorScheme.surfaceContainer,
                    ),
                    onChanged: (value) {
                      setState(() {});
                      _scheduleSearchRefresh(value);
                    },
                    onSubmitted: (value) => _refreshDrivers(query: value),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Expanded(
                child: _isLoading && _drivers.isEmpty
                    ? Center(
                        child: CupertinoActivityIndicator(
                          color: themeData.colorScheme.primary,
                          radius: 16,
                        ),
                      )
                    : _statusMessage.isNotEmpty
                        ? Center(
                            child: Text(
                              _statusMessage,
                              style: themeData.textTheme.bodyLarge?.copyWith(
                                color: themeData.colorScheme.error,
                              ),
                              textAlign: TextAlign.center,
                            ),
                          )
                        : _filteredDrivers.isEmpty
                            ? Center(
                                child: Text(
                                  _searchController.text.trim().isEmpty
                                      ? 'driverAdmin.empty.default'.tr
                                      : 'driverAdmin.empty.filtered'.tr,
                                  style:
                                      themeData.textTheme.bodyLarge?.copyWith(
                                    color:
                                        themeData.colorScheme.onSurfaceVariant,
                                  ),
                                  textAlign: TextAlign.center,
                                ),
                              )
                            : RefreshIndicator(
                                onRefresh: () => _refreshDrivers(),
                                color: themeData.colorScheme.primary,
                                backgroundColor:
                                    themeData.colorScheme.surfaceContainer,
                                child: ListView.separated(
                                  controller: _scrollController,
                                  physics:
                                      const AlwaysScrollableScrollPhysics(),
                                  itemCount: _filteredDrivers.length +
                                      ((_isLoading && _drivers.isNotEmpty)
                                          ? 1
                                          : 0),
                                  separatorBuilder: (_, index) =>
                                      index >= _filteredDrivers.length - 1
                                          ? const SizedBox.shrink()
                                          : const SizedBox(height: 12),
                                  itemBuilder: (context, index) {
                                    if (index >= _filteredDrivers.length) {
                                      return const Padding(
                                        padding:
                                            EdgeInsets.symmetric(vertical: 16),
                                        child: Center(
                                          child: CupertinoActivityIndicator(
                                            radius: 12,
                                          ),
                                        ),
                                      );
                                    }
                                    final driver = _filteredDrivers[index];
                                    final name =
                                        driverDisplayValue(driver.name);
                                    final driverId =
                                        '${driver.driverId ?? 'common.none'.tr}';
                                    final contact = driverDisplayValue(
                                      driver.contactNumber,
                                    );
                                    final license = driverDisplayValue(
                                      driver.driverLicenseNumber,
                                    );

                                    return Card(
                                      elevation: 2,
                                      color: themeData
                                          .colorScheme.surfaceContainerLowest,
                                      shape: RoundedRectangleBorder(
                                        borderRadius:
                                            BorderRadius.circular(16.0),
                                      ),
                                      child: InkWell(
                                        borderRadius:
                                            BorderRadius.circular(16.0),
                                        onTap: () => _openDetailPage(driver),
                                        child: Padding(
                                          padding: const EdgeInsets.all(16.0),
                                          child: Column(
                                            crossAxisAlignment:
                                                CrossAxisAlignment.start,
                                            children: [
                                              Row(
                                                children: [
                                                  Expanded(
                                                    child: Text(
                                                      name,
                                                      style: themeData
                                                          .textTheme.titleMedium
                                                          ?.copyWith(
                                                        fontWeight:
                                                            FontWeight.w700,
                                                      ),
                                                    ),
                                                  ),
                                                  const Icon(
                                                    CupertinoIcons
                                                        .right_chevron,
                                                    size: 18,
                                                  ),
                                                ],
                                              ),
                                              const SizedBox(height: 8),
                                              _buildInfoLine(
                                                themeData,
                                                'driverAdmin.field.driverId'.tr,
                                                driverId,
                                              ),
                                              _buildInfoLine(
                                                themeData,
                                                'driverAdmin.field.gender'.tr,
                                                localizeDriverGender(
                                                  driver.gender,
                                                ),
                                              ),
                                              _buildInfoLine(
                                                themeData,
                                                'driverAdmin.field.contactNumber'
                                                    .tr,
                                                contact,
                                              ),
                                              _buildInfoLine(
                                                themeData,
                                                'driverAdmin.field.driverLicenseNumber'
                                                    .tr,
                                                license,
                                              ),
                                            ],
                                          ),
                                        ),
                                      ),
                                    );
                                  },
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

class AddDriverPage extends StatefulWidget {
  const AddDriverPage({super.key});

  @override
  State<AddDriverPage> createState() => _AddDriverPageState();
}

class _AddDriverPageState extends State<AddDriverPage> {
  final DriverInformationControllerApi driverApi =
      DriverInformationControllerApi();
  final DashboardController controller = Get.find<DashboardController>();
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final _DriverFormControllers _controllers = _DriverFormControllers();

  bool _isLoading = false;
  String _statusMessage = '';
  String? _selectedGender;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  @override
  void dispose() {
    _controllers.dispose();
    super.dispose();
  }

  Future<void> _initialize() async {
    if (mounted) {
      setState(() {
        _isLoading = true;
        _statusMessage = '';
      });
    }

    try {
      final roles = await _resolveDriverManagementRoles();
      final canManage = hasAnyRole(roles, _driverManagementRoles);
      if (!mounted) return;
      setState(() {
        if (!canManage) {
          _statusMessage = 'driverAdmin.error.adminOnly'.tr;
        }
      });
      if (!canManage) {
        return;
      }
      await driverApi.initializeWithJwt();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _statusMessage = 'driverAdmin.error.initFailed'.trParams({
          'error': formatDriverAdminError(e),
        });
      });
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _pickDate(String fieldKey) async {
    final pickedDate = await showDatePicker(
      context: context,
      initialDate: _controllers.dateValueFor(fieldKey) ?? DateTime.now(),
      firstDate: DateTime(1900),
      lastDate: DateTime(2100),
    );
    if (!mounted || pickedDate == null) return;
    setState(() => _controllers.setDateValue(fieldKey, pickedDate));
  }

  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;
    final themeData = controller.currentBodyTheme.value;
    ScaffoldMessenger.of(context).clearSnackBars();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError
            ? themeData.colorScheme.error
            : themeData.colorScheme.primary,
      ),
    );
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) {
      _showSnackBar('driverAdmin.validation.fixFormErrors'.tr, isError: true);
      return;
    }
    if (_selectedGender == null) {
      _showSnackBar('driverAdmin.validation.genderRequired'.tr, isError: true);
      return;
    }

    if (mounted) {
      setState(() => _isLoading = true);
    }

    try {
      await driverApi.initializeWithJwt();
      final driver = DriverInformation(
        name: _controllers.name.text.trim(),
        idCardNumber: _controllers.idCardNumber.text.trim(),
        contactNumber: _controllers.contactNumber.text.trim(),
        driverLicenseNumber: _controllers.driverLicenseNumber.text.trim(),
        gender: driverGenderToBackend(_selectedGender),
        birthdate: _controllers.birthdateValue,
        firstLicenseDate: _controllers.firstLicenseDateValue,
        allowedVehicleType: _controllers.allowedVehicleType.text.trim().isEmpty
            ? null
            : _controllers.allowedVehicleType.text.trim(),
        issueDate: _controllers.issueDateValue,
        expiryDate: _controllers.expiryDateValue,
      );

      await driverApi.apiDriversPost(
        driverInformation: driver,
        idempotencyKey: generateIdempotencyKey(),
      );

      if (!mounted) return;
      Get.back(result: true);
    } catch (e) {
      _showSnackBar(
        'driverAdmin.error.createFailed'.trParams({
          'error': formatDriverAdminError(e),
        }),
        isError: true,
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
      final themeData = controller.currentBodyTheme.value;
      return DashboardPageTemplate(
        theme: themeData,
        title: 'driverAdmin.page.addTitle'.tr,
        pageType: DashboardPageType.admin,
        bodyIsScrollable: true,
        padding: EdgeInsets.zero,
        onThemeToggle: controller.toggleBodyTheme,
        body: Padding(
          padding: const EdgeInsets.all(16.0),
          child: _isLoading && _statusMessage.isEmpty
              ? Center(
                  child: CupertinoActivityIndicator(
                    color: themeData.colorScheme.primary,
                    radius: 16,
                  ),
                )
              : _statusMessage.isNotEmpty
                  ? Center(
                      child: Text(
                        _statusMessage,
                        style: themeData.textTheme.bodyLarge?.copyWith(
                          color: themeData.colorScheme.error,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    )
                  : _DriverFormCard(
                      themeData: themeData,
                      formKey: _formKey,
                      controllers: _controllers,
                      selectedGender: _selectedGender,
                      onGenderChanged: (value) {
                        setState(() => _selectedGender = value);
                      },
                      onPickDate: _pickDate,
                      onSubmit: _submit,
                      submitLabel: 'common.submit'.tr,
                      loading: _isLoading,
                    ),
        ),
      );
    });
  }
}

class EditDriverPage extends StatefulWidget {
  final DriverInformation driver;

  const EditDriverPage({super.key, required this.driver});

  @override
  State<EditDriverPage> createState() => _EditDriverPageState();
}

class _EditDriverPageState extends State<EditDriverPage> {
  final DriverInformationControllerApi driverApi =
      DriverInformationControllerApi();
  final DashboardController controller = Get.find<DashboardController>();
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final _DriverFormControllers _controllers = _DriverFormControllers();

  bool _isLoading = false;
  String _statusMessage = '';
  String? _selectedGender;

  @override
  void initState() {
    super.initState();
    _hydrate();
    _initialize();
  }

  void _hydrate() {
    _controllers.name.text = widget.driver.name ?? '';
    _controllers.idCardNumber.text = widget.driver.idCardNumber ?? '';
    _controllers.contactNumber.text = widget.driver.contactNumber ?? '';
    _controllers.driverLicenseNumber.text =
        widget.driver.driverLicenseNumber ?? '';
    _controllers.setDateValue(_fieldBirthdate, widget.driver.birthdate);
    _controllers.setDateValue(
        _fieldFirstLicenseDate, widget.driver.firstLicenseDate);
    _controllers.allowedVehicleType.text =
        widget.driver.allowedVehicleType ?? '';
    _controllers.setDateValue(_fieldIssueDate, widget.driver.issueDate);
    _controllers.setDateValue(_fieldExpiryDate, widget.driver.expiryDate);
    _selectedGender = normalizeDriverGenderCode(widget.driver.gender);
  }

  @override
  void dispose() {
    _controllers.dispose();
    super.dispose();
  }

  Future<void> _initialize() async {
    if (mounted) {
      setState(() {
        _isLoading = true;
        _statusMessage = '';
      });
    }

    try {
      final roles = await _resolveDriverManagementRoles();
      final canManage = hasAnyRole(roles, _driverManagementRoles);
      if (!mounted) return;
      setState(() {
        if (!canManage) {
          _statusMessage = 'driverAdmin.error.adminOnly'.tr;
        }
      });
      if (!canManage) {
        return;
      }
      await driverApi.initializeWithJwt();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _statusMessage = 'driverAdmin.error.initFailed'.trParams({
          'error': formatDriverAdminError(e),
        });
      });
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _pickDate(String fieldKey) async {
    final pickedDate = await showDatePicker(
      context: context,
      initialDate: _controllers.dateValueFor(fieldKey) ?? DateTime.now(),
      firstDate: DateTime(1900),
      lastDate: DateTime(2100),
    );
    if (!mounted || pickedDate == null) return;
    setState(() => _controllers.setDateValue(fieldKey, pickedDate));
  }

  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;
    final themeData = controller.currentBodyTheme.value;
    ScaffoldMessenger.of(context).clearSnackBars();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError
            ? themeData.colorScheme.error
            : themeData.colorScheme.primary,
      ),
    );
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) {
      _showSnackBar('driverAdmin.validation.fixFormErrors'.tr, isError: true);
      return;
    }
    if (_selectedGender == null) {
      _showSnackBar('driverAdmin.validation.genderRequired'.tr, isError: true);
      return;
    }
    if (widget.driver.driverId == null) {
      _showSnackBar('driverAdmin.error.idMissing'.tr, isError: true);
      return;
    }

    if (mounted) {
      setState(() => _isLoading = true);
    }

    try {
      await driverApi.initializeWithJwt();
      final updatedDriver = widget.driver.copyWith(
        name: _controllers.name.text.trim(),
        idCardNumber: _controllers.idCardNumber.text.trim(),
        contactNumber: _controllers.contactNumber.text.trim(),
        driverLicenseNumber: _controllers.driverLicenseNumber.text.trim(),
        gender: driverGenderToBackend(_selectedGender),
        birthdate: _controllers.birthdateValue,
        firstLicenseDate: _controllers.firstLicenseDateValue,
        allowedVehicleType: _controllers.allowedVehicleType.text.trim().isEmpty
            ? null
            : _controllers.allowedVehicleType.text.trim(),
        issueDate: _controllers.issueDateValue,
        expiryDate: _controllers.expiryDateValue,
      );

      await driverApi.apiDriversDriverIdPut(
        driverId: widget.driver.driverId!,
        driverInformation: updatedDriver,
        idempotencyKey: generateIdempotencyKey(),
      );

      if (!mounted) return;
      Get.back(result: true);
    } catch (e) {
      _showSnackBar(
        'driverAdmin.error.updateFailed'.trParams({
          'error': formatDriverAdminError(e),
        }),
        isError: true,
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
      final themeData = controller.currentBodyTheme.value;
      return DashboardPageTemplate(
        theme: themeData,
        title: 'driverAdmin.page.editTitle'.tr,
        pageType: DashboardPageType.admin,
        bodyIsScrollable: true,
        padding: EdgeInsets.zero,
        onThemeToggle: controller.toggleBodyTheme,
        body: Padding(
          padding: const EdgeInsets.all(16.0),
          child: _isLoading && _statusMessage.isEmpty
              ? Center(
                  child: CupertinoActivityIndicator(
                    color: themeData.colorScheme.primary,
                    radius: 16,
                  ),
                )
              : _statusMessage.isNotEmpty
                  ? Center(
                      child: Text(
                        _statusMessage,
                        style: themeData.textTheme.bodyLarge?.copyWith(
                          color: themeData.colorScheme.error,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    )
                  : _DriverFormCard(
                      themeData: themeData,
                      formKey: _formKey,
                      controllers: _controllers,
                      selectedGender: _selectedGender,
                      onGenderChanged: (value) {
                        setState(() => _selectedGender = value);
                      },
                      onPickDate: _pickDate,
                      onSubmit: _submit,
                      submitLabel: 'common.save'.tr,
                      loading: _isLoading,
                    ),
        ),
      );
    });
  }
}

class DriverDetailPage extends StatefulWidget {
  final DriverInformation driver;

  const DriverDetailPage({super.key, required this.driver});

  @override
  State<DriverDetailPage> createState() => _DriverDetailPageState();
}

class _DriverDetailPageState extends State<DriverDetailPage> {
  final DriverInformationControllerApi driverApi =
      DriverInformationControllerApi();
  final DashboardController controller = Get.find<DashboardController>();

  DriverInformation? _driver;
  bool _isLoading = false;
  bool _canManageDrivers = false;
  String _statusMessage = '';

  @override
  void initState() {
    super.initState();
    _driver = widget.driver;
    _loadDriver();
  }

  Future<void> _loadDriver() async {
    final driverId = _driver?.driverId;
    if (driverId == null) {
      if (mounted) {
        setState(() => _statusMessage = 'driverAdmin.error.idMissing'.tr);
      }
      return;
    }

    if (mounted) {
      setState(() {
        _isLoading = true;
        _statusMessage = '';
      });
    }

    try {
      final roles = await _resolveDriverManagementRoles();
      final canManage = hasAnyRole(roles, _driverManagementRoles);
      if (!mounted) return;
      setState(() {
        _canManageDrivers = canManage;
        if (!canManage) {
          _statusMessage = 'driverAdmin.error.adminOnly'.tr;
        }
      });
      if (!canManage) {
        return;
      }
      await driverApi.initializeWithJwt();
      final driver = await driverApi.apiDriversDriverIdGet(driverId: driverId);
      if (!mounted) return;
      if (driver == null) {
        setState(() => _statusMessage = 'driverAdmin.error.detailNotFound'.tr);
        return;
      }
      setState(() => _driver = driver);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _statusMessage = 'driverAdmin.error.detailFailed'.trParams({
          'error': formatDriverAdminError(e),
        });
      });
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _openEditPage() async {
    final driver = _driver;
    if (driver == null) return;
    final updated = await Get.to<bool>(() => EditDriverPage(driver: driver));
    if (!mounted) return;
    if (updated == true) {
      await _loadDriver();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('driverAdmin.success.updated'.tr)),
        );
      }
    }
  }

  Future<void> _deleteDriver() async {
    final driverId = _driver?.driverId;
    if (driverId == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('driverAdmin.error.idMissing'.tr),
            backgroundColor:
                controller.currentBodyTheme.value.colorScheme.error,
          ),
        );
      }
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        final themeData = controller.currentBodyTheme.value;
        return Theme(
          data: themeData,
          child: AlertDialog(
            title: Text('driverAdmin.delete.confirmTitle'.tr),
            content: Text('driverAdmin.delete.confirmBody'.tr),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(dialogContext).pop(false),
                child: Text('common.cancel'.tr),
              ),
              ElevatedButton(
                onPressed: () => Navigator.of(dialogContext).pop(true),
                style: ElevatedButton.styleFrom(
                  backgroundColor: themeData.colorScheme.error,
                  foregroundColor: themeData.colorScheme.onError,
                ),
                child: Text('driverAdmin.action.delete'.tr),
              ),
            ],
          ),
        );
      },
    );

    if (confirmed != true || !mounted) return;

    try {
      await driverApi.initializeWithJwt();
      await driverApi.apiDriversDriverIdDelete(driverId: driverId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('driverAdmin.success.deleted'.tr)),
      );
      Get.back(result: true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'driverAdmin.error.deleteFailed'.trParams({
              'error': formatDriverAdminError(e),
            }),
          ),
          backgroundColor: controller.currentBodyTheme.value.colorScheme.error,
        ),
      );
    }
  }

  Widget _buildDetailRow(
    ThemeData themeData,
    String label,
    String value,
  ) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 180,
            child: Text(
              '$label:',
              style: themeData.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: themeData.textTheme.bodyLarge?.copyWith(
                color: themeData.colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final themeData = controller.currentBodyTheme.value;
      final driver = _driver;

      return DashboardPageTemplate(
        theme: themeData,
        title: 'driverAdmin.page.detailTitle'.tr,
        pageType: DashboardPageType.admin,
        bodyIsScrollable: true,
        padding: EdgeInsets.zero,
        onThemeToggle: controller.toggleBodyTheme,
        actions: [
          if (_canManageDrivers && driver != null)
            DashboardPageBarAction(
              icon: Icons.edit_outlined,
              onPressed: () => _openEditPage(),
              tooltip: 'driverAdmin.action.edit'.tr,
            ),
          if (_canManageDrivers && driver != null)
            DashboardPageBarAction(
              icon: Icons.delete_outline,
              onPressed: () => _deleteDriver(),
              tooltip: 'driverAdmin.action.delete'.tr,
              color: themeData.colorScheme.error,
            ),
        ],
        body: Padding(
          padding: const EdgeInsets.all(16.0),
          child: _isLoading
              ? Center(
                  child: CupertinoActivityIndicator(
                    color: themeData.colorScheme.primary,
                    radius: 16,
                  ),
                )
              : _statusMessage.isNotEmpty
                  ? Center(
                      child: Text(
                        _statusMessage,
                        style: themeData.textTheme.bodyLarge?.copyWith(
                          color: themeData.colorScheme.error,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    )
                  : driver == null
                      ? const SizedBox.shrink()
                      : SingleChildScrollView(
                          child: Card(
                            elevation: 2,
                            color: themeData.colorScheme.surfaceContainerLowest,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16.0),
                            ),
                            child: Padding(
                              padding: const EdgeInsets.all(20.0),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  _buildDetailRow(
                                    themeData,
                                    'driverAdmin.field.driverId'.tr,
                                    '${driver.driverId ?? 'common.none'.tr}',
                                  ),
                                  _buildDetailRow(
                                    themeData,
                                    'driverAdmin.field.name'.tr,
                                    driverDisplayValue(driver.name),
                                  ),
                                  _buildDetailRow(
                                    themeData,
                                    'driverAdmin.field.idCardNumber'.tr,
                                    driverDisplayValue(driver.idCardNumber),
                                  ),
                                  _buildDetailRow(
                                    themeData,
                                    'driverAdmin.field.contactNumber'.tr,
                                    driverDisplayValue(driver.contactNumber),
                                  ),
                                  _buildDetailRow(
                                    themeData,
                                    'driverAdmin.field.driverLicenseNumber'.tr,
                                    driverDisplayValue(
                                      driver.driverLicenseNumber,
                                    ),
                                  ),
                                  _buildDetailRow(
                                    themeData,
                                    'driverAdmin.field.gender'.tr,
                                    localizeDriverGender(driver.gender),
                                  ),
                                  _buildDetailRow(
                                    themeData,
                                    'driverAdmin.field.birthdate'.tr,
                                    formatDriverDate(driver.birthdate),
                                  ),
                                  _buildDetailRow(
                                    themeData,
                                    'driverAdmin.field.firstLicenseDate'.tr,
                                    formatDriverDate(driver.firstLicenseDate),
                                  ),
                                  _buildDetailRow(
                                    themeData,
                                    'driverAdmin.field.allowedVehicleType'.tr,
                                    driverDisplayValue(
                                      driver.allowedVehicleType,
                                    ),
                                  ),
                                  _buildDetailRow(
                                    themeData,
                                    'driverAdmin.field.issueDate'.tr,
                                    formatDriverDate(driver.issueDate),
                                  ),
                                  _buildDetailRow(
                                    themeData,
                                    'driverAdmin.field.expiryDate'.tr,
                                    formatDriverDate(driver.expiryDate),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
        ),
      );
    });
  }
}

class _DriverFormCard extends StatelessWidget {
  const _DriverFormCard({
    required this.themeData,
    required this.formKey,
    required this.controllers,
    required this.selectedGender,
    required this.onGenderChanged,
    required this.onPickDate,
    required this.onSubmit,
    required this.submitLabel,
    required this.loading,
  });

  final ThemeData themeData;
  final GlobalKey<FormState> formKey;
  final _DriverFormControllers controllers;
  final String? selectedGender;
  final ValueChanged<String?> onGenderChanged;
  final Future<void> Function(String fieldKey) onPickDate;
  final Future<void> Function() onSubmit;
  final String submitLabel;
  final bool loading;

  Widget _buildTextField({
    required TextEditingController controller,
    required String fieldKey,
    bool required = false,
    TextInputType? keyboardType,
    bool readOnly = false,
    VoidCallback? onTap,
  }) {
    return TextFormField(
      controller: controller,
      keyboardType: keyboardType,
      readOnly: readOnly,
      onTap: onTap,
      decoration: InputDecoration(
        labelText: driverFieldLabel(fieldKey, required: required),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12.0),
        ),
        filled: true,
        fillColor: themeData.colorScheme.surfaceContainer,
        suffixIcon: readOnly ? const Icon(Icons.calendar_today_outlined) : null,
      ),
      validator: (value) => validateDriverField(
        fieldKey,
        value,
        required: required,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Form(
      key: formKey,
      child: SingleChildScrollView(
        child: Card(
          elevation: 2,
          color: themeData.colorScheme.surfaceContainerLowest,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16.0),
          ),
          child: Padding(
            padding: const EdgeInsets.all(20.0),
            child: Column(
              children: [
                _buildTextField(
                  controller: controllers.name,
                  fieldKey: _fieldName,
                  required: true,
                ),
                const SizedBox(height: 16),
                _buildTextField(
                  controller: controllers.idCardNumber,
                  fieldKey: _fieldIdCardNumber,
                  required: true,
                  keyboardType: TextInputType.number,
                ),
                const SizedBox(height: 16),
                _buildTextField(
                  controller: controllers.contactNumber,
                  fieldKey: _fieldContactNumber,
                  required: true,
                  keyboardType: TextInputType.phone,
                ),
                const SizedBox(height: 16),
                _buildTextField(
                  controller: controllers.driverLicenseNumber,
                  fieldKey: _fieldDriverLicenseNumber,
                  required: true,
                  keyboardType: TextInputType.number,
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  initialValue: selectedGender,
                  decoration: InputDecoration(
                    labelText: driverFieldLabel(_fieldGender, required: true),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12.0),
                    ),
                    filled: true,
                    fillColor: themeData.colorScheme.surfaceContainer,
                  ),
                  items: kDriverGenderValues
                      .map(
                        (gender) => DropdownMenuItem<String>(
                          value: gender,
                          child: Text(localizeDriverGender(gender)),
                        ),
                      )
                      .toList(),
                  onChanged: onGenderChanged,
                ),
                const SizedBox(height: 16),
                _buildTextField(
                  controller: controllers.birthdate,
                  fieldKey: _fieldBirthdate,
                  readOnly: true,
                  onTap: () => onPickDate(_fieldBirthdate),
                ),
                const SizedBox(height: 16),
                _buildTextField(
                  controller: controllers.firstLicenseDate,
                  fieldKey: _fieldFirstLicenseDate,
                  readOnly: true,
                  onTap: () => onPickDate(_fieldFirstLicenseDate),
                ),
                const SizedBox(height: 16),
                _buildTextField(
                  controller: controllers.allowedVehicleType,
                  fieldKey: _fieldAllowedVehicleType,
                ),
                const SizedBox(height: 16),
                _buildTextField(
                  controller: controllers.issueDate,
                  fieldKey: _fieldIssueDate,
                  readOnly: true,
                  onTap: () => onPickDate(_fieldIssueDate),
                ),
                const SizedBox(height: 16),
                _buildTextField(
                  controller: controllers.expiryDate,
                  fieldKey: _fieldExpiryDate,
                  readOnly: true,
                  onTap: () => onPickDate(_fieldExpiryDate),
                ),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: loading ? null : () => onSubmit(),
                    child: Text(submitLabel),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
