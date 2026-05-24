import 'package:final_assignment_front/config/routes/app_routes.dart';
import 'package:final_assignment_front/features/dashboard/views/admin/admin_dashboard_screen.dart';

class ManagerDashboardScreen extends AdminDashboardScreen {
  const ManagerDashboardScreen({super.key})
      : super(
          titleKey: 'manager.title',
          subtitleKey: 'manager.subtitle',
          pageTitleKey: 'manager.pageTitle',
          workspaceEyebrowKey: 'common.managerConsole',
          summaryKey: 'manager.metric.modeDetail',
          modeValueKey: 'manager.metric.modeValue',
          coreEntriesTitleKey: 'manager.coreEntries',
          secondaryActionLabelKey: 'manager.hero.secondary',
          businessRoute: Routes.managerBusinessProcessing,
          profileRoute: Routes.managerPersonalPage,
          settingsRoute: Routes.managerSetting,
        );
}
