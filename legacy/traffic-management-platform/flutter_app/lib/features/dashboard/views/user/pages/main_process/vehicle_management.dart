// ignore_for_file: use_build_context_synchronously
import 'package:flutter/material.dart';
import 'package:final_assignment_front/features/api/vehicle_information_controller_api.dart';
import 'package:final_assignment_front/features/api/driver_information_controller_api.dart';
import 'package:final_assignment_front/features/api/user_management_controller_api.dart';
import 'package:final_assignment_front/features/model/vehicle_information.dart';
import 'package:final_assignment_front/features/model/driver_information.dart';
import 'package:final_assignment_front/features/model/user_management.dart';
import 'package:final_assignment_front/features/dashboard/controllers/user_dashboard_screen_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/dashboard_page_template.dart';
import 'package:final_assignment_front/i18n/status_localizers.dart';
import 'package:final_assignment_front/i18n/vehicle_field_localizers.dart';
import 'package:final_assignment_front/utils/helpers/api_exception.dart';
import 'package:final_assignment_front/utils/helpers/role_utils.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:jwt_decoder/jwt_decoder.dart';

String generateIdempotencyKey() {
  return DateTime.now().millisecondsSinceEpoch.toString();
}

String buildVehicleLicensePlate(String plateSuffix) {
  return '$kVehiclePlatePrefix${plateSuffix.trim()}';
}

String? validateProfileBoundVehicleIdCard(String? value) {
  final validationMessage = validateVehicleField(
    kVehicleFieldIdCard,
    value,
    required: true,
  );
  if (validationMessage == null) {
    return null;
  }

  return (value?.trim().isEmpty ?? true)
      ? 'vehicle.error.fillIdCardInProfile'.tr
      : validationMessage;
}

Future<bool> ensureVehicleLicensePlateAvailable({
  required VehicleInformationControllerApi vehicleApi,
  required String licensePlate,
  String? currentLicensePlate,
}) async {
  if (licensePlate == currentLicensePlate) {
    return true;
  }

  return !(await vehicleApi.apiVehiclesExistsLicensePlateGet(
    licensePlate: licensePlate,
  ));
}

String? _trimVehicleProfileValue(String? value) {
  final normalized = value?.trim();
  if (normalized == null || normalized.isEmpty) {
    return null;
  }
  return normalized;
}

String? _resolveVehicleOwnerName({
  DriverInformation? driverInfo,
  UserManagement? user,
  SharedPreferences? prefs,
  VehicleInformation? vehicle,
}) {
  return _trimVehicleProfileValue(driverInfo?.name) ??
      _trimVehicleProfileValue(user?.realName) ??
      _trimVehicleProfileValue(prefs?.getString('displayName')) ??
      _trimVehicleProfileValue(prefs?.getString('driverName')) ??
      _trimVehicleProfileValue(user?.username) ??
      _trimVehicleProfileValue(prefs?.getString('userName')) ??
      _trimVehicleProfileValue(vehicle?.ownerName);
}

String? _resolveVehicleOwnerIdCard({
  DriverInformation? driverInfo,
  UserManagement? user,
  VehicleInformation? vehicle,
}) {
  return _trimVehicleProfileValue(driverInfo?.idCardNumber) ??
      _trimVehicleProfileValue(user?.idCardNumber) ??
      _trimVehicleProfileValue(vehicle?.idCardNumber);
}

String? _resolveVehicleOwnerContact({
  DriverInformation? driverInfo,
  UserManagement? user,
  VehicleInformation? vehicle,
}) {
  return _trimVehicleProfileValue(driverInfo?.contactNumber) ??
      _trimVehicleProfileValue(user?.contactNumber) ??
      _trimVehicleProfileValue(vehicle?.contactNumber);
}

class VehicleManagement extends StatefulWidget {
  const VehicleManagement({super.key});

  @override
  State<VehicleManagement> createState() => _VehicleManagementState();
}

class _VehicleManagementState extends State<VehicleManagement> {
  final TextEditingController _searchController = TextEditingController();
  final VehicleInformationControllerApi vehicleApi =
      VehicleInformationControllerApi();
  final UserManagementControllerApi userApi = UserManagementControllerApi();
  final DriverInformationControllerApi driverApi =
      DriverInformationControllerApi();
  final List<VehicleInformation> _vehicleList = [];
  List<VehicleInformation> _filteredVehicleList = [];
  bool _isLoading = true;
  String _errorMessage = '';
  String? _currentDriverIdCardNumber;
  bool _hasMore = true;
  String _searchType = kVehicleSearchTypeLicensePlate;

  final UserDashboardController controller =
      Get.find<UserDashboardController>();

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  void _setStateSafely(VoidCallback update) {
    if (!mounted) return;
    setState(update);
  }

  List<VehicleInformation> _buildFilteredVehicles(
    Iterable<VehicleInformation> vehicles,
    String query,
  ) {
    final searchQuery = query.trim().toLowerCase();
    if (searchQuery.isEmpty) {
      return vehicles.toList();
    }

    return vehicles.where((vehicle) {
      final licensePlate = (vehicle.licensePlate ?? '').toLowerCase();
      final vehicleType = (vehicle.vehicleType ?? '').toLowerCase();
      if (_searchType == kVehicleSearchTypeLicensePlate) {
        return licensePlate.contains(searchQuery);
      }
      return vehicleType.contains(searchQuery);
    }).toList();
  }

  String _resolveVehicleListErrorMessage(
    List<VehicleInformation> filteredVehicles,
    String query,
  ) {
    if (filteredVehicles.isNotEmpty) return '';
    if (_vehicleList.isEmpty) return 'vehicle.empty'.tr;
    return query.trim().isNotEmpty
        ? 'vehicle.empty.filtered'.tr
        : 'vehicle.empty'.tr;
  }

  Future<void> _initialize() async {
    _setStateSafely(() {
      _isLoading = true;
      _errorMessage = '';
    });
    try {
      final prefs = await SharedPreferences.getInstance();
      if (!mounted) return;
      final jwtToken = await AuthTokenStore.instance.getJwtToken();
      if (jwtToken == null) {
        throw Exception('vehicle.error.jwtMissingRelogin'.tr);
      }

      await vehicleApi.initializeWithJwt();
      if (!mounted) return;
      await driverApi.initializeWithJwt();
      if (!mounted) return;
      await userApi.initializeWithJwt();
      if (!mounted) return;

      final user = await _fetchUserManagement();
      if (!mounted) return;
      final driverInfo = await _fetchDriverInformation();
      if (!mounted) return;
      _resolveVehicleOwnerName(
        driverInfo: driverInfo,
        user: user,
        prefs: prefs,
      );
      _currentDriverIdCardNumber = _resolveVehicleOwnerIdCard(
        driverInfo: driverInfo,
        user: user,
      );

      if (_currentDriverIdCardNumber == null ||
          _currentDriverIdCardNumber!.isEmpty) {
        throw Exception('vehicle.error.driverIdCardMissing'.tr);
      }

      await _fetchUserVehicles(reset: true);
    } catch (e) {
      _setStateSafely(() {
        _errorMessage = 'vehicle.error.initializeFailed'
            .trParams({'error': formatVehicleError(e)});
      });
    } finally {
      _setStateSafely(() => _isLoading = false);
    }
  }

  Future<UserManagement?> _fetchUserManagement() async {
    try {
      await userApi.initializeWithJwt();
      return await userApi.apiUsersMeGet();
    } catch (e) {
      debugPrint('Failed to fetch UserManagement: $e');
      return null;
    }
  }

  Future<DriverInformation?> _fetchDriverInformation() async {
    try {
      await driverApi.initializeWithJwt();
      return await driverApi.apiDriversMeGet();
    } catch (e) {
      debugPrint('Failed to fetch DriverInformation: $e');
      return null;
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _fetchUserVehicles({bool reset = false, String? query}) async {
    if (_currentDriverIdCardNumber == null) {
      _setStateSafely(() {
        _errorMessage = 'vehicle.error.missingIdCard'.tr;
        _isLoading = false;
      });
      return;
    }

    if (reset) {
      _hasMore = true;
      _vehicleList.clear();
      _filteredVehicleList.clear();
    }
    if (!_hasMore && query == null) return;

    _setStateSafely(() {
      _isLoading = true;
      _errorMessage = '';
    });

    final searchQuery = query?.trim() ?? '';
    debugPrint(
        'Fetching vehicles with query: $searchQuery, searchType: $_searchType');

    try {
      final vehicles = await vehicleApi.apiVehiclesMeGet();
      if (!mounted) return;
      final filteredVehicles = _buildFilteredVehicles(vehicles, searchQuery);

      _setStateSafely(() {
        _vehicleList
          ..clear()
          ..addAll(vehicles);
        _filteredVehicleList = filteredVehicles;
        _hasMore = false;
        _errorMessage =
            _resolveVehicleListErrorMessage(filteredVehicles, searchQuery);
      });
    } catch (e) {
      _setStateSafely(() {
        if (e is ApiException && e.code == 400) {
          _errorMessage = 'vehicle.error.invalidQuery'.tr;
        } else if (e is ApiException && e.code == 404) {
          _vehicleList.clear();
          _filteredVehicleList.clear();
          _errorMessage = 'vehicle.error.notFoundBySearchType'.trParams({
            'field': vehicleSearchFieldLabel(_searchType),
            'query': searchQuery,
          });
          _hasMore = false;
        } else {
          _errorMessage = e is ApiException && e.code == 403
              ? 'vehicle.error.unauthorized'.tr
              : 'vehicle.error.loadFailed'
                  .trParams({'error': formatVehicleError(e)});
        }
      });
    } finally {
      _setStateSafely(() => _isLoading = false);
    }
  }

  void _applyFilters(String query) {
    final filteredVehicles = _buildFilteredVehicles(_vehicleList, query);
    _setStateSafely(() {
      _filteredVehicleList = filteredVehicles;
      _errorMessage = _resolveVehicleListErrorMessage(filteredVehicles, query);
    });
  }

  Future<List<String>> _fetchAutocompleteSuggestions(String prefix) async {
    if (_currentDriverIdCardNumber == null) {
      return [];
    }
    try {
      if (_searchType == kVehicleSearchTypeLicensePlate) {
        final suggestions = await vehicleApi.apiVehiclesMeAutocompletePlatesGet(
          prefix: prefix,
          size: 5,
        );
        return suggestions
            .where((s) => s.toLowerCase().contains(prefix.toLowerCase()))
            .toList();
      } else {
        final suggestions = await vehicleApi.apiVehiclesMeAutocompleteTypesGet(
          prefix: prefix,
          size: 5,
        );
        return suggestions
            .where((s) => s.toLowerCase().contains(prefix.toLowerCase()))
            .toList();
      }
    } catch (e) {
      debugPrint('Failed to fetch autocomplete suggestions: $e');
      return [];
    }
  }

  Future<void> _loadMoreVehicles() async {
    if (!_hasMore || _isLoading) return;
    await _fetchUserVehicles(query: _searchController.text);
  }

  Future<void> _refreshVehicles() async {
    _searchController.clear();
    await _fetchUserVehicles(reset: true);
  }

  Future<void> _searchVehicles() async {
    final query = _searchController.text.trim();
    _applyFilters(query);
  }

  void _createVehicle() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => const AddVehiclePage()),
    ).then((value) {
      if (value == true && mounted) _fetchUserVehicles(reset: true);
    });
  }

  void _goToDetailPage(VehicleInformation vehicle) {
    Navigator.push(
      context,
      MaterialPageRoute(
          builder: (context) => VehicleDetailPage(vehicle: vehicle)),
    ).then((value) {
      if (value == true && mounted) _fetchUserVehicles(reset: true);
    });
  }

  Future<void> _deleteVehicle(int vehicleId, String licensePlate) async {
    _showDeleteConfirmationDialog('vehicle.action.delete'.tr, () async {
      _setStateSafely(() => _isLoading = true);
      try {
        await vehicleApi.apiVehiclesMeVehicleIdDelete(vehicleId: vehicleId);
        _showSnackBar('vehicle.success.deleted'.tr);
        await _fetchUserVehicles(reset: true);
      } catch (e) {
        _showSnackBar(
          'vehicle.error.deleteFailed'
              .trParams({'error': formatVehicleError(e)}),
          isError: true,
        );
      } finally {
        _setStateSafely(() => _isLoading = false);
      }
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

  void _showDeleteConfirmationDialog(String action, VoidCallback onConfirm) {
    showDialog(
      context: context,
      builder: (ctx) {
        final themeData = controller.currentBodyTheme.value;
        return AlertDialog(
          backgroundColor: themeData.colorScheme.surfaceContainerHighest,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: Text(
            'vehicle.dialog.deleteTitle'.tr,
            style: themeData.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
              color: themeData.colorScheme.onSurface,
            ),
          ),
          content: Text(
            'vehicle.dialog.deleteConfirm'.trParams({'action': action}),
            style: themeData.textTheme.bodyMedium?.copyWith(
              color: themeData.colorScheme.onSurfaceVariant,
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: Text(
                'common.cancel'.tr,
                style: themeData.textTheme.labelLarge?.copyWith(
                  color: themeData.colorScheme.onSurfaceVariant,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            ElevatedButton(
              onPressed: () {
                onConfirm();
                Navigator.pop(ctx);
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: themeData.colorScheme.error,
                foregroundColor: themeData.colorScheme.onError,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12)),
                padding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              ),
              child: Text('vehicle.action.delete'.tr),
            ),
          ],
        );
      },
    );
  }

  Widget _buildSearchField(ThemeData themeData) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
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
                _searchVehicles();
              },
              fieldViewBuilder:
                  (context, controller, focusNode, onFieldSubmitted) {
                _searchController.text = controller.text;
                return TextField(
                  controller: controller,
                  focusNode: focusNode,
                  style: TextStyle(color: themeData.colorScheme.onSurface),
                  decoration: InputDecoration(
                    hintText: _searchType == kVehicleSearchTypeLicensePlate
                        ? 'vehicle.search.plateHint'.tr
                        : 'vehicle.search.typeHint'.tr,
                    hintStyle: TextStyle(
                        color: themeData.colorScheme.onSurface
                            .withValues(alpha: 0.6)),
                    prefixIcon: Icon(Icons.search,
                        color: themeData.colorScheme.primary),
                    suffixIcon: controller.text.isNotEmpty
                        ? IconButton(
                            icon: Icon(Icons.clear,
                                color: themeData.colorScheme.onSurfaceVariant),
                            onPressed: () {
                              controller.clear();
                              _searchController.clear();
                              _fetchUserVehicles(reset: true);
                            },
                          )
                        : null,
                    border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12.0)),
                    enabledBorder: OutlineInputBorder(
                      borderSide: BorderSide(
                          color: themeData.colorScheme.outline
                              .withValues(alpha: 0.3)),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderSide: BorderSide(
                          color: themeData.colorScheme.primary, width: 1.5),
                    ),
                    filled: true,
                    fillColor: themeData.colorScheme.surfaceContainerLowest,
                    contentPadding: const EdgeInsets.symmetric(
                        vertical: 12.0, horizontal: 16.0),
                  ),
                  onChanged: (value) => _applyFilters(value),
                  onSubmitted: (value) => _searchVehicles(),
                );
              },
            ),
          ),
          const SizedBox(width: 8),
          DropdownButton<String>(
            value: _searchType,
            onChanged: (String? newValue) {
              if (newValue == null || newValue == _searchType) {
                return;
              }
              _setStateSafely(() {
                _searchType = newValue;
                _searchController.clear();
              });
              _fetchUserVehicles(reset: true);
            },
            items: <String>[
              kVehicleSearchTypeLicensePlate,
              kVehicleSearchTypeVehicleType,
            ].map<DropdownMenuItem<String>>((String value) {
              return DropdownMenuItem<String>(
                value: value,
                child: Text(
                  vehicleSearchTypeLabel(value),
                  style: TextStyle(color: themeData.colorScheme.onSurface),
                ),
              );
            }).toList(),
            dropdownColor: themeData.colorScheme.surfaceContainer,
            icon: Icon(Icons.arrow_drop_down,
                color: themeData.colorScheme.primary),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final themeData = controller.currentBodyTheme.value;
      return DashboardPageTemplate(
        theme: themeData,
        title: 'vehicle.page.title'.tr,
        pageType: DashboardPageType.user,
        onThemeToggle: controller.toggleBodyTheme,
        bodyIsScrollable: true,
        padding: EdgeInsets.zero,
        actions: [
          DashboardPageBarAction(
            icon: Icons.refresh,
            tooltip: 'vehicle.action.refresh'.tr,
            onPressed: _refreshVehicles,
          ),
          DashboardPageBarAction(
            icon: Icons.add,
            tooltip: 'vehicle.action.addInfo'.tr,
            onPressed: _createVehicle,
          ),
        ],
        floatingActionButton: FloatingActionButton(
          onPressed: _createVehicle,
          backgroundColor: themeData.colorScheme.primary,
          foregroundColor: themeData.colorScheme.onPrimary,
          tooltip: 'vehicle.action.add'.tr,
          child: const Icon(Icons.add),
        ),
        body: RefreshIndicator(
          onRefresh: _refreshVehicles,
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              children: [
                _buildSearchField(themeData),
                const SizedBox(height: 12),
                Expanded(
                  child: NotificationListener<ScrollNotification>(
                    onNotification: (scrollInfo) {
                      if (scrollInfo.metrics.pixels ==
                              scrollInfo.metrics.maxScrollExtent &&
                          _hasMore) {
                        _loadMoreVehicles();
                      }
                      return false;
                    },
                    child: _isLoading && _vehicleList.isEmpty
                        ? Center(
                            child: CircularProgressIndicator(
                                valueColor: AlwaysStoppedAnimation(
                                    themeData.colorScheme.primary)))
                        : _errorMessage.isNotEmpty &&
                                _filteredVehicleList.isEmpty
                            ? Center(
                                child: Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Text(
                                      _errorMessage,
                                      style: themeData.textTheme.titleMedium
                                          ?.copyWith(
                                              color:
                                                  themeData.colorScheme.error,
                                              fontWeight: FontWeight.w500),
                                      textAlign: TextAlign.center,
                                    ),
                                    if (shouldShowVehicleUserReloginAction(
                                        _errorMessage))
                                      Padding(
                                        padding:
                                            const EdgeInsets.only(top: 16.0),
                                        child: ElevatedButton(
                                          onPressed: () =>
                                              Navigator.pushReplacementNamed(
                                                  context, '/login'),
                                          style: ElevatedButton.styleFrom(
                                              backgroundColor:
                                                  themeData.colorScheme.primary,
                                              foregroundColor: themeData
                                                  .colorScheme.onPrimary),
                                          child:
                                              Text('vehicle.action.relogin'.tr),
                                        ),
                                      ),
                                  ],
                                ),
                              )
                            : ListView.builder(
                                itemCount: _filteredVehicleList.length +
                                    (_hasMore ? 1 : 0),
                                itemBuilder: (context, index) {
                                  if (index == _filteredVehicleList.length &&
                                      _hasMore) {
                                    return const Padding(
                                        padding: EdgeInsets.all(8.0));
                                  }
                                  final vehicle = _filteredVehicleList[index];
                                  return Card(
                                    margin: const EdgeInsets.symmetric(
                                        vertical: 8.0),
                                    elevation: 3,
                                    color:
                                        themeData.colorScheme.surfaceContainer,
                                    shape: RoundedRectangleBorder(
                                        borderRadius:
                                            BorderRadius.circular(16.0)),
                                    child: ListTile(
                                      contentPadding:
                                          const EdgeInsets.symmetric(
                                              horizontal: 16.0, vertical: 12.0),
                                      title: Text(
                                        'vehicle.card.plate'.trParams({
                                          'value': vehicle.licensePlate ??
                                              'vehicle.value.noPlate'.tr,
                                        }),
                                        style: themeData.textTheme.titleMedium
                                            ?.copyWith(
                                                color: themeData
                                                    .colorScheme.onSurface,
                                                fontWeight: FontWeight.w600),
                                      ),
                                      subtitle: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          const SizedBox(height: 4),
                                          Text(
                                              'vehicle.card.type'.trParams({
                                                'value': vehicle.vehicleType ??
                                                    'vehicle.value.noType'.tr,
                                              }),
                                              style: themeData
                                                  .textTheme.bodyMedium
                                                  ?.copyWith(
                                                      color: themeData
                                                          .colorScheme
                                                          .onSurfaceVariant)),
                                          Text(
                                              'vehicle.card.owner'.trParams({
                                                'value': vehicle.ownerName ??
                                                    'vehicle.value.noOwner'.tr,
                                              }),
                                              style: themeData
                                                  .textTheme.bodyMedium
                                                  ?.copyWith(
                                                      color: themeData
                                                          .colorScheme
                                                          .onSurfaceVariant)),
                                          Text(
                                              'vehicle.card.status'.trParams({
                                                'value': localizeVehicleStatus(
                                                    vehicle.currentStatus),
                                              }),
                                              style: themeData
                                                  .textTheme.bodyMedium
                                                  ?.copyWith(
                                                      color: themeData
                                                          .colorScheme
                                                          .onSurfaceVariant)),
                                        ],
                                      ),
                                      trailing: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          IconButton(
                                            icon: const Icon(Icons.edit),
                                            color:
                                                themeData.colorScheme.primary,
                                            onPressed: () =>
                                                _goToDetailPage(vehicle),
                                            tooltip: 'vehicle.action.edit'.tr,
                                          ),
                                          IconButton(
                                            icon: Icon(Icons.delete,
                                                color: themeData
                                                    .colorScheme.error),
                                            onPressed: () => _deleteVehicle(
                                                vehicle.vehicleId ?? 0,
                                                vehicle.licensePlate ?? ''),
                                            tooltip: 'vehicle.action.delete'.tr,
                                          ),
                                        ],
                                      ),
                                      onTap: () => _goToDetailPage(vehicle),
                                    ),
                                  );
                                },
                              ),
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

class AddVehiclePage extends StatefulWidget {
  final VoidCallback? onVehicleAdded;

  const AddVehiclePage({super.key, this.onVehicleAdded});

  @override
  State<AddVehiclePage> createState() => _AddVehiclePageState();
}

class _AddVehiclePageState extends State<AddVehiclePage> {
  final VehicleInformationControllerApi vehicleApi =
      VehicleInformationControllerApi();
  final UserManagementControllerApi userApi = UserManagementControllerApi();
  final DriverInformationControllerApi driverApi =
      DriverInformationControllerApi();
  final _formKey = GlobalKey<FormState>();
  final _licensePlateController = TextEditingController();
  final _vehicleTypeController = TextEditingController();
  final _ownerNameController = TextEditingController();
  final _idCardNumberController = TextEditingController();
  final _contactNumberController = TextEditingController();
  final _engineNumberController = TextEditingController();
  final _frameNumberController = TextEditingController();
  final _vehicleColorController = TextEditingController();
  final _firstRegistrationDateController = TextEditingController();
  final _currentStatusController = TextEditingController();
  DateTime? _selectedFirstRegistrationDate;
  bool _isLoading = false;

  final UserDashboardController? controller =
      Get.isRegistered<UserDashboardController>()
          ? Get.find<UserDashboardController>()
          : null;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    setState(() => _isLoading = true);
    try {
      final jwtToken = await AuthTokenStore.instance.getJwtToken();
      if (jwtToken == null) throw Exception('vehicle.error.jwtMissing'.tr);

      await vehicleApi.initializeWithJwt();
      await driverApi.initializeWithJwt();
      await userApi.initializeWithJwt();
      await _preFillForm();
    } catch (e) {
      _showSnackBar(
        'vehicle.error.initializeFailed'
            .trParams({'error': formatVehicleError(e)}),
        isError: true,
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _preFillForm() async {
    final user = await _fetchUserManagement();
    final driverInfo = await _fetchDriverInformation();
    final ownerName =
        _resolveVehicleOwnerName(driverInfo: driverInfo, user: user);
    final ownerIdCard =
        _resolveVehicleOwnerIdCard(driverInfo: driverInfo, user: user);
    final ownerContact =
        _resolveVehicleOwnerContact(driverInfo: driverInfo, user: user);

    debugPrint('Fetched UserManagement: ${user?.toJson()}');
    debugPrint('Fetched DriverInformation: ${driverInfo?.toString()}');

    if (ownerName == null) {
      throw Exception('vehicle.error.driverInfoMissingDetailed'.trParams({
        'driverId': '${user?.userId}',
        'username': user?.username ?? '',
      }));
    }
    if (ownerIdCard == null) {
      throw Exception('vehicle.error.driverIdCardMissing'.tr);
    }

    setState(() {
      _ownerNameController.text = ownerName;
      _idCardNumberController.text = ownerIdCard;
      _contactNumberController.text = ownerContact ?? '';
      debugPrint('Set ownerNameController.text to: $ownerName');
    });
  }

  Future<UserManagement?> _fetchUserManagement() async {
    try {
      await userApi.initializeWithJwt();
      return await userApi.apiUsersMeGet();
    } catch (e) {
      debugPrint('Error fetching UserManagement: $e');
      return null;
    }
  }

  Future<DriverInformation?> _fetchDriverInformation() async {
    try {
      await driverApi.initializeWithJwt();
      return await driverApi.apiDriversMeGet();
    } catch (e) {
      debugPrint('Error fetching DriverInformation: $e');
      return null;
    }
  }

  @override
  void dispose() {
    _licensePlateController.dispose();
    _vehicleTypeController.dispose();
    _ownerNameController.dispose();
    _idCardNumberController.dispose();
    _contactNumberController.dispose();
    _engineNumberController.dispose();
    _frameNumberController.dispose();
    _vehicleColorController.dispose();
    _firstRegistrationDateController.dispose();
    _currentStatusController.dispose();
    super.dispose();
  }

  void _setFirstRegistrationDate(DateTime? value) {
    _selectedFirstRegistrationDate =
        value == null ? null : DateUtils.dateOnly(value);
    _firstRegistrationDateController.text = formatVehicleDate(
      _selectedFirstRegistrationDate,
      emptyKey: 'common.none',
    );
  }

  Future<void> _submitVehicle() async {
    if (!_formKey.currentState!.validate()) return;

    final licensePlate = buildVehicleLicensePlate(_licensePlateController.text);
    if (!await ensureVehicleLicensePlateAvailable(
      vehicleApi: vehicleApi,
      licensePlate: licensePlate,
    )) {
      _showSnackBar('vehicle.error.plateExists'.tr, isError: true);
      return;
    }

    final idCardNumber = _idCardNumberController.text.trim();
    setState(() => _isLoading = true);
    try {
      final vehicle = VehicleInformation(
        vehicleId: null,
        licensePlate: licensePlate,
        vehicleType: _vehicleTypeController.text.trim(),
        ownerName: _ownerNameController.text.trim(),
        ownerIdCard: idCardNumber,
        ownerContact: _contactNumberController.text.trim().isEmpty
            ? null
            : _contactNumberController.text.trim(),
        engineNumber: _engineNumberController.text.trim().isEmpty
            ? null
            : _engineNumberController.text.trim(),
        frameNumber: _frameNumberController.text.trim().isEmpty
            ? null
            : _frameNumberController.text.trim(),
        vehicleColor: _vehicleColorController.text.trim().isEmpty
            ? null
            : _vehicleColorController.text.trim(),
        firstRegistrationDate: _selectedFirstRegistrationDate,
        status: _currentStatusController.text.trim().isEmpty
            ? 'Active'
            : _currentStatusController.text.trim(),
      );

      await vehicleApi.apiVehiclesMePost(vehicle: vehicle);

      _showSnackBar('vehicle.success.created'.tr);
      if (mounted) {
        Navigator.pop(context, true);
        widget.onVehicleAdded?.call();
      }
    } catch (e) {
      _showSnackBar(
        'vehicle.error.createFailed'.trParams({'error': formatVehicleError(e)}),
        isError: true,
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
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

  Future<void> _pickDate() async {
    final pickedDate = await showDatePicker(
      context: context,
      initialDate: _selectedFirstRegistrationDate ?? DateTime.now(),
      firstDate: DateTime(1900),
      lastDate: DateTime.now(),
      builder: (context, child) => Theme(
        data: Theme.of(context).copyWith(
          colorScheme: Theme.of(context).colorScheme.copyWith(
              primary: controller?.currentBodyTheme.value.colorScheme.primary),
        ),
        child: child!,
      ),
    );
    if (pickedDate != null && mounted) {
      setState(() => _setFirstRegistrationDate(pickedDate));
    }
  }

  Widget _buildTextField(
      String labelKey, TextEditingController controller, ThemeData themeData,
      {TextInputType? keyboardType,
      bool readOnly = false,
      VoidCallback? onTap,
      bool required = false,
      String? prefix,
      int? maxLength,
      String? Function(String?)? validator}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6.0),
      child: TextFormField(
        controller: controller,
        style: TextStyle(color: themeData.colorScheme.onSurface),
        decoration: InputDecoration(
          labelText: labelKey.tr,
          labelStyle: TextStyle(color: themeData.colorScheme.onSurfaceVariant),
          helperText: vehicleFieldHelperKey(labelKey)?.tr,
          helperStyle: TextStyle(
              color: themeData.colorScheme.onSurfaceVariant
                  .withValues(alpha: 0.6)),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12.0)),
          enabledBorder: OutlineInputBorder(
              borderSide: BorderSide(
                  color: themeData.colorScheme.outline.withValues(alpha: 0.3))),
          focusedBorder: OutlineInputBorder(
              borderSide:
                  BorderSide(color: themeData.colorScheme.primary, width: 1.5)),
          filled: true,
          fillColor: readOnly
              ? themeData.colorScheme.surfaceContainerHighest
                  .withValues(alpha: 0.5)
              : themeData.colorScheme.surfaceContainerLowest,
          prefixText: prefix,
          prefixStyle: TextStyle(
              color: themeData.colorScheme.onSurface,
              fontWeight: FontWeight.bold),
          suffixIcon: readOnly &&
                  isVehicleField(labelKey, kVehicleFieldFirstRegistrationDate)
              ? Icon(Icons.calendar_today,
                  size: 18, color: themeData.colorScheme.primary)
              : null,
          hintText: vehicleFieldHintKey(labelKey, readOnly: readOnly)?.tr,
          hintStyle: TextStyle(
              color: themeData.colorScheme.onSurfaceVariant
                  .withValues(alpha: 0.6)),
        ),
        keyboardType: keyboardType,
        readOnly: readOnly,
        onTap: onTap,
        maxLength: maxLength,
        validator: validator ??
            (value) => validateVehicleField(labelKey, value,
                required: required,
                selectedDate:
                    isVehicleField(labelKey, kVehicleFieldFirstRegistrationDate)
                        ? _selectedFirstRegistrationDate
                        : null),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final themeData = controller?.currentBodyTheme.value ?? ThemeData.light();
    final hideAppBar = widget.onVehicleAdded != null;
    return DashboardPageTemplate(
      theme: themeData,
      title: 'vehicle.add.title'.tr,
      pageType: hideAppBar ? DashboardPageType.custom : DashboardPageType.user,
      onThemeToggle: hideAppBar ? null : controller?.toggleBodyTheme,
      bodyIsScrollable: true,
      padding: EdgeInsets.zero,
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : Form(
                key: _formKey,
                child: SingleChildScrollView(
                  child: Column(
                    children: [
                      Card(
                        elevation: 3,
                        color: themeData.colorScheme.surfaceContainer,
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(16.0)),
                        child: Padding(
                          padding: const EdgeInsets.all(16.0),
                          child: Column(
                            children: [
                              if (widget.onVehicleAdded != null)
                                Text('vehicle.add.emptyPrompt'.tr,
                                    style: themeData.textTheme.titleMedium
                                        ?.copyWith(
                                            color:
                                                themeData.colorScheme.onSurface,
                                            fontWeight: FontWeight.bold)),
                              if (widget.onVehicleAdded != null)
                                const SizedBox(height: 16),
                              _buildTextField(kVehicleFieldLicensePlate,
                                  _licensePlateController, themeData,
                                  required: true,
                                  prefix: kVehiclePlatePrefix,
                                  maxLength: 17),
                              _buildTextField(kVehicleFieldType,
                                  _vehicleTypeController, themeData,
                                  required: true, maxLength: 50),
                              _buildTextField(kVehicleFieldOwnerName,
                                  _ownerNameController, themeData,
                                  required: true,
                                  readOnly: true,
                                  maxLength: 100),
                              _buildTextField(kVehicleFieldIdCard,
                                  _idCardNumberController, themeData,
                                  required: true,
                                  readOnly: true,
                                  keyboardType: TextInputType.number,
                                  maxLength: 18,
                                  validator: validateProfileBoundVehicleIdCard),
                              _buildTextField(kVehicleFieldContact,
                                  _contactNumberController, themeData,
                                  readOnly: true,
                                  keyboardType: TextInputType.phone,
                                  maxLength: 20),
                              _buildTextField(kVehicleFieldEngineNumber,
                                  _engineNumberController, themeData,
                                  maxLength: 50),
                              _buildTextField(kVehicleFieldFrameNumber,
                                  _frameNumberController, themeData,
                                  maxLength: 50),
                              _buildTextField(kVehicleFieldColor,
                                  _vehicleColorController, themeData,
                                  maxLength: 50),
                              _buildTextField(
                                  kVehicleFieldFirstRegistrationDate,
                                  _firstRegistrationDateController,
                                  themeData,
                                  readOnly: true,
                                  onTap: _pickDate),
                              _buildTextField(kVehicleFieldCurrentStatus,
                                  _currentStatusController, themeData,
                                  maxLength: 50),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 20),
                      ElevatedButton(
                        onPressed: _submitVehicle,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: themeData.colorScheme.primary,
                          foregroundColor: themeData.colorScheme.onPrimary,
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12.0)),
                          padding: const EdgeInsets.symmetric(
                              vertical: 14.0, horizontal: 20.0),
                          textStyle: themeData.textTheme.labelLarge
                              ?.copyWith(fontWeight: FontWeight.bold),
                        ),
                        child: Text('common.submit'.tr),
                      ),
                    ],
                  ),
                ),
              ),
      ),
    );
  }
}

class EditVehiclePage extends StatefulWidget {
  final VehicleInformation vehicle;

  const EditVehiclePage({super.key, required this.vehicle});

  @override
  State<EditVehiclePage> createState() => _EditVehiclePageState();
}

class _EditVehiclePageState extends State<EditVehiclePage> {
  final VehicleInformationControllerApi vehicleApi =
      VehicleInformationControllerApi();
  final UserManagementControllerApi userApi = UserManagementControllerApi();
  final DriverInformationControllerApi driverApi =
      DriverInformationControllerApi();
  final _formKey = GlobalKey<FormState>();
  final _licensePlateController = TextEditingController();
  final _vehicleTypeController = TextEditingController();
  final _ownerNameController = TextEditingController();
  final _idCardNumberController = TextEditingController();
  final _contactNumberController = TextEditingController();
  final _engineNumberController = TextEditingController();
  final _frameNumberController = TextEditingController();
  final _vehicleColorController = TextEditingController();
  final _firstRegistrationDateController = TextEditingController();
  final _currentStatusController = TextEditingController();
  DateTime? _selectedFirstRegistrationDate;
  bool _isLoading = false;

  final UserDashboardController? controller =
      Get.isRegistered<UserDashboardController>()
          ? Get.find<UserDashboardController>()
          : null;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    setState(() => _isLoading = true);
    try {
      await vehicleApi.initializeWithJwt();
      await driverApi.initializeWithJwt();
      await _initializeFields();
    } catch (e) {
      _showSnackBar(
        'vehicle.error.initializeFailed'
            .trParams({'error': formatVehicleError(e)}),
        isError: true,
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _initializeFields() async {
    final jwtToken = await AuthTokenStore.instance.getJwtToken();
    if (jwtToken == null) throw Exception('vehicle.error.jwtMissing'.tr);

    await userApi.initializeWithJwt();
    final driverInfo = await _fetchDriverInformation();
    final user = await _fetchUserManagement();
    final ownerName = _resolveVehicleOwnerName(
      driverInfo: driverInfo,
      user: user,
      vehicle: widget.vehicle,
    );
    final ownerIdCard = _resolveVehicleOwnerIdCard(
      driverInfo: driverInfo,
      user: user,
      vehicle: widget.vehicle,
    );
    final ownerContact = _resolveVehicleOwnerContact(
      driverInfo: driverInfo,
      user: user,
      vehicle: widget.vehicle,
    );

    if (ownerName == null) {
      throw Exception('vehicle.error.driverInfoMissing'.tr);
    }
    if (ownerIdCard == null) {
      throw Exception('vehicle.error.driverIdCardMissing'.tr);
    }

    setState(() {
      _licensePlateController.text =
          widget.vehicle.licensePlate?.replaceFirst(kVehiclePlatePrefix, '') ??
              '';
      _vehicleTypeController.text = widget.vehicle.vehicleType ?? '';
      _ownerNameController.text = ownerName;
      _idCardNumberController.text = ownerIdCard;
      _contactNumberController.text = ownerContact ?? '';
      _engineNumberController.text = widget.vehicle.engineNumber ?? '';
      _frameNumberController.text = widget.vehicle.frameNumber ?? '';
      _vehicleColorController.text = widget.vehicle.vehicleColor ?? '';
      _setFirstRegistrationDate(widget.vehicle.firstRegistrationDate);
      _currentStatusController.text = widget.vehicle.currentStatus ?? '';
    });
  }

  Future<DriverInformation?> _fetchDriverInformation() async {
    try {
      await driverApi.initializeWithJwt();
      return await driverApi.apiDriversMeGet();
    } catch (e) {
      debugPrint('Failed to fetch DriverInformation: $e');
      return null;
    }
  }

  Future<UserManagement?> _fetchUserManagement() async {
    try {
      await userApi.initializeWithJwt();
      return await userApi.apiUsersMeGet();
    } catch (e) {
      debugPrint('Failed to fetch UserManagement: $e');
      return null;
    }
  }

  @override
  void dispose() {
    _licensePlateController.dispose();
    _vehicleTypeController.dispose();
    _ownerNameController.dispose();
    _idCardNumberController.dispose();
    _contactNumberController.dispose();
    _engineNumberController.dispose();
    _frameNumberController.dispose();
    _vehicleColorController.dispose();
    _firstRegistrationDateController.dispose();
    _currentStatusController.dispose();
    super.dispose();
  }

  void _setFirstRegistrationDate(DateTime? value) {
    _selectedFirstRegistrationDate =
        value == null ? null : DateUtils.dateOnly(value);
    _firstRegistrationDateController.text = formatVehicleDate(
      _selectedFirstRegistrationDate,
      emptyKey: 'common.none',
    );
  }

  Future<void> _submitVehicle() async {
    if (!_formKey.currentState!.validate()) return;

    final newLicensePlate =
        buildVehicleLicensePlate(_licensePlateController.text);
    if (!await ensureVehicleLicensePlateAvailable(
      vehicleApi: vehicleApi,
      licensePlate: newLicensePlate,
      currentLicensePlate: widget.vehicle.licensePlate,
    )) {
      _showSnackBar('vehicle.error.plateExists'.tr, isError: true);
      return;
    }

    setState(() => _isLoading = true);
    try {
      final vehicle = VehicleInformation(
        vehicleId: widget.vehicle.vehicleId,
        licensePlate: newLicensePlate,
        vehicleType: _vehicleTypeController.text.trim(),
        ownerName: _ownerNameController.text.trim(),
        ownerIdCard: _idCardNumberController.text.trim(),
        ownerContact: _contactNumberController.text.trim().isEmpty
            ? null
            : _contactNumberController.text.trim(),
        engineNumber: _engineNumberController.text.trim().isEmpty
            ? null
            : _engineNumberController.text.trim(),
        frameNumber: _frameNumberController.text.trim().isEmpty
            ? null
            : _frameNumberController.text.trim(),
        vehicleColor: _vehicleColorController.text.trim().isEmpty
            ? null
            : _vehicleColorController.text.trim(),
        firstRegistrationDate: _selectedFirstRegistrationDate,
        status: _currentStatusController.text.trim().isEmpty
            ? 'Active'
            : _currentStatusController.text.trim(),
      );

      await vehicleApi.apiVehiclesMeVehicleIdPut(
        vehicleId: widget.vehicle.vehicleId ?? 0,
        vehicle: vehicle,
      );

      _showSnackBar('vehicle.success.updated'.tr);
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      _showSnackBar(
        'vehicle.error.updateFailed'.trParams({'error': formatVehicleError(e)}),
        isError: true,
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
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

  Future<void> _pickDate() async {
    final pickedDate = await showDatePicker(
      context: context,
      initialDate: _selectedFirstRegistrationDate ??
          widget.vehicle.firstRegistrationDate ??
          DateTime.now(),
      firstDate: DateTime(1900),
      lastDate: DateTime.now(),
      builder: (context, child) => Theme(
        data: Theme.of(context).copyWith(
          colorScheme: Theme.of(context).colorScheme.copyWith(
              primary: controller?.currentBodyTheme.value.colorScheme.primary),
        ),
        child: child!,
      ),
    );
    if (pickedDate != null && mounted) {
      setState(() => _setFirstRegistrationDate(pickedDate));
    }
  }

  Widget _buildTextField(
      String labelKey, TextEditingController controller, ThemeData themeData,
      {TextInputType? keyboardType,
      bool readOnly = false,
      VoidCallback? onTap,
      bool required = false,
      String? prefix,
      int? maxLength,
      String? Function(String?)? validator}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6.0),
      child: TextFormField(
        controller: controller,
        style: TextStyle(color: themeData.colorScheme.onSurface),
        decoration: InputDecoration(
          labelText: labelKey.tr,
          labelStyle: TextStyle(color: themeData.colorScheme.onSurfaceVariant),
          helperText: vehicleFieldHelperKey(labelKey)?.tr,
          helperStyle: TextStyle(
              color: themeData.colorScheme.onSurfaceVariant
                  .withValues(alpha: 0.6)),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12.0)),
          enabledBorder: OutlineInputBorder(
              borderSide: BorderSide(
                  color: themeData.colorScheme.outline.withValues(alpha: 0.3))),
          focusedBorder: OutlineInputBorder(
              borderSide:
                  BorderSide(color: themeData.colorScheme.primary, width: 1.5)),
          filled: true,
          fillColor: readOnly
              ? themeData.colorScheme.surfaceContainerHighest
                  .withValues(alpha: 0.5)
              : themeData.colorScheme.surfaceContainerLowest,
          prefixText: prefix,
          prefixStyle: TextStyle(
              color: themeData.colorScheme.onSurface,
              fontWeight: FontWeight.bold),
          suffixIcon: readOnly &&
                  isVehicleField(labelKey, kVehicleFieldFirstRegistrationDate)
              ? Icon(Icons.calendar_today,
                  size: 18, color: themeData.colorScheme.primary)
              : null,
          hintText: vehicleFieldHintKey(labelKey, readOnly: readOnly)?.tr,
          hintStyle: TextStyle(
              color: themeData.colorScheme.onSurfaceVariant
                  .withValues(alpha: 0.6)),
        ),
        keyboardType: keyboardType,
        readOnly: readOnly,
        onTap: onTap,
        maxLength: maxLength,
        validator: validator ??
            (value) => validateVehicleField(labelKey, value,
                required: required,
                selectedDate:
                    isVehicleField(labelKey, kVehicleFieldFirstRegistrationDate)
                        ? _selectedFirstRegistrationDate
                        : null),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final themeData = controller?.currentBodyTheme.value ?? ThemeData.light();
    return DashboardPageTemplate(
      theme: themeData,
      title: 'vehicle.edit.title'.tr,
      pageType: DashboardPageType.user,
      onThemeToggle: controller?.toggleBodyTheme,
      bodyIsScrollable: true,
      padding: EdgeInsets.zero,
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : Form(
                key: _formKey,
                child: SingleChildScrollView(
                  child: Column(
                    children: [
                      Card(
                        elevation: 3,
                        color: themeData.colorScheme.surfaceContainer,
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(16.0)),
                        child: Padding(
                          padding: const EdgeInsets.all(16.0),
                          child: Column(
                            children: [
                              _buildTextField(kVehicleFieldLicensePlate,
                                  _licensePlateController, themeData,
                                  required: true,
                                  prefix: kVehiclePlatePrefix,
                                  maxLength: 17),
                              _buildTextField(kVehicleFieldType,
                                  _vehicleTypeController, themeData,
                                  required: true, maxLength: 50),
                              _buildTextField(kVehicleFieldOwnerName,
                                  _ownerNameController, themeData,
                                  required: true,
                                  readOnly: true,
                                  maxLength: 100),
                              _buildTextField(kVehicleFieldIdCard,
                                  _idCardNumberController, themeData,
                                  required: true,
                                  readOnly: true,
                                  keyboardType: TextInputType.number,
                                  maxLength: 18,
                                  validator: validateProfileBoundVehicleIdCard),
                              _buildTextField(kVehicleFieldContact,
                                  _contactNumberController, themeData,
                                  readOnly: true,
                                  keyboardType: TextInputType.phone,
                                  maxLength: 20),
                              _buildTextField(kVehicleFieldEngineNumber,
                                  _engineNumberController, themeData,
                                  maxLength: 50),
                              _buildTextField(kVehicleFieldFrameNumber,
                                  _frameNumberController, themeData,
                                  maxLength: 50),
                              _buildTextField(kVehicleFieldColor,
                                  _vehicleColorController, themeData,
                                  maxLength: 50),
                              _buildTextField(
                                  kVehicleFieldFirstRegistrationDate,
                                  _firstRegistrationDateController,
                                  themeData,
                                  readOnly: true,
                                  onTap: _pickDate),
                              _buildTextField(kVehicleFieldCurrentStatus,
                                  _currentStatusController, themeData,
                                  maxLength: 50),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 20),
                      ElevatedButton(
                        onPressed: _submitVehicle,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: themeData.colorScheme.primary,
                          foregroundColor: themeData.colorScheme.onPrimary,
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12.0)),
                          padding: const EdgeInsets.symmetric(
                              vertical: 14.0, horizontal: 20.0),
                          textStyle: themeData.textTheme.labelLarge
                              ?.copyWith(fontWeight: FontWeight.bold),
                        ),
                        child: Text('common.save'.tr),
                      ),
                    ],
                  ),
                ),
              ),
      ),
    );
  }
}

class VehicleDetailPage extends StatefulWidget {
  final VehicleInformation vehicle;

  const VehicleDetailPage({super.key, required this.vehicle});

  @override
  State<VehicleDetailPage> createState() => _VehicleDetailPageState();
}

class _VehicleDetailPageState extends State<VehicleDetailPage> {
  final VehicleInformationControllerApi vehicleApi =
      VehicleInformationControllerApi();
  final UserManagementControllerApi userApi = UserManagementControllerApi();
  final DriverInformationControllerApi driverApi =
      DriverInformationControllerApi();
  bool _isLoading = false;
  bool _isEditable = false;
  String _errorMessage = '';
  String? _currentDriverIdCardNumber;

  final UserDashboardController? controller =
      Get.isRegistered<UserDashboardController>()
          ? Get.find<UserDashboardController>()
          : null;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    setState(() => _isLoading = true);
    try {
      final jwtToken = await AuthTokenStore.instance.getJwtToken();
      if (jwtToken == null) {
        throw Exception('vehicle.error.jwtMissingRelogin'.tr);
      }

      await vehicleApi.initializeWithJwt();
      await driverApi.initializeWithJwt();
      await userApi.initializeWithJwt();
      final user = await _fetchUserManagement();
      final driverInfo = await _fetchDriverInformation();
      _currentDriverIdCardNumber = _resolveVehicleOwnerIdCard(
        driverInfo: driverInfo,
        user: user,
      );
      await _checkUserRole();
    } catch (e) {
      setState(() => _errorMessage = 'vehicle.error.initializeFailed'
          .trParams({'error': formatVehicleError(e)}));
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<DriverInformation?> _fetchDriverInformation() async {
    try {
      await driverApi.initializeWithJwt();
      return await driverApi.apiDriversMeGet();
    } catch (e) {
      debugPrint('Failed to fetch DriverInformation: $e');
      return null;
    }
  }

  Future<UserManagement?> _fetchUserManagement() async {
    try {
      await userApi.initializeWithJwt();
      return await userApi.apiUsersMeGet();
    } catch (e) {
      debugPrint('Failed to fetch UserManagement: $e');
      return null;
    }
  }

  Future<void> _checkUserRole() async {
    try {
      final jwtToken = await AuthTokenStore.instance.getJwtToken();
      if (jwtToken == null) {
        throw Exception('vehicle.error.jwtMissingRelogin'.tr);
      }
      final decodedToken = JwtDecoder.decode(jwtToken);
      final roles = decodedToken['roles'];
      setState(() {
        _isEditable = hasAnyRole(roles, const ['SUPER_ADMIN', 'ADMIN']) ||
            (_currentDriverIdCardNumber != null &&
                _currentDriverIdCardNumber == widget.vehicle.idCardNumber);
      });
    } catch (e) {
      setState(() => _errorMessage = 'vehicle.error.permissionLoadFailed'
          .trParams({'error': formatVehicleError(e)}));
    }
  }

  Future<void> _deleteVehicle(int vehicleId) async {
    setState(() => _isLoading = true);
    try {
      await vehicleApi.apiVehiclesMeVehicleIdDelete(vehicleId: vehicleId);
      _showSnackBar('vehicle.success.deleted'.tr);
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      _showSnackBar(
        'vehicle.error.deleteFailed'.trParams({'error': formatVehicleError(e)}),
        isError: true,
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
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

  Widget _buildDetailRow(String label, String value, ThemeData themeData) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('common.labelWithColon'.trParams({'label': label}),
              style: themeData.textTheme.bodyLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: themeData.colorScheme.onSurface)),
          Expanded(
              child: Text(value,
                  style: themeData.textTheme.bodyMedium?.copyWith(
                      color: themeData.colorScheme.onSurfaceVariant))),
        ],
      ),
    );
  }

  void _showDeleteConfirmationDialog(String action, VoidCallback onConfirm) {
    showDialog(
      context: context,
      builder: (ctx) {
        final themeData =
            controller?.currentBodyTheme.value ?? ThemeData.light();
        return AlertDialog(
          backgroundColor: themeData.colorScheme.surfaceContainerHighest,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: Text('vehicle.dialog.deleteTitle'.tr,
              style: themeData.textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: themeData.colorScheme.onSurface)),
          content: Text(
              'vehicle.dialog.deleteConfirm'.trParams({'action': action}),
              style: themeData.textTheme.bodyMedium
                  ?.copyWith(color: themeData.colorScheme.onSurfaceVariant)),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: Text('common.cancel'.tr,
                  style: themeData.textTheme.labelLarge?.copyWith(
                      color: themeData.colorScheme.onSurfaceVariant,
                      fontWeight: FontWeight.w600)),
            ),
            ElevatedButton(
              onPressed: () {
                onConfirm();
                Navigator.pop(ctx);
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: themeData.colorScheme.error,
                foregroundColor: themeData.colorScheme.onError,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12)),
                padding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              ),
              child: Text('vehicle.action.delete'.tr),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final themeData = controller?.currentBodyTheme.value ?? ThemeData.light();
    if (_errorMessage.isNotEmpty) {
      return DashboardPageTemplate(
        theme: themeData,
        title: 'vehicle.detail.title'.tr,
        pageType: DashboardPageType.custom,
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(_errorMessage,
                  style: themeData.textTheme.titleMedium?.copyWith(
                      color: themeData.colorScheme.error,
                      fontWeight: FontWeight.w500),
                  textAlign: TextAlign.center),
              if (shouldShowVehicleUserReloginAction(_errorMessage))
                Padding(
                  padding: const EdgeInsets.only(top: 16.0),
                  child: ElevatedButton(
                    onPressed: () =>
                        Navigator.pushReplacementNamed(context, '/login'),
                    style: ElevatedButton.styleFrom(
                        backgroundColor: themeData.colorScheme.primary,
                        foregroundColor: themeData.colorScheme.onPrimary),
                    child: Text('vehicle.action.goLogin'.tr),
                  ),
                ),
            ],
          ),
        ),
      );
    }

    final actions = <DashboardPageBarAction>[];
    if (_isEditable) {
      actions.addAll([
        DashboardPageBarAction(
          icon: Icons.edit,
          tooltip: 'vehicle.detail.editTooltip'.tr,
          onPressed: () {
            Navigator.push(
                    context,
                    MaterialPageRoute(
                        builder: (context) =>
                            EditVehiclePage(vehicle: widget.vehicle)))
                .then((value) {
              if (value == true && mounted) {
                Navigator.pop(context, true);
              }
            });
          },
        ),
        DashboardPageBarAction(
          icon: Icons.delete,
          color: themeData.colorScheme.error,
          tooltip: 'vehicle.detail.deleteTooltip'.tr,
          onPressed: () => _showDeleteConfirmationDialog(
              'vehicle.action.delete'.tr,
              () => _deleteVehicle(widget.vehicle.vehicleId ?? 0)),
        ),
      ]);
    }

    return DashboardPageTemplate(
      theme: themeData,
      title: 'vehicle.detail.title'.tr,
      pageType: DashboardPageType.user,
      onThemeToggle: controller?.toggleBodyTheme,
      actions: actions,
      bodyIsScrollable: true,
      padding: EdgeInsets.zero,
      body: _isLoading
          ? Center(
              child: CircularProgressIndicator(
                  valueColor:
                      AlwaysStoppedAnimation(themeData.colorScheme.primary)))
          : Padding(
              padding: const EdgeInsets.all(16.0),
              child: Card(
                elevation: 3,
                color: themeData.colorScheme.surfaceContainer,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16.0)),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: SingleChildScrollView(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildDetailRow(
                            'vehicle.detail.type'.tr,
                            widget.vehicle.vehicleType ??
                                'vehicle.value.noType'.tr,
                            themeData),
                        _buildDetailRow(
                            'vehicle.detail.plate'.tr,
                            widget.vehicle.licensePlate ??
                                'vehicle.value.noPlate'.tr,
                            themeData),
                        _buildDetailRow(
                            'vehicle.detail.owner'.tr,
                            widget.vehicle.ownerName ??
                                'vehicle.value.noOwner'.tr,
                            themeData),
                        _buildDetailRow(
                            'vehicle.detail.status'.tr,
                            localizeVehicleStatus(widget.vehicle.currentStatus),
                            themeData),
                        _buildDetailRow(
                            'vehicle.detail.idCard'.tr,
                            widget.vehicle.idCardNumber ?? 'common.none'.tr,
                            themeData),
                        _buildDetailRow(
                            'vehicle.detail.contact'.tr,
                            widget.vehicle.contactNumber ?? 'common.none'.tr,
                            themeData),
                        _buildDetailRow(
                            'vehicle.detail.engine'.tr,
                            widget.vehicle.engineNumber ?? 'common.none'.tr,
                            themeData),
                        _buildDetailRow(
                            'vehicle.detail.frame'.tr,
                            widget.vehicle.frameNumber ?? 'common.none'.tr,
                            themeData),
                        _buildDetailRow(
                            'vehicle.detail.color'.tr,
                            widget.vehicle.vehicleColor ?? 'common.none'.tr,
                            themeData),
                        _buildDetailRow(
                            'vehicle.detail.firstRegistrationDate'.tr,
                            formatVehicleDate(
                              widget.vehicle.firstRegistrationDate,
                              emptyKey: 'common.none',
                            ),
                            themeData),
                      ],
                    ),
                  ),
                ),
              ),
            ),
    );
  }
}
