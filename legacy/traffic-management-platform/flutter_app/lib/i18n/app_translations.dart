import 'package:flutter/material.dart';
import 'package:get/get.dart';

class AppTranslations extends Translations {
  static const fallbackLocale = Locale('en', 'US');
  static const supportedLocales = [
    Locale('zh', 'CN'),
    Locale('en', 'US'),
  ];

  @override
  Map<String, Map<String, String>> get keys => {
        'en_US': _enUs,
        'zh_CN': _zhCn,
      };

  static const Map<String, String> _enUs = {
    'app.name': 'Traffic Agent',
    'common.cancel': 'Cancel',
    'common.continue': 'Continue',
    'common.login': 'Login',
    'common.register': 'Register',
    'common.settings': 'Settings',
    'common.profile': 'Profile',
    'common.home': 'Home',
    'common.theme': 'Theme',
    'common.agent': 'Agent',
    'common.online': 'Online',
    'common.loading': 'Loading',
    'common.focus': 'Focus',
    'common.today': 'Today',
    'common.workspace': 'Workspace',
    'common.userWorkspace': 'User workspace',
    'common.adminConsole': 'Admin console',
    'common.managerConsole': 'Operations console',
    'common.openAgent': 'Open agent',
    'common.search': 'Search',
    'common.language': 'Language',
    'common.language.zh': 'Chinese',
    'common.language.en': 'English',
    'common.confirm': 'Confirm',
    'common.ok': 'OK',
    'common.success': 'Success',
    'common.failed': 'Failed',
    'common.save': 'Save',
    'common.create': 'Create',
    'common.submit': 'Submit',
    'common.edit': 'Edit',
    'common.feedback': 'Feedback',
    'common.logout': 'Logout',
    'common.backHome': 'Back home',
    'common.unknown': 'Unknown',
    'common.noData': 'No data',
    'common.notFilled': 'Not provided',
    'common.calculating': 'Calculating...',
    'common.labelWithColon': '@label: ',
    'common.labelWithValue': '@label: @value',
    'common.status.pending': 'Pending',
    'common.status.approved': 'Approved',
    'common.status.rejected': 'Rejected',
    'common.toggleTheme': 'Toggle theme',
    'common.switchLanguage': 'Switch language',
    'common.dark': 'Dark',
    'common.light': 'Light',
    'api.error.notAuthenticated':
        'You are not signed in. Please sign in again.',
    'api.error.unknown': 'Unknown error.',
    'api.error.emptyResponse': 'The server returned an empty response.',
    'api.error.httpStatus': 'Request failed (HTTP @statusCode).',
    'api.error.missingRequiredParam': 'Missing required parameter: @param.',
    'api.error.missingRequiredParams': 'Missing required parameters: @params.',
    'api.error.duplicateRequestIdempotency':
        'Duplicate request detected with idempotencyKey: @key.',
    'api.error.endpointRemoved': 'Endpoint removed: @endpoint',
    'api.error.entityNotFoundWithId': '@entity not found with ID: @id',
    'api.error.adminOnlyDelete':
        'Unauthorized: Only ADMIN can delete @resource',
    'api.error.invalidRequestData': 'Invalid request data',
    'api.error.cannotDetermineUserRole':
        'Unable to determine the current user role.',
    'api.entity.driver': 'Driver',
    'api.entity.offense': 'Offense',
    'api.entity.fine': 'Fine',
    'api.resource.drivers': 'drivers',
    'api.resource.offenses': 'offenses',
    'api.resource.fines': 'fines',
    'shell.workspaceLabel': 'Workspace',
    'shell.footer': 'Traffic Agent Workspace',
    'shell.openChat': 'Open agent panel',
    'auth.validation.emailRequired': 'Email is required',
    'auth.validation.emailInvalid': 'Enter a valid email address',
    'auth.validation.passwordRequired': 'Password is required',
    'auth.validation.passwordShort': 'Password must be at least 5 characters',
    'auth.error.passwordMismatch': 'Passwords do not match',
    'auth.error.registering': 'Registration is already in progress',
    'auth.error.registerCancelled': 'Registration cancelled',
    'auth.error.loginRequiredForReset': 'Login is required before reset',
    'auth.error.loginFailed': 'Login failed',
    'auth.error.invalidJwt': 'Invalid login token.',
    'auth.error.registerFailed': 'Registration failed',
    'auth.error.loginError': 'Login error: @error',
    'auth.error.registerError': 'Registration error: @error',
    'auth.error.passwordResetCancelled': 'Password reset cancelled',
    'auth.error.passwordResetFailed': 'Password reset failed: @code',
    'auth.error.passwordResetError': 'Password reset error: @error',
    'auth.error.currentPasswordIncorrect': 'Current password is incorrect',
    'auth.success.passwordUpdated': 'Password updated',
    'auth.resetPassword': 'Reset password',
    'auth.email': 'Email',
    'auth.password': 'Password',
    'auth.currentPassword': 'Current password',
    'auth.newPassword': 'New password',
    'auth.confirmPassword': 'Confirm password',
    'auth.createAccount': 'Create account',
    'auth.backToLogin': 'Back to login',
    'auth.enterWorkspace': 'Enter workspace',
    'auth.enterWorkspaceBody':
        'Use email and password to sign in, or create a new account.',
    'auth.signingIn': 'Signing in...',
    'auth.creating': 'Creating...',
    'auth.brandBadge': 'Traffic Violation Processing Workspace',
    'auth.brandTitle': 'A rebuilt entry for a cleaner workspace.',
    'auth.brandBody':
        'The old login style is gone. This page now uses a tighter brand panel, a simple auth card, and a clearer visual hierarchy.',
    'auth.metric.mode': 'Mode',
    'auth.metric.flow': 'Flow',
    'auth.metric.agent': 'Agent',
    'auth.metric.flowValue': 'Login / Register',
    'auth.metric.agentValue': 'Ready',
    'auth.promptIdeas': 'Prompt ideas',
    'auth.promptLine1': 'help me find the fastest business entry for today',
    'auth.promptLine2': 'open the admin log center and suggest an order',
    'user.title': 'User workspace',
    'user.subtitle':
        'A simpler home for progress, records, profile and agent help',
    'user.pageTitle': 'Business page',
    'user.nav.progress': 'Progress',
    'user.nav.records': 'Records',
    'user.nav.news': 'News',
    'user.nav.support': 'Support',
    'user.hero.badge': 'User Workspace',
    'user.hero.title': 'Hello, @name',
    'user.hero.subtitle':
        'Your key tasks now live in one cleaner workspace with a focused agent panel.',
    'user.hero.commandHint': 'ask agent: what should I handle first today?',
    'user.hero.secondary': 'View progress',
    'user.metric.identity': 'Identity',
    'user.metric.identityReady': 'Ready',
    'user.metric.identityPending': 'Needs details',
    'user.metric.identityReadyDetail':
        'Profile is complete enough for online processing',
    'user.metric.identityPendingDetail': 'Finish basic credentials first',
    'user.metric.themeDetail': 'Toggle anytime from the top bar',
    'user.metric.agentSyncing': 'Syncing',
    'user.metric.agentDetail': 'Route help, search guidance and page actions',
    'user.quickAccess': 'Quick access',
    'user.card.progress.title': 'Business progress',
    'user.card.progress.subtitle':
        'Track current steps, status and required actions',
    'user.card.records.title': 'Violation records',
    'user.card.records.subtitle':
        'Review open records, penalties and next steps',
    'user.card.profile.title': 'Personal profile',
    'user.card.profile.subtitle':
        'Manage ID, license details and account basics',
    'user.card.news.title': 'Latest updates',
    'user.card.news.subtitle': 'Read public guidance and recent violation news',
    'user.card.support.title': 'Support',
    'user.card.support.subtitle':
        'Escalate complex questions to agent or support',
    'user.card.preferences.title': 'Preferences',
    'user.card.preferences.subtitle':
        'Adjust visual settings and usage preferences',
    'user.today.line1':
        'Check profile details first to avoid avoidable processing failures.',
    'user.today.line2':
        'Use the agent panel when you need search context or route guidance.',
    'user.today.line3':
        'Describe the goal in plain language before jumping into a page.',
    'user.focus.profileStatus': 'Profile status',
    'user.focus.profileReady': 'Ready to use',
    'user.focus.profilePending': 'Complete your credentials',
    'user.focus.agentPanel': 'Agent panel',
    'user.focus.agentPanelValue': 'Always available on the right side',
    'user.focus.workspace': 'Workspace',
    'user.focus.workspaceValue': 'Rebuilt home with a simpler visual system',
    'admin.title': 'Admin console',
    'admin.subtitle':
        'A cleaner control room for governance, progress and agent collaboration',
    'admin.pageTitle': 'Management page',
    'admin.nav.users': 'Users',
    'admin.nav.progress': 'Progress',
    'admin.nav.logs': 'Logs',
    'admin.nav.business': 'Business',
    'admin.hero.badge': 'Admin Console',
    'admin.hero.title': 'Welcome back, @name',
    'admin.hero.subtitle':
        'This admin home is rebuilt as a tighter operating console with less switching and clearer priorities.',
    'admin.hero.commandHint':
        'ask agent: show me the most important admin entry today',
    'admin.hero.secondary': 'Open user management',
    'admin.metric.mode': 'Mode',
    'admin.metric.modeValue': 'Admin enabled',
    'admin.metric.modeDetail': 'This account has access to governance pages',
    'admin.metric.themeDetail': 'Switch instantly from the top bar',
    'admin.metric.agentDetail': 'Skills, routing and suggested next actions',
    'admin.coreEntries': 'Core entries',
    'admin.card.users.title': 'User management',
    'admin.card.users.subtitle':
        'Inspect accounts, permissions and identity details',
    'admin.card.progress.title': 'Progress management',
    'admin.card.progress.subtitle':
        'Review workflow status, queue health and handoffs',
    'admin.card.logs.title': 'Log center',
    'admin.card.logs.subtitle':
        'Audit operations and investigate system issues',
    'admin.card.business.title': 'Business processing',
    'admin.card.business.subtitle':
        'Handle backend business tasks from a focused view',
    'admin.card.profile.title': 'Admin profile',
    'admin.card.profile.subtitle':
        'Update your own admin identity and display details',
    'admin.card.settings.title': 'Console settings',
    'admin.card.settings.subtitle':
        'Adjust theme, layout density and preferences',
    'admin.today.line1':
        'Start with users and progress to find the highest value tasks quickly.',
    'admin.today.line2':
        'Let the agent narrow down next actions if the control surface feels too wide.',
    'admin.today.line3':
        'Use logs for investigation and traceability, not as the default landing path.',
    'manager.title': 'Operations console',
    'manager.subtitle':
        'A focused control room for business queues, progress and agent collaboration',
    'manager.pageTitle': 'Operations page',
    'manager.hero.secondary': 'Open business processing',
    'manager.metric.modeValue': 'Operations enabled',
    'manager.metric.modeDetail':
        'This account has access to operational processing pages.',
    'manager.coreEntries': 'Core entries',
    'manager.business.title': 'Operations processing menu',
    'manager.business.enter': 'Tap to enter',
    'chat.subtitle': 'skills-aware assistant',
    'chat.webOn': 'web on',
    'chat.webOff': 'web off',
    'chat.loadingSkills': 'loading skills',
    'chat.webResults': 'web results',
    'chat.contextTitle': 'agent context',
    'chat.context.operator': 'Current role',
    'chat.context.scope': 'Access scope',
    'chat.status': 'status',
    'chat.you': 'you',
    'chat.agent': 'agent',
    'chat.runAction': 'run action',
    'chat.emptyTitle': 'Start with a command',
    'chat.emptyBody':
        'Describe the outcome. The agent will plan skills, search when needed, and suggest route actions.',
    'chat.inputHint': 'Type a command, for example: open business progress',
    'chat.footer':
        'Enter to send. Agent returns guidance, search context, and route actions.',
    'dialog.fillInfo': 'Fill in information',
    'page.refreshList': 'Refresh list',
    'personal.title': 'Personal information',
    'personal.error.notLoggedIn':
        'You are not logged in. Please sign in again.',
    'personal.error.loadUserFailed': 'Failed to load user information.',
    'personal.error.currentUserNotFound':
        'Current user information was not found.',
    'personal.error.loginTokenMissing': 'Login token was not found.',
    'personal.error.unknownField': 'Unknown field: @field',
    'personal.error.requestFailed': 'Request failed (@code): @message',
    'personal.success.fieldUpdated': '@field updated successfully',
    'personal.editDialog.title': 'Edit @field',
    'personal.editDialog.hint': 'Enter a new @field',
    'personal.field.name': 'Name',
    'personal.field.contactNumber': 'Phone number',
    'personal.field.idCardNumber': 'ID card number',
    'personal.field.driverLicenseNumber': 'Driver license number',
    'personal.field.password': 'Password',
    'personal.field.email': 'Email',
    'personal.field.status': 'Status',
    'personal.field.createdTime': 'Created time',
    'personal.field.modifiedTime': 'Modified time',
    'personal.status.active': 'Active',
    'personal.status.inactive': 'Inactive',
    'personal.value.unknownUser': 'Unknown user',
    'personal.value.changePassword': 'Tap to change password',
    'settings.title': 'Settings',
    'settings.theme': 'Display theme',
    'settings.cache': 'Clear cache',
    'settings.saveSettings': 'Save settings',
    'settings.cacheCleared': 'Cache cleared',
    'settings.saved': 'Settings saved',
    'settings.successTitle': 'Operation successful',
    'settings.confirmLogoutTitle': 'Log out',
    'settings.confirmLogoutMessage': 'Are you sure you want to log out?',
    'settings.themeDialogTitle': 'Choose a display theme',
    'settings.summary.darkMode': 'Dark mode: @value',
    'settings.summary.currentTheme': 'Current theme: @value',
    'settings.summary.cacheSize': 'Cache size: @value MB',
    'settings.themeMode.enabled': 'Enabled',
    'settings.themeMode.disabled': 'Disabled',
    'settings.theme.materialLight': 'Material Light',
    'settings.theme.materialDark': 'Material Dark',
    'settings.theme.ionicLight': 'Ionic Light',
    'settings.theme.ionicDark': 'Ionic Dark',
    'settings.theme.basicLight': 'Basic Light',
    'settings.theme.basicDark': 'Basic Dark',
    'settings.notifications': 'Notifications',
    'settings.notificationsEnabled': 'Notifications enabled',
    'settings.controlTitle': 'Product control surface',
    'settings.controlBody':
        'Operate product configuration from one place, monitor editable scope, and keep sensitive values out of casual views.',
    'settings.workspaceTitle': 'Workspace preferences',
    'settings.workspaceBody':
        'Keep personal console preferences separate from shared system configuration so operating habits do not leak into product governance.',
    'settings.registryTitle': 'Configuration registry',
    'settings.registryBody':
        'Search, filter, and update real system settings with category, type, editability, and encryption state visible at a glance.',
    'settings.searchHint':
        'Search by key, category, type, description, remarks, or value',
    'settings.filter.all': 'All categories',
    'settings.metric.total': 'Total settings',
    'settings.metric.editable': 'Editable',
    'settings.metric.encrypted': 'Encrypted',
    'settings.metric.categories': 'Categories',
    'settings.metric.lastSync': 'Last sync',
    'settings.metric.neverSynced': 'Not synced yet',
    'settings.preference.notificationsBody':
        'Keep non-critical console reminders on this device only.',
    'settings.preference.themeBody': 'Current display theme: @value',
    'settings.preference.themeChange': 'Change theme',
    'settings.preference.localSaveBody':
        'Persist local console preferences without touching shared product settings.',
    'settings.preference.logoutBody':
        'Sign out of the current workspace and clear the local token.',
    'settings.action.newSetting': 'New setting',
    'settings.action.editSetting': 'Edit',
    'settings.action.saveLocal': 'Save local',
    'settings.action.reload': 'Reload',
    'settings.message.localSaved': 'Local preferences saved',
    'settings.message.loadFailed': 'Failed to load settings: @error',
    'settings.message.createSuccess': 'Setting created',
    'settings.message.updateSuccess': 'Setting updated',
    'settings.message.notEditable':
        'This setting is marked read-only and cannot be edited here.',
    'settings.state.emptyTitle': 'No settings match the current filter',
    'settings.state.emptyBody':
        'Try another search term or category, or create a new setting entry.',
    'settings.form.createTitle': 'Create setting',
    'settings.form.editTitle': 'Edit setting',
    'settings.form.key': 'Setting key',
    'settings.form.value': 'Setting value',
    'settings.form.type': 'Setting type',
    'settings.form.category': 'Category',
    'settings.form.description': 'Description',
    'settings.form.remarks': 'Remarks',
    'settings.form.sortOrder': 'Sort order',
    'settings.form.isEditable': 'Editable in console',
    'settings.form.isEncrypted': 'Encrypted value',
    'settings.form.keyRequired': 'Setting key is required',
    'settings.form.valueRequired': 'Setting value is required',
    'settings.value.none': 'Not provided',
    'settings.value.readOnly': 'Read-only',
    'settings.value.editable': 'Editable',
    'settings.value.encrypted': 'Encrypted',
    'settings.value.plaintext': 'Plain text',
    'settings.value.notConfigured': 'Not configured',
    'settings.label.updatedBy': 'Updated by: @value',
    'settings.label.updatedAt': 'Updated at: @value',
    'shared.profileTile.role.userWelcome':
        'Welcome to the driver workspace of the traffic violation processing system',
    'shared.profileTile.role.adminWelcome':
        'Welcome to the admin workspace of the traffic violation processing system',
    'shared.profileTile.role.defaultWelcome':
        'Welcome to the traffic violation processing system',
    'shared.map.title': 'Harbin traffic map',
    'shared.map.error.tileLoadFailed':
        'Failed to load map tiles after @count attempts.',
    'shared.map.error.placeholder': 'Map error',
    'shared.map.attribution.openStreetMap': 'OpenStreetMap contributors',
    'shared.notificationBar.defaultMessage':
        'Please enter your ID card number and driver license number to continue',
    'shared.notificationBar.defaultAction': 'Enter now',
    'shared.notificationBar.navigationError':
        'Unable to navigate to the target page. Please try again.',
    'shared.addCarCard.title': 'Motor vehicle',
    'shared.addCarCard.action': 'Register vehicle information',
    'shared.postCard.title': 'Keep traffic safety in mind at all times',
    'shared.postCard.body': 'Enjoy a safe and happy life every day',
    'shared.policeCard.title':
        'Law enforcement for the people\nFair and clean\nSelfless dedication',
    'shared.policeCard.body':
        'Strengthen comprehensive governance and protect traffic safety',
    'shared.progressReport.appeals': 'Appeals',
    'shared.progressReport.appealsHandled': 'Handled appeals',
    'shared.progressReport.appealsPending': 'Pending appeals',
    'shared.progressReport.completionRate': 'Completion rate',
    'shared.trafficViolation.total': 'Total violations',
    'shared.trafficViolation.handled': 'Handled violations',
    'shared.trafficViolation.pending': 'Pending violations',
    'shared.trafficViolation.rate': 'Handling rate',
    'shared.caseCard.overdueInDays': 'Late by @days days',
    'shared.caseCard.dueInDays': 'Due in @days days',
    'shared.caseCard.dueToday': 'Due today',
    'shared.userScreenSwiper.slogan.safeDriving':
        'Drive safely and travel with courtesy',
    'shared.userScreenSwiper.slogan.followRules':
        'Follow traffic rules and return home safely',
    'shared.userScreenSwiper.slogan.slowDown': 'Slow down and put life first',
    'feedback.title': 'Consultation and feedback',
    'feedback.label': 'Enter your feedback or consultation details',
    'feedback.hint': 'Please enter your feedback...',
    'feedback.submit': 'Submit feedback',
    'feedback.empty': 'Please enter your feedback first',
    'feedback.error.notLoggedIn':
        'Login information was not found. Please sign in again.',
    'feedback.error.submitFailed': 'Failed to submit feedback: @error',
    'feedback.error.httpStatus': 'Request failed (HTTP @statusCode).',
    'feedback.successTitle': 'Success',
    'feedback.successMessage':
        'Your feedback has been submitted and is waiting for admin review.',
    'feedback.successConfirm': 'OK',
    'feedback.approvalTitle': 'Feedback review',
    'feedback.approvalEmpty': 'No feedback requests yet',
    'feedback.approvalUser': 'User: @user',
    'feedback.approvalDetail': 'Feedback: @feedback\nStatus: @status',
    'feedback.approvalApprove': 'Approve',
    'feedback.approvalReject': 'Reject',
    'feedback.approvalInvalidId': 'Invalid feedback ID',
    'feedback.approvalUpdated': 'Feedback has been @status',
    'feedback.error.loadFailed': 'Failed to load feedback requests: @error',
    'feedback.error.updateFailed': 'Failed to update feedback: @error',
    'admin.personal.title': 'Admin profile',
    'admin.personal.logoutTooltip': 'Log out',
    'admin.personal.error.userFromToken':
        'Could not resolve the current user from the token.',
    'admin.personal.error.jwtMissing': 'JWT token was not found in storage.',
    'admin.personal.field.username': 'Username',
    'admin.personal.field.emailAddress': 'Email address',
    'admin.personal.field.remarks': 'Remarks',
    'admin.personal.status.active': 'Active',
    'admin.personal.status.inactive': 'Inactive',
    'admin.personal.logoutConfirmTitle': 'Confirm logout',
    'admin.personal.logoutConfirmBody': 'Are you sure you want to log out?',
    'admin.personal.noData': 'No data',
    'admin.business.title': 'Business processing menu',
    'admin.business.appeal': 'Appeal management',
    'admin.business.deduction': 'Deduction management',
    'admin.business.driver': 'Driver management',
    'admin.business.fine': 'Fine management',
    'admin.business.vehicle': 'Vehicle management',
    'admin.business.offense': 'Violation management',
    'admin.business.enter': 'Tap to enter',
    'admin.logs.title': 'Log management menu',
    'driverAdmin.page.listTitle': 'Driver list',
    'driverAdmin.page.addTitle': 'Add driver',
    'driverAdmin.page.editTitle': 'Edit driver',
    'driverAdmin.page.detailTitle': 'Driver details',
    'driverAdmin.search.hint':
        'Search drivers by name, ID, phone number, ID card number, or license number',
    'driverAdmin.empty.default': 'No driver records available.',
    'driverAdmin.empty.filtered': 'No drivers match the current filters.',
    'driverAdmin.action.add': 'Add driver',
    'driverAdmin.action.edit': 'Edit driver',
    'driverAdmin.action.delete': 'Delete driver',
    'driverAdmin.action.refresh': 'Refresh list',
    'driverAdmin.delete.confirmTitle': 'Confirm delete',
    'driverAdmin.delete.confirmBody':
        'Are you sure you want to delete this driver? This action cannot be undone.',
    'driverAdmin.field.driverId': 'Driver ID',
    'driverAdmin.field.name': 'Name',
    'driverAdmin.field.idCardNumber': 'ID card number',
    'driverAdmin.field.contactNumber': 'Contact number',
    'driverAdmin.field.driverLicenseNumber': 'Driver license number',
    'driverAdmin.field.gender': 'Gender',
    'driverAdmin.field.birthdate': 'Date of birth',
    'driverAdmin.field.firstLicenseDate': 'First license issue date',
    'driverAdmin.field.allowedVehicleType': 'Allowed vehicle type',
    'driverAdmin.field.issueDate': 'Issue date',
    'driverAdmin.field.expiryDate': 'Expiration date',
    'driverAdmin.gender.male': 'Male',
    'driverAdmin.gender.female': 'Female',
    'driverAdmin.gender.unknown': 'Unknown',
    'driverAdmin.validation.required': '@field cannot be empty.',
    'driverAdmin.validation.nameLength':
        'Name must be between 2 and 50 characters.',
    'driverAdmin.validation.idCardInvalid':
        'Enter a valid ID card number (15 or 18 digits).',
    'driverAdmin.validation.contactInvalid':
        'Enter a valid 11-digit phone number.',
    'driverAdmin.validation.licenseInvalid':
        'Enter a valid 12-digit driver license number.',
    'driverAdmin.validation.allowedVehicleTypeTooLong':
        'Allowed vehicle type cannot exceed 50 characters.',
    'driverAdmin.validation.genderRequired': 'Please select a gender.',
    'driverAdmin.validation.fixFormErrors':
        'Please correct the errors in the form.',
    'driverAdmin.error.initFailed': 'Initialization failed: @error',
    'driverAdmin.error.loadFailed': 'Failed to load drivers: @error',
    'driverAdmin.error.detailFailed': 'Failed to load driver details: @error',
    'driverAdmin.error.detailNotFound': 'Driver details not found.',
    'driverAdmin.error.idMissing':
        'Driver ID is missing. Cannot continue the current action.',
    'driverAdmin.error.request': 'Request error: @message',
    'driverAdmin.error.forbidden': 'Permission denied: @message',
    'driverAdmin.error.notFound': 'Not found: @message',
    'driverAdmin.error.duplicateRequest': 'Duplicate request: @message',
    'driverAdmin.error.server': 'Server error: @message',
    'driverAdmin.error.operationFailed': 'Operation failed: @error',
    'driverAdmin.error.createFailed': 'Failed to add driver: @error',
    'driverAdmin.error.updateFailed': 'Failed to update driver: @error',
    'driverAdmin.error.deleteFailed': 'Failed to delete driver: @error',
    'driverAdmin.success.created': 'Driver added successfully.',
    'driverAdmin.success.updated': 'Driver updated successfully.',
    'driverAdmin.success.deleted': 'Driver deleted successfully.',
    'userAdmin.page.title': 'User management',
    'userAdmin.error.unauthorized': 'Unauthorized. Please sign in again.',
    'userAdmin.error.expired': 'Session expired. Please sign in again.',
    'userAdmin.error.invalidLogin':
        'Invalid login information. Please sign in again. @error',
    'userAdmin.error.adminOnly':
        'Insufficient permissions: only administrators can access the user management page.',
    'userAdmin.error.initFailed': 'Initialization failed: @error',
    'userAdmin.error.loadFailed': 'Failed to load users: @error',
    'userAdmin.error.request': 'Request error: @message',
    'userAdmin.error.forbidden': 'Permission denied: @message',
    'userAdmin.error.notFound': 'Not found: @message',
    'userAdmin.error.duplicateRequest': 'Duplicate request: @message',
    'userAdmin.error.server': 'Server error: @message',
    'userAdmin.error.operationFailed': 'Operation failed: @error',
    'userAdmin.error.createFailed': 'Failed to create user: @error',
    'userAdmin.error.updateFailed': 'Failed to update user: @error',
    'userAdmin.error.deleteFailed': 'Failed to delete user: @error',
    'userAdmin.error.roleLoadFailed': 'Failed to manage user roles: @error',
    'userAdmin.empty.default': 'No user records available.',
    'userAdmin.empty.filtered': 'No users match the current filters.',
    'userAdmin.empty.roles': 'This user has no role bindings yet.',
    'userAdmin.workspace.eyebrow': 'User control center',
    'userAdmin.workspace.title': 'User management workspace',
    'userAdmin.workspace.subtitle':
        'Search, compare status, and open account actions from one tighter admin surface.',
    'userAdmin.workspace.signal.query': 'Query: @value',
    'userAdmin.workspace.signal.queryIdle': 'Query scope: all loaded users',
    'userAdmin.workspace.signal.mode': 'Search mode: @value',
    'userAdmin.workspace.metric.loaded': 'Loaded',
    'userAdmin.workspace.metric.visible': 'Visible',
    'userAdmin.workspace.metric.active': 'Active',
    'userAdmin.workspace.metric.inactive': 'Inactive',
    'userAdmin.workspace.metric.department': 'Departments',
    'userAdmin.workspace.filterEyebrow': 'Filters',
    'userAdmin.workspace.filterTitle': 'Search and narrow users',
    'userAdmin.workspace.filterBody':
        'Switch search mode, refine the current user set, and refresh the visible list.',
    'userAdmin.workspace.filterMode': 'Search mode',
    'userAdmin.workspace.filterReset': 'Reset filters',
    'userAdmin.workspace.filterRefresh': 'Refresh users',
    'userAdmin.workspace.listEyebrow': 'Users',
    'userAdmin.workspace.listTitle': 'User records',
    'userAdmin.workspace.listBody':
        'Scan status, owner details, department, and contact data before editing or role changes.',
    'userAdmin.workspace.emptyTitle': 'No users in the current view',
    'userAdmin.workspace.errorTitle': 'Could not load user records',
    'userAdmin.search.username': 'Search username',
    'userAdmin.search.status': 'Search status',
    'userAdmin.search.department': 'Search department',
    'userAdmin.search.contactNumber': 'Search contact number',
    'userAdmin.search.email': 'Search email',
    'userAdmin.filter.byUsername': 'By username',
    'userAdmin.filter.byStatus': 'By status',
    'userAdmin.filter.byDepartment': 'By department',
    'userAdmin.filter.byContactNumber': 'By contact number',
    'userAdmin.filter.byEmail': 'By email',
    'userAdmin.dialog.createTitle': 'Create user',
    'userAdmin.dialog.editTitle': 'Edit user',
    'userAdmin.dialog.manageRolesTitle': 'Manage roles for @username',
    'userAdmin.delete.confirmTitle': 'Confirm delete',
    'userAdmin.delete.confirmBody':
        'Are you sure you want to delete this user? This action cannot be undone.',
    'userAdmin.action.relogin': 'Sign in again',
    'userAdmin.action.create': 'Create user',
    'userAdmin.action.manageRoles': 'Manage roles',
    'userAdmin.action.edit': 'Edit user',
    'userAdmin.action.delete': 'Delete user',
    'userAdmin.action.refresh': 'Refresh list',
    'userAdmin.hint.selectRole': 'Select a role to add',
    'userAdmin.field.username': 'Username',
    'userAdmin.field.password': 'Password',
    'userAdmin.field.newPassword': 'New password',
    'userAdmin.field.contactNumber': 'Contact number',
    'userAdmin.field.email': 'Email',
    'userAdmin.field.department': 'Department',
    'userAdmin.field.status': 'Status',
    'userAdmin.field.remarks': 'Remarks',
    'userAdmin.field.createdTime': 'Created time',
    'userAdmin.field.modifiedTime': 'Modified time',
    'userAdmin.helper.passwordOptional':
        'Leave blank to keep the current password.',
    'userAdmin.validation.required': '@field cannot be empty.',
    'userAdmin.validation.usernameTooLong':
        'Username cannot exceed 50 characters.',
    'userAdmin.validation.passwordTooLong':
        'Password cannot exceed 255 characters.',
    'userAdmin.validation.contactNumberTooLong':
        'Contact number cannot exceed 20 characters.',
    'userAdmin.validation.emailTooLong': 'Email cannot exceed 100 characters.',
    'userAdmin.validation.emailInvalid': 'Enter a valid email address.',
    'userAdmin.validation.departmentTooLong':
        'Department cannot exceed 100 characters.',
    'userAdmin.validation.remarksTooLong':
        'Remarks cannot exceed 255 characters.',
    'userAdmin.validation.statusRequired': 'Please select a status.',
    'userAdmin.validation.roleRequired': 'Please select a role first.',
    'userAdmin.validation.usernameExists': 'This username already exists.',
    'userAdmin.success.created': 'User created successfully.',
    'userAdmin.success.updated': 'User updated successfully.',
    'userAdmin.success.deleted': 'User deleted successfully.',
    'userAdmin.success.roleAdded': 'Role binding added successfully.',
    'userAdmin.success.roleRemoved': 'Role binding removed successfully.',
    'userAdmin.status.active': 'Active',
    'userAdmin.status.inactive': 'Inactive',
    'userAdmin.value.unknownUser': 'Unknown user',
    'business.menu.title': 'Business menu',
    'business.menu.signal': 'Business workspace',
    'business.menu.subtitle':
        'Review records, pay fines, submit appeals, and track progress from one focused workspace.',
    'business.menu.ready': 'Ready',
    'business.menu.statusReview': 'Needs review',
    'business.menu.sectionTitle': 'Available actions',
    'business.menu.sectionBody':
        'Open the task that matches your current self-service step.',
    'business.menu.quickStatus': 'Current status',
    'business.menu.quickStatusBody':
        'Use this page as the primary entry for routine self-service processing.',
    'business.menu.tipTitle': 'Today',
    'business.menu.tip1':
        'Check offense details before you pay, appeal, or submit follow-up steps.',
    'business.menu.tip2':
        'Use progress tracking after each submission to confirm the latest state.',
    'business.menu.tip3':
        'Keep vehicle information current to avoid routing and ownership issues.',
    'business.menu.offenseDetail': 'Offense details',
    'business.menu.offenseDetail.subtitle':
        'Review current records, evidence, and decision details.',
    'business.menu.finePayment': 'Fine payment',
    'business.menu.finePayment.subtitle':
        'Pay open penalties and confirm payment status.',
    'business.menu.userAppeal': 'User appeal',
    'business.menu.userAppeal.subtitle':
        'Submit a new appeal or review existing requests.',
    'business.menu.onlineProcessingProgress': 'Processing progress',
    'business.menu.onlineProcessingProgress.subtitle':
        'Track workflow state, timestamps, and next actions.',
    'business.menu.vehicleManagement': 'Vehicle registration management',
    'business.menu.vehicleManagement.subtitle':
        'Maintain registered vehicle details before processing.',
    'loginLog.page.title': 'Login logs',
    'loginLog.error.unauthorized': 'Unauthorized. Please sign in again.',
    'loginLog.error.expired': 'Your login has expired. Please sign in again.',
    'loginLog.error.invalidLogin':
        'Invalid login information. Please sign in again.',
    'loginLog.error.adminOnly':
        'Access denied. This page is only available to administrators.',
    'loginLog.error.initFailed': 'Initialization failed: @error',
    'loginLog.error.roleCheckFailed': 'Role verification failed: @error',
    'loginLog.error.loadFailed': 'Failed to load login logs: @error',
    'loginLog.error.request': 'Request error: @message',
    'loginLog.error.forbidden': 'No permission: @message',
    'loginLog.error.notFound': 'Not found: @message',
    'loginLog.error.duplicateRequest': 'Duplicate request: @message',
    'loginLog.error.server': 'Server error: @message',
    'loginLog.error.operationFailed': 'Operation failed: @error',
    'loginLog.error.idMissingEdit':
        'Unable to edit because the log ID is missing.',
    'loginLog.error.idMissingDelete':
        'Unable to delete because the log ID is missing.',
    'loginLog.empty.filtered': 'No login logs matched the current filters.',
    'loginLog.empty.default': 'No login logs yet.',
    'loginLog.dialog.createTitle': 'Create login log',
    'loginLog.dialog.editTitle': 'Edit login log',
    'loginLog.field.username': 'Username',
    'loginLog.field.loginIp': 'Login IP address',
    'loginLog.field.loginResult': 'Login result',
    'loginLog.field.browserType': 'Browser type',
    'loginLog.field.osVersion': 'Operating system version',
    'loginLog.field.remarks': 'Remarks',
    'loginLog.validation.usernameRequired': 'Username cannot be empty.',
    'loginLog.validation.loginIpRequired': 'Login IP address cannot be empty.',
    'loginLog.validation.loginResultRequired': 'Login result cannot be empty.',
    'loginLog.validation.usernameTooLong':
        'Username cannot exceed 100 characters.',
    'loginLog.validation.loginIpTooLong':
        'Login IP address cannot exceed 50 characters.',
    'loginLog.validation.loginResultTooLong':
        'Login result cannot exceed 50 characters.',
    'loginLog.validation.browserTypeTooLong':
        'Browser type cannot exceed 100 characters.',
    'loginLog.validation.osVersionTooLong':
        'Operating system version cannot exceed 100 characters.',
    'loginLog.validation.remarksTooLong':
        'Remarks cannot exceed 500 characters.',
    'loginLog.success.created': 'Login log created successfully.',
    'loginLog.success.updated': 'Login log updated successfully.',
    'loginLog.success.deleted': 'Login log deleted successfully.',
    'loginLog.delete.confirmTitle': 'Confirm deletion',
    'loginLog.delete.confirmBody':
        'Are you sure you want to delete this login log? This action cannot be undone.',
    'loginLog.search.username': 'Search username',
    'loginLog.search.loginResult': 'Search login result',
    'loginLog.search.timeRangeSelected': 'Search time range (selected)',
    'loginLog.filter.byUsername': 'By username',
    'loginLog.filter.byLoginResult': 'By login result',
    'loginLog.filter.dateRangeLabel': 'Date range: @start to @end',
    'loginLog.filter.selectDateRange': 'Select a date range',
    'loginLog.filter.tooltip': 'Search by date range',
    'loginLog.filter.startDate': 'Start date',
    'loginLog.filter.endDate': 'End date',
    'loginLog.filter.clearDateRange': 'Clear date range',
    'loginLog.detail.id': 'Log ID: @value',
    'loginLog.detail.username': 'Username: @value',
    'loginLog.detail.loginIp': 'Login IP address: @value',
    'loginLog.detail.loginResult': 'Login result: @value',
    'loginLog.detail.loginTime': 'Login time: @value',
    'loginLog.detail.browserType': 'Browser type: @value',
    'loginLog.detail.osVersion': 'Operating system version: @value',
    'loginLog.detail.remarks': 'Remarks: @value',
    'loginLog.action.relogin': 'Sign in again',
    'loginLog.action.create': 'Create',
    'loginLog.action.edit': 'Edit login log',
    'loginLog.action.delete': 'Delete login log',
    'operationLog.page.title': 'Operation logs',
    'operationLog.error.unauthorized': 'Unauthorized. Please sign in again.',
    'operationLog.error.expired':
        'Your login has expired. Please sign in again.',
    'operationLog.error.invalidLogin':
        'Invalid login information. Please sign in again.',
    'operationLog.error.adminOnly':
        'Access denied. This page is only available to administrators.',
    'operationLog.error.initFailed': 'Initialization failed: @error',
    'operationLog.error.roleCheckFailed': 'Role verification failed: @error',
    'operationLog.error.loadFailed': 'Failed to load operation logs: @error',
    'operationLog.error.request': 'Request error: @message',
    'operationLog.error.forbidden': 'No permission: @message',
    'operationLog.error.notFound': 'Not found: @message',
    'operationLog.error.duplicateRequest': 'Duplicate request: @message',
    'operationLog.error.server': 'Server error: @message',
    'operationLog.error.operationFailed': 'Operation failed: @error',
    'operationLog.workspace.eyebrow': 'Operation log center',
    'operationLog.workspace.title': 'Operation activity stream',
    'operationLog.workspace.subtitle':
        'Search by actor, result, or date range and inspect recent backend operations from one focused console.',
    'operationLog.workspace.signal.query': 'Query: @value',
    'operationLog.workspace.signal.queryIdle':
        'Query scope: all loaded operation logs',
    'operationLog.workspace.signal.rangeIdle': 'No date range selected',
    'operationLog.workspace.metric.loaded': 'Loaded',
    'operationLog.workspace.metric.visible': 'Visible',
    'operationLog.workspace.metric.success': 'Successful',
    'operationLog.workspace.metric.failed': 'Failed',
    'operationLog.workspace.filterEyebrow': 'Filters',
    'operationLog.workspace.filterTitle': 'Search and narrow operations',
    'operationLog.workspace.filterBody':
        'Switch search mode, apply date range, and refresh the visible stream.',
    'operationLog.workspace.filterMode': 'Search mode',
    'operationLog.workspace.filterReset': 'Reset filters',
    'operationLog.workspace.filterRefresh': 'Refresh logs',
    'operationLog.workspace.listEyebrow': 'Stream',
    'operationLog.workspace.listTitle': 'Operation records',
    'operationLog.workspace.listBody':
        'Scan result, actor, time, and content to locate the latest backend action quickly.',
    'operationLog.workspace.emptyTitle':
        'No operation logs in the current view',
    'operationLog.workspace.errorTitle': 'Could not load operation logs',
    'operationLog.error.idMissingEdit':
        'Unable to edit because the log ID is missing.',
    'operationLog.error.idMissingDelete':
        'Unable to delete because the log ID is missing.',
    'operationLog.empty.filtered':
        'No operation logs matched the current filters.',
    'operationLog.empty.default': 'No operation logs yet.',
    'operationLog.dialog.createTitle': 'Create operation log',
    'operationLog.dialog.editTitle': 'Edit operation log',
    'operationLog.field.userId': 'User ID',
    'operationLog.field.operationContent': 'Operation content',
    'operationLog.field.operationResult': 'Operation result',
    'operationLog.field.remarks': 'Remarks',
    'operationLog.field.requestIp': 'IP address',
    'operationLog.field.operationTime': 'Operation time',
    'operationLog.validation.userIdRequired': 'User ID cannot be empty.',
    'operationLog.validation.userIdNumeric': 'User ID must be a number.',
    'operationLog.validation.userIdTooLong':
        'User ID cannot exceed 20 characters.',
    'operationLog.validation.operationContentRequired':
        'Operation content cannot be empty.',
    'operationLog.validation.operationContentTooLong':
        'Operation content cannot exceed 500 characters.',
    'operationLog.validation.operationResultRequired':
        'Operation result cannot be empty.',
    'operationLog.validation.operationResultTooLong':
        'Operation result cannot exceed 100 characters.',
    'operationLog.validation.remarksTooLong':
        'Remarks cannot exceed 500 characters.',
    'operationLog.success.created': 'Operation log created successfully.',
    'operationLog.success.updated': 'Operation log updated successfully.',
    'operationLog.success.deleted': 'Operation log deleted successfully.',
    'operationLog.delete.confirmTitle': 'Confirm deletion',
    'operationLog.delete.confirmBody':
        'Are you sure you want to delete this operation log? This action cannot be undone.',
    'operationLog.search.userId': 'Search user ID',
    'operationLog.search.operationResult': 'Search operation result',
    'operationLog.search.timeRangeSelected': 'Search time range (selected)',
    'operationLog.filter.byUserId': 'By user ID',
    'operationLog.filter.byOperationResult': 'By operation result',
    'operationLog.filter.dateRangeLabel': 'Date range: @start to @end',
    'operationLog.filter.selectDateRange': 'Select a date range',
    'operationLog.filter.tooltip': 'Search by date range',
    'operationLog.filter.startDate': 'Start date',
    'operationLog.filter.endDate': 'End date',
    'operationLog.filter.clearDateRange': 'Clear date range',
    'operationLog.detail.id': 'Log ID: @value',
    'operationLog.detail.userId': 'User ID: @value',
    'operationLog.detail.operationContent': 'Operation content: @value',
    'operationLog.detail.operationResult': 'Operation result: @value',
    'operationLog.detail.operationTime': 'Operation time: @value',
    'operationLog.detail.requestIp': 'IP address: @value',
    'operationLog.detail.remarks': 'Remarks: @value',
    'operationLog.action.relogin': 'Sign in again',
    'operationLog.action.create': 'Create',
    'operationLog.action.edit': 'Edit operation log',
    'operationLog.action.delete': 'Delete operation log',
    'systemLog.page.title': 'System logs',
    'systemLog.section.overview': 'System overview',
    'systemLog.section.recentLogin': 'Recent login logs',
    'systemLog.section.recentOperation': 'Recent operation logs',
    'systemLog.overview.loginLogCount': 'Login logs',
    'systemLog.overview.operationLogCount': 'Operation logs',
    'systemLog.overview.requestHistoryCount': 'Request history',
    'systemLog.empty.overview': 'No system overview data available.',
    'systemLog.empty.login': 'No recent login logs.',
    'systemLog.empty.operation': 'No recent operation logs.',
    'systemLog.error.unauthorized': 'Unauthorized. Please sign in again.',
    'systemLog.error.expired': 'Your login has expired. Please sign in again.',
    'systemLog.error.invalidLogin':
        'Invalid login information. Please sign in again.',
    'systemLog.error.adminOnly':
        'Access denied. This page is only available to administrators.',
    'systemLog.error.initFailed': 'Initialization failed: @error',
    'systemLog.error.roleCheckFailed': 'Role verification failed: @error',
    'systemLog.error.loadFailed': 'Failed to load system logs: @error',
    'systemLog.error.request': 'Request error: @message',
    'systemLog.error.forbidden': 'No permission: @message',
    'systemLog.error.notFound': 'Not found: @message',
    'systemLog.error.duplicateRequest': 'Duplicate request: @message',
    'systemLog.error.server': 'Server error: @message',
    'systemLog.error.operationFailed': 'Operation failed: @error',
    'systemLog.workspace.eyebrow': 'System log center',
    'systemLog.workspace.title': 'System activity console',
    'systemLog.workspace.subtitle':
        'Monitor overview counts, recent logins, and recent operations from one tighter log surface.',
    'systemLog.workspace.signal.login': 'Recent logins: @count',
    'systemLog.workspace.signal.operation': 'Recent operations: @count',
    'systemLog.workspace.signal.refresh':
        'Pull to refresh or use top bar actions',
    'systemLog.workspace.metric.overview': 'Overview blocks',
    'systemLog.workspace.metric.login': 'Login rows',
    'systemLog.workspace.metric.operation': 'Operation rows',
    'systemLog.workspace.metric.alert': 'Attention items',
    'systemLog.workspace.overviewBody':
        'Use the overview counts to confirm whether ingestion and log volume look normal.',
    'systemLog.workspace.loginEyebrow': 'Login stream',
    'systemLog.workspace.loginBody':
        'Review recent sign-ins first when validating account access or suspicious activity.',
    'systemLog.workspace.operationEyebrow': 'Operation stream',
    'systemLog.workspace.operationBody':
        'Use recent operation logs to inspect changes, outcomes, and actor traces.',
    'systemLog.workspace.errorTitle': 'Could not load system logs',
    'systemLog.detail.loginResult': 'Result: @value',
    'systemLog.detail.loginIp': 'IP: @value',
    'systemLog.detail.loginLocation': 'Location: @value',
    'systemLog.detail.loginDevice': 'Device: @value',
    'systemLog.detail.remarks': 'Remarks: @value',
    'systemLog.detail.operationType': 'Type: @value',
    'systemLog.detail.user': 'User: @value',
    'systemLog.detail.operationResult': 'Result: @value',
    'systemLog.detail.operationContent': 'Content: @value',
    'systemLog.detail.requestIp': 'IP: @value',
    'systemLog.action.relogin': 'Sign in again',
    'systemLog.value.unknownUser': 'Unknown user',
    'systemLog.value.unknownModule': 'Unknown module',
    'backupRestore.page.title': 'Backup and restore',
    'backupRestore.detailPage.title': 'Backup details',
    'backupRestore.dialog.editTitle': 'Edit backup',
    'backupRestore.search.filterType': 'Search field',
    'backupRestore.search.type.all': 'All records',
    'backupRestore.search.type.fileName': 'File name',
    'backupRestore.search.type.backupTime': 'Backup time',
    'backupRestore.search.type.restoreTime': 'Restore time',
    'backupRestore.search.type.backupType': 'Backup type',
    'backupRestore.search.type.handler': 'Backup handler',
    'backupRestore.search.type.status': 'Task status',
    'backupRestore.search.type.restoreStatus': 'Restore status',
    'backupRestore.search.byFileName': 'Search backups by file name',
    'backupRestore.search.byBackupTime': 'Search backups by backup time',
    'backupRestore.search.byRestoreTime': 'Search backups by restore time',
    'backupRestore.search.byType': 'Search backups by type',
    'backupRestore.search.byHandler': 'Search backups by handler',
    'backupRestore.search.byStatus': 'Filter by task status',
    'backupRestore.search.byRestoreStatus': 'Filter by restore status',
    'backupRestore.search.allStatuses': 'All statuses',
    'backupRestore.empty.noRecords': 'No backup records found.',
    'backupRestore.error.notLoggedIn':
        'You are not signed in. Please sign in again.',
    'backupRestore.error.adminOnly':
        'Access denied. This page is only available to administrators.',
    'backupRestore.error.initFailed': 'Initialization failed: @error',
    'backupRestore.error.loadFailed': 'Failed to load backup records: @error',
    'backupRestore.error.createFailed': 'Failed to create backup: @error',
    'backupRestore.error.updateFailed': 'Failed to update backup: @error',
    'backupRestore.error.restoreFailed': 'Failed to restore backup: @error',
    'backupRestore.error.deleteFailed': 'Failed to delete backup: @error',
    'backupRestore.error.server': 'Server error',
    'backupRestore.error.fileNameRequired': 'File name cannot be empty.',
    'backupRestore.validation.required': 'Please fill in @field.',
    'backupRestore.validation.fileNameTooLong':
        'File name cannot exceed 255 characters.',
    'backupRestore.validation.remarksTooLong':
        'Remarks cannot exceed 500 characters.',
    'backupRestore.success.created': 'Backup created successfully.',
    'backupRestore.success.updated': 'Backup updated successfully.',
    'backupRestore.success.restored': 'Backup restored successfully.',
    'backupRestore.success.deleted': 'Backup deleted successfully.',
    'backupRestore.action.create': 'Create backup',
    'backupRestore.action.restore': 'Restore this backup',
    'backupRestore.action.edit': 'Edit this backup',
    'backupRestore.action.delete': 'Delete this backup',
    'backupRestore.action.viewDetails': 'View details',
    'backupRestore.action.resetFilters': 'Reset filters',
    'backupRestore.field.backupId': 'Backup ID',
    'backupRestore.field.backupType': 'Backup type',
    'backupRestore.field.fileName': 'File name',
    'backupRestore.field.backupTime': 'Backup time',
    'backupRestore.field.backupHandler': 'Backup handler',
    'backupRestore.field.restoreTime': 'Restore time',
    'backupRestore.field.restoreStatus': 'Restore status',
    'backupRestore.field.restoreHandler': 'Restore handler',
    'backupRestore.field.status': 'Task status',
    'backupRestore.field.remarks': 'Remarks',
    'backupRestore.field.idempotencyKey': 'Idempotency key',
    'backupRestore.detail.backupType': 'Backup type: @value',
    'backupRestore.detail.fileName': 'File name: @value',
    'backupRestore.detail.backupTime': 'Backup time: @value',
    'backupRestore.detail.backupHandler': 'Backup handler: @value',
    'backupRestore.detail.restoreTime': 'Restore time: @value',
    'backupRestore.detail.restoreStatus': 'Restore status: @value',
    'backupRestore.detail.restoreHandler': 'Restore handler: @value',
    'backupRestore.detail.status': 'Task status: @value',
    'backupRestore.status.pending': 'Pending',
    'backupRestore.status.restored': 'Restored',
    'backupRestore.status.failed': 'Failed',
    'backupRestore.status.notRestored': 'Not restored',
    'backupRestore.type.full': 'Full backup',
    'backupRestore.type.incremental': 'Incremental backup',
    'backupRestore.type.differential': 'Differential backup',
    'backupRestore.type.manual': 'Manual backup',
    'backupRestore.type.auto': 'Automatic backup',
    'backupRestore.value.manualCreatedRemarks': 'Manually created backup',
    'progress.pageTitle': 'Progress updates',
    'progress.empty': 'No progress records yet',
    'progress.status': 'Status',
    'progress.status.pending': 'Pending',
    'progress.status.processing': 'Processing',
    'progress.status.completed': 'Completed',
    'progress.status.archived': 'Archived',
    'progress.submitTime': 'Submitted at',
    'progress.viewDetail': 'View details',
    'progress.filter.status': 'Status filter',
    'progress.filter.timeRange': 'Filter by time range',
    'progress.filter.clear': 'Clear filters',
    'progress.filter.selectTimeRange': 'Select a time range',
    'progress.filter.clearTooltip': 'Clear filters',
    'progress.view.items': 'Progress updates',
    'progress.view.refunds': 'Refund audits',
    'progress.refund.empty': 'No refund audit records found',
    'progress.refund.filter.fineId': 'Fine ID',
    'progress.refund.filter.paymentId': 'Payment ID',
    'progress.refund.filter.searchTooltip': 'Search refund audits',
    'progress.refund.filter.clearTooltip': 'Clear refund filters',
    'progress.refund.status.all': 'All statuses',
    'progress.refund.type.partial': 'Partial refund',
    'progress.refund.type.waive': 'Waive and refund',
    'progress.refund.type.partialFailed': 'Partial refund failed',
    'progress.refund.type.waiveFailed': 'Waive and refund failed',
    'progress.refund.detail.businessType': 'Refund type: @value',
    'progress.refund.detail.businessId': 'Payment ID: @value',
    'progress.refund.detail.fineId': 'Fine ID: @value',
    'progress.refund.detail.refundAmount': 'Refund amount: @value',
    'progress.refund.detail.operator': 'Operator: @value',
    'progress.refund.detail.reason': 'Reason: @value',
    'progress.refund.detail.failure': 'Failure: @value',
    'progress.refund.detail.requestIp': 'Request IP: @value',
    'progress.refund.detail.userId': 'User ID: @value',
    'progress.refund.detail.updatedTime': 'Updated at: @value',
    'progress.refund.detail.idempotencyKey': 'Idempotency key: @value',
    'progress.refund.detail.noReason': 'No refund reason',
    'progress.submitNew': 'Submit new progress',
    'progress.dialog.submitTitle': 'Submit new progress',
    'progress.dialog.editTitle': 'Edit progress',
    'progress.field.title': 'Progress title',
    'progress.field.details': 'Details',
    'progress.field.detailsOptional': 'Details (optional)',
    'progress.field.relatedAppealOptional': 'Related appeal (optional)',
    'progress.field.appealOption': 'Appeal: @name (ID: @id)',
    'progress.validation.required': 'Please fill in @field.',
    'progress.validation.titleAndDetails': 'Title and details cannot be empty.',
    'progress.validation.titleRequired': 'Title cannot be empty.',
    'progress.validation.titleTooLong':
        'Progress title cannot exceed 100 characters.',
    'progress.validation.detailsTooLong':
        'Progress details cannot exceed 500 characters.',
    'progress.error.adminOnly':
        'Access denied. This page is only available to administrators.',
    'progress.detail.status': 'Status: @value',
    'progress.detail.submitTime': 'Submitted at: @value',
    'progress.action.createTooltip': 'Create progress',
    'progress.action.viewEdit': 'View/Edit',
    'progress.action.delete': 'Delete',
    'progress.action.setPending': 'Set to pending',
    'progress.action.setProcessing': 'Set to processing',
    'progress.action.setCompleted': 'Set to completed',
    'progress.action.setArchived': 'Set to archived',
    'progress.delete.confirmTitle': 'Confirm deletion',
    'progress.delete.confirmMessage':
        'Are you sure you want to delete this progress record? This action cannot be undone.',
    'progress.delete.confirmBody':
        'Are you sure you want to delete this progress record? This action cannot be undone.',
    'progress.detail.title': 'Progress details',
    'progress.detail.id': 'Progress ID',
    'progress.detail.user': 'Submitted by',
    'progress.detail.relatedBusiness': 'Related business',
    'progress.action.processing': 'Processing',
    'progress.action.completed': 'Completed',
    'progress.error.idMissingUpdate':
        'Cannot update because the progress ID is missing.',
    'progress.error.idMissingDelete':
        'Cannot delete because the progress ID is missing.',
    'progress.error.loadAppeals': 'Failed to load appeals: @error',
    'progress.error.fetchFailed': 'Failed to load progress records.',
    'progress.error.submitFailed': 'Failed to submit progress.',
    'progress.error.updateFailed': 'Failed to update progress.',
    'progress.error.fetchByTimeRangeFailed':
        'Failed to load progress records for the selected time range.',
    'progress.error.request': 'Request error: @message',
    'progress.error.permission': 'No permission: @message',
    'progress.error.notFound': 'Not found: @message',
    'progress.error.server': 'Server error: @message',
    'progress.error.operationFailed': 'Operation failed: @error',
    'progress.context.appealId': 'Appeal ID: @id',
    'progress.context.deductionId': 'Deduction ID: @id',
    'progress.context.driverId': 'Driver ID: @id',
    'progress.context.fineId': 'Fine ID: @id',
    'progress.context.vehicleId': 'Vehicle ID: @id',
    'progress.context.offenseId': 'Offense ID: @id',
    'progress.context.noRelatedBusiness': 'No related business',
    'progress.success.submitted': 'Progress submitted successfully.',
    'progress.success.updated': 'Progress updated successfully.',
    'progress.success.statusUpdated': 'Status updated successfully.',
    'progress.error.statusUpdateFailed': 'Failed to update status: @error',
    'progress.success.deleted': 'Deleted successfully.',
    'progress.error.deleteFailed': 'Failed to delete: @error',
    'common.status.processing': 'Processing',
    'common.status.completed': 'Completed',
    'common.status.archived': 'Archived',
    'trafficDashboard.page.title': 'Traffic violation dashboard',
    'trafficDashboard.error.loadFailed':
        'Failed to load traffic dashboard: @error',
    'trafficDashboard.section.violationType': 'Violation type distribution',
    'trafficDashboard.section.fineTrend': 'Fine and point trends',
    'trafficDashboard.section.appealReason': 'Appeal reason distribution',
    'trafficDashboard.section.paymentStatus': 'Fine payment status',
    'trafficDashboard.empty.violationType': 'No violation type data.',
    'trafficDashboard.empty.timeSeries': 'No time-series data.',
    'trafficDashboard.empty.appealReason': 'No appeal reason data.',
    'trafficDashboard.empty.paymentStatus': 'No payment status data.',
    'trafficDashboard.empty.timeSeriesAvailable':
        'No time-series data is available.',
    'trafficDashboard.empty.dataAvailable': 'No data is available.',
    'trafficDashboard.empty.violationAvailable':
        'No violation data is available.',
    'trafficDashboard.snackbar.violationType': 'Viewing violation type details',
    'trafficDashboard.snackbar.timeSeries': 'Viewing time-series details',
    'trafficDashboard.snackbar.appealReason': 'Viewing appeal reason details',
    'trafficDashboard.snackbar.paymentStatus': 'Viewing payment status details',
    'trafficDashboard.snackbar.viewDetails': 'Viewing details: @title',
    'trafficDashboard.metric.fine': 'Fine',
    'trafficDashboard.metric.points': 'Points',
    'trafficDashboard.metric.total': 'Total',
    'trafficDashboard.tooltip.fine': '@date\nFine: @value',
    'trafficDashboard.tooltip.count': '@label\n@value times',
    'trafficDashboard.violationType.speeding': 'Speeding',
    'trafficDashboard.violationType.redLight': 'Red-light running',
    'trafficDashboard.violationType.illegalParking': 'Illegal parking',
    'trafficDashboard.violationType.drunkDriving': 'Drunk driving',
    'trafficDashboard.violationType.other': 'Other',
    'trafficDashboard.appealReason.insufficientEvidence':
        'Insufficient evidence',
    'trafficDashboard.appealReason.proceduralIssue': 'Procedural issue',
    'trafficDashboard.appealReason.misjudgment': 'Misjudgment',
    'trafficDashboard.appealReason.other': 'Other',
    'trafficDashboard.paymentStatus.paid': 'Paid',
    'trafficDashboard.paymentStatus.unpaid': 'Unpaid',
    'chart.noOffenseData': 'No offense data available',
    'chart.noData': 'No data available',
    'chart.total': 'Total',
    'chart.error.loadData': 'Failed to load chart data.',
    'search.hint': 'Please enter keywords...',
    'common.none': 'None',
    'offense.error.unauthorized': 'Unauthorized. Please sign in again.',
    'offense.error.userOnly': 'Access denied. This page is only for users.',
    'offense.error.loginExpired':
        'Your login has expired. Please sign in again.',
    'offense.error.driverNameMissing':
        'Could not get the driver name. Please sign in again.',
    'offense.error.invalidLogin':
        'Invalid login information. Please sign in again.',
    'offense.error.usernameMissing':
        'Could not determine the current username.',
    'offense.error.initializeFailed': 'Initialization failed: @error',
    'offense.error.noRecordsInRange':
        'No violation records were found in the selected time range.',
    'offense.error.noRecordsBySearch':
        'No violation records matched the current search.',
    'offense.error.empty': 'No violation records yet.',
    'offense.error.notFound': 'No violation records were found.',
    'offense.error.loadFailed': 'Failed to load violation records: @error',
    'offense.error.badRequest': 'Bad request: @message',
    'offense.error.forbidden': 'Forbidden: @message',
    'offense.error.notFoundMessage': 'Not found: @message',
    'offense.error.duplicateRequest': 'Duplicate request: @message',
    'offense.error.server': 'Server error: @message',
    'offense.error.operationFailed': 'Operation failed: @error',
    'offense.workspace.eyebrow': 'Violation workspace',
    'offense.workspace.live': 'Live feed',
    'offense.workspace.filtered': 'Filtered view',
    'offense.workspace.title': 'Records for @name',
    'offense.workspace.subtitle':
        'Search, narrow, and open the exact record that needs action.',
    'offense.workspace.searchIdle': 'Search scope: all loaded records',
    'offense.workspace.searchActive': 'Search keyword: @value',
    'offense.workspace.rangeIdle': 'No time range selected',
    'offense.workspace.metric.loaded': 'Loaded',
    'offense.workspace.metric.visible': 'Visible',
    'offense.workspace.metric.pending': 'Needs action',
    'offense.workspace.metric.points': 'Points in view',
    'offense.workspace.metric.fine': 'Fines in view',
    'offense.workspace.filterEyebrow': 'Filters',
    'offense.workspace.filterTitle': 'Search and narrow records',
    'offense.workspace.filterBody':
        'Use violation type, code, and date range to reduce the current record set.',
    'offense.workspace.filterReset': 'Reset filters',
    'offense.workspace.filterRefresh': 'Refresh records',
    'offense.workspace.listEyebrow': 'Records',
    'offense.workspace.listTitle': 'Violation list',
    'offense.workspace.listBody':
        'Open a row to inspect status, timing, amount, and location.',
    'offense.workspace.emptyTitle': 'No records in the current view',
    'offense.workspace.emptyBody':
        'Change the keyword or date range, or refresh the records.',
    'offense.workspace.errorTitle': 'Could not load records',
    'offense.search.hint': 'Search violation type or code',
    'offense.filter.rangeLabel': 'Time range: @start to @end',
    'offense.filter.select': 'Select a time range',
    'offense.filter.tooltip': 'Filter by time range',
    'offense.filter.startDate': 'Start date',
    'offense.filter.endDate': 'End date',
    'offense.filter.clear': 'Clear time range',
    'offense.page.title': 'My violation records',
    'offense.action.relogin': 'Sign in again',
    'offense.card.type': 'Violation type: @value',
    'offense.card.licensePlate': 'Plate number: @value',
    'offense.card.points': 'Points deducted: @value',
    'offense.card.time': 'Time: @value',
    'offense.detail.title': 'Violation details',
    'offense.detail.id': 'Violation ID',
    'offense.detail.licensePlate': 'Plate number',
    'offense.detail.driverName': 'Driver name',
    'offense.detail.type': 'Violation type',
    'offense.detail.code': 'Violation code',
    'offense.detail.points': 'Points deducted',
    'offense.detail.amount': 'Fine amount',
    'offense.detail.time': 'Violation time',
    'offense.detail.location': 'Violation location',
    'offense.detail.processStatus': 'Processing status',
    'offense.detail.processResult': 'Processing result',
    'offense.value.points': '@value points',
    'offense.value.amount': '@value yuan',
    'offenseAdmin.page.title': 'Violation management',
    'offenseAdmin.action.add': 'Add violation record',
    'offenseAdmin.action.refresh': 'Refresh list',
    'offenseAdmin.action.relogin': 'Sign in again',
    'offenseAdmin.action.edit': 'Edit violation',
    'offenseAdmin.action.delete': 'Delete violation',
    'offenseAdmin.search.driverName': 'Search driver name',
    'offenseAdmin.search.licensePlate': 'Search plate number',
    'offenseAdmin.search.offenseType': 'Search violation type',
    'offenseAdmin.search.timeRangeSelected': 'Violation time range selected',
    'offenseAdmin.filter.byDriverName': 'By driver name',
    'offenseAdmin.filter.byLicensePlate': 'By plate number',
    'offenseAdmin.filter.byOffenseType': 'By violation type',
    'offenseAdmin.filter.dateRangeLabel':
        'Violation time range: @start to @end',
    'offenseAdmin.filter.selectDateRange': 'Select a violation time range',
    'offenseAdmin.filter.tooltip': 'Filter by violation time range',
    'offenseAdmin.filter.startDate': 'Start date',
    'offenseAdmin.filter.endDate': 'End date',
    'offenseAdmin.filter.clearDateRange': 'Clear date range',
    'offenseAdmin.error.unauthorized': 'Unauthorized. Please sign in again.',
    'offenseAdmin.error.expired':
        'Your login has expired. Please sign in again.',
    'offenseAdmin.error.refreshedExpired':
        'The refreshed login information has expired. Please sign in again.',
    'offenseAdmin.error.invalidLogin':
        'Invalid login information. Please sign in again.',
    'offenseAdmin.error.initFailed': 'Initialization failed: @error',
    'offenseAdmin.error.httpStatus': 'Request failed (HTTP @statusCode).',
    'offenseAdmin.error.roleCheckFailed': 'Role verification failed: @error',
    'offenseAdmin.error.adminOnly':
        'Access denied. This page is only available to administrators.',
    'offenseAdmin.error.filteredEmpty':
        'No violation records matched the current filters.',
    'offenseAdmin.error.notFound': 'No violation records were found.',
    'offenseAdmin.empty.default': 'There are no violation records right now.',
    'offenseAdmin.workspace.eyebrow': 'Violation control center',
    'offenseAdmin.workspace.title': 'Violation management workspace',
    'offenseAdmin.workspace.subtitle':
        'Search by driver, plate, or violation type and review current records from one focused admin surface.',
    'offenseAdmin.workspace.signal.query': 'Query: @value',
    'offenseAdmin.workspace.signal.queryIdle':
        'Query scope: all loaded violation records',
    'offenseAdmin.workspace.signal.rangeIdle': 'No date range selected',
    'offenseAdmin.workspace.metric.loaded': 'Loaded',
    'offenseAdmin.workspace.metric.visible': 'Visible',
    'offenseAdmin.workspace.metric.pending': 'Pending',
    'offenseAdmin.workspace.metric.points': 'Points in view',
    'offenseAdmin.workspace.metric.fine': 'Fines in view',
    'offenseAdmin.workspace.filterEyebrow': 'Filters',
    'offenseAdmin.workspace.filterTitle': 'Search and narrow violations',
    'offenseAdmin.workspace.filterBody':
        'Switch search mode, apply date range, and refresh the current violation stream.',
    'offenseAdmin.workspace.filterMode': 'Search mode',
    'offenseAdmin.workspace.filterReset': 'Reset filters',
    'offenseAdmin.workspace.filterRefresh': 'Refresh records',
    'offenseAdmin.workspace.listEyebrow': 'Records',
    'offenseAdmin.workspace.listTitle': 'Violation records',
    'offenseAdmin.workspace.listBody':
        'Scan status, owner, timing, points, and location before opening details or deleting a record.',
    'offenseAdmin.workspace.emptyTitle':
        'No violation records in the current view',
    'offenseAdmin.workspace.errorTitle': 'Could not load violation records',
    'offenseAdmin.error.loadFailed': 'Failed to load violation records: @error',
    'offenseAdmin.error.suggestionFailed': 'Failed to load suggestions: @error',
    'offenseAdmin.error.deleteFailed': 'Failed to delete violation: @error',
    'offenseAdmin.delete.confirmTitle': 'Confirm deletion',
    'offenseAdmin.delete.confirmBody':
        'Are you sure you want to delete this violation record? This action cannot be undone.',
    'offenseAdmin.card.type': 'Violation type: @value',
    'offenseAdmin.card.licensePlate': 'Plate number: @value',
    'offenseAdmin.card.driverName': 'Driver name: @value',
    'offenseAdmin.card.status': 'Status: @value',
    'offenseAdmin.form.addTitle': 'Add a new violation record',
    'offenseAdmin.form.editTitle': 'Edit violation record',
    'offenseAdmin.form.driverName': 'Driver name',
    'offenseAdmin.form.licensePlate': 'Plate number',
    'offenseAdmin.form.offenseType': 'Violation type',
    'offenseAdmin.form.offenseCode': 'Violation code',
    'offenseAdmin.form.offenseLocation': 'Violation location',
    'offenseAdmin.form.offenseTime': 'Violation time',
    'offenseAdmin.form.deductedPoints': 'Points deducted',
    'offenseAdmin.form.fineAmount': 'Fine amount',
    'offenseAdmin.form.processStatus': 'Processing status',
    'offenseAdmin.form.processResult': 'Processing result',
    'offenseAdmin.form.plateHelper':
        'Enter a valid plate number, for example: HeiAWS34.',
    'offenseAdmin.form.locationHelper':
        'Enter a violation location, for example: XX intersection.',
    'offenseAdmin.validation.required': '@field cannot be empty.',
    'offenseAdmin.validation.driverNameTooLong':
        'Driver name cannot exceed 100 characters.',
    'offenseAdmin.validation.plateTooLong':
        'Plate number cannot exceed 20 characters.',
    'offenseAdmin.validation.plateInvalid':
        'Please enter a valid plate number, for example: HeiAWS34.',
    'offenseAdmin.validation.typeTooLong':
        'Violation type cannot exceed 100 characters.',
    'offenseAdmin.validation.codeTooLong':
        'Violation code cannot exceed 50 characters.',
    'offenseAdmin.validation.locationTooLong':
        'Violation location cannot exceed 100 characters.',
    'offenseAdmin.validation.timeInvalid': 'Invalid date format.',
    'offenseAdmin.validation.timeFuture':
        'Violation time cannot be later than today.',
    'offenseAdmin.validation.pointsInteger':
        'Points deducted must be an integer.',
    'offenseAdmin.validation.pointsNegative':
        'Points deducted cannot be negative.',
    'offenseAdmin.validation.pointsTooLarge':
        'Points deducted cannot exceed 12.',
    'offenseAdmin.validation.amountNumber': 'Fine amount must be a number.',
    'offenseAdmin.validation.amountNegative': 'Fine amount cannot be negative.',
    'offenseAdmin.validation.amountTooLarge':
        'Fine amount cannot exceed 99999999.99.',
    'offenseAdmin.validation.amountPrecision':
        'Fine amount can have at most two decimal places.',
    'offenseAdmin.validation.statusTooLong':
        'Processing status cannot exceed 50 characters.',
    'offenseAdmin.validation.resultTooLong':
        'Processing result cannot exceed 255 characters.',
    'offenseAdmin.success.created': 'Violation record created successfully.',
    'offenseAdmin.success.updated': 'Violation record updated successfully.',
    'offenseAdmin.success.deleted': 'Violation record deleted successfully.',
    'offenseAdmin.error.createFailed':
        'Failed to create violation record: @error',
    'offenseAdmin.error.updateFailed':
        'Failed to update violation record: @error',
    'offenseAdmin.error.permissionLoadFailed':
        'Failed to load permissions: @error',
    'fine.status.paid': 'Paid',
    'fine.status.pending': 'Pending',
    'fine.error.missingLoginOrDriver':
        'You are not signed in or the driver information is missing.',
    'fine.error.usernameMissing': 'Could not determine the current username.',
    'fine.error.initializeFailed': 'Initialization failed: @error',
    'fine.error.loadFailed': 'Failed to load fine information: @error',
    'fine.error.generateQrFailed': 'Failed to generate payment QR code: @error',
    'fine.error.refreshFailed': 'Failed to refresh fine information: @error',
    'fine.error.driverNotFoundRelogin':
        'Driver information was not found. Please sign in again.',
    'fine.detail.title': 'Fine details',
    'fine.detail.amount': 'Fine amount',
    'fine.value.amount': '@value yuan',
    'fine.detail.payee': 'Payee',
    'fine.detail.account': 'Bank account',
    'fine.detail.bank': 'Bank',
    'fine.detail.receipt': 'Receipt number',
    'fine.detail.time': 'Fine time',
    'fine.detail.status': 'Status',
    'fine.detail.outstanding': 'Outstanding amount',
    'fine.detail.remarks': 'Remarks',
    'fine.paymentHistory.title': 'Payment history',
    'fine.paymentHistory.empty': 'No payment records yet.',
    'fine.paymentHistory.loadFailed': 'Failed to load payment history: @error',
    'fine.paymentHistory.recordTitle': 'Payment amount: \$@amount',
    'fine.paymentHistory.status': 'Payment status',
    'fine.paymentHistory.time': 'Payment time',
    'fine.paymentHistory.method': 'Payment method',
    'fine.paymentHistory.channel': 'Payment channel',
    'fine.paymentHistory.paymentNumber': 'Payment number',
    'fine.paymentHistory.transactionId': 'Transaction ID',
    'fine.paymentHistory.receiptNumber': 'Receipt number',
    'fine.paymentHistory.receiptUrl': 'Payment proof link',
    'fine.paymentHistory.payerName': 'Payer name',
    'fine.paymentHistory.payerIdCard': 'Payer ID card',
    'fine.paymentHistory.payerContact': 'Payer contact',
    'fine.paymentHistory.bankName': 'Bank name',
    'fine.paymentHistory.bankAccount': 'Bank account',
    'fine.paymentHistory.refund': 'Refund information',
    'fine.paymentHistory.refundValue': '\$@amount at @time',
    'fine.paymentHistory.missingProofHint':
        'Self-service payment is confirmed but no proof link was uploaded. Finance should verify it manually.',
    'fine.reviewQueue.title': 'Pending payment reviews',
    'fine.reviewQueue.empty': 'No pending finance review tasks right now.',
    'fine.reviewQueue.loadFailed':
        'Failed to load payment review tasks: @error',
    'fine.reviewQueue.openFine': 'Open fine',
    'fine.reviewQueue.openFailed': 'Failed to open the related fine: @error',
    'fine.reviewQueue.recordSubtitle': 'Fine #@fineId · @status · @channel',
    'fine.reviewQueue.selectionHint': '@count selected',
    'fine.reviewQueue.selectAll': 'Select all',
    'fine.reviewQueue.clearSelection': 'Clear selection',
    'fine.reviewQueue.batchNeedProof': 'Batch request proof',
    'fine.reviewQueue.batchNeedProofSuccess':
        'Marked @count payment review tasks as needing more proof.',
    'fine.reviewQueue.batchNeedProofFailed':
        'Failed to batch request more proof: @error',
    'fine.reviewQueue.batchApprove': 'Batch verify',
    'fine.reviewQueue.batchApproveSuccess':
        'Marked @count payment review tasks as verified.',
    'fine.reviewQueue.batchApproveFailed':
        'Failed to batch verify payment review tasks: @error',
    'fine.reviewQueue.filter.all': 'All',
    'fine.reviewQueue.filter.overdue': 'Overdue',
    'fine.reviewQueue.filter.missingProof': 'Missing proof',
    'fine.reviewQueue.filter.needProof': 'Need proof again',
    'fine.reviewQueue.sort.pending': 'Sort: newest pending',
    'fine.reviewQueue.sort.amount': 'Sort: highest amount',
    'fine.reviewQueue.filteredEmpty':
        'No payment review tasks match the current filter.',
    'fine.reviewQueue.overdueBadge': 'Overdue',
    'fine.reviewQueue.pendingSince': 'Pending since @time',
    'fine.reviewQueue.pendingHours': '@hours h',
    'fine.reviewQueue.pendingDays': '@days d',
    'fine.paymentReview.latest': 'Latest finance review',
    'fine.paymentReview.result': 'Review result',
    'fine.paymentReview.time': 'Review time',
    'fine.paymentReview.reviewer': 'Reviewer',
    'fine.paymentReview.opinion': 'Review note',
    'fine.paymentReview.result.approved': 'Verified',
    'fine.paymentReview.result.needProof': 'Need more proof',
    'fine.paymentReview.action.approve': 'Mark verified',
    'fine.paymentReview.action.needProof': 'Request proof',
    'fine.paymentReview.dialog.needProofTitle': 'Request more proof',
    'fine.paymentReview.dialog.needProofHint':
        'Tell the payer what proof still needs to be uploaded for finance verification.',
    'fine.paymentReview.validation.opinionRequired':
        'Please enter the proof request before submitting.',
    'fine.paymentReview.success.approved': 'Finance review marked as verified.',
    'fine.paymentReview.success.needProof':
        'Finance review marked as proof required.',
    'fine.paymentReview.failed': 'Failed to submit finance review: @error',
    'fine.payment.action.uploadProof': 'Upload proof',
    'fine.payment.proofDialog.title': 'Upload payment proof',
    'fine.payment.proofDialog.hint':
        'Paste the latest receipt or proof link for this payment so finance can continue the review.',
    'fine.payment.proof.validation.receiptUrlRequired':
        'Please enter the payment proof link before submitting.',
    'fine.payment.proof.success': 'Payment proof updated successfully.',
    'fine.payment.proof.failed': 'Failed to update payment proof: @error',
    'fine.qr.alipayHint': 'Scan the QR code below with Alipay to pay',
    'fine.action.close': 'Close',
    'fine.action.payNow': 'Pay now (\$@amount)',
    'fine.payment.unavailable': 'This fine cannot be paid right now.',
    'fine.payment.orderCreated':
        'Payment order created: \$@amount. Confirm it after you finish paying.',
    'fine.payment.confirmAction': 'Confirm payment',
    'fine.payment.confirmSuccess': 'Payment confirmed: \$@amount',
    'fine.payment.confirmFailed': 'Failed to confirm payment: @error',
    'fine.payment.confirmDialog.title': 'Confirm payment',
    'fine.payment.confirmDialog.hint':
        'Enter the real transaction ID used for this payment. You can also keep a proof link for later review.',
    'fine.payment.form.transactionId': 'Transaction ID *',
    'fine.payment.form.receiptUrl': 'Payment proof link (optional)',
    'fine.payment.validation.transactionIdRequired':
        'Please enter the transaction ID before confirming payment.',
    'fine.payment.pendingHint':
        'This order is waiting for payment confirmation. Complete the transfer first, then confirm here.',
    'fine.payment.expiredHint':
        'This pending payment order has expired. You can create a new one if you still need to pay.',
    'fine.payment.pendingExistsInline':
        'There is already a pending payment order for this fine. Confirm it before creating another one.',
    'fine.payment.success': 'Payment recorded successfully: \$@amount',
    'fine.payment.failed': 'Failed to record payment: @error',
    'fine.page.title': 'Traffic violation fine records',
    'fine.action.refresh': 'Refresh fine records',
    'fine.empty.byDriver': 'No fine records matched driver @driver',
    'fine.card.amount': 'Fine amount: \$@amount',
    'fine.card.summary': 'Payee: @payee\nTime: @time\nStatus: @status',
    'fineAdmin.page.title': 'Fine management',
    'fineAdmin.action.add': 'Add fine information',
    'fineAdmin.action.refresh': 'Refresh list',
    'fineAdmin.action.retry': 'Retry',
    'fineAdmin.action.restoreCache': 'Restore cached data',
    'fineAdmin.action.relogin': 'Sign in again',
    'fineAdmin.action.edit': 'Edit fine',
    'fineAdmin.action.delete': 'Delete fine',
    'fineAdmin.search.payee': 'Search payee',
    'fineAdmin.search.timeRangeSelected': 'Search time range (selected)',
    'fineAdmin.filter.byPayee': 'By payee',
    'fineAdmin.filter.byTimeRange': 'By time range',
    'fineAdmin.filter.dateRangeLabel': 'Fine date range: @start to @end',
    'fineAdmin.filter.selectDateRange': 'Select a fine date range',
    'fineAdmin.filter.tooltip': 'Search by fine date range',
    'fineAdmin.filter.startDate': 'Start date',
    'fineAdmin.filter.endDate': 'End date',
    'fineAdmin.filter.clearDateRange': 'Clear date range',
    'fineAdmin.error.unauthorized': 'Unauthorized. Please sign in again.',
    'fineAdmin.error.expired': 'Your login has expired. Please sign in again.',
    'fineAdmin.error.refreshedExpired':
        'The refreshed login information has expired. Please sign in again.',
    'fineAdmin.error.invalidLogin':
        'Invalid login information. Please sign in again.',
    'fineAdmin.error.adminOnly':
        'Access denied. This page is only available to administrators.',
    'fineAdmin.error.initFailed': 'Initialization failed: @error',
    'fineAdmin.error.httpStatus': 'Request failed (HTTP @statusCode).',
    'fineAdmin.error.roleCheckFailed': 'Role verification failed: @error',
    'fineAdmin.error.notFound': 'No fine records were found.',
    'fineAdmin.error.filteredEmpty':
        'No fine records matched the current filters.',
    'fineAdmin.empty.default': 'There are no fine records right now.',
    'fineAdmin.error.loadFailed': 'Failed to load fine information: @error',
    'fineAdmin.error.loadLatestFallback':
        'Failed to load the latest fines. Showing cached data instead.',
    'fineAdmin.error.suggestionFailed':
        'Failed to load autocomplete suggestions: @error',
    'fineAdmin.success.refreshed': 'Fine list refreshed.',
    'fineAdmin.delete.confirmTitle': 'Confirm deletion',
    'fineAdmin.delete.confirmBody':
        'Are you sure you want to delete this fine record? This action cannot be undone.',
    'fineAdmin.success.deleted': 'Fine deleted successfully.',
    'fineAdmin.error.deleteFailed': 'Failed to delete fine: @error',
    'fineAdmin.card.amount': 'Amount: @amount yuan',
    'fineAdmin.card.payee': 'Payee: @value',
    'fineAdmin.card.time': 'Time: @value',
    'fineAdmin.card.status': 'Status: @value',
    'fineAdmin.form.addTitle': 'Add a new fine',
    'fineAdmin.form.editTitle': 'Edit fine',
    'fineAdmin.form.plateNumber': 'Plate number',
    'fineAdmin.form.amount': 'Fine amount',
    'fineAdmin.form.payee': 'Payee',
    'fineAdmin.form.accountNumber': 'Bank account',
    'fineAdmin.form.bank': 'Bank',
    'fineAdmin.form.receiptNumber': 'Receipt number',
    'fineAdmin.form.remarks': 'Remarks',
    'fineAdmin.form.fineDate': 'Fine date',
    'fineAdmin.form.plateHelper':
        'Enter a valid plate number, for example: province code + A12345.',
    'fineAdmin.form.accountHelper': 'Enter a bank account number if available.',
    'fineAdmin.validation.required': '@field cannot be empty.',
    'fineAdmin.validation.plateTooLong':
        'The plate number cannot exceed 20 characters.',
    'fineAdmin.validation.plateInvalid':
        'Enter a valid plate number, for example: province code + A12345.',
    'fineAdmin.validation.payeeTooLong':
        'The payee name cannot exceed 100 characters.',
    'fineAdmin.validation.amountNumber':
        'The fine amount must be a valid number.',
    'fineAdmin.validation.amountNegative':
        'The fine amount cannot be negative.',
    'fineAdmin.validation.amountTooLarge':
        'The fine amount cannot exceed 99999999.99.',
    'fineAdmin.validation.amountPrecision':
        'The fine amount can include up to 2 decimal places.',
    'fineAdmin.validation.accountTooLong':
        'The bank account cannot exceed 50 characters.',
    'fineAdmin.validation.bankTooLong':
        'The bank name cannot exceed 100 characters.',
    'fineAdmin.validation.receiptTooLong':
        'The receipt number cannot exceed 50 characters.',
    'fineAdmin.validation.remarksTooLong':
        'Remarks cannot exceed 255 characters.',
    'fineAdmin.validation.dateInvalid': 'Invalid date format.',
    'fineAdmin.validation.dateFuture':
        'The fine date cannot be later than today.',
    'fineAdmin.error.jwtMissingRelogin':
        'JWT was not found. Please sign in again.',
    'fineAdmin.error.fetchPlateSuggestionsFailed':
        'Failed to load plate suggestions: @error',
    'fineAdmin.error.fetchPayeeSuggestionsFailed':
        'Failed to load payee suggestions: @error',
    'fineAdmin.error.offenseNotFoundByPlate':
        'No violation record was found for this plate number.',
    'fineAdmin.error.fetchOffenseFailed':
        'Failed to load violation information: @error',
    'fineAdmin.error.invalidOffense': 'Invalid violation record.',
    'fineAdmin.error.loadPayeeFailed':
        'Failed to load payee information: @error',
    'fineAdmin.error.selectValidOffense':
        'Please select a valid violation record first.',
    'fineAdmin.success.updated': 'Fine updated successfully.',
    'fineAdmin.success.created': 'Fine created successfully.',
    'fineAdmin.error.updateFailed': 'Failed to update fine: @error',
    'fineAdmin.error.createFailed': 'Failed to create fine: @error',
    'fineAdmin.detail.title': 'Fine details',
    'fineAdmin.detail.editTooltip': 'Edit fine',
    'fineAdmin.detail.approveTooltip': 'Approve fine',
    'fineAdmin.detail.rejectTooltip': 'Reject fine',
    'fineAdmin.detail.deleteTooltip': 'Delete fine',
    'fineAdmin.success.statusUpdated': 'Fine record marked as @status.',
    'fineAdmin.error.statusUpdateFailed':
        'Failed to update fine status: @error',
    'fineAdmin.error.permissionLoadFailed':
        'Failed to load permissions: @error',
    'appeal.status.pending': 'Pending',
    'appeal.status.approved': 'Approved',
    'appeal.status.rejected': 'Rejected',
    'appeal.error.notLoggedIn': 'You are not signed in. Please sign in again.',
    'appeal.error.driverNameMissingRelogin':
        'Could not get the driver name. Please sign in again.',
    'appeal.error.userOnly': 'Access denied. This page is only for users.',
    'appeal.error.loadFailed': 'Failed to load appeal data: @error',
    'appeal.error.invalidJwt': 'Invalid JWT format',
    'appeal.error.currentUserMissing': 'Could not determine the current user.',
    'appeal.error.driverNameNotFound': 'Driver name was not found.',
    'appeal.error.checkOffenseFailed':
        'Failed to verify violation information: @error',
    'appeal.error.usernameMissing': 'Username was not found.',
    'appeal.empty': 'No appeal records yet.',
    'appeal.empty.filtered': 'No appeal records matched the current filters.',
    'appeal.error.loadRecordsFailed': 'Failed to load appeal records: @error',
    'appeal.success.submitted': 'Appeal submitted successfully.',
    'appeal.error.submitFailed': 'Failed to submit appeal: @error',
    'appeal.error.noOffenseToSubmit':
        'You do not have any violation records, so an appeal cannot be submitted.',
    'appeal.error.completeProfileBeforeSubmit':
        'Complete your name, ID card number and contact number in personal profile before submitting an appeal.',
    'appeal.dialog.submitTitle': 'Submit an appeal',
    'appeal.form.offense': 'Violation record *',
    'appeal.form.offenseOption': 'ID: @id - @type',
    'appeal.value.noDescription': 'No description',
    'appeal.validation.offenseRequired': 'Please select a violation record.',
    'appeal.form.appellantName': 'Appellant name *',
    'appeal.form.idCard': 'ID card number *',
    'appeal.form.contact': 'Contact number *',
    'appeal.form.identityFromProfile':
        'This information is taken from your current personal profile.',
    'appeal.form.reason': 'Appeal reason *',
    'appeal.form.initialEvidenceDescription': 'Evidence description (optional)',
    'appeal.form.initialEvidenceUrls': 'Evidence links (optional)',
    'appeal.validation.required': 'Please fill in @field.',
    'appeal.validation.reasonTooLong':
        'Appeal reason cannot exceed 500 characters.',
    'appeal.validation.requiredFields': 'Please fill in all required fields.',
    'appeal.search.hint': 'Search appeal reason',
    'appeal.filter.rangeLabel': 'Date range: @start to @end',
    'appeal.filter.select': 'Select a date range',
    'appeal.filter.tooltip': 'Search by date range',
    'appeal.filter.startDate': 'Start date',
    'appeal.filter.endDate': 'End date',
    'appeal.filter.clear': 'Clear date range',
    'appeal.page.title': 'User appeal management',
    'appeal.action.submit': 'Submit appeal',
    'appeal.action.supplementComplete': 'Submit supplemental materials',
    'appeal.action.resubmit': 'Resubmit appeal',
    'appeal.action.withdraw': 'Withdraw appeal',
    'appeal.empty.byAppellant': 'No appeal records matched appellant @name',
    'appeal.card.title': 'Appellant: @name (ID: @id)',
    'appeal.card.summary': 'Reason: @reason\nStatus: @status\nTime: @time',
    'appeal.progress.submitTitle': 'Submit feedback',
    'appeal.progress.title': 'Feedback title',
    'appeal.progress.detailsOptional': 'Details (optional)',
    'appeal.progress.titleRequired': 'The title cannot be empty.',
    'appeal.detail.title': 'Appeal details',
    'appeal.progress.submitAction': 'Submit feedback',
    'appeal.detail.appealId': 'Appeal ID',
    'appeal.detail.offenseId': 'Violation ID',
    'appeal.detail.appellant': 'Appellant',
    'appeal.detail.idCard': 'ID card number',
    'appeal.detail.contact': 'Contact number',
    'appeal.detail.reason': 'Appeal reason',
    'appeal.detail.evidenceDescription': 'Evidence description',
    'appeal.detail.evidenceUrls': 'Evidence links',
    'appeal.detail.time': 'Appeal time',
    'appeal.detail.acceptanceStatus': 'Acceptance status',
    'appeal.detail.status': 'Processing status',
    'appeal.detail.result': 'Processing result',
    'appeal.detail.reviewHistory': 'Review history',
    'appeal.detail.reviewEmpty': 'No review history yet.',
    'appeal.detail.reviewCount': '@count review records',
    'appeal.detail.reviewReviewer': 'Reviewer',
    'appeal.detail.reviewReviewerDept': 'Reviewer department',
    'appeal.detail.reviewLevel': 'Review level',
    'appeal.detail.reviewResult': 'Review result',
    'appeal.detail.reviewOpinion': 'Review opinion',
    'appeal.detail.reviewTime': 'Review time',
    'appeal.form.supplementTitle': 'Update appeal materials',
    'appeal.form.supplementHint':
        'Adjust your appeal reason or supplementary evidence before sending it back for review.',
    'appeal.form.evidenceDescription': 'Supplementary evidence description',
    'appeal.form.evidenceUrls': 'Supplementary evidence links',
    'appeal.form.evidenceUrlsHint':
        'Paste one or more file links or JSON array content if available',
    'appeal.progress.related': 'Related feedback',
    'appeal.progress.empty': 'No related feedback records yet.',
    'appeal.progress.summary': 'Status: @status\nSubmitted at: @time',
    'appeal.note.readonly':
        'Note: users cannot edit or delete appeals. Contact an administrator for changes.',
    'appeal.note.awaitingUserAction':
        'This appeal is waiting for your action before acceptance can continue.',
    'appeal.note.withdrawable':
        'You can withdraw this appeal before the review process is completed.',
    'appeal.success.supplementCompleted':
        'Your supplemental materials were submitted for acceptance review.',
    'appeal.success.resubmitted':
        'Your appeal has been resubmitted for acceptance review.',
    'appeal.success.withdrawn': 'Your appeal has been withdrawn successfully.',
    'appealAdmin.page.title': 'Appeal review management',
    'appealAdmin.error.unauthorizedMissing':
        'Unauthorized: login information was not found. Please sign in again.',
    'appealAdmin.error.unauthorized': 'Unauthorized. Please sign in again.',
    'appealAdmin.error.expired':
        'Your login has expired. Please sign in again.',
    'appealAdmin.error.refreshedExpired':
        'The refreshed login has expired. Please sign in again.',
    'appealAdmin.error.invalidLogin':
        'Invalid login information: @error. Please sign in again.',
    'appealAdmin.error.adminOnly':
        'Access denied. This page is only available to administrators.',
    'appealAdmin.error.initFailed': 'Initialization failed: @error',
    'appealAdmin.error.roleCheckFailed': 'Role verification failed: @error',
    'appealAdmin.error.jwtAdminOnly':
        'Access denied: JWT roles are @roles, not administrator roles.',
    'appealAdmin.error.jwtRoleCheckFailed':
        'JWT role verification failed: @error',
    'appealAdmin.error.loadFailed': 'Failed to load appeal data: @error',
    'appealAdmin.error.request': 'Request error: @message',
    'appealAdmin.error.forbidden': 'No permission: @message',
    'appealAdmin.error.notFound': 'Not found: @message',
    'appealAdmin.error.duplicateRequest': 'Duplicate request: @message',
    'appealAdmin.error.server': 'Server error: @message',
    'appealAdmin.error.operationFailed': 'Operation failed: @error',
    'appealAdmin.error.invalidAppealId': 'The appeal ID is invalid.',
    'appealAdmin.search.appealReason': 'Search appeal reason',
    'appealAdmin.search.appellantName': 'Search appellant name',
    'appealAdmin.search.processStatus': 'Search processing status',
    'appealAdmin.search.timeRangeSelected': 'Search time range (selected)',
    'appealAdmin.view.appeals': 'Appeals',
    'appealAdmin.view.reviews': 'Reviews',
    'appealAdmin.review.search.reviewer': 'Search reviewer',
    'appealAdmin.review.search.reviewerDept': 'Search reviewer department',
    'appealAdmin.review.search.timeRangeSelected':
        'Search review time range (selected)',
    'appealAdmin.filter.byAppealReason': 'By appeal reason',
    'appealAdmin.filter.byAppellantName': 'By appellant name',
    'appealAdmin.filter.byProcessStatus': 'By processing status',
    'appealAdmin.filter.byTimeRange': 'By time range',
    'appealAdmin.review.filter.byReviewer': 'By reviewer',
    'appealAdmin.review.filter.byReviewerDept': 'By reviewer department',
    'appealAdmin.review.filter.byTimeRange': 'By review time range',
    'appealAdmin.card.reason': 'Reason: @value',
    'appealAdmin.card.status': 'Status: @value',
    'appealAdmin.card.time': 'Time: @value',
    'appealAdmin.review.empty': 'No appeal review records yet.',
    'appealAdmin.review.empty.filtered':
        'No appeal review records match the current filter.',
    'appealAdmin.review.loadFailed': 'Failed to load appeal reviews: @error',
    'appealAdmin.review.card.title': 'Appeal #@appealId · @level review',
    'appealAdmin.review.card.result': 'Result: @value',
    'appealAdmin.review.card.reviewer': 'Reviewer: @value',
    'appealAdmin.review.card.reviewerDept': 'Department: @value',
    'appealAdmin.review.card.time': 'Reviewed at: @value',
    'appealAdmin.review.card.opinion': 'Opinion: @value',
    'appealAdmin.review.level.primary': 'Primary',
    'appealAdmin.review.level.secondary': 'Secondary',
    'appealAdmin.review.level.final': 'Final',
    'appealAdmin.review.result.approved': 'Approved',
    'appealAdmin.review.result.rejected': 'Rejected',
    'appealAdmin.review.result.needResubmit': 'Need resubmit',
    'appealAdmin.review.result.transfer': 'Transfer',
    'appealAdmin.review.workbench.title': 'Review workbench',
    'appealAdmin.review.workbench.subtitle':
        'Track review workload, open queues, and today\'s output from one panel.',
    'appealAdmin.review.workbench.loadFailed':
        'Failed to load review workbench: @error',
    'appealAdmin.review.metric.primary': 'Primary reviews',
    'appealAdmin.review.metric.primary.helper':
        'Total records currently in the primary review layer.',
    'appealAdmin.review.metric.secondary': 'Secondary reviews',
    'appealAdmin.review.metric.secondary.helper':
        'Total records currently in the secondary review layer.',
    'appealAdmin.review.metric.final': 'Final reviews',
    'appealAdmin.review.metric.final.helper':
        'Total records currently in the final review layer.',
    'appealAdmin.review.metric.today': 'Reviewed today',
    'appealAdmin.review.metric.today.helper':
        'Reviews completed today in the current loaded dataset.',
    'appealAdmin.review.metric.pendingStart': 'Awaiting review start',
    'appealAdmin.review.metric.pendingStart.helper':
        'Accepted appeals that still have not entered formal review.',
    'appealAdmin.review.metric.inProgress': 'Under review',
    'appealAdmin.review.metric.inProgress.helper':
        'Appeals currently sitting in the active review stage.',
    'appealAdmin.review.metric.visibleTotal': 'Loaded review records: @count',
    'appealAdmin.review.metric.visibleApproved':
        'Approved in current list: @count',
    'appealAdmin.review.metric.visibleRejected':
        'Rejected in current list: @count',
    'appealAdmin.review.quick.today': 'Today\'s reviews',
    'appealAdmin.review.quick.pendingStart': 'Awaiting start appeals',
    'appealAdmin.review.quick.inProgress': 'Appeals under review',
    'appealAdmin.review.quick.refreshWorkbench': 'Refresh workbench',
    'appealAdmin.review.queue.title': 'Priority queue',
    'appealAdmin.review.queue.empty':
        'No accepted appeals are waiting for review right now.',
    'appealAdmin.review.queue.reason': 'Reason: @value',
    'appealAdmin.review.queue.status': 'Status: @value',
    'appealAdmin.review.queue.time': 'Latest node time: @value',
    'appealAdmin.result.approved': 'Appeal approved',
    'appealAdmin.success.approved': 'The appeal has been approved.',
    'appealAdmin.success.acceptanceRejected':
        'The appeal was not accepted. The user can resubmit after fixing the issue.',
    'appealAdmin.success.supplementRequested':
        'Supplemental materials have been requested for this appeal.',
    'appealAdmin.success.supplementCompleted':
        'The supplemental materials were marked complete and sent back for acceptance review.',
    'appealAdmin.success.resubmitted':
        'The appeal has been resubmitted for acceptance review.',
    'appealAdmin.success.finalRejected': 'The appeal review has been rejected.',
    'appealAdmin.note.awaitingApplicantSupplement':
        'Waiting for the appellant to submit supplementary materials.',
    'appealAdmin.note.awaitingApplicantResubmission':
        'Waiting for the appellant to resubmit the appeal.',
    'appealAdmin.dialog.rejectTitle': 'Reject appeal',
    'appealAdmin.dialog.requestSupplementTitle':
        'Request supplemental materials',
    'appealAdmin.field.rejectionReason': 'Rejection reason',
    'appealAdmin.field.supplementReason': 'Supplement request details',
    'appealAdmin.validation.rejectionReasonRequired':
        'Please enter a rejection reason.',
    'appealAdmin.validation.supplementReasonRequired':
        'Please enter the required supplemental materials.',
    'appealAdmin.action.approve': 'Approve',
    'appealAdmin.action.reject': 'Reject',
    'appealAdmin.action.relogin': 'Sign in again',
    'appealAdmin.action.confirmReject': 'Confirm rejection',
    'appealAdmin.action.confirmRequestSupplement': 'Confirm request',
    'appealAdmin.note.alreadyProcessed':
        'This appeal has already been processed and cannot be reviewed again.',
    'appealAdmin.note.adminApprovalOnly':
        'Access denied. Only administrators can review appeals.',
    'deductionAdmin.page.title': 'Deduction management',
    'deductionAdmin.action.add': 'Add deduction record',
    'deductionAdmin.action.refresh': 'Refresh list',
    'deductionAdmin.action.retry': 'Retry',
    'deductionAdmin.action.relogin': 'Sign in again',
    'deductionAdmin.action.edit': 'Edit deduction record',
    'deductionAdmin.action.delete': 'Delete deduction record',
    'deductionAdmin.search.handler': 'Search handler',
    'deductionAdmin.filter.byHandler': 'By handler',
    'deductionAdmin.filter.byTimeRange': 'By time range',
    'deductionAdmin.filter.dateRangeLabel':
        'Deduction date range: @start to @end',
    'deductionAdmin.filter.selectDateRange': 'Select a deduction date range',
    'deductionAdmin.filter.tooltip': 'Search by deduction date range',
    'deductionAdmin.filter.clearDateRange': 'Clear date range',
    'deductionAdmin.error.unauthorized': 'Unauthorized. Please sign in again.',
    'deductionAdmin.error.expired':
        'Your login has expired. Please sign in again.',
    'deductionAdmin.error.invalidLogin':
        'Invalid login information: @error. Please sign in again.',
    'deductionAdmin.error.adminOnly':
        'Access denied. This page is only available to administrators.',
    'deductionAdmin.error.initFailed': 'Initialization failed: @error',
    'deductionAdmin.error.loadFailed':
        'Failed to load deduction records: @error',
    'deductionAdmin.error.filteredEmpty':
        'No deduction records matched the current criteria.',
    'deductionAdmin.empty.default': 'There are no deduction records right now.',
    'deductionAdmin.error.request': 'Request error: @message',
    'deductionAdmin.error.forbidden': 'No permission: @message',
    'deductionAdmin.error.notFound': 'Not found: @message',
    'deductionAdmin.error.duplicateRequest': 'Duplicate request: @message',
    'deductionAdmin.error.server': 'Server error: @message',
    'deductionAdmin.error.operationFailed': 'Operation failed: @error',
    'deductionAdmin.card.points': 'Points deducted: @value',
    'deductionAdmin.card.summary':
        'Handler: @handler | Time: @time | Violation ID: @offenseId',
    'deductionAdmin.dialog.deleteTitle': 'Confirm deletion',
    'deductionAdmin.dialog.deleteBody':
        'Are you sure you want to delete this deduction record?',
    'deductionAdmin.success.deleted': 'Deduction record deleted successfully.',
    'deductionAdmin.error.deleteFailed':
        'Failed to delete deduction record: @error',
    'deductionAdmin.form.addTitle': 'Add deduction information',
    'deductionAdmin.form.editTitle': 'Edit deduction information',
    'deductionAdmin.field.offenseRecord': 'Violation record',
    'deductionAdmin.field.deductedPoints': 'Points deducted',
    'deductionAdmin.field.handler': 'Handler',
    'deductionAdmin.field.approver': 'Approver',
    'deductionAdmin.field.remarks': 'Remarks',
    'deductionAdmin.field.deductionTime': 'Deduction time',
    'deductionAdmin.helper.selectOffense': 'Please select a violation record.',
    'deductionAdmin.helper.nameOptional': 'Enter the @field name (optional).',
    'deductionAdmin.helper.points': 'Enter the number of points to deduct.',
    'deductionAdmin.helper.date': 'Please select the deduction date.',
    'deductionAdmin.validation.required': '@field cannot be empty.',
    'deductionAdmin.validation.pointsNumber':
        'Points deducted must be a number.',
    'deductionAdmin.validation.pointsNegative':
        'Points deducted cannot be negative.',
    'deductionAdmin.validation.pointsTooLarge':
        'Points deducted cannot exceed 12.',
    'deductionAdmin.validation.nameTooLong':
        '@field cannot exceed 100 characters.',
    'deductionAdmin.validation.remarksTooLong':
        'Remarks cannot exceed 255 characters.',
    'deductionAdmin.validation.dateInvalid': 'Invalid date format.',
    'deductionAdmin.validation.dateFuture':
        'The deduction date cannot be later than today.',
    'deductionAdmin.offense.option':
        'Violation ID: @id | Points: @points | Time: @time',
    'deductionAdmin.offense.fallbackOption': 'Violation ID: @id',
    'deductionAdmin.error.offenseLoadFailed':
        'Failed to load violation records: @error',
    'deductionAdmin.error.offenseSelectFailed':
        'Failed to select violation record: @error',
    'deductionAdmin.error.selectOffenseFirst':
        'Please select a violation record first.',
    'deductionAdmin.success.created': 'Deduction record created successfully.',
    'deductionAdmin.success.updated': 'Deduction record updated successfully.',
    'deductionAdmin.error.createFailed':
        'Failed to create deduction record: @error',
    'deductionAdmin.error.updateFailed':
        'Failed to update deduction record: @error',
    'vehicle.field.licensePlate': 'Plate number',
    'vehicle.field.vehicleType': 'Vehicle type',
    'vehicle.field.ownerName': 'Owner name',
    'vehicle.field.idCardNumber': 'ID card number',
    'vehicle.field.contactNumber': 'Contact number',
    'vehicle.field.engineNumber': 'Engine number',
    'vehicle.field.frameNumber': 'Frame number',
    'vehicle.field.vehicleColor': 'Vehicle color',
    'vehicle.field.firstRegistrationDate': 'First registration date',
    'vehicle.field.currentStatus': 'Current status',
    'vehicle.helper.plateSuffix': 'Enter the plate suffix, for example: 12345',
    'vehicle.helper.idCard': 'Enter a 15-digit or 18-digit ID card number',
    'vehicle.helper.contact': 'Enter an 11-digit mobile number',
    'vehicle.hint.modifyIdCardInProfile':
        'Please update the ID card number in profile management',
    'vehicle.validation.required': '@field cannot be empty',
    'vehicle.validation.licensePlateTooLong':
        'The plate number cannot exceed 20 characters.',
    'vehicle.validation.licensePlateInvalid':
        'Invalid plate number format, for example: province code + A12345.',
    'vehicle.validation.vehicleTypeTooLong':
        'The vehicle type cannot exceed 50 characters.',
    'vehicle.validation.ownerNameTooLong':
        'The owner name cannot exceed 100 characters.',
    'vehicle.validation.idCardRequired': 'The ID card number cannot be empty.',
    'vehicle.validation.idCardTooLong':
        'The ID card number cannot exceed 18 characters.',
    'vehicle.validation.idCardInvalid': 'Invalid ID card number format.',
    'vehicle.validation.contactTooLong':
        'The contact number cannot exceed 20 characters.',
    'vehicle.validation.contactInvalid':
        'Please enter a valid 11-digit mobile number.',
    'vehicle.validation.engineTooLong':
        'The engine number cannot exceed 50 characters.',
    'vehicle.validation.frameTooLong':
        'The frame number cannot exceed 50 characters.',
    'vehicle.validation.colorTooLong':
        'The vehicle color cannot exceed 50 characters.',
    'vehicle.validation.dateInvalid': 'Invalid date format.',
    'vehicle.validation.dateFuture':
        'The first registration date cannot be later than today.',
    'vehicle.validation.statusTooLong':
        'The current status cannot exceed 50 characters.',
    'vehicle.error.jwtMissingRelogin':
        'JWT was not found. Please sign in again.',
    'vehicle.error.jwtMissing': 'JWT was not found.',
    'vehicle.error.usernameMissingInJwt': 'Username was not found in the JWT.',
    'vehicle.error.driverIdCardMissing':
        'The ID card number was not found. Please complete the driver profile first.',
    'vehicle.error.initializeFailed': 'Initialization failed: @error',
    'vehicle.error.missingIdCard':
        'The ID card number is missing, so vehicle information cannot be loaded.',
    'vehicle.empty.filtered': 'No vehicles matched the current criteria.',
    'vehicle.empty': 'You do not have any vehicle records yet.',
    'vehicle.error.invalidQuery':
        'The ID card number or search query is invalid. Please try again.',
    'vehicle.error.expired': 'Your login has expired. Please sign in again.',
    'vehicle.error.refreshedExpired':
        'The refreshed login information has expired. Please sign in again.',
    'vehicle.error.invalidLogin':
        'Invalid login information. Please sign in again.',
    'vehicle.error.roleCheckFailed': 'Role verification failed: @error',
    'vehicle.error.notFound': 'No vehicle records were found.',
    'vehicle.error.suggestionFailed': 'Failed to load suggestions: @error',
    'vehicle.error.userInfoLoadFailed':
        'Failed to load user information: @error',
    'vehicle.error.driverInfoLoadFailed':
        'Failed to load driver information: @error',
    'vehicle.error.idMissingDelete':
        'Unable to delete because the vehicle ID is missing.',
    'vehicle.error.notFoundBySearchType':
        'No vehicle matched the current search. The @field "@query" may not exist.',
    'vehicle.error.unauthorized': 'Unauthorized. Please sign in again.',
    'vehicle.error.loadFailed': 'Failed to load vehicle information: @error',
    'vehicle.success.deleted': 'Vehicle deleted successfully.',
    'vehicle.error.deleteFailed': 'Failed to delete vehicle: @error',
    'vehicle.dialog.deleteTitle': 'Confirm deletion',
    'vehicle.dialog.deleteConfirm':
        'Are you sure you want to @action this vehicle? This action cannot be undone.',
    'vehicle.action.delete': 'Delete',
    'vehicle.action.edit': 'Edit',
    'vehicle.action.refresh': 'Refresh vehicles',
    'vehicle.action.addInfo': 'Add vehicle information',
    'vehicle.action.add': 'Add vehicle',
    'vehicle.action.relogin': 'Sign in again',
    'vehicle.action.goLogin': 'Go to login',
    'vehicle.search.plateHint': 'Search plate number',
    'vehicle.search.typeHint': 'Search vehicle type',
    'vehicle.search.byPlate': 'By plate number',
    'vehicle.search.byType': 'By vehicle type',
    'vehicle.filter.dateRangeLabel': 'First registration date: @start to @end',
    'vehicle.filter.selectDateRange': 'Select a first registration date range',
    'vehicle.filter.tooltip': 'Search by first registration date range',
    'vehicle.filter.startDate': 'Start date',
    'vehicle.filter.endDate': 'End date',
    'vehicle.filter.clearDateRange': 'Clear date range',
    'vehicle.page.title': 'Vehicle management',
    'vehicle.workspace.eyebrow': 'Vehicle workspace',
    'vehicle.workspace.title': 'Vehicle operations and registration overview',
    'vehicle.workspace.subtitle':
        'Monitor loaded vehicles, active availability, and registration coverage while keeping search and cleanup actions in one place.',
    'vehicle.workspace.signal.query': 'Search active: @value',
    'vehicle.workspace.signal.queryIdle': 'Search is currently idle',
    'vehicle.workspace.signal.rangeIdle': 'No registration date range selected',
    'vehicle.workspace.metric.loaded': 'Loaded',
    'vehicle.workspace.metric.visible': 'Visible',
    'vehicle.workspace.metric.active': 'Active',
    'vehicle.workspace.metric.inactive': 'Inactive',
    'vehicle.workspace.metric.type': 'Types',
    'vehicle.workspace.filterEyebrow': 'Filters',
    'vehicle.workspace.filterTitle': 'Refine the vehicle workspace',
    'vehicle.workspace.filterBody':
        'Switch search mode, review autocomplete results, and narrow the list by first registration date range.',
    'vehicle.workspace.filterMode': 'Search mode',
    'vehicle.workspace.filterReset': 'Clear filters',
    'vehicle.workspace.filterRefresh': 'Refresh list',
    'vehicle.workspace.listEyebrow': 'Records',
    'vehicle.workspace.listTitle': 'Vehicle records',
    'vehicle.workspace.listBody':
        'Review current status, ownership details, and registration signals before opening a detailed record.',
    'vehicle.workspace.emptyTitle': 'No vehicles available',
    'vehicle.workspace.errorTitle': 'Vehicle workspace unavailable',
    'vehicle.card.plate': 'Plate number: @value',
    'vehicle.card.type': 'Type: @value',
    'vehicle.card.owner': 'Owner: @value',
    'vehicle.card.status': 'Status: @value',
    'vehicle.value.noPlate': 'Unknown plate number',
    'vehicle.value.noType': 'Unknown vehicle type',
    'vehicle.value.noOwner': 'Unknown owner',
    'vehicle.status.active': 'Active',
    'vehicle.status.inactive': 'Inactive',
    'vehicle.status.suspended': 'Suspended',
    'vehicle.status.archived': 'Archived',
    'vehicle.error.driverInfoMissingDetailed':
        'Could not get the driver information or name. Driver ID: @driverId, Username: @username',
    'vehicle.error.driverInfoMissing':
        'Could not get the driver information or name.',
    'vehicle.error.plateInvalid':
        'Invalid plate number format. Please enter a valid plate number, for example: province code + A12345.',
    'vehicle.error.plateExists':
        'The plate number already exists. Please use another one.',
    'vehicle.error.fillIdCardInProfile':
        'Please fill in the ID card number in personal profile management first.',
    'vehicle.success.created': 'Vehicle created successfully.',
    'vehicle.error.createFailed': 'Failed to create vehicle: @error',
    'vehicle.error.httpStatus': 'Request failed (HTTP @statusCode).',
    'vehicle.add.title': 'Add a new vehicle',
    'vehicle.add.emptyPrompt':
        'You do not have any vehicle records yet. Please add a new vehicle.',
    'vehicle.edit.title': 'Edit vehicle information',
    'vehicle.success.updated': 'Vehicle updated successfully.',
    'vehicle.error.updateFailed': 'Failed to update vehicle: @error',
    'vehicle.error.permissionLoadFailed': 'Failed to load permissions: @error',
    'vehicle.detail.title': 'Vehicle details',
    'vehicle.detail.editTooltip': 'Edit vehicle information',
    'vehicle.detail.deleteTooltip': 'Delete vehicle',
    'vehicle.detail.type': 'Vehicle type',
    'vehicle.detail.plate': 'Plate number',
    'vehicle.detail.owner': 'Owner name',
    'vehicle.detail.status': 'Vehicle status',
    'vehicle.detail.idCard': 'ID card number',
    'vehicle.detail.contact': 'Contact number',
    'vehicle.detail.engine': 'Engine number',
    'vehicle.detail.frame': 'Frame number',
    'vehicle.detail.color': 'Vehicle color',
    'vehicle.detail.firstRegistrationDate': 'First registration date',
    'common.close': 'Close',
    'common.details': 'Details',
    'common.error': 'Error',
    'common.location.default': 'Harbin',
    'common.pageNotFound': 'Page not found',
    'dashboard.error.title': 'Error',
    'dashboard.projectName': 'Traffic Violation Processing Management System',
    'dashboard.task.todo1': 'To-do task 1',
    'dashboard.task.inProgress1': 'In-progress task 1',
    'dashboard.task.done1': 'Completed task 1',
    'chart.title.presentation': 'Chart presentation',
    'chart.currentTimeLabel': 'Current time:',
    'captcha.dialog.title': 'CAPTCHA verification',
    'captcha.action.verify': 'Verify CAPTCHA',
    'captcha.input.label': 'Enter CAPTCHA',
    'captcha.input.hint': 'Please enter the CAPTCHA',
    'captcha.validation.required': 'Please enter the CAPTCHA',
    'captcha.validation.length': 'The CAPTCHA must be @length characters long.',
    'captcha.validation.invalid': 'Incorrect CAPTCHA. Please try again.',
    'chat.modal.title': 'Notice',
    'chat.confirmAction.title': 'Confirm action',
    'chat.confirmAction.message':
        'The agent suggested an executable action. Continue?',
    'chat.error.requestTitle': 'Agent request failed',
    'chat.error.requestBody': 'The request failed. Please try again later.',
    'chat.error.noContent': 'No content was returned.',
    'chat.error.actionUnavailableTitle': 'Action unavailable',
    'chat.error.actionUnavailableBody':
        'The current action has no executable target.',
    'chat.status.preparing': 'Preparing a response...',
    'chat.status.processing': 'Processing...',
    'today.location.default': 'Harbin',
    'news.menu.title': 'User guide',
    'news.menu.latest.title': 'Latest traffic violation news',
    'news.menu.latest.description':
        'Stay updated on recent policy changes and enforcement activity',
    'news.menu.fine.title': 'Fine payment notice',
    'news.menu.fine.description': 'View the latest guidance for paying fines',
    'news.menu.quickGuide.title': 'Accident quick-handling guide',
    'news.menu.quickGuide.description':
        'Learn the key steps for handling an accident quickly',
    'news.menu.progress.title': 'Accident handling progress overview',
    'news.menu.progress.description':
        'Learn how to track accident handling status',
    'news.menu.evidence.title': 'Accident evidence materials',
    'news.menu.evidence.description':
        'Check the evidence materials required for accident handling',
    'news.menu.video.title': 'Accident video quick handling',
    'news.menu.video.description':
        'Improve accident handling efficiency with video evidence',
    'news.accidentEvidence.title': 'Accident evidence materials',
    'news.accidentEvidence.section.required': 'Required evidence',
    'news.accidentEvidence.photo.title': 'Photo materials',
    'news.accidentEvidence.photo.body':
        'Provide photos of the accident scene, vehicle damage, and road conditions from multiple angles.',
    'news.accidentEvidence.video.title': 'Video materials',
    'news.accidentEvidence.video.body':
        'Dashcam or surveillance videos can significantly improve processing efficiency.',
    'news.accidentEvidence.detail.title': 'Accident details',
    'news.accidentEvidence.detail.body':
        'Include the accident time, location, weather conditions, and driver information for both parties.',
    'news.accidentQuickGuide.title': 'Accident quick-handling guide',
    'news.accidentQuickGuide.section.steps': 'Quick handling steps',
    'news.accidentQuickGuide.section.notice': 'Important notes',
    'news.accidentQuickGuide.step1.title': '1. Ensure safety',
    'news.accidentQuickGuide.step1.body':
        'Move the vehicle to a safe location and turn on the hazard lights.',
    'news.accidentQuickGuide.step2.title': '2. Take photos',
    'news.accidentQuickGuide.step2.body':
        'Take accident scene photos from at least three different angles.',
    'news.accidentQuickGuide.step3.title': '3. Submit online',
    'news.accidentQuickGuide.step3.body':
        'Upload photos through the system and fill in the accident details.',
    'news.accidentQuickGuide.step4.title': '4. Time limit',
    'news.accidentQuickGuide.step4.body':
        'Submit within 24 hours after the accident occurs.',
    'news.accidentProgress.title': 'Accident handling status tracking',
    'news.accidentProgress.section.howTo':
        'How to track accident handling status',
    'news.accidentProgress.step1.title': '1. Sign in to the system',
    'news.accidentProgress.step1.body':
        'Sign in with your account, then open the user dashboard of the traffic violation processing system.',
    'news.accidentProgress.step2.title': '2. Open accident management',
    'news.accidentProgress.step2.body':
        'Choose the accident management entry on the dashboard to view submitted accident records.',
    'news.accidentProgress.step3.title': '3. Check progress details',
    'news.accidentProgress.step3.body':
        'Open a specific accident record to see statuses such as submitted, under review, or completed.',
    'news.accidentProgress.section.tips': 'Practical tips',
    'news.accidentProgress.tip1.title': 'Check regularly',
    'news.accidentProgress.tip1.body':
        'Sign in weekly to check progress so you can respond to review requests in time.',
    'news.accidentProgress.tip2.title': 'Notification settings',
    'news.accidentProgress.tip2.body':
        'Enable system notifications to receive real-time status updates and avoid missing important information.',
    'news.accidentVideo.title': 'Accident video quick handling',
    'news.accidentVideo.section.flow': 'Video quick-handling flow',
    'news.accidentVideo.step1.title': '1. Record a video',
    'news.accidentVideo.step1.body':
        'Record an accident scene video with a duration of no more than 1 minute.',
    'news.accidentVideo.step2.title': '2. Upload the video',
    'news.accidentVideo.step2.body':
        'Upload the video file through the system. MP4 format is supported.',
    'news.accidentVideo.step3.title': '3. Submit for review',
    'news.accidentVideo.step3.body':
        'Fill in the accident details and submit them for processing.',
    'news.accidentVideo.section.advantages': 'Advantages',
    'news.accidentVideo.advantage.title': 'Fast and efficient',
    'news.accidentVideo.advantage.body':
        'Video-based quick handling reduces on-site waiting time and can complete review within 24 hours.',
    'news.fineNotice.title': 'Fine payment notice',
    'news.fineNotice.section.flow': 'Payment flow',
    'news.fineNotice.step1.title': '1. Open fine management',
    'news.fineNotice.step1.body':
        'Open the fine management module to view pending fine records.',
    'news.fineNotice.step2.title': '2. Select a fine record',
    'news.fineNotice.step2.body':
        'Check the fine amount and deduction information.',
    'news.fineNotice.step3.title': '3. Confirm payment',
    'news.fineNotice.step3.body':
        'Online payment is supported, and the system updates the status automatically after completion.',
    'news.fineNotice.section.tip': 'Reminder',
    'news.fineNotice.tip.title': 'Pay on time',
    'news.fineNotice.tip.body':
        'Overdue payment may cause extra fees or affect driving credit.',
    'news.latest.title': 'Latest traffic violation news',
    'news.latest.section.headlines': 'Headlines',
    'news.latest.item1.title': '2025 new traffic rules take effect',
    'news.latest.item1.body':
        'Starting on January 1, 2025, speeding by more than 10% may lead to higher fines and more points in order to improve road safety.',
    'news.latest.section.recent': 'Recent updates',
    'news.latest.item2.title': 'Special drunk-driving campaign launched',
    'news.latest.item2.body':
        'A three-month drunk-driving enforcement campaign is underway nationwide, with more than 3,000 violations already handled.',
    'news.latest.item3.title': 'Smart monitoring upgraded',
    'news.latest.item3.body':
        'An additional 1,000 smart cameras now cover major cities to automatically detect red-light running and speeding.',
    'news.latest.section.expert': 'Expert advice',
    'news.latest.expert.title': 'Follow traffic regulations',
    'news.latest.expert.body':
        'Experts urge drivers to follow the new rules strictly to avoid unnecessary fines and safety risks.',
    'news.latest.heroLabel': 'Live headline',
    'news.latest.section.liveFeed': 'Live traffic feed',
    'news.latest.loading': 'Loading live traffic news...',
    'news.latest.emptyRealtime': 'No live traffic news is available right now.',
    'news.latest.loadFailed': 'Failed to load live traffic news: @error',
    'news.latest.action.retry': 'Retry',
    'news.latest.action.refresh': 'Refresh live news',
    'news.latest.field.source': 'Source: @value',
    'news.latest.field.publishedAt': 'Published: @value',
    'news.latest.source.unknown': 'Unknown source',
    'scan.pageTitle': 'QR code generator',
    'scan.dialog.fineQr': 'Fine QR code',
    'scan.dialog.genericQr': 'QR code',
    'scan.action.generate': 'Generate QR code',
    'scan.action.regenerate': 'Regenerate',
    'scan.error.generateFailed': 'Failed to generate QR code: @error',
    'scan.fineDetail.title': 'Fine details',
    'scan.field.fineId': 'Fine ID',
    'scan.field.fineAmount': 'Fine amount',
    'scan.field.payee': 'Payee',
    'scan.field.paymentStatus': 'Payment status',
    'scan.status.notGenerated': 'The QR code has not been generated yet.',
    'scan.status.generated': 'QR code generated',
    'scan.status.waiting': 'Waiting to generate QR code',
    'questions.user.title': 'Common user questions',
    'questions.user.item1': 'How do I check my traffic violation records?',
    'questions.user.item2': 'What is the process for paying a fine?',
    'questions.user.item3':
        'What materials are required for a traffic violation appeal?',
    'questions.user.item4': 'When does my fine expire?',
    'questions.user.item5': 'How do I handle a speeding violation?',
    'questions.admin.title': 'Predefined admin questions',
    'questions.admin.item1':
        'How do I view all unprocessed traffic violation records?',
    'questions.admin.item2':
        'How do I calculate the total fine payments for this month?',
    'questions.admin.item3':
        'Which traffic violation appeals are pending review?',
    'questions.admin.item4': 'How do I bulk update fine due statuses?',
    'questions.admin.item5':
        'What is the handling process for speeding violations?',
    'validation.required': 'This field is required.',
    'lookup.taskType.todo': 'To-do',
    'lookup.taskType.inProgress': 'In progress',
    'lookup.taskType.done': 'Completed',
    'lookup.paymentStatus.unpaid': 'Unpaid',
    'lookup.paymentStatus.partial': 'Partially paid',
    'lookup.paymentStatus.paid': 'Paid',
    'lookup.paymentStatus.overdue': 'Overdue',
    'lookup.paymentStatus.waived': 'Waived',
    'lookup.offenseProcessStatus.unprocessed': 'Unprocessed',
    'lookup.offenseProcessStatus.processing': 'Processing',
    'lookup.offenseProcessStatus.processed': 'Processed',
    'lookup.offenseProcessStatus.appealing': 'Under appeal',
    'lookup.offenseProcessStatus.appealApproved': 'Appeal approved',
    'lookup.offenseProcessStatus.appealRejected': 'Appeal rejected',
    'lookup.offenseProcessStatus.cancelled': 'Cancelled',
    'lookup.deductionStatus.effective': 'Effective',
    'lookup.deductionStatus.cancelled': 'Cancelled',
    'lookup.deductionStatus.restored': 'Restored',
    'lookup.appealAcceptanceStatus.pending': 'Pending acceptance',
    'lookup.appealAcceptanceStatus.accepted': 'Accepted',
    'lookup.appealAcceptanceStatus.rejected': 'Rejected',
    'lookup.appealAcceptanceStatus.needSupplement': 'Supplement required',
    'lookup.appealProcessStatus.unprocessed': 'Unprocessed',
    'lookup.appealProcessStatus.underReview': 'Under review',
    'lookup.appealProcessStatus.approved': 'Approved',
    'lookup.appealProcessStatus.rejected': 'Rejected',
    'lookup.appealProcessStatus.withdrawn': 'Withdrawn',
    'lookup.paymentEventType.partialPay': 'Partial payment',
    'lookup.paymentEventType.completePayment': 'Complete payment',
    'lookup.paymentEventType.markOverdue': 'Mark overdue',
    'lookup.paymentEventType.waiveFine': 'Waive fine',
    'lookup.paymentEventType.continuePayment': 'Continue payment',
    'lookup.deductionEventType.cancel': 'Cancel deduction',
    'lookup.deductionEventType.restore': 'Restore deduction',
    'lookup.deductionEventType.reactivate': 'Reactivate',
    'lookup.offenseProcessEventType.startProcessing': 'Start processing',
    'lookup.offenseProcessEventType.completeProcessing': 'Complete processing',
    'lookup.offenseProcessEventType.submitAppeal': 'Submit appeal',
    'lookup.offenseProcessEventType.approveAppeal': 'Approve appeal',
    'lookup.offenseProcessEventType.rejectAppeal': 'Reject appeal',
    'lookup.offenseProcessEventType.cancel': 'Cancel record',
    'lookup.offenseProcessEventType.withdrawAppeal': 'Withdraw appeal',
    'lookup.appealAcceptanceEventType.accept': 'Accept appeal',
    'lookup.appealAcceptanceEventType.reject': 'Reject appeal',
    'lookup.appealAcceptanceEventType.requestSupplement':
        'Request supplementary materials',
    'lookup.appealAcceptanceEventType.supplementComplete':
        'Supplement completed',
    'lookup.appealAcceptanceEventType.resubmit': 'Resubmit',
    'lookup.appealProcessEventType.startReview': 'Start review',
    'lookup.appealProcessEventType.approve': 'Approve appeal',
    'lookup.appealProcessEventType.reject': 'Reject appeal',
    'lookup.appealProcessEventType.withdraw': 'Withdraw appeal',
    'lookup.appealProcessEventType.reopenReview': 'Reopen review',
    'dashboard.error.adminOnlyFunction':
        'Insufficient permissions: only administrators can access this feature.',
    'dashboard.offense.unknownType': 'Unknown type',
  };

  static const Map<String, String> _zhCn = {
    'validation.required': '此字段为必填项',
    'lookup.taskType.todo': '待办',
    'lookup.taskType.inProgress': '进行中',
    'lookup.taskType.done': '已完成',
    'lookup.paymentStatus.unpaid': '未支付',
    'lookup.paymentStatus.partial': '部分支付',
    'lookup.paymentStatus.paid': '已支付',
    'lookup.paymentStatus.overdue': '已逾期',
    'lookup.paymentStatus.waived': '已减免',
    'lookup.offenseProcessStatus.unprocessed': '未处理',
    'lookup.offenseProcessStatus.processing': '处理中',
    'lookup.offenseProcessStatus.processed': '已处理',
    'lookup.offenseProcessStatus.appealing': '申诉中',
    'lookup.offenseProcessStatus.appealApproved': '申诉通过',
    'lookup.offenseProcessStatus.appealRejected': '申诉驳回',
    'lookup.offenseProcessStatus.cancelled': '已取消',
    'lookup.deductionStatus.effective': '生效中',
    'lookup.deductionStatus.cancelled': '已取消',
    'lookup.deductionStatus.restored': '已恢复',
    'lookup.appealAcceptanceStatus.pending': '待受理',
    'lookup.appealAcceptanceStatus.accepted': '已受理',
    'lookup.appealAcceptanceStatus.rejected': '不予受理',
    'lookup.appealAcceptanceStatus.needSupplement': '需补充材料',
    'lookup.appealProcessStatus.unprocessed': '未处理',
    'lookup.appealProcessStatus.underReview': '审核中',
    'lookup.appealProcessStatus.approved': '已批准',
    'lookup.appealProcessStatus.rejected': '已驳回',
    'lookup.appealProcessStatus.withdrawn': '已撤回',
    'lookup.paymentEventType.partialPay': '部分支付',
    'lookup.paymentEventType.completePayment': '完成支付',
    'lookup.paymentEventType.markOverdue': '标记逾期',
    'lookup.paymentEventType.waiveFine': '减免罚款',
    'lookup.paymentEventType.continuePayment': '继续支付',
    'lookup.deductionEventType.cancel': '取消扣分',
    'lookup.deductionEventType.restore': '恢复扣分',
    'lookup.deductionEventType.reactivate': '重新生效',
    'lookup.offenseProcessEventType.startProcessing': '开始处理',
    'lookup.offenseProcessEventType.completeProcessing': '完成处理',
    'lookup.offenseProcessEventType.submitAppeal': '提交申诉',
    'lookup.offenseProcessEventType.approveAppeal': '申诉通过',
    'lookup.offenseProcessEventType.rejectAppeal': '申诉驳回',
    'lookup.offenseProcessEventType.cancel': '取消记录',
    'lookup.offenseProcessEventType.withdrawAppeal': '撤回申诉',
    'lookup.appealAcceptanceEventType.accept': '受理申诉',
    'lookup.appealAcceptanceEventType.reject': '拒绝受理',
    'lookup.appealAcceptanceEventType.requestSupplement': '要求补充材料',
    'lookup.appealAcceptanceEventType.supplementComplete': '补充完成',
    'lookup.appealAcceptanceEventType.resubmit': '重新提交',
    'lookup.appealProcessEventType.startReview': '开始审核',
    'lookup.appealProcessEventType.approve': '批准申诉',
    'lookup.appealProcessEventType.reject': '驳回申诉',
    'lookup.appealProcessEventType.withdraw': '撤回申诉',
    'lookup.appealProcessEventType.reopenReview': '重新审核',
    'dashboard.error.adminOnlyFunction': '权限不足：仅管理员可访问此功能。',
    'dashboard.offense.unknownType': '未知类型',
    'app.name': '\u4ea4\u901a Agent',
    'common.cancel': '\u53d6\u6d88',
    'common.continue': '\u7ee7\u7eed',
    'common.login': '\u767b\u5f55',
    'common.register': '\u6ce8\u518c',
    'common.settings': '\u8bbe\u7f6e',
    'common.profile': '\u4e2a\u4eba\u8d44\u6599',
    'common.home': '\u9996\u9875',
    'common.theme': '\u4e3b\u9898',
    'common.agent': 'Agent',
    'common.online': '\u5728\u7ebf',
    'common.loading': '\u52a0\u8f7d\u4e2d',
    'common.focus': '\u5f53\u524d\u7126\u70b9',
    'common.today': '\u4eca\u65e5',
    'common.workspace': '\u5de5\u4f5c\u533a',
    'common.userWorkspace': '\u7528\u6237\u5de5\u4f5c\u53f0',
    'common.adminConsole': '\u7ba1\u7406\u63a7\u5236\u53f0',
    'common.managerConsole': '\u4e1a\u52a1\u63a7\u5236\u53f0',
    'common.openAgent': '\u6253\u5f00 Agent',
    'common.search': '\u68c0\u7d22',
    'common.language': '\u8bed\u8a00',
    'common.language.zh': '\u4e2d\u6587',
    'common.language.en': '\u82f1\u6587',
    'common.confirm': '\u786e\u5b9a',
    'common.ok': '\u597d\u7684',
    'common.success': '\u6210\u529f',
    'common.failed': '\u5931\u8d25',
    'common.save': '\u4fdd\u5b58',
    'common.create': '\u521b\u5efa',
    'common.submit': '\u63d0\u4ea4',
    'common.edit': '\u7f16\u8f91',
    'common.feedback': '\u53cd\u9988',
    'common.logout': '\u767b\u51fa',
    'common.backHome': '\u8fd4\u56de\u9996\u9875',
    'common.unknown': '\u672a\u77e5',
    'common.noData': '\u65e0\u6570\u636e',
    'common.notFilled': '\u672a\u586b\u5199',
    'common.calculating': '\u8ba1\u7b97\u4e2d...',
    'common.labelWithColon': '@label\uff1a',
    'common.labelWithValue': '@label\uff1a@value',
    'common.status.pending': '\u5f85\u5ba1\u6838',
    'common.status.approved': '\u5df2\u6279\u51c6',
    'common.status.rejected': '\u5df2\u62d2\u7edd',
    'common.toggleTheme': '\u5207\u6362\u4e3b\u9898',
    'common.switchLanguage': '\u5207\u6362\u8bed\u8a00',
    'common.dark': '\u6df1\u8272',
    'common.light': '\u6d45\u8272',
    'api.error.notAuthenticated':
        '\u60a8\u5c1a\u672a\u767b\u5f55\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55\u3002',
    'api.error.unknown': '\u672a\u77e5\u9519\u8bef\u3002',
    'api.error.emptyResponse':
        '\u670d\u52a1\u5668\u8fd4\u56de\u4e86\u7a7a\u54cd\u5e94\u3002',
    'api.error.httpStatus':
        '\u8bf7\u6c42\u5931\u8d25\uff08HTTP @statusCode\uff09\u3002',
    'api.error.missingRequiredParam':
        '\u7f3a\u5c11\u5fc5\u586b\u53c2\u6570\uff1a@param\u3002',
    'api.error.missingRequiredParams':
        '\u7f3a\u5c11\u5fc5\u586b\u53c2\u6570\uff1a@params\u3002',
    'api.error.duplicateRequestIdempotency':
        '\u68c0\u6d4b\u5230\u91cd\u590d\u8bf7\u6c42\uff0cidempotencyKey\uff1a@key\u3002',
    'api.error.endpointRemoved':
        '\u63a5\u53e3\u5df2\u79fb\u9664\uff1a@endpoint',
    'api.error.entityNotFoundWithId':
        '\u672a\u627e\u5230@entity\uff0cID\uff1a@id\u3002',
    'api.error.adminOnlyDelete':
        '\u672a\u6388\u6743\uff1a\u4ec5 ADMIN \u53ef\u5220\u9664@resource',
    'api.error.invalidRequestData': '\u8bf7\u6c42\u6570\u636e\u65e0\u6548',
    'api.error.cannotDetermineUserRole':
        '\u65e0\u6cd5\u786e\u5b9a\u5f53\u524d\u7528\u6237\u89d2\u8272\u3002',
    'api.entity.driver': '\u9a7e\u9a76\u4eba',
    'api.entity.offense': '\u8fdd\u6cd5\u8bb0\u5f55',
    'api.entity.fine': '\u7f5a\u6b3e\u8bb0\u5f55',
    'api.resource.drivers': '\u9a7e\u9a76\u4eba',
    'api.resource.offenses': '\u8fdd\u6cd5\u8bb0\u5f55',
    'api.resource.fines': '\u7f5a\u6b3e\u8bb0\u5f55',
    'shell.workspaceLabel': '\u5de5\u4f5c\u533a',
    'shell.footer': '\u4ea4\u901a Agent \u5de5\u4f5c\u533a',
    'shell.openChat': '\u6253\u5f00 Agent \u4fa7\u680f',
    'auth.validation.emailRequired': '\u90ae\u7bb1\u4e0d\u80fd\u4e3a\u7a7a',
    'auth.validation.emailInvalid':
        '\u8bf7\u8f93\u5165\u6709\u6548\u7684\u90ae\u7bb1\u5730\u5740',
    'auth.validation.passwordRequired': '\u5bc6\u7801\u4e0d\u80fd\u4e3a\u7a7a',
    'auth.validation.passwordShort':
        '\u5bc6\u7801\u81f3\u5c11\u9700\u8981 5 \u4f4d',
    'auth.error.passwordMismatch':
        '\u4e24\u6b21\u8f93\u5165\u7684\u5bc6\u7801\u4e0d\u4e00\u81f4',
    'auth.error.registering':
        '\u6ce8\u518c\u8bf7\u6c42\u5df2\u63d0\u4ea4\uff0c\u8bf7\u7a0d\u540e\u518d\u8bd5',
    'auth.error.registerCancelled':
        '\u5df2\u53d6\u6d88\u6ce8\u518c\u6d41\u7a0b',
    'auth.error.loginRequiredForReset':
        '\u5f53\u524d\u540e\u7aef\u8981\u6c42\u5148\u767b\u5f55\u540e\u518d\u6267\u884c\u5bc6\u7801\u91cd\u7f6e',
    'auth.error.loginFailed': '\u767b\u5f55\u5931\u8d25',
    'auth.error.invalidJwt': '\u767b\u5f55\u51ed\u8bc1\u65e0\u6548\u3002',
    'auth.error.registerFailed': '\u6ce8\u518c\u5931\u8d25',
    'auth.error.loginError': '\u767b\u5f55\u5f02\u5e38: @error',
    'auth.error.registerError': '\u6ce8\u518c\u5f02\u5e38: @error',
    'auth.error.passwordResetCancelled':
        '\u5df2\u53d6\u6d88\u5bc6\u7801\u91cd\u7f6e',
    'auth.error.passwordResetFailed':
        '\u5bc6\u7801\u91cd\u7f6e\u5931\u8d25: @code',
    'auth.error.passwordResetError':
        '\u5bc6\u7801\u91cd\u7f6e\u5f02\u5e38: @error',
    'auth.error.currentPasswordIncorrect':
        '\u5f53\u524d\u5bc6\u7801\u4e0d\u6b63\u786e',
    'auth.success.passwordUpdated': '\u5bc6\u7801\u5df2\u66f4\u65b0',
    'auth.resetPassword': '\u91cd\u7f6e\u5bc6\u7801',
    'auth.email': '\u90ae\u7bb1',
    'auth.password': '\u5bc6\u7801',
    'auth.currentPassword': '\u5f53\u524d\u5bc6\u7801',
    'auth.newPassword': '\u65b0\u5bc6\u7801',
    'auth.confirmPassword': '\u786e\u8ba4\u5bc6\u7801',
    'auth.createAccount': '\u521b\u5efa\u8d26\u53f7',
    'auth.backToLogin': '\u8fd4\u56de\u767b\u5f55',
    'auth.enterWorkspace': '\u8fdb\u5165\u5de5\u4f5c\u53f0',
    'auth.enterWorkspaceBody':
        '\u4f7f\u7528\u90ae\u7bb1\u548c\u5bc6\u7801\u767b\u5f55\uff0c\u6216\u521b\u5efa\u4e00\u4e2a\u65b0\u8d26\u53f7\u540e\u76f4\u63a5\u8fdb\u5165\u3002',
    'auth.signingIn': '\u767b\u5f55\u4e2d...',
    'auth.creating': '\u6ce8\u518c\u4e2d...',
    'auth.brandBadge': '\u4ea4\u901a\u8fdd\u6cd5\u5904\u7406\u5de5\u4f5c\u533a',
    'auth.brandTitle':
        '\u91cd\u6784\u540e\u7684\u66f4\u6e05\u723d\u767b\u5f55\u5165\u53e3',
    'auth.brandBody':
        '\u65e7\u6837\u5f0f\u5df2\u88ab\u79fb\u9664\uff0c\u73b0\u5728\u767b\u5f55\u9875\u6539\u6210\u54c1\u724c\u9762\u677f\u3001\u7b80\u6d01\u8ba4\u8bc1\u5361\u7247\u548c\u66f4\u6e05\u6670\u7684\u4fe1\u606f\u5c42\u7ea7\u3002',
    'auth.metric.mode': '\u6a21\u5f0f',
    'auth.metric.flow': '\u6d41\u7a0b',
    'auth.metric.agent': 'Agent',
    'auth.metric.flowValue': '\u767b\u5f55 / \u6ce8\u518c',
    'auth.metric.agentValue': '\u5df2\u5c31\u7eea',
    'auth.promptIdeas': '\u793a\u4f8b\u6307\u4ee4',
    'auth.promptLine1':
        '\u5e2e\u6211\u627e\u5230\u4eca\u5929\u6700\u5feb\u7684\u4e1a\u52a1\u5165\u53e3',
    'auth.promptLine2':
        '\u6253\u5f00\u7ba1\u7406\u65e5\u5fd7\u4e2d\u5fc3\uff0c\u5e76\u7ed9\u6211\u4e00\u4e2a\u5904\u7406\u987a\u5e8f',
    'user.title': '\u7528\u6237\u5de5\u4f5c\u53f0',
    'user.subtitle':
        '\u4e3a\u8fdb\u5ea6\u3001\u8bb0\u5f55\u3001\u8d44\u6599\u548c Agent \u534f\u4f5c\u91cd\u6784\u7684\u7b80\u6d01\u9996\u9875',
    'user.pageTitle': '\u4e1a\u52a1\u9875\u9762',
    'user.nav.progress': '\u8fdb\u5ea6',
    'user.nav.records': '\u8bb0\u5f55',
    'user.nav.news': '\u8d44\u8baf',
    'user.nav.support': '\u54a8\u8be2',
    'user.hero.badge': '\u7528\u6237\u5de5\u4f5c\u533a',
    'user.hero.title': '\u4f60\u597d\uff0c@name',
    'user.hero.subtitle':
        '\u67e5\u8be2\u3001\u529e\u7406\u3001\u8d44\u6599\u7ef4\u62a4\u4e0e Agent \u5bf9\u8bdd\u73b0\u5728\u90fd\u6536\u655b\u5728\u540c\u4e00\u4e2a\u66f4\u6e05\u6670\u7684\u5de5\u4f5c\u533a\u91cc\u3002',
    'user.hero.commandHint':
        '\u544a\u8bc9 Agent\uff1a\u5e2e\u6211\u68b3\u7406\u4eca\u5929\u8981\u5148\u5904\u7406\u4ec0\u4e48',
    'user.hero.secondary': '\u67e5\u770b\u8fdb\u5ea6',
    'user.metric.identity': '\u8eab\u4efd\u8d44\u6599',
    'user.metric.identityReady': '\u5df2\u5b8c\u5584',
    'user.metric.identityPending': '\u5f85\u8865\u5168',
    'user.metric.identityReadyDetail':
        '\u8d44\u6599\u5df2\u8db3\u4ee5\u652f\u6301\u7ebf\u4e0a\u529e\u7406',
    'user.metric.identityPendingDetail':
        '\u5efa\u8bae\u5148\u8865\u5168\u57fa\u7840\u8bc1\u4ef6\u4fe1\u606f',
    'user.metric.themeDetail':
        '\u53ef\u5728\u9876\u90e8\u5b9e\u65f6\u5207\u6362',
    'user.metric.agentSyncing': '\u540c\u6b65\u4e2d',
    'user.metric.agentDetail':
        '\u63d0\u4f9b\u8def\u7531\u5efa\u8bae\u3001\u68c0\u7d22\u8f85\u52a9\u548c\u9875\u9762\u52a8\u4f5c',
    'user.quickAccess': '\u5e38\u7528\u5165\u53e3',
    'user.card.progress.title': '\u4e1a\u52a1\u8fdb\u5ea6',
    'user.card.progress.subtitle':
        '\u8ddf\u8e2a\u5f53\u524d\u8282\u70b9\u3001\u72b6\u6001\u548c\u5f85\u5904\u7406\u52a8\u4f5c',
    'user.card.records.title': '\u8fdd\u6cd5\u8bb0\u5f55',
    'user.card.records.subtitle':
        '\u67e5\u770b\u672a\u5b8c\u6210\u8bb0\u5f55\u3001\u5904\u7f5a\u4e0e\u540e\u7eed\u6b65\u9aa4',
    'user.card.profile.title': '\u4e2a\u4eba\u8d44\u6599',
    'user.card.profile.subtitle':
        '\u7ba1\u7406\u8bc1\u4ef6\u3001\u9a7e\u9a76\u8bc1\u4e0e\u8d26\u53f7\u57fa\u7840\u4fe1\u606f',
    'user.card.news.title': '\u6700\u65b0\u8d44\u8baf',
    'user.card.news.subtitle':
        '\u9605\u8bfb\u516c\u5f00\u6307\u5357\u4e0e\u8fdd\u6cd5\u76f8\u5173\u8d44\u8baf',
    'user.card.support.title': '\u54a8\u8be2\u53cd\u9988',
    'user.card.support.subtitle':
        '\u5c06\u590d\u6742\u95ee\u9898\u4ea4\u7ed9 Agent \u6216\u4eba\u5de5\u652f\u6301',
    'user.card.preferences.title': '\u504f\u597d\u8bbe\u7f6e',
    'user.card.preferences.subtitle':
        '\u8c03\u6574\u89c6\u89c9\u8bbe\u7f6e\u4e0e\u4f7f\u7528\u504f\u597d',
    'user.today.line1':
        '\u5148\u68c0\u67e5\u4e2a\u4eba\u8d44\u6599\uff0c\u53ef\u4ee5\u907f\u514d\u8bb8\u591a\u53ef\u9884\u89c1\u7684\u529e\u7406\u5931\u8d25\u3002',
    'user.today.line2':
        '\u5f53\u4f60\u9700\u8981\u68c0\u7d22\u4e0a\u4e0b\u6587\u6216\u5bfc\u822a\u5efa\u8bae\u65f6\uff0c\u76f4\u63a5\u4f7f\u7528\u53f3\u4fa7 Agent \u9762\u677f\u3002',
    'user.today.line3':
        '\u5148\u7528\u81ea\u7136\u8bed\u8a00\u63cf\u8ff0\u76ee\u6807\uff0c\u518d\u8df3\u8f6c\u5230\u5177\u4f53\u9875\u9762\u3002',
    'user.focus.profileStatus': '\u8d44\u6599\u72b6\u6001',
    'user.focus.profileReady': '\u53ef\u76f4\u63a5\u4f7f\u7528',
    'user.focus.profilePending': '\u8bf7\u5148\u8865\u5168\u8bc1\u4ef6',
    'user.focus.agentPanel': 'Agent \u4fa7\u680f',
    'user.focus.agentPanelValue': '\u59cb\u7ec8\u5728\u53f3\u4fa7\u53ef\u7528',
    'user.focus.workspace': '\u5de5\u4f5c\u53f0',
    'user.focus.workspaceValue':
        '\u65b0\u7684\u9996\u9875\u4f7f\u7528\u66f4\u7b80\u6d01\u7684\u89c6\u89c9\u7cfb\u7edf',
    'admin.title': '\u7ba1\u7406\u63a7\u5236\u53f0',
    'admin.subtitle':
        '\u4e3a\u6cbb\u7406\u3001\u8fdb\u5ea6\u4e0e Agent \u534f\u4f5c\u91cd\u6784\u7684\u7b80\u6d01\u63a7\u5236\u5ba4',
    'admin.pageTitle': '\u7ba1\u7406\u9875\u9762',
    'admin.nav.users': '\u7528\u6237',
    'admin.nav.progress': '\u8fdb\u5ea6',
    'admin.nav.logs': '\u65e5\u5fd7',
    'admin.nav.business': '\u4e1a\u52a1',
    'admin.hero.badge': '\u7ba1\u7406\u63a7\u5236\u53f0',
    'admin.hero.title': '\u6b22\u8fce\u56de\u6765\uff0c@name',
    'admin.hero.subtitle':
        '\u7ba1\u7406\u7aef\u9996\u9875\u5df2\u91cd\u6784\u4e3a\u66f4\u7d27\u51d1\u7684\u603b\u63a7\u53f0\uff0c\u51cf\u5c11\u5207\u6362\uff0c\u5f3a\u5316\u4f18\u5148\u7ea7\u3002',
    'admin.hero.commandHint':
        '\u544a\u8bc9 Agent\uff1a\u5e2e\u6211\u627e\u51fa\u4eca\u5929\u6700\u503c\u5f97\u4f18\u5148\u5173\u6ce8\u7684\u540e\u53f0\u5165\u53e3',
    'admin.hero.secondary': '\u6253\u5f00\u7528\u6237\u7ba1\u7406',
    'admin.metric.mode': '\u6a21\u5f0f',
    'admin.metric.modeValue': '\u7ba1\u7406\u5df2\u542f\u7528',
    'admin.metric.modeDetail':
        '\u5f53\u524d\u8d26\u53f7\u62e5\u6709\u540e\u53f0\u6cbb\u7406\u6743\u9650',
    'admin.metric.themeDetail':
        '\u53ef\u4ece\u9876\u90e8\u7acb\u5373\u5207\u6362',
    'admin.metric.agentDetail':
        '\u6280\u80fd\u89c4\u5212\u3001\u8def\u7531\u5efa\u8bae\u4e0e\u4e0b\u4e00\u6b65\u52a8\u4f5c',
    'admin.coreEntries': '\u6838\u5fc3\u5165\u53e3',
    'admin.card.users.title': '\u7528\u6237\u7ba1\u7406',
    'admin.card.users.subtitle':
        '\u68c0\u67e5\u8d26\u53f7\u3001\u6743\u9650\u4e0e\u8eab\u4efd\u8d44\u6599',
    'admin.card.progress.title': '\u8fdb\u5ea6\u7ba1\u7406',
    'admin.card.progress.subtitle':
        '\u67e5\u770b\u6d41\u7a0b\u72b6\u6001\u3001\u961f\u5217\u5065\u5eb7\u5ea6\u4e0e\u4ea4\u63a5',
    'admin.card.logs.title': '\u65e5\u5fd7\u4e2d\u5fc3',
    'admin.card.logs.subtitle':
        '\u5ba1\u8ba1\u64cd\u4f5c\u8bb0\u5f55\u5e76\u6392\u67e5\u7cfb\u7edf\u95ee\u9898',
    'admin.card.business.title': '\u4e1a\u52a1\u5904\u7406',
    'admin.card.business.subtitle':
        '\u5728\u66f4\u805a\u7126\u7684\u89c6\u56fe\u4e2d\u5904\u7406\u540e\u53f0\u4e1a\u52a1',
    'admin.card.profile.title': '\u7ba1\u7406\u5458\u8d44\u6599',
    'admin.card.profile.subtitle':
        '\u66f4\u65b0\u7ba1\u7406\u5458\u81ea\u8eab\u7684\u8eab\u4efd\u4e0e\u5c55\u793a\u4fe1\u606f',
    'admin.card.settings.title': '\u63a7\u5236\u53f0\u8bbe\u7f6e',
    'admin.card.settings.subtitle':
        '\u8c03\u6574\u4e3b\u9898\u3001\u5bc6\u5ea6\u4e0e\u4f7f\u7528\u504f\u597d',
    'admin.today.line1':
        '\u4ece\u7528\u6237\u4e0e\u8fdb\u5ea6\u5f00\u59cb\uff0c\u80fd\u66f4\u5feb\u627e\u5230\u5f53\u524d\u6700\u6709\u4ef7\u503c\u7684\u4efb\u52a1\u3002',
    'admin.today.line2':
        '\u5982\u679c\u63a7\u5236\u9762\u8fc7\u4e8e\u5bbd\uff0c\u8ba9 Agent \u5148\u5e2e\u4f60\u6536\u7f29\u4e0b\u4e00\u6b65\u52a8\u4f5c\u3002',
    'admin.today.line3':
        '\u65e5\u5fd7\u9002\u5408\u505a\u5f02\u5e38\u8ffd\u8e2a\u548c\u5ba1\u8ba1\uff0c\u4e0d\u5efa\u8bae\u4f5c\u4e3a\u9ed8\u8ba4\u9996\u5c4f\u5165\u53e3\u3002',
    'manager.title': '\u4e1a\u52a1\u63a7\u5236\u53f0',
    'manager.subtitle':
        '\u4e3a\u4e1a\u52a1\u961f\u5217\u3001\u8fdb\u5ea6\u4e0e Agent \u534f\u4f5c\u63d0\u4f9b\u66f4\u805a\u7126\u7684\u64cd\u4f5c\u5de5\u4f5c\u533a',
    'manager.pageTitle': '\u4e1a\u52a1\u9875\u9762',
    'manager.hero.secondary': '\u6253\u5f00\u4e1a\u52a1\u5904\u7406',
    'manager.metric.modeValue': '\u4e1a\u52a1\u6a21\u5f0f\u5df2\u542f\u7528',
    'manager.metric.modeDetail':
        '\u5f53\u524d\u8d26\u53f7\u53ef\u8bbf\u95ee\u8fd0\u8425\u5904\u7406\u76f8\u5173\u9875\u9762\u3002',
    'manager.coreEntries': '\u6838\u5fc3\u5165\u53e3',
    'manager.business.title': '\u4e1a\u52a1\u5904\u7406\u83dc\u5355',
    'manager.business.enter': '\u70b9\u51fb\u8fdb\u5165',
    'chat.subtitle': '\u9762\u5411 skills \u7684 Agent \u52a9\u624b',
    'chat.webOn': '\u8054\u7f51\u5f00',
    'chat.webOff': '\u8054\u7f51\u5173',
    'chat.loadingSkills': '\u6b63\u5728\u52a0\u8f7d skills',
    'chat.webResults': '\u8054\u7f51\u7ed3\u679c',
    'chat.contextTitle': '\u5f53\u524d\u4e0a\u4e0b\u6587',
    'chat.context.operator': '\u5f53\u524d\u8eab\u4efd',
    'chat.context.scope': '\u8bbf\u95ee\u8303\u56f4',
    'chat.status': '\u72b6\u6001',
    'chat.you': '\u4f60',
    'chat.agent': 'agent',
    'chat.runAction': '\u6267\u884c\u52a8\u4f5c',
    'chat.emptyTitle': '\u4ece\u4e00\u6761\u6307\u4ee4\u5f00\u59cb',
    'chat.emptyBody':
        '\u76f4\u63a5\u63cf\u8ff0\u76ee\u6807\uff0cAgent \u4f1a\u89c4\u5212 skills\uff0c\u5728\u9700\u8981\u65f6\u8054\u7f51\u68c0\u7d22\uff0c\u5e76\u8fd4\u56de\u8def\u7531\u52a8\u4f5c\u5efa\u8bae\u3002',
    'chat.inputHint':
        '\u8f93\u5165\u6307\u4ee4\uff0c\u4f8b\u5982\uff1a\u6253\u5f00\u4e1a\u52a1\u8fdb\u5ea6',
    'chat.footer':
        '\u56de\u8f66\u53d1\u9001\u3002Agent \u4f1a\u8fd4\u56de\u6307\u5bfc\u3001\u68c0\u7d22\u4e0a\u4e0b\u6587\u4e0e\u8def\u7531\u52a8\u4f5c\u3002',
    'dialog.fillInfo': '\u586b\u5199\u4fe1\u606f',
    'page.refreshList': '\u5237\u65b0\u5217\u8868',
    'personal.title': '\u4e2a\u4eba\u4fe1\u606f\u7ba1\u7406',
    'personal.error.notLoggedIn':
        '\u5c1a\u672a\u767b\u5f55\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55\u3002',
    'personal.error.loadUserFailed':
        '\u52a0\u8f7d\u7528\u6237\u4fe1\u606f\u5931\u8d25\u3002',
    'personal.error.currentUserNotFound':
        '\u672a\u627e\u5230\u5f53\u524d\u7528\u6237\u4fe1\u606f\u3002',
    'personal.error.loginTokenMissing':
        '\u672a\u627e\u5230\u767b\u5f55\u51ed\u8bc1\u3002',
    'personal.error.unknownField': '\u672a\u77e5\u5b57\u6bb5\uff1a@field',
    'personal.error.requestFailed':
        '\u8bf7\u6c42\u5931\u8d25(@code)\uff1a@message',
    'personal.success.fieldUpdated': '@field\u66f4\u65b0\u6210\u529f',
    'personal.editDialog.title': '\u7f16\u8f91@field',
    'personal.editDialog.hint': '\u8f93\u5165\u65b0\u7684@field',
    'personal.field.name': '\u59d3\u540d',
    'personal.field.contactNumber': '\u8054\u7cfb\u7535\u8bdd',
    'personal.field.idCardNumber': '\u8eab\u4efd\u8bc1\u53f7\u7801',
    'personal.field.driverLicenseNumber': '\u9a7e\u9a76\u8bc1\u53f7',
    'personal.field.password': '\u5bc6\u7801',
    'personal.field.email': '\u90ae\u7bb1',
    'personal.field.status': '\u72b6\u6001',
    'personal.field.createdTime': '\u521b\u5efa\u65f6\u95f4',
    'personal.field.modifiedTime': '\u4fee\u6539\u65f6\u95f4',
    'personal.status.active': '\u542f\u7528',
    'personal.status.inactive': '\u7981\u7528',
    'personal.value.unknownUser': '\u672a\u77e5\u7528\u6237',
    'personal.value.changePassword': '\u70b9\u51fb\u4fee\u6539\u5bc6\u7801',
    'settings.title': '\u8bbe\u7f6e\u7ba1\u7406',
    'settings.theme': '\u9009\u62e9\u663e\u793a\u4e3b\u9898',
    'settings.cache': '\u6e05\u9664\u7f13\u5b58',
    'settings.saveSettings': '\u4fdd\u5b58\u8bbe\u7f6e',
    'settings.cacheCleared': '\u7f13\u5b58\u5df2\u6e05\u9664',
    'settings.saved': '\u8bbe\u7f6e\u5df2\u4fdd\u5b58',
    'settings.successTitle': '\u64cd\u4f5c\u6210\u529f',
    'settings.confirmLogoutTitle': '\u767b\u51fa',
    'settings.confirmLogoutMessage':
        '\u786e\u5b9a\u8981\u767b\u51fa\u5417\uff1f',
    'settings.themeDialogTitle': '\u9009\u62e9\u663e\u793a\u4e3b\u9898',
    'settings.summary.darkMode': '\u6df1\u8272\u6a21\u5f0f\uff1a@value',
    'settings.summary.currentTheme': '\u5f53\u524d\u4e3b\u9898\uff1a@value',
    'settings.summary.cacheSize': '\u7f13\u5b58\u5927\u5c0f\uff1a@value MB',
    'settings.themeMode.enabled': '\u5df2\u542f\u7528',
    'settings.themeMode.disabled': '\u5df2\u5173\u95ed',
    'settings.theme.materialLight': '\u539f\u751f\u6d45\u8272',
    'settings.theme.materialDark': '\u539f\u751f\u6df1\u8272',
    'settings.theme.ionicLight': 'Ionic \u6d45\u8272',
    'settings.theme.ionicDark': 'Ionic \u6df1\u8272',
    'settings.theme.basicLight': '\u57fa\u7840\u6d45\u8272',
    'settings.theme.basicDark': '\u57fa\u7840\u6df1\u8272',
    'settings.notifications': '\u901a\u77e5',
    'settings.notificationsEnabled': '\u542f\u7528\u901a\u77e5',
    'settings.controlTitle': '\u4ea7\u54c1\u63a7\u5236\u53f0',
    'settings.controlBody':
        '\u5728\u540c\u4e00\u4e2a\u5de5\u4f5c\u9762\u4e2d\u7ba1\u7406\u4ea7\u54c1\u914d\u7f6e\uff0c\u76f4\u89c2\u67e5\u770b\u53ef\u7f16\u8f91\u8303\u56f4\uff0c\u5e76\u907f\u514d\u5728\u5217\u8868\u4e2d\u66b4\u9732\u654f\u611f\u503c\u3002',
    'settings.workspaceTitle': '\u672c\u5730\u63a7\u5236\u53f0\u504f\u597d',
    'settings.workspaceBody':
        '\u5c06\u4e2a\u4eba\u63a7\u5236\u53f0\u504f\u597d\u4e0e\u5171\u4eab\u7cfb\u7edf\u914d\u7f6e\u5206\u79bb\uff0c\u907f\u514d\u4e2a\u4eba\u64cd\u4f5c\u4e60\u60ef\u5f71\u54cd\u4ea7\u54c1\u6cbb\u7406\u3002',
    'settings.registryTitle': '\u914d\u7f6e\u6ce8\u518c\u8868',
    'settings.registryBody':
        '\u6309\u952e\u3001\u5206\u7c7b\u3001\u7c7b\u578b\u3001\u63cf\u8ff0\u548c\u72b6\u6001\u7b5b\u9009\u771f\u5b9e\u7cfb\u7edf\u914d\u7f6e\uff0c\u5e76\u76f4\u63a5\u7ef4\u62a4\u3002',
    'settings.searchHint':
        '\u6309\u952e\u3001\u5206\u7c7b\u3001\u7c7b\u578b\u3001\u63cf\u8ff0\u3001\u5907\u6ce8\u6216\u503c\u8fdb\u884c\u641c\u7d22',
    'settings.filter.all': '\u5168\u90e8\u5206\u7c7b',
    'settings.metric.total': '\u603b\u914d\u7f6e\u6570',
    'settings.metric.editable': '\u53ef\u7f16\u8f91',
    'settings.metric.encrypted': '\u5df2\u52a0\u5bc6',
    'settings.metric.categories': '\u5206\u7c7b\u6570',
    'settings.metric.lastSync': '\u6700\u540e\u540c\u6b65',
    'settings.metric.neverSynced': '\u5c1a\u672a\u540c\u6b65',
    'settings.preference.notificationsBody':
        '\u4ec5\u5728\u672c\u8bbe\u5907\u4fdd\u7559\u63a7\u5236\u53f0\u63d0\u9192\uff0c\u4e0d\u5199\u5165\u5171\u4eab\u4ea7\u54c1\u914d\u7f6e\u3002',
    'settings.preference.themeBody':
        '\u5f53\u524d\u663e\u793a\u4e3b\u9898\uff1a@value',
    'settings.preference.themeChange': '\u5207\u6362\u4e3b\u9898',
    'settings.preference.localSaveBody':
        '\u4fdd\u5b58\u672c\u5730\u63a7\u5236\u53f0\u504f\u597d\uff0c\u4e0d\u6539\u52a8\u5171\u4eab\u4ea7\u54c1\u914d\u7f6e\u3002',
    'settings.preference.logoutBody':
        '\u9000\u51fa\u5f53\u524d\u5de5\u4f5c\u533a\u5e76\u6e05\u7406\u672c\u5730\u4ee4\u724c\u3002',
    'settings.action.newSetting': '\u65b0\u5efa\u914d\u7f6e',
    'settings.action.editSetting': '\u7f16\u8f91',
    'settings.action.saveLocal': '\u4fdd\u5b58\u672c\u5730',
    'settings.action.reload': '\u91cd\u65b0\u52a0\u8f7d',
    'settings.message.localSaved': '\u672c\u5730\u504f\u597d\u5df2\u4fdd\u5b58',
    'settings.message.loadFailed':
        '\u52a0\u8f7d\u914d\u7f6e\u5931\u8d25\uff1a@error',
    'settings.message.createSuccess': '\u914d\u7f6e\u5df2\u521b\u5efa',
    'settings.message.updateSuccess': '\u914d\u7f6e\u5df2\u66f4\u65b0',
    'settings.message.notEditable':
        '\u8be5\u914d\u7f6e\u5df2\u6807\u8bb0\u4e3a\u53ea\u8bfb\uff0c\u65e0\u6cd5\u5728\u6b64\u9875\u7f16\u8f91\u3002',
    'settings.state.emptyTitle':
        '\u5f53\u524d\u7b5b\u9009\u6761\u4ef6\u4e0b\u6682\u65e0\u914d\u7f6e',
    'settings.state.emptyBody':
        '\u8bf7\u5c1d\u8bd5\u66f4\u6362\u641c\u7d22\u8bcd\u6216\u5206\u7c7b\uff0c\u4e5f\u53ef\u4ee5\u65b0\u5efa\u4e00\u6761\u914d\u7f6e\u3002',
    'settings.form.createTitle': '\u65b0\u5efa\u914d\u7f6e',
    'settings.form.editTitle': '\u7f16\u8f91\u914d\u7f6e',
    'settings.form.key': '\u914d\u7f6e\u952e',
    'settings.form.value': '\u914d\u7f6e\u503c',
    'settings.form.type': '\u914d\u7f6e\u7c7b\u578b',
    'settings.form.category': '\u5206\u7c7b',
    'settings.form.description': '\u63cf\u8ff0',
    'settings.form.remarks': '\u5907\u6ce8',
    'settings.form.sortOrder': '\u6392\u5e8f',
    'settings.form.isEditable': '\u63a7\u5236\u53f0\u53ef\u7f16\u8f91',
    'settings.form.isEncrypted': '\u503c\u5df2\u52a0\u5bc6',
    'settings.form.keyRequired': '\u8bf7\u586b\u5199\u914d\u7f6e\u952e',
    'settings.form.valueRequired': '\u8bf7\u586b\u5199\u914d\u7f6e\u503c',
    'settings.value.none': '\u672a\u586b\u5199',
    'settings.value.readOnly': '\u53ea\u8bfb',
    'settings.value.editable': '\u53ef\u7f16\u8f91',
    'settings.value.encrypted': '\u5df2\u52a0\u5bc6',
    'settings.value.plaintext': '\u660e\u6587',
    'settings.value.notConfigured': '\u672a\u914d\u7f6e',
    'settings.label.updatedBy': '\u66f4\u65b0\u4eba\uff1a@value',
    'settings.label.updatedAt': '\u66f4\u65b0\u65f6\u95f4\uff1a@value',
    'shared.profileTile.role.userWelcome':
        '\u6b22\u8fce\u4f7f\u7528\u4ea4\u901a\u8fdd\u6cd5\u884c\u4e3a\u5904\u7406\u7ba1\u7406\u7cfb\u7edf\u9a7e\u9a76\u5458\u7aef',
    'shared.profileTile.role.adminWelcome':
        '\u6b22\u8fce\u4f7f\u7528\u4ea4\u901a\u8fdd\u6cd5\u884c\u4e3a\u5904\u7406\u7ba1\u7406\u7cfb\u7edf\u4ea4\u901a\u7ba1\u7406\u5458\u7aef',
    'shared.profileTile.role.defaultWelcome':
        '\u6b22\u8fce\u4f7f\u7528\u4ea4\u901a\u8fdd\u6cd5\u884c\u4e3a\u5904\u7406\u7ba1\u7406\u7cfb\u7edf',
    'shared.map.title': '\u54c8\u5c14\u6ee8\u4ea4\u901a\u5730\u56fe',
    'shared.map.error.tileLoadFailed':
        '\u5730\u56fe\u74e6\u7247\u91cd\u8bd5 @count \u6b21\u540e\u4ecd\u52a0\u8f7d\u5931\u8d25\u3002',
    'shared.map.error.placeholder': '\u5730\u56fe\u52a0\u8f7d\u9519\u8bef',
    'shared.map.attribution.openStreetMap': 'OpenStreetMap \u8d21\u732e\u8005',
    'shared.notificationBar.defaultMessage':
        '\u8bf7\u8f93\u5165\u8eab\u4efd\u8bc1\u53f7\u548c\u9a7e\u9a76\u8bc1\u53f7\u4ee5\u7ee7\u7eed',
    'shared.notificationBar.defaultAction': '\u7acb\u5373\u586b\u5199',
    'shared.notificationBar.navigationError':
        '\u65e0\u6cd5\u5bfc\u822a\u5230\u76ee\u6807\u9875\u9762\uff0c\u8bf7\u91cd\u8bd5\u3002',
    'shared.addCarCard.title': '\u673a\u52a8\u8f66',
    'shared.addCarCard.action': '\u5907\u6848\u673a\u52a8\u8f66\u4fe1\u606f',
    'shared.postCard.title': '\u4ea4\u901a\u5b89\u5168\u65f6\u65f6\u4e0d\u5fd8',
    'shared.postCard.body': '\u5e78\u798f\u751f\u6d3b\u5929\u5929\u62e5\u6709',
    'shared.policeCard.title':
        '\u6267\u6cd5\u4e3a\u6c11\n\u516c\u6b63\u5ec9\u6d01\n\u65e0\u79c1\u5949\u732e',
    'shared.policeCard.body':
        '\u52a0\u5f3a\u7efc\u5408\u6cbb\u7406\uff0c\u4fdd\u969c\u4ea4\u901a\u5b89\u5168',
    'shared.progressReport.appeals': '\u7533\u8bc9',
    'shared.progressReport.appealsHandled':
        '\u5df2\u5904\u7406\u7684\u7533\u8bc9',
    'shared.progressReport.appealsPending':
        '\u672a\u5904\u7406\u7684\u7533\u8bc9',
    'shared.progressReport.completionRate': '\u5b8c\u6210\u5ea6',
    'shared.trafficViolation.total': '\u603b\u8fdd\u6cd5\u884c\u4e3a',
    'shared.trafficViolation.handled': '\u5df2\u5904\u7406\u7684\u8fdd\u6cd5',
    'shared.trafficViolation.pending': '\u672a\u5904\u7406\u7684\u8fdd\u6cd5',
    'shared.trafficViolation.rate': '\u5904\u7406\u7387',
    'shared.caseCard.overdueInDays': '\u5df2\u903e\u671f @days \u5929',
    'shared.caseCard.dueInDays': '@days \u5929\u540e\u5230\u671f',
    'shared.caseCard.dueToday': '\u4eca\u65e5\u5230\u671f',
    'shared.userScreenSwiper.slogan.safeDriving':
        '\u5b89\u5168\u9a7e\u9a76\uff0c\u6587\u660e\u51fa\u884c',
    'shared.userScreenSwiper.slogan.followRules':
        '\u9075\u5b88\u4ea4\u89c4\uff0c\u5e73\u5b89\u56de\u5bb6',
    'shared.userScreenSwiper.slogan.slowDown':
        '\u51cf\u901f\u6162\u884c\uff0c\u751f\u547d\u81f3\u4e0a',
    'feedback.title': '\u54a8\u8be2\u4e0e\u53cd\u9988',
    'feedback.label':
        '\u8bf7\u8f93\u5165\u60a8\u7684\u53cd\u9988\u6216\u54a8\u8be2\u5185\u5bb9',
    'feedback.hint': '\u8bf7\u8f93\u5165\u53cd\u9988\u5185\u5bb9...',
    'feedback.submit': '\u63d0\u4ea4\u53cd\u9988',
    'feedback.empty': '\u8bf7\u5148\u586b\u5199\u53cd\u9988\u5185\u5bb9',
    'feedback.error.notLoggedIn':
        '\u672a\u627e\u5230\u767b\u5f55\u4fe1\u606f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55\u3002',
    'feedback.error.submitFailed':
        '\u63d0\u4ea4\u53cd\u9988\u5931\u8d25\uff1a@error',
    'feedback.error.httpStatus':
        '\u8bf7\u6c42\u5931\u8d25\uff08HTTP @statusCode\uff09\u3002',
    'feedback.successTitle': '\u6210\u529f',
    'feedback.successMessage':
        '\u53cd\u9988\u5df2\u63d0\u4ea4\uff0c\u8bf7\u7b49\u5f85\u7ba1\u7406\u5458\u5ba1\u6838\u3002',
    'feedback.successConfirm': '\u77e5\u9053\u4e86',
    'feedback.approvalTitle': '\u53cd\u9988\u5ba1\u6279',
    'feedback.approvalEmpty': '\u6682\u65e0\u53cd\u9988\u8bf7\u6c42',
    'feedback.approvalUser': '\u7528\u6237\uff1a@user',
    'feedback.approvalDetail':
        '\u53cd\u9988\uff1a@feedback\n\u72b6\u6001\uff1a@status',
    'feedback.approvalApprove': '\u6279\u51c6',
    'feedback.approvalReject': '\u62d2\u7edd',
    'feedback.approvalInvalidId': '\u65e0\u6548\u7684\u53cd\u9988 ID',
    'feedback.approvalUpdated': '\u53cd\u9988\u5df2@status',
    'feedback.error.loadFailed':
        '\u52a0\u8f7d\u53cd\u9988\u8bf7\u6c42\u5931\u8d25\uff1a@error',
    'feedback.error.updateFailed':
        '\u66f4\u65b0\u53cd\u9988\u5931\u8d25\uff1a@error',
    'admin.personal.title': '\u7ba1\u7406\u5458\u8d44\u6599',
    'admin.personal.logoutTooltip': '\u9000\u51fa\u767b\u5f55',
    'admin.personal.error.userFromToken':
        '\u672a\u80fd\u4ece\u51ed\u8bc1\u4e2d\u89e3\u6790\u5f53\u524d\u7528\u6237\u3002',
    'admin.personal.error.jwtMissing':
        '\u672a\u5728\u5b58\u50a8\u4e2d\u627e\u5230 JWT \u51ed\u8bc1\u3002',
    'admin.personal.field.username': '\u7528\u6237\u540d',
    'admin.personal.field.emailAddress': '\u90ae\u7bb1\u5730\u5740',
    'admin.personal.field.remarks': '\u5907\u6ce8',
    'admin.personal.status.active': '\u542f\u7528',
    'admin.personal.status.inactive': '\u7981\u7528',
    'admin.personal.logoutConfirmTitle': '\u786e\u8ba4\u9000\u51fa',
    'admin.personal.logoutConfirmBody':
        '\u60a8\u786e\u5b9a\u8981\u9000\u51fa\u767b\u5f55\u5417\uff1f',
    'admin.personal.noData': '\u65e0\u6570\u636e',
    'admin.business.title': '\u4e1a\u52a1\u5904\u7406\u83dc\u5355',
    'admin.business.appeal': '\u7533\u8bc9\u7ba1\u7406',
    'admin.business.deduction': '\u6263\u5206\u7ba1\u7406',
    'admin.business.driver': '\u53f8\u673a\u7ba1\u7406',
    'admin.business.fine': '\u7f5a\u6b3e\u7ba1\u7406',
    'admin.business.vehicle': '\u8f66\u8f86\u7ba1\u7406',
    'admin.business.offense': '\u8fdd\u6cd5\u884c\u4e3a',
    'admin.business.enter': '\u70b9\u51fb\u8fdb\u5165',
    'admin.logs.title': '\u65e5\u5fd7\u7ba1\u7406\u83dc\u5355',
    'driverAdmin.page.listTitle': '司机列表',
    'driverAdmin.page.addTitle': '添加司机',
    'driverAdmin.page.editTitle': '编辑司机',
    'driverAdmin.page.detailTitle': '司机详情',
    'driverAdmin.search.hint': '按姓名、ID、电话、身份证号或驾驶证号搜索司机',
    'driverAdmin.empty.default': '当前暂无司机记录。',
    'driverAdmin.empty.filtered': '没有匹配当前筛选条件的司机。',
    'driverAdmin.action.add': '添加司机',
    'driverAdmin.action.edit': '编辑司机',
    'driverAdmin.action.delete': '删除司机',
    'driverAdmin.action.refresh': '刷新列表',
    'driverAdmin.delete.confirmTitle': '确认删除',
    'driverAdmin.delete.confirmBody': '确定要删除此司机吗？此操作不可撤销。',
    'driverAdmin.field.driverId': '司机 ID',
    'driverAdmin.field.name': '姓名',
    'driverAdmin.field.idCardNumber': '身份证号',
    'driverAdmin.field.contactNumber': '联系电话',
    'driverAdmin.field.driverLicenseNumber': '驾驶证号',
    'driverAdmin.field.gender': '性别',
    'driverAdmin.field.birthdate': '出生日期',
    'driverAdmin.field.firstLicenseDate': '初次领证日期',
    'driverAdmin.field.allowedVehicleType': '准驾车型',
    'driverAdmin.field.issueDate': '发证日期',
    'driverAdmin.field.expiryDate': '有效期截止日期',
    'driverAdmin.gender.male': '男',
    'driverAdmin.gender.female': '女',
    'driverAdmin.gender.unknown': '未知',
    'driverAdmin.validation.required': '@field 不能为空。',
    'driverAdmin.validation.nameLength': '姓名长度必须在 2 到 50 个字符之间。',
    'driverAdmin.validation.idCardInvalid': '请输入有效的身份证号（15 位或 18 位）。',
    'driverAdmin.validation.contactInvalid': '请输入有效的 11 位手机号。',
    'driverAdmin.validation.licenseInvalid': '请输入有效的 12 位驾驶证号。',
    'driverAdmin.validation.allowedVehicleTypeTooLong': '允许驾驶车型长度不能超过 50 个字符。',
    'driverAdmin.validation.genderRequired': '请选择性别。',
    'driverAdmin.validation.fixFormErrors': '请修正表单中的错误。',
    'driverAdmin.error.initFailed': '初始化失败：@error',
    'driverAdmin.error.loadFailed': '加载司机失败：@error',
    'driverAdmin.error.detailFailed': '加载司机详情失败：@error',
    'driverAdmin.error.detailNotFound': '未找到司机详情。',
    'driverAdmin.error.idMissing': '司机 ID 缺失，无法继续当前操作。',
    'driverAdmin.error.request': '请求错误：@message',
    'driverAdmin.error.forbidden': '无权限：@message',
    'driverAdmin.error.notFound': '未找到：@message',
    'driverAdmin.error.duplicateRequest': '重复请求：@message',
    'driverAdmin.error.server': '服务器错误：@message',
    'driverAdmin.error.operationFailed': '操作失败：@error',
    'driverAdmin.error.createFailed': '添加司机失败：@error',
    'driverAdmin.error.updateFailed': '更新司机失败：@error',
    'driverAdmin.error.deleteFailed': '删除司机失败：@error',
    'driverAdmin.success.created': '司机添加成功。',
    'driverAdmin.success.updated': '司机更新成功。',
    'driverAdmin.success.deleted': '司机删除成功。',
    'userAdmin.page.title': '用户管理',
    'userAdmin.error.unauthorized': '未授权，请重新登录。',
    'userAdmin.error.expired': '登录已过期，请重新登录。',
    'userAdmin.error.invalidLogin': '登录信息无效，请重新登录。@error',
    'userAdmin.error.adminOnly': '权限不足：仅管理员可访问用户管理页面。',
    'userAdmin.error.initFailed': '初始化失败：@error',
    'userAdmin.error.loadFailed': '加载用户失败：@error',
    'userAdmin.error.request': '请求错误：@message',
    'userAdmin.error.forbidden': '无权限：@message',
    'userAdmin.error.notFound': '未找到：@message',
    'userAdmin.error.duplicateRequest': '重复请求：@message',
    'userAdmin.error.server': '服务器错误：@message',
    'userAdmin.error.operationFailed': '操作失败：@error',
    'userAdmin.error.createFailed': '创建用户失败：@error',
    'userAdmin.error.updateFailed': '更新用户失败：@error',
    'userAdmin.error.deleteFailed': '删除用户失败：@error',
    'userAdmin.error.roleLoadFailed': '管理用户角色失败：@error',
    'userAdmin.empty.default': '当前暂无用户记录。',
    'userAdmin.empty.filtered': '没有匹配当前筛选条件的用户。',
    'userAdmin.empty.roles': '该用户当前还没有角色绑定。',
    'userAdmin.workspace.eyebrow': '用户控制中心',
    'userAdmin.workspace.title': '用户管理工作台',
    'userAdmin.workspace.subtitle': '在一个更集中的管理界面中搜索、比对状态，并快速进入账号操作。',
    'userAdmin.workspace.signal.query': '搜索：@value',
    'userAdmin.workspace.signal.queryIdle': '搜索范围：所有已加载用户',
    'userAdmin.workspace.signal.mode': '搜索模式：@value',
    'userAdmin.workspace.metric.loaded': '已加载',
    'userAdmin.workspace.metric.visible': '当前可见',
    'userAdmin.workspace.metric.active': '启用',
    'userAdmin.workspace.metric.inactive': '停用',
    'userAdmin.workspace.metric.department': '部门数',
    'userAdmin.workspace.filterEyebrow': '筛选',
    'userAdmin.workspace.filterTitle': '搜索与缩小用户范围',
    'userAdmin.workspace.filterBody': '切换搜索模式，收敛当前用户集，并刷新当前列表。',
    'userAdmin.workspace.filterMode': '搜索模式',
    'userAdmin.workspace.filterReset': '重置筛选',
    'userAdmin.workspace.filterRefresh': '刷新用户',
    'userAdmin.workspace.listEyebrow': '用户',
    'userAdmin.workspace.listTitle': '用户记录',
    'userAdmin.workspace.listBody': '先查看状态、负责人、部门和联系方式，再决定编辑或角色调整。',
    'userAdmin.workspace.emptyTitle': '当前视图没有用户',
    'userAdmin.workspace.errorTitle': '用户记录加载失败',
    'userAdmin.search.username': '搜索账号',
    'userAdmin.search.status': '搜索状态',
    'userAdmin.search.department': '搜索部门',
    'userAdmin.search.contactNumber': '搜索联系电话',
    'userAdmin.search.email': '搜索邮箱',
    'userAdmin.filter.byUsername': '按账号',
    'userAdmin.filter.byStatus': '按状态',
    'userAdmin.filter.byDepartment': '按部门',
    'userAdmin.filter.byContactNumber': '按联系电话',
    'userAdmin.filter.byEmail': '按邮箱',
    'userAdmin.dialog.createTitle': '创建用户',
    'userAdmin.dialog.editTitle': '编辑用户',
    'userAdmin.dialog.manageRolesTitle': '管理 @username 的角色',
    'userAdmin.delete.confirmTitle': '确认删除',
    'userAdmin.delete.confirmBody': '确定要删除此用户吗？此操作不可撤销。',
    'userAdmin.action.relogin': '重新登录',
    'userAdmin.action.create': '创建用户',
    'userAdmin.action.manageRoles': '管理角色',
    'userAdmin.action.edit': '编辑用户',
    'userAdmin.action.delete': '删除用户',
    'userAdmin.action.refresh': '刷新列表',
    'userAdmin.hint.selectRole': '选择要新增的角色',
    'userAdmin.field.username': '账号',
    'userAdmin.field.password': '密码',
    'userAdmin.field.newPassword': '新密码',
    'userAdmin.field.contactNumber': '联系电话',
    'userAdmin.field.email': '邮箱',
    'userAdmin.field.department': '部门',
    'userAdmin.field.status': '状态',
    'userAdmin.field.remarks': '备注',
    'userAdmin.field.createdTime': '创建时间',
    'userAdmin.field.modifiedTime': '修改时间',
    'userAdmin.helper.passwordOptional': '留空则保持当前密码不变。',
    'userAdmin.validation.required': '@field 不能为空。',
    'userAdmin.validation.usernameTooLong': '账号长度不能超过 50 个字符。',
    'userAdmin.validation.passwordTooLong': '密码长度不能超过 255 个字符。',
    'userAdmin.validation.contactNumberTooLong': '联系电话长度不能超过 20 个字符。',
    'userAdmin.validation.emailTooLong': '邮箱长度不能超过 100 个字符。',
    'userAdmin.validation.emailInvalid': '请输入有效的邮箱地址。',
    'userAdmin.validation.departmentTooLong': '部门长度不能超过 100 个字符。',
    'userAdmin.validation.remarksTooLong': '备注长度不能超过 255 个字符。',
    'userAdmin.validation.statusRequired': '请选择状态。',
    'userAdmin.validation.roleRequired': '请先选择一个角色。',
    'userAdmin.validation.usernameExists': '该账号已存在。',
    'userAdmin.success.created': '用户创建成功。',
    'userAdmin.success.updated': '用户更新成功。',
    'userAdmin.success.deleted': '用户删除成功。',
    'userAdmin.success.roleAdded': '角色绑定添加成功。',
    'userAdmin.success.roleRemoved': '角色绑定移除成功。',
    'userAdmin.status.active': '启用',
    'userAdmin.status.inactive': '禁用',
    'userAdmin.value.unknownUser': '未知用户',
    'business.menu.title': '\u4e1a\u52a1\u529e\u7406\u83dc\u5355',
    'business.menu.signal': '\u4e1a\u52a1\u5de5\u4f5c\u53f0',
    'business.menu.subtitle':
        '\u5728\u4e00\u4e2a\u96c6\u4e2d\u7684\u5de5\u4f5c\u53f0\u4e2d\u67e5\u770b\u8fdd\u6cd5\u8bb0\u5f55\u3001\u7f34\u7eb3\u7f5a\u6b3e\u3001\u63d0\u4ea4\u7533\u8bc9\u5e76\u8ddf\u8fdb\u529e\u7406\u8fdb\u5ea6\u3002',
    'business.menu.ready': '\u5c31\u7eea',
    'business.menu.statusReview': '\u5f85\u68c0\u67e5',
    'business.menu.sectionTitle': '\u53ef\u7528\u64cd\u4f5c',
    'business.menu.sectionBody':
        '\u6309\u7167\u5f53\u524d\u81ea\u52a9\u529e\u7406\u9636\u6bb5\u9009\u62e9\u5bf9\u5e94\u4efb\u52a1\u3002',
    'business.menu.quickStatus': '\u5f53\u524d\u72b6\u6001',
    'business.menu.quickStatusBody':
        '\u5c06\u6b64\u9875\u4f5c\u4e3a\u65e5\u5e38\u81ea\u52a9\u4e1a\u52a1\u529e\u7406\u7684\u4e3b\u5165\u53e3\u3002',
    'business.menu.tipTitle': '\u4eca\u65e5\u63d0\u793a',
    'business.menu.tip1':
        '\u5728\u7f34\u6b3e\u3001\u7533\u8bc9\u6216\u63d0\u4ea4\u540e\u7eed\u6b65\u9aa4\u524d\uff0c\u5148\u6838\u5bf9\u8fdd\u6cd5\u8be6\u60c5\u3002',
    'business.menu.tip2':
        '\u6bcf\u6b21\u63d0\u4ea4\u540e\uff0c\u90fd\u53ef\u5728\u8fdb\u5ea6\u9875\u786e\u8ba4\u6700\u65b0\u72b6\u6001\u3002',
    'business.menu.tip3':
        '\u4fdd\u6301\u8f66\u8f86\u4fe1\u606f\u6700\u65b0\uff0c\u53ef\u51cf\u5c11\u529e\u7406\u8def\u7531\u548c\u5f52\u5c5e\u95ee\u9898\u3002',
    'business.menu.offenseDetail': '\u8fdd\u6cd5\u8be6\u60c5',
    'business.menu.offenseDetail.subtitle':
        '\u67e5\u770b\u5f53\u524d\u8bb0\u5f55\u3001\u8bc1\u636e\u548c\u5904\u7f5a\u7ed3\u8bba\u3002',
    'business.menu.finePayment': '\u7f5a\u6b3e\u7f34\u7eb3',
    'business.menu.finePayment.subtitle':
        '\u7f34\u7eb3\u672a\u5b8c\u6210\u7f5a\u6b3e\u5e76\u786e\u8ba4\u7f34\u8d39\u72b6\u6001\u3002',
    'business.menu.userAppeal': '\u7528\u6237\u7533\u8bc9',
    'business.menu.userAppeal.subtitle':
        '\u53d1\u8d77\u65b0\u7533\u8bc9\u6216\u67e5\u770b\u5df2\u63d0\u4ea4\u7533\u8bc9\u3002',
    'business.menu.onlineProcessingProgress': '\u529e\u7406\u8fdb\u5ea6',
    'business.menu.onlineProcessingProgress.subtitle':
        '\u8ddf\u8e2a\u6d41\u7a0b\u72b6\u6001\u3001\u65f6\u95f4\u8282\u70b9\u548c\u4e0b\u4e00\u6b65\u64cd\u4f5c\u3002',
    'business.menu.vehicleManagement': '\u8f66\u8f86\u767b\u8bb0\u7ba1\u7406',
    'business.menu.vehicleManagement.subtitle':
        '\u5728\u529e\u7406\u524d\u7ef4\u62a4\u5df2\u767b\u8bb0\u8f66\u8f86\u4fe1\u606f\u3002',
    'loginLog.page.title': '\u767b\u5f55\u65e5\u5fd7',
    'loginLog.error.unauthorized':
        '\u672a\u6388\u6743\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'loginLog.error.expired':
        '\u767b\u5f55\u5df2\u8fc7\u671f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'loginLog.error.invalidLogin':
        '\u65e0\u6548\u7684\u767b\u5f55\u4fe1\u606f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'loginLog.error.adminOnly':
        '\u6743\u9650\u4e0d\u8db3\uff1a\u4ec5\u7ba1\u7406\u5458\u53ef\u8bbf\u95ee\u6b64\u9875\u9762',
    'loginLog.error.initFailed': '\u521d\u59cb\u5316\u5931\u8d25: @error',
    'loginLog.error.roleCheckFailed':
        '\u9a8c\u8bc1\u89d2\u8272\u5931\u8d25: @error',
    'loginLog.error.loadFailed':
        '\u52a0\u8f7d\u767b\u5f55\u65e5\u5fd7\u5931\u8d25: @error',
    'loginLog.error.request': '\u8bf7\u6c42\u9519\u8bef: @message',
    'loginLog.error.forbidden': '\u65e0\u6743\u9650: @message',
    'loginLog.error.notFound': '\u672a\u627e\u5230: @message',
    'loginLog.error.duplicateRequest': '\u91cd\u590d\u8bf7\u6c42: @message',
    'loginLog.error.server': '\u670d\u52a1\u5668\u9519\u8bef: @message',
    'loginLog.error.operationFailed': '\u64cd\u4f5c\u5931\u8d25: @error',
    'loginLog.error.idMissingEdit':
        '\u65e0\u6cd5\u7f16\u8f91\uff1a\u65e5\u5fd7 ID \u7f3a\u5931\u3002',
    'loginLog.error.idMissingDelete':
        '\u65e0\u6cd5\u5220\u9664\uff1a\u65e5\u5fd7 ID \u7f3a\u5931\u3002',
    'loginLog.empty.filtered':
        '\u672a\u627e\u5230\u7b26\u5408\u5f53\u524d\u7b5b\u9009\u6761\u4ef6\u7684\u767b\u5f55\u65e5\u5fd7',
    'loginLog.empty.default': '\u6682\u65e0\u767b\u5f55\u65e5\u5fd7',
    'loginLog.dialog.createTitle': '\u521b\u5efa\u767b\u5f55\u65e5\u5fd7',
    'loginLog.dialog.editTitle': '\u7f16\u8f91\u767b\u5f55\u65e5\u5fd7',
    'loginLog.field.username': '\u7528\u6237\u540d',
    'loginLog.field.loginIp': '\u767b\u5f55 IP \u5730\u5740',
    'loginLog.field.loginResult': '\u767b\u5f55\u7ed3\u679c',
    'loginLog.field.browserType': '\u6d4f\u89c8\u5668\u7c7b\u578b',
    'loginLog.field.osVersion': '\u64cd\u4f5c\u7cfb\u7edf\u7248\u672c',
    'loginLog.field.remarks': '\u5907\u6ce8',
    'loginLog.validation.usernameRequired':
        '\u7528\u6237\u540d\u4e0d\u80fd\u4e3a\u7a7a',
    'loginLog.validation.loginIpRequired':
        '\u767b\u5f55 IP \u5730\u5740\u4e0d\u80fd\u4e3a\u7a7a',
    'loginLog.validation.loginResultRequired':
        '\u767b\u5f55\u7ed3\u679c\u4e0d\u80fd\u4e3a\u7a7a',
    'loginLog.validation.usernameTooLong':
        '\u7528\u6237\u540d\u4e0d\u80fd\u8d85\u8fc7100\u4e2a\u5b57\u7b26',
    'loginLog.validation.loginIpTooLong':
        '\u767b\u5f55 IP \u5730\u5740\u4e0d\u80fd\u8d85\u8fc750\u4e2a\u5b57\u7b26',
    'loginLog.validation.loginResultTooLong':
        '\u767b\u5f55\u7ed3\u679c\u4e0d\u80fd\u8d85\u8fc750\u4e2a\u5b57\u7b26',
    'loginLog.validation.browserTypeTooLong':
        '\u6d4f\u89c8\u5668\u7c7b\u578b\u4e0d\u80fd\u8d85\u8fc7100\u4e2a\u5b57\u7b26',
    'loginLog.validation.osVersionTooLong':
        '\u64cd\u4f5c\u7cfb\u7edf\u7248\u672c\u4e0d\u80fd\u8d85\u8fc7100\u4e2a\u5b57\u7b26',
    'loginLog.validation.remarksTooLong':
        '\u5907\u6ce8\u4e0d\u80fd\u8d85\u8fc7500\u4e2a\u5b57\u7b26',
    'loginLog.success.created':
        '\u767b\u5f55\u65e5\u5fd7\u521b\u5efa\u6210\u529f',
    'loginLog.success.updated':
        '\u767b\u5f55\u65e5\u5fd7\u66f4\u65b0\u6210\u529f',
    'loginLog.success.deleted':
        '\u767b\u5f55\u65e5\u5fd7\u5220\u9664\u6210\u529f',
    'loginLog.delete.confirmTitle': '\u786e\u8ba4\u5220\u9664',
    'loginLog.delete.confirmBody':
        '\u786e\u5b9a\u8981\u5220\u9664\u6b64\u767b\u5f55\u65e5\u5fd7\u5417\uff1f\u6b64\u64cd\u4f5c\u4e0d\u53ef\u64a4\u9500\u3002',
    'loginLog.search.username': '\u641c\u7d22\u7528\u6237\u540d',
    'loginLog.search.loginResult': '\u641c\u7d22\u767b\u5f55\u7ed3\u679c',
    'loginLog.search.timeRangeSelected':
        '\u641c\u7d22\u65f6\u95f4\u8303\u56f4\uff08\u5df2\u9009\u62e9\uff09',
    'loginLog.filter.byUsername': '\u6309\u7528\u6237\u540d',
    'loginLog.filter.byLoginResult': '\u6309\u767b\u5f55\u7ed3\u679c',
    'loginLog.filter.dateRangeLabel':
        '\u65e5\u671f\u8303\u56f4\uff1a@start \u81f3 @end',
    'loginLog.filter.selectDateRange': '\u9009\u62e9\u65e5\u671f\u8303\u56f4',
    'loginLog.filter.tooltip': '\u6309\u65e5\u671f\u8303\u56f4\u641c\u7d22',
    'loginLog.filter.startDate': '\u5f00\u59cb\u65e5\u671f',
    'loginLog.filter.endDate': '\u7ed3\u675f\u65e5\u671f',
    'loginLog.filter.clearDateRange': '\u6e05\u9664\u65e5\u671f\u8303\u56f4',
    'loginLog.detail.id': '\u65e5\u5fd7 ID\uff1a@value',
    'loginLog.detail.username': '\u7528\u6237\u540d\uff1a@value',
    'loginLog.detail.loginIp': '\u767b\u5f55 IP \u5730\u5740\uff1a@value',
    'loginLog.detail.loginResult': '\u767b\u5f55\u7ed3\u679c\uff1a@value',
    'loginLog.detail.loginTime': '\u767b\u5f55\u65f6\u95f4\uff1a@value',
    'loginLog.detail.browserType': '\u6d4f\u89c8\u5668\u7c7b\u578b\uff1a@value',
    'loginLog.detail.osVersion':
        '\u64cd\u4f5c\u7cfb\u7edf\u7248\u672c\uff1a@value',
    'loginLog.detail.remarks': '\u5907\u6ce8\uff1a@value',
    'loginLog.action.relogin': '\u91cd\u65b0\u767b\u5f55',
    'loginLog.action.create': '\u521b\u5efa',
    'loginLog.action.edit': '\u7f16\u8f91\u65e5\u5fd7',
    'loginLog.action.delete': '\u5220\u9664\u65e5\u5fd7',
    'operationLog.page.title': '\u64cd\u4f5c\u65e5\u5fd7',
    'operationLog.error.unauthorized':
        '\u672a\u6388\u6743\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'operationLog.error.expired':
        '\u767b\u5f55\u5df2\u8fc7\u671f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'operationLog.error.invalidLogin':
        '\u65e0\u6548\u7684\u767b\u5f55\u4fe1\u606f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'operationLog.error.adminOnly':
        '\u6743\u9650\u4e0d\u8db3\uff1a\u4ec5\u7ba1\u7406\u5458\u53ef\u8bbf\u95ee\u6b64\u9875\u9762',
    'operationLog.error.initFailed': '\u521d\u59cb\u5316\u5931\u8d25: @error',
    'operationLog.error.roleCheckFailed':
        '\u9a8c\u8bc1\u89d2\u8272\u5931\u8d25: @error',
    'operationLog.error.loadFailed':
        '\u52a0\u8f7d\u64cd\u4f5c\u65e5\u5fd7\u5931\u8d25: @error',
    'operationLog.error.request': '\u8bf7\u6c42\u9519\u8bef: @message',
    'operationLog.error.forbidden': '\u65e0\u6743\u9650: @message',
    'operationLog.error.notFound': '\u672a\u627e\u5230: @message',
    'operationLog.error.duplicateRequest': '\u91cd\u590d\u8bf7\u6c42: @message',
    'operationLog.error.server': '\u670d\u52a1\u5668\u9519\u8bef: @message',
    'operationLog.error.operationFailed': '\u64cd\u4f5c\u5931\u8d25: @error',
    'operationLog.workspace.eyebrow': '\u64cd\u4f5c\u65e5\u5fd7\u4e2d\u5fc3',
    'operationLog.workspace.title': '\u64cd\u4f5c\u6d3b\u52a8\u6d41',
    'operationLog.workspace.subtitle':
        '\u6309\u64cd\u4f5c\u4eba\u3001\u7ed3\u679c\u6216\u65f6\u95f4\u8303\u56f4\u641c\u7d22\uff0c\u5728\u4e00\u4e2a\u96c6\u4e2d\u63a7\u5236\u53f0\u4e2d\u67e5\u770b\u8fd1\u671f\u540e\u7aef\u64cd\u4f5c\u3002',
    'operationLog.workspace.signal.query': '\u641c\u7d22\uff1a@value',
    'operationLog.workspace.signal.queryIdle':
        '\u641c\u7d22\u8303\u56f4\uff1a\u6240\u6709\u5df2\u52a0\u8f7d\u64cd\u4f5c\u65e5\u5fd7',
    'operationLog.workspace.signal.rangeIdle':
        '\u672a\u9009\u62e9\u65f6\u95f4\u8303\u56f4',
    'operationLog.workspace.metric.loaded': '\u5df2\u52a0\u8f7d',
    'operationLog.workspace.metric.visible': '\u5f53\u524d\u53ef\u89c1',
    'operationLog.workspace.metric.success': '\u6210\u529f',
    'operationLog.workspace.metric.failed': '\u5931\u8d25',
    'operationLog.workspace.filterEyebrow': '\u7b5b\u9009',
    'operationLog.workspace.filterTitle':
        '\u641c\u7d22\u4e0e\u7f29\u5c0f\u64cd\u4f5c\u8303\u56f4',
    'operationLog.workspace.filterBody':
        '\u5207\u6362\u641c\u7d22\u6a21\u5f0f\uff0c\u5e94\u7528\u65f6\u95f4\u8303\u56f4\uff0c\u5e76\u5237\u65b0\u5f53\u524d\u65e5\u5fd7\u6d41\u3002',
    'operationLog.workspace.filterMode': '\u641c\u7d22\u6a21\u5f0f',
    'operationLog.workspace.filterReset': '\u91cd\u7f6e\u7b5b\u9009',
    'operationLog.workspace.filterRefresh': '\u5237\u65b0\u65e5\u5fd7',
    'operationLog.workspace.listEyebrow': '\u65e5\u5fd7\u6d41',
    'operationLog.workspace.listTitle': '\u64cd\u4f5c\u8bb0\u5f55',
    'operationLog.workspace.listBody':
        '\u901a\u8fc7\u7ed3\u679c\u3001\u64cd\u4f5c\u4eba\u3001\u65f6\u95f4\u548c\u5185\u5bb9\u5feb\u901f\u5b9a\u4f4d\u6700\u65b0\u64cd\u4f5c\u3002',
    'operationLog.workspace.emptyTitle':
        '\u5f53\u524d\u89c6\u56fe\u6ca1\u6709\u64cd\u4f5c\u65e5\u5fd7',
    'operationLog.workspace.errorTitle':
        '\u64cd\u4f5c\u65e5\u5fd7\u52a0\u8f7d\u5931\u8d25',
    'operationLog.error.idMissingEdit':
        '\u65e0\u6cd5\u7f16\u8f91\uff1a\u65e5\u5fd7 ID \u7f3a\u5931\u3002',
    'operationLog.error.idMissingDelete':
        '\u65e0\u6cd5\u5220\u9664\uff1a\u65e5\u5fd7 ID \u7f3a\u5931\u3002',
    'operationLog.empty.filtered':
        '\u672a\u627e\u5230\u7b26\u5408\u5f53\u524d\u7b5b\u9009\u6761\u4ef6\u7684\u64cd\u4f5c\u65e5\u5fd7',
    'operationLog.empty.default': '\u6682\u65e0\u64cd\u4f5c\u65e5\u5fd7',
    'operationLog.dialog.createTitle': '\u521b\u5efa\u64cd\u4f5c\u65e5\u5fd7',
    'operationLog.dialog.editTitle': '\u7f16\u8f91\u64cd\u4f5c\u65e5\u5fd7',
    'operationLog.field.userId': '\u7528\u6237 ID',
    'operationLog.field.operationContent': '\u64cd\u4f5c\u5185\u5bb9',
    'operationLog.field.operationResult': '\u64cd\u4f5c\u7ed3\u679c',
    'operationLog.field.remarks': '\u5907\u6ce8',
    'operationLog.field.requestIp': 'IP \u5730\u5740',
    'operationLog.field.operationTime': '\u64cd\u4f5c\u65f6\u95f4',
    'operationLog.validation.userIdRequired':
        '\u7528\u6237 ID \u4e0d\u80fd\u4e3a\u7a7a',
    'operationLog.validation.userIdNumeric':
        '\u7528\u6237 ID \u5fc5\u987b\u662f\u6570\u5b57',
    'operationLog.validation.userIdTooLong':
        '\u7528\u6237 ID \u4e0d\u80fd\u8d85\u8fc720\u4e2a\u5b57\u7b26',
    'operationLog.validation.operationContentRequired':
        '\u64cd\u4f5c\u5185\u5bb9\u4e0d\u80fd\u4e3a\u7a7a',
    'operationLog.validation.operationContentTooLong':
        '\u64cd\u4f5c\u5185\u5bb9\u4e0d\u80fd\u8d85\u8fc7500\u4e2a\u5b57\u7b26',
    'operationLog.validation.operationResultRequired':
        '\u64cd\u4f5c\u7ed3\u679c\u4e0d\u80fd\u4e3a\u7a7a',
    'operationLog.validation.operationResultTooLong':
        '\u64cd\u4f5c\u7ed3\u679c\u4e0d\u80fd\u8d85\u8fc7100\u4e2a\u5b57\u7b26',
    'operationLog.validation.remarksTooLong':
        '\u5907\u6ce8\u4e0d\u80fd\u8d85\u8fc7500\u4e2a\u5b57\u7b26',
    'operationLog.success.created':
        '\u64cd\u4f5c\u65e5\u5fd7\u521b\u5efa\u6210\u529f',
    'operationLog.success.updated':
        '\u64cd\u4f5c\u65e5\u5fd7\u66f4\u65b0\u6210\u529f',
    'operationLog.success.deleted':
        '\u64cd\u4f5c\u65e5\u5fd7\u5220\u9664\u6210\u529f',
    'operationLog.delete.confirmTitle': '\u786e\u8ba4\u5220\u9664',
    'operationLog.delete.confirmBody':
        '\u786e\u5b9a\u8981\u5220\u9664\u6b64\u64cd\u4f5c\u65e5\u5fd7\u5417\uff1f\u6b64\u64cd\u4f5c\u4e0d\u53ef\u64a4\u9500\u3002',
    'operationLog.search.userId': '\u641c\u7d22\u7528\u6237 ID',
    'operationLog.search.operationResult':
        '\u641c\u7d22\u64cd\u4f5c\u7ed3\u679c',
    'operationLog.search.timeRangeSelected':
        '\u641c\u7d22\u65f6\u95f4\u8303\u56f4\uff08\u5df2\u9009\u62e9\uff09',
    'operationLog.filter.byUserId': '\u6309\u7528\u6237 ID',
    'operationLog.filter.byOperationResult': '\u6309\u64cd\u4f5c\u7ed3\u679c',
    'operationLog.filter.dateRangeLabel':
        '\u65e5\u671f\u8303\u56f4\uff1a@start \u81f3 @end',
    'operationLog.filter.selectDateRange':
        '\u9009\u62e9\u65e5\u671f\u8303\u56f4',
    'operationLog.filter.tooltip': '\u6309\u65e5\u671f\u8303\u56f4\u641c\u7d22',
    'operationLog.filter.startDate': '\u5f00\u59cb\u65e5\u671f',
    'operationLog.filter.endDate': '\u7ed3\u675f\u65e5\u671f',
    'operationLog.filter.clearDateRange':
        '\u6e05\u9664\u65e5\u671f\u8303\u56f4',
    'operationLog.detail.id': '\u65e5\u5fd7 ID\uff1a@value',
    'operationLog.detail.userId': '\u7528\u6237 ID\uff1a@value',
    'operationLog.detail.operationContent':
        '\u64cd\u4f5c\u5185\u5bb9\uff1a@value',
    'operationLog.detail.operationResult':
        '\u64cd\u4f5c\u7ed3\u679c\uff1a@value',
    'operationLog.detail.operationTime': '\u64cd\u4f5c\u65f6\u95f4\uff1a@value',
    'operationLog.detail.requestIp': 'IP \u5730\u5740\uff1a@value',
    'operationLog.detail.remarks': '\u5907\u6ce8\uff1a@value',
    'operationLog.action.relogin': '\u91cd\u65b0\u767b\u5f55',
    'operationLog.action.create': '\u521b\u5efa',
    'operationLog.action.edit': '\u7f16\u8f91\u64cd\u4f5c\u65e5\u5fd7',
    'operationLog.action.delete': '\u5220\u9664\u64cd\u4f5c\u65e5\u5fd7',
    'systemLog.page.title': '\u7cfb\u7edf\u65e5\u5fd7',
    'systemLog.section.overview': '\u7cfb\u7edf\u6982\u89c8',
    'systemLog.section.recentLogin': '\u8fd1\u671f\u767b\u5f55\u65e5\u5fd7',
    'systemLog.section.recentOperation': '\u8fd1\u671f\u64cd\u4f5c\u65e5\u5fd7',
    'systemLog.overview.loginLogCount': '\u767b\u5f55\u65e5\u5fd7',
    'systemLog.overview.operationLogCount': '\u64cd\u4f5c\u65e5\u5fd7',
    'systemLog.overview.requestHistoryCount': '\u8bf7\u6c42\u5386\u53f2',
    'systemLog.empty.overview':
        '\u6682\u65e0\u7cfb\u7edf\u6982\u89c8\u6570\u636e',
    'systemLog.empty.login': '\u6682\u65e0\u767b\u5f55\u65e5\u5fd7',
    'systemLog.empty.operation': '\u6682\u65e0\u64cd\u4f5c\u65e5\u5fd7',
    'systemLog.error.unauthorized':
        '\u672a\u6388\u6743\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'systemLog.error.expired':
        '\u767b\u5f55\u5df2\u8fc7\u671f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'systemLog.error.invalidLogin':
        '\u65e0\u6548\u7684\u767b\u5f55\u4fe1\u606f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'systemLog.error.adminOnly':
        '\u6743\u9650\u4e0d\u8db3\uff1a\u4ec5\u7ba1\u7406\u5458\u53ef\u8bbf\u95ee\u6b64\u9875\u9762',
    'systemLog.error.initFailed': '\u521d\u59cb\u5316\u5931\u8d25: @error',
    'systemLog.error.roleCheckFailed':
        '\u9a8c\u8bc1\u89d2\u8272\u5931\u8d25: @error',
    'systemLog.error.loadFailed':
        '\u52a0\u8f7d\u7cfb\u7edf\u65e5\u5fd7\u5931\u8d25: @error',
    'systemLog.error.request': '\u8bf7\u6c42\u9519\u8bef: @message',
    'systemLog.error.forbidden': '\u65e0\u6743\u9650: @message',
    'systemLog.error.notFound': '\u672a\u627e\u5230: @message',
    'systemLog.error.duplicateRequest': '\u91cd\u590d\u8bf7\u6c42: @message',
    'systemLog.error.server': '\u670d\u52a1\u5668\u9519\u8bef: @message',
    'systemLog.error.operationFailed': '\u64cd\u4f5c\u5931\u8d25: @error',
    'systemLog.workspace.eyebrow': '\u7cfb\u7edf\u65e5\u5fd7\u4e2d\u5fc3',
    'systemLog.workspace.title': '\u7cfb\u7edf\u6d3b\u52a8\u63a7\u5236\u53f0',
    'systemLog.workspace.subtitle':
        '\u5728\u4e00\u4e2a\u66f4\u96c6\u4e2d\u7684\u65e5\u5fd7\u89c6\u56fe\u4e2d\u76d1\u63a7\u6982\u89c8\u8ba1\u6570\u3001\u8fd1\u671f\u767b\u5f55\u548c\u8fd1\u671f\u64cd\u4f5c\u3002',
    'systemLog.workspace.signal.login': '\u8fd1\u671f\u767b\u5f55\uff1a@count',
    'systemLog.workspace.signal.operation':
        '\u8fd1\u671f\u64cd\u4f5c\uff1a@count',
    'systemLog.workspace.signal.refresh':
        '\u53ef\u4e0b\u62c9\u5237\u65b0\u6216\u4f7f\u7528\u9876\u90e8\u64cd\u4f5c',
    'systemLog.workspace.metric.overview': '\u6982\u89c8\u5757',
    'systemLog.workspace.metric.login': '\u767b\u5f55\u8bb0\u5f55',
    'systemLog.workspace.metric.operation': '\u64cd\u4f5c\u8bb0\u5f55',
    'systemLog.workspace.metric.alert': '\u9700\u5173\u6ce8',
    'systemLog.workspace.overviewBody':
        '\u901a\u8fc7\u6982\u89c8\u8ba1\u6570\u5feb\u901f\u5224\u65ad\u65e5\u5fd7\u63a5\u5165\u548c\u6570\u91cf\u662f\u5426\u6b63\u5e38\u3002',
    'systemLog.workspace.loginEyebrow': '\u767b\u5f55\u6d41',
    'systemLog.workspace.loginBody':
        '\u5728\u6392\u67e5\u8d26\u53f7\u8bbf\u95ee\u6216\u53ef\u7591\u6d3b\u52a8\u65f6\uff0c\u5148\u67e5\u8fd1\u671f\u767b\u5f55\u3002',
    'systemLog.workspace.operationEyebrow': '\u64cd\u4f5c\u6d41',
    'systemLog.workspace.operationBody':
        '\u901a\u8fc7\u8fd1\u671f\u64cd\u4f5c\u65e5\u5fd7\u67e5\u770b\u53d8\u66f4\u3001\u7ed3\u679c\u548c\u64cd\u4f5c\u4eba\u8f68\u8ff9\u3002',
    'systemLog.workspace.errorTitle':
        '\u7cfb\u7edf\u65e5\u5fd7\u52a0\u8f7d\u5931\u8d25',
    'systemLog.detail.loginResult': '\u7ed3\u679c\uff1a@value',
    'systemLog.detail.loginIp': 'IP\uff1a@value',
    'systemLog.detail.loginLocation': '\u4f4d\u7f6e\uff1a@value',
    'systemLog.detail.loginDevice': '\u7ec8\u7aef\uff1a@value',
    'systemLog.detail.remarks': '\u5907\u6ce8\uff1a@value',
    'systemLog.detail.operationType': '\u7c7b\u578b\uff1a@value',
    'systemLog.detail.user': '\u7528\u6237\uff1a@value',
    'systemLog.detail.operationResult': '\u7ed3\u679c\uff1a@value',
    'systemLog.detail.operationContent': '\u5185\u5bb9\uff1a@value',
    'systemLog.detail.requestIp': 'IP\uff1a@value',
    'systemLog.action.relogin': '\u91cd\u65b0\u767b\u5f55',
    'systemLog.value.unknownUser': '\u672a\u77e5\u7528\u6237',
    'systemLog.value.unknownModule': '\u672a\u77e5\u6a21\u5757',
    'backupRestore.page.title': '\u5907\u4efd\u4e0e\u6062\u590d\u7ba1\u7406',
    'backupRestore.detailPage.title': '\u5907\u4efd\u8be6\u60c5',
    'backupRestore.dialog.editTitle': '\u7f16\u8f91\u5907\u4efd',
    'backupRestore.search.filterType': '\u68c0\u7d22\u6761\u4ef6',
    'backupRestore.search.type.all': '\u5168\u90e8\u8bb0\u5f55',
    'backupRestore.search.type.fileName': '\u6587\u4ef6\u540d',
    'backupRestore.search.type.backupTime': '\u5907\u4efd\u65f6\u95f4',
    'backupRestore.search.type.restoreTime': '\u6062\u590d\u65f6\u95f4',
    'backupRestore.search.type.backupType': '\u5907\u4efd\u7c7b\u578b',
    'backupRestore.search.type.handler': '\u5907\u4efd\u6267\u884c\u4eba',
    'backupRestore.search.type.status': '\u4efb\u52a1\u72b6\u6001',
    'backupRestore.search.type.restoreStatus': '\u6062\u590d\u72b6\u6001',
    'backupRestore.search.byFileName':
        '\u6309\u6587\u4ef6\u540d\u641c\u7d22\u5907\u4efd',
    'backupRestore.search.byBackupTime':
        '\u6309\u5907\u4efd\u65f6\u95f4\u641c\u7d22\u5907\u4efd',
    'backupRestore.search.byRestoreTime':
        '\u6309\u6062\u590d\u65f6\u95f4\u641c\u7d22\u5907\u4efd',
    'backupRestore.search.byType':
        '\u6309\u5907\u4efd\u7c7b\u578b\u641c\u7d22\u5907\u4efd',
    'backupRestore.search.byHandler':
        '\u6309\u5907\u4efd\u6267\u884c\u4eba\u641c\u7d22\u5907\u4efd',
    'backupRestore.search.byStatus':
        '\u6309\u4efb\u52a1\u72b6\u6001\u7b5b\u9009',
    'backupRestore.search.byRestoreStatus':
        '\u6309\u6062\u590d\u72b6\u6001\u7b5b\u9009',
    'backupRestore.search.allStatuses': '\u5168\u90e8\u72b6\u6001',
    'backupRestore.empty.noRecords':
        '\u6ca1\u6709\u627e\u5230\u5907\u4efd\u8bb0\u5f55',
    'backupRestore.error.notLoggedIn':
        '\u672a\u767b\u5f55\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'backupRestore.error.adminOnly':
        '\u6743\u9650\u4e0d\u8db3\uff1a\u4ec5\u7ba1\u7406\u5458\u53ef\u8bbf\u95ee\u6b64\u9875\u9762',
    'backupRestore.error.initFailed': '\u521d\u59cb\u5316\u5931\u8d25: @error',
    'backupRestore.error.loadFailed':
        '\u52a0\u8f7d\u5907\u4efd\u8bb0\u5f55\u5931\u8d25: @error',
    'backupRestore.error.createFailed':
        '\u521b\u5efa\u5907\u4efd\u5931\u8d25: @error',
    'backupRestore.error.updateFailed':
        '\u66f4\u65b0\u5907\u4efd\u5931\u8d25: @error',
    'backupRestore.error.restoreFailed':
        '\u6062\u590d\u5907\u4efd\u5931\u8d25: @error',
    'backupRestore.error.deleteFailed':
        '\u5220\u9664\u5907\u4efd\u5931\u8d25: @error',
    'backupRestore.error.server': '\u670d\u52a1\u5668\u9519\u8bef',
    'backupRestore.error.fileNameRequired':
        '\u6587\u4ef6\u540d\u4e0d\u80fd\u4e3a\u7a7a',
    'backupRestore.validation.required': '\u8bf7\u586b\u5199@field',
    'backupRestore.validation.fileNameTooLong':
        '\u6587\u4ef6\u540d\u4e0d\u80fd\u8d85\u8fc7255\u4e2a\u5b57\u7b26',
    'backupRestore.validation.remarksTooLong':
        '\u5907\u6ce8\u4e0d\u80fd\u8d85\u8fc7500\u4e2a\u5b57\u7b26',
    'backupRestore.success.created': '\u5907\u4efd\u521b\u5efa\u6210\u529f',
    'backupRestore.success.updated': '\u5907\u4efd\u66f4\u65b0\u6210\u529f',
    'backupRestore.success.restored': '\u5907\u4efd\u6062\u590d\u6210\u529f',
    'backupRestore.success.deleted': '\u5907\u4efd\u5220\u9664\u6210\u529f',
    'backupRestore.action.create': '\u521b\u5efa\u65b0\u5907\u4efd',
    'backupRestore.action.restore': '\u6062\u590d\u6b64\u5907\u4efd',
    'backupRestore.action.edit': '\u7f16\u8f91\u6b64\u5907\u4efd',
    'backupRestore.action.delete': '\u5220\u9664\u6b64\u5907\u4efd',
    'backupRestore.action.viewDetails': '\u67e5\u770b\u8be6\u60c5',
    'backupRestore.action.resetFilters': '\u91cd\u7f6e\u7b5b\u9009',
    'backupRestore.field.backupId': '\u5907\u4efd ID',
    'backupRestore.field.backupType': '\u5907\u4efd\u7c7b\u578b',
    'backupRestore.field.fileName': '\u6587\u4ef6\u540d',
    'backupRestore.field.backupTime': '\u5907\u4efd\u65f6\u95f4',
    'backupRestore.field.backupHandler': '\u5907\u4efd\u6267\u884c\u4eba',
    'backupRestore.field.restoreTime': '\u6062\u590d\u65f6\u95f4',
    'backupRestore.field.restoreStatus': '\u6062\u590d\u72b6\u6001',
    'backupRestore.field.restoreHandler': '\u6062\u590d\u6267\u884c\u4eba',
    'backupRestore.field.status': '\u4efb\u52a1\u72b6\u6001',
    'backupRestore.field.remarks': '\u5907\u6ce8',
    'backupRestore.field.idempotencyKey': '\u5e42\u7b49\u952e',
    'backupRestore.detail.backupType': '\u5907\u4efd\u7c7b\u578b\uff1a@value',
    'backupRestore.detail.fileName': '\u6587\u4ef6\u540d\uff1a@value',
    'backupRestore.detail.backupTime': '\u5907\u4efd\u65f6\u95f4\uff1a@value',
    'backupRestore.detail.backupHandler':
        '\u5907\u4efd\u6267\u884c\u4eba\uff1a@value',
    'backupRestore.detail.restoreTime': '\u6062\u590d\u65f6\u95f4\uff1a@value',
    'backupRestore.detail.restoreStatus':
        '\u6062\u590d\u72b6\u6001\uff1a@value',
    'backupRestore.detail.restoreHandler':
        '\u6062\u590d\u6267\u884c\u4eba\uff1a@value',
    'backupRestore.detail.status': '\u4efb\u52a1\u72b6\u6001\uff1a@value',
    'backupRestore.status.pending': '\u5f85\u5904\u7406',
    'backupRestore.status.restored': '\u5df2\u6062\u590d',
    'backupRestore.status.failed': '\u5931\u8d25',
    'backupRestore.status.notRestored': '\u672a\u6062\u590d',
    'backupRestore.type.full': '\u5168\u91cf\u5907\u4efd',
    'backupRestore.type.incremental': '\u589e\u91cf\u5907\u4efd',
    'backupRestore.type.differential': '\u5dee\u5f02\u5907\u4efd',
    'backupRestore.type.manual': '\u624b\u52a8\u5907\u4efd',
    'backupRestore.type.auto': '\u81ea\u52a8\u5907\u4efd',
    'backupRestore.value.manualCreatedRemarks':
        '\u624b\u52a8\u521b\u5efa\u7684\u5907\u4efd',
    'progress.pageTitle': '\u8fdb\u5ea6\u6d88\u606f',
    'progress.empty': '\u6682\u65e0\u8fdb\u5ea6\u8bb0\u5f55',
    'progress.status': '\u72b6\u6001',
    'progress.status.pending': '\u5f85\u5904\u7406',
    'progress.status.processing': '\u5904\u7406\u4e2d',
    'progress.status.completed': '\u5df2\u5b8c\u6210',
    'progress.status.archived': '\u5df2\u5f52\u6863',
    'progress.submitTime': '\u63d0\u4ea4\u65f6\u95f4',
    'progress.viewDetail': '\u67e5\u770b\u8be6\u60c5',
    'progress.filter.status': '\u72b6\u6001\u7b5b\u9009',
    'progress.filter.timeRange': '\u6309\u65f6\u95f4\u8303\u56f4\u7b5b\u9009',
    'progress.filter.clear': '\u6e05\u9664\u7b5b\u9009',
    'progress.filter.selectTimeRange': '\u9009\u62e9\u65f6\u95f4\u8303\u56f4',
    'progress.filter.clearTooltip': '\u6e05\u9664\u7b5b\u9009',
    'progress.view.items': '\u8fdb\u5ea6\u6d88\u606f',
    'progress.view.refunds': '\u9000\u6b3e\u5ba1\u8ba1',
    'progress.refund.empty':
        '\u672a\u627e\u5230\u9000\u6b3e\u5ba1\u8ba1\u8bb0\u5f55',
    'progress.refund.filter.fineId': '\u7f5a\u6b3e ID',
    'progress.refund.filter.paymentId': '\u7f34\u8d39 ID',
    'progress.refund.filter.searchTooltip':
        '\u67e5\u8be2\u9000\u6b3e\u5ba1\u8ba1',
    'progress.refund.filter.clearTooltip':
        '\u6e05\u7a7a\u9000\u6b3e\u7b5b\u9009',
    'progress.refund.status.all': '\u5168\u90e8\u72b6\u6001',
    'progress.refund.type.partial': '\u90e8\u5206\u9000\u6b3e',
    'progress.refund.type.waive': '\u514d\u7f5a\u5e76\u9000\u6b3e',
    'progress.refund.type.partialFailed':
        '\u90e8\u5206\u9000\u6b3e\u5931\u8d25',
    'progress.refund.type.waiveFailed':
        '\u514d\u7f5a\u5e76\u9000\u6b3e\u5931\u8d25',
    'progress.refund.detail.businessType':
        '\u9000\u6b3e\u7c7b\u578b\uff1a@value',
    'progress.refund.detail.businessId': '\u7f34\u8d39 ID\uff1a@value',
    'progress.refund.detail.fineId': '\u7f5a\u6b3e ID\uff1a@value',
    'progress.refund.detail.refundAmount':
        '\u9000\u6b3e\u91d1\u989d\uff1a@value',
    'progress.refund.detail.operator': '\u64cd\u4f5c\u4eba\uff1a@value',
    'progress.refund.detail.reason': '\u539f\u56e0\uff1a@value',
    'progress.refund.detail.failure': '\u5931\u8d25\u4fe1\u606f\uff1a@value',
    'progress.refund.detail.requestIp': 'IP\uff1a@value',
    'progress.refund.detail.userId': '\u7528\u6237 ID\uff1a@value',
    'progress.refund.detail.updatedTime':
        '\u66f4\u65b0\u65f6\u95f4\uff1a@value',
    'progress.refund.detail.idempotencyKey': '\u5e42\u7b49\u952e\uff1a@value',
    'progress.refund.detail.noReason': '\u65e0\u9000\u6b3e\u539f\u56e0',
    'progress.submitNew': '\u63d0\u4ea4\u65b0\u8fdb\u5ea6',
    'progress.dialog.submitTitle': '\u63d0\u4ea4\u65b0\u8fdb\u5ea6',
    'progress.dialog.editTitle': '\u7f16\u8f91\u8fdb\u5ea6',
    'progress.field.title': '\u8fdb\u5ea6\u6807\u9898',
    'progress.field.details': '\u8be6\u60c5',
    'progress.field.detailsOptional': '\u8be6\u60c5\uff08\u53ef\u9009\uff09',
    'progress.field.relatedAppealOptional':
        '\u5173\u8054\u7533\u8bc9\uff08\u53ef\u9009\uff09',
    'progress.field.appealOption': '\u7533\u8bc9\uff1a@name (ID: @id)',
    'progress.validation.required': '\u8bf7\u586b\u5199@field',
    'progress.validation.titleAndDetails':
        '\u6807\u9898\u548c\u8be6\u60c5\u4e0d\u80fd\u4e3a\u7a7a\u3002',
    'progress.validation.titleRequired': '\u6807\u9898\u4e0d\u80fd\u4e3a\u7a7a',
    'progress.validation.titleTooLong':
        '\u8fdb\u5ea6\u6807\u9898\u4e0d\u80fd\u8d85\u8fc7100\u4e2a\u5b57\u7b26',
    'progress.validation.detailsTooLong':
        '\u8fdb\u5ea6\u8be6\u60c5\u4e0d\u80fd\u8d85\u8fc7500\u4e2a\u5b57\u7b26',
    'progress.error.adminOnly':
        '\u6743\u9650\u4e0d\u8db3\uff1a\u4ec5\u7ba1\u7406\u5458\u53ef\u8bbf\u95ee',
    'progress.detail.status': '\u72b6\u6001\uff1a@value',
    'progress.detail.submitTime': '\u63d0\u4ea4\u65f6\u95f4\uff1a@value',
    'progress.action.createTooltip': '\u521b\u5efa\u8fdb\u5ea6',
    'progress.action.viewEdit': '\u67e5\u770b/\u7f16\u8f91',
    'progress.action.delete': '\u5220\u9664',
    'progress.action.setPending': '\u8bbe\u4e3a\u5f85\u5904\u7406',
    'progress.action.setProcessing': '\u8bbe\u4e3a\u5904\u7406\u4e2d',
    'progress.action.setCompleted': '\u8bbe\u4e3a\u5df2\u5b8c\u6210',
    'progress.action.setArchived': '\u8bbe\u4e3a\u5df2\u5f52\u6863',
    'progress.delete.confirmTitle': '\u786e\u8ba4\u5220\u9664',
    'progress.delete.confirmMessage':
        '\u60a8\u786e\u5b9a\u8981\u5220\u9664\u6b64\u8fdb\u5ea6\u8bb0\u5f55\u5417\uff1f\u6b64\u64cd\u4f5c\u4e0d\u53ef\u64a4\u9500\u3002',
    'progress.delete.confirmBody':
        '\u786e\u5b9a\u8981\u5220\u9664\u6b64\u8fdb\u5ea6\u8bb0\u5f55\u5417\uff1f\u6b64\u64cd\u4f5c\u4e0d\u53ef\u64a4\u9500\u3002',
    'progress.detail.title': '\u8fdb\u5ea6\u8be6\u60c5',
    'progress.detail.id': '\u8fdb\u5ea6 ID',
    'progress.detail.user': '\u63d0\u4ea4\u7528\u6237',
    'progress.detail.relatedBusiness': '\u5173\u8054\u4e1a\u52a1',
    'progress.action.processing': '\u5904\u7406\u4e2d',
    'progress.action.completed': '\u5b8c\u6210',
    'progress.error.idMissingUpdate':
        '\u65e0\u6cd5\u66f4\u65b0\uff1a\u8fdb\u5ea6 ID \u4e3a\u7a7a\u3002',
    'progress.error.idMissingDelete':
        '\u65e0\u6cd5\u5220\u9664\uff1a\u8fdb\u5ea6 ID \u4e3a\u7a7a\u3002',
    'progress.error.loadAppeals':
        '\u52a0\u8f7d\u7533\u8bc9\u5931\u8d25\uff1a@error',
    'progress.error.fetchFailed':
        '\u52a0\u8f7d\u8fdb\u5ea6\u8bb0\u5f55\u5931\u8d25\u3002',
    'progress.error.submitFailed': '\u63d0\u4ea4\u8fdb\u5ea6\u5931\u8d25\u3002',
    'progress.error.updateFailed': '\u66f4\u65b0\u8fdb\u5ea6\u5931\u8d25\u3002',
    'progress.error.fetchByTimeRangeFailed':
        '\u52a0\u8f7d\u6240\u9009\u65f6\u95f4\u8303\u56f4\u7684\u8fdb\u5ea6\u8bb0\u5f55\u5931\u8d25\u3002',
    'progress.error.request': '\u8bf7\u6c42\u9519\u8bef\uff1a@message',
    'progress.error.permission': '\u65e0\u6743\u9650\uff1a@message',
    'progress.error.notFound': '\u672a\u627e\u5230\uff1a@message',
    'progress.error.server': '\u670d\u52a1\u5668\u9519\u8bef\uff1a@message',
    'progress.error.operationFailed': '\u64cd\u4f5c\u5931\u8d25\uff1a@error',
    'progress.context.appealId': '\u7533\u8bc9 ID\uff1a@id',
    'progress.context.deductionId': '\u6263\u5206 ID\uff1a@id',
    'progress.context.driverId': '\u53f8\u673a ID\uff1a@id',
    'progress.context.fineId': '\u7f5a\u6b3e ID\uff1a@id',
    'progress.context.vehicleId': '\u8f66\u8f86 ID\uff1a@id',
    'progress.context.offenseId': '\u8fdd\u7ae0 ID\uff1a@id',
    'progress.context.noRelatedBusiness': '\u65e0\u5173\u8054\u4e1a\u52a1',
    'progress.success.submitted': '\u8fdb\u5ea6\u63d0\u4ea4\u6210\u529f\u3002',
    'progress.success.updated': '\u8fdb\u5ea6\u66f4\u65b0\u6210\u529f\u3002',
    'progress.success.statusUpdated':
        '\u72b6\u6001\u66f4\u65b0\u6210\u529f\u3002',
    'progress.error.statusUpdateFailed':
        '\u66f4\u65b0\u72b6\u6001\u5931\u8d25\uff1a@error',
    'progress.success.deleted': '\u5220\u9664\u6210\u529f\u3002',
    'progress.error.deleteFailed': '\u5220\u9664\u5931\u8d25\uff1a@error',
    'common.status.processing': '\u5904\u7406\u4e2d',
    'common.status.completed': '\u5df2\u5b8c\u6210',
    'common.status.archived': '\u5df2\u5f52\u6863',
    'trafficDashboard.page.title': '\u4ea4\u901a\u8fdd\u6cd5\u4eea\u8868\u677f',
    'trafficDashboard.error.loadFailed':
        '\u52a0\u8f7d\u4ea4\u901a\u8fdd\u6cd5\u4eea\u8868\u677f\u5931\u8d25\uff1a@error',
    'trafficDashboard.section.violationType':
        '\u8fdd\u6cd5\u7c7b\u578b\u5206\u5e03',
    'trafficDashboard.section.fineTrend':
        '\u7f5a\u6b3e\u4e0e\u6263\u5206\u8d8b\u52bf',
    'trafficDashboard.section.appealReason':
        '\u7533\u8bc9\u7406\u7531\u5206\u5e03',
    'trafficDashboard.section.paymentStatus':
        '\u7f5a\u6b3e\u652f\u4ed8\u72b6\u6001',
    'trafficDashboard.empty.violationType':
        '\u65e0\u8fdd\u6cd5\u7c7b\u578b\u6570\u636e',
    'trafficDashboard.empty.timeSeries':
        '\u65e0\u65f6\u95f4\u5e8f\u5217\u6570\u636e',
    'trafficDashboard.empty.appealReason':
        '\u65e0\u7533\u8bc9\u7406\u7531\u6570\u636e',
    'trafficDashboard.empty.paymentStatus':
        '\u65e0\u652f\u4ed8\u72b6\u6001\u6570\u636e',
    'trafficDashboard.empty.timeSeriesAvailable':
        '\u65e0\u53ef\u7528\u65f6\u95f4\u5e8f\u5217\u6570\u636e',
    'trafficDashboard.empty.dataAvailable': '\u65e0\u53ef\u7528\u6570\u636e',
    'trafficDashboard.empty.violationAvailable':
        '\u65e0\u53ef\u7528\u8fdd\u6cd5\u6570\u636e',
    'trafficDashboard.snackbar.violationType':
        '\u67e5\u770b\u8fdd\u6cd5\u7c7b\u578b\u8be6\u60c5',
    'trafficDashboard.snackbar.timeSeries':
        '\u67e5\u770b\u65f6\u95f4\u5e8f\u5217\u8be6\u60c5',
    'trafficDashboard.snackbar.appealReason':
        '\u67e5\u770b\u7533\u8bc9\u7406\u7531\u8be6\u60c5',
    'trafficDashboard.snackbar.paymentStatus':
        '\u67e5\u770b\u652f\u4ed8\u72b6\u6001\u8be6\u60c5',
    'trafficDashboard.snackbar.viewDetails':
        '\u67e5\u770b\u8be6\u60c5\uff1a@title',
    'trafficDashboard.metric.fine': '\u7f5a\u6b3e',
    'trafficDashboard.metric.points': '\u6263\u5206',
    'trafficDashboard.metric.total': '\u603b\u6570',
    'trafficDashboard.tooltip.fine': '@date\n\u7f5a\u6b3e\uff1a@value',
    'trafficDashboard.tooltip.count': '@label\n@value \u6b21',
    'trafficDashboard.violationType.speeding': '\u8d85\u901f',
    'trafficDashboard.violationType.redLight': '\u95ef\u7ea2\u706f',
    'trafficDashboard.violationType.illegalParking': '\u8fdd\u505c',
    'trafficDashboard.violationType.drunkDriving': '\u9152\u9a7e',
    'trafficDashboard.violationType.other': '\u5176\u4ed6',
    'trafficDashboard.appealReason.insufficientEvidence':
        '\u8bc1\u636e\u4e0d\u8db3',
    'trafficDashboard.appealReason.proceduralIssue': '\u7a0b\u5e8f\u4e0d\u5f53',
    'trafficDashboard.appealReason.misjudgment': '\u8bef\u5224',
    'trafficDashboard.appealReason.other': '\u5176\u4ed6',
    'trafficDashboard.paymentStatus.paid': '\u5df2\u652f\u4ed8',
    'trafficDashboard.paymentStatus.unpaid': '\u672a\u652f\u4ed8',
    'chart.noOffenseData': '\u6682\u65e0\u8fdd\u6cd5\u6570\u636e',
    'chart.noData': '\u6682\u65e0\u6570\u636e',
    'chart.total': '\u603b\u8ba1',
    'chart.error.loadData':
        '\u52a0\u8f7d\u56fe\u8868\u6570\u636e\u5931\u8d25\u3002',
    'search.hint': '\u8bf7\u8f93\u5165...',
    'common.none': '\u65e0',
    'offense.error.unauthorized':
        '\u672a\u6388\u6743\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'offense.error.userOnly':
        '\u6743\u9650\u4e0d\u8db3\uff1a\u4ec5\u7528\u6237\u53ef\u8bbf\u95ee\u6b64\u9875\u9762',
    'offense.error.loginExpired':
        '\u767b\u5f55\u5df2\u8fc7\u671f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'offense.error.driverNameMissing':
        '\u65e0\u6cd5\u83b7\u53d6\u53f8\u673a\u59d3\u540d\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'offense.error.invalidLogin':
        '\u65e0\u6548\u7684\u767b\u5f55\u4fe1\u606f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'offense.error.usernameMissing':
        '\u65e0\u6cd5\u786e\u5b9a\u5f53\u524d\u7528\u6237\u540d',
    'offense.error.initializeFailed': '\u521d\u59cb\u5316\u5931\u8d25: @error',
    'offense.error.noRecordsInRange':
        '\u672a\u627e\u5230\u7b26\u5408\u65f6\u95f4\u8303\u56f4\u7684\u8fdd\u6cd5\u8bb0\u5f55',
    'offense.error.noRecordsBySearch':
        '\u672a\u627e\u5230\u7b26\u5408\u641c\u7d22\u6761\u4ef6\u7684\u8fdd\u6cd5\u8bb0\u5f55',
    'offense.error.empty': '\u6682\u65e0\u8fdd\u6cd5\u8bb0\u5f55',
    'offense.error.notFound': '\u672a\u627e\u5230\u8fdd\u6cd5\u8bb0\u5f55',
    'offense.error.loadFailed':
        '\u83b7\u53d6\u8fdd\u6cd5\u8bb0\u5f55\u5931\u8d25: @error',
    'offense.error.badRequest': '\u8bf7\u6c42\u9519\u8bef: @message',
    'offense.error.forbidden': '\u65e0\u6743\u9650: @message',
    'offense.error.notFoundMessage': '\u672a\u627e\u5230: @message',
    'offense.error.duplicateRequest': '\u91cd\u590d\u8bf7\u6c42: @message',
    'offense.error.server': '\u670d\u52a1\u5668\u9519\u8bef: @message',
    'offense.error.operationFailed': '\u64cd\u4f5c\u5931\u8d25: @error',
    'offense.workspace.eyebrow': '\u8fdd\u7ae0\u5de5\u4f5c\u53f0',
    'offense.workspace.live': '\u5b9e\u65f6\u5217\u8868',
    'offense.workspace.filtered': '\u7b5b\u9009\u89c6\u56fe',
    'offense.workspace.title': '@name \u7684\u8fdd\u7ae0\u8bb0\u5f55',
    'offense.workspace.subtitle':
        '\u7528\u641c\u7d22\u3001\u65f6\u95f4\u8303\u56f4\u548c\u8be6\u7ec6\u4fe1\u606f\u5feb\u901f\u5b9a\u4f4d\u9700\u8981\u5904\u7406\u7684\u8bb0\u5f55\u3002',
    'offense.workspace.searchIdle':
        '\u641c\u7d22\u8303\u56f4\uff1a\u6240\u6709\u5df2\u52a0\u8f7d\u8bb0\u5f55',
    'offense.workspace.searchActive':
        '\u641c\u7d22\u5173\u952e\u8bcd\uff1a@value',
    'offense.workspace.rangeIdle': '\u672a\u9009\u62e9\u65f6\u95f4\u8303\u56f4',
    'offense.workspace.metric.loaded': '\u5df2\u52a0\u8f7d',
    'offense.workspace.metric.visible': '\u5f53\u524d\u53ef\u89c1',
    'offense.workspace.metric.pending': '\u5f85\u5904\u7406',
    'offense.workspace.metric.points': '\u5f53\u524d\u6263\u5206',
    'offense.workspace.metric.fine': '\u5f53\u524d\u7f5a\u6b3e',
    'offense.workspace.filterEyebrow': '\u7b5b\u9009',
    'offense.workspace.filterTitle':
        '\u641c\u7d22\u4e0e\u7f29\u5c0f\u8bb0\u5f55\u8303\u56f4',
    'offense.workspace.filterBody':
        '\u901a\u8fc7\u8fdd\u7ae0\u7c7b\u578b\u3001\u4ee3\u7801\u548c\u65f6\u95f4\u8303\u56f4\u5feb\u901f\u5b9a\u4f4d\u8bb0\u5f55\u3002',
    'offense.workspace.filterReset': '\u91cd\u7f6e\u7b5b\u9009',
    'offense.workspace.filterRefresh': '\u5237\u65b0\u8bb0\u5f55',
    'offense.workspace.listEyebrow': '\u8bb0\u5f55',
    'offense.workspace.listTitle': '\u8fdd\u7ae0\u5217\u8868',
    'offense.workspace.listBody':
        '\u6253\u5f00\u5355\u6761\u8bb0\u5f55\u53ef\u67e5\u770b\u72b6\u6001\u3001\u65f6\u95f4\u3001\u7f5a\u6b3e\u4e0e\u5730\u70b9\u3002',
    'offense.workspace.emptyTitle':
        '\u5f53\u524d\u89c6\u56fe\u6ca1\u6709\u8bb0\u5f55',
    'offense.workspace.emptyBody':
        '\u53ef\u4ee5\u66f4\u6362\u5173\u952e\u8bcd\u3001\u8c03\u6574\u65f6\u95f4\u8303\u56f4\u6216\u5237\u65b0\u8bb0\u5f55\u3002',
    'offense.workspace.errorTitle': '\u8bb0\u5f55\u52a0\u8f7d\u5931\u8d25',
    'offense.search.hint':
        '\u641c\u7d22\u8fdd\u6cd5\u7c7b\u578b\u6216\u4ee3\u7801',
    'offense.filter.rangeLabel': '\u65f6\u95f4\u8303\u56f4: @start \u81f3 @end',
    'offense.filter.select': '\u9009\u62e9\u65f6\u95f4\u8303\u56f4',
    'offense.filter.tooltip': '\u6309\u65f6\u95f4\u8303\u56f4\u7b5b\u9009',
    'offense.filter.startDate': '\u5f00\u59cb\u65e5\u671f',
    'offense.filter.endDate': '\u7ed3\u675f\u65e5\u671f',
    'offense.filter.clear': '\u6e05\u9664\u65f6\u95f4\u8303\u56f4',
    'offense.page.title': '\u6211\u7684\u8fdd\u6cd5\u8bb0\u5f55',
    'offense.action.relogin': '\u91cd\u65b0\u767b\u5f55',
    'offense.card.type': '\u8fdd\u6cd5\u7c7b\u578b: @value',
    'offense.card.licensePlate': '\u8f66\u724c\u53f7: @value',
    'offense.card.points': '\u6263\u5206: @value',
    'offense.card.time': '\u65f6\u95f4: @value',
    'offense.detail.title': '\u8fdd\u6cd5\u8be6\u60c5',
    'offense.detail.id': '\u8fdd\u6cd5 ID',
    'offense.detail.licensePlate': '\u8f66\u724c\u53f7',
    'offense.detail.driverName': '\u9a7e\u9a76\u5458\u59d3\u540d',
    'offense.detail.type': '\u8fdd\u6cd5\u7c7b\u578b',
    'offense.detail.code': '\u8fdd\u6cd5\u4ee3\u7801',
    'offense.detail.points': '\u6263\u5206',
    'offense.detail.amount': '\u7f5a\u6b3e\u91d1\u989d',
    'offense.detail.time': '\u8fdd\u6cd5\u65f6\u95f4',
    'offense.detail.location': '\u8fdd\u6cd5\u5730\u70b9',
    'offense.detail.processStatus': '\u5904\u7406\u72b6\u6001',
    'offense.detail.processResult': '\u5904\u7406\u7ed3\u679c',
    'offense.value.points': '@value \u5206',
    'offense.value.amount': '@value \u5143',
    'offenseAdmin.page.title': '\u8fdd\u6cd5\u884c\u4e3a\u7ba1\u7406',
    'offenseAdmin.action.add': '\u6dfb\u52a0\u8fdd\u6cd5\u4fe1\u606f',
    'offenseAdmin.action.refresh': '\u5237\u65b0\u5217\u8868',
    'offenseAdmin.action.relogin': '\u91cd\u65b0\u767b\u5f55',
    'offenseAdmin.action.edit': '\u7f16\u8f91\u8fdd\u6cd5\u4fe1\u606f',
    'offenseAdmin.action.delete': '\u5220\u9664\u8fdd\u6cd5\u4fe1\u606f',
    'offenseAdmin.search.driverName': '\u641c\u7d22\u53f8\u673a\u59d3\u540d',
    'offenseAdmin.search.licensePlate': '\u641c\u7d22\u8f66\u724c\u53f7',
    'offenseAdmin.search.offenseType': '\u641c\u7d22\u8fdd\u6cd5\u7c7b\u578b',
    'offenseAdmin.search.timeRangeSelected':
        '\u5df2\u9009\u62e9\u8fdd\u6cd5\u65f6\u95f4\u8303\u56f4',
    'offenseAdmin.filter.byDriverName': '\u6309\u53f8\u673a\u59d3\u540d',
    'offenseAdmin.filter.byLicensePlate': '\u6309\u8f66\u724c\u53f7',
    'offenseAdmin.filter.byOffenseType': '\u6309\u8fdd\u6cd5\u7c7b\u578b',
    'offenseAdmin.filter.dateRangeLabel':
        '\u8fdd\u6cd5\u65f6\u95f4\u8303\u56f4\uff1a@start \u81f3 @end',
    'offenseAdmin.filter.selectDateRange':
        '\u9009\u62e9\u8fdd\u6cd5\u65f6\u95f4\u8303\u56f4',
    'offenseAdmin.filter.tooltip':
        '\u6309\u8fdd\u6cd5\u65f6\u95f4\u8303\u56f4\u7b5b\u9009',
    'offenseAdmin.filter.startDate': '\u5f00\u59cb\u65e5\u671f',
    'offenseAdmin.filter.endDate': '\u7ed3\u675f\u65e5\u671f',
    'offenseAdmin.filter.clearDateRange':
        '\u6e05\u9664\u65e5\u671f\u8303\u56f4',
    'offenseAdmin.error.unauthorized':
        '\u672a\u6388\u6743\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'offenseAdmin.error.expired':
        '\u767b\u5f55\u5df2\u8fc7\u671f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'offenseAdmin.error.refreshedExpired':
        '\u65b0\u767b\u5f55\u4fe1\u606f\u5df2\u8fc7\u671f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'offenseAdmin.error.invalidLogin':
        '\u65e0\u6548\u7684\u767b\u5f55\u4fe1\u606f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'offenseAdmin.error.initFailed': '\u521d\u59cb\u5316\u5931\u8d25: @error',
    'offenseAdmin.error.httpStatus':
        '\u8bf7\u6c42\u5931\u8d25\uff08HTTP @statusCode\uff09\u3002',
    'offenseAdmin.error.roleCheckFailed':
        '\u9a8c\u8bc1\u89d2\u8272\u5931\u8d25: @error',
    'offenseAdmin.error.adminOnly':
        '\u6743\u9650\u4e0d\u8db3\uff1a\u4ec5\u7ba1\u7406\u5458\u53ef\u8bbf\u95ee\u6b64\u9875\u9762',
    'offenseAdmin.error.filteredEmpty':
        '\u672a\u627e\u5230\u7b26\u5408\u6761\u4ef6\u7684\u8fdd\u6cd5\u4fe1\u606f',
    'offenseAdmin.error.notFound': '\u672a\u627e\u5230\u8fdd\u6cd5\u8bb0\u5f55',
    'offenseAdmin.empty.default':
        '\u5f53\u524d\u6ca1\u6709\u8fdd\u6cd5\u8bb0\u5f55',
    'offenseAdmin.workspace.eyebrow': '\u8fdd\u7ae0\u63a7\u5236\u4e2d\u5fc3',
    'offenseAdmin.workspace.title':
        '\u8fdd\u7ae0\u7ba1\u7406\u5de5\u4f5c\u53f0',
    'offenseAdmin.workspace.subtitle':
        '\u6309\u9a7e\u9a76\u4eba\u3001\u8f66\u724c\u6216\u8fdd\u7ae0\u7c7b\u578b\u641c\u7d22\uff0c\u5728\u4e00\u4e2a\u96c6\u4e2d\u7684\u7ba1\u7406\u754c\u9762\u4e2d\u67e5\u770b\u5f53\u524d\u8bb0\u5f55\u3002',
    'offenseAdmin.workspace.signal.query': '\u641c\u7d22\uff1a@value',
    'offenseAdmin.workspace.signal.queryIdle':
        '\u641c\u7d22\u8303\u56f4\uff1a\u6240\u6709\u5df2\u52a0\u8f7d\u8fdd\u7ae0\u8bb0\u5f55',
    'offenseAdmin.workspace.signal.rangeIdle':
        '\u672a\u9009\u62e9\u65f6\u95f4\u8303\u56f4',
    'offenseAdmin.workspace.metric.loaded': '\u5df2\u52a0\u8f7d',
    'offenseAdmin.workspace.metric.visible': '\u5f53\u524d\u53ef\u89c1',
    'offenseAdmin.workspace.metric.pending': '\u5f85\u5904\u7406',
    'offenseAdmin.workspace.metric.points': '\u5f53\u524d\u6263\u5206',
    'offenseAdmin.workspace.metric.fine': '\u5f53\u524d\u7f5a\u6b3e',
    'offenseAdmin.workspace.filterEyebrow': '\u7b5b\u9009',
    'offenseAdmin.workspace.filterTitle':
        '\u641c\u7d22\u4e0e\u7f29\u5c0f\u8fdd\u7ae0\u8303\u56f4',
    'offenseAdmin.workspace.filterBody':
        '\u5207\u6362\u641c\u7d22\u6a21\u5f0f\uff0c\u5e94\u7528\u65f6\u95f4\u8303\u56f4\uff0c\u5e76\u5237\u65b0\u5f53\u524d\u8fdd\u7ae0\u6d41\u3002',
    'offenseAdmin.workspace.filterMode': '\u641c\u7d22\u6a21\u5f0f',
    'offenseAdmin.workspace.filterReset': '\u91cd\u7f6e\u7b5b\u9009',
    'offenseAdmin.workspace.filterRefresh': '\u5237\u65b0\u8bb0\u5f55',
    'offenseAdmin.workspace.listEyebrow': '\u8bb0\u5f55',
    'offenseAdmin.workspace.listTitle': '\u8fdd\u7ae0\u8bb0\u5f55',
    'offenseAdmin.workspace.listBody':
        '\u5728\u6253\u5f00\u8be6\u60c5\u6216\u5220\u9664\u8bb0\u5f55\u524d\uff0c\u5148\u67e5\u770b\u72b6\u6001\u3001\u5f52\u5c5e\u4eba\u3001\u65f6\u95f4\u3001\u6263\u5206\u548c\u5730\u70b9\u3002',
    'offenseAdmin.workspace.emptyTitle':
        '\u5f53\u524d\u89c6\u56fe\u6ca1\u6709\u8fdd\u7ae0\u8bb0\u5f55',
    'offenseAdmin.workspace.errorTitle':
        '\u8fdd\u7ae0\u8bb0\u5f55\u52a0\u8f7d\u5931\u8d25',
    'offenseAdmin.error.loadFailed':
        '\u83b7\u53d6\u8fdd\u6cd5\u4fe1\u606f\u5931\u8d25: @error',
    'offenseAdmin.error.suggestionFailed':
        '\u83b7\u53d6\u5efa\u8bae\u5931\u8d25: @error',
    'offenseAdmin.error.deleteFailed':
        '\u5220\u9664\u8fdd\u6cd5\u4fe1\u606f\u5931\u8d25: @error',
    'offenseAdmin.delete.confirmTitle': '\u786e\u8ba4\u5220\u9664',
    'offenseAdmin.delete.confirmBody':
        '\u786e\u5b9a\u8981\u5220\u9664\u6b64\u8fdd\u6cd5\u4fe1\u606f\u5417\uff1f\u6b64\u64cd\u4f5c\u4e0d\u53ef\u64a4\u9500\u3002',
    'offenseAdmin.card.type': '\u8fdd\u6cd5\u7c7b\u578b\uff1a@value',
    'offenseAdmin.card.licensePlate': '\u8f66\u724c\u53f7\uff1a@value',
    'offenseAdmin.card.driverName': '\u53f8\u673a\u59d3\u540d\uff1a@value',
    'offenseAdmin.card.status': '\u72b6\u6001\uff1a@value',
    'fine.status.paid': '\u5df2\u7f34\u7eb3',
    'fine.status.pending': '\u5f85\u7f34\u7eb3',
    'fine.error.missingLoginOrDriver':
        '\u672a\u767b\u5f55\u6216\u672a\u627e\u5230\u9a7e\u9a76\u5458\u4fe1\u606f',
    'fine.error.usernameMissing':
        '\u65e0\u6cd5\u786e\u5b9a\u5f53\u524d\u7528\u6237\u540d',
    'fine.error.initializeFailed': '\u521d\u59cb\u5316\u5931\u8d25: @error',
    'fine.error.loadFailed':
        '\u52a0\u8f7d\u7f5a\u6b3e\u4fe1\u606f\u5931\u8d25: @error',
    'fine.error.generateQrFailed':
        '\u751f\u6210\u4ed8\u6b3e\u7801\u5931\u8d25: @error',
    'fine.error.refreshFailed':
        '\u5237\u65b0\u7f5a\u6b3e\u4fe1\u606f\u5931\u8d25: @error',
    'fine.error.driverNotFoundRelogin':
        '\u672a\u627e\u5230\u9a7e\u9a76\u5458\u4fe1\u606f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'fine.detail.title': '\u7f5a\u6b3e\u8be6\u60c5',
    'fine.detail.amount': '\u7f5a\u6b3e\u91d1\u989d',
    'fine.value.amount': '@value \u5143',
    'fine.detail.payee': '\u7f34\u6b3e\u4eba',
    'fine.detail.account': '\u94f6\u884c\u8d26\u53f7',
    'fine.detail.bank': '\u94f6\u884c\u540d\u79f0',
    'fine.detail.receipt': '\u6536\u636e\u7f16\u53f7',
    'fine.detail.time': '\u7f5a\u6b3e\u65f6\u95f4',
    'fine.detail.status': '\u72b6\u6001',
    'fine.detail.outstanding': '\u5f85\u7f34\u91d1\u989d',
    'fine.detail.remarks': '\u5907\u6ce8',
    'fine.paymentHistory.title': '\u652f\u4ed8\u8bb0\u5f55',
    'fine.paymentHistory.empty': '\u6682\u65e0\u652f\u4ed8\u8bb0\u5f55',
    'fine.paymentHistory.loadFailed':
        '\u652f\u4ed8\u8bb0\u5f55\u52a0\u8f7d\u5931\u8d25\uff1a@error',
    'fine.paymentHistory.recordTitle':
        '\u652f\u4ed8\u91d1\u989d\uff1a\$@amount',
    'fine.paymentHistory.status': '\u652f\u4ed8\u72b6\u6001',
    'fine.paymentHistory.time': '\u652f\u4ed8\u65f6\u95f4',
    'fine.paymentHistory.method': '\u652f\u4ed8\u65b9\u5f0f',
    'fine.paymentHistory.channel': '\u652f\u4ed8\u6e20\u9053',
    'fine.paymentHistory.paymentNumber': '\u652f\u4ed8\u5355\u53f7',
    'fine.paymentHistory.transactionId': '\u4ea4\u6613\u6d41\u6c34\u53f7',
    'fine.paymentHistory.receiptNumber': '\u6536\u636e\u7f16\u53f7',
    'fine.paymentHistory.receiptUrl': '\u652f\u4ed8\u51ed\u8bc1\u94fe\u63a5',
    'fine.paymentHistory.payerName': '\u4ed8\u6b3e\u4eba\u59d3\u540d',
    'fine.paymentHistory.payerIdCard':
        '\u4ed8\u6b3e\u4eba\u8eab\u4efd\u8bc1\u53f7',
    'fine.paymentHistory.payerContact':
        '\u4ed8\u6b3e\u4eba\u8054\u7cfb\u65b9\u5f0f',
    'fine.paymentHistory.bankName': '\u94f6\u884c\u540d\u79f0',
    'fine.paymentHistory.bankAccount': '\u94f6\u884c\u8d26\u53f7',
    'fine.paymentHistory.refund': '\u9000\u6b3e\u4fe1\u606f',
    'fine.paymentHistory.refundValue': '\$@amount\uff0c\u65f6\u95f4\uff1a@time',
    'fine.paymentHistory.missingProofHint':
        '\u8be5\u6761\u81ea\u52a9\u652f\u4ed8\u5df2\u786e\u8ba4\uff0c\u4f46\u672a\u4e0a\u4f20\u652f\u4ed8\u51ed\u8bc1\u94fe\u63a5\uff0c\u8d22\u52a1\u9700\u4eba\u5de5\u590d\u6838\u3002',
    'fine.reviewQueue.title': '\u5f85\u590d\u6838\u652f\u4ed8',
    'fine.reviewQueue.empty':
        '\u5f53\u524d\u6ca1\u6709\u5f85\u8d22\u52a1\u590d\u6838\u7684\u652f\u4ed8\u4efb\u52a1\u3002',
    'fine.reviewQueue.loadFailed':
        '\u52a0\u8f7d\u5f85\u590d\u6838\u652f\u4ed8\u4efb\u52a1\u5931\u8d25\uff1a@error',
    'fine.reviewQueue.openFine': '\u6253\u5f00\u7f5a\u5355',
    'fine.reviewQueue.openFailed':
        '\u6253\u5f00\u5173\u8054\u7f5a\u5355\u5931\u8d25\uff1a@error',
    'fine.reviewQueue.recordSubtitle':
        '\u7f5a\u5355 #@fineId \u00b7 @status \u00b7 @channel',
    'fine.reviewQueue.selectionHint': '\u5df2\u9009 @count \u6761',
    'fine.reviewQueue.selectAll': '\u5168\u9009',
    'fine.reviewQueue.clearSelection': '\u6e05\u7a7a\u9009\u4e2d',
    'fine.reviewQueue.batchNeedProof':
        '\u6279\u91cf\u8981\u6c42\u8865\u51ed\u8bc1',
    'fine.reviewQueue.batchNeedProofSuccess':
        '\u5df2\u6279\u91cf\u6807\u8bb0 @count \u6761\u652f\u4ed8\u5f85\u590d\u6838\u4efb\u52a1\u9700\u8865\u5145\u51ed\u8bc1\u3002',
    'fine.reviewQueue.batchNeedProofFailed':
        '\u6279\u91cf\u8981\u6c42\u8865\u5145\u51ed\u8bc1\u5931\u8d25\uff1a@error',
    'fine.reviewQueue.batchApprove':
        '\u6279\u91cf\u6807\u8bb0\u5df2\u6838\u9a8c',
    'fine.reviewQueue.batchApproveSuccess':
        '\u5df2\u6279\u91cf\u6807\u8bb0 @count \u6761\u652f\u4ed8\u5f85\u590d\u6838\u4efb\u52a1\u4e3a\u5df2\u6838\u9a8c\u3002',
    'fine.reviewQueue.batchApproveFailed':
        '\u6279\u91cf\u6807\u8bb0\u5f85\u590d\u6838\u652f\u4ed8\u5931\u8d25\uff1a@error',
    'fine.reviewQueue.filter.all': '\u5168\u90e8',
    'fine.reviewQueue.filter.overdue': '\u8d85\u65f6',
    'fine.reviewQueue.filter.missingProof': '\u7f3a\u5c11\u51ed\u8bc1',
    'fine.reviewQueue.filter.needProof': '\u9700\u518d\u6b21\u8865\u8bc1',
    'fine.reviewQueue.sort.pending':
        '\u6392\u5e8f\uff1a\u6700\u65b0\u5f85\u5904\u7406',
    'fine.reviewQueue.sort.amount':
        '\u6392\u5e8f\uff1a\u91d1\u989d\u4ece\u9ad8\u5230\u4f4e',
    'fine.reviewQueue.filteredEmpty':
        '\u5f53\u524d\u7b5b\u9009\u6761\u4ef6\u4e0b\u6682\u65e0\u5f85\u590d\u6838\u652f\u4ed8\u4efb\u52a1\u3002',
    'fine.reviewQueue.overdueBadge': '\u8d85\u65f6',
    'fine.reviewQueue.pendingSince': '\u5df2\u5f85\u5904\u7406 @time',
    'fine.reviewQueue.pendingHours': '@hours \u5c0f\u65f6',
    'fine.reviewQueue.pendingDays': '@days \u5929',
    'fine.paymentReview.latest': '\u6700\u65b0\u8d22\u52a1\u590d\u6838',
    'fine.paymentReview.result': '\u590d\u6838\u7ed3\u679c',
    'fine.paymentReview.time': '\u590d\u6838\u65f6\u95f4',
    'fine.paymentReview.reviewer': '\u590d\u6838\u4eba',
    'fine.paymentReview.opinion': '\u590d\u6838\u8bf4\u660e',
    'fine.paymentReview.result.approved': '\u5df2\u6838\u9a8c',
    'fine.paymentReview.result.needProof': '\u9700\u8865\u5145\u51ed\u8bc1',
    'fine.paymentReview.action.approve': '\u6807\u8bb0\u5df2\u6838\u9a8c',
    'fine.paymentReview.action.needProof': '\u8981\u6c42\u8865\u51ed\u8bc1',
    'fine.paymentReview.dialog.needProofTitle':
        '\u8981\u6c42\u8865\u5145\u51ed\u8bc1',
    'fine.paymentReview.dialog.needProofHint':
        '\u8bf7\u544a\u77e5\u7f34\u6b3e\u4eba\u8fd8\u9700\u8865\u4e0a\u54ea\u4e9b\u51ed\u8bc1\uff0c\u4f9b\u8d22\u52a1\u590d\u6838\u3002',
    'fine.paymentReview.validation.opinionRequired':
        '\u63d0\u4ea4\u524d\u8bf7\u5148\u586b\u5199\u8865\u5145\u51ed\u8bc1\u8981\u6c42\u3002',
    'fine.paymentReview.success.approved':
        '\u5df2\u6807\u8bb0\u4e3a\u8d22\u52a1\u5df2\u6838\u9a8c\u3002',
    'fine.paymentReview.success.needProof':
        '\u5df2\u6807\u8bb0\u4e3a\u9700\u8865\u5145\u51ed\u8bc1\u3002',
    'fine.paymentReview.failed':
        '\u63d0\u4ea4\u8d22\u52a1\u590d\u6838\u5931\u8d25\uff1a@error',
    'fine.payment.action.uploadProof': '\u8865\u4f20\u652f\u4ed8\u51ed\u8bc1',
    'fine.payment.proofDialog.title': '\u4e0a\u4f20\u652f\u4ed8\u51ed\u8bc1',
    'fine.payment.proofDialog.hint':
        '\u8bf7\u7c98\u8d34\u8fd9\u7b14\u652f\u4ed8\u7684\u6700\u65b0\u6536\u636e\u6216\u51ed\u8bc1\u94fe\u63a5\uff0c\u4ee5\u4fbf\u8d22\u52a1\u7ee7\u7eed\u590d\u6838\u3002',
    'fine.payment.proof.validation.receiptUrlRequired':
        '\u63d0\u4ea4\u524d\u8bf7\u5148\u586b\u5199\u652f\u4ed8\u51ed\u8bc1\u94fe\u63a5\u3002',
    'fine.payment.proof.success':
        '\u652f\u4ed8\u51ed\u8bc1\u5df2\u66f4\u65b0\u3002',
    'fine.payment.proof.failed':
        '\u66f4\u65b0\u652f\u4ed8\u51ed\u8bc1\u5931\u8d25\uff1a@error',
    'fine.qr.alipayHint':
        '\u8bf7\u4f7f\u7528\u652f\u4ed8\u5b9d\u626b\u63cf\u4e0b\u65b9\u4e8c\u7ef4\u7801\u5b8c\u6210\u652f\u4ed8',
    'fine.action.close': '\u5173\u95ed',
    'fine.action.payNow': '\u7acb\u5373\u7f34\u8d39 (\$@amount)',
    'fine.payment.unavailable':
        '\u5f53\u524d\u7f5a\u6b3e\u6682\u65f6\u65e0\u6cd5\u652f\u4ed8',
    'fine.payment.orderCreated':
        '\u5df2\u751f\u6210\u5f85\u786e\u8ba4\u652f\u4ed8\u8ba2\u5355\uff1a\$@amount\uff0c\u5b8c\u6210\u4ed8\u6b3e\u540e\u8bf7\u518d\u786e\u8ba4',
    'fine.payment.confirmAction': '\u786e\u8ba4\u5df2\u652f\u4ed8',
    'fine.payment.confirmSuccess':
        '\u652f\u4ed8\u5df2\u786e\u8ba4\uff1a\$@amount',
    'fine.payment.confirmFailed':
        '\u786e\u8ba4\u652f\u4ed8\u5931\u8d25\uff1a@error',
    'fine.payment.confirmDialog.title': '\u786e\u8ba4\u652f\u4ed8',
    'fine.payment.confirmDialog.hint':
        '\u8bf7\u586b\u5199\u672c\u6b21\u4ed8\u6b3e\u7684\u771f\u5b9e\u4ea4\u6613\u6d41\u6c34\u53f7\uff0c\u4e5f\u53ef\u4ee5\u8865\u5145\u652f\u4ed8\u51ed\u8bc1\u94fe\u63a5\u4f9b\u540e\u7eed\u6838\u5bf9',
    'fine.payment.form.transactionId': '\u4ea4\u6613\u6d41\u6c34\u53f7 *',
    'fine.payment.form.receiptUrl':
        '\u652f\u4ed8\u51ed\u8bc1\u94fe\u63a5\uff08\u53ef\u9009\uff09',
    'fine.payment.validation.transactionIdRequired':
        '\u786e\u8ba4\u652f\u4ed8\u524d\uff0c\u8bf7\u5148\u586b\u5199\u4ea4\u6613\u6d41\u6c34\u53f7',
    'fine.payment.pendingHint':
        '\u8be5\u652f\u4ed8\u8ba2\u5355\u6b63\u5728\u7b49\u5f85\u786e\u8ba4\uff0c\u8bf7\u5148\u5b8c\u6210\u4ed8\u6b3e\uff0c\u518d\u5728\u6b64\u786e\u8ba4',
    'fine.payment.expiredHint':
        '\u8be5\u5f85\u786e\u8ba4\u652f\u4ed8\u8ba2\u5355\u5df2\u5931\u6548\uff0c\u5982\u4ecd\u9700\u7f34\u8d39\uff0c\u53ef\u91cd\u65b0\u521b\u5efa',
    'fine.payment.pendingExistsInline':
        '\u8be5\u7f5a\u6b3e\u5df2\u6709\u4e00\u7b14\u5f85\u786e\u8ba4\u7684\u652f\u4ed8\u8ba2\u5355\uff0c\u8bf7\u5148\u5b8c\u6210\u786e\u8ba4\u518d\u521b\u5efa\u65b0\u8ba2\u5355',
    'fine.payment.success':
        '\u652f\u4ed8\u8bb0\u5f55\u5df2\u751f\u6210: \$@amount',
    'fine.payment.failed':
        '\u751f\u6210\u652f\u4ed8\u8bb0\u5f55\u5931\u8d25: @error',
    'fine.page.title': '\u4ea4\u901a\u8fdd\u6cd5\u7f5a\u6b3e\u8bb0\u5f55',
    'fine.action.refresh': '\u5237\u65b0\u7f5a\u6b3e\u8bb0\u5f55',
    'fine.empty.byDriver':
        '\u6682\u65e0\u4e0e\u9a7e\u9a76\u5458 @driver \u5339\u914d\u7684\u7f5a\u6b3e\u8bb0\u5f55',
    'fine.card.amount': '\u7f5a\u6b3e\u91d1\u989d: \$@amount',
    'fine.card.summary':
        '\u7f34\u6b3e\u4eba: @payee\n\u65f6\u95f4: @time\n\u72b6\u6001: @status',
    'fineAdmin.page.title': '\u7f5a\u6b3e\u7ba1\u7406',
    'fineAdmin.action.add': '\u6dfb\u52a0\u7f5a\u6b3e\u4fe1\u606f',
    'fineAdmin.action.refresh': '\u5237\u65b0\u5217\u8868',
    'fineAdmin.action.retry': '\u91cd\u8bd5',
    'fineAdmin.action.restoreCache': '\u6062\u590d\u7f13\u5b58\u6570\u636e',
    'fineAdmin.action.relogin': '\u91cd\u65b0\u767b\u5f55',
    'fineAdmin.action.edit': '\u7f16\u8f91\u7f5a\u6b3e',
    'fineAdmin.action.delete': '\u5220\u9664\u7f5a\u6b3e',
    'fineAdmin.search.payee': '\u641c\u7d22\u7f34\u6b3e\u4eba',
    'fineAdmin.search.timeRangeSelected':
        '\u641c\u7d22\u65f6\u95f4\u8303\u56f4\uff08\u5df2\u9009\u62e9\uff09',
    'fineAdmin.filter.byPayee': '\u6309\u7f34\u6b3e\u4eba',
    'fineAdmin.filter.byTimeRange': '\u6309\u65f6\u95f4\u8303\u56f4',
    'fineAdmin.filter.dateRangeLabel':
        '\u7f5a\u6b3e\u65e5\u671f\u8303\u56f4\uff1a@start \u81f3 @end',
    'fineAdmin.filter.selectDateRange':
        '\u9009\u62e9\u7f5a\u6b3e\u65e5\u671f\u8303\u56f4',
    'fineAdmin.filter.tooltip':
        '\u6309\u7f5a\u6b3e\u65e5\u671f\u8303\u56f4\u641c\u7d22',
    'fineAdmin.filter.startDate': '\u5f00\u59cb\u65e5\u671f',
    'fineAdmin.filter.endDate': '\u7ed3\u675f\u65e5\u671f',
    'fineAdmin.filter.clearDateRange': '\u6e05\u9664\u65e5\u671f\u8303\u56f4',
    'fineAdmin.error.unauthorized':
        '\u672a\u6388\u6743\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'fineAdmin.error.expired':
        '\u767b\u5f55\u5df2\u8fc7\u671f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'fineAdmin.error.refreshedExpired':
        '\u65b0\u767b\u5f55\u4fe1\u606f\u5df2\u8fc7\u671f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'fineAdmin.error.invalidLogin':
        '\u65e0\u6548\u7684\u767b\u5f55\u4fe1\u606f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'fineAdmin.error.adminOnly':
        '\u6743\u9650\u4e0d\u8db3\uff1a\u4ec5\u7ba1\u7406\u5458\u53ef\u8bbf\u95ee\u6b64\u9875\u9762',
    'fineAdmin.error.initFailed': '\u521d\u59cb\u5316\u5931\u8d25: @error',
    'fineAdmin.error.httpStatus':
        '\u8bf7\u6c42\u5931\u8d25\uff08HTTP @statusCode\uff09\u3002',
    'fineAdmin.error.roleCheckFailed':
        '\u9a8c\u8bc1\u89d2\u8272\u5931\u8d25: @error',
    'fineAdmin.error.notFound': '\u672a\u627e\u5230\u7f5a\u6b3e\u8bb0\u5f55',
    'fineAdmin.error.filteredEmpty':
        '\u672a\u627e\u5230\u7b26\u5408\u6761\u4ef6\u7684\u7f5a\u6b3e\u4fe1\u606f',
    'fineAdmin.empty.default':
        '\u5f53\u524d\u6ca1\u6709\u7f5a\u6b3e\u8bb0\u5f55',
    'fineAdmin.error.loadFailed':
        '\u83b7\u53d6\u7f5a\u6b3e\u4fe1\u606f\u5931\u8d25: @error',
    'fineAdmin.error.loadLatestFallback':
        '\u83b7\u53d6\u6700\u65b0\u7f5a\u6b3e\u5931\u8d25\uff0c\u5df2\u663e\u793a\u7f13\u5b58\u6570\u636e',
    'fineAdmin.error.suggestionFailed':
        '\u83b7\u53d6\u5efa\u8bae\u5931\u8d25: @error',
    'fineAdmin.success.refreshed': '\u7f5a\u6b3e\u5217\u8868\u5df2\u5237\u65b0',
    'fineAdmin.delete.confirmTitle': '\u786e\u8ba4\u5220\u9664',
    'fineAdmin.delete.confirmBody':
        '\u786e\u5b9a\u8981\u5220\u9664\u6b64\u7f5a\u6b3e\u4fe1\u606f\u5417\uff1f\u6b64\u64cd\u4f5c\u4e0d\u53ef\u64a4\u9500\u3002',
    'fineAdmin.success.deleted': '\u5220\u9664\u7f5a\u6b3e\u6210\u529f',
    'fineAdmin.error.deleteFailed':
        '\u5220\u9664\u7f5a\u6b3e\u5931\u8d25: @error',
    'fineAdmin.card.amount': '\u91d1\u989d\uff1a@amount \u5143',
    'fineAdmin.card.payee': '\u7f34\u6b3e\u4eba\uff1a@value',
    'fineAdmin.card.time': '\u65f6\u95f4\uff1a@value',
    'fineAdmin.card.status': '\u72b6\u6001\uff1a@value',
    'fineAdmin.form.addTitle': '\u6dfb\u52a0\u65b0\u7f5a\u6b3e',
    'fineAdmin.form.editTitle': '\u7f16\u8f91\u7f5a\u6b3e',
    'fineAdmin.form.plateNumber': '\u8f66\u724c\u53f7',
    'fineAdmin.form.amount': '\u7f5a\u6b3e\u91d1\u989d',
    'fineAdmin.form.payee': '\u7f34\u6b3e\u4eba',
    'fineAdmin.form.accountNumber': '\u94f6\u884c\u8d26\u53f7',
    'fineAdmin.form.bank': '\u94f6\u884c\u540d\u79f0',
    'fineAdmin.form.receiptNumber': '\u6536\u636e\u7f16\u53f7',
    'fineAdmin.form.remarks': '\u5907\u6ce8',
    'fineAdmin.form.fineDate': '\u7f5a\u6b3e\u65e5\u671f',
    'fineAdmin.form.plateHelper':
        '\u8bf7\u8f93\u5165\u6709\u6548\u8f66\u724c\u53f7\uff0c\u4f8b\u5982\uff1a\u7ca4A12345',
    'fineAdmin.form.accountHelper':
        '\u5982\u679c\u6709\u94f6\u884c\u8d26\u53f7\uff0c\u53ef\u5728\u6b64\u586b\u5199\u3002',
    'fineAdmin.validation.required': '@field\u4e0d\u80fd\u4e3a\u7a7a',
    'fineAdmin.validation.plateTooLong':
        '\u8f66\u724c\u53f7\u4e0d\u80fd\u8d85\u8fc7 20 \u4e2a\u5b57\u7b26',
    'fineAdmin.validation.plateInvalid':
        '\u8bf7\u8f93\u5165\u6709\u6548\u8f66\u724c\u53f7\uff0c\u4f8b\u5982\uff1a\u7ca4A12345',
    'fineAdmin.validation.payeeTooLong':
        '\u7f34\u6b3e\u4eba\u59d3\u540d\u4e0d\u80fd\u8d85\u8fc7 100 \u4e2a\u5b57\u7b26',
    'fineAdmin.validation.amountNumber':
        '\u7f5a\u6b3e\u91d1\u989d\u5fc5\u987b\u662f\u6709\u6548\u6570\u5b57',
    'fineAdmin.validation.amountNegative':
        '\u7f5a\u6b3e\u91d1\u989d\u4e0d\u80fd\u4e3a\u8d1f\u6570',
    'fineAdmin.validation.amountTooLarge':
        '\u7f5a\u6b3e\u91d1\u989d\u4e0d\u80fd\u8d85\u8fc7 99999999.99',
    'fineAdmin.validation.amountPrecision':
        '\u7f5a\u6b3e\u91d1\u989d\u6700\u591a\u4fdd\u7559 2 \u4f4d\u5c0f\u6570',
    'fineAdmin.validation.accountTooLong':
        '\u94f6\u884c\u8d26\u53f7\u4e0d\u80fd\u8d85\u8fc7 50 \u4e2a\u5b57\u7b26',
    'fineAdmin.validation.bankTooLong':
        '\u94f6\u884c\u540d\u79f0\u4e0d\u80fd\u8d85\u8fc7 100 \u4e2a\u5b57\u7b26',
    'fineAdmin.validation.receiptTooLong':
        '\u6536\u636e\u7f16\u53f7\u4e0d\u80fd\u8d85\u8fc7 50 \u4e2a\u5b57\u7b26',
    'fineAdmin.validation.remarksTooLong':
        '\u5907\u6ce8\u4e0d\u80fd\u8d85\u8fc7 255 \u4e2a\u5b57\u7b26',
    'fineAdmin.validation.dateInvalid':
        '\u65e0\u6548\u7684\u65e5\u671f\u683c\u5f0f',
    'fineAdmin.validation.dateFuture':
        '\u7f5a\u6b3e\u65e5\u671f\u4e0d\u80fd\u665a\u4e8e\u5f53\u524d\u65e5\u671f',
    'fineAdmin.error.jwtMissingRelogin':
        '\u672a\u627e\u5230 JWT\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'fineAdmin.error.fetchPlateSuggestionsFailed':
        '\u83b7\u53d6\u8f66\u724c\u53f7\u5efa\u8bae\u5931\u8d25: @error',
    'fineAdmin.error.fetchPayeeSuggestionsFailed':
        '\u83b7\u53d6\u7f34\u6b3e\u4eba\u5efa\u8bae\u5931\u8d25: @error',
    'fineAdmin.error.offenseNotFoundByPlate':
        '\u672a\u627e\u5230\u4e0e\u6b64\u8f66\u724c\u76f8\u5173\u7684\u8fdd\u6cd5\u8bb0\u5f55',
    'fineAdmin.error.fetchOffenseFailed':
        '\u83b7\u53d6\u8fdd\u6cd5\u4fe1\u606f\u5931\u8d25: @error',
    'fineAdmin.error.invalidOffense':
        '\u65e0\u6548\u7684\u8fdd\u6cd5\u8bb0\u5f55',
    'fineAdmin.error.loadPayeeFailed':
        '\u52a0\u8f7d\u7f34\u6b3e\u4eba\u4fe1\u606f\u5931\u8d25: @error',
    'fineAdmin.error.selectValidOffense':
        '\u8bf7\u5148\u9009\u62e9\u6709\u6548\u7684\u8fdd\u6cd5\u8bb0\u5f55',
    'fineAdmin.success.updated': '\u66f4\u65b0\u7f5a\u6b3e\u6210\u529f',
    'fineAdmin.success.created': '\u521b\u5efa\u7f5a\u6b3e\u6210\u529f',
    'fineAdmin.error.updateFailed':
        '\u66f4\u65b0\u7f5a\u6b3e\u5931\u8d25: @error',
    'fineAdmin.error.createFailed':
        '\u521b\u5efa\u7f5a\u6b3e\u5931\u8d25: @error',
    'fineAdmin.detail.title': '\u7f5a\u6b3e\u8be6\u60c5',
    'fineAdmin.detail.editTooltip': '\u7f16\u8f91\u7f5a\u6b3e',
    'fineAdmin.detail.approveTooltip': '\u6279\u51c6\u7f5a\u6b3e',
    'fineAdmin.detail.rejectTooltip': '\u62d2\u7edd\u7f5a\u6b3e',
    'fineAdmin.detail.deleteTooltip': '\u5220\u9664\u7f5a\u6b3e',
    'fineAdmin.success.statusUpdated': '\u7f5a\u6b3e\u8bb0\u5f55\u5df2@status',
    'fineAdmin.error.statusUpdateFailed':
        '\u66f4\u65b0\u7f5a\u6b3e\u72b6\u6001\u5931\u8d25: @error',
    'fineAdmin.error.permissionLoadFailed':
        '\u52a0\u8f7d\u6743\u9650\u5931\u8d25: @error',
    'appeal.status.pending': '\u5f85\u5904\u7406',
    'appeal.status.approved': '\u5df2\u901a\u8fc7',
    'appeal.status.rejected': '\u5df2\u62d2\u7edd',
    'appeal.error.notLoggedIn':
        '\u672a\u767b\u5f55\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'appeal.error.driverNameMissingRelogin':
        '\u65e0\u6cd5\u83b7\u53d6\u9a7e\u9a76\u5458\u59d3\u540d\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'appeal.error.userOnly':
        '\u6743\u9650\u4e0d\u8db3\uff1a\u4ec5\u7528\u6237\u53ef\u8bbf\u95ee\u6b64\u9875\u9762',
    'appeal.error.loadFailed': '\u52a0\u8f7d\u5931\u8d25: @error',
    'appeal.error.invalidJwt': '\u65e0\u6548\u7684 JWT \u683c\u5f0f',
    'appeal.error.currentUserMissing':
        '\u65e0\u6cd5\u786e\u5b9a\u5f53\u524d\u7528\u6237',
    'appeal.error.driverNameNotFound':
        '\u672a\u627e\u5230\u9a7e\u9a76\u5458\u59d3\u540d',
    'appeal.error.checkOffenseFailed':
        '\u65e0\u6cd5\u68c0\u67e5\u8fdd\u6cd5\u4fe1\u606f: @error',
    'appeal.error.usernameMissing': '\u672a\u627e\u5230\u7528\u6237\u540d',
    'appeal.empty': '\u6682\u65e0\u7533\u8bc9\u8bb0\u5f55',
    'appeal.empty.filtered':
        '\u672a\u627e\u5230\u7b26\u5408\u6761\u4ef6\u7684\u7533\u8bc9\u8bb0\u5f55',
    'appeal.error.loadRecordsFailed':
        '\u52a0\u8f7d\u7533\u8bc9\u8bb0\u5f55\u5931\u8d25: @error',
    'appeal.success.submitted': '\u7533\u8bc9\u63d0\u4ea4\u6210\u529f',
    'appeal.error.submitFailed': '\u7533\u8bc9\u63d0\u4ea4\u5931\u8d25: @error',
    'appeal.error.noOffenseToSubmit':
        '\u60a8\u5f53\u524d\u6ca1\u6709\u8fdd\u6cd5\u8bb0\u5f55\uff0c\u65e0\u6cd5\u63d0\u4ea4\u7533\u8bc9',
    'appeal.error.completeProfileBeforeSubmit':
        '\u63d0\u4ea4\u7533\u8bc9\u524d\uff0c\u8bf7\u5148\u5728\u4e2a\u4eba\u8d44\u6599\u4e2d\u8865\u5168\u59d3\u540d\u3001\u8eab\u4efd\u8bc1\u53f7\u7801\u548c\u8054\u7cfb\u7535\u8bdd\u3002',
    'appeal.dialog.submitTitle': '\u63d0\u4ea4\u7533\u8bc9',
    'appeal.form.offense': '\u9009\u62e9\u8fdd\u6cd5\u8bb0\u5f55 *',
    'appeal.form.offenseOption': 'ID: @id - @type',
    'appeal.value.noDescription': '\u65e0\u63cf\u8ff0',
    'appeal.validation.offenseRequired':
        '\u8bf7\u9009\u62e9\u4e00\u6761\u8fdd\u6cd5\u8bb0\u5f55',
    'appeal.form.appellantName': '\u7533\u8bc9\u4eba\u59d3\u540d *',
    'appeal.form.idCard': '\u8eab\u4efd\u8bc1\u53f7\u7801 *',
    'appeal.form.contact': '\u8054\u7cfb\u7535\u8bdd *',
    'appeal.form.identityFromProfile':
        '\u8fd9\u4e9b\u4fe1\u606f\u5c06\u76f4\u63a5\u4f7f\u7528\u4f60\u5f53\u524d\u7684\u4e2a\u4eba\u6863\u6848\u3002',
    'appeal.form.reason': '\u7533\u8bc9\u539f\u56e0 *',
    'appeal.form.initialEvidenceDescription':
        '\u8bc1\u636e\u8bf4\u660e\uff08\u53ef\u9009\uff09',
    'appeal.form.initialEvidenceUrls':
        '\u8bc1\u636e\u94fe\u63a5\uff08\u53ef\u9009\uff09',
    'appeal.validation.required': '\u8bf7\u586b\u5199@field',
    'appeal.validation.reasonTooLong':
        '\u7533\u8bc9\u539f\u56e0\u4e0d\u80fd\u8d85\u8fc7500\u4e2a\u5b57\u7b26',
    'appeal.validation.requiredFields':
        '\u8bf7\u586b\u5199\u6240\u6709\u5fc5\u586b\u5b57\u6bb5',
    'appeal.search.hint': '\u641c\u7d22\u7533\u8bc9\u539f\u56e0',
    'appeal.filter.rangeLabel': '\u65e5\u671f\u8303\u56f4: @start \u81f3 @end',
    'appeal.filter.select': '\u9009\u62e9\u65e5\u671f\u8303\u56f4',
    'appeal.filter.tooltip': '\u6309\u65e5\u671f\u8303\u56f4\u641c\u7d22',
    'appeal.filter.startDate': '\u5f00\u59cb\u65e5\u671f',
    'appeal.filter.endDate': '\u7ed3\u675f\u65e5\u671f',
    'appeal.filter.clear': '\u6e05\u9664\u65e5\u671f\u8303\u56f4',
    'appeal.page.title': '\u7528\u6237\u7533\u8bc9\u7ba1\u7406',
    'appeal.action.submit': '\u63d0\u4ea4\u7533\u8bc9',
    'appeal.action.supplementComplete': '\u63d0\u4ea4\u8865\u5145\u6750\u6599',
    'appeal.action.resubmit': '\u91cd\u65b0\u63d0\u4ea4\u7533\u8bc9',
    'appeal.action.withdraw': '\u64a4\u56de\u7533\u8bc9',
    'appeal.empty.byAppellant':
        '\u6682\u65e0\u4e0e\u7533\u8bc9\u4eba @name \u5339\u914d\u7684\u7533\u8bc9\u8bb0\u5f55',
    'appeal.card.title': '\u7533\u8bc9\u4eba: @name (ID: @id)',
    'appeal.card.summary':
        '\u539f\u56e0: @reason\n\u72b6\u6001: @status\n\u65f6\u95f4: @time',
    'appeal.progress.submitTitle': '\u63d0\u4ea4\u53cd\u9988',
    'appeal.progress.title': '\u53cd\u9988\u5185\u5bb9\u6807\u9898',
    'appeal.progress.detailsOptional': '\u8be6\u60c5\uff08\u53ef\u9009\uff09',
    'appeal.progress.titleRequired': '\u6807\u9898\u4e0d\u80fd\u4e3a\u7a7a',
    'appeal.detail.title': '\u7533\u8bc9\u8be6\u60c5',
    'appeal.progress.submitAction': '\u63d0\u4ea4\u53cd\u9988',
    'appeal.detail.appealId': '\u7533\u8bc9 ID',
    'appeal.detail.offenseId': '\u8fdd\u6cd5 ID',
    'appeal.detail.appellant': '\u4e0a\u8bc9\u4eba',
    'appeal.detail.idCard': '\u8eab\u4efd\u8bc1\u53f7\u7801',
    'appeal.detail.contact': '\u8054\u7cfb\u7535\u8bdd',
    'appeal.detail.reason': '\u7533\u8bc9\u539f\u56e0',
    'appeal.detail.evidenceDescription': '\u8bc1\u636e\u8bf4\u660e',
    'appeal.detail.evidenceUrls': '\u8bc1\u636e\u94fe\u63a5',
    'appeal.detail.time': '\u7533\u8bc9\u65f6\u95f4',
    'appeal.detail.acceptanceStatus': '\u53d7\u7406\u72b6\u6001',
    'appeal.detail.status': '\u5904\u7406\u72b6\u6001',
    'appeal.detail.result': '\u5904\u7406\u7ed3\u679c',
    'appeal.detail.reviewHistory': '\u590d\u6838\u5386\u53f2',
    'appeal.detail.reviewEmpty': '\u6682\u65e0\u590d\u6838\u8bb0\u5f55',
    'appeal.detail.reviewCount': '\u5171 @count \u6761\u590d\u6838\u8bb0\u5f55',
    'appeal.detail.reviewReviewer': '\u590d\u6838\u4eba',
    'appeal.detail.reviewReviewerDept': '\u590d\u6838\u90e8\u95e8',
    'appeal.detail.reviewLevel': '\u590d\u6838\u7ea7\u522b',
    'appeal.detail.reviewResult': '\u590d\u6838\u7ed3\u679c',
    'appeal.detail.reviewOpinion': '\u590d\u6838\u610f\u89c1',
    'appeal.detail.reviewTime': '\u590d\u6838\u65f6\u95f4',
    'appeal.form.supplementTitle': '\u66f4\u65b0\u7533\u8bc9\u6750\u6599',
    'appeal.form.supplementHint':
        '\u5728\u9001\u56de\u53d7\u7406\u524d\uff0c\u53ef\u5148\u8865\u5145\u6216\u4fee\u6539\u7533\u8bc9\u539f\u56e0\u3001\u8bc1\u636e\u8bf4\u660e\u548c\u94fe\u63a5\u3002',
    'appeal.form.evidenceDescription': '\u8865\u5145\u8bc1\u636e\u8bf4\u660e',
    'appeal.form.evidenceUrls': '\u8865\u5145\u8bc1\u636e\u94fe\u63a5',
    'appeal.form.evidenceUrlsHint':
        '\u53ef\u7c98\u8d34\u4e00\u4e2a\u6216\u591a\u4e2a\u6587\u4ef6\u94fe\u63a5\uff0c\u4e5f\u53ef\u76f4\u63a5\u7c98\u8d34 JSON \u6570\u7ec4\u5b57\u7b26\u4e32',
    'appeal.progress.related': '\u76f8\u5173\u53cd\u9988',
    'appeal.progress.empty': '\u6682\u65e0\u76f8\u5173\u53cd\u9988\u8bb0\u5f55',
    'appeal.progress.summary':
        '\u72b6\u6001: @status\n\u63d0\u4ea4\u65f6\u95f4: @time',
    'appeal.note.readonly':
        '\u6ce8\u610f\uff1a\u7528\u6237\u65e0\u6cd5\u4fee\u6539\u6216\u5220\u9664\u7533\u8bc9\uff0c\u8bf7\u8054\u7cfb\u7ba1\u7406\u5458\u5904\u7406\u3002',
    'appeal.note.awaitingUserAction':
        '\u5f53\u524d\u7533\u8bc9\u9700\u8981\u4f60\u5148\u5b8c\u6210\u540e\u7eed\u64cd\u4f5c\uff0c\u624d\u80fd\u7ee7\u7eed\u53d7\u7406\u3002',
    'appeal.note.withdrawable':
        '\u5728\u5ba1\u6838\u7ed3\u675f\u524d\uff0c\u4f60\u53ef\u4ee5\u4e3b\u52a8\u64a4\u56de\u8fd9\u6761\u7533\u8bc9\u3002',
    'appeal.success.supplementCompleted':
        '\u8865\u5145\u6750\u6599\u5df2\u63d0\u4ea4\uff0c\u7533\u8bc9\u5df2\u9001\u56de\u5f85\u53d7\u7406',
    'appeal.success.resubmitted':
        '\u7533\u8bc9\u5df2\u91cd\u65b0\u63d0\u4ea4\u5f85\u53d7\u7406',
    'appeal.success.withdrawn': '\u7533\u8bc9\u5df2\u6210\u529f\u64a4\u56de',
    'appealAdmin.page.title': '\u7533\u8bc9\u5ba1\u6279\u7ba1\u7406',
    'appealAdmin.error.unauthorizedMissing':
        '\u672a\u6388\u6743\uff1a\u672a\u627e\u5230\u767b\u5f55\u4fe1\u606f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'appealAdmin.error.unauthorized':
        '\u672a\u6388\u6743\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'appealAdmin.error.expired':
        '\u767b\u5f55\u5df2\u8fc7\u671f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'appealAdmin.error.refreshedExpired':
        '\u65b0\u767b\u5f55\u4fe1\u606f\u5df2\u8fc7\u671f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'appealAdmin.error.invalidLogin':
        '\u65e0\u6548\u7684\u767b\u5f55\u4fe1\u606f\uff1a@error\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'appealAdmin.error.adminOnly':
        '\u6743\u9650\u4e0d\u8db3\uff1a\u4ec5\u7ba1\u7406\u5458\u53ef\u8bbf\u95ee\u6b64\u9875\u9762',
    'appealAdmin.error.initFailed': '\u521d\u59cb\u5316\u5931\u8d25: @error',
    'appealAdmin.error.roleCheckFailed':
        '\u9a8c\u8bc1\u89d2\u8272\u5931\u8d25: @error',
    'appealAdmin.error.jwtAdminOnly':
        '\u6743\u9650\u4e0d\u8db3\uff1aJWT \u89d2\u8272\u4e3a @roles\uff0c\u975e\u7ba1\u7406\u5458',
    'appealAdmin.error.jwtRoleCheckFailed':
        '\u4ece JWT \u9a8c\u8bc1\u89d2\u8272\u5931\u8d25: @error',
    'appealAdmin.error.loadFailed':
        '\u52a0\u8f7d\u7533\u8bc9\u4fe1\u606f\u5931\u8d25: @error',
    'appealAdmin.error.request': '\u8bf7\u6c42\u9519\u8bef: @message',
    'appealAdmin.error.forbidden': '\u65e0\u6743\u9650: @message',
    'appealAdmin.error.notFound': '\u672a\u627e\u5230: @message',
    'appealAdmin.error.duplicateRequest': '\u91cd\u590d\u8bf7\u6c42: @message',
    'appealAdmin.error.server': '\u670d\u52a1\u5668\u9519\u8bef: @message',
    'appealAdmin.error.operationFailed': '\u64cd\u4f5c\u5931\u8d25: @error',
    'appealAdmin.error.invalidAppealId': '\u7533\u8bc9 ID \u65e0\u6548',
    'appealAdmin.search.appealReason': '\u641c\u7d22\u7533\u8bc9\u539f\u56e0',
    'appealAdmin.search.appellantName':
        '\u641c\u7d22\u7533\u8bc9\u4eba\u59d3\u540d',
    'appealAdmin.search.processStatus': '\u641c\u7d22\u5904\u7406\u72b6\u6001',
    'appealAdmin.search.timeRangeSelected':
        '\u641c\u7d22\u65f6\u95f4\u8303\u56f4\uff08\u5df2\u9009\u62e9\uff09',
    'appealAdmin.view.appeals': '\u7533\u8bc9\u8bb0\u5f55',
    'appealAdmin.view.reviews': '\u590d\u6838\u8bb0\u5f55',
    'appealAdmin.review.search.reviewer': '\u641c\u7d22\u590d\u6838\u4eba',
    'appealAdmin.review.search.reviewerDept':
        '\u641c\u7d22\u590d\u6838\u4eba\u90e8\u95e8',
    'appealAdmin.review.search.timeRangeSelected':
        '\u641c\u7d22\u590d\u6838\u65f6\u95f4\u8303\u56f4\uff08\u5df2\u9009\u62e9\uff09',
    'appealAdmin.filter.byAppealReason': '\u6309\u7533\u8bc9\u539f\u56e0',
    'appealAdmin.filter.byAppellantName':
        '\u6309\u7533\u8bc9\u4eba\u59d3\u540d',
    'appealAdmin.filter.byProcessStatus': '\u6309\u5904\u7406\u72b6\u6001',
    'appealAdmin.filter.byTimeRange': '\u6309\u65f6\u95f4\u8303\u56f4',
    'appealAdmin.review.filter.byReviewer': '\u6309\u590d\u6838\u4eba',
    'appealAdmin.review.filter.byReviewerDept':
        '\u6309\u590d\u6838\u4eba\u90e8\u95e8',
    'appealAdmin.review.filter.byTimeRange':
        '\u6309\u590d\u6838\u65f6\u95f4\u8303\u56f4',
    'appealAdmin.card.reason': '\u539f\u56e0: @value',
    'appealAdmin.card.status': '\u72b6\u6001: @value',
    'appealAdmin.card.time': '\u65f6\u95f4: @value',
    'appealAdmin.review.empty':
        '\u6682\u65e0\u7533\u8bc9\u590d\u6838\u8bb0\u5f55',
    'appealAdmin.review.empty.filtered':
        '\u5f53\u524d\u7b5b\u9009\u6761\u4ef6\u4e0b\u65e0\u7533\u8bc9\u590d\u6838\u8bb0\u5f55',
    'appealAdmin.review.loadFailed':
        '\u52a0\u8f7d\u7533\u8bc9\u590d\u6838\u8bb0\u5f55\u5931\u8d25: @error',
    'appealAdmin.review.card.title':
        '\u7533\u8bc9 #@appealId \u00b7 @level\u590d\u6838',
    'appealAdmin.review.card.result': '\u7ed3\u679c: @value',
    'appealAdmin.review.card.reviewer': '\u590d\u6838\u4eba: @value',
    'appealAdmin.review.card.reviewerDept': '\u90e8\u95e8: @value',
    'appealAdmin.review.card.time': '\u590d\u6838\u65f6\u95f4: @value',
    'appealAdmin.review.card.opinion': '\u610f\u89c1: @value',
    'appealAdmin.review.level.primary': '\u521d\u5ba1',
    'appealAdmin.review.level.secondary': '\u590d\u5ba1',
    'appealAdmin.review.level.final': '\u7ec8\u5ba1',
    'appealAdmin.review.result.approved': '\u901a\u8fc7',
    'appealAdmin.review.result.rejected': '\u9a73\u56de',
    'appealAdmin.review.result.needResubmit': '\u9700\u91cd\u65b0\u63d0\u4ea4',
    'appealAdmin.review.result.transfer': '\u8f6c\u529e',
    'appealAdmin.review.workbench.title': '\u590d\u6838\u5de5\u4f5c\u53f0',
    'appealAdmin.review.workbench.subtitle':
        '\u5728\u4e00\u4e2a\u9762\u677f\u4e2d\u7edf\u4e00\u67e5\u770b\u590d\u6838\u8d1f\u8f7d\u3001\u5f85\u529e\u961f\u5217\u548c\u5f53\u65e5\u4ea7\u51fa',
    'appealAdmin.review.workbench.loadFailed':
        '\u52a0\u8f7d\u590d\u6838\u5de5\u4f5c\u53f0\u5931\u8d25: @error',
    'appealAdmin.review.metric.primary': '\u521d\u5ba1\u603b\u91cf',
    'appealAdmin.review.metric.primary.helper':
        '\u5f53\u524d\u5904\u4e8e\u521d\u5ba1\u5c42\u7684\u590d\u6838\u8bb0\u5f55\u603b\u6570',
    'appealAdmin.review.metric.secondary': '\u590d\u5ba1\u603b\u91cf',
    'appealAdmin.review.metric.secondary.helper':
        '\u5f53\u524d\u5904\u4e8e\u590d\u5ba1\u5c42\u7684\u590d\u6838\u8bb0\u5f55\u603b\u6570',
    'appealAdmin.review.metric.final': '\u7ec8\u5ba1\u603b\u91cf',
    'appealAdmin.review.metric.final.helper':
        '\u5f53\u524d\u5904\u4e8e\u7ec8\u5ba1\u5c42\u7684\u590d\u6838\u8bb0\u5f55\u603b\u6570',
    'appealAdmin.review.metric.today': '\u4eca\u65e5\u5df2\u590d\u6838',
    'appealAdmin.review.metric.today.helper':
        '\u5f53\u524d\u5df2\u52a0\u8f7d\u6570\u636e\u96c6\u4e2d\u4eca\u65e5\u5b8c\u6210\u7684\u590d\u6838\u6570',
    'appealAdmin.review.metric.pendingStart': '\u5f85\u542f\u52a8\u590d\u6838',
    'appealAdmin.review.metric.pendingStart.helper':
        '\u5df2\u53d7\u7406\u4f46\u5c1a\u672a\u8fdb\u5165\u6b63\u5f0f\u590d\u6838\u7684\u7533\u8bc9',
    'appealAdmin.review.metric.inProgress': '\u590d\u6838\u4e2d\u7533\u8bc9',
    'appealAdmin.review.metric.inProgress.helper':
        '\u5f53\u524d\u5904\u4e8e\u590d\u6838\u73af\u8282\u7684\u7533\u8bc9\u6570',
    'appealAdmin.review.metric.visibleTotal':
        '\u5df2\u52a0\u8f7d\u590d\u6838\u8bb0\u5f55: @count',
    'appealAdmin.review.metric.visibleApproved':
        '\u5f53\u524d\u5217\u8868\u901a\u8fc7: @count',
    'appealAdmin.review.metric.visibleRejected':
        '\u5f53\u524d\u5217\u8868\u9a73\u56de: @count',
    'appealAdmin.review.quick.today': '\u67e5\u770b\u4eca\u65e5\u590d\u6838',
    'appealAdmin.review.quick.pendingStart':
        '\u67e5\u770b\u5f85\u542f\u52a8\u7533\u8bc9',
    'appealAdmin.review.quick.inProgress':
        '\u67e5\u770b\u590d\u6838\u4e2d\u7533\u8bc9',
    'appealAdmin.review.quick.refreshWorkbench':
        '\u5237\u65b0\u5de5\u4f5c\u53f0',
    'appealAdmin.review.queue.title': '\u4f18\u5148\u5f85\u529e\u961f\u5217',
    'appealAdmin.review.queue.empty':
        '\u5f53\u524d\u6ca1\u6709\u5df2\u53d7\u7406\u4e14\u7b49\u5f85\u590d\u6838\u7684\u7533\u8bc9',
    'appealAdmin.review.queue.reason': '\u7533\u8bc9\u539f\u56e0: @value',
    'appealAdmin.review.queue.status': '\u5f53\u524d\u8282\u70b9: @value',
    'appealAdmin.review.queue.time':
        '\u6700\u65b0\u8282\u70b9\u65f6\u95f4: @value',
    'appealAdmin.result.approved': '\u7533\u8bc9\u5df2\u901a\u8fc7',
    'appealAdmin.success.approved':
        '\u7533\u8bc9\u5df2\u5ba1\u6279\u901a\u8fc7',
    'appealAdmin.success.acceptanceRejected':
        '\u7533\u8bc9\u672a\u88ab\u53d7\u7406\uff0c\u7528\u6237\u4fee\u6539\u540e\u53ef\u91cd\u65b0\u63d0\u4ea4',
    'appealAdmin.success.supplementRequested':
        '\u5df2\u8981\u6c42\u7533\u8bc9\u4eba\u8865\u5145\u6750\u6599',
    'appealAdmin.success.supplementCompleted':
        '\u5df2\u6807\u8bb0\u8865\u5145\u5b8c\u6210\uff0c\u7533\u8bc9\u5df2\u9000\u56de\u5f85\u53d7\u7406',
    'appealAdmin.success.resubmitted':
        '\u7533\u8bc9\u5df2\u91cd\u65b0\u63d0\u4ea4\u5f85\u53d7\u7406',
    'appealAdmin.success.finalRejected':
        '\u7533\u8bc9\u7ec8\u5ba1\u5df2\u9a73\u56de',
    'appealAdmin.note.awaitingApplicantSupplement':
        '\u7b49\u5f85\u7533\u8bc9\u4eba\u63d0\u4ea4\u8865\u5145\u6750\u6599',
    'appealAdmin.note.awaitingApplicantResubmission':
        '\u7b49\u5f85\u7533\u8bc9\u4eba\u91cd\u65b0\u63d0\u4ea4\u7533\u8bc9',
    'appealAdmin.dialog.rejectTitle': '\u9a73\u56de\u7533\u8bc9',
    'appealAdmin.dialog.requestSupplementTitle':
        '\u8981\u6c42\u8865\u5145\u6750\u6599',
    'appealAdmin.field.rejectionReason': '\u9a73\u56de\u539f\u56e0',
    'appealAdmin.field.supplementReason':
        '\u8865\u5145\u8981\u6c42\u8bf4\u660e',
    'appealAdmin.validation.rejectionReasonRequired':
        '\u8bf7\u586b\u5199\u9a73\u56de\u539f\u56e0',
    'appealAdmin.validation.supplementReasonRequired':
        '\u8bf7\u586b\u5199\u9700\u8981\u8865\u5145\u7684\u6750\u6599\u8bf4\u660e',
    'appealAdmin.action.approve': '\u901a\u8fc7',
    'appealAdmin.action.reject': '\u9a73\u56de',
    'appealAdmin.action.relogin': '\u91cd\u65b0\u767b\u5f55',
    'appealAdmin.action.confirmReject': '\u786e\u8ba4\u9a73\u56de',
    'appealAdmin.action.confirmRequestSupplement': '\u786e\u8ba4\u8981\u6c42',
    'appealAdmin.note.alreadyProcessed':
        '\u6b64\u7533\u8bc9\u5df2\u5904\u7406\uff0c\u65e0\u6cd5\u518d\u6b21\u5ba1\u6279',
    'appealAdmin.note.adminApprovalOnly':
        '\u6743\u9650\u4e0d\u8db3\uff0c\u4ec5\u7ba1\u7406\u5458\u53ef\u5ba1\u6279\u7533\u8bc9',
    'deductionAdmin.page.title': '\u6263\u5206\u7ba1\u7406',
    'deductionAdmin.action.add': '\u6dfb\u52a0\u6263\u5206\u8bb0\u5f55',
    'deductionAdmin.action.refresh': '\u5237\u65b0\u5217\u8868',
    'deductionAdmin.action.retry': '\u91cd\u8bd5',
    'deductionAdmin.action.relogin': '\u91cd\u65b0\u767b\u5f55',
    'deductionAdmin.action.edit': '\u7f16\u8f91\u6263\u5206\u8bb0\u5f55',
    'deductionAdmin.action.delete': '\u5220\u9664\u6263\u5206\u8bb0\u5f55',
    'deductionAdmin.search.handler': '\u641c\u7d22\u5904\u7406\u4eba',
    'deductionAdmin.filter.byHandler': '\u6309\u5904\u7406\u4eba',
    'deductionAdmin.filter.byTimeRange': '\u6309\u65f6\u95f4\u8303\u56f4',
    'deductionAdmin.filter.dateRangeLabel':
        '\u6263\u5206\u65e5\u671f\u8303\u56f4\uff1a@start \u81f3 @end',
    'deductionAdmin.filter.selectDateRange':
        '\u9009\u62e9\u6263\u5206\u65e5\u671f\u8303\u56f4',
    'deductionAdmin.filter.tooltip':
        '\u6309\u6263\u5206\u65e5\u671f\u8303\u56f4\u641c\u7d22',
    'deductionAdmin.filter.clearDateRange':
        '\u6e05\u9664\u65f6\u95f4\u8303\u56f4',
    'deductionAdmin.error.unauthorized':
        '\u672a\u6388\u6743\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'deductionAdmin.error.expired':
        '\u767b\u5f55\u5df2\u8fc7\u671f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'deductionAdmin.error.invalidLogin':
        '\u65e0\u6548\u7684\u767b\u5f55\u4fe1\u606f\uff1a@error\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'deductionAdmin.error.adminOnly':
        '\u6743\u9650\u4e0d\u8db3\uff0c\u4ec5\u7ba1\u7406\u5458\u53ef\u8bbf\u95ee\u6b64\u9875\u9762',
    'deductionAdmin.error.initFailed': '\u521d\u59cb\u5316\u5931\u8d25: @error',
    'deductionAdmin.error.loadFailed':
        '\u52a0\u8f7d\u6263\u5206\u8bb0\u5f55\u5931\u8d25: @error',
    'deductionAdmin.error.filteredEmpty':
        '\u672a\u627e\u5230\u7b26\u5408\u6761\u4ef6\u7684\u6263\u5206\u8bb0\u5f55',
    'deductionAdmin.empty.default':
        '\u5f53\u524d\u6682\u65e0\u6263\u5206\u8bb0\u5f55',
    'deductionAdmin.error.request': '\u8bf7\u6c42\u9519\u8bef: @message',
    'deductionAdmin.error.forbidden': '\u65e0\u6743\u9650: @message',
    'deductionAdmin.error.notFound': '\u672a\u627e\u5230: @message',
    'deductionAdmin.error.duplicateRequest':
        '\u91cd\u590d\u8bf7\u6c42: @message',
    'deductionAdmin.error.server': '\u670d\u52a1\u5668\u9519\u8bef: @message',
    'deductionAdmin.error.operationFailed': '\u64cd\u4f5c\u5931\u8d25: @error',
    'deductionAdmin.card.points': '\u6263\u5206\uff1a@value',
    'deductionAdmin.card.summary':
        '\u5904\u7406\u4eba\uff1a@handler | \u65f6\u95f4\uff1a@time | \u8fdd\u6cd5 ID\uff1a@offenseId',
    'deductionAdmin.dialog.deleteTitle': '\u786e\u8ba4\u5220\u9664',
    'deductionAdmin.dialog.deleteBody':
        '\u786e\u5b9a\u8981\u5220\u9664\u6b64\u6263\u5206\u8bb0\u5f55\u5417\uff1f',
    'deductionAdmin.success.deleted':
        '\u6263\u5206\u8bb0\u5f55\u5220\u9664\u6210\u529f',
    'deductionAdmin.error.deleteFailed':
        '\u5220\u9664\u6263\u5206\u8bb0\u5f55\u5931\u8d25: @error',
    'deductionAdmin.form.addTitle': '\u6dfb\u52a0\u6263\u5206\u4fe1\u606f',
    'deductionAdmin.form.editTitle': '\u7f16\u8f91\u6263\u5206\u4fe1\u606f',
    'deductionAdmin.field.offenseRecord': '\u8fdd\u6cd5\u8bb0\u5f55',
    'deductionAdmin.field.deductedPoints': '\u6263\u5206\u5206\u6570',
    'deductionAdmin.field.handler': '\u5904\u7406\u4eba',
    'deductionAdmin.field.approver': '\u5ba1\u6279\u4eba',
    'deductionAdmin.field.remarks': '\u5907\u6ce8',
    'deductionAdmin.field.deductionTime': '\u6263\u5206\u65f6\u95f4',
    'deductionAdmin.helper.selectOffense':
        '\u8bf7\u9009\u62e9\u4e00\u6761\u8fdd\u6cd5\u8bb0\u5f55',
    'deductionAdmin.helper.nameOptional':
        '\u8bf7\u8f93\u5165 @field\uff08\u9009\u586b\uff09',
    'deductionAdmin.helper.points':
        '\u8bf7\u8f93\u5165\u6263\u5206\u70b9\u6570',
    'deductionAdmin.helper.date': '\u8bf7\u9009\u62e9\u6263\u5206\u65e5\u671f',
    'deductionAdmin.validation.required': '@field\u4e0d\u80fd\u4e3a\u7a7a',
    'deductionAdmin.validation.pointsNumber':
        '\u6263\u5206\u5206\u6570\u5fc5\u987b\u662f\u6570\u5b57',
    'deductionAdmin.validation.pointsNegative':
        '\u6263\u5206\u5206\u6570\u4e0d\u80fd\u4e3a\u8d1f\u6570',
    'deductionAdmin.validation.pointsTooLarge':
        '\u6263\u5206\u5206\u6570\u4e0d\u80fd\u8d85\u8fc7 12',
    'deductionAdmin.validation.nameTooLong':
        '@field\u4e0d\u80fd\u8d85\u8fc7 100 \u4e2a\u5b57\u7b26',
    'deductionAdmin.validation.remarksTooLong':
        '\u5907\u6ce8\u4e0d\u80fd\u8d85\u8fc7 255 \u4e2a\u5b57\u7b26',
    'deductionAdmin.validation.dateInvalid':
        '\u65e0\u6548\u7684\u65e5\u671f\u683c\u5f0f',
    'deductionAdmin.validation.dateFuture':
        '\u6263\u5206\u65e5\u671f\u4e0d\u80fd\u665a\u4e8e\u4eca\u5929',
    'deductionAdmin.offense.option':
        '\u8fdd\u6cd5 ID\uff1a@id | \u6263\u5206\uff1a@points | \u65f6\u95f4\uff1a@time',
    'deductionAdmin.offense.fallbackOption': '\u8fdd\u6cd5 ID\uff1a@id',
    'deductionAdmin.error.offenseLoadFailed':
        '\u52a0\u8f7d\u8fdd\u6cd5\u8bb0\u5f55\u5931\u8d25: @error',
    'deductionAdmin.error.offenseSelectFailed':
        '\u9009\u62e9\u8fdd\u6cd5\u8bb0\u5f55\u5931\u8d25: @error',
    'deductionAdmin.error.selectOffenseFirst':
        '\u8bf7\u5148\u9009\u62e9\u4e00\u6761\u8fdd\u6cd5\u8bb0\u5f55',
    'deductionAdmin.success.created':
        '\u6263\u5206\u8bb0\u5f55\u521b\u5efa\u6210\u529f',
    'deductionAdmin.success.updated':
        '\u6263\u5206\u8bb0\u5f55\u66f4\u65b0\u6210\u529f',
    'deductionAdmin.error.createFailed':
        '\u521b\u5efa\u6263\u5206\u8bb0\u5f55\u5931\u8d25: @error',
    'deductionAdmin.error.updateFailed':
        '\u66f4\u65b0\u6263\u5206\u8bb0\u5f55\u5931\u8d25: @error',
    'vehicle.field.licensePlate': '\u8f66\u724c\u53f7',
    'vehicle.field.vehicleType': '\u8f66\u8f86\u7c7b\u578b',
    'vehicle.field.ownerName': '\u8f66\u4e3b\u59d3\u540d',
    'vehicle.field.idCardNumber': '\u8eab\u4efd\u8bc1\u53f7\u7801',
    'vehicle.field.contactNumber': '\u8054\u7cfb\u7535\u8bdd',
    'vehicle.field.engineNumber': '\u53d1\u52a8\u673a\u53f7',
    'vehicle.field.frameNumber': '\u8f66\u67b6\u53f7',
    'vehicle.field.vehicleColor': '\u8f66\u8eab\u989c\u8272',
    'vehicle.field.firstRegistrationDate':
        '\u9996\u6b21\u6ce8\u518c\u65e5\u671f',
    'vehicle.field.currentStatus': '\u5f53\u524d\u72b6\u6001',
    'vehicle.helper.plateSuffix':
        '\u8bf7\u8f93\u5165\u8f66\u724c\u53f7\u540e\u7f00\uff0c\u4f8b\u5982\uff1a12345',
    'vehicle.helper.idCard':
        '\u8bf7\u8f93\u516515\u621618\u4f4d\u8eab\u4efd\u8bc1\u53f7\u7801',
    'vehicle.helper.contact': '\u8bf7\u8f93\u516511\u4f4d\u624b\u673a\u53f7',
    'vehicle.hint.modifyIdCardInProfile':
        '\u8bf7\u5728\u7528\u6237\u4fe1\u606f\u7ba1\u7406\u4e2d\u4fee\u6539\u8eab\u4efd\u8bc1\u53f7\u7801',
    'vehicle.validation.required': '@field\u4e0d\u80fd\u4e3a\u7a7a',
    'vehicle.validation.licensePlateTooLong':
        '\u8f66\u724c\u53f7\u4e0d\u80fd\u8d85\u8fc720\u4e2a\u5b57\u7b26',
    'vehicle.validation.licensePlateInvalid':
        '\u8f66\u724c\u53f7\u683c\u5f0f\u65e0\u6548\uff08\u4f8b\u5982\uff1a\u9ed1A12345\uff09',
    'vehicle.validation.vehicleTypeTooLong':
        '\u8f66\u8f86\u7c7b\u578b\u4e0d\u80fd\u8d85\u8fc750\u4e2a\u5b57\u7b26',
    'vehicle.validation.ownerNameTooLong':
        '\u8f66\u4e3b\u59d3\u540d\u4e0d\u80fd\u8d85\u8fc7100\u4e2a\u5b57\u7b26',
    'vehicle.validation.idCardRequired':
        '\u8eab\u4efd\u8bc1\u53f7\u7801\u4e0d\u80fd\u4e3a\u7a7a',
    'vehicle.validation.idCardTooLong':
        '\u8eab\u4efd\u8bc1\u53f7\u7801\u4e0d\u80fd\u8d85\u8fc718\u4e2a\u5b57\u7b26',
    'vehicle.validation.idCardInvalid':
        '\u8eab\u4efd\u8bc1\u53f7\u7801\u683c\u5f0f\u65e0\u6548',
    'vehicle.validation.contactTooLong':
        '\u8054\u7cfb\u7535\u8bdd\u4e0d\u80fd\u8d85\u8fc720\u4e2a\u5b57\u7b26',
    'vehicle.validation.contactInvalid':
        '\u8bf7\u8f93\u5165\u6709\u6548\u768411\u4f4d\u624b\u673a\u53f7',
    'vehicle.validation.engineTooLong':
        '\u53d1\u52a8\u673a\u53f7\u4e0d\u80fd\u8d85\u8fc750\u4e2a\u5b57\u7b26',
    'vehicle.validation.frameTooLong':
        '\u8f66\u67b6\u53f7\u4e0d\u80fd\u8d85\u8fc750\u4e2a\u5b57\u7b26',
    'vehicle.validation.colorTooLong':
        '\u8f66\u8eab\u989c\u8272\u4e0d\u80fd\u8d85\u8fc750\u4e2a\u5b57\u7b26',
    'vehicle.validation.dateInvalid':
        '\u65e0\u6548\u7684\u65e5\u671f\u683c\u5f0f',
    'vehicle.validation.dateFuture':
        '\u9996\u6b21\u6ce8\u518c\u65e5\u671f\u4e0d\u80fd\u665a\u4e8e\u5f53\u524d\u65e5\u671f',
    'vehicle.validation.statusTooLong':
        '\u5f53\u524d\u72b6\u6001\u4e0d\u80fd\u8d85\u8fc750\u4e2a\u5b57\u7b26',
    'vehicle.error.jwtMissingRelogin':
        '\u672a\u627e\u5230 JWT\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'vehicle.error.jwtMissing': '\u672a\u627e\u5230 JWT',
    'vehicle.error.usernameMissingInJwt':
        'JWT \u4e2d\u672a\u627e\u5230\u7528\u6237\u540d',
    'vehicle.error.driverIdCardMissing':
        '\u672a\u627e\u5230\u8eab\u4efd\u8bc1\u53f7\u7801\uff0c\u8bf7\u786e\u4fdd\u9a7e\u9a76\u5458\u4fe1\u606f\u5df2\u5b8c\u5584',
    'vehicle.error.initializeFailed': '\u521d\u59cb\u5316\u5931\u8d25: @error',
    'vehicle.error.missingIdCard':
        '\u7f3a\u5c11\u8eab\u4efd\u8bc1\u53f7\u7801\uff0c\u65e0\u6cd5\u83b7\u53d6\u8f66\u8f86\u4fe1\u606f',
    'vehicle.empty.filtered':
        '\u672a\u627e\u5230\u7b26\u5408\u6761\u4ef6\u7684\u8f66\u8f86',
    'vehicle.empty': '\u60a8\u5f53\u524d\u6ca1\u6709\u8f66\u8f86\u8bb0\u5f55',
    'vehicle.error.invalidQuery':
        '\u8eab\u4efd\u8bc1\u53f7\u7801\u6216\u67e5\u8be2\u6761\u4ef6\u65e0\u6548\uff0c\u8bf7\u91cd\u8bd5',
    'vehicle.error.expired':
        '\u767b\u5f55\u5df2\u8fc7\u671f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'vehicle.error.refreshedExpired':
        '\u65b0\u767b\u5f55\u4fe1\u606f\u5df2\u8fc7\u671f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'vehicle.error.invalidLogin':
        '\u65e0\u6548\u7684\u767b\u5f55\u4fe1\u606f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'vehicle.error.roleCheckFailed':
        '\u9a8c\u8bc1\u89d2\u8272\u5931\u8d25: @error',
    'vehicle.error.notFound': '\u672a\u627e\u5230\u8f66\u8f86\u8bb0\u5f55',
    'vehicle.error.suggestionFailed':
        '\u83b7\u53d6\u5efa\u8bae\u5931\u8d25: @error',
    'vehicle.error.userInfoLoadFailed':
        '\u83b7\u53d6\u7528\u6237\u4fe1\u606f\u5931\u8d25: @error',
    'vehicle.error.driverInfoLoadFailed':
        '\u83b7\u53d6\u53f8\u673a\u4fe1\u606f\u5931\u8d25: @error',
    'vehicle.error.idMissingDelete':
        '\u65e0\u6cd5\u5220\u9664\uff1a\u7f3a\u5c11\u8f66\u8f86 ID',
    'vehicle.error.notFoundBySearchType':
        '\u672a\u627e\u5230\u7b26\u5408\u6761\u4ef6\u7684\u8f66\u8f86\uff0c\u53ef\u80fd @field "@query" \u4e0d\u5b58\u5728',
    'vehicle.error.unauthorized':
        '\u672a\u6388\u6743\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55',
    'vehicle.error.loadFailed':
        '\u83b7\u53d6\u8f66\u8f86\u4fe1\u606f\u5931\u8d25: @error',
    'vehicle.success.deleted': '\u5220\u9664\u8f66\u8f86\u6210\u529f',
    'vehicle.error.deleteFailed': '\u5220\u9664\u5931\u8d25: @error',
    'vehicle.dialog.deleteTitle': '\u786e\u8ba4\u5220\u9664',
    'vehicle.dialog.deleteConfirm':
        '\u60a8\u786e\u5b9a\u8981@action\u6b64\u8f66\u8f86\u5417\uff1f\u6b64\u64cd\u4f5c\u4e0d\u53ef\u64a4\u9500\u3002',
    'vehicle.action.delete': '\u5220\u9664',
    'vehicle.action.edit': '\u7f16\u8f91',
    'vehicle.action.refresh': '\u5237\u65b0\u8f66\u8f86',
    'vehicle.action.addInfo': '\u6dfb\u52a0\u65b0\u8f66\u8f86\u4fe1\u606f',
    'vehicle.action.add': '\u6dfb\u52a0\u65b0\u8f66\u8f86',
    'vehicle.action.relogin': '\u91cd\u65b0\u767b\u5f55',
    'vehicle.action.goLogin': '\u524d\u5f80\u767b\u5f55',
    'vehicle.search.plateHint': '\u641c\u7d22\u8f66\u724c\u53f7',
    'vehicle.search.typeHint': '\u641c\u7d22\u8f66\u8f86\u7c7b\u578b',
    'vehicle.search.byPlate': '\u6309\u8f66\u724c\u53f7',
    'vehicle.search.byType': '\u6309\u8f66\u8f86\u7c7b\u578b',
    'vehicle.filter.dateRangeLabel':
        '\u9996\u6b21\u6ce8\u518c\u65e5\u671f\uff1a@start \u81f3 @end',
    'vehicle.filter.selectDateRange':
        '\u9009\u62e9\u9996\u6b21\u6ce8\u518c\u65e5\u671f\u8303\u56f4',
    'vehicle.filter.tooltip':
        '\u6309\u9996\u6b21\u6ce8\u518c\u65e5\u671f\u8303\u56f4\u641c\u7d22',
    'vehicle.filter.startDate': '\u5f00\u59cb\u65e5\u671f',
    'vehicle.filter.endDate': '\u7ed3\u675f\u65e5\u671f',
    'vehicle.filter.clearDateRange': '\u6e05\u9664\u65e5\u671f\u8303\u56f4',
    'vehicle.page.title': '\u8f66\u8f86\u7ba1\u7406',
    'vehicle.workspace.eyebrow': '\u8f66\u8f86\u5de5\u4f5c\u53f0',
    'vehicle.workspace.title':
        '\u8f66\u8f86\u8fd0\u8425\u4e0e\u6ce8\u518c\u603b\u89c8',
    'vehicle.workspace.subtitle':
        '\u96c6\u4e2d\u67e5\u770b\u5df2\u52a0\u8f7d\u8f66\u8f86\u3001\u53ef\u7528\u72b6\u6001\u4e0e\u6ce8\u518c\u8986\u76d6\u60c5\u51b5\uff0c\u540c\u65f6\u5728\u540c\u4e00\u5de5\u4f5c\u533a\u5b8c\u6210\u641c\u7d22\u4e0e\u5237\u65b0\u3002',
    'vehicle.workspace.signal.query': '\u5f53\u524d\u641c\u7d22\uff1a@value',
    'vehicle.workspace.signal.queryIdle':
        '\u5f53\u524d\u672a\u542f\u7528\u641c\u7d22',
    'vehicle.workspace.signal.rangeIdle':
        '\u5f53\u524d\u672a\u8bbe\u7f6e\u9996\u6b21\u6ce8\u518c\u65e5\u671f\u8303\u56f4',
    'vehicle.workspace.metric.loaded': '\u5df2\u52a0\u8f7d',
    'vehicle.workspace.metric.visible': '\u53ef\u89c1',
    'vehicle.workspace.metric.active': '\u6b63\u5e38',
    'vehicle.workspace.metric.inactive': '\u975e\u6d3b\u8dc3',
    'vehicle.workspace.metric.type': '\u7c7b\u578b\u6570',
    'vehicle.workspace.filterEyebrow': '\u7b5b\u9009',
    'vehicle.workspace.filterTitle':
        '\u7ec6\u5316\u8f66\u8f86\u5de5\u4f5c\u533a',
    'vehicle.workspace.filterBody':
        '\u5207\u6362\u641c\u7d22\u6a21\u5f0f\uff0c\u5229\u7528\u81ea\u52a8\u8865\u5168\u5feb\u901f\u5b9a\u4f4d\u8f66\u8f86\uff0c\u5e76\u6309\u9996\u6b21\u6ce8\u518c\u65e5\u671f\u8303\u56f4\u7f29\u5c0f\u7ed3\u679c\u3002',
    'vehicle.workspace.filterMode': '\u641c\u7d22\u6a21\u5f0f',
    'vehicle.workspace.filterReset': '\u6e05\u7a7a\u7b5b\u9009',
    'vehicle.workspace.filterRefresh': '\u5237\u65b0\u5217\u8868',
    'vehicle.workspace.listEyebrow': '\u8bb0\u5f55',
    'vehicle.workspace.listTitle': '\u8f66\u8f86\u8bb0\u5f55',
    'vehicle.workspace.listBody':
        '\u5148\u5feb\u901f\u67e5\u770b\u5f53\u524d\u72b6\u6001\u3001\u8f66\u4e3b\u4fe1\u606f\u548c\u6ce8\u518c\u4fe1\u53f7\uff0c\u518d\u8fdb\u5165\u8be6\u60c5\u64cd\u4f5c\u3002',
    'vehicle.workspace.emptyTitle': '\u6682\u65e0\u8f66\u8f86',
    'vehicle.workspace.errorTitle':
        '\u8f66\u8f86\u5de5\u4f5c\u53f0\u4e0d\u53ef\u7528',
    'vehicle.card.plate': '\u8f66\u724c\u53f7: @value',
    'vehicle.card.type': '\u7c7b\u578b: @value',
    'vehicle.card.owner': '\u8f66\u4e3b: @value',
    'vehicle.card.status': '\u72b6\u6001: @value',
    'vehicle.value.noPlate': '\u672a\u77e5\u8f66\u724c',
    'vehicle.value.noType': '\u672a\u77e5\u7c7b\u578b',
    'vehicle.value.noOwner': '\u672a\u77e5\u8f66\u4e3b',
    'vehicle.status.active': '\u6b63\u5e38',
    'vehicle.status.inactive': '\u505c\u7528',
    'vehicle.status.suspended': '\u6682\u505c',
    'vehicle.status.archived': '\u5df2\u5f52\u6863',
    'vehicle.error.driverInfoMissingDetailed':
        '\u65e0\u6cd5\u83b7\u53d6\u9a7e\u9a76\u5458\u4fe1\u606f\u6216\u59d3\u540d (Driver ID: @driverId, Username: @username)',
    'vehicle.error.driverInfoMissing':
        '\u65e0\u6cd5\u83b7\u53d6\u9a7e\u9a76\u5458\u4fe1\u606f\u6216\u59d3\u540d',
    'vehicle.error.plateInvalid':
        '\u8f66\u724c\u53f7\u683c\u5f0f\u65e0\u6548\uff0c\u8bf7\u8f93\u5165\u6709\u6548\u8f66\u724c\u53f7\uff08\u4f8b\u5982\uff1a\u9ed1A12345\uff09',
    'vehicle.error.plateExists':
        '\u8f66\u724c\u53f7\u5df2\u5b58\u5728\uff0c\u8bf7\u4f7f\u7528\u5176\u4ed6\u8f66\u724c\u53f7',
    'vehicle.error.fillIdCardInProfile':
        '\u8bf7\u5230\u4e2a\u4eba-\u7528\u6237\u4fe1\u606f\u7ba1\u7406\u5904\u586b\u5199\u8eab\u4efd\u8bc1\u53f7\u7801',
    'vehicle.success.created': '\u521b\u5efa\u8f66\u8f86\u6210\u529f',
    'vehicle.error.createFailed':
        '\u521b\u5efa\u8f66\u8f86\u5931\u8d25: @error',
    'vehicle.error.httpStatus':
        '\u8bf7\u6c42\u5931\u8d25\uff08HTTP @statusCode\uff09\u3002',
    'vehicle.add.title': '\u6dfb\u52a0\u65b0\u8f66\u8f86',
    'vehicle.add.emptyPrompt':
        '\u60a8\u5f53\u524d\u6ca1\u6709\u8f66\u8f86\u8bb0\u5f55\uff0c\u8bf7\u6dfb\u52a0\u65b0\u8f66\u8f86',
    'vehicle.edit.title': '\u7f16\u8f91\u8f66\u8f86\u4fe1\u606f',
    'vehicle.success.updated': '\u66f4\u65b0\u8f66\u8f86\u6210\u529f',
    'vehicle.error.updateFailed':
        '\u66f4\u65b0\u8f66\u8f86\u5931\u8d25: @error',
    'vehicle.error.permissionLoadFailed':
        '\u52a0\u8f7d\u6743\u9650\u5931\u8d25: @error',
    'vehicle.detail.title': '\u8f66\u8f86\u8be6\u60c5',
    'vehicle.detail.editTooltip': '\u7f16\u8f91\u8f66\u8f86\u4fe1\u606f',
    'vehicle.detail.deleteTooltip': '\u5220\u9664\u8f66\u8f86',
    'vehicle.detail.type': '\u8f66\u8f86\u7c7b\u578b',
    'vehicle.detail.plate': '\u8f66\u724c\u53f7',
    'vehicle.detail.owner': '\u8f66\u4e3b\u59d3\u540d',
    'vehicle.detail.status': '\u8f66\u8f86\u72b6\u6001',
    'vehicle.detail.idCard': '\u8eab\u4efd\u8bc1\u53f7\u7801',
    'vehicle.detail.contact': '\u8054\u7cfb\u7535\u8bdd',
    'vehicle.detail.engine': '\u53d1\u52a8\u673a\u53f7',
    'vehicle.detail.frame': '\u8f66\u67b6\u53f7',
    'vehicle.detail.color': '\u8f66\u8eab\u989c\u8272',
    'vehicle.detail.firstRegistrationDate':
        '\u9996\u6b21\u6ce8\u518c\u65e5\u671f',
    'common.close': '关闭',
    'common.details': '详情',
    'common.error': '错误',
    'common.location.default': '哈尔滨',
    'common.pageNotFound': '页面未找到',
    'dashboard.error.title': '错误',
    'dashboard.projectName': '交通违法处理管理系统',
    'dashboard.task.todo1': '待办任务 1',
    'dashboard.task.inProgress1': '进行中任务 1',
    'dashboard.task.done1': '已完成任务 1',
    'chart.title.presentation': '图表展示',
    'chart.currentTimeLabel': '当前时间：',
    'captcha.dialog.title': '验证码验证',
    'captcha.action.verify': '验证验证码',
    'captcha.input.label': '输入验证码',
    'captcha.input.hint': '请输入验证码',
    'captcha.validation.required': '请输入验证码',
    'captcha.validation.length': '验证码长度应为 @length',
    'captcha.validation.invalid': '验证码错误，请重试。',
    'chat.modal.title': '提示',
    'chat.confirmAction.title': '确认执行',
    'chat.confirmAction.message': 'Agent 给出了可执行动作，是否继续？',
    'chat.error.requestTitle': 'Agent 请求失败',
    'chat.error.requestBody': '请求失败，请稍后重试。',
    'chat.error.noContent': '暂时没有返回内容。',
    'chat.error.actionUnavailableTitle': '动作暂不可执行',
    'chat.error.actionUnavailableBody': '当前动作缺少可执行目标。',
    'chat.status.preparing': '正在整理方案...',
    'chat.status.processing': '正在处理中...',
    'today.location.default': '哈尔滨',
    'news.menu.title': '用户指南',
    'news.menu.latest.title': '最新交通违法新闻',
    'news.menu.latest.description': '了解近期政策更新和执法动态',
    'news.menu.fine.title': '罚款缴纳须知',
    'news.menu.fine.description': '查看罚款缴纳的最新指引',
    'news.menu.quickGuide.title': '事故快处指南',
    'news.menu.quickGuide.description': '快速了解事故处理关键步骤',
    'news.menu.progress.title': '事故处理进度介绍',
    'news.menu.progress.description': '了解如何跟踪事故处理状态',
    'news.menu.evidence.title': '事故证据材料',
    'news.menu.evidence.description': '查看事故处理所需证据材料',
    'news.menu.video.title': '事故视频快处',
    'news.menu.video.description': '通过视频取证提升事故处理效率',
    'news.accidentEvidence.title': '事故证据材料',
    'news.accidentEvidence.section.required': '必备证据',
    'news.accidentEvidence.photo.title': '照片资料',
    'news.accidentEvidence.photo.body': '需要提供事故现场、车辆损坏、路面状况的多角度照片。',
    'news.accidentEvidence.video.title': '视频资料',
    'news.accidentEvidence.video.body': '如有行车记录仪视频或监控视频，可大幅提升处理效率。',
    'news.accidentEvidence.detail.title': '事故详情',
    'news.accidentEvidence.detail.body': '包括事故时间、地点、天气情况以及双方驾驶员信息。',
    'news.accidentQuickGuide.title': '事故快处指南',
    'news.accidentQuickGuide.section.steps': '快速处理步骤',
    'news.accidentQuickGuide.section.notice': '注意事项',
    'news.accidentQuickGuide.step1.title': '1. 确保安全',
    'news.accidentQuickGuide.step1.body': '将车辆移至安全位置，打开警示灯。',
    'news.accidentQuickGuide.step2.title': '2. 拍照取证',
    'news.accidentQuickGuide.step2.body': '拍摄事故现场照片，至少三张不同角度。',
    'news.accidentQuickGuide.step3.title': '3. 在线提交',
    'news.accidentQuickGuide.step3.body': '通过系统上传照片并填写事故详情。',
    'news.accidentQuickGuide.step4.title': '4. 时间限制',
    'news.accidentQuickGuide.step4.body': '需在事故发生后 24 小时内提交。',
    'news.accidentProgress.title': '事故处理状态追踪',
    'news.accidentProgress.section.howTo': '如何跟踪事故处理状态',
    'news.accidentProgress.step1.title': '1. 登录系统',
    'news.accidentProgress.step1.body': '使用您的账号登录交通违法处理管理系统，进入用户仪表板。',
    'news.accidentProgress.step2.title': '2. 进入事故管理',
    'news.accidentProgress.step2.body': '在仪表板中选择事故管理入口，查看已提交的事故记录。',
    'news.accidentProgress.step3.title': '3. 查看进度详情',
    'news.accidentProgress.step3.body': '打开具体事故记录，查看已提交、审核中或已完成等状态。',
    'news.accidentProgress.section.tips': '实用建议',
    'news.accidentProgress.tip1.title': '定期检查',
    'news.accidentProgress.tip1.body': '建议每周登录系统检查事故处理进度，确保及时响应审核要求。',
    'news.accidentProgress.tip2.title': '通知设置',
    'news.accidentProgress.tip2.body': '启用系统通知，获取状态更新的实时提醒，避免遗漏重要信息。',
    'news.accidentVideo.title': '事故视频快处',
    'news.accidentVideo.section.flow': '视频快处流程',
    'news.accidentVideo.step1.title': '1. 录制视频',
    'news.accidentVideo.step1.body': '拍摄事故现场视频，时长不超过 1 分钟。',
    'news.accidentVideo.step2.title': '2. 上传视频',
    'news.accidentVideo.step2.body': '通过系统上传视频文件，支持 MP4 格式。',
    'news.accidentVideo.step3.title': '3. 提交审核',
    'news.accidentVideo.step3.body': '填写事故详情并提交，等待处理结果。',
    'news.accidentVideo.section.advantages': '优势',
    'news.accidentVideo.advantage.title': '快速高效',
    'news.accidentVideo.advantage.body': '视频快处可减少现场等待时间，最快 24 小时内完成审核。',
    'news.fineNotice.title': '罚款缴纳须知',
    'news.fineNotice.section.flow': '缴纳流程',
    'news.fineNotice.step1.title': '1. 进入罚款管理',
    'news.fineNotice.step1.body': '进入罚款管理模块，查看待缴纳的罚款记录。',
    'news.fineNotice.step2.title': '2. 选择罚款记录',
    'news.fineNotice.step2.body': '核对罚款金额和扣分信息。',
    'news.fineNotice.step3.title': '3. 确认支付',
    'news.fineNotice.step3.body': '支持线上支付，完成后系统会自动更新状态。',
    'news.fineNotice.section.tip': '温馨提示',
    'news.fineNotice.tip.title': '及时缴纳',
    'news.fineNotice.tip.body': '逾期缴纳可能导致额外费用或影响驾驶信用。',
    'news.latest.title': '最新交通违法新闻',
    'news.latest.section.headlines': '头条新闻',
    'news.latest.item1.title': '2025 年新交规实施',
    'news.latest.item1.body': '自 2025 年 1 月 1 日起，超速 10% 以上将面临更高罚款和扣分，旨在提升道路安全。',
    'news.latest.section.recent': '近期动态',
    'news.latest.item2.title': '酒驾专项整治启动',
    'news.latest.item2.body': '全国范围内开展为期三个月的酒驾整治行动，已查处 3000 余起违法行为。',
    'news.latest.item3.title': '智能监控升级',
    'news.latest.item3.body': '新增 1000 个智能摄像头，覆盖主要城市，自动识别闯红灯和超速行为。',
    'news.latest.section.expert': '专家建议',
    'news.latest.expert.title': '遵守交通法规',
    'news.latest.expert.body': '专家呼吁司机严格遵守新规，避免不必要的罚款和安全隐患。',
    'scan.pageTitle': '二维码生成',
    'scan.dialog.fineQr': '罚款二维码',
    'scan.dialog.genericQr': '二维码',
    'scan.action.generate': '生成二维码',
    'scan.action.regenerate': '重新生成',
    'scan.error.generateFailed': '生成二维码失败：@error',
    'scan.fineDetail.title': '罚款详情',
    'scan.field.fineId': '罚款编号',
    'scan.field.fineAmount': '罚款金额',
    'scan.field.payee': '缴纳对象',
    'scan.field.paymentStatus': '缴纳状态',
    'scan.status.notGenerated': '尚未生成二维码。',
    'scan.status.generated': '已生成二维码',
    'scan.status.waiting': '等待生成二维码',
    'questions.user.title': '用户常见问题',
    'questions.user.item1': '如何查询我的交通违法记录？',
    'questions.user.item2': '罚款缴纳的流程是什么？',
    'questions.user.item3': '交通违法申诉需要哪些材料？',
    'questions.user.item4': '我的罚款什么时候到期？',
    'questions.user.item5': '如何处理超速违章？',
    'questions.admin.title': '管理员预定义问题',
    'questions.admin.item1': '如何查看所有未处理的交通违法记录？',
    'questions.admin.item2': '如何统计本月罚款缴纳总额？',
    'questions.admin.item3': '有哪些待审核的交通违法申诉？',
    'questions.admin.item4': '如何批量更新罚款到期状态？',
    'questions.admin.item5': '超速违章的处理流程是什么？',
    'news.latest.heroLabel': '实时头条',
    'news.latest.section.liveFeed': '实时交通新闻流',
    'news.latest.loading': '正在加载实时交通新闻...',
    'news.latest.emptyRealtime': '当前暂无可展示的实时交通新闻',
    'news.latest.loadFailed': '加载实时交通新闻失败: @error',
    'news.latest.action.retry': '重试',
    'news.latest.action.refresh': '刷新实时新闻',
    'news.latest.field.source': '来源: @value',
    'news.latest.field.publishedAt': '发布时间: @value',
    'news.latest.source.unknown': '未知来源',
  };
}
