import 'package:final_assignment_front/features/api/backup_restore_controller_api.dart';
import 'package:final_assignment_front/features/dashboard/controllers/admin_dashboard_controller.dart';
import 'package:final_assignment_front/features/dashboard/views/shared/widgets/dashboard_page_template.dart';
import 'package:final_assignment_front/features/model/backup_restore.dart';
import 'package:final_assignment_front/i18n/backup_restore_localizers.dart';
import 'package:final_assignment_front/i18n/status_localizers.dart';
import 'package:final_assignment_front/utils/helpers/role_utils.dart';
import 'package:final_assignment_front/utils/services/auth_token_store.dart';
import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:jwt_decoder/jwt_decoder.dart';
import 'package:uuid/uuid.dart';

String generateIdempotencyKey() => const Uuid().v4();

class BackupAndRestore extends StatefulWidget {
  const BackupAndRestore({super.key});

  @override
  State<BackupAndRestore> createState() => _BackupAndRestoreState();
}

class _BackupAndRestoreState extends State<BackupAndRestore> {
  static const int _pageSize = 20;
  static const String _searchTypeAll = 'all';
  static const String _searchTypeFileName = 'filename';
  static const String _searchTypeBackupTime = 'backupTime';
  static const String _searchTypeRestoreTime = 'restoreTime';
  static const String _searchTypeBackupType = 'backupType';
  static const String _searchTypeHandler = 'handler';
  static const String _searchTypeStatus = 'status';
  static const String _searchTypeRestoreStatus = 'restoreStatus';

  final BackupRestoreControllerApi backupApi = BackupRestoreControllerApi();
  final DashboardController controller = Get.find<DashboardController>();
  final ScrollController _scrollController = ScrollController();
  final List<BackupRestore> _backups = [];
  List<BackupRestore> _filteredBackups = [];
  bool _apiInitialized = false;
  bool _isLoading = true;
  bool _isAdmin = false;
  String _errorMessage = '';
  String _activeSearchType = _searchTypeAll;
  String _selectedSearchType = _searchTypeAll;
  String _activeQuery = '';
  int _currentPage = 1;
  bool _hasMore = true;
  DateTime? _selectedSearchDate;
  String _selectedStatusFilter = '';
  String _selectedRestoreStatusFilter = '';
  final TextEditingController _searchValueController = TextEditingController();
  final TextEditingController _searchDateController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _initialize();
    _scrollController.addListener(() {
      if (_scrollController.position.pixels >=
              _scrollController.position.maxScrollExtent - 200 &&
          _hasMore &&
          !_isLoading) {
        _loadBackups();
      }
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _searchValueController.dispose();
    _searchDateController.dispose();
    super.dispose();
  }

  Future<void> _initialize() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });
    try {
      if (!await _ensureApiInitialized()) {
        setState(() {
          _errorMessage = 'backupRestore.error.notLoggedIn'.tr;
          _isLoading = false;
        });
        return;
      }
      final jwtToken = await AuthTokenStore.instance.getJwtToken();
      if (jwtToken == null || jwtToken.isEmpty) {
        throw Exception('backupRestore.error.notLoggedIn'.tr);
      }
      final roles = _extractRoles(jwtToken);
      final isAdmin = hasAnyRole(roles, const ['SUPER_ADMIN', 'ADMIN']);
      if (!isAdmin) {
        setState(() {
          _isAdmin = false;
          _errorMessage = 'backupRestore.error.adminOnly'.tr;
          _isLoading = false;
        });
        return;
      }
      setState(() => _isAdmin = true);
      await _loadBackups();
    } catch (e) {
      setState(() {
        _errorMessage = 'backupRestore.error.initFailed'
            .trParams({'error': formatBackupRestoreError(e)});
        _isLoading = false;
      });
    }
  }

  Future<bool> _ensureApiInitialized() async {
    if (_apiInitialized) return true;
    try {
      await backupApi.initializeWithJwt();
      _apiInitialized = true;
      return true;
    } catch (_) {
      return false;
    }
  }

  List<String> _extractRoles(String jwtToken) {
    final decoded = JwtDecoder.decode(jwtToken);
    return normalizeRoleCodes(decoded['roles']);
  }

  Future<void> _loadBackups({
    bool reset = false,
    String? searchType,
    String? query,
  }) async {
    if (!_isAdmin) {
      setState(() => _isLoading = false);
      return;
    }
    if (reset) {
      _currentPage = 1;
      _hasMore = true;
      _activeSearchType = searchType ?? _resolveSearchType();
      _activeQuery = (query ?? _resolveQuery()).trim();
      _backups.clear();
      _filteredBackups.clear();
    }
    if (!reset && (_isLoading || !_hasMore)) {
      return;
    }
    if (!await _ensureApiInitialized()) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'backupRestore.error.notLoggedIn'.tr;
      });
      return;
    }
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    try {
      final backups = await _loadBackupPage(page: _currentPage);
      setState(() {
        _backups.addAll(backups);
        _filteredBackups = List<BackupRestore>.from(_backups);
        _hasMore = backups.length == _pageSize;
        _currentPage++;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'backupRestore.error.loadFailed'
            .trParams({'error': formatBackupRestoreError(e)});
        _filteredBackups = [];
      });
    }
  }

  Future<List<BackupRestore>> _loadBackupPage({required int page}) {
    if (_activeSearchType == _searchTypeBackupTime &&
        _selectedSearchDate != null) {
      final start = DateTime(
        _selectedSearchDate!.year,
        _selectedSearchDate!.month,
        _selectedSearchDate!.day,
      );
      final end = start.add(const Duration(days: 1));
      return backupApi.apiSystemBackupSearchBackupTimeRangeGet(
        startTime: start.toIso8601String(),
        endTime: end.toIso8601String(),
        page: page,
        size: _pageSize,
      );
    }
    if (_activeSearchType == _searchTypeRestoreTime &&
        _selectedSearchDate != null) {
      final start = DateTime(
        _selectedSearchDate!.year,
        _selectedSearchDate!.month,
        _selectedSearchDate!.day,
      );
      final end = start.add(const Duration(days: 1));
      return backupApi.apiSystemBackupSearchRestoreTimeRangeGet(
        startTime: start.toIso8601String(),
        endTime: end.toIso8601String(),
        page: page,
        size: _pageSize,
      );
    }
    if (_activeSearchType == _searchTypeFileName && _activeQuery.isNotEmpty) {
      return backupApi.apiSystemBackupSearchFileNameGet(
        backupFileName: _activeQuery,
        page: page,
        size: _pageSize,
      );
    }
    if (_activeSearchType == _searchTypeBackupType && _activeQuery.isNotEmpty) {
      return backupApi.apiSystemBackupSearchTypeGet(
        backupType: _activeQuery,
        page: page,
        size: _pageSize,
      );
    }
    if (_activeSearchType == _searchTypeHandler && _activeQuery.isNotEmpty) {
      return backupApi.apiSystemBackupSearchHandlerGet(
        backupHandler: _activeQuery,
        page: page,
        size: _pageSize,
      );
    }
    if (_activeSearchType == _searchTypeStatus && _activeQuery.isNotEmpty) {
      return backupApi.apiSystemBackupSearchStatusGet(
        status: _activeQuery,
        page: page,
        size: _pageSize,
      );
    }
    if (_activeSearchType == _searchTypeRestoreStatus &&
        _activeQuery.isNotEmpty) {
      return backupApi.apiSystemBackupSearchRestoreStatusGet(
        restoreStatus: _activeQuery,
        page: page,
        size: _pageSize,
      );
    }
    return backupApi.apiSystemBackupGet(page: page, size: _pageSize);
  }

  String _resolveSearchType() {
    return _selectedSearchType;
  }

  String _resolveQuery() {
    switch (_selectedSearchType) {
      case _searchTypeBackupTime:
      case _searchTypeRestoreTime:
        return _searchDateController.text.trim();
      case _searchTypeStatus:
        return _selectedStatusFilter;
      case _searchTypeRestoreStatus:
        return _selectedRestoreStatusFilter;
      case _searchTypeFileName:
      case _searchTypeBackupType:
      case _searchTypeHandler:
        return _searchValueController.text.trim();
      default:
        return '';
    }
  }

  Future<void> _searchBackups() async {
    final query = _resolveQuery().trim();
    final searchType = (_selectedSearchType == _searchTypeAll || query.isEmpty)
        ? _searchTypeAll
        : _selectedSearchType;
    await _loadBackups(
      reset: true,
      searchType: searchType,
      query: searchType == _searchTypeAll ? '' : query,
    );
  }

  Future<void> _refreshBackups() async {
    await _loadBackups(
      reset: true,
      searchType: _activeSearchType,
      query: _activeQuery,
    );
  }

  void _resetSearchFilters() {
    setState(() {
      _selectedSearchType = _searchTypeAll;
      _activeSearchType = _searchTypeAll;
      _activeQuery = '';
      _selectedSearchDate = null;
      _selectedStatusFilter = '';
      _selectedRestoreStatusFilter = '';
      _searchValueController.clear();
      _searchDateController.clear();
    });
    _loadBackups(reset: true, searchType: _searchTypeAll, query: '');
  }

  void _onSearchTypeChanged(String? value) {
    setState(() {
      _selectedSearchType = value ?? _searchTypeAll;
      _selectedSearchDate = null;
      _selectedStatusFilter = '';
      _selectedRestoreStatusFilter = '';
      _searchValueController.clear();
      _searchDateController.clear();
    });
  }

  String _searchTypeLabel(String type) {
    switch (type) {
      case _searchTypeFileName:
        return 'backupRestore.search.type.fileName'.tr;
      case _searchTypeBackupTime:
        return 'backupRestore.search.type.backupTime'.tr;
      case _searchTypeRestoreTime:
        return 'backupRestore.search.type.restoreTime'.tr;
      case _searchTypeBackupType:
        return 'backupRestore.search.type.backupType'.tr;
      case _searchTypeHandler:
        return 'backupRestore.search.type.handler'.tr;
      case _searchTypeStatus:
        return 'backupRestore.search.type.status'.tr;
      case _searchTypeRestoreStatus:
        return 'backupRestore.search.type.restoreStatus'.tr;
      case _searchTypeAll:
      default:
        return 'backupRestore.search.type.all'.tr;
    }
  }

  String _statusOptionLabel(String? value) {
    final normalized = value?.trim() ?? '';
    if (normalized.isEmpty) {
      return 'backupRestore.search.allStatuses'.tr;
    }
    return localizeBackupRestoreStatus(normalized);
  }

  Future<void> _pickSearchDate() async {
    final pickedDate = await showDatePicker(
      context: context,
      initialDate: _selectedSearchDate ?? DateTime.now(),
      firstDate: DateTime(2000),
      lastDate: DateTime(2101),
    );
    if (pickedDate == null) return;
    setState(() {
      _selectedSearchDate = pickedDate;
      _searchDateController.text = formatBackupDate(pickedDate);
    });
  }

  Future<void> _createBackup() async {
    if (!mounted || !_isAdmin) return;

    final scaffoldMessenger = ScaffoldMessenger.of(context);
    if (!await _ensureApiInitialized()) {
      scaffoldMessenger.showSnackBar(
        SnackBar(content: Text('backupRestore.error.notLoggedIn'.tr)),
      );
      return;
    }

    try {
      final backupName =
          'backup_${DateTime.now().millisecondsSinceEpoch.toString()}';
      final idempotencyKey = generateIdempotencyKey();

      final newBackup = BackupRestore(
        backupType: 'MANUAL',
        backupFileName: backupName,
        backupTime: DateTime.now(),
        remarks: 'backupRestore.value.manualCreatedRemarks'.tr,
        status: 'PENDING',
        idempotencyKey: idempotencyKey,
      );

      await backupApi.apiSystemBackupPost(
        backupRestore: newBackup,
        idempotencyKey: idempotencyKey,
      );

      scaffoldMessenger.showSnackBar(
        SnackBar(content: Text('backupRestore.success.created'.tr)),
      );
      await _refreshBackups();
    } catch (e) {
      scaffoldMessenger.showSnackBar(
        SnackBar(
          content: Text(
            'backupRestore.error.createFailed'
                .trParams({'error': formatBackupRestoreError(e)}),
          ),
        ),
      );
    }
  }

  Future<void> _updateBackup(int backupId, BackupRestore updatedBackup) async {
    if (!mounted || !_isAdmin) return;

    final scaffoldMessenger = ScaffoldMessenger.of(context);
    if (!await _ensureApiInitialized()) {
      scaffoldMessenger.showSnackBar(
        SnackBar(content: Text('backupRestore.error.notLoggedIn'.tr)),
      );
      return;
    }

    try {
      final idempotencyKey = generateIdempotencyKey();
      final payload = updatedBackup.copyWith(idempotencyKey: idempotencyKey);
      await backupApi.apiSystemBackupBackupIdPut(
        backupId: backupId,
        backupRestore: payload,
        idempotencyKey: idempotencyKey,
      );
      scaffoldMessenger.showSnackBar(
        SnackBar(content: Text('backupRestore.success.updated'.tr)),
      );
      await _refreshBackups();
    } catch (e) {
      scaffoldMessenger.showSnackBar(
        SnackBar(
          content: Text(
            'backupRestore.error.updateFailed'
                .trParams({'error': formatBackupRestoreError(e)}),
          ),
        ),
      );
    }
  }

  Future<void> _restoreBackup(BackupRestore backup) async {
    if (!mounted || !_isAdmin || backup.backupId == null) return;

    final scaffoldMessenger = ScaffoldMessenger.of(context);
    if (!await _ensureApiInitialized()) {
      scaffoldMessenger.showSnackBar(
        SnackBar(content: Text('backupRestore.error.notLoggedIn'.tr)),
      );
      return;
    }

    try {
      final idempotencyKey = generateIdempotencyKey();
      final payload = backup.copyWith(
        restoreTime: DateTime.now(),
        restoreStatus: 'RESTORED',
        status: 'RESTORED',
        idempotencyKey: idempotencyKey,
      );
      await backupApi.apiSystemBackupBackupIdPut(
        backupId: backup.backupId!,
        backupRestore: payload,
        idempotencyKey: idempotencyKey,
      );
      scaffoldMessenger.showSnackBar(
        SnackBar(content: Text('backupRestore.success.restored'.tr)),
      );
      await _refreshBackups();
    } catch (e) {
      scaffoldMessenger.showSnackBar(
        SnackBar(
          content: Text(
            'backupRestore.error.restoreFailed'
                .trParams({'error': formatBackupRestoreError(e)}),
          ),
        ),
      );
    }
  }

  Future<void> _deleteBackup(int backupId) async {
    if (!mounted || !_isAdmin) return;

    final scaffoldMessenger = ScaffoldMessenger.of(context);
    if (!await _ensureApiInitialized()) {
      scaffoldMessenger.showSnackBar(
        SnackBar(content: Text('backupRestore.error.notLoggedIn'.tr)),
      );
      return;
    }

    try {
      await backupApi.apiSystemBackupBackupIdDelete(backupId: backupId);
      scaffoldMessenger.showSnackBar(
        SnackBar(content: Text('backupRestore.success.deleted'.tr)),
      );
      await _refreshBackups();
    } catch (e) {
      scaffoldMessenger.showSnackBar(
        SnackBar(
          content: Text(
            'backupRestore.error.deleteFailed'
                .trParams({'error': formatBackupRestoreError(e)}),
          ),
        ),
      );
    }
  }

  void _goToDetailPage(BackupRestore backup) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => BackupDetailPage(backup: backup),
      ),
    ).then((value) {
      if (value == true && mounted) {
        _refreshBackups();
      }
    });
  }

  void _showUpdateBackupDialog(BackupRestore backup) {
    final TextEditingController fileNameController =
        TextEditingController(text: backup.backupFileName ?? '');
    final TextEditingController remarksController =
        TextEditingController(text: backup.remarks ?? '');
    final formKey = GlobalKey<FormState>();
    var autovalidateMode = AutovalidateMode.disabled;
    StateSetter? updateDialogState;

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('backupRestore.dialog.editTitle'.tr),
        content: StatefulBuilder(
          builder: (context, setState) {
            updateDialogState = setState;
            return Form(
              key: formKey,
              autovalidateMode: autovalidateMode,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextFormField(
                      controller: fileNameController,
                      maxLength: 255,
                      autofocus: true,
                      decoration: InputDecoration(
                        labelText: 'backupRestore.field.fileName'.tr,
                      ),
                      validator: (value) => validateBackupRestoreField(
                        'fileName',
                        value: value,
                        required: true,
                      ),
                    ),
                    TextFormField(
                      controller: remarksController,
                      maxLength: 500,
                      decoration: InputDecoration(
                        labelText: 'backupRestore.field.remarks'.tr,
                      ),
                      maxLines: 3,
                      validator: (value) => validateBackupRestoreField(
                        'remarks',
                        value: value,
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text('common.cancel'.tr),
          ),
          ElevatedButton(
            onPressed: () {
              final isValid = formKey.currentState?.validate() ?? false;
              if (!isValid) {
                updateDialogState?.call(() {
                  autovalidateMode = AutovalidateMode.onUserInteraction;
                });
                return;
              }
              final String fileName = fileNameController.text.trim();
              final String remarks = remarksController.text.trim();

              final updatedBackup = backup.copyWith(
                backupFileName: fileName,
                remarks: remarks,
              );

              _updateBackup(backup.backupId!, updatedBackup);
              Navigator.pop(ctx);
            },
            child: Text('common.save'.tr),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (!_isAdmin) {
      return DashboardPageTemplate(
        theme: controller.currentBodyTheme.value,
        title: 'backupRestore.page.title'.tr,
        pageType: DashboardPageType.admin,
        isLoading: _isLoading,
        errorMessage: _errorMessage.isNotEmpty
            ? _errorMessage
            : 'backupRestore.error.adminOnly'.tr,
        body: const SizedBox.shrink(),
      );
    }

    return Obx(() {
      final themeData = controller.currentBodyTheme.value;
      final bool isLight = themeData.brightness == Brightness.light;
      return DashboardPageTemplate(
        theme: themeData,
        title: 'backupRestore.page.title'.tr,
        pageType: DashboardPageType.admin,
        bodyIsScrollable: true,
        padding: EdgeInsets.zero,
        actions: [
          DashboardPageBarAction(
            icon: Icons.add,
            onPressed: _createBackup,
            tooltip: 'backupRestore.action.create'.tr,
          ),
        ],
        body: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            children: [
              Card(
                margin: EdgeInsets.zero,
                elevation: 2,
                color: isLight ? Colors.white : Colors.grey[850],
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    children: [
                      DropdownButtonFormField<String>(
                        initialValue: _selectedSearchType,
                        decoration: InputDecoration(
                          labelText: 'backupRestore.search.filterType'.tr,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8.0),
                          ),
                        ),
                        items: [
                          _searchTypeAll,
                          _searchTypeFileName,
                          _searchTypeBackupTime,
                          _searchTypeRestoreTime,
                          _searchTypeBackupType,
                          _searchTypeHandler,
                          _searchTypeStatus,
                          _searchTypeRestoreStatus,
                        ]
                            .map(
                              (type) => DropdownMenuItem<String>(
                                value: type,
                                child: Text(_searchTypeLabel(type)),
                              ),
                            )
                            .toList(),
                        onChanged: _onSearchTypeChanged,
                      ),
                      const SizedBox(height: 12),
                      if (_selectedSearchType == _searchTypeFileName ||
                          _selectedSearchType == _searchTypeBackupType ||
                          _selectedSearchType == _searchTypeHandler)
                        TextField(
                          controller: _searchValueController,
                          decoration: InputDecoration(
                            labelText: _selectedSearchType ==
                                    _searchTypeFileName
                                ? 'backupRestore.search.byFileName'.tr
                                : _selectedSearchType == _searchTypeBackupType
                                    ? 'backupRestore.search.byType'.tr
                                    : 'backupRestore.search.byHandler'.tr,
                            prefixIcon: const Icon(Icons.search),
                            suffixIcon:
                                _searchValueController.text.trim().isEmpty
                                    ? null
                                    : IconButton(
                                        onPressed: () {
                                          setState(() {
                                            _searchValueController.clear();
                                          });
                                        },
                                        icon: const Icon(Icons.clear),
                                      ),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8.0),
                            ),
                          ),
                          onChanged: (_) => setState(() {}),
                        ),
                      if (_selectedSearchType == _searchTypeBackupTime ||
                          _selectedSearchType == _searchTypeRestoreTime)
                        TextField(
                          controller: _searchDateController,
                          readOnly: true,
                          decoration: InputDecoration(
                            labelText:
                                _selectedSearchType == _searchTypeBackupTime
                                    ? 'backupRestore.search.byBackupTime'.tr
                                    : 'backupRestore.search.byRestoreTime'.tr,
                            prefixIcon: const Icon(Icons.calendar_today),
                            suffixIcon:
                                _searchDateController.text.trim().isEmpty
                                    ? null
                                    : IconButton(
                                        onPressed: () {
                                          setState(() {
                                            _selectedSearchDate = null;
                                            _searchDateController.clear();
                                          });
                                        },
                                        icon: const Icon(Icons.clear),
                                      ),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8.0),
                            ),
                          ),
                          onTap: _pickSearchDate,
                        ),
                      if (_selectedSearchType == _searchTypeStatus)
                        DropdownButtonFormField<String>(
                          initialValue: _selectedStatusFilter,
                          decoration: InputDecoration(
                            labelText: 'backupRestore.search.byStatus'.tr,
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8.0),
                            ),
                          ),
                          items: const ['', 'PENDING', 'RESTORED', 'FAILED']
                              .map(
                                (status) => DropdownMenuItem<String>(
                                  value: status,
                                  child: Text(_statusOptionLabel(status)),
                                ),
                              )
                              .toList(),
                          onChanged: (value) {
                            setState(() {
                              _selectedStatusFilter = value ?? '';
                            });
                          },
                        ),
                      if (_selectedSearchType == _searchTypeRestoreStatus)
                        DropdownButtonFormField<String>(
                          initialValue: _selectedRestoreStatusFilter,
                          decoration: InputDecoration(
                            labelText:
                                'backupRestore.search.byRestoreStatus'.tr,
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(8.0),
                            ),
                          ),
                          items: const ['', 'PENDING', 'RESTORED', 'FAILED']
                              .map(
                                (status) => DropdownMenuItem<String>(
                                  value: status,
                                  child: Text(_statusOptionLabel(status)),
                                ),
                              )
                              .toList(),
                          onChanged: (value) {
                            setState(() {
                              _selectedRestoreStatusFilter = value ?? '';
                            });
                          },
                        ),
                      if (_selectedSearchType != _searchTypeAll)
                        const SizedBox(height: 12),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        alignment: WrapAlignment.end,
                        children: [
                          ElevatedButton.icon(
                            onPressed: _searchBackups,
                            style: ElevatedButton.styleFrom(
                              backgroundColor:
                                  isLight ? Colors.blue : Colors.blueGrey,
                              foregroundColor: Colors.white,
                            ),
                            icon: const Icon(Icons.search),
                            label: Text('common.search'.tr),
                          ),
                          OutlinedButton.icon(
                            onPressed: _resetSearchFilters,
                            icon: const Icon(Icons.restart_alt),
                            label: Text('backupRestore.action.resetFilters'.tr),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Expanded(
                child: _isLoading
                    ? const Center(child: CircularProgressIndicator())
                    : _errorMessage.isNotEmpty
                        ? Center(
                            child: Text(
                              _errorMessage,
                              style: TextStyle(
                                color: isLight ? Colors.black : Colors.white,
                              ),
                            ),
                          )
                        : _filteredBackups.isEmpty
                            ? Center(
                                child: Text(
                                  'backupRestore.empty.noRecords'.tr,
                                  style: TextStyle(
                                    color:
                                        isLight ? Colors.black : Colors.white,
                                  ),
                                ),
                              )
                            : RefreshIndicator(
                                onRefresh: _refreshBackups,
                                child: ListView.builder(
                                  controller: _scrollController,
                                  physics:
                                      const AlwaysScrollableScrollPhysics(),
                                  itemCount: _filteredBackups.length +
                                      ((_isLoading && _backups.isNotEmpty)
                                          ? 1
                                          : 0),
                                  itemBuilder: (context, index) {
                                    if (index >= _filteredBackups.length) {
                                      return const Padding(
                                        padding:
                                            EdgeInsets.symmetric(vertical: 16),
                                        child: Center(
                                          child: CircularProgressIndicator(),
                                        ),
                                      );
                                    }
                                    final backup = _filteredBackups[index];
                                    return Card(
                                      margin: const EdgeInsets.symmetric(
                                          vertical: 8.0, horizontal: 16.0),
                                      elevation: 4,
                                      color: isLight
                                          ? Colors.white
                                          : Colors.grey[800],
                                      shape: RoundedRectangleBorder(
                                        borderRadius:
                                            BorderRadius.circular(10.0),
                                      ),
                                      child: ListTile(
                                        title: Text(
                                          'backupRestore.detail.fileName'
                                              .trParams({
                                            'value': backupDisplayValue(
                                              backup.backupFileName,
                                            ),
                                          }),
                                          style: TextStyle(
                                            color: isLight
                                                ? Colors.black87
                                                : Colors.white,
                                          ),
                                        ),
                                        subtitle: Text(
                                          [
                                            'backupRestore.detail.backupType'
                                                .trParams({
                                              'value': localizeBackupType(
                                                backup.backupType,
                                              ),
                                            }),
                                            'backupRestore.detail.backupTime'
                                                .trParams({
                                              'value': formatBackupDateTime(
                                                backup.backupTime,
                                              ),
                                            }),
                                            'backupRestore.detail.status'
                                                .trParams({
                                              'value':
                                                  localizeBackupRestoreStatus(
                                                backup.status,
                                              ),
                                            }),
                                            'backupRestore.detail.backupHandler'
                                                .trParams({
                                              'value': backupDisplayValue(
                                                backup.backupHandler,
                                              ),
                                            }),
                                            'backupRestore.detail.restoreTime'
                                                .trParams({
                                              'value': formatBackupDateTime(
                                                backup.restoreTime,
                                              ),
                                            }),
                                            'backupRestore.detail.restoreStatus'
                                                .trParams({
                                              'value':
                                                  localizeBackupRestoreStatus(
                                                backup.restoreStatus,
                                              ),
                                            }),
                                            'backupRestore.detail.restoreHandler'
                                                .trParams({
                                              'value': backupDisplayValue(
                                                backup.restoreHandler,
                                              ),
                                            }),
                                          ].join('\n'),
                                          style: TextStyle(
                                            color: isLight
                                                ? Colors.black54
                                                : Colors.white70,
                                          ),
                                        ),
                                        trailing: Row(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            IconButton(
                                              icon: Icon(
                                                Icons.restore,
                                                color: isLight
                                                    ? Colors.green
                                                    : Colors.green[300],
                                              ),
                                              onPressed: () =>
                                                  _restoreBackup(backup),
                                              tooltip:
                                                  'backupRestore.action.restore'
                                                      .tr,
                                            ),
                                            IconButton(
                                              icon: Icon(
                                                Icons.edit,
                                                color: isLight
                                                    ? Colors.blue
                                                    : Colors.blue[300],
                                              ),
                                              onPressed: () =>
                                                  _showUpdateBackupDialog(
                                                      backup),
                                              tooltip:
                                                  'backupRestore.action.edit'
                                                      .tr,
                                            ),
                                            IconButton(
                                              icon: Icon(
                                                Icons.delete,
                                                color: isLight
                                                    ? Colors.red
                                                    : Colors.red[300],
                                              ),
                                              onPressed: () => _deleteBackup(
                                                  backup.backupId!),
                                              tooltip:
                                                  'backupRestore.action.delete'
                                                      .tr,
                                            ),
                                            IconButton(
                                              icon: Icon(
                                                Icons.info,
                                                color: isLight
                                                    ? Colors.blue
                                                    : Colors.blue[300],
                                              ),
                                              onPressed: () =>
                                                  _goToDetailPage(backup),
                                              tooltip:
                                                  'backupRestore.action.viewDetails'
                                                      .tr,
                                            ),
                                          ],
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

class BackupDetailPage extends StatefulWidget {
  final BackupRestore backup;

  const BackupDetailPage({super.key, required this.backup});

  @override
  State<BackupDetailPage> createState() => _BackupDetailPageState();
}

class _BackupDetailPageState extends State<BackupDetailPage> {
  final BackupRestoreControllerApi _backupApi = BackupRestoreControllerApi();
  final TextEditingController _remarksController = TextEditingController();
  bool _apiInitialized = false;
  bool _isLoading = false;
  bool _isAdmin = false;
  late BackupRestore _backup;

  @override
  void initState() {
    super.initState();
    _backup = widget.backup;
    _remarksController.text = _backup.remarks ?? '';
    _initialize();
  }

  @override
  void dispose() {
    _remarksController.dispose();
    super.dispose();
  }

  Future<void> _initialize() async {
    setState(() => _isLoading = true);
    try {
      if (!await _ensureApiInitialized()) {
        setState(() => _isLoading = false);
        return;
      }
      final token = await AuthTokenStore.instance.getJwtToken();
      if (token == null || token.isEmpty) {
        setState(() {
          _isAdmin = false;
          _isLoading = false;
        });
        return;
      }
      final roles = _extractRoles(token);
      setState(() {
        _isAdmin = hasAnyRole(roles, const ['SUPER_ADMIN', 'ADMIN']);
        _isLoading = false;
      });
    } catch (_) {
      setState(() {
        _isAdmin = false;
        _isLoading = false;
      });
    }
  }

  Future<bool> _ensureApiInitialized() async {
    if (_apiInitialized) return true;
    try {
      await _backupApi.initializeWithJwt();
      _apiInitialized = true;
      return true;
    } catch (_) {
      return false;
    }
  }

  List<String> _extractRoles(String token) {
    final decoded = JwtDecoder.decode(token);
    return normalizeRoleCodes(decoded['roles']);
  }

  Future<void> _updateBackup(int backupId, BackupRestore updatedBackup) async {
    if (!mounted || !_isAdmin) return;

    final scaffoldMessenger = ScaffoldMessenger.of(context);
    setState(() => _isLoading = true);

    if (!await _ensureApiInitialized()) {
      scaffoldMessenger.showSnackBar(
        SnackBar(content: Text('backupRestore.error.notLoggedIn'.tr)),
      );
      setState(() => _isLoading = false);
      return;
    }

    try {
      final idempotencyKey = generateIdempotencyKey();
      final payload = updatedBackup.copyWith(idempotencyKey: idempotencyKey);
      final result = await _backupApi.apiSystemBackupBackupIdPut(
        backupId: backupId,
        backupRestore: payload,
        idempotencyKey: idempotencyKey,
      );

      scaffoldMessenger.showSnackBar(
        SnackBar(content: Text('backupRestore.success.updated'.tr)),
      );
      setState(() {
        _backup = result;
        _isLoading = false;
      });
      if (mounted) {
        Navigator.pop(context, true);
      }
    } catch (e) {
      setState(() => _isLoading = false);
      scaffoldMessenger.showSnackBar(
        SnackBar(
          content: Text(
            'backupRestore.error.updateFailed'
                .trParams({'error': formatBackupRestoreError(e)}),
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_isAdmin) {
      return DashboardPageTemplate(
        theme: Theme.of(context),
        title: 'backupRestore.detailPage.title'.tr,
        pageType: DashboardPageType.admin,
        isLoading: _isLoading,
        errorMessage: _isLoading ? null : 'backupRestore.error.adminOnly'.tr,
        body: const SizedBox.shrink(),
      );
    }

    return DashboardPageTemplate(
      theme: Theme.of(context),
      title: 'backupRestore.detailPage.title'.tr,
      pageType: DashboardPageType.admin,
      bodyIsScrollable: true,
      padding: EdgeInsets.zero,
      actions: [
        DashboardPageBarAction(
          icon: Icons.edit,
          onPressed: () => _showUpdateBackupDialog(_backup),
          tooltip: 'backupRestore.action.edit'.tr,
        ),
      ],
      isLoading: _isLoading,
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : ListView(
                children: [
                  _buildDetailRow(
                    context,
                    'backupRestore.field.backupId'.tr,
                    _backup.backupId?.toString() ?? 'common.none'.tr,
                  ),
                  _buildDetailRow(
                    context,
                    'backupRestore.field.backupType'.tr,
                    localizeBackupType(_backup.backupType),
                  ),
                  _buildDetailRow(
                    context,
                    'backupRestore.field.fileName'.tr,
                    backupDisplayValue(_backup.backupFileName),
                  ),
                  _buildDetailRow(
                    context,
                    'backupRestore.field.backupTime'.tr,
                    formatBackupDateTime(_backup.backupTime),
                  ),
                  _buildDetailRow(
                    context,
                    'backupRestore.field.backupHandler'.tr,
                    backupDisplayValue(_backup.backupHandler),
                  ),
                  _buildDetailRow(
                    context,
                    'backupRestore.field.status'.tr,
                    localizeBackupRestoreStatus(_backup.status),
                  ),
                  _buildDetailRow(
                    context,
                    'backupRestore.field.restoreTime'.tr,
                    formatBackupDateTime(_backup.restoreTime),
                  ),
                  _buildDetailRow(
                    context,
                    'backupRestore.field.restoreStatus'.tr,
                    localizeBackupRestoreStatus(_backup.restoreStatus),
                  ),
                  _buildDetailRow(
                    context,
                    'backupRestore.field.restoreHandler'.tr,
                    backupDisplayValue(_backup.restoreHandler),
                  ),
                  _buildDetailRow(
                    context,
                    'backupRestore.field.remarks'.tr,
                    backupDisplayValue(_backup.remarks),
                  ),
                  _buildDetailRow(
                    context,
                    'backupRestore.field.idempotencyKey'.tr,
                    backupDisplayValue(_backup.idempotencyKey),
                  ),
                ],
              ),
      ),
    );
  }

  Widget _buildDetailRow(BuildContext context, String label, String value) {
    final currentTheme = Theme.of(context);
    final bool isLight = currentTheme.brightness == Brightness.light;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'common.labelWithColon'.trParams({'label': label}),
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: isLight ? Colors.black87 : Colors.white,
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                color: isLight ? Colors.black54 : Colors.white70,
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _showUpdateBackupDialog(BackupRestore backup) {
    final TextEditingController fileNameController =
        TextEditingController(text: backup.backupFileName ?? '');
    final TextEditingController remarksController =
        TextEditingController(text: backup.remarks ?? '');
    final formKey = GlobalKey<FormState>();
    var autovalidateMode = AutovalidateMode.disabled;
    StateSetter? updateDialogState;

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('backupRestore.dialog.editTitle'.tr),
        content: StatefulBuilder(
          builder: (context, setState) {
            updateDialogState = setState;
            return Form(
              key: formKey,
              autovalidateMode: autovalidateMode,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextFormField(
                      controller: fileNameController,
                      maxLength: 255,
                      autofocus: true,
                      decoration: InputDecoration(
                        labelText: 'backupRestore.field.fileName'.tr,
                      ),
                      validator: (value) => validateBackupRestoreField(
                        'fileName',
                        value: value,
                        required: true,
                      ),
                    ),
                    TextFormField(
                      controller: remarksController,
                      maxLength: 500,
                      decoration: InputDecoration(
                        labelText: 'backupRestore.field.remarks'.tr,
                      ),
                      maxLines: 3,
                      validator: (value) => validateBackupRestoreField(
                        'remarks',
                        value: value,
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text('common.cancel'.tr),
          ),
          ElevatedButton(
            onPressed: () {
              final isValid = formKey.currentState?.validate() ?? false;
              if (!isValid) {
                updateDialogState?.call(() {
                  autovalidateMode = AutovalidateMode.onUserInteraction;
                });
                return;
              }
              final String fileName = fileNameController.text.trim();
              final String remarks = remarksController.text.trim();

              final updatedBackup = backup.copyWith(
                backupFileName: fileName,
                remarks: remarks,
              );

              _updateBackup(backup.backupId!, updatedBackup);
              Navigator.pop(ctx);
            },
            child: Text('common.save'.tr),
          ),
        ],
      ),
    );
  }
}
